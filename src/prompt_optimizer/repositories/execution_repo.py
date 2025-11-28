"""Repository para PromptExecution."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.db_models import PromptExecution
from ..models.schemas import PromptExecutionCreate, PromptExecutionUpdate


class ExecutionRepository:
    """Repository para operações com PromptExecution."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, data: PromptExecutionCreate) -> PromptExecution:
        """Cria um novo registro de execução."""
        execution = PromptExecution(
            optimization_request_id=data.optimization_request_id,
            prompt_template_id=data.prompt_template_id,
            prompt_rendered=data.prompt_rendered,
            llm_response=data.llm_response,
            llm_model=data.llm_model,
            tokens_input=data.tokens_input,
            tokens_output=data.tokens_output,
            latency_ms=data.latency_ms,
        )
        self.session.add(execution)
        await self.session.flush()
        await self.session.refresh(execution)
        return execution
    
    async def get_by_id(
        self, 
        execution_id: UUID,
        include_feedbacks: bool = False
    ) -> Optional[PromptExecution]:
        """Busca execução por ID."""
        query = select(PromptExecution).where(PromptExecution.id == execution_id)
        
        if include_feedbacks:
            query = query.options(selectinload(PromptExecution.feedbacks))
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_optimization_request(
        self, 
        optimization_request_id: UUID
    ) -> list[PromptExecution]:
        """Busca execuções por requisição de otimização."""
        result = await self.session.execute(
            select(PromptExecution)
            .where(PromptExecution.optimization_request_id == optimization_request_id)
            .order_by(PromptExecution.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def update(
        self, 
        execution_id: UUID, 
        data: PromptExecutionUpdate
    ) -> Optional[PromptExecution]:
        """Atualiza uma execução existente."""
        execution = await self.get_by_id(execution_id)
        if execution is None:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(execution, field, value)
        
        await self.session.flush()
        await self.session.refresh(execution)
        return execution
    
    async def list_recent(
        self, 
        skip: int = 0, 
        limit: int = 100,
        days: int = 30
    ) -> tuple[list[PromptExecution], int]:
        """Lista execuções recentes."""
        since = datetime.utcnow() - timedelta(days=days)
        
        query = (
            select(PromptExecution)
            .where(PromptExecution.created_at >= since)
            .order_by(PromptExecution.created_at.desc())
        )
        
        # Count total
        count_result = await self.session.execute(
            select(func.count())
            .select_from(PromptExecution)
            .where(PromptExecution.created_at >= since)
        )
        total = count_result.scalar() or 0
        
        # Paginate
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        
        return list(result.scalars().all()), total
    
    async def list_without_feedback(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> tuple[list[PromptExecution], int]:
        """Lista execuções que ainda não têm feedback."""
        from ..models.db_models import Feedback
        
        # Subquery para execuções com feedback
        subquery = (
            select(Feedback.execution_id)
            .distinct()
            .subquery()
        )
        
        query = (
            select(PromptExecution)
            .where(PromptExecution.id.notin_(select(subquery)))
            .order_by(PromptExecution.created_at.desc())
        )
        
        # Count total
        count_result = await self.session.execute(
            select(func.count())
            .select_from(query.subquery())
        )
        total = count_result.scalar() or 0
        
        # Paginate
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        
        return list(result.scalars().all()), total
    
    async def get_token_stats(
        self, 
        days: int = 30
    ) -> tuple[int, int, int]:
        """
        Retorna estatísticas de tokens.
        Returns: (total_executions, total_input_tokens, total_output_tokens)
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        result = await self.session.execute(
            select(
                func.count(PromptExecution.id),
                func.sum(PromptExecution.tokens_input),
                func.sum(PromptExecution.tokens_output),
            )
            .where(PromptExecution.created_at >= since)
        )
        row = result.one()
        return (
            row[0] or 0,
            row[1] or 0,
            row[2] or 0,
        )

