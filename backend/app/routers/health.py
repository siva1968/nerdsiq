"""Health check router."""

from fastapi import APIRouter
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.
    
    Returns the API status and connectivity to Qdrant.
    """
    qdrant_status = "disconnected"
    
    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        # Check if Qdrant is reachable
        client.get_collections()
        qdrant_status = "connected"
    except (UnexpectedResponse, Exception):
        qdrant_status = "disconnected"
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.app_env,
        "qdrant": qdrant_status,
    }
