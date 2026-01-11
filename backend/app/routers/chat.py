"""Chat router for RAG queries."""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.chat import ChatHistoryResponse, MessageResponse, QueryRequest, QueryResponse
from app.services.rag_service import RAGService

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_rag(
    request: QueryRequest,
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
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty",
        )
    
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
    
    # Process RAG query
    try:
        rag_service = RAGService()
        answer, sources = await rag_service.query(
            question=request.question,
            session_id=request.session_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}",
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
    
    messages = [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            sources=json.loads(msg.sources) if msg.sources else None,
            created_at=msg.created_at,
        )
        for msg in sorted(conversation.messages, key=lambda m: m.created_at)
    ]
    
    return ChatHistoryResponse(session_id=session_id, messages=messages)


@router.post("/session")
async def create_session(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a new chat session and return the session ID."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    return {"session_id": session_id}
