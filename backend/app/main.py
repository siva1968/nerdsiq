"""NerdsIQ FastAPI Application Entry Point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.database import create_tables
from app.routers import auth, chat, health, analytics, logs
from app.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    AuditLogMiddleware,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info("Starting NerdsIQ API...")
    logger.info(f"Environment: {settings.app_env}")
    
    # Create database tables
    await create_tables()
    logger.info("Database tables created")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NerdsIQ API...")


# Create FastAPI application
app = FastAPI(
    title="NerdsIQ API",
    description="RAG-based AI Knowledge Assistant for NerdsToGo",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# Add security middlewares (order matters - first added = last executed)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# Register routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["Logs"])

# Import documents router
from app.routers import documents
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])


@app.get("/")
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": "NerdsIQ API",
        "version": "1.0.0",
        "docs": "/docs" if settings.is_development else None,
    }
