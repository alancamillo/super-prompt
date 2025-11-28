"""Models - modelos SQLAlchemy e schemas Pydantic."""

from .db_models import PromptTemplate, OptimizationRequest, PromptExecution, Feedback, FeedbackType
from .schemas import (
    # Prompt Templates
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptTemplateListResponse,
    # Optimization
    OptimizationRequestCreate,
    OptimizationRequestResponse,
    OptimizePromptRequest,
    OptimizePromptResponse,
    # Executions
    PromptExecutionCreate,
    PromptExecutionUpdate,
    PromptExecutionResponse,
    # Feedbacks
    FeedbackCreate,
    FeedbackResponse,
    FeedbackListResponse,
)

__all__ = [
    # DB Models
    "PromptTemplate",
    "OptimizationRequest", 
    "PromptExecution",
    "Feedback",
    "FeedbackType",
    # Schemas
    "PromptTemplateCreate",
    "PromptTemplateUpdate",
    "PromptTemplateResponse",
    "PromptTemplateListResponse",
    "OptimizationRequestCreate",
    "OptimizationRequestResponse",
    "OptimizePromptRequest",
    "OptimizePromptResponse",
    "PromptExecutionCreate",
    "PromptExecutionUpdate",
    "PromptExecutionResponse",
    "FeedbackCreate",
    "FeedbackResponse",
    "FeedbackListResponse",
]

