#!/usr/bin/env python
"""Index documents from Google Drive into Qdrant."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tiktoken
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from loguru import logger

from app.config import settings
from app.services.drive_service import DriveService
from app.services.embedding_service import EmbeddingService


# Chunking configuration
CHUNK_SIZE = 500      # tokens
CHUNK_OVERLAP = 50    # tokens


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks by token count.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum tokens per chunk
        overlap: Number of overlapping tokens between chunks
        
    Returns:
        List of text chunks
    """
    # Use tiktoken for accurate token counting
    encoder = tiktoken.encoding_for_model("gpt-4o-mini")
    tokens = encoder.encode(text)
    
    chunks = []
    start = 0
    
    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = encoder.decode(chunk_tokens)
        chunks.append(chunk_text)
        
        # Move start with overlap
        start = end - overlap
        
        if start >= len(tokens):
            break
    
    return chunks


async def index_documents() -> None:
    """Index all documents from Google Drive into Qdrant."""
    logger.info("Starting document indexing...")
    
    # Initialize services
    drive = DriveService()
    embedding_service = EmbeddingService()
    
    # Initialize Qdrant
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    
    # Create collection if it doesn't exist
    collections = [c.name for c in qdrant.get_collections().collections]
    
    if settings.qdrant_collection not in collections:
        qdrant.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=1536,  # text-embedding-3-small dimension
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Created Qdrant collection: {settings.qdrant_collection}")
    else:
        # Clear existing points for re-indexing
        qdrant.delete_collection(settings.qdrant_collection)
        qdrant.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=1536,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Recreated Qdrant collection: {settings.qdrant_collection}")
    
    # Get files from Google Drive
    files = drive.list_files()
    
    if not files:
        logger.warning("No files found in Google Drive folder!")
        return
    
    total_chunks = 0
    point_id = 0
    
    for file_info in files:
        file_id = file_info["id"]
        file_name = file_info["name"]
        web_url = file_info.get("webViewLink", drive.get_file_url(file_id))
        
        logger.info(f"Processing: {file_name}")
        
        try:
            # Get file content
            content = drive.get_file_content(file_id)
            
            if not content.strip():
                logger.warning(f"  Skipping empty file: {file_name}")
                continue
            
            # Chunk the content
            chunks = chunk_text(content)
            logger.info(f"  Created {len(chunks)} chunks")
            
            # Generate embeddings in batch
            embeddings = await embedding_service.embed_batch(chunks)
            
            # Create points for Qdrant
            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                point_id += 1
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "text": chunk,
                            "source_id": file_id,
                            "source_name": file_name,
                            "source_url": web_url,
                            "chunk_index": i,
                        },
                    )
                )
            
            # Upsert to Qdrant
            qdrant.upsert(
                collection_name=settings.qdrant_collection,
                points=points,
            )
            
            total_chunks += len(chunks)
            logger.info(f"  Indexed {len(chunks)} chunks for {file_name}")
            
        except Exception as e:
            logger.error(f"  Error processing {file_name}: {e}")
            continue
    
    logger.info(f"✅ Indexing complete! Total chunks: {total_chunks}")


def main() -> None:
    """Run the indexing script."""
    asyncio.run(index_documents())


if __name__ == "__main__":
    main()
