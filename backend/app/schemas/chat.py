"""Chat and query schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """RAG query request schema."""

    question: str = Field(..., min_length=1, max_length=1000, description="User question")
    session_id: str = Field(..., description="Session ID for conversation continuity")


class QueryResponse(BaseModel):
    """RAG query response schema."""

    answer: str
    sources: list[str] = Field(default_factory=list, description="Source document URLs")
    session_id: str


class MessageResponse(BaseModel):
    """Individual message response schema."""

    id: int
    role: str  # 'user' or 'assistant'
    content: str
    sources: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    """Chat history response schema."""

    session_id: str
    messages: list[MessageResponse]
