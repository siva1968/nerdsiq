"""
Document viewing router for NerdsIQ
Allows authenticated users to view Google Drive documents
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.routers.auth import get_current_user
from app.models.user import User
from app.services.document_service import DocumentService
import logging
import io

logger = logging.getLogger(__name__)

router = APIRouter()
document_service = DocumentService()


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
