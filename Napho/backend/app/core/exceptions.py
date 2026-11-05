from __future__ import annotations

from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    """404 with a resource-specific message."""

    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found",
        )


class UnauthorizedError(HTTPException):
    """401 with WWW-Authenticate header."""

    def __init__(self, detail: str = "Not authenticated") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(HTTPException):
    """403 for authorisation failures."""

    def __init__(self, detail: str = "You do not have permission to perform this action") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class ConflictError(HTTPException):
    """409 for business-logic violations / state conflicts."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class ValidationError(HTTPException):
    """422 for semantic validation failures that Pydantic doesn't catch."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )
