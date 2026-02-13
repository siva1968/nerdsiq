"""Embedding service using OpenAI."""

import asyncio
from typing import List
from openai import AsyncOpenAI
from openai.types.create_embedding_response import CreateEmbeddingResponse
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import tiktoken

from app.config import settings


class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""

    def __init__(self) -> None:
        """Initialize embedding service with OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_embedding_model
        self.dimension = 1536  # text-embedding-3-small output dimension
        self.max_tokens_per_request = 300000  # OpenAI's limit
        self.max_batch_size = 2048  # OpenAI's limit for embeddings
        
        # Initialize tokenizer for counting tokens
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model)
        except KeyError:
            # Fallback for text-embedding-3-small
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

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
    
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text."""
        return len(self.tokenizer.encode(text))
    
    def estimate_batch_tokens(self, texts: List[str]) -> int:
        """Estimate total tokens for a batch of texts."""
        return sum(self.count_tokens(text) for text in texts)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((Exception,))
    )
    async def _create_embeddings_with_retry(self, texts: List[str]) -> CreateEmbeddingResponse:
        """Create embeddings with retry logic."""
        return await self.client.embeddings.create(
            model=self.model,
            input=texts,
        )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts with smart batching and rate limiting.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Split into smaller batches if needed
        all_embeddings = []
        current_batch = []
        current_tokens = 0
        
        for text in texts:
            text_tokens = self.count_tokens(text)
            
            # Skip texts that are too large
            if text_tokens > self.max_tokens_per_request:
                logger.warning(f"Skipping text with {text_tokens} tokens (exceeds limit)")
                all_embeddings.append([0.0] * self.dimension)  # Placeholder
                continue
            
            # Check if adding this text would exceed limits
            if (current_tokens + text_tokens > self.max_tokens_per_request or 
                len(current_batch) >= self.max_batch_size):
                
                # Process current batch
                if current_batch:
                    batch_embeddings = await self._process_batch(current_batch)
                    all_embeddings.extend(batch_embeddings)
                    
                    # Rate limiting delay between batches
                    await asyncio.sleep(0.1)
                
                # Start new batch
                current_batch = [text]
                current_tokens = text_tokens
            else:
                current_batch.append(text)
                current_tokens += text_tokens
        
        # Process final batch
        if current_batch:
            batch_embeddings = await self._process_batch(current_batch)
            all_embeddings.extend(batch_embeddings)
        
        logger.debug(f"Generated {len(all_embeddings)} embeddings in {len(texts)} input texts")
        return all_embeddings
    
    async def _process_batch(self, batch: List[str]) -> List[List[float]]:
        """Process a single batch of texts."""
        try:
            response = await self._create_embeddings_with_retry(batch)
            # Sort by index to maintain order
            return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        except Exception as e:
            logger.error(f"Failed to process batch of {len(batch)} texts: {e}")
            # Return zero vectors as fallback
            return [[0.0] * self.dimension for _ in batch]
