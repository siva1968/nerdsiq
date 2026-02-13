#!/usr/bin/env python3
"""Daily log management and reporting tool for NerdsIQ indexing."""

import sys
import json
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import argparse

# Add the backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger
from app.services.monitoring_service import EmailNotifier


class LogManager:
    """Manages daily log files and provides reporting capabilities."""
    
    def __init__(self, log_dir: str = "daily_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
    
    def list_available_dates(self) -> List[date]:
        """List all dates with available log files."""
        dates = []
        for log_file in self.log_dir.glob("indexing_*.log"):
            try:
                date_str = log_file.stem.replace("indexing_", "")
                log_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                dates.append(log_date)
            except ValueError:
                continue
        
        return sorted(dates)
    
    def get_status_for_date(self, target_date: date) -> Optional[Dict]:
        """Get status information for a specific date."""
        status_file = self.log_dir / f"status_{target_date.strftime('%Y-%m-%d')}.json"
        
        if not status_file.exists():
            return None
        
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Could not read status file for {target_date}: {e}")
            return None
    
    def get_log_for_date(self, target_date: date) -> Optional[str]:
        """Get log content for a specific date."""
        log_file = self.log_dir / f"indexing_{target_date.strftime('%Y-%m-%d')}.log"
        
        if not log_file.exists():
            return None
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Could not read log file for {target_date}: {e}")
            return None
    
    def show_daily_summary(self, target_date: date) -> None:
        """Show summary for a specific date."""
        logger.info(f"📅 Daily Summary for {target_date}")
        logger.info("=" * 50)
        
        status = self.get_status_for_date(target_date)
        
        if not status:
            logger.warning("❌ No status data found for this date")
            return
        
        # Display summary
        print(status.get('summary', 'No summary available'))
        
        # Show error details if any
        errors = status.get('errors', [])
        if errors:
            logger.info(f"\n🔍 Error Details ({len(errors)} total):")
            for i, error in enumerate(errors[:10], 1):  # Show first 10 errors
                print(f"   {i}. [{error['timestamp']}] {error['message']}")
            
            if len(errors) > 10:
                print(f"   ... and {len(errors) - 10} more errors")
    
    def show_weekly_report(self, end_date: Optional[date] = None) -> None:
        """Show weekly summary report."""
        if end_date is None:
            end_date = date.today()
        
        start_date = end_date - timedelta(days=6)  # 7 days total
        
        logger.info(f"📊 Weekly Report: {start_date} to {end_date}")
        logger.info("=" * 60)
        
        total_files = 0
        total_successful = 0
        total_failed = 0
        total_chunks = 0
        days_with_data = 0
        
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            status = self.get_status_for_date(current_date)
            
            if status:
                days_with_data += 1
                total_files += status.get('total_files_processed', 0)
                total_successful += status.get('successful_files', 0)
                total_failed += status.get('failed_files', 0)
                total_chunks += status.get('total_chunks_added', 0)
                
                # Daily summary line
                success_rate = (status.get('successful_files', 0) / 
                              max(status.get('total_files_processed', 1), 1)) * 100
                
                status_icon = "✅" if status.get('failed_files', 0) == 0 else "⚠️"
                
                print(f"{current_date.strftime('%Y-%m-%d')}: {status_icon} "
                      f"{status.get('successful_files', 0):3d} files, "
                      f"{status.get('total_chunks_added', 0):5,d} chunks, "
                      f"{success_rate:5.1f}% success")
            else:
                print(f"{current_date.strftime('%Y-%m-%d')}: ⭕ No indexing activity")
        
        # Weekly totals
        print("\n" + "=" * 60)
        print(f"📊 Weekly Totals:")
        print(f"   Days with activity: {days_with_data}/7")
        print(f"   Total files processed: {total_files:,}")
        print(f"   Successful files: {total_successful:,}")
        print(f"   Failed files: {total_failed:,}")
        print(f"   Total chunks added: {total_chunks:,}")
        
        if total_files > 0:
            overall_success = (total_successful / total_files) * 100
            print(f"   Overall success rate: {overall_success:.1f}%")
    
    def clean_old_logs(self, days_to_keep: int = 30) -> None:
        """Clean log files older than specified days."""
        cutoff_date = date.today() - timedelta(days=days_to_keep)
        
        cleaned_files = []
        
        for log_file in self.log_dir.glob("*_*.log"):
            try:
                date_str = log_file.stem.split("_", 1)[1]
                log_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                if log_date < cutoff_date:
                    log_file.unlink()
                    cleaned_files.append(str(log_file))
                    
            except (ValueError, IndexError):
                continue
        
        for status_file in self.log_dir.glob("status_*.json"):
            try:
                date_str = status_file.stem.replace("status_", "")
                log_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                if log_date < cutoff_date:
                    status_file.unlink()
                    cleaned_files.append(str(status_file))
                    
            except ValueError:
                continue
        
        if cleaned_files:
            logger.info(f"🧹 Cleaned {len(cleaned_files)} old log files")
            for file in cleaned_files:
                logger.info(f"   Removed: {file}")
        else:
            logger.info("🧹 No old log files to clean")
    
    def export_logs(self, start_date: date, end_date: date, output_file: str) -> None:
        """Export logs for a date range to a file."""
        output_path = Path(output_file)
        
        exported_data = {
            "export_date": datetime.now().isoformat(),
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "daily_data": []
        }
        
        current_date = start_date
        while current_date <= end_date:
            status = self.get_status_for_date(current_date)
            log_content = self.get_log_for_date(current_date)
            
            if status or log_content:
                daily_entry = {
                    "date": current_date.isoformat(),
                    "status": status,
                    "log_content": log_content
                }
                exported_data["daily_data"].append(daily_entry)
            
            current_date += timedelta(days=1)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(exported_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📤 Exported logs to: {output_path}")
        logger.info(f"   Date range: {start_date} to {end_date}")
        logger.info(f"   Days included: {len(exported_data['daily_data'])}")


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description="NerdsIQ Daily Log Manager")
    parser.add_argument("command", choices=[
        "list", "show", "weekly", "clean", "export", "email-test"
    ], help="Command to execute")
    
    parser.add_argument("--date", type=str, help="Date in YYYY-MM-DD format")
    parser.add_argument("--days", type=int, default=30, help="Number of days for clean command")
    parser.add_argument("--output", type=str, help="Output file for export command")
    parser.add_argument("--start-date", type=str, help="Start date for export (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date for export (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    log_manager = LogManager()
    
    if args.command == "list":
        dates = log_manager.list_available_dates()
        if dates:
            logger.info(f"📋 Available log dates ({len(dates)} total):")
            for log_date in dates[-10:]:  # Show last 10 dates
                logger.info(f"   {log_date}")
            if len(dates) > 10:
                logger.info(f"   ... and {len(dates) - 10} more dates")
        else:
            logger.info("📋 No log files found")
    
    elif args.command == "show":
        if not args.date:
            target_date = date.today()
        else:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        
        log_manager.show_daily_summary(target_date)
    
    elif args.command == "weekly":
        if args.date:
            end_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        else:
            end_date = date.today()
        
        log_manager.show_weekly_report(end_date)
    
    elif args.command == "clean":
        log_manager.clean_old_logs(args.days)
    
    elif args.command == "export":
        if not all([args.start_date, args.end_date, args.output]):
            logger.error("Export requires --start-date, --end-date, and --output arguments")
            return
        
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        
        log_manager.export_logs(start_date, end_date, args.output)
    
    elif args.command == "email-test":
        logger.info("📧 Testing email notification...")
        email_notifier = EmailNotifier()
        
        if not email_notifier.enabled:
            logger.warning("❌ Email notifications not configured")
            logger.info("Configure these environment variables:")
            logger.info("   SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD")
            logger.info("   FROM_EMAIL, NOTIFICATION_EMAILS")
            return
        
        success = email_notifier.send_alert(
            "Test Notification",
            "This is a test email from NerdsIQ log management system.\n\n"
            f"Sent at: {datetime.now().isoformat()}\n\n"
            "If you receive this, email notifications are working correctly!"
        )
        
        if success:
            logger.info("✅ Test email sent successfully!")
        else:
            logger.error("❌ Failed to send test email")


if __name__ == "__main__":
    main()