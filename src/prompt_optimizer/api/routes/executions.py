"""Endpoints para execuções de prompts."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...models.schemas import (
    PromptExecutionCreate,
    PromptExecutionUpdate,
    PromptExecutionResponse,
)
from ...repositories.execution_repo import ExecutionRepository
from ..dependencies import get_execution_repo

router = APIRouter(prefix="/executions", tags=["executions"])


@router.post(
    "",
    response_model=PromptExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra uma execução de prompt",
    description="""
    Registra a execução de um prompt com a resposta do LLM.
    
    Use este endpoint após enviar o prompt para o LLM para:
    - Armazenar o prompt renderizado
    - Armazenar a resposta do LLM
    - Registrar métricas (tokens, latência)
    - Permitir feedback posterior
    """,
)
async def create_execution(
    data: PromptExecutionCreate,
    repo: ExecutionRepository = Depends(get_execution_repo),
) -> PromptExecutionResponse:
    """Cria um novo registro de execução."""
    execution = await repo.create(data)
    return PromptExecutionResponse.model_validate(execution)


@router.get(
    "/{execution_id}",
    response_model=PromptExecutionResponse,
    summary="Busca execução por ID",
)
async def get_execution(
    execution_id: UUID,
    repo: ExecutionRepository = Depends(get_execution_repo),
) -> PromptExecutionResponse:
    """Busca uma execução específica pelo ID."""
    execution = await repo.get_by_id(execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execução {execution_id} não encontrada",
        )
    return PromptExecutionResponse.model_validate(execution)


@router.get(
    "",
    response_model=list[PromptExecutionResponse],
    summary="Lista execuções",
)
async def list_executions(
    request_id: Optional[UUID] = Query(None, description="Filtrar por requisição de otimização"),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    days: int = Query(30, ge=1, le=365, description="Últimos N dias"),
    repo: ExecutionRepository = Depends(get_execution_repo),
) -> list[PromptExecutionResponse]:
    """Lista execuções recentes."""
    skip = (page - 1) * page_size
    
    if request_id:
        executions = await repo.get_by_optimization_request(request_id)
        # Paginar manualmente
        executions = executions[skip:skip + page_size]
    else:
        executions, _ = await repo.list_recent(
            skip=skip, 
            limit=page_size,
            days=days,
        )
    
    return [PromptExecutionResponse.model_validate(e) for e in executions]


@router.patch(
    "/{execution_id}",
    response_model=PromptExecutionResponse,
    summary="Atualiza uma execução",
    description="""
    Atualiza dados de uma execução.
    
    Use para adicionar/atualizar:
    - Resposta do LLM
    - Modelo usado
    - Contagem de tokens
    - Latência
    """,
)
async def update_execution(
    execution_id: UUID,
    data: PromptExecutionUpdate,
    repo: ExecutionRepository = Depends(get_execution_repo),
) -> PromptExecutionResponse:
    """Atualiza uma execução existente."""
    execution = await repo.update(execution_id, data)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execução {execution_id} não encontrada",
        )
    return PromptExecutionResponse.model_validate(execution)


@router.get(
    "/pending/review",
    response_model=list[PromptExecutionResponse],
    summary="Lista execuções sem feedback",
    description="Lista execuções que ainda não receberam feedback para revisão.",
)
async def list_pending_review(
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    repo: ExecutionRepository = Depends(get_execution_repo),
) -> list[PromptExecutionResponse]:
    """Lista execuções pendentes de revisão."""
    skip = (page - 1) * page_size
    executions, _ = await repo.list_without_feedback(skip=skip, limit=page_size)
    return [PromptExecutionResponse.model_validate(e) for e in executions]

