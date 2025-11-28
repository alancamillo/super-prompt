"""Serviço principal de otimização de prompts."""

import re
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cache import CacheService
from ..models.db_models import PromptTemplate, OptimizationRequest
from ..models.schemas import OptimizePromptRequest, OptimizePromptResponse
from ..repositories.prompt_repo import PromptTemplateRepository
from ..repositories.optimization_repo import OptimizationRepository
from .similarity import SimilarityService
from .embeddings import EmbeddingService


class OptimizerService:
    """
    Serviço principal de otimização de prompts.
    
    Fluxo:
    1. Recebe requisição
    2. Gera hash e verifica cache
    3. Se cache miss, busca similaridade no Weaviate
    4. Se match, reutiliza prompt otimizado
    5. Se não, seleciona template e renderiza
    6. Salva no PostgreSQL e cacheia no Redis
    7. Indexa no Weaviate para futuras buscas
    """
    
    def __init__(
        self,
        session: AsyncSession,
        cache_service: CacheService,
        similarity_service: SimilarityService,
    ):
        self.session = session
        self.cache = cache_service
        self.similarity = similarity_service
        self.embedding_service = EmbeddingService()
        self.prompt_repo = PromptTemplateRepository(session)
        self.optimization_repo = OptimizationRepository(session)
    
    async def optimize(
        self, 
        request: OptimizePromptRequest
    ) -> OptimizePromptResponse:
        """
        Otimiza um prompt baseado na requisição.
        
        Args:
            request: Dados da requisição de otimização
            
        Returns:
            Prompt otimizado com metadados
        """
        # 1. Gera chave de cache
        cache_key = self.embedding_service.generate_cache_key(
            request.request,
            request.template_name,
        )
        
        # 2. Verifica cache
        cached = await self.cache.get_optimization_cache(cache_key)
        if cached:
            return OptimizePromptResponse(
                optimization_request_id=UUID(cached["optimization_request_id"]),
                prompt_rendered=cached["prompt_rendered"],
                template_id=UUID(cached["template_id"]) if cached.get("template_id") else None,
                template_name=cached.get("template_name"),
                template_version=cached.get("template_version"),
                was_cached=True,
                similarity_match=None,
            )
        
        # 3. Busca similaridade no Weaviate
        threshold = request.similarity_threshold
        similar_requests = await self.similarity.search_similar(
            request.request,
            limit=1,
            threshold=threshold,
        )
        
        matched_request_id = None
        similarity_score = None
        similarity_match = None
        
        if similar_requests:
            # Encontrou match de similaridade
            match = similar_requests[0]
            matched_request_id = UUID(match["optimization_id"])
            similarity_score = match["similarity_score"]
            similarity_match = {
                "matched_request_id": str(matched_request_id),
                "similarity_score": similarity_score,
                "matched_text": match["request_text"][:100] + "...",
            }
        
        # 4. Busca ou seleciona template
        template = await self._get_template(request.template_name)
        
        # 5. Renderiza prompt com variáveis
        prompt_rendered = self._render_prompt(
            template.content if template else request.request,
            request.variables,
        )
        
        # 6. Cria registro de otimização
        optimization = await self.optimization_repo.create(
            original_request=request.request,
            matched_request_id=matched_request_id,
            similarity_score=similarity_score,
            prompt_template_id=template.id if template else None,
        )
        
        # 7. Indexa no Weaviate
        weaviate_id = await self.similarity.index_request(
            request_text=request.request,
            optimization_id=optimization.id,
            prompt_template_name=template.name if template else None,
        )
        
        # Atualiza com ID do Weaviate
        await self.optimization_repo.update_weaviate_id(
            optimization.id, 
            weaviate_id
        )
        
        # 8. Cacheia resultado
        cache_data = {
            "optimization_request_id": str(optimization.id),
            "prompt_rendered": prompt_rendered,
            "template_id": str(template.id) if template else None,
            "template_name": template.name if template else None,
            "template_version": template.version if template else None,
        }
        await self.cache.set_optimization_cache(cache_key, cache_data)
        
        return OptimizePromptResponse(
            optimization_request_id=optimization.id,
            prompt_rendered=prompt_rendered,
            template_id=template.id if template else None,
            template_name=template.name if template else None,
            template_version=template.version if template else None,
            was_cached=False,
            similarity_match=similarity_match,
        )
    
    async def _get_template(
        self, 
        template_name: Optional[str]
    ) -> Optional[PromptTemplate]:
        """Busca template pelo nome."""
        if not template_name:
            return None
        
        return await self.prompt_repo.get_latest_by_name(template_name)
    
    def _render_prompt(
        self, 
        template_content: str, 
        variables: dict[str, str]
    ) -> str:
        """
        Renderiza template substituindo variáveis.
        
        Variáveis são no formato {{nome_variavel}}.
        
        Args:
            template_content: Conteúdo do template
            variables: Dicionário de variáveis para substituir
            
        Returns:
            Prompt renderizado
        """
        result = template_content
        
        for key, value in variables.items():
            # Suporta {{variavel}} e {{ variavel }}
            pattern = r'\{\{\s*' + re.escape(key) + r'\s*\}\}'
            result = re.sub(pattern, value, result)
        
        return result
    
    async def get_optimization_by_id(
        self, 
        optimization_id: UUID
    ) -> Optional[OptimizationRequest]:
        """Busca otimização por ID."""
        return await self.optimization_repo.get_by_id(optimization_id)
    
    async def invalidate_template_cache(self, template_name: str) -> int:
        """Invalida cache de todas as otimizações de um template."""
        return await self.cache.invalidate_template_cache(template_name)

