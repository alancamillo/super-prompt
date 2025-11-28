"""Modelos SQLAlchemy para o banco de dados PostgreSQL."""

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class FeedbackType(enum.Enum):
    """Tipos de feedback."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    SUGGESTION = "suggestion"


class PromptTemplate(Base):
    """
    Template de prompt com versionamento.
    
    Armazena templates de prompts que podem ter múltiplas versões,
    permitindo evolução controlada dos prompts.
    """
    __tablename__ = "prompt_templates"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", 
        JSONB, 
        nullable=False, 
        default=dict
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    optimization_requests: Mapped[list["OptimizationRequest"]] = relationship(
        back_populates="prompt_template"
    )
    executions: Mapped[list["PromptExecution"]] = relationship(
        back_populates="prompt_template"
    )
    
    def __repr__(self) -> str:
        return f"<PromptTemplate(name='{self.name}', version={self.version})>"


class OptimizationRequest(Base):
    """
    Registro de requisição de otimização.
    
    Registra cada requisição de otimização recebida, permitindo rastrear
    o que foi pedido e se houve reuso de otimização similar.
    """
    __tablename__ = "optimization_requests"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    original_request: Mapped[str] = mapped_column(Text, nullable=False)
    weaviate_vector_id: Mapped[Optional[str]] = mapped_column(String(255))
    matched_request_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("optimization_requests.id"),
        nullable=True
    )
    similarity_score: Mapped[Optional[float]] = mapped_column(Float)
    prompt_template_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_templates.id"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        index=True
    )
    
    # Relationships
    prompt_template: Mapped[Optional["PromptTemplate"]] = relationship(
        back_populates="optimization_requests"
    )
    matched_request: Mapped[Optional["OptimizationRequest"]] = relationship(
        remote_side=[id]
    )
    executions: Mapped[list["PromptExecution"]] = relationship(
        back_populates="optimization_request"
    )
    
    def __repr__(self) -> str:
        return f"<OptimizationRequest(id='{self.id}', similarity={self.similarity_score})>"


class PromptExecution(Base):
    """
    Registro de execução de prompt.
    
    Registra a execução real do prompt - o prompt final enviado ao LLM
    e a resposta recebida. Essencial para o ciclo de feedback.
    """
    __tablename__ = "prompt_executions"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    optimization_request_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("optimization_requests.id"),
        nullable=True
    )
    prompt_template_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_templates.id"),
        nullable=True
    )
    prompt_rendered: Mapped[str] = mapped_column(Text, nullable=False)
    llm_response: Mapped[Optional[str]] = mapped_column(Text)
    llm_model: Mapped[Optional[str]] = mapped_column(String(100))
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Relationships
    optimization_request: Mapped[Optional["OptimizationRequest"]] = relationship(
        back_populates="executions"
    )
    prompt_template: Mapped[Optional["PromptTemplate"]] = relationship(
        back_populates="executions"
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(
        back_populates="execution"
    )
    
    def __repr__(self) -> str:
        return f"<PromptExecution(id='{self.id}', model='{self.llm_model}')>"


class Feedback(Base):
    """
    Feedback humano sobre respostas.
    
    Armazena feedback humano sobre as respostas do LLM,
    permitindo "ensinar" o sistema sobre o que funcionou ou não.
    """
    __tablename__ = "feedbacks"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    execution_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_executions.id"),
        nullable=False,
        index=True
    )
    rating: Mapped[Optional[int]] = mapped_column(Integer)
    observation: Mapped[Optional[str]] = mapped_column(Text)
    suggested_correction: Mapped[Optional[str]] = mapped_column(Text)
    feedback_type: Mapped[FeedbackType] = mapped_column(
        Enum(FeedbackType, name="feedback_type"),
        nullable=False,
        default=FeedbackType.SUGGESTION,
        index=True
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Relationships
    execution: Mapped["PromptExecution"] = relationship(
        back_populates="feedbacks"
    )
    
    def __repr__(self) -> str:
        return f"<Feedback(id='{self.id}', type='{self.feedback_type.value}', rating={self.rating})>"

