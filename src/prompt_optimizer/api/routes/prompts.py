"""Endpoints para prompts e otimização."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...models.schemas import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptTemplateListResponse,
    OptimizePromptRequest,
    OptimizePromptResponse,
)
from ...repositories.prompt_repo import PromptTemplateRepository
from ...services.optimizer import OptimizerService
from ..dependencies import get_prompt_repo, get_optimizer_service

router = APIRouter(prefix="/prompts", tags=["prompts"])


# =============================================================================
# Otimização de Prompts
# =============================================================================

@router.post(
    "/optimize",
    response_model=OptimizePromptResponse,
    status_code=status.HTTP_200_OK,
    summary="Otimiza um prompt",
    description="""
    Recebe uma requisição e retorna um prompt otimizado.
    
    O sistema:
    1. Verifica cache para requisições idênticas
    2. Busca requisições similares no Weaviate
    3. Aplica template e variáveis
    4. Cacheia resultado para futuras requisições
    """,
)
async def optimize_prompt(
    request: OptimizePromptRequest,
    optimizer: OptimizerService = Depends(get_optimizer_service),
) -> OptimizePromptResponse:
    """Otimiza um prompt baseado na requisição."""
    return await optimizer.optimize(request)


# =============================================================================
# CRUD de Templates
# =============================================================================

@router.get(
    "/templates",
    response_model=PromptTemplateListResponse,
    summary="Lista templates de prompts",
)
async def list_templates(
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    active_only: bool = Query(True, description="Apenas templates ativos"),
    repo: PromptTemplateRepository = Depends(get_prompt_repo),
) -> PromptTemplateListResponse:
    """Lista todos os templates de prompts."""
    skip = (page - 1) * page_size
    templates, total = await repo.list_all(
        skip=skip, 
        limit=page_size,
        active_only=active_only,
    )
    
    return PromptTemplateListResponse(
        items=[PromptTemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/templates",
    response_model=PromptTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo template",
)
async def create_template(
    data: PromptTemplateCreate,
    repo: PromptTemplateRepository = Depends(get_prompt_repo),
) -> PromptTemplateResponse:
    """
    Cria um novo template de prompt.
    
    Se já existir um template com o mesmo nome, cria uma nova versão.
    """
    template = await repo.create(data)
    return PromptTemplateResponse.model_validate(template)


@router.get(
    "/templates/{template_id}",
    response_model=PromptTemplateResponse,
    summary="Busca template por ID",
)
async def get_template(
    template_id: UUID,
    repo: PromptTemplateRepository = Depends(get_prompt_repo),
) -> PromptTemplateResponse:
    """Busca um template específico pelo ID."""
    template = await repo.get_by_id(template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} não encontrado",
        )
    return PromptTemplateResponse.model_validate(template)


@router.get(
    "/templates/name/{name}",
    response_model=PromptTemplateResponse,
    summary="Busca template por nome",
)
async def get_template_by_name(
    name: str,
    version: Optional[int] = Query(None, description="Versão específica"),
    repo: PromptTemplateRepository = Depends(get_prompt_repo),
) -> PromptTemplateResponse:
    """Busca template pelo nome (retorna versão mais recente se não especificada)."""
    if version:
        template = await repo.get_by_name_and_version(name, version)
    else:
        template = await repo.get_latest_by_name(name)
    
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{name}' não encontrado",
        )
    return PromptTemplateResponse.model_validate(template)


@router.get(
    "/templates/{template_id}/versions",
    response_model=list[PromptTemplateResponse],
    summary="Lista versões de um template",
)
async def list_template_versions(
    template_id: UUID,
    repo: PromptTemplateRepository = Depends(get_prompt_repo),
) -> list[PromptTemplateResponse]:
    """Lista todas as versões de um template."""
    # Primeiro busca o template para pegar o nome
    template = await repo.get_by_id(template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} não encontrado",
        )
    
    versions = await repo.get_all_versions(template.name)
    return [PromptTemplateResponse.model_validate(v) for v in versions]


@router.patch(
    "/templates/{template_id}",
    response_model=PromptTemplateResponse,
    summary="Atualiza um template",
)
async def update_template(
    template_id: UUID,
    data: PromptTemplateUpdate,
    repo: PromptTemplateRepository = Depends(get_prompt_repo),
) -> PromptTemplateResponse:
    """Atualiza um template existente."""
    template = await repo.update(template_id, data)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} não encontrado",
        )
    return PromptTemplateResponse.model_validate(template)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desativa um template",
)
async def deactivate_template(
    template_id: UUID,
    repo: PromptTemplateRepository = Depends(get_prompt_repo),
) -> None:
    """Desativa um template (soft delete)."""
    success = await repo.deactivate(template_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} não encontrado",
        )

