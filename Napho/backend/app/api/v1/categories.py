from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_org, get_current_user
from app.database import get_db
from app.models.expense_category import ExpenseCategory
from app.schemas.expense_category import CategoryOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["Categories"])


def _build_tree(categories: list[ExpenseCategory]) -> list[CategoryOut]:
    """Build a tree-shaped list of CategoryOut from a flat list."""
    # Index by id
    id_to_cat: dict[str, CategoryOut] = {}
    for cat in categories:
        id_to_cat[cat.id] = CategoryOut(
            id=cat.id,
            name=cat.name,
            code=cat.code,
            icon=cat.icon,
            requires_receipt=cat.requires_receipt,
            max_amount=cat.max_amount,
            is_active=cat.is_active,
            sort_order=cat.sort_order,
            children=[],
        )

    roots: list[CategoryOut] = []
    for cat in categories:
        node = id_to_cat[cat.id]
        if cat.parent_id and cat.parent_id in id_to_cat:
            id_to_cat[cat.parent_id].children.append(node)
        else:
            roots.append(node)

    # Sort at each level by sort_order
    def _sort_tree(nodes: list[CategoryOut]) -> list[CategoryOut]:
        nodes.sort(key=lambda n: n.sort_order)
        for node in nodes:
            _sort_tree(node.children)
        return nodes

    return _sort_tree(roots)


@router.get("", response_model=list[CategoryOut])
def list_categories(
    current_user=Depends(get_current_user),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> list[CategoryOut]:
    """Return tree-shaped expense categories for the current organisation."""
    categories = (
        db.query(ExpenseCategory)
        .filter(
            ExpenseCategory.org_id == org.id,
            ExpenseCategory.is_active == True,  # noqa: E712
        )
        .order_by(ExpenseCategory.sort_order)
        .all()
    )

    return _build_tree(categories)
