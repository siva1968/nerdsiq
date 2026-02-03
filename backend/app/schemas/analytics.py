"""Analytics schemas for API requests and responses."""

from datetime import datetime
from pydantic import BaseModel, Field


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response."""
    
    period_days: int
    total_queries: int
    unique_users: int
    total_sessions: int
    avg_response_time_ms: float
    cached_queries: int
    cache_hit_rate: float
    failed_queries: int
    success_rate: float


class QueryPerDayItem(BaseModel):
    """Single day query count."""
    
    date: str
    count: int


class TopUserItem(BaseModel):
    """Top user by query count."""
    
    user_id: int
    email: str
    full_name: str | None
    query_count: int


class PopularQuestionItem(BaseModel):
    """Popular question item."""
    
    question: str
    count: int
    last_asked: str | None


class HourlyDistributionItem(BaseModel):
    """Hourly distribution item."""
    
    hour: int = Field(..., ge=0, le=23)
    count: int


class UserStatsResponse(BaseModel):
    """User statistics response."""
    
    user_id: int
    period_days: int
    query_count: int
    session_count: int
    avg_response_time_ms: float
    last_activity: str | None


class RecentQueryItem(BaseModel):
    """Recent query item."""
    
    id: int
    user_id: int
    email: str
    question: str
    response_time_ms: int | None
    was_cached: bool
    had_error: bool
    created_at: str


class AnalyticsOverviewResponse(BaseModel):
    """Complete analytics overview for dashboard."""
    
    stats: DashboardStatsResponse
    queries_per_day: list[QueryPerDayItem]
    top_users: list[TopUserItem]
    popular_questions: list[PopularQuestionItem]
    hourly_distribution: list[HourlyDistributionItem]
