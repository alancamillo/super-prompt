"""Configuração do cache Redis."""

import json
from typing import Any, Optional

import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_settings

settings = get_settings()

# Pool de conexões Redis
redis_pool: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Retorna conexão Redis do pool."""
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_pool


async def close_redis() -> None:
    """Fecha conexão Redis."""
    global redis_pool
    if redis_pool is not None:
        await redis_pool.close()
        redis_pool = None


class CacheService:
    """Serviço de cache para prompts otimizados."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = settings.cache_ttl_seconds
        self.prefix = "prompt_optimizer:"
    
    def _make_key(self, key: str) -> str:
        """Cria chave com prefixo."""
        return f"{self.prefix}{key}"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get(self, key: str) -> Optional[dict]:
        """Busca valor do cache."""
        cached = await self.redis.get(self._make_key(key))
        if cached:
            return json.loads(cached)
        return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def set(self, key: str, value: dict, ttl: Optional[int] = None) -> bool:
        """Armazena valor no cache."""
        return await self.redis.set(
            self._make_key(key),
            json.dumps(value),
            ex=ttl or self.ttl,
        )
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def delete(self, key: str) -> bool:
        """Remove valor do cache."""
        return await self.redis.delete(self._make_key(key)) > 0
    
    async def get_optimization_cache(self, request_hash: str) -> Optional[dict]:
        """Busca otimização cacheada por hash da requisição."""
        return await self.get(f"optimization:{request_hash}")
    
    async def set_optimization_cache(
        self, 
        request_hash: str, 
        optimization_data: dict,
        ttl: Optional[int] = None
    ) -> bool:
        """Cacheia resultado de otimização."""
        return await self.set(f"optimization:{request_hash}", optimization_data, ttl)
    
    async def invalidate_template_cache(self, template_name: str) -> int:
        """Invalida cache de todas as otimizações de um template."""
        pattern = self._make_key(f"optimization:*:{template_name}:*")
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            return await self.redis.delete(*keys)
        return 0


async def get_cache_service() -> CacheService:
    """Dependency para injetar serviço de cache."""
    redis_client = await get_redis()
    return CacheService(redis_client)

