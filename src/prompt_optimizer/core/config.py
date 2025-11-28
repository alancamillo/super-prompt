"""Configurações centralizadas do Prompt Optimizer."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente."""
    
    # Aplicação
    app_name: str = "Prompt Optimizer"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # PostgreSQL
    database_url: str = "postgresql+asyncpg://prompt_optimizer:prompt_optimizer_secret@localhost:5432/prompt_optimizer"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600  # 1 hora
    
    # Weaviate
    weaviate_url: str = "http://localhost:8080"
    weaviate_api_key: Optional[str] = None
    similarity_threshold: float = 0.85  # 85% de similaridade para considerar match
    
    # LM Studio - Embeddings locais (API OpenAI-compatible)
    # URL do LM Studio local para geração de embeddings
    lmstudio_base_url: str = "http://localhost:1234/v1"
    # Modelo de embeddings no LM Studio (ex: nomic-embed-text-v1.5, bge-small-en-v1.5)
    lmstudio_embedding_model: str = "nomic-embed-text-v1.5"
    
    # OpenAI (fallback ou alternativa)
    openai_api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-small"
    
    # Usar LM Studio para embeddings (True) ou OpenAI (False)
    use_local_embeddings: bool = True
    
    # API
    api_prefix: str = "/api/v1"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Retorna instância cacheada das configurações."""
    return Settings()

