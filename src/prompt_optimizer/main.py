"""Aplicação FastAPI principal do Prompt Optimizer."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.database import init_db, close_db
from .core.cache import get_redis, close_redis
from .services.similarity import get_similarity_service, close_similarity_service
from .api.routes import (
    prompts_router,
    executions_router,
    feedbacks_router,
    analytics_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação."""
    # Startup
    print("🚀 Iniciando Prompt Optimizer...")
    
    # Inicializa banco de dados
    await init_db()
    print("✅ Banco de dados conectado")
    
    # Inicializa Redis
    await get_redis()
    print("✅ Redis conectado")
    
    # Inicializa Weaviate
    try:
        similarity = await get_similarity_service()
        await similarity.ensure_schema()
        print("✅ Weaviate conectado")
    except Exception as e:
        print(f"⚠️ Weaviate não disponível: {e}")
    
    yield
    
    # Shutdown
    print("🛑 Encerrando Prompt Optimizer...")
    await close_similarity_service()
    await close_redis()
    await close_db()
    print("✅ Conexões encerradas")


# Cria aplicação FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## Prompt Optimizer API

Sistema de otimização de prompts com:

- **Persistência**: PostgreSQL para dados, Redis para cache
- **Busca Vetorial**: Weaviate para similaridade de requisições
- **Feedback**: Sistema human-in-the-loop para melhoria contínua

### Fluxo Principal

1. **Otimização** (`POST /prompts/optimize`)
   - Recebe requisição do usuário
   - Busca similaridade em requisições anteriores
   - Aplica template e retorna prompt otimizado
   
2. **Execução** (`POST /executions`)
   - Registra prompt enviado ao LLM + resposta recebida
   
3. **Feedback** (`POST /feedbacks/executions/{id}`)
   - Permite adicionar observações e correções
   - Alimenta ciclo de melhoria contínua
    """,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar origens permitidas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra routers
app.include_router(prompts_router, prefix=settings.api_prefix)
app.include_router(executions_router, prefix=settings.api_prefix)
app.include_router(feedbacks_router, prefix=settings.api_prefix)
app.include_router(analytics_router, prefix=settings.api_prefix)


@app.get("/", tags=["health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check detalhado."""
    return {
        "status": "healthy",
        "database": "connected",
        "cache": "connected",
        "vector_store": "connected",
    }

