"""Repository para OptimizationRequest."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.db_models import OptimizationRequest
from ..models.schemas import OptimizationRequestCreate


class OptimizationRepository:
    """Repository para operações com OptimizationRequest."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        original_request: str,
        weaviate_vector_id: Optional[str] = None,
        matched_request_id: Optional[UUID] = None,
        similarity_score: Optional[float] = None,
        prompt_template_id: Optional[UUID] = None,
    ) -> OptimizationRequest:
        """Cria um novo registro de requisição de otimização."""
        request = OptimizationRequest(
            original_request=original_request,
            weaviate_vector_id=weaviate_vector_id,
            matched_request_id=matched_request_id,
            similarity_score=similarity_score,
            prompt_template_id=prompt_template_id,
        )
        self.session.add(request)
        await self.session.flush()
        await self.session.refresh(request)
        return request
    
    async def get_by_id(self, request_id: UUID) -> Optional[OptimizationRequest]:
        """Busca requisição por ID."""
        result = await self.session.execute(
            select(OptimizationRequest)
            .where(OptimizationRequest.id == request_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_weaviate_id(
        self, 
        weaviate_vector_id: str
    ) -> Optional[OptimizationRequest]:
        """Busca requisição por ID do vetor no Weaviate."""
        result = await self.session.execute(
            select(OptimizationRequest)
            .where(OptimizationRequest.weaviate_vector_id == weaviate_vector_id)
        )
        return result.scalar_one_or_none()
    
    async def update_weaviate_id(
        self, 
        request_id: UUID, 
        weaviate_vector_id: str
    ) -> Optional[OptimizationRequest]:
        """Atualiza o ID do vetor no Weaviate."""
        request = await self.get_by_id(request_id)
        if request is None:
            return None
        
        request.weaviate_vector_id = weaviate_vector_id
        await self.session.flush()
        await self.session.refresh(request)
        return request
    
    async def list_recent(
        self, 
        skip: int = 0, 
        limit: int = 100,
        days: int = 30
    ) -> tuple[list[OptimizationRequest], int]:
        """Lista requisições recentes."""
        since = datetime.utcnow() - timedelta(days=days)
        
        query = (
            select(OptimizationRequest)
            .where(OptimizationRequest.created_at >= since)
            .order_by(OptimizationRequest.created_at.desc())
        )
        
        # Count total
        count_result = await self.session.execute(
            select(func.count())
            .select_from(OptimizationRequest)
            .where(OptimizationRequest.created_at >= since)
        )
        total = count_result.scalar() or 0
        
        # Paginate
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        
        return list(result.scalars().all()), total
    
    async def count_similarity_matches(
        self, 
        days: int = 30
    ) -> tuple[int, int, float]:
        """
        Conta matches de similaridade.
        Retorna: (total_requests, similarity_matches, average_score)
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        # Total de requisições
        total_result = await self.session.execute(
            select(func.count())
            .select_from(OptimizationRequest)
            .where(OptimizationRequest.created_at >= since)
        )
        total = total_result.scalar() or 0
        
        # Requisições com match
        match_result = await self.session.execute(
            select(func.count())
            .select_from(OptimizationRequest)
            .where(OptimizationRequest.created_at >= since)
            .where(OptimizationRequest.matched_request_id.isnot(None))
        )
        matches = match_result.scalar() or 0
        
        # Score médio
        avg_result = await self.session.execute(
            select(func.avg(OptimizationRequest.similarity_score))
            .where(OptimizationRequest.created_at >= since)
            .where(OptimizationRequest.similarity_score.isnot(None))
        )
        avg_score = avg_result.scalar() or 0.0
        
        return total, matches, float(avg_score)

