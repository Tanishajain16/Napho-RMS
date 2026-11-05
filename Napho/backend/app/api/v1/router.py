from fastapi import APIRouter

from app.api.v1 import auth, users, claims, approvals, notifications, categories, uploads
from app.api.v1 import analytics, admin, chat, payments

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(claims.router)
api_router.include_router(approvals.router)
api_router.include_router(payments.router)
api_router.include_router(notifications.router)
api_router.include_router(categories.router)
api_router.include_router(uploads.router)
api_router.include_router(analytics.router)
api_router.include_router(admin.router)
api_router.include_router(chat.router)
