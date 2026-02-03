"""Analytics API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    DashboardStatsResponse,
    QueryPerDayItem,
    TopUserItem,
    PopularQuestionItem,
    HourlyDistributionItem,
    UserStatsResponse,
    RecentQueryItem,
    AnalyticsOverviewResponse,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    """Dependency to get analytics service."""
    return AnalyticsService(db)


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """Get dashboard statistics for the specified period."""
    stats = await analytics.get_dashboard_stats(days=days)
    return DashboardStatsResponse(**stats)


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """Get complete analytics overview for dashboard."""
    stats = await analytics.get_dashboard_stats(days=days)
    queries_per_day = await analytics.get_queries_per_day(days=days)
    top_users = await analytics.get_top_users(days=days)
    popular_questions = await analytics.get_popular_questions(days=days)
    hourly_distribution = await analytics.get_hourly_distribution(days=days)

    return AnalyticsOverviewResponse(
        stats=DashboardStatsResponse(**stats),
        queries_per_day=[QueryPerDayItem(**q) for q in queries_per_day],
        top_users=[TopUserItem(**u) for u in top_users],
        popular_questions=[PopularQuestionItem(**p) for p in popular_questions],
        hourly_distribution=[HourlyDistributionItem(**h) for h in hourly_distribution],
    )


@router.get("/queries-per-day", response_model=list[QueryPerDayItem])
async def get_queries_per_day(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """Get query count per day for the specified period."""
    data = await analytics.get_queries_per_day(days=days)
    return [QueryPerDayItem(**item) for item in data]


@router.get("/top-users", response_model=list[TopUserItem])
async def get_top_users(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """Get top users by query count."""
    data = await analytics.get_top_users(days=days, limit=limit)
    return [TopUserItem(**item) for item in data]


@router.get("/popular-questions", response_model=list[PopularQuestionItem])
async def get_popular_questions(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """Get most popular questions."""
    data = await analytics.get_popular_questions(days=days, limit=limit)
    return [PopularQuestionItem(**item) for item in data]


@router.get("/hourly-distribution", response_model=list[HourlyDistributionItem])
async def get_hourly_distribution(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """Get query distribution by hour of day."""
    data = await analytics.get_hourly_distribution(days=days)
    return [HourlyDistributionItem(**item) for item in data]


@router.get("/user/{user_id}", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: int,
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """Get statistics for a specific user."""
    data = await analytics.get_user_stats(user_id=user_id, days=days)
    return UserStatsResponse(**data)


@router.get("/my-stats", response_model=UserStatsResponse)
async def get_my_stats(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """Get statistics for the current user."""
    data = await analytics.get_user_stats(user_id=current_user.id, days=days)
    return UserStatsResponse(**data)


@router.get("/recent-queries", response_model=list[RecentQueryItem])
async def get_recent_queries(
    limit: int = Query(default=50, ge=1, le=500),
    user_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """Get recent queries with optional user filter."""
    data = await analytics.get_recent_queries(limit=limit, user_id=user_id)
    return [RecentQueryItem(**item) for item in data]
