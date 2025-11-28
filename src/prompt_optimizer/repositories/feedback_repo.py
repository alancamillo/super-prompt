"""Repository para Feedback."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.db_models import Feedback, FeedbackType
from ..models.schemas import FeedbackCreate


class FeedbackRepository:
    """Repository para operações com Feedback."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self, 
        execution_id: UUID, 
        data: FeedbackCreate
    ) -> Feedback:
        """Cria um novo feedback."""
        feedback = Feedback(
            execution_id=execution_id,
            rating=data.rating,
            observation=data.observation,
            suggested_correction=data.suggested_correction,
            feedback_type=FeedbackType(data.feedback_type),
            created_by=data.created_by,
        )
        self.session.add(feedback)
        await self.session.flush()
        await self.session.refresh(feedback)
        return feedback
    
    async def get_by_id(self, feedback_id: UUID) -> Optional[Feedback]:
        """Busca feedback por ID."""
        result = await self.session.execute(
            select(Feedback).where(Feedback.id == feedback_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_execution(self, execution_id: UUID) -> list[Feedback]:
        """Busca todos os feedbacks de uma execução."""
        result = await self.session.execute(
            select(Feedback)
            .where(Feedback.execution_id == execution_id)
            .order_by(Feedback.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def list_by_type(
        self, 
        feedback_type: FeedbackType,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Feedback], int]:
        """Lista feedbacks por tipo."""
        query = (
            select(Feedback)
            .where(Feedback.feedback_type == feedback_type)
            .order_by(Feedback.created_at.desc())
        )
        
        # Count total
        count_result = await self.session.execute(
            select(func.count())
            .select_from(Feedback)
            .where(Feedback.feedback_type == feedback_type)
        )
        total = count_result.scalar() or 0
        
        # Paginate
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        
        return list(result.scalars().all()), total
    
    async def list_pending_review(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> tuple[list[Feedback], int]:
        """Lista feedbacks do tipo 'suggestion' para revisão."""
        return await self.list_by_type(
            FeedbackType.SUGGESTION, 
            skip=skip, 
            limit=limit
        )
    
    async def list_recent(
        self, 
        skip: int = 0, 
        limit: int = 100,
        days: int = 30
    ) -> tuple[list[Feedback], int]:
        """Lista feedbacks recentes."""
        since = datetime.utcnow() - timedelta(days=days)
        
        query = (
            select(Feedback)
            .where(Feedback.created_at >= since)
            .order_by(Feedback.created_at.desc())
        )
        
        # Count total
        count_result = await self.session.execute(
            select(func.count())
            .select_from(Feedback)
            .where(Feedback.created_at >= since)
        )
        total = count_result.scalar() or 0
        
        # Paginate
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        
        return list(result.scalars().all()), total
    
    async def get_summary(
        self, 
        days: int = 30
    ) -> dict:
        """Retorna resumo estatístico dos feedbacks."""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Total de feedbacks
        total_result = await self.session.execute(
            select(func.count())
            .select_from(Feedback)
            .where(Feedback.created_at >= since)
        )
        total = total_result.scalar() or 0
        
        # Média de rating
        avg_result = await self.session.execute(
            select(func.avg(Feedback.rating))
            .where(Feedback.created_at >= since)
            .where(Feedback.rating.isnot(None))
        )
        avg_rating = avg_result.scalar()
        
        # Contagem por tipo
        type_counts = {}
        for fb_type in FeedbackType:
            count_result = await self.session.execute(
                select(func.count())
                .select_from(Feedback)
                .where(Feedback.created_at >= since)
                .where(Feedback.feedback_type == fb_type)
            )
            type_counts[fb_type.value] = count_result.scalar() or 0
        
        return {
            "total_feedbacks": total,
            "average_rating": float(avg_rating) if avg_rating else None,
            "positive_count": type_counts.get("positive", 0),
            "negative_count": type_counts.get("negative", 0),
            "suggestion_count": type_counts.get("suggestion", 0),
            "pending_review": type_counts.get("suggestion", 0),  # suggestions são pendentes
        }

