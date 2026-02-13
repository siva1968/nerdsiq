"""Daily logging and email notification service for NerdsIQ indexing."""

import os
import smtplib
import json
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional
import json
import asyncio
from loguru import logger

from app.config import settings


class DailyLogger:
    """Handles daily log files and status tracking."""
    
    def __init__(self, log_dir: str = "daily_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.current_date = date.today()
        self.log_file = self.log_dir / f"indexing_{self.current_date.strftime('%Y-%m-%d')}.log"
        self.status_file = self.log_dir / f"status_{self.current_date.strftime('%Y-%m-%d')}.json"
        
        # Initialize status tracking
        self.session_stats = {
            "date": self.current_date.isoformat(),
            "session_start": datetime.now().isoformat(),
            "session_end": None,
            "total_files_processed": 0,
            "successful_files": 0,
            "failed_files": 0,
            "total_chunks_added": 0,
            "errors": [],
            "summary": "",
            "collection_stats_before": {},
            "collection_stats_after": {},
        }
    
    def log_info(self, message: str) -> None:
        """Log info message to daily log file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] INFO: {message}\n"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        logger.info(message)
    
    def log_error(self, message: str, error: Optional[Exception] = None) -> None:
        """Log error message to daily log file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_msg = f"{message} - {str(error)}" if error else message
        log_entry = f"[{timestamp}] ERROR: {error_msg}\n"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        # Add to session errors
        self.session_stats["errors"].append({
            "timestamp": timestamp,
            "message": error_msg
        })
        
        logger.error(message)
    
    def log_success(self, file_name: str, chunks_added: int) -> None:
        """Log successful file processing."""
        self.session_stats["successful_files"] += 1
        self.session_stats["total_chunks_added"] += chunks_added
        self.log_info(f"✅ Successfully indexed {file_name}: {chunks_added} chunks")
    
    def log_failure(self, file_name: str, error: str) -> None:
        """Log failed file processing."""
        self.session_stats["failed_files"] += 1
        self.log_error(f"❌ Failed to index {file_name}: {error}")
    
    def update_collection_stats(self, stage: str, stats: dict) -> None:
        """Update collection statistics."""
        if stage == "before":
            self.session_stats["collection_stats_before"] = stats
        elif stage == "after":
            self.session_stats["collection_stats_after"] = stats
    
    def finalize_session(self) -> dict:
        """Finalize the session and return summary."""
        self.session_stats["session_end"] = datetime.now().isoformat()
        self.session_stats["total_files_processed"] = (
            self.session_stats["successful_files"] + 
            self.session_stats["failed_files"]
        )
        
        # Create summary
        duration = datetime.fromisoformat(self.session_stats["session_end"]) - \
                  datetime.fromisoformat(self.session_stats["session_start"])
        
        summary = f"""
📊 NerdsIQ Indexing Session Summary - {self.current_date}
=======================================================

⏱️  Duration: {str(duration).split('.')[0]}
📁 Files Processed: {self.session_stats['total_files_processed']}
✅ Successful: {self.session_stats['successful_files']}
❌ Failed: {self.session_stats['failed_files']}
📄 Total Chunks Added: {self.session_stats['total_chunks_added']:,}

🗄️  Collection Stats:
   Before: {self.session_stats['collection_stats_before'].get('points_count', 'N/A')} points
   After:  {self.session_stats['collection_stats_after'].get('points_count', 'N/A')} points
   
{'❌ Errors Encountered:' if self.session_stats['errors'] else '✅ No Errors Encountered'}
"""
        
        if self.session_stats['errors']:
            summary += "\n"
            for i, error in enumerate(self.session_stats['errors'][:5], 1):  # Show first 5 errors
                summary += f"   {i}. {error['message']}\n"
            
            if len(self.session_stats['errors']) > 5:
                summary += f"   ... and {len(self.session_stats['errors']) - 5} more errors\n"
        
        self.session_stats["summary"] = summary
        
        # Save status file
        with open(self.status_file, "w", encoding="utf-8") as f:
            json.dump(self.session_stats, f, indent=2, ensure_ascii=False)
        
        # Log final summary
        self.log_info("Session Summary:\n" + summary)
        
        return self.session_stats


class EmailNotifier:
    """Handles email notifications via Zepto Mail API or SMTP."""
    
    def __init__(self):
        self.api_key = settings.zeptomail_api_key
        self.api_url = settings.zeptomail_api_url
        self.use_api = settings.use_zeptomail_api and bool(self.api_key)
        
        # SMTP fallback configuration
        self.smtp_server = settings.smtp_server or "smtp.zeptomail.com"
        self.smtp_port = settings.smtp_port or 587
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        
        # Email settings
        self.from_email = settings.from_email
        self.notification_emails = settings.notification_emails_list
        
        # Check if any email method is enabled
        self.enabled = bool(
            (self.use_api and self.api_key and self.from_email and self.notification_emails) or
            (not self.use_api and self.smtp_username and self.smtp_password and self.notification_emails)
        )
        
        if not self.enabled:
            logger.warning("Email notifications disabled - missing Zepto Mail configuration")
        elif self.use_api:
            logger.info("Email notifications enabled via Zepto Mail API")
        else:
            logger.info("Email notifications enabled via Zepto Mail SMTP")
    
    def send_email_api(self, subject: str, html_body: str, text_body: str = None) -> bool:
        """Send email using Zepto Mail REST API."""
        try:
            # Prepare recipients
            recipients = []
            for email in self.notification_emails:
                recipients.append({
                    "email_address": {
                        "address": email,
                        "name": email.split("@")[0].title()
                    }
                })
            
            # Prepare payload
            payload = {
                "from": {
                    "address": self.from_email,
                    "name": "NerdsIQ System"
                },
                "to": recipients,
                "subject": subject,
                "htmlbody": html_body
            }
            
            # Add text body if provided
            if text_body:
                payload["textbody"] = text_body
            
            # Send via API
            headers = {
                "accept": "application/json",
                "authorization": self.api_key,  # API key already includes "Zoho-enczapikey" prefix
                "content-type": "application/json",
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:  # 201 is "Created" for email requests
                    result = response.json()
                    logger.info(f"✅ Email sent via Zepto Mail API: {result.get('message', 'Success')}")
                    return True
                else:
                    logger.error(f"❌ Zepto Mail API error: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Failed to send email via Zepto Mail API: {e}")
            return False
    
    def send_email_smtp(self, subject: str, html_body: str, text_body: str = None) -> bool:
        """Send email using SMTP as fallback."""
        try:
            # Create multipart message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = ", ".join(self.notification_emails)
            msg['Subject'] = subject
            
            # Add text part
            if text_body:
                text_part = MIMEText(text_body, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML part
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info("✅ Email sent via Zepto Mail SMTP")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email via SMTP: {e}")
            return False
    
    def send_daily_report(self, daily_stats: dict, log_file: Path) -> bool:
        """Send daily indexing report via Zepto Mail."""
        if not self.enabled:
            logger.info("Email notifications disabled - skipping daily report")
            return False
        
        try:
            # Create formatted email content
            subject = f"NerdsIQ Daily Report - {daily_stats.get('date', 'Unknown')}"
            
            # Create plain text version
            text_body = f"""
NerdsIQ Daily Report - {daily_stats.get('date', 'Unknown')}

Summary:
{daily_stats.get('summary', 'No summary available')}

Statistics:
• Files Processed: {daily_stats.get('total_files_processed', 0):,}
• Successful: {daily_stats.get('successful_files', 0):,}  
• Failed: {daily_stats.get('failed_files', 0):,}
• Chunks Added: {daily_stats.get('total_chunks_added', 0):,}

Generated by NerdsIQ Monitoring System
            """
            
            # Send email using preferred method (API or SMTP)
            if self.use_api:
                # Use simple HTML for API
                html_body = text_body.replace('\n', '<br>')
                success = self.send_email_api(subject, f"<html><body><pre>{html_body}</pre></body></html>", text_body)
            else:
                success = self.send_email_smtp(subject, f"<html><body><pre>{text_body}</pre></body></html>", text_body)
            
            if success:
                logger.info(f"✅ Daily report sent to {len(self.notification_emails)} recipients")
                return True
            else:
                logger.error("❌ Failed to send daily report")
                return False
            
        except Exception as e:
            logger.error(f"❌ Failed to send daily report: {e}")
            return False
    
    def send_alert(self, subject: str, message: str, is_html: bool = False) -> bool:
        """Send immediate alert email via Zepto Mail."""
        if not self.enabled:
            return False
        
        try:
            # Use preferred method (API or SMTP)
            if self.use_api:
                if is_html:
                    html_body = message
                    # Create plain text fallback
                    import re
                    text_body = re.sub(r'<[^>]+>', '', message)
                else:
                    text_body = message
                    html_body = f"<html><body><pre>{message}</pre></body></html>"
                
                success = self.send_email_api(f"NerdsIQ Alert: {subject}", html_body, text_body)
                if success:
                    logger.info(f"✅ Alert sent via Zepto Mail API: {subject}")
                    return True
                else:
                    logger.error(f"❌ Failed to send alert via Zepto Mail API: {subject}")
                    return False
            else:
                # Fallback to SMTP
                if is_html:
                    msg = MIMEMultipart('alternative')
                    msg['From'] = self.from_email
                    msg['To'] = ", ".join(self.notification_emails)
                    msg['Subject'] = f"NerdsIQ Alert: {subject}"
                    
                    # Add HTML version
                    html_part = MIMEText(message, 'html', 'utf-8')
                    msg.attach(html_part)
                    
                    # Add plain text fallback
                    import re
                    plain_text = re.sub(r'<[^>]+>', '', message)
                    text_part = MIMEText(plain_text, 'plain', 'utf-8')
                    msg.attach(text_part)
                else:
                    msg = MIMEText(message, 'plain', 'utf-8')
                    msg['From'] = self.from_email
                    msg['To'] = ", ".join(self.notification_emails)
                    msg['Subject'] = f"NerdsIQ Alert: {subject}"
                
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
                
                logger.info(f"✅ Alert sent via SMTP: {subject}")
                return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send alert via Zepto Mail: {e}")
            return False


class IndexingMonitor:
    """Combined monitoring service for indexing operations."""
    
    def __init__(self):
        self.daily_logger = DailyLogger()
        self.email_notifier = EmailNotifier()
        self.session_active = False
    
    def start_session(self, operation_type: str = "incremental_indexing") -> None:
        """Start a new monitoring session."""
        self.session_active = True
        self.daily_logger.log_info(f"🚀 Starting {operation_type} session")
    
    def log_collection_stats(self, stage: str, stats: dict) -> None:
        """Log collection statistics."""
        points_count = stats.get('points_count', 0)
        self.daily_logger.update_collection_stats(stage, stats)
        self.daily_logger.log_info(f"📊 Collection stats ({stage}): {points_count:,} points")
    
    def log_file_success(self, file_name: str, chunks: int) -> None:
        """Log successful file processing."""
        self.daily_logger.log_success(file_name, chunks)
    
    def log_file_error(self, file_name: str, error: str) -> None:
        """Log file processing error."""
        self.daily_logger.log_failure(file_name, error)
    
    def log_info(self, message: str) -> None:
        """Log general information."""
        self.daily_logger.log_info(message)
    
    def log_error(self, message: str, error: Optional[Exception] = None) -> None:
        """Log error with optional exception."""
        self.daily_logger.log_error(message, error)
    
    def end_session(self, send_email: bool = True) -> dict:
        """End monitoring session and optionally send report."""
        if not self.session_active:
            return {}
        
        self.session_active = False
        final_stats = self.daily_logger.finalize_session()
        
        # Send email report if enabled
        if send_email:
            self.email_notifier.send_daily_report(
                final_stats, 
                self.daily_logger.log_file
            )
        
        return final_stats
    
    def send_alert_if_needed(self, stats: dict) -> None:
        """Send alert email if there are critical issues."""
        if stats.get('failed_files', 0) > stats.get('successful_files', 0):
            # More failures than successes
            self.email_notifier.send_alert(
                "Critical Indexing Failures",
                f"Indexing session had {stats['failed_files']} failures vs {stats['successful_files']} successes. Please check the logs."
            )
        elif len(stats.get('errors', [])) > 10:
            # Too many errors
            self.email_notifier.send_alert(
                "High Error Rate",
                f"Indexing session encountered {len(stats['errors'])} errors. System may need attention."
            )


# Global monitor instance
indexing_monitor = IndexingMonitor()