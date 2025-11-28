"""Services - lógica de negócio."""

from .similarity import SimilarityService
from .embeddings import EmbeddingService
from .optimizer import OptimizerService

__all__ = [
    "SimilarityService",
    "EmbeddingService",
    "OptimizerService",
]

