#!/usr/bin/env python3
"""Enhanced incremental indexing with daily logging and email notifications."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, Distance, VectorParams
from loguru import logger
import tiktoken

from app.config import settings
from app.services.drive_service import DriveService
from app.services.embedding_service import EmbeddingService
from app.services.monitoring_service import indexing_monitor


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Chunk text into overlapping segments."""
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


async def monitored_incremental_index(send_email: bool = True):
    """Enhanced incremental indexing with monitoring and notifications."""
    
    # Start monitoring session
    indexing_monitor.start_session("Enhanced Incremental Indexing")
    
    try:
        # Initialize services
        indexing_monitor.log_info("🔧 Initializing services...")
        drive = DriveService()
        embedding_service = EmbeddingService()
        
        # Connect to existing Qdrant
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        
        # Check collection exists
        collections = [c.name for c in qdrant.get_collections().collections]
        if settings.qdrant_collection not in collections:
            indexing_monitor.log_error(f"Collection {settings.qdrant_collection} not found!")
            indexing_monitor.log_info("Run with --create-collection flag first")
            return
        
        # Get initial collection stats
        collection_info = qdrant.get_collection(settings.qdrant_collection)
        indexing_monitor.log_collection_stats("before", {
            "points_count": collection_info.points_count,
            "status": collection_info.status
        })
        
        # Get existing file IDs
        indexing_monitor.log_info("🔍 Scanning existing indexed files...")
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
                    
            indexing_monitor.log_info(f"📁 Found {len(existing_files)} unique files already indexed")
            
        except Exception as e:
            indexing_monitor.log_error("Could not scan existing files", e)
            existing_files = set()
        
        # Get files from Google Drive with retry
        indexing_monitor.log_info("🔍 Scanning Google Drive...")
        
        max_retries = 3
        files = None
        
        for attempt in range(max_retries):
            try:
                files = drive.list_files_recursive()
                indexing_monitor.log_info(f"📂 Found {len(files) if files else 0} total files in Drive")
                break
            except Exception as e:
                indexing_monitor.log_error(f"Drive scan attempt {attempt + 1} failed", e)
                if attempt == max_retries - 1:
                    indexing_monitor.log_error("Could not scan Google Drive after 3 attempts")
                    return
                await asyncio.sleep(5)
        
        if not files:
            indexing_monitor.log_info("⚠️ No files found in Google Drive")
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
        
        indexing_monitor.log_info(f"📄 Found {len(new_files)} new files to index")
        
        if not new_files:
            indexing_monitor.log_info("✅ No new files to index - collection is up to date!")
            # Still end the session to log completion
            final_stats = indexing_monitor.end_session(send_email=send_email)
            return final_stats
        
        # Get current max point ID
        point_id = collection_info.points_count
        total_new_chunks = 0
        processed_files = 0
        
        # Process files with progress tracking
        for i, file_info in enumerate(new_files, 1):
            file_id = file_info["id"]
            file_name = file_info["name"]
            web_url = file_info.get("webViewLink", drive.get_file_url(file_id))
            
            indexing_monitor.log_info(f"[{i}/{len(new_files)}] Processing: {file_name}")
            processed_files += 1
            
            try:
                # Get file content
                content = drive.get_file_content(file_id)
                
                if not content.strip():
                    indexing_monitor.log_info(f"  ⚠️ Skipping empty file: {file_name}")
                    continue
                
                # Chunk the content
                chunks = chunk_text(content)
                indexing_monitor.log_info(f"  📝 Created {len(chunks)} chunks")
                
                if not chunks:
                    continue
                    
                # Generate embeddings
                try:
                    embeddings = await embedding_service.embed_batch(chunks)
                    
                    if len(embeddings) != len(chunks):
                        indexing_monitor.log_file_error(
                            file_name,
                            f"Embedding mismatch: {len(embeddings)} vs {len(chunks)}"
                        )
                        continue
                        
                except Exception as e:
                    indexing_monitor.log_file_error(file_name, f"Failed embeddings: {str(e)}")
                    continue
                
                # Remove existing points for this file (in case of updates)
                try:
                    from qdrant_client.http.models import Filter, FieldCondition, MatchValue
                    qdrant.delete(
                        collection_name=settings.qdrant_collection,
                        points_selector=Filter(
                            must=[
                                FieldCondition(
                                    key="source_id",
                                    match=MatchValue(value=file_id)
                                )
                            ]
                        )
                    )
                except Exception as e:
                    # This is expected for new files
                    pass
                
                # Create points for Qdrant
                points = []
                valid_chunks = 0
                
                for j, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    # Skip zero vectors (failed embeddings)
                    if all(x == 0.0 for x in embedding):
                        indexing_monitor.log_info(f"  ⚠️ Skipping zero vector for chunk {j}")
                        continue
                        
                    point_id += 1
                    valid_chunks += 1
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
                                "indexed_at": datetime.now().isoformat(),
                            },
                        )
                    )
                
                # Upsert to Qdrant
                if points:
                    qdrant.upsert(
                        collection_name=settings.qdrant_collection,
                        points=points,
                    )
                    
                    total_new_chunks += valid_chunks
                    indexing_monitor.log_file_success(file_name, valid_chunks)
                else:
                    indexing_monitor.log_file_error(file_name, "No valid points created")
                
                # Progress update every 25 files
                if processed_files % 25 == 0:
                    indexing_monitor.log_info(f"🔄 Progress: {processed_files}/{len(new_files)} files processed")
                
                # Small delay to avoid overwhelming APIs
                if i % 10 == 0:
                    await asyncio.sleep(0.5)
                
            except Exception as e:
                indexing_monitor.log_file_error(file_name, str(e))
                continue
        
        # Get final collection stats
        try:
            final_collection = qdrant.get_collection(settings.qdrant_collection)
            indexing_monitor.log_collection_stats("after", {
                "points_count": final_collection.points_count,
                "status": final_collection.status
            })
        except Exception as e:
            indexing_monitor.log_error("Could not get final collection stats", e)
        
        # End monitoring session
        final_stats = indexing_monitor.end_session(send_email=send_email)
        
        # Send alert if there were significant issues
        indexing_monitor.send_alert_if_needed(final_stats)
        
        return final_stats
        
    except Exception as e:
        indexing_monitor.log_error("Critical error in indexing session", e)
        indexing_monitor.end_session(send_email=send_email)
        raise


def main():
    """Main function with command line options."""
    send_email = True
    create_collection = False
    
    # Parse simple command line arguments
    for arg in sys.argv[1:]:
        if arg == "--no-email":
            send_email = False
        elif arg == "--create-collection":
            create_collection = True
    
    if create_collection:
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
    
    # Run monitored incremental indexing
    logger.info("🚀 Starting monitored incremental indexing...")
    logger.info(f"📧 Email notifications: {'Enabled' if send_email else 'Disabled'}")
    
    try:
        final_stats = asyncio.run(monitored_incremental_index(send_email=send_email))
        
        if final_stats:
            success_rate = (final_stats['successful_files'] / 
                          max(final_stats['total_files_processed'], 1)) * 100
            
            logger.info(f"🎉 Session completed!")
            logger.info(f"📊 Success rate: {success_rate:.1f}%")
            logger.info(f"📄 Total new chunks: {final_stats['total_chunks_added']:,}")
            
            # Print daily log location
            log_dir = Path("daily_logs")
            today = datetime.now().date()
            log_file = log_dir / f"indexing_{today.strftime('%Y-%m-%d')}.log"
            logger.info(f"📋 Full log saved to: {log_file}")
    
    except Exception as e:
        logger.error(f"❌ Session failed: {e}")
        raise


if __name__ == "__main__":
    main()