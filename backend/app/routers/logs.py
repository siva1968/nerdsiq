"""
Router for log management endpoints
"""
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.models.user import User
from app.routers.auth import get_current_user
from app.services.monitoring_service import EmailNotifier


router = APIRouter()


@router.get("/dates")
async def get_log_dates(current_user: User = Depends(get_current_user)) -> dict:
    """Get all available log dates."""
    try:
        log_dir = Path("daily_logs")
        if not log_dir.exists():
            return {"dates": []}
        
        dates = []
        for log_file in log_dir.glob("indexing_*.log"):
            try:
                date_str = log_file.stem.replace("indexing_", "")
                log_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                dates.append(log_date.isoformat())
            except ValueError:
                continue
        
        # Sort dates in descending order (newest first)
        dates.sort(reverse=True)
        
        logger.info(f"Found {len(dates)} log dates")
        return {"dates": dates}
        
    except Exception as e:
        logger.error(f"Error getting log dates: {e}")
        raise HTTPException(status_code=500, detail="Failed to get log dates")


@router.get("/daily/{log_date}")
async def get_daily_log(
    log_date: str, 
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get daily log content and status for a specific date."""
    try:
        # Validate date format
        try:
            target_date = datetime.strptime(log_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        log_dir = Path("daily_logs")
        
        # Read log file
        log_file = log_dir / f"indexing_{log_date}.log"
        log_content = None
        
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
            except Exception as e:
                logger.warning(f"Could not read log file for {log_date}: {e}")
        
        # Read status file
        status_file = log_dir / f"status_{log_date}.json"
        status_data = None
        
        if status_file.exists():
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not read status file for {log_date}: {e}")
        
        if not log_content and not status_data:
            raise HTTPException(status_code=404, detail=f"No log data found for {log_date}")
        
        return {
            "date": log_date,
            "log_content": log_content,
            "status": status_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting daily log for {log_date}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get daily log")


@router.get("/weekly")
async def get_weekly_report(
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get weekly report data."""
    try:
        if end_date:
            try:
                target_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
        else:
            target_end_date = date.today()
        
        start_date = target_end_date - timedelta(days=6)  # 7 days total
        
        log_dir = Path("daily_logs")
        daily_reports = []
        
        # Collect data for each day
        current_date = start_date
        while current_date <= target_end_date:
            date_str = current_date.isoformat()
            status_file = log_dir / f"status_{date_str}.json"
            
            day_data = {
                "date": date_str,
                "total_files_processed": 0,
                "successful_files": 0,
                "failed_files": 0,
                "total_chunks_added": 0
            }
            
            if status_file.exists():
                try:
                    with open(status_file, 'r', encoding='utf-8') as f:
                        status = json.load(f)
                        day_data.update({
                            "total_files_processed": status.get('total_files_processed', 0),
                            "successful_files": status.get('successful_files', 0), 
                            "failed_files": status.get('failed_files', 0),
                            "total_chunks_added": status.get('total_chunks_added', 0)
                        })
                except Exception as e:
                    logger.warning(f"Could not read status file for {date_str}: {e}")
            
            daily_reports.append(day_data)
            current_date += timedelta(days=1)
        
        # Calculate totals
        totals = {
            "days_with_activity": len([d for d in daily_reports if d["total_files_processed"] > 0]),
            "total_files": sum(d["total_files_processed"] for d in daily_reports),
            "successful_files": sum(d["successful_files"] for d in daily_reports),
            "failed_files": sum(d["failed_files"] for d in daily_reports),
            "total_chunks": sum(d["total_chunks_added"] for d in daily_reports)
        }
        
        return {
            "date_range": {
                "start": start_date.isoformat(),
                "end": target_end_date.isoformat()
            },
            "daily_reports": daily_reports,
            "totals": totals
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate weekly report")


@router.post("/test-email")
async def test_email_notification(current_user: User = Depends(get_current_user)) -> dict:
    """Test email notification functionality."""
    try:
        email_notifier = EmailNotifier()
        
        if not email_notifier.enabled:
            raise HTTPException(
                status_code=400, 
                detail="Email notifications not configured. Check SMTP settings."
            )
        
        test_subject = f"NerdsIQ Test Email - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        test_message = f"""
NerdsIQ Email Test

This is a test email sent from the WordPress admin panel to verify email notification functionality.

Test initiated by: {current_user.email}
Test time: {datetime.now().isoformat()}

If you receive this email, the notification system is working correctly!

System Information:
- SMTP Server: {email_notifier.smtp_server}
- From Email: {email_notifier.from_email}
- Recipients: {len(email_notifier.notification_emails)} configured

---
NerdsIQ Monitoring System
        """.strip()
        
        success = email_notifier.send_alert(test_subject, test_message)
        
        if success:
            logger.info(f"Test email sent successfully by {current_user.email}")
            return {
                "message": "Test email sent successfully!",
                "recipients": email_notifier.notification_emails,
                "smtp_server": email_notifier.smtp_server
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send test email")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test email")


@router.get("/status")
async def get_monitoring_status(current_user: User = Depends(get_current_user)) -> dict:
    """Get current monitoring system status."""
    try:
        log_dir = Path("daily_logs")
        email_notifier = EmailNotifier()
        
        # Check recent activity
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        today_status_file = log_dir / f"status_{today.isoformat()}.json"
        yesterday_status_file = log_dir / f"status_{yesterday.isoformat()}.json"
        
        status_info = {
            "monitoring_enabled": True,
            "log_directory_exists": log_dir.exists(),
            "email_configured": email_notifier.enabled,
            "recent_activity": {
                "today": today_status_file.exists(),
                "yesterday": yesterday_status_file.exists()
            }
        }
        
        if email_notifier.enabled:
            status_info["email_config"] = {
                "smtp_server": email_notifier.smtp_server,
                "from_email": email_notifier.from_email,
                "recipients_count": len(email_notifier.notification_emails)
            }
        
        return status_info
        
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get monitoring status")