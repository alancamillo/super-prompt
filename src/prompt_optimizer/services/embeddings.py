"""Serviço de geração de embeddings."""

import hashlib
from typing import Optional

from openai import AsyncOpenAI

from ..core.config import get_settings

settings = get_settings()


class EmbeddingService:
    """
    Serviço para geração de embeddings.
    
    Pode usar OpenAI ou o vectorizer interno do Weaviate.
    Este serviço é útil para:
    - Gerar hashes de requisições para cache
    - Gerar embeddings customizados quando necessário
    """
    
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.model = settings.embedding_model
    
    def _get_client(self) -> AsyncOpenAI:
        """Retorna cliente OpenAI (lazy initialization)."""
        if self.client is None:
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY não configurada")
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self.client
    
    async def generate_embedding(self, text: str) -> list[float]:
        """
        Gera embedding para um texto usando OpenAI.
        
        Args:
            text: Texto para gerar embedding
            
        Returns:
            Vetor de embedding
        """
        client = self._get_client()
        
        response = await client.embeddings.create(
            model=self.model,
            input=text,
        )
        
        return response.data[0].embedding
    
    def generate_hash(self, text: str) -> str:
        """
        Gera hash determinístico para um texto.
        
        Útil para cache - textos idênticos terão o mesmo hash.
        
        Args:
            text: Texto para gerar hash
            
        Returns:
            Hash SHA-256 do texto normalizado
        """
        # Normaliza o texto (lowercase, remove espaços extras)
        normalized = " ".join(text.lower().split())
        
        # Gera hash SHA-256
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def generate_cache_key(
        self, 
        request_text: str, 
        template_name: Optional[str] = None
    ) -> str:
        """
        Gera chave de cache para uma requisição.
        
        Args:
            request_text: Texto da requisição
            template_name: Nome do template (opcional)
            
        Returns:
            Chave de cache
        """
        text_hash = self.generate_hash(request_text)
        
        if template_name:
            return f"{template_name}:{text_hash}"
        
        return text_hash


# Singleton
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Retorna instância do serviço de embeddings."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

