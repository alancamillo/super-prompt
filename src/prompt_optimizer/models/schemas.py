"""Schemas Pydantic para validação e serialização de dados."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Prompt Templates
# =============================================================================

class PromptTemplateBase(BaseModel):
    """Base schema para PromptTemplate."""
    name: str = Field(..., min_length=1, max_length=255, description="Nome identificador do prompt")
    content: str = Field(..., min_length=1, description="Conteúdo do prompt com placeholders {{variavel}}")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais")


class PromptTemplateCreate(PromptTemplateBase):
    """Schema para criação de PromptTemplate."""
    pass


class PromptTemplateUpdate(BaseModel):
    """Schema para atualização de PromptTemplate."""
    content: Optional[str] = Field(None, min_length=1, description="Novo conteúdo do prompt")
    metadata: Optional[dict[str, Any]] = Field(None, description="Novos metadados")
    is_active: Optional[bool] = Field(None, description="Se a versão está ativa")


class PromptTemplateResponse(PromptTemplateBase):
    """Schema de resposta para PromptTemplate."""
    id: UUID
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class PromptTemplateListResponse(BaseModel):
    """Schema de resposta para lista de PromptTemplates."""
    items: list[PromptTemplateResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Optimization Requests
# =============================================================================

class OptimizationRequestCreate(BaseModel):
    """Schema para criação de OptimizationRequest."""
    original_request: str = Field(..., min_length=1, description="Texto original da requisição")
    prompt_template_name: Optional[str] = Field(None, description="Nome do template a usar")


class OptimizationRequestResponse(BaseModel):
    """Schema de resposta para OptimizationRequest."""
    id: UUID
    original_request: str
    weaviate_vector_id: Optional[str] = None
    matched_request_id: Optional[UUID] = None
    similarity_score: Optional[float] = None
    prompt_template_id: Optional[UUID] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class OptimizePromptRequest(BaseModel):
    """Schema para requisição de otimização de prompt."""
    request: str = Field(..., min_length=1, description="Texto da requisição a otimizar")
    template_name: Optional[str] = Field(None, description="Nome do template específico")
    variables: dict[str, str] = Field(default_factory=dict, description="Variáveis para substituição")
    similarity_threshold: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="Threshold de similaridade (0.0 a 1.0)"
    )


class OptimizePromptResponse(BaseModel):
    """Schema de resposta para otimização de prompt."""
    optimization_request_id: UUID
    prompt_rendered: str
    template_id: Optional[UUID] = None
    template_name: Optional[str] = None
    template_version: Optional[int] = None
    was_cached: bool = False
    similarity_match: Optional[dict] = None


# =============================================================================
# Prompt Executions
# =============================================================================

class PromptExecutionCreate(BaseModel):
    """Schema para criação de PromptExecution."""
    optimization_request_id: Optional[UUID] = Field(None, description="ID da requisição de otimização")
    prompt_template_id: Optional[UUID] = Field(None, description="ID do template usado")
    prompt_rendered: str = Field(..., min_length=1, description="Prompt final renderizado")
    llm_response: Optional[str] = Field(None, description="Resposta do LLM")
    llm_model: Optional[str] = Field(None, description="Modelo LLM usado")
    tokens_input: int = Field(0, ge=0, description="Tokens de entrada")
    tokens_output: int = Field(0, ge=0, description="Tokens de saída")
    latency_ms: int = Field(0, ge=0, description="Latência em milissegundos")


class PromptExecutionUpdate(BaseModel):
    """Schema para atualização de PromptExecution."""
    llm_response: Optional[str] = Field(None, description="Resposta do LLM")
    llm_model: Optional[str] = Field(None, description="Modelo LLM usado")
    tokens_input: Optional[int] = Field(None, ge=0, description="Tokens de entrada")
    tokens_output: Optional[int] = Field(None, ge=0, description="Tokens de saída")
    latency_ms: Optional[int] = Field(None, ge=0, description="Latência em milissegundos")


class PromptExecutionResponse(BaseModel):
    """Schema de resposta para PromptExecution."""
    id: UUID
    optimization_request_id: Optional[UUID] = None
    prompt_template_id: Optional[UUID] = None
    prompt_rendered: str
    llm_response: Optional[str] = None
    llm_model: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: int = 0
    created_at: datetime
    
    model_config = {"from_attributes": True}


# =============================================================================
# Feedbacks
# =============================================================================

class FeedbackCreate(BaseModel):
    """Schema para criação de Feedback."""
    rating: Optional[int] = Field(None, ge=1, le=5, description="Nota de 1 a 5")
    observation: Optional[str] = Field(None, description="Observação sobre o problema ou acerto")
    suggested_correction: Optional[str] = Field(None, description="Sugestão de correção")
    feedback_type: str = Field("suggestion", description="Tipo: positive, negative, suggestion")
    created_by: Optional[str] = Field(None, max_length=255, description="Identificador do revisor")
    
    @field_validator("feedback_type")
    @classmethod
    def validate_feedback_type(cls, v: str) -> str:
        allowed = {"positive", "negative", "suggestion"}
        if v not in allowed:
            raise ValueError(f"feedback_type deve ser um de: {allowed}")
        return v


class FeedbackResponse(BaseModel):
    """Schema de resposta para Feedback."""
    id: UUID
    execution_id: UUID
    rating: Optional[int] = None
    observation: Optional[str] = None
    suggested_correction: Optional[str] = None
    feedback_type: str
    created_by: Optional[str] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}
    
    @field_validator("feedback_type", mode="before")
    @classmethod
    def convert_enum_to_str(cls, v):
        if hasattr(v, "value"):
            return v.value
        return v


class FeedbackListResponse(BaseModel):
    """Schema de resposta para lista de Feedbacks."""
    items: list[FeedbackResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Analytics
# =============================================================================

class TokenSavingsResponse(BaseModel):
    """Resposta de economia de tokens."""
    total_requests: int
    cached_hits: int
    cache_hit_rate: float
    estimated_tokens_saved: int
    period_start: datetime
    period_end: datetime


class SimilarityHitsResponse(BaseModel):
    """Resposta de hits de similaridade."""
    total_requests: int
    similarity_matches: int
    match_rate: float
    average_similarity_score: float
    period_start: datetime
    period_end: datetime


class FeedbackSummaryResponse(BaseModel):
    """Resposta de resumo de feedbacks."""
    total_feedbacks: int
    average_rating: Optional[float]
    positive_count: int
    negative_count: int
    suggestion_count: int
    pending_review: int

