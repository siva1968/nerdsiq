"""Analytics service for tracking and reporting user activity."""

import json
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import QueryLog, DailyStats, UserActivity
from app.models.user import User


class AnalyticsService:
    """Service for tracking and retrieving analytics data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_query(
        self,
        user_id: int,
        session_id: str,
        question: str,
        answer: str | None = None,
        sources_count: int = 0,
        response_time_ms: int | None = None,
        tokens_used: int | None = None,
        was_cached: bool = False,
        error_message: str | None = None,
    ) -> QueryLog:
        """Log a user query with metrics."""
        query_log = QueryLog(
            user_id=user_id,
            session_id=session_id,
            question=question,
            answer=answer,
            sources_count=sources_count,
            response_time_ms=response_time_ms,
            tokens_used=tokens_used,
            was_cached=was_cached,
            error_message=error_message,
        )
        self.db.add(query_log)
        await self.db.commit()
        await self.db.refresh(query_log)
        return query_log

    async def log_activity(
        self,
        user_id: int,
        activity_type: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        extra_data: dict | None = None,
    ) -> UserActivity:
        """Log a user activity event."""
        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=json.dumps(extra_data) if extra_data else None,
        )
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

    async def get_dashboard_stats(self, days: int = 30) -> dict[str, Any]:
        """Get dashboard statistics for the admin panel."""
        since = datetime.utcnow() - timedelta(days=days)

        # Total queries
        total_queries_result = await self.db.execute(
            select(func.count(QueryLog.id)).where(QueryLog.created_at >= since)
        )
        total_queries = total_queries_result.scalar() or 0

        # Unique users
        unique_users_result = await self.db.execute(
            select(func.count(distinct(QueryLog.user_id))).where(QueryLog.created_at >= since)
        )
        unique_users = unique_users_result.scalar() or 0

        # Total sessions
        total_sessions_result = await self.db.execute(
            select(func.count(distinct(QueryLog.session_id))).where(QueryLog.created_at >= since)
        )
        total_sessions = total_sessions_result.scalar() or 0

        # Average response time
        avg_response_result = await self.db.execute(
            select(func.avg(QueryLog.response_time_ms)).where(
                QueryLog.created_at >= since,
                QueryLog.response_time_ms.isnot(None)
            )
        )
        avg_response_time = avg_response_result.scalar()
        avg_response_time = round(avg_response_time, 2) if avg_response_time else 0

        # Cached queries
        cached_result = await self.db.execute(
            select(func.count(QueryLog.id)).where(
                QueryLog.created_at >= since,
                QueryLog.was_cached == True
            )
        )
        cached_queries = cached_result.scalar() or 0

        # Failed queries
        failed_result = await self.db.execute(
            select(func.count(QueryLog.id)).where(
                QueryLog.created_at >= since,
                QueryLog.error_message.isnot(None)
            )
        )
        failed_queries = failed_result.scalar() or 0

        # Cache hit rate
        cache_hit_rate = round((cached_queries / total_queries * 100), 1) if total_queries > 0 else 0

        # Success rate
        success_rate = round(((total_queries - failed_queries) / total_queries * 100), 1) if total_queries > 0 else 100

        return {
            "period_days": days,
            "total_queries": total_queries,
            "unique_users": unique_users,
            "total_sessions": total_sessions,
            "avg_response_time_ms": avg_response_time,
            "cached_queries": cached_queries,
            "cache_hit_rate": cache_hit_rate,
            "failed_queries": failed_queries,
            "success_rate": success_rate,
        }

    async def get_queries_per_day(self, days: int = 30) -> list[dict[str, Any]]:
        """Get query count per day for charting."""
        since = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.date(QueryLog.created_at).label("date"),
                func.count(QueryLog.id).label("count"),
            )
            .where(QueryLog.created_at >= since)
            .group_by(func.date(QueryLog.created_at))
            .order_by(func.date(QueryLog.created_at))
        )
        
        rows = result.all()
        return [{"date": str(row.date), "count": row.count} for row in rows]

    async def get_top_users(self, days: int = 30, limit: int = 10) -> list[dict[str, Any]]:
        """Get top users by query count."""
        since = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(
                QueryLog.user_id,
                User.email,
                User.full_name,
                func.count(QueryLog.id).label("query_count"),
            )
            .join(User, QueryLog.user_id == User.id)
            .where(QueryLog.created_at >= since)
            .group_by(QueryLog.user_id, User.email, User.full_name)
            .order_by(func.count(QueryLog.id).desc())
            .limit(limit)
        )
        
        rows = result.all()
        return [
            {
                "user_id": row.user_id,
                "email": row.email,
                "full_name": row.full_name,
                "query_count": row.query_count,
            }
            for row in rows
        ]

    async def get_popular_questions(self, days: int = 30, limit: int = 10) -> list[dict[str, Any]]:
        """Get most frequently asked questions (simplified by first 100 chars)."""
        since = datetime.utcnow() - timedelta(days=days)

        # Get recent questions and count similar ones
        result = await self.db.execute(
            select(
                QueryLog.question,
                func.count(QueryLog.id).label("count"),
                func.max(QueryLog.created_at).label("last_asked"),
            )
            .where(QueryLog.created_at >= since)
            .group_by(QueryLog.question)
            .order_by(func.count(QueryLog.id).desc())
            .limit(limit)
        )
        
        rows = result.all()
        return [
            {
                "question": row.question[:200] + "..." if len(row.question) > 200 else row.question,
                "count": row.count,
                "last_asked": row.last_asked.isoformat() if row.last_asked else None,
            }
            for row in rows
        ]

    async def get_hourly_distribution(self, days: int = 30) -> list[dict[str, Any]]:
        """Get query distribution by hour of day."""
        since = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.extract("hour", QueryLog.created_at).label("hour"),
                func.count(QueryLog.id).label("count"),
            )
            .where(QueryLog.created_at >= since)
            .group_by(func.extract("hour", QueryLog.created_at))
            .order_by(func.extract("hour", QueryLog.created_at))
        )
        
        rows = result.all()
        # Fill in missing hours with 0
        hourly_data = {int(row.hour): row.count for row in rows}
        return [{"hour": h, "count": hourly_data.get(h, 0)} for h in range(24)]

    async def get_user_stats(self, user_id: int, days: int = 30) -> dict[str, Any]:
        """Get statistics for a specific user."""
        since = datetime.utcnow() - timedelta(days=days)

        # Query count
        query_count_result = await self.db.execute(
            select(func.count(QueryLog.id)).where(
                QueryLog.user_id == user_id,
                QueryLog.created_at >= since
            )
        )
        query_count = query_count_result.scalar() or 0

        # Session count
        session_count_result = await self.db.execute(
            select(func.count(distinct(QueryLog.session_id))).where(
                QueryLog.user_id == user_id,
                QueryLog.created_at >= since
            )
        )
        session_count = session_count_result.scalar() or 0

        # Average response time
        avg_response_result = await self.db.execute(
            select(func.avg(QueryLog.response_time_ms)).where(
                QueryLog.user_id == user_id,
                QueryLog.created_at >= since,
                QueryLog.response_time_ms.isnot(None)
            )
        )
        avg_response_time = avg_response_result.scalar()
        avg_response_time = round(avg_response_time, 2) if avg_response_time else 0

        # Last activity
        last_activity_result = await self.db.execute(
            select(func.max(QueryLog.created_at)).where(QueryLog.user_id == user_id)
        )
        last_activity = last_activity_result.scalar()

        return {
            "user_id": user_id,
            "period_days": days,
            "query_count": query_count,
            "session_count": session_count,
            "avg_response_time_ms": avg_response_time,
            "last_activity": last_activity.isoformat() if last_activity else None,
        }

    async def get_recent_queries(
        self, 
        limit: int = 50, 
        user_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Get recent queries with optional user filter."""
        query = (
            select(
                QueryLog.id,
                QueryLog.user_id,
                User.email,
                QueryLog.question,
                QueryLog.response_time_ms,
                QueryLog.was_cached,
                QueryLog.error_message,
                QueryLog.created_at,
            )
            .join(User, QueryLog.user_id == User.id)
            .order_by(QueryLog.created_at.desc())
            .limit(limit)
        )
        
        if user_id:
            query = query.where(QueryLog.user_id == user_id)

        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "id": row.id,
                "user_id": row.user_id,
                "email": row.email,
                "question": row.question[:100] + "..." if len(row.question) > 100 else row.question,
                "response_time_ms": row.response_time_ms,
                "was_cached": row.was_cached,
                "had_error": row.error_message is not None,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    async def update_daily_stats(self, target_date: date | None = None) -> DailyStats:
        """Update or create daily stats for a given date."""
        if target_date is None:
            target_date = date.today()

        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())

        # Get stats for the day
        stats_result = await self.db.execute(
            select(
                func.count(QueryLog.id).label("total_queries"),
                func.count(distinct(QueryLog.user_id)).label("unique_users"),
                func.count(distinct(QueryLog.session_id)).label("total_sessions"),
                func.avg(QueryLog.response_time_ms).label("avg_response_time"),
                func.sum(func.cast(QueryLog.was_cached, Integer)).label("cached_queries"),
                func.sum(func.cast(QueryLog.error_message.isnot(None), Integer)).label("failed_queries"),
                func.sum(func.coalesce(QueryLog.tokens_used, 0)).label("total_tokens"),
            ).where(
                QueryLog.created_at >= start_of_day,
                QueryLog.created_at <= end_of_day
            )
        )
        row = stats_result.one()

        # Check if daily stats exist
        existing_result = await self.db.execute(
            select(DailyStats).where(DailyStats.date == target_date)
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.total_queries = row.total_queries or 0
            existing.unique_users = row.unique_users or 0
            existing.total_sessions = row.total_sessions or 0
            existing.avg_response_time_ms = float(row.avg_response_time) if row.avg_response_time else None
            existing.cached_queries = row.cached_queries or 0
            existing.failed_queries = row.failed_queries or 0
            existing.total_tokens_used = row.total_tokens or 0
            await self.db.commit()
            return existing
        else:
            daily_stats = DailyStats(
                date=target_date,
                total_queries=row.total_queries or 0,
                unique_users=row.unique_users or 0,
                total_sessions=row.total_sessions or 0,
                avg_response_time_ms=float(row.avg_response_time) if row.avg_response_time else None,
                cached_queries=row.cached_queries or 0,
                failed_queries=row.failed_queries or 0,
                total_tokens_used=row.total_tokens or 0,
            )
            self.db.add(daily_stats)
            await self.db.commit()
            await self.db.refresh(daily_stats)
            return daily_stats
