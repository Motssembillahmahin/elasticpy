from sentence_transformers import SentenceTransformer
from typing import List
import logging

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMS = 384


class EmbeddingService:
    """Singleton sentence-transformer embedding service.

    Lazy-loads the model on first use so startup time is unaffected
    when semantic search is not called.
    """

    _model: SentenceTransformer | None = None

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            cls._model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("Embedding model loaded")
        return cls._model

    @classmethod
    def embed(cls, text: str) -> List[float]:
        """Embed a single string, returns a normalised 384-dim vector."""
        return cls.get_model().encode(text, normalize_embeddings=True).tolist()

    @classmethod
    def embed_batch(cls, texts: List[str]) -> List[List[float]]:
        """Embed a list of strings in one forward pass."""
        return cls.get_model().encode(texts, normalize_embeddings=True).tolist()
