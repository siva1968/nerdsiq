#!/usr/bin/env python3
"""Document indexing management script for NerdsIQ."""

import json
from pathlib import Path
from datetime import datetime
import asyncio
import sys
import os

# Add the backend directory to path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from loguru import logger
from app.config import settings


def check_indexing_status():
    """Check current indexing status."""
    logger.info("📊 Checking indexing status...")
    
    # Check progress file
    progress_file = Path("indexing_progress.json")
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            progress = json.load(f)
            
        logger.info(f"📁 Progress file found:")
        logger.info(f"   • Indexed files: {len(progress.get('indexed_files', []))}")
        logger.info(f"   • Failed files: {len(progress.get('failed_files', []))}")
        logger.info(f"   • Total chunks: {progress.get('total_chunks', 0)}")
        logger.info(f"   • Last updated: {progress.get('last_updated', 'Unknown')}")
        
        if progress.get('failed_files'):
            logger.info(f"❌ Failed files: {len(progress['failed_files'])}")
    else:
        logger.info("📁 No progress file found - starting fresh")
    
    # Check Qdrant collection
    try:
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        collections = [c.name for c in qdrant.get_collections().collections]
        
        if settings.qdrant_collection in collections:
            collection_info = qdrant.get_collection(settings.qdrant_collection)
            logger.info(f"🗄️ Qdrant collection '{settings.qdrant_collection}':")
            logger.info(f"   • Total points: {collection_info.points_count:,}")
            logger.info(f"   • Total vectors: {collection_info.vectors_count:,}")
            logger.info(f"   • Status: {collection_info.status}")
            
            # Get unique files count
            try:
                scroll_result = qdrant.scroll(
                    collection_name=settings.qdrant_collection,
                    limit=1000,
                    with_payload=True,
                    with_vectors=False,
                )
                
                unique_files = set()
                for point in scroll_result[0]:
                    if point.payload and "source_id" in point.payload:
                        unique_files.add(point.payload["source_id"])
                
                logger.info(f"   • Unique source files: {len(unique_files)}")
                
            except Exception as e:
                logger.warning(f"Could not count unique files: {e}")
            
        else:
            logger.warning(f"⚠️ Qdrant collection '{settings.qdrant_collection}' does not exist")
            
    except Exception as e:
        logger.error(f"❌ Could not connect to Qdrant: {e}")


def show_recommendations():
    """Show recommendations based on current status."""
    logger.info("💡 Recommendations:")
    logger.info("")
    
    progress_file = Path("indexing_progress.json")
    has_progress = progress_file.exists()
    
    try:
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        collections = [c.name for c in qdrant.get_collections().collections]
        has_collection = settings.qdrant_collection in collections
        
        if has_collection:
            collection_info = qdrant.get_collection(settings.qdrant_collection)
            has_data = collection_info.points_count > 0
        else:
            has_data = False
            
    except:
        has_collection = False
        has_data = False
    
    if not has_data:
        logger.info("🚀 FIRST TIME SETUP:")
        logger.info("   Run: python scripts/index_documents.py")
        logger.info("   This will index all documents from scratch")
        
    elif has_progress:
        with open(progress_file, 'r') as f:
            progress = json.load(f)
            
        failed_count = len(progress.get('failed_files', []))
        
        if failed_count > 0:
            logger.info("🔄 RESUME INDEXING:")
            logger.info("   Run: python scripts/index_documents.py --resume")
            logger.info(f"   This will retry {failed_count} failed files")
        
        logger.info("⚡ INCREMENTAL UPDATE:")
        logger.info("   Run: python scripts/index_documents.py")
        logger.info("   This will only index new/changed files")
        
    logger.info("")
    logger.info("🔧 OTHER OPTIONS:")
    logger.info("   Full reindex: python scripts/index_documents.py --force-reindex")
    logger.info("   Specific files: python scripts/index_documents.py --files FILE_ID1 FILE_ID2")
    logger.info("   Check status: python scripts/manage_indexing.py status")


def main():
    """Main management function."""
    if len(sys.argv) < 2:
        logger.info("📖 NerdsIQ Document Indexing Manager")
        logger.info("")
        logger.info("Usage: python scripts/manage_indexing.py <command>")
        logger.info("")
        logger.info("Commands:")
        logger.info("  status     - Check current indexing status")
        logger.info("  recommend  - Show recommended actions")
        logger.info("  clean      - Clean progress file and start fresh")
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        check_indexing_status()
        
    elif command == "recommend":
        check_indexing_status()
        logger.info("")
        show_recommendations()
        
    elif command == "clean":
        progress_file = Path("indexing_progress.json")
        if progress_file.exists():
            progress_file.unlink()
            logger.info("🧹 Cleaned progress file - next indexing will start fresh")
        else:
            logger.info("🧹 No progress file to clean")
            
    else:
        logger.error(f"❌ Unknown command: {command}")
        logger.info("Available commands: status, recommend, clean")


if __name__ == "__main__":
    main()