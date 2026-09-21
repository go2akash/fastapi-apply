from fastapi import APIRouter
from app.api.v1.endpoints import health
from app.api.v1.endpoints import user
from app.api.v1.endpoints import chat

v1_router = APIRouter()

v1_router.include_router(health.router)
v1_router.include_router(user.router)
v1_router.include_router(chat.router)
