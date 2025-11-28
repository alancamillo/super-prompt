"""Serviço de busca por similaridade usando Weaviate."""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery

from ..core.config import get_settings

settings = get_settings()


class SimilarityService:
    """
    Serviço para busca vetorial e similaridade usando Weaviate.
    
    Suporta dois modos de embeddings:
    1. LM Studio local (padrão) - usa text2vec-openai apontando para LM Studio
    2. OpenAI API - usa text2vec-openai com API da OpenAI
    """
    
    COLLECTION_NAME = "PromptRequest"
    
    def __init__(self):
        self.client: Optional[weaviate.WeaviateClient] = None
    
    async def connect(self) -> None:
        """Conecta ao Weaviate."""
        if self.client is None:
            self.client = weaviate.connect_to_custom(
                http_host=settings.weaviate_url.replace("http://", "").split(":")[0],
                http_port=int(settings.weaviate_url.split(":")[-1]),
                http_secure=False,
                grpc_host=settings.weaviate_url.replace("http://", "").split(":")[0],
                grpc_port=50051,
                grpc_secure=False,
            )
    
    async def close(self) -> None:
        """Fecha conexão com Weaviate."""
        if self.client is not None:
            self.client.close()
            self.client = None
    
    def _get_vectorizer_config(self) -> Configure.Vectorizer:
        """
        Retorna configuração do vectorizer baseado nas settings.
        
        Se use_local_embeddings=True, usa LM Studio local.
        Caso contrário, usa OpenAI API.
        """
        if settings.use_local_embeddings:
            # LM Studio local - API compatível com OpenAI
            return Configure.Vectorizer.text2vec_openai(
                model=settings.lmstudio_embedding_model,
                base_url=settings.lmstudio_base_url,
            )
        else:
            # OpenAI API
            return Configure.Vectorizer.text2vec_openai(
                model=settings.embedding_model,
            )
    
    async def ensure_schema(self) -> None:
        """Garante que o schema existe no Weaviate."""
        await self.connect()
        
        if not self.client.collections.exists(self.COLLECTION_NAME):
            self.client.collections.create(
                name=self.COLLECTION_NAME,
                vectorizer_config=self._get_vectorizer_config(),
                properties=[
                    Property(
                        name="request_text",
                        data_type=DataType.TEXT,
                        description="Texto original da requisição",
                        skip_vectorization=False,
                    ),
                    Property(
                        name="optimization_id",
                        data_type=DataType.TEXT,
                        description="UUID da optimization_request no PostgreSQL",
                        skip_vectorization=True,
                    ),
                    Property(
                        name="prompt_template_name",
                        data_type=DataType.TEXT,
                        description="Nome do template de prompt associado",
                        skip_vectorization=True,
                    ),
                    Property(
                        name="created_at",
                        data_type=DataType.DATE,
                        description="Data de criação",
                    ),
                ],
            )
    
    async def index_request(
        self,
        request_text: str,
        optimization_id: UUID,
        prompt_template_name: Optional[str] = None,
    ) -> str:
        """
        Indexa uma requisição no Weaviate.
        
        Args:
            request_text: Texto da requisição
            optimization_id: ID da optimization_request no PostgreSQL
            prompt_template_name: Nome do template associado
            
        Returns:
            ID do objeto no Weaviate
        """
        await self.connect()
        collection = self.client.collections.get(self.COLLECTION_NAME)
        
        result = collection.data.insert(
            properties={
                "request_text": request_text,
                "optimization_id": str(optimization_id),
                "prompt_template_name": prompt_template_name or "",
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        
        return str(result)
    
    async def search_similar(
        self,
        request_text: str,
        limit: int = 5,
        threshold: Optional[float] = None,
    ) -> list[dict]:
        """
        Busca requisições similares.
        
        Args:
            request_text: Texto para buscar similaridade
            limit: Número máximo de resultados
            threshold: Score mínimo de similaridade (0.0 a 1.0)
            
        Returns:
            Lista de resultados com similarity_score e dados
        """
        await self.connect()
        collection = self.client.collections.get(self.COLLECTION_NAME)
        
        threshold = threshold or settings.similarity_threshold
        
        # Busca por similaridade textual
        results = collection.query.near_text(
            query=request_text,
            limit=limit,
            return_metadata=MetadataQuery(distance=True),
        )
        
        similar_requests = []
        for obj in results.objects:
            # Weaviate retorna distance (menor = mais similar)
            # Convertemos para score (maior = mais similar)
            distance = obj.metadata.distance or 1.0
            similarity_score = 1.0 - distance
            
            if similarity_score >= threshold:
                similar_requests.append({
                    "weaviate_id": str(obj.uuid),
                    "request_text": obj.properties.get("request_text"),
                    "optimization_id": obj.properties.get("optimization_id"),
                    "prompt_template_name": obj.properties.get("prompt_template_name"),
                    "similarity_score": similarity_score,
                })
        
        return similar_requests
    
    async def get_by_id(self, weaviate_id: str) -> Optional[dict]:
        """Busca objeto por ID no Weaviate."""
        await self.connect()
        collection = self.client.collections.get(self.COLLECTION_NAME)
        
        try:
            obj = collection.query.fetch_object_by_id(weaviate_id)
            if obj:
                return {
                    "weaviate_id": str(obj.uuid),
                    "request_text": obj.properties.get("request_text"),
                    "optimization_id": obj.properties.get("optimization_id"),
                    "prompt_template_name": obj.properties.get("prompt_template_name"),
                }
        except Exception:
            return None
        
        return None
    
    async def delete_by_optimization_id(self, optimization_id: UUID) -> bool:
        """Remove objeto do Weaviate pelo optimization_id."""
        await self.connect()
        collection = self.client.collections.get(self.COLLECTION_NAME)
        
        # Busca o objeto pelo optimization_id
        results = collection.query.fetch_objects(
            filters=weaviate.classes.query.Filter.by_property("optimization_id").equal(str(optimization_id)),
            limit=1,
        )
        
        if results.objects:
            collection.data.delete_by_id(results.objects[0].uuid)
            return True
        
        return False


# Singleton para o serviço
_similarity_service: Optional[SimilarityService] = None


async def get_similarity_service() -> SimilarityService:
    """Retorna instância do serviço de similaridade."""
    global _similarity_service
    if _similarity_service is None:
        _similarity_service = SimilarityService()
        await _similarity_service.ensure_schema()
    return _similarity_service


async def close_similarity_service() -> None:
    """Fecha o serviço de similaridade."""
    global _similarity_service
    if _similarity_service is not None:
        await _similarity_service.close()
        _similarity_service = None

