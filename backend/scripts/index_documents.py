#!/usr/bin/env python
"""Index documents from Google Drive into Qdrant."""

import asyncio
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Set, List, Dict, Any, Optional

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

# Supported file types for indexing
SUPPORTED_MIME_TYPES = {
    # Google Workspace
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
    # Microsoft Office
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/msword",  # .doc
    # PDF
    "application/pdf",
    # Text formats
    "text/plain",
    "text/csv",
    "text/html",
}

# File extensions to skip (images, videos, audio, etc.)
SKIP_EXTENSIONS = {
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff",
    # Videos
    ".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm", ".m4v",
    # Audio
    ".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac", ".wma",
    # Archives
    ".zip", ".rar", ".7z", ".tar", ".gz",
    # Executables
    ".exe", ".dll", ".so", ".dylib",
    # Other
    ".eps", ".ps",
}


def should_index_file(file_info: Dict[str, Any]) -> bool:
    """
    Check if a file should be indexed based on its type.
    
    Args:
        file_info: File metadata from Google Drive
        
    Returns:
        True if file should be indexed, False otherwise
    """
    mime_type = file_info.get("mimeType", "")
    file_name = file_info.get("name", "").lower()
    
    # Skip folders
    if mime_type == "application/vnd.google-apps.folder":
        return False
    
    # Skip Google Shortcuts
    if mime_type == "application/vnd.google-apps.shortcut":
        return False
    
    # Check file extension
    for ext in SKIP_EXTENSIONS:
        if file_name.endswith(ext):
            return False
    
    # Check if MIME type is supported
    if mime_type in SUPPORTED_MIME_TYPES:
        return True
    
    # For files without clear MIME type, check extension
    text_extensions = {".txt", ".csv", ".html", ".htm", ".pdf", ".doc", ".docx", 
                      ".ppt", ".pptx", ".xls", ".xlsx"}
    if any(file_name.endswith(ext) for ext in text_extensions):
        return True
    
    return False


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


class IndexingProgress:
    """Track indexing progress and state."""
    
    def __init__(self, progress_file: str = "indexing_progress.json"):
        self.progress_file = Path(progress_file)
        self.indexed_files: Set[str] = set()
        self.failed_files: Set[str] = set()
        self.total_chunks = 0
        self.session_start = datetime.now()
        self._load_progress()
    
    def _load_progress(self) -> None:
        """Load previous progress from file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    self.indexed_files = set(data.get('indexed_files', []))
                    self.failed_files = set(data.get('failed_files', []))
                    self.total_chunks = data.get('total_chunks', 0)
                    logger.info(f"Loaded progress: {len(self.indexed_files)} files indexed, {self.total_chunks} chunks")
            except Exception as e:
                logger.warning(f"Could not load progress file: {e}")
    
    def save_progress(self) -> None:
        """Save current progress to file."""
        try:
            data = {
                'indexed_files': list(self.indexed_files),
                'failed_files': list(self.failed_files),
                'total_chunks': self.total_chunks,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.progress_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save progress: {e}")
    
    def mark_indexed(self, file_id: str, chunks_added: int) -> None:
        """Mark a file as successfully indexed."""
        self.indexed_files.add(file_id)
        self.failed_files.discard(file_id)  # Remove from failed if it was there
        self.total_chunks += chunks_added
        self.save_progress()
    
    def mark_failed(self, file_id: str) -> None:
        """Mark a file as failed to index."""
        self.failed_files.add(file_id)
        self.save_progress()
    
    def is_indexed(self, file_id: str) -> bool:
        """Check if file is already indexed."""
        return file_id in self.indexed_files
    
    def get_summary(self) -> str:
        """Get indexing summary."""
        duration = datetime.now() - self.session_start
        return f"Progress: {len(self.indexed_files)} indexed, {len(self.failed_files)} failed, {self.total_chunks} total chunks, Duration: {duration}"


def get_existing_files_in_qdrant(qdrant: QdrantClient) -> Set[str]:
    """Get list of file IDs already in Qdrant collection."""
    existing_files = set()
    
    try:
        # Scroll through all points to get unique source_ids
        scroll_result = qdrant.scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter=None,
            limit=10000,  # Large batch
            with_payload=True,
            with_vectors=False,
        )
        
        for point in scroll_result[0]:  # scroll_result is (points, next_page_offset)
            if point.payload and "source_id" in point.payload:
                existing_files.add(point.payload["source_id"])
        
        # Continue scrolling if there are more points
        offset = scroll_result[1]
        while offset is not None:
            scroll_result = qdrant.scroll(
                collection_name=settings.qdrant_collection,
                offset=offset,
                limit=10000,
                with_payload=True,
                with_vectors=False,
            )
            
            for point in scroll_result[0]:
                if point.payload and "source_id" in point.payload:
                    existing_files.add(point.payload["source_id"])
            
            offset = scroll_result[1]
            
        logger.info(f"Found {len(existing_files)} unique files already in Qdrant")
        
    except Exception as e:
        logger.warning(f"Could not scan existing files in Qdrant: {e}")
    
    return existing_files


async def index_documents(force_reindex: bool = False, target_files: list[str] = None) -> None:
    """Index documents from Google Drive into Qdrant with incremental support.
    
    Args:
        force_reindex: If True, reindex all files (recreates collection)
        target_files: If provided, only index these specific file IDs
    """
    logger.info(f"Starting {'full' if force_reindex else 'incremental'} document indexing...")
    
    # Initialize services
    drive = DriveService()
    embedding_service = EmbeddingService()
    progress = IndexingProgress()
    
    # Initialize Qdrant
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    
    # Handle collection creation/recreation
    collections = [c.name for c in qdrant.get_collections().collections]
    
    if settings.qdrant_collection not in collections:
        logger.info(f"Creating new Qdrant collection: {settings.qdrant_collection}")
        qdrant.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=1536,  # text-embedding-3-small dimension
                distance=Distance.COSINE,
            ),
        )
    elif force_reindex:
        logger.info(f"Force reindex: recreating collection {settings.qdrant_collection}")
        qdrant.delete_collection(settings.qdrant_collection)
        qdrant.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=1536,
                distance=Distance.COSINE,
            ),
        )
        # Reset progress for full reindex
        progress = IndexingProgress()
    else:
        logger.info(f"Incremental indexing: using existing collection {settings.qdrant_collection}")
    
    # Get existing files in Qdrant (for incremental indexing)
    existing_in_qdrant = set() if force_reindex else get_existing_files_in_qdrant(qdrant)
    
    # Get files from Google Drive
    logger.info("Scanning Google Drive folder recursively...")
    all_files = drive.list_files_recursive()
    
    if not all_files:
        logger.warning("No files found in Google Drive folder!")
        return
    
    # Filter out unsupported file types (images, videos, audio, etc.)
    files = [f for f in all_files if should_index_file(f)]
    skipped = len(all_files) - len(files)
    logger.info(f"Filtered to {len(files)} indexable files (skipped {skipped} images/videos/audio)")
    
    # Filter files based on target_files or incremental logic
    if target_files:
        files = [f for f in files if f["id"] in target_files]
        logger.info(f"Filtering to {len(files)} target files")
    elif not force_reindex:
        # Skip files already indexed (but retry failed ones)
        files_to_process = []
        for file_info in files:
            file_id = file_info["id"]
            if file_id in existing_in_qdrant and not file_id in progress.failed_files:
                continue  # Skip already indexed files
            files_to_process.append(file_info)
        files = files_to_process
        logger.info(f"Incremental mode: {len(files)} files to process (skipping {len(existing_in_qdrant)} already indexed)")
    
    logger.info(f"Processing {len(files)} files total")
    
    # Get current max point ID for new points
    try:
        # Get collection info to find max point ID
        collection_info = qdrant.get_collection(settings.qdrant_collection)
        point_id = collection_info.points_count if not force_reindex else 0
    except:
        point_id = 0
    
    processed_count = 0
    
    for file_info in files:
        file_id = file_info["id"]
        file_name = file_info["name"]
        mime_type = file_info.get("mimeType", "")
        web_url = file_info.get("webViewLink", drive.get_file_url(file_id))
        
        processed_count += 1
        logger.info(f"[{processed_count}/{len(files)}] Processing: {file_name}")
        
        try:
            # Get file content
            content = drive.get_file_content(file_id)
            
            if not content.strip():
                logger.warning(f"  Skipping empty file: {file_name}")
                continue
            
            # Chunk the content
            chunks = chunk_text(content)
            logger.info(f"  Created {len(chunks)} chunks")
            
            if len(chunks) == 0:
                logger.warning(f"  No chunks created for {file_name}")
                continue
            
            # Generate embeddings with rate limiting
            try:
                embeddings = await embedding_service.embed_batch(chunks)
                
                # Validate embeddings
                if len(embeddings) != len(chunks):
                    logger.warning(f"  Embedding mismatch for {file_name}: {len(embeddings)} vs {len(chunks)}")
                    progress.mark_failed(file_id)
                    continue
                    
            except Exception as e:
                logger.error(f"  Failed to generate embeddings for {file_name}: {e}")
                progress.mark_failed(file_id)
                continue
            
            # Remove existing points for this file (in case of updates)
            try:
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
                logger.debug(f"  No existing points to delete for {file_name}: {e}")
            
            # Create points for Qdrant
            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Skip zero vectors (failed embeddings)
                if all(x == 0.0 for x in embedding):
                    logger.warning(f"  Skipping zero vector for chunk {i} in {file_name}")
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
                            "chunk_index": i,
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
                
                progress.mark_indexed(file_id, len(points))
                logger.info(f"  ✅ Indexed {len(points)} chunks for {file_name}")
            else:
                logger.warning(f"  No valid points created for {file_name}")
                progress.mark_failed(file_id)
            
            # Progress update every 10 files
            if processed_count % 10 == 0:
                logger.info(f"📊 {progress.get_summary()}")
            
        except Exception as e:
            logger.error(f"  ❌ Error processing {file_name}: {e}")
            progress.mark_failed(file_id)
            continue
    
    # Final summary
    logger.info(f"🎉 Indexing session complete!")
    logger.info(f"📊 Final: {progress.get_summary()}")
    
    # Show collection stats
    try:
        collection_info = qdrant.get_collection(settings.qdrant_collection)
        # Handle version compatibility for vectors_count
        if hasattr(collection_info, 'vectors_count'):
            total_vectors = collection_info.vectors_count
        else:
            total_vectors = collection_info.points_count
        logger.info(f"📈 Collection stats: {collection_info.points_count} total points, {total_vectors} vectors")
    except Exception as e:
        logger.warning(f"Could not get collection stats: {e}")


def main() -> None:
    """Run the indexing script with command line options."""
    parser = argparse.ArgumentParser(description="Index Google Drive documents into Qdrant")
    parser.add_argument(
        "--force-reindex", 
        action="store_true", 
        help="Force complete reindexing (recreates collection)"
    )
    parser.add_argument(
        "--files", 
        nargs="+", 
        help="Specific file IDs to index (space-separated)"
    )
    parser.add_argument(
        "--resume", 
        action="store_true", 
        help="Resume from previous indexing session"
    )
    
    args = parser.parse_args()
    
    if args.force_reindex:
        logger.info("🔄 Force reindex mode: Will recreate collection and index all files")
    elif args.files:
        logger.info(f"🎯 Target mode: Will index specific files: {args.files}")
    else:
        logger.info("⚡ Incremental mode: Will skip already indexed files")
    
    asyncio.run(index_documents(
        force_reindex=args.force_reindex,
        target_files=args.files
    ))


if __name__ == "__main__":
    main()
