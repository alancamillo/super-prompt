"""Dependencies para injeção de dependências FastAPI."""

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.cache import get_cache_service, CacheService
from ..services.similarity import get_similarity_service, SimilarityService
from ..services.optimizer import OptimizerService
from ..repositories.prompt_repo import PromptTemplateRepository
from ..repositories.optimization_repo import OptimizationRepository
from ..repositories.execution_repo import ExecutionRepository
from ..repositories.feedback_repo import FeedbackRepository


async def get_prompt_repo(
    session: AsyncSession = Depends(get_db)
) -> PromptTemplateRepository:
    """Dependency para PromptTemplateRepository."""
    return PromptTemplateRepository(session)


async def get_optimization_repo(
    session: AsyncSession = Depends(get_db)
) -> OptimizationRepository:
    """Dependency para OptimizationRepository."""
    return OptimizationRepository(session)


async def get_execution_repo(
    session: AsyncSession = Depends(get_db)
) -> ExecutionRepository:
    """Dependency para ExecutionRepository."""
    return ExecutionRepository(session)


async def get_feedback_repo(
    session: AsyncSession = Depends(get_db)
) -> FeedbackRepository:
    """Dependency para FeedbackRepository."""
    return FeedbackRepository(session)


async def get_optimizer_service(
    session: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
    similarity: SimilarityService = Depends(get_similarity_service),
) -> OptimizerService:
    """Dependency para OptimizerService."""
    return OptimizerService(
        session=session,
        cache_service=cache,
        similarity_service=similarity,
    )

