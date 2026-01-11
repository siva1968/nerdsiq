"""Embedding service using OpenAI."""

from openai import AsyncOpenAI
from loguru import logger

from app.config import settings


class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""

    def __init__(self) -> None:
        """Initialize embedding service with OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_embedding_model
        self.dimension = 1536  # text-embedding-3-small output dimension

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector (1536 dimensions)
        """
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        
        embedding = response.data[0].embedding
        logger.debug(f"Generated embedding for text: {text[:50]}...")
        
        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        
        # Sort by index to maintain order
        embeddings = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        logger.debug(f"Generated {len(embeddings)} embeddings in batch")
        
        return embeddings
