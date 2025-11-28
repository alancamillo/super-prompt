"""Endpoints para feedback human-in-the-loop."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...models.schemas import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackListResponse,
)
from ...repositories.feedback_repo import FeedbackRepository
from ...repositories.execution_repo import ExecutionRepository
from ..dependencies import get_feedback_repo, get_execution_repo

router = APIRouter(prefix="/feedbacks", tags=["feedbacks"])


@router.post(
    "/executions/{execution_id}",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona feedback a uma execução",
    description="""
    Adiciona feedback humano a uma execução de prompt.
    
    Tipos de feedback:
    - **positive**: A resposta foi satisfatória
    - **negative**: A resposta teve problemas
    - **suggestion**: Sugestão de melhoria para o prompt
    
    O feedback pode incluir:
    - Rating (1-5)
    - Observação sobre o problema/acerto
    - Sugestão de correção para o prompt
    """,
)
async def add_feedback(
    execution_id: UUID,
    data: FeedbackCreate,
    feedback_repo: FeedbackRepository = Depends(get_feedback_repo),
    execution_repo: ExecutionRepository = Depends(get_execution_repo),
) -> FeedbackResponse:
    """Adiciona feedback a uma execução."""
    # Verifica se a execução existe
    execution = await execution_repo.get_by_id(execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execução {execution_id} não encontrada",
        )
    
    feedback = await feedback_repo.create(execution_id, data)
    return FeedbackResponse.model_validate(feedback)


@router.get(
    "/executions/{execution_id}",
    response_model=list[FeedbackResponse],
    summary="Lista feedbacks de uma execução",
)
async def list_execution_feedbacks(
    execution_id: UUID,
    feedback_repo: FeedbackRepository = Depends(get_feedback_repo),
    execution_repo: ExecutionRepository = Depends(get_execution_repo),
) -> list[FeedbackResponse]:
    """Lista todos os feedbacks de uma execução."""
    # Verifica se a execução existe
    execution = await execution_repo.get_by_id(execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execução {execution_id} não encontrada",
        )
    
    feedbacks = await feedback_repo.get_by_execution(execution_id)
    return [FeedbackResponse.model_validate(f) for f in feedbacks]


@router.get(
    "/{feedback_id}",
    response_model=FeedbackResponse,
    summary="Busca feedback por ID",
)
async def get_feedback(
    feedback_id: UUID,
    repo: FeedbackRepository = Depends(get_feedback_repo),
) -> FeedbackResponse:
    """Busca um feedback específico pelo ID."""
    feedback = await repo.get_by_id(feedback_id)
    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback {feedback_id} não encontrado",
        )
    return FeedbackResponse.model_validate(feedback)


@router.get(
    "/pending",
    response_model=FeedbackListResponse,
    summary="Lista feedbacks pendentes de revisão",
    description="Lista feedbacks do tipo 'suggestion' que precisam ser revisados.",
)
async def list_pending_feedbacks(
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    repo: FeedbackRepository = Depends(get_feedback_repo),
) -> FeedbackListResponse:
    """Lista feedbacks pendentes de revisão."""
    skip = (page - 1) * page_size
    feedbacks, total = await repo.list_pending_review(skip=skip, limit=page_size)
    
    return FeedbackListResponse(
        items=[FeedbackResponse.model_validate(f) for f in feedbacks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "",
    response_model=FeedbackListResponse,
    summary="Lista feedbacks recentes",
)
async def list_feedbacks(
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    days: int = Query(30, ge=1, le=365, description="Últimos N dias"),
    repo: FeedbackRepository = Depends(get_feedback_repo),
) -> FeedbackListResponse:
    """Lista feedbacks recentes."""
    skip = (page - 1) * page_size
    feedbacks, total = await repo.list_recent(
        skip=skip, 
        limit=page_size,
        days=days,
    )
    
    return FeedbackListResponse(
        items=[FeedbackResponse.model_validate(f) for f in feedbacks],
        total=total,
        page=page,
        page_size=page_size,
    )

