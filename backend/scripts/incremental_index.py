#!/usr/bin/env python3
"""Simple incremental document indexing script."""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, Distance, VectorParams
from loguru import logger

from app.config import settings
from app.services.drive_service import DriveService
from app.services.embedding_service import EmbeddingService


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Chunk text into overlapping segments."""
    import tiktoken
    
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    
    if len(tokens) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text.strip())
        
        if end >= len(tokens):
            break
            
        start = end - overlap
        if start >= len(tokens):
            break
    
    return chunks


async def simple_incremental_index():
    """Simple incremental indexing that doesn't recreate collection."""
    logger.info("🔄 Starting simple incremental indexing...")
    
    # Initialize services
    drive = DriveService()
    embedding_service = EmbeddingService()
    
    # Connect to existing Qdrant
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    
    # Check collection exists
    collections = [c.name for c in qdrant.get_collections().collections]
    if settings.qdrant_collection not in collections:
        logger.error(f"❌ Collection {settings.qdrant_collection} not found!")
        logger.info("Run with --create-collection flag first")
        return
    
    # Get current collection stats
    collection_info = qdrant.get_collection(settings.qdrant_collection)
    logger.info(f"📊 Current collection: {collection_info.points_count:,} points")
    
    # Get existing file IDs
    logger.info("🔍 Scanning existing indexed files...")
    existing_files = set()
    
    try:
        scroll_result = qdrant.scroll(
            collection_name=settings.qdrant_collection,
            limit=1000,
            with_payload=True,
            with_vectors=False,
        )
        
        for point in scroll_result[0]:
            if point.payload and "source_id" in point.payload:
                existing_files.add(point.payload["source_id"])
                
        logger.info(f"📁 Found {len(existing_files)} unique files already indexed")
        
    except Exception as e:
        logger.warning(f"Could not scan existing files: {e}")
        existing_files = set()
    
    # Get files from Google Drive with retry
    logger.info("🔍 Scanning Google Drive...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            files = drive.list_files_recursive()
            break
        except Exception as e:
            logger.warning(f"Drive scan attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logger.error("❌ Could not scan Google Drive after 3 attempts")
                return
            await asyncio.sleep(5)  # Wait 5 seconds before retry
    
    if not files:
        logger.warning("⚠️ No files found in Google Drive")
        return
    
    # Filter out already indexed files and folders
    new_files = []
    for file_info in files:
        file_id = file_info["id"]
        mime_type = file_info.get("mimeType", "")
        
        # Skip folders
        if mime_type == "application/vnd.google-apps.folder":
            continue
            
        # Skip already indexed files
        if file_id not in existing_files:
            new_files.append(file_info)
    
    logger.info(f"📄 Found {len(new_files)} new files to index")
    
    if not new_files:
        logger.info("✅ No new files to index - collection is up to date!")
        return
    
    # Get current max point ID
    point_id = collection_info.points_count
    total_new_chunks = 0
    
    for i, file_info in enumerate(new_files, 1):
        file_id = file_info["id"]
        file_name = file_info["name"]
        web_url = file_info.get("webViewLink", drive.get_file_url(file_id))
        
        logger.info(f"[{i}/{len(new_files)}] Processing: {file_name}")
        
        try:
            # Get file content
            content = drive.get_file_content(file_id)
            
            if not content.strip():
                logger.warning(f"  ⚠️ Skipping empty file: {file_name}")
                continue
            
            # Chunk the content
            chunks = chunk_text(content)
            logger.info(f"  📝 Created {len(chunks)} chunks")
            
            if not chunks:
                continue
                
            # Generate embeddings
            try:
                embeddings = await embedding_service.embed_batch(chunks)
                
                if len(embeddings) != len(chunks):
                    logger.warning(f"  ⚠️ Embedding mismatch: {len(embeddings)} vs {len(chunks)}")
                    continue
                    
            except Exception as e:
                logger.error(f"  ❌ Failed embeddings for {file_name}: {e}")
                continue
            
            # Create points
            points = []
            for j, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Skip zero vectors
                if all(x == 0.0 for x in embedding):
                    continue
                    
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
                            "chunk_index": j,
                        },
                    )
                )
            
            # Upsert to Qdrant
            if points:
                qdrant.upsert(
                    collection_name=settings.qdrant_collection,
                    points=points,
                )
                
                total_new_chunks += len(points)
                logger.info(f"  ✅ Indexed {len(points)} chunks")
            
        except Exception as e:
            logger.error(f"  ❌ Error processing {file_name}: {e}")
            continue
    
    logger.info(f"🎉 Incremental indexing complete!")
    logger.info(f"📊 Added {total_new_chunks:,} new chunks from {len(new_files)} files")
    
    # Final stats
    try:
        final_collection = qdrant.get_collection(settings.qdrant_collection)
        logger.info(f"📈 Final collection: {final_collection.points_count:,} total points")
    except Exception as e:
        logger.warning(f"Could not get final stats: {e}")


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--create-collection":
        # Create collection only
        logger.info("🏗️ Creating collection...")
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        
        collections = [c.name for c in qdrant.get_collections().collections]
        if settings.qdrant_collection not in collections:
            qdrant.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
            logger.info(f"✅ Created collection: {settings.qdrant_collection}")
        else:
            logger.info(f"✅ Collection already exists: {settings.qdrant_collection}")
        return
    
    # Run incremental indexing
    asyncio.run(simple_incremental_index())


if __name__ == "__main__":
    main()