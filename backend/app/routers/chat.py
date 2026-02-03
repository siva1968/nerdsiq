"""Chat router for RAG queries."""

import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.chat import ChatHistoryResponse, MessageResponse, QueryRequest, QueryResponse, SessionListResponse, SessionSummary
from app.services.rag_service import RAGService
from app.services.analytics_service import AnalyticsService
from app.services.cache_service import CacheService
from app.security import InputValidator

router = APIRouter()
cache_service = CacheService()


@router.post("/query", response_model=QueryResponse)
async def query_rag(
    request: QueryRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """
    Process a RAG query and return an AI-generated answer with sources.
    
    The query is processed through the RAG pipeline:
    1. Embed the question
    2. Search Qdrant for relevant document chunks
    3. Build context and query GPT-4o-mini
    4. Return answer with source URLs
    """
    start_time = time.time()
    analytics = AnalyticsService(db)
    error_message = None
    answer = ""
    sources = []
    
    # Validate and sanitize question
    is_valid, validation_error = InputValidator.validate_question(request.question)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_error,
        )
    
    # Sanitize question
    question = InputValidator.sanitize_text(request.question, max_length=1000)
    
    # Get or create conversation
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == request.session_id)
        .where(Conversation.user_id == current_user.id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        conversation = Conversation(
            user_id=current_user.id,
            session_id=request.session_id,
        )
        db.add(conversation)
        await db.flush()
    
    # Store user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.question,
    )
    db.add(user_message)
    
    # Check cache first
    cache_key = CacheService.generate_key(request.question)
    cached_result = await cache_service.get(cache_key)
    was_cached = False
    
    if cached_result:
        # Use cached response
        answer = cached_result.get("answer", "")
        sources = cached_result.get("sources", [])
        was_cached = True
    else:
        # Process RAG query
        try:
            rag_service = RAGService()
            answer, sources = await rag_service.query(
                question=request.question,
                session_id=request.session_id,
                model=request.model,
            )
            
            # Cache the result
            await cache_service.set(cache_key, {
                "answer": answer,
                "sources": sources,
            })
        except Exception as e:
            error_message = str(e)
            # Log the failed query
            response_time_ms = int((time.time() - start_time) * 1000)
            await analytics.log_query(
                user_id=current_user.id,
                session_id=request.session_id,
                question=request.question,
                error_message=error_message,
                response_time_ms=response_time_ms,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing query: {str(e)}",
            )
    
    # Calculate response time
    response_time_ms = int((time.time() - start_time) * 1000)
    
    # Log successful query
    await analytics.log_query(
        user_id=current_user.id,
        session_id=request.session_id,
        question=request.question,
        answer=answer,
        sources_count=len(sources),
        response_time_ms=response_time_ms,
        was_cached=was_cached,
    )
    
    # Store assistant response
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        sources=json.dumps(sources) if sources else None,
    )
    db.add(assistant_message)
    
    return QueryResponse(
        answer=answer,
        sources=sources,
        session_id=request.session_id,
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryResponse:
    """
    Get chat history for a specific session.
    
    Returns all messages in chronological order.
    """
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.session_id == session_id)
        .where(Conversation.user_id == current_user.id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        return ChatHistoryResponse(session_id=session_id, messages=[])
    
    messages = []
    for msg in sorted(conversation.messages, key=lambda m: m.created_at):
        # Parse sources - handle both old format (list of strings) and new format (list of dicts)
        sources = None
        if msg.sources:
            sources_data = json.loads(msg.sources)
            # Convert old format (strings) to new format (Source objects)
            if sources_data and isinstance(sources_data[0], str):
                # Old format: list of URL strings
                sources = [{"url": url, "name": url.split('/')[-1].split('?')[0] or "Document"} for url in sources_data]
            else:
                # New format: already list of dicts
                sources = sources_data
        
        messages.append(MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            sources=sources,
            created_at=msg.created_at,
        ))
    
    return ChatHistoryResponse(session_id=session_id, messages=messages)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> SessionListResponse:
    """
    List all chat sessions for the current user.
    
    Returns sessions with summary info, ordered by most recent activity.
    """
    from sqlalchemy import func, desc
    
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.user_id == current_user.id)
        .order_by(desc(Conversation.created_at))
        .limit(limit)
    )
    conversations = result.scalars().all()
    
    sessions = []
    for conv in conversations:
        # Get the last user message as preview
        user_messages = [m for m in conv.messages if m.role == 'user']
        last_message = user_messages[-1].content[:100] if user_messages else None
        
        # Get the latest message time for last_activity
        if conv.messages:
            last_activity = max(m.created_at for m in conv.messages)
        else:
            last_activity = conv.created_at
        
        sessions.append(SessionSummary(
            session_id=conv.session_id,
            message_count=len(conv.messages),
            last_message=last_message,
            last_activity=last_activity,
            created_at=conv.created_at,
        ))
    
    return SessionListResponse(sessions=sessions)


@router.post("/session")
async def create_session(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a new chat session and return the session ID."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    return {"session_id": session_id}
