"""
Document viewing router for NerdsIQ
Allows authenticated users to view Google Drive documents
"""
from fastapi import APIRouter, Depends, HTTPException, Response, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.routers.auth import get_current_user
from app.models.user import User
from app.services.document_service import DocumentService
from app.services.cache_service import CacheService
from app.services.webhook_service import webhook_service
from app.services.drive_service import DriveService
from app.config import settings
from loguru import logger
import io
import asyncio
import subprocess
import sys
import time
import json
from pathlib import Path
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

router = APIRouter()
document_service = DocumentService()
cache_service = CacheService()

# Debouncing for webhook notifications
_reindex_task: Optional[asyncio.Task] = None
_last_webhook_time: float = 0
REINDEX_DEBOUNCE_SECONDS = 30  # Wait 30 seconds after last change before reindexing


class DocumentViewRequest(BaseModel):
    document_url: str


class DocumentViewResponse(BaseModel):
    content: str
    mime_type: str
    file_name: str


class DocumentProxyRequest(BaseModel):
    document_url: str


@router.post("/view", response_model=DocumentViewResponse)
async def view_document(
    request: DocumentViewRequest,
    current_user: User = Depends(get_current_user),
) -> DocumentViewResponse:
    """
    Fetch and convert a Google Drive document for viewing.
    
    The document is fetched using the service account credentials,
    converted to HTML, and returned for display in the frontend.
    """
    try:
        result = await document_service.get_document(request.document_url)
        return DocumentViewResponse(
            content=result['content'],
            mime_type=result['mime_type'],
            file_name=result['file_name']
        )
    except ValueError as e:
        logger.error(f"Invalid document URL: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
        raise HTTPException(status_code=403, detail="Document access denied")
    except Exception as e:
        logger.error(f"Error fetching document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch document")


@router.post("/proxy")
async def proxy_document(
    request: DocumentProxyRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Proxy a document directly from Google Drive.
    Returns the raw file bytes with appropriate content type.
    This allows embedding documents without requiring Google auth.
    """
    try:
        file_id = document_service.extract_file_id(request.document_url)
        result = await document_service.get_raw_document(file_id)
        
        return Response(
            content=result['content'],
            media_type=result['mime_type'],
            headers={
                'Content-Disposition': f'inline; filename="{result["file_name"]}"',
                'Cache-Control': 'private, max-age=3600'
            }
        )
    except ValueError as e:
        logger.error(f"Invalid document URL: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
        raise HTTPException(status_code=403, detail="Document access denied")
    except Exception as e:
        logger.error(f"Error proxying document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch document")


async def cleanup_deleted_files():
    """
    Compare files in Qdrant with files in Google Drive and remove deleted ones.
    This runs after detecting file changes to keep the index in sync.
    """
    try:
        logger.info("🗑️  Checking for deleted files in Google Drive...")
        
        # Initialize services
        drive = DriveService()
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        
        # Get all files currently in Google Drive
        logger.info("📥 Fetching current files from Google Drive...")
        all_drive_files = await asyncio.to_thread(drive.list_files_recursive, settings.google_drive_folder_id)
        drive_file_ids = {file['id'] for file in all_drive_files}
        logger.info(f"   Found {len(drive_file_ids)} files in Google Drive")
        
        # Get all unique source_ids from Qdrant
        logger.info("📊 Fetching indexed files from Qdrant...")
        collection_name = settings.qdrant_collection
        
        # Scroll through all points to get unique source_ids
        offset = None
        indexed_file_ids = set()
        while True:
            result = qdrant.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                with_payload=["source_id"]
            )
            
            points, next_offset = result
            if not points:
                break
                
            for point in points:
                if point.payload and "source_id" in point.payload:
                    indexed_file_ids.add(point.payload["source_id"])
            
            if next_offset is None:
                break
            offset = next_offset
        
        logger.info(f"   Found {len(indexed_file_ids)} unique files in Qdrant")
        
        # Find files that are in Qdrant but not in Drive (deleted files)
        deleted_file_ids = indexed_file_ids - drive_file_ids
        
        if not deleted_file_ids:
            logger.info("✅ No deleted files found - index is up to date")
            return 0
        
        logger.info(f"🗑️  Found {len(deleted_file_ids)} deleted files to remove from index")
        
        # Remove chunks for each deleted file
        total_removed = 0
        for file_id in deleted_file_ids:
            try:
                # Delete all points with this source_id
                qdrant.delete(
                    collection_name=collection_name,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="source_id",
                                match=MatchValue(value=file_id)
                            )
                        ]
                    )
                )
                total_removed += 1
                logger.info(f"   ✅ Removed chunks for file: {file_id}")
            except Exception as e:
                logger.error(f"   ❌ Failed to remove file {file_id}: {e}")
        
        # Update indexing progress file
        try:
            progress_file = Path("/app/indexing_progress.json")
            if progress_file.exists():
                with open(progress_file, 'r') as f:
                    progress = json.load(f)
                
                # Remove deleted files from indexed_files list
                original_count = len(progress.get('indexed_files', []))
                progress['indexed_files'] = [
                    f for f in progress.get('indexed_files', [])
                    if f.get('id') not in deleted_file_ids
                ]
                removed_count = original_count - len(progress['indexed_files'])
                
                # Update timestamp
                from datetime import datetime
                progress['last_updated'] = datetime.utcnow().isoformat()
                
                with open(progress_file, 'w') as f:
                    json.dump(progress, f, indent=2)
                
                logger.info(f"📝 Updated progress file: removed {removed_count} deleted files")
        except Exception as e:
            logger.error(f"⚠️  Failed to update progress file: {e}")
        
        logger.info(f"✅ Cleanup complete: removed {total_removed} deleted files from index")
        return total_removed
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}", exc_info=True)
        return 0


async def debounced_reindexing():
    """
    Debounced reindexing that waits for a quiet period before actually reindexing.
    This prevents excessive reindexing when many files change in quick succession.
    """
    global _last_webhook_time
    
    # Wait for the debounce period
    while time.time() - _last_webhook_time < REINDEX_DEBOUNCE_SECONDS:
        await asyncio.sleep(5)  # Check every 5 seconds
    
    # Now do the actual reindexing
    await trigger_reindexing()


async def schedule_reindexing():
    """
    Schedule a debounced reindexing operation.
    If already scheduled, this extends the debounce period.
    """
    global _reindex_task, _last_webhook_time
    
    _last_webhook_time = time.time()
    
    # If there's already a reindexing task running, let it continue
    # The debouncing logic will handle the timing
    if _reindex_task and not _reindex_task.done():
        logger.info("   ⏳ Extending reindex debounce period")
        return
    
    # Start new debounced reindexing task
    logger.info(f"   🕐 Scheduling reindexing (will wait {REINDEX_DEBOUNCE_SECONDS}s for more changes)")
    _reindex_task = asyncio.create_task(debounced_reindexing())


async def trigger_reindexing():
    """Background task to reindex documents after Google Drive changes."""
    try:
        logger.info("🔄 Starting automatic document reindexing...")
        
        # Clear all cached queries since documents may have changed
        await cache_service.invalidate_all()
        logger.info("💨 Cleared all cached queries")
        
        # TODO: In the future, we could implement smarter reindexing:
        # - Parse webhook payload to identify specific changed files
        # - Only reindex changed files instead of full reindex
        # - Use Google Drive's changes.list API to get detailed changes
        
        # Get the path to the indexing script
        script_path = Path(__file__).parent.parent.parent / "scripts" / "index_documents.py"
        python_path = sys.executable
        
        # Run the indexing script in the background with --resume flag for incremental updates
        process = await asyncio.create_subprocess_exec(
            python_path, str(script_path), "--resume",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info("✅ Document reindexing completed successfully")
            logger.debug(f"Indexing output: {stdout.decode()}")
            
            # After successful reindexing, cleanup deleted files
            logger.info("🧹 Running cleanup to remove deleted files...")
            removed_count = await cleanup_deleted_files()
            if removed_count > 0:
                logger.info(f"♻️  Removed {removed_count} deleted files from index")
        else:
            logger.error(f"❌ Document reindexing failed with code {process.returncode}")
            logger.error(f"Error output: {stderr.decode()}")
            
    except Exception as e:
        logger.error(f"❌ Failed to trigger reindexing: {e}", exc_info=True)


@router.post("/webhook/drive-changes")
async def google_drive_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle Google Drive push notifications for file changes.
    
    This endpoint receives webhook notifications from Google Drive API
    when files in the monitored folder are added, modified, or deleted.
    
    Google Drive sends notifications with headers:
    - X-Goog-Channel-ID: The channel ID
    - X-Goog-Resource-State: sync, add, remove, update, etc.
    - X-Goog-Resource-ID: The resource being watched
    """
    try:
        # Get notification headers
        channel_id = request.headers.get("X-Goog-Channel-ID", "")
        resource_state = request.headers.get("X-Goog-Resource-State", "")
        resource_id = request.headers.get("X-Goog-Resource-ID", "")
        
        logger.info(f"📨 Google Drive webhook received:")
        logger.info(f"   Channel ID: {channel_id}")
        logger.info(f"   Resource State: {resource_state}")
        logger.info(f"   Resource ID: {resource_id}")
        
        # Ignore sync messages (initial webhook verification)
        if resource_state == "sync":
            logger.info("   ⏭️  Ignoring sync message")
            return {"status": "ok", "message": "sync acknowledged"}
        
        # For all file changes (add, remove, update, trash, untrash), trigger reindexing
        if resource_state in ["add", "remove", "update", "change", "trash", "untrash"]:
            logger.info(f"   🚀 Scheduling debounced reindexing due to {resource_state} event")
            await schedule_reindexing()
        else:
            logger.info(f"   ⏭️  Ignoring unknown state: {resource_state}")
        
        return {"status": "ok", "message": f"processed {resource_state} event"}
        
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}", exc_info=True)
        # Always return 200 to prevent Google from retrying
        return {"status": "error", "message": "webhook processing failed"}


@router.post("/webhook/setup")
async def setup_webhook(
    current_user: User = Depends(get_current_user),
):
    """
    Set up Google Drive webhook for automatic document synchronization.
    
    This creates a webhook that will automatically trigger reindexing
    when documents are added, modified, or removed from Google Drive.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Determine the callback URL
        # In production, this should be your public domain
        # For development, you might use a tunnel service like ngrok or cloudflare tunnel
        callback_url = f"{settings.webhook_callback_base_url}/api/v1/documents/webhook/drive-changes"
        
        # Start auto-renewal (creates initial webhook and schedules renewals)
        await webhook_service.start_auto_renewal(callback_url)
        
        status = webhook_service.get_webhook_status()
        
        return {
            "status": "success",
            "message": "Webhook setup completed",
            "webhook": status
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to setup webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Webhook setup failed: {str(e)}")


@router.get("/webhook/status")
async def webhook_status(
    current_user: User = Depends(get_current_user),
):
    """Get current webhook status."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    return webhook_service.get_webhook_status()


@router.post("/webhook/stop")
async def stop_webhook(
    current_user: User = Depends(get_current_user),
):
    """Stop the current webhook."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        await webhook_service.stop_auto_renewal()
        return {"status": "success", "message": "Webhook stopped"}
    except Exception as e:
        logger.error(f"❌ Failed to stop webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop webhook: {str(e)}")


@router.post("/folder/change")
async def change_sync_folder(
    request: dict,
    current_user: User = Depends(get_current_user),
):
    """
    Change the Google Drive folder being synced.
    
    Body: { "folder_id": "new-folder-id" }
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    new_folder_id = request.get("folder_id", "").strip()
    if not new_folder_id:
        raise HTTPException(status_code=400, detail="folder_id is required")
    
    try:
        # Stop current webhook
        logger.info(f"🛑 Stopping current webhook...")
        await webhook_service.stop_auto_renewal()
        
        # Update folder ID in settings
        old_folder_id = settings.google_drive_folder_id
        settings.google_drive_folder_id = new_folder_id
        
        logger.info(f"📁 Changed sync folder from {old_folder_id} to {new_folder_id}")
        
        # Clear all caches
        await cache_service.invalidate_all()
        logger.info("💨 Cleared all cached queries")
        
        # Start new webhook for new folder
        callback_url = f"{settings.webhook_callback_base_url}/api/v1/documents/webhook/drive-changes"
        await webhook_service.start_auto_renewal(callback_url)
        
        # Trigger reindexing for new folder
        logger.info("🔄 Triggering reindexing for new folder...")
        await schedule_reindexing()
        
        webhook_status = webhook_service.get_webhook_status()
        
        return {
            "status": "success",
            "message": f"Sync folder changed successfully",
            "old_folder_id": old_folder_id,
            "new_folder_id": new_folder_id,
            "webhook": webhook_status,
            "next_steps": [
                "Webhook has been updated for the new folder",
                "Document reindexing is running in background",
                "Cache has been cleared",
                "System will now monitor the new folder for changes"
            ]
        }
        
    except Exception as e:
        # Restore old folder ID if something failed
        settings.google_drive_folder_id = old_folder_id
        logger.error(f"❌ Failed to change sync folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to change sync folder: {str(e)}")


@router.get("/folder/current")
async def get_current_folder(
    current_user: User = Depends(get_current_user),
):
    """Get information about the currently synced folder."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Get folder info from Google Drive
        from app.services.drive_service import DriveService
        drive_service = DriveService()
        
        # Get folder details
        folder_info = drive_service.service.files().get(
            fileId=settings.google_drive_folder_id,
            fields="id,name,webViewLink,modifiedTime,parents"
        ).execute()
        
        # Count files in folder
        files = drive_service.list_files_recursive()
        file_count = len([f for f in files if f.get('mimeType') != 'application/vnd.google-apps.folder'])
        
        webhook_status = webhook_service.get_webhook_status()
        
        return {
            "folder_id": settings.google_drive_folder_id,
            "folder_name": folder_info.get("name"),
            "folder_url": folder_info.get("webViewLink"),
            "last_modified": folder_info.get("modifiedTime"),
            "file_count": file_count,
            "webhook_status": webhook_status["status"],
            "webhook_details": webhook_status.get("webhook")
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get folder info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get folder info: {str(e)}")


@router.post("/webhook/stop")
async def stop_webhook(
    current_user: User = Depends(get_current_user),
):
    """Stop the current webhook."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        await webhook_service.stop_auto_renewal()
        return {"status": "success", "message": "Webhook stopped"}
    except Exception as e:
        logger.error(f"❌ Failed to stop webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop webhook: {str(e)}")
