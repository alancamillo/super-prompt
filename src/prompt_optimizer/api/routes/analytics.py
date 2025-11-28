"""Endpoints para métricas e analytics."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query

from ...models.schemas import (
    TokenSavingsResponse,
    SimilarityHitsResponse,
    FeedbackSummaryResponse,
)
from ...repositories.optimization_repo import OptimizationRepository
from ...repositories.execution_repo import ExecutionRepository
from ...repositories.feedback_repo import FeedbackRepository
from ..dependencies import (
    get_optimization_repo, 
    get_execution_repo, 
    get_feedback_repo,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/token-savings",
    response_model=TokenSavingsResponse,
    summary="Economia de tokens",
    description="""
    Retorna métricas de economia de tokens.
    
    Calcula:
    - Total de requisições
    - Hits de cache
    - Taxa de cache hit
    - Estimativa de tokens economizados
    """,
)
async def get_token_savings(
    days: int = Query(30, ge=1, le=365, description="Período em dias"),
    optimization_repo: OptimizationRepository = Depends(get_optimization_repo),
    execution_repo: ExecutionRepository = Depends(get_execution_repo),
) -> TokenSavingsResponse:
    """Calcula economia de tokens."""
    # Estatísticas de similaridade
    total_requests, similarity_matches, _ = await optimization_repo.count_similarity_matches(days)
    
    # Estatísticas de tokens
    total_executions, total_input, total_output = await execution_repo.get_token_stats(days)
    
    # Estimativa de tokens economizados (baseado na taxa de cache hit)
    # Assume que cada cache hit economiza a média de tokens por execução
    if total_executions > 0:
        avg_tokens_per_execution = (total_input + total_output) / total_executions
        estimated_savings = int(similarity_matches * avg_tokens_per_execution)
    else:
        estimated_savings = 0
    
    cache_hit_rate = (similarity_matches / total_requests) if total_requests > 0 else 0.0
    
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=days)
    
    return TokenSavingsResponse(
        total_requests=total_requests,
        cached_hits=similarity_matches,
        cache_hit_rate=cache_hit_rate,
        estimated_tokens_saved=estimated_savings,
        period_start=period_start,
        period_end=period_end,
    )


@router.get(
    "/similarity-hits",
    response_model=SimilarityHitsResponse,
    summary="Hits de similaridade",
    description="""
    Retorna métricas de busca por similaridade.
    
    Mostra:
    - Total de requisições
    - Matches de similaridade encontrados
    - Taxa de match
    - Score médio de similaridade
    """,
)
async def get_similarity_hits(
    days: int = Query(30, ge=1, le=365, description="Período em dias"),
    repo: OptimizationRepository = Depends(get_optimization_repo),
) -> SimilarityHitsResponse:
    """Retorna estatísticas de hits de similaridade."""
    total, matches, avg_score = await repo.count_similarity_matches(days)
    
    match_rate = (matches / total) if total > 0 else 0.0
    
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=days)
    
    return SimilarityHitsResponse(
        total_requests=total,
        similarity_matches=matches,
        match_rate=match_rate,
        average_similarity_score=avg_score,
        period_start=period_start,
        period_end=period_end,
    )


@router.get(
    "/feedback-summary",
    response_model=FeedbackSummaryResponse,
    summary="Resumo de feedbacks",
    description="""
    Retorna resumo estatístico dos feedbacks.
    
    Inclui:
    - Total de feedbacks
    - Média de rating
    - Contagem por tipo (positive, negative, suggestion)
    - Feedbacks pendentes de revisão
    """,
)
async def get_feedback_summary(
    days: int = Query(30, ge=1, le=365, description="Período em dias"),
    repo: FeedbackRepository = Depends(get_feedback_repo),
) -> FeedbackSummaryResponse:
    """Retorna resumo de feedbacks."""
    summary = await repo.get_summary(days)
    return FeedbackSummaryResponse(**summary)

