#!/usr/bin/env python3
"""Automated daily report generator for NerdsIQ monitoring."""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# Add the backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger
from app.services.monitoring_service import EmailNotifier


def generate_daily_report():
    """Generate and email daily report."""
    logger.info("🔄 Generating daily report...")
    
    yesterday = date.today() - timedelta(days=1)
    log_dir = Path("daily_logs")
    
    # Read yesterday's status
    status_file = log_dir / f"status_{yesterday.strftime('%Y-%m-%d')}.json"
    
    if not status_file.exists():
        logger.warning(f"❌ No status file found for {yesterday}")
        return
    
    import json
    
    try:
        with open(status_file, 'r', encoding='utf-8') as f:
            status = json.load(f)
    except Exception as e:
        logger.error(f"Could not read status file: {e}")
        return
    
    # Generate report content
    subject = f"NerdsIQ Daily Report - {yesterday.strftime('%B %d, %Y')}"
    
    # Get summary from status
    summary = status.get('summary', 'No summary available')
    
    # Build detailed HTML report for better email formatting
    report_lines = [
        f"<html><body style='font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;'>",
        f"<div style='background: #0047AC; color: white; padding: 20px; text-align: center;'>",
        f"<h1 style='margin: 0; color: white;'>📊 NerdsIQ Daily Report</h1>",
        f"<p style='margin: 10px 0 0 0; color: #FFD301;'>{yesterday.strftime('%A, %B %d, %Y')}</p>",
        f"</div>",
        f"",
        f"<div style='padding: 20px; background: #f8f9fa;'>",
        f"<h2 style='color: #0047AC; margin-top: 0;'>📋 Summary</h2>",
        f"<div style='background: white; padding: 15px; border-radius: 5px; margin-bottom: 20px;'>",
        summary.replace('\\n', '<br>'),
        f"</div>",
        f"",
        f"<h2 style='color: #0047AC;'>📊 Statistics</h2>",
        f"<div style='display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 20px;'>",
        f"<div style='background: white; padding: 15px; border-radius: 5px; text-align: center;'>",
        f"<div style='font-size: 24px; font-weight: bold; color: #0047AC;'>{status.get('total_files_processed', 0):,}</div>",
        f"<div style='color: #666;'>Files Processed</div>",
        f"</div>",
        f"<div style='background: white; padding: 15px; border-radius: 5px; text-align: center;'>",
        f"<div style='font-size: 24px; font-weight: bold; color: #28a745;'>{status.get('successful_files', 0):,}</div>",
        f"<div style='color: #666;'>Successful</div>",
        f"</div>",
        f"<div style='background: white; padding: 15px; border-radius: 5px; text-align: center;'>",
        f"<div style='font-size: 24px; font-weight: bold; color: #dc3545;'>{status.get('failed_files', 0):,}</div>",
        f"<div style='color: #666;'>Failed</div>",
        f"</div>",
        f"<div style='background: white; padding: 15px; border-radius: 5px; text-align: center;'>",
        f"<div style='font-size: 24px; font-weight: bold; color: #0047AC;'>{status.get('total_chunks_added', 0):,}</div>",
        f"<div style='color: #666;'>Chunks Added</div>",
        f"</div>",
        f"</div>",
        f"",
    ]
    
    # Add error details if any
    errors = status.get('errors', [])
    if errors:
        report_lines.extend([
            f"<h2 style='color: #dc3545;'>⚠️ Errors ({len(errors)} total)</h2>",
            f"<div style='background: white; padding: 15px; border-radius: 5px; margin-bottom: 20px;'>",
        ])
        
        # Show first 10 errors
        for i, error in enumerate(errors[:10], 1):
            timestamp = error.get('timestamp', 'Unknown')
            message = error.get('message', 'Unknown error')
            report_lines.append(f"<div style='margin-bottom: 10px; padding: 10px; background: #fff5f5; border-left: 4px solid #dc3545;'>")
            report_lines.append(f"<strong style='color: #dc3545;'>{i}. [{timestamp}]</strong><br>")
            report_lines.append(f"<span style='color: #666;'>{message}</span>")
            report_lines.append(f"</div>")
        
        if len(errors) > 10:
            report_lines.append(f"<p style='color: #666; font-style: italic;'>... and {len(errors) - 10} more errors</p>")
        
        report_lines.append("</div>")
    
    # Add next steps or recommendations
    failed_files = status.get('failed_files', 0)
    
    if failed_files > 0:
        report_lines.extend([
            f"<h2 style='color: #ffc107;'>🔧 Recommendations</h2>",
            f"<div style='background: #fff8e1; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;'>",
            f"<ul style='margin: 0; padding-left: 20px;'>",
            f"<li>Review and retry failed files ({failed_files} total)</li>",
            f"<li>Check error patterns for common issues</li>",
            f"<li>Consider adjusting batch sizes if rate limit errors</li>",
            f"</ul>",
            f"</div>",
        ])
    else:
        report_lines.extend([
            f"<div style='background: #d4edda; padding: 15px; border-radius: 5px; border-left: 4px solid #28a745; text-align: center;'>",
            f"<h3 style='color: #28a745; margin: 0;'>✅ All Files Processed Successfully!</h3>",
            f"<p style='margin: 5px 0 0 0; color: #666;'>No action required</p>",
            f"</div>",
        ])
    
    # Footer
    report_lines.extend([
        f"</div>",
        f"<div style='background: #0047AC; color: white; padding: 20px; text-align: center; margin-top: 20px;'>",
        f"<p style='margin: 0; font-size: 14px;'>Generated by NerdsIQ Monitoring System</p>",
        f"<p style='margin: 5px 0 0 0; font-size: 12px; color: #FFD301;'>Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        f"</div>",
        f"</body></html>",
    ])
    
    report_content = "\n".join(report_lines)
    
    # Send email report
    email_notifier = EmailNotifier()
    
    if email_notifier.enabled:
        # Send HTML email for better formatting
        success = email_notifier.send_alert(subject, report_content, is_html=True)
        
        if success:
            logger.info("✅ Daily report sent successfully via Zepto Mail!")
        else:
            logger.error("❌ Failed to send daily report via Zepto Mail")
    else:
        logger.warning("❌ Zepto Mail not configured - printing report to console:")
        # Convert HTML to plain text for console
        import re
        plain_text = re.sub(r'<[^>]+>', '', report_content)
        print("\n" + plain_text)
    
    logger.info("📧 Daily report generation completed")


def main():
    """Main function for the daily report generator."""
    logger.info("🌅 Starting daily report generation...")
    
    try:
        generate_daily_report()
        logger.info("✅ Daily report completed successfully")
    except Exception as e:
        logger.error(f"❌ Daily report failed: {e}")
        
        # Try to send error notification
        email_notifier = EmailNotifier()
        if email_notifier.enabled:
            error_subject = f"NerdsIQ Daily Report Failed - {date.today().strftime('%Y-%m-%d')}"
            error_message = (
                f"The daily report generation failed with the following error:\n\n"
                f"Error: {str(e)}\n\n"
                f"Time: {datetime.now().isoformat()}\n\n"
                f"Please check the logs and system status."
            )
            email_notifier.send_alert(error_subject, error_message)


if __name__ == "__main__":
    main()