"""Aggregates all v1 route modules into one router."""

from fastapi import APIRouter

from app.api.v1.routes import categories, chat, health, statements, summary, transactions

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(categories.router)
api_v1_router.include_router(statements.router)
api_v1_router.include_router(summary.router)
api_v1_router.include_router(transactions.router)
api_v1_router.include_router(chat.router)
