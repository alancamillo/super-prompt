"""Routes - Rotas da API."""

from .prompts import router as prompts_router
from .executions import router as executions_router
from .feedbacks import router as feedbacks_router
from .analytics import router as analytics_router

__all__ = [
    "prompts_router",
    "executions_router",
    "feedbacks_router",
    "analytics_router",
]

