"""Health check router."""

from fastapi import APIRouter, Depends
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import settings
from app.services.cache_service import CacheService
from app.routers.auth import get_current_user
from app.models.user import User

router = APIRouter()
cache_service = CacheService()


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
        "cache": cache_service.stats(),
    }


@router.post("/cache/invalidate")
async def invalidate_cache(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Invalidate all cached query responses.
    
    Call this after document updates to ensure fresh responses.
    """
    await cache_service.invalidate_all()
    return {"message": "Cache invalidated successfully"}
