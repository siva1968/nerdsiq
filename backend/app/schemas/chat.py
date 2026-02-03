"""Chat and query schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Source document information."""
    
    url: str = Field(..., description="Document URL")
    name: str = Field(..., description="Document name")


class QueryRequest(BaseModel):
    """RAG query request schema."""

    question: str = Field(..., min_length=1, max_length=1000, description="User question")
    session_id: str = Field(..., description="Session ID for conversation continuity")
    model: str | None = Field(default=None, description="OpenAI model to use (e.g., gpt-4o, gpt-4o-mini)")


class QueryResponse(BaseModel):
    """RAG query response schema."""

    answer: str
    sources: list[Source] = Field(default_factory=list, description="Source documents")
    session_id: str


class MessageResponse(BaseModel):
    """Individual message response schema."""

    id: int
    role: str  # 'user' or 'assistant'
    content: str
    sources: list[Source] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    """Chat history response schema."""

    session_id: str
    messages: list[MessageResponse]


class SessionSummary(BaseModel):
    """Summary of a chat session for listing."""

    session_id: str
    message_count: int
    last_message: str | None = None
    last_activity: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    """List of user sessions."""

    sessions: list[SessionSummary]
