"""Aggregates all v1 route modules into one router."""

from fastapi import APIRouter

from app.api.v1.routes import health, statements, transactions

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(statements.router)
api_v1_router.include_router(transactions.router)
