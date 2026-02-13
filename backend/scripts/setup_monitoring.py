#!/usr/bin/env python3
"""Setup and configuration script for NerdsIQ monitoring system."""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add the backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger
from app.services.monitoring_service import DailyLogger, EmailNotifier


def setup_directories():
    """Create necessary directories for logging."""
    logger.info("📁 Setting up directories...")
    
    directories = [
        Path("daily_logs"),
        Path("logs"),  # For general application logs
    ]
    
    for directory in directories:
        directory.mkdir(exist_ok=True)
        logger.info(f"   ✅ Created/verified: {directory}")


def check_email_config():
    """Check and validate email configuration."""
    logger.info("📧 Checking email configuration...")
    
    required_vars = [
        "SMTP_SERVER",
        "SMTP_USERNAME", 
        "SMTP_PASSWORD",
        "FROM_EMAIL",
        "NOTIFICATION_EMAILS"
    ]
    
    missing_vars = []
    configured_vars = []
    
    for var in required_vars:
        if os.getenv(var):
            configured_vars.append(var)
        else:
            missing_vars.append(var)
    
    if configured_vars:
        logger.info(f"   ✅ Configured variables ({len(configured_vars)}):")
        for var in configured_vars:
            # Mask sensitive information
            value = os.getenv(var)
            if "password" in var.lower():
                display_value = "*" * len(value) if value else "Not set"
            elif "@" in str(value):  # Email addresses
                display_value = str(value)[:3] + "***@" + str(value).split("@")[1] if value else "Not set"
            else:
                display_value = str(value)[:10] + "..." if len(str(value)) > 10 else str(value)
            
            logger.info(f"      {var}: {display_value}")
    
    if missing_vars:
        logger.warning(f"   ⚠️  Missing variables ({len(missing_vars)}):")
        for var in missing_vars:
            logger.warning(f"      {var}: Not configured")
        
        logger.info("\n   📝 Add these to your .env file:")
        logger.info("      # Zepto Mail API Configuration (Recommended)")
        logger.info("      ZEPTOMAIL_API_KEY=your-zoho-enczapikey-token")
        logger.info("      ZEPTOMAIL_REGION=in")
        logger.info("      USE_ZEPTOMAIL_API=true")
        logger.info("      FROM_EMAIL=noreply@yourdomain.com")
        logger.info("      NOTIFICATION_EMAILS=admin@company.com,alerts@company.com")
        logger.info("")
        logger.info("      # Alternative: SMTP Configuration")
        logger.info("      SMTP_SERVER=smtp.zeptomail.com")
        logger.info("      SMTP_PORT=587")
        logger.info("      SMTP_USERNAME=emailapikey")
        logger.info("      SMTP_PASSWORD=your-zepto-mail-token")
        
        return False
    
    return True


def test_email_notification():
    """Test email notification functionality."""
    logger.info("🧪 Testing email notification...")
    
    email_notifier = EmailNotifier()
    
    if not email_notifier.enabled:
        logger.error("   ❌ Email notifications not enabled")
        return False
    
    test_subject = f"NerdsIQ Monitoring Setup Test - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    test_message = f"""
NerdsIQ Monitoring System Setup Test

This is a test email to verify that the monitoring system can send notifications successfully.

Setup completed at: {datetime.now().isoformat()}

System Information:
- Email server: {os.getenv('SMTP_SERVER', 'Not configured')}
- From address: {os.getenv('FROM_EMAIL', 'Not configured')}
- Notification recipients: {len(email_notifier.notification_emails)} addresses

If you receive this email, the monitoring system is configured correctly and ready to send daily reports and alerts!

---
NerdsIQ Monitoring System
    """.strip()
    
    success = email_notifier.send_alert(test_subject, test_message)
    
    if success:
        logger.info("   ✅ Test email sent successfully!")
        logger.info(f"   📧 Recipients: {', '.join(email_notifier.notification_emails)}")
        return True
    else:
        logger.error("   ❌ Failed to send test email")
        return False


def create_sample_log_entry():
    """Create a sample log entry for testing."""
    logger.info("📝 Creating sample log entry...")
    
    daily_logger = DailyLogger()
    
    # Log some sample events
    daily_logger.log_info("Sample indexing session started")
    daily_logger.log_info("Processing document: sample_document.pdf")
    daily_logger.log_info("Generated 50 chunks from document")
    daily_logger.log_error("Rate limit encountered, retrying...")
    daily_logger.log_info("Document processing completed successfully")
    daily_logger.log_info("Sample indexing session completed")
    
    # Save sample status
    sample_status = {
        "start_time": datetime.now().isoformat(),
        "end_time": datetime.now().isoformat(),
        "total_files_processed": 1,
        "successful_files": 1,
        "failed_files": 0,
        "total_chunks_added": 50,
        "processing_time": "30 seconds",
        "errors": [],
        "summary": "✅ Sample indexing completed successfully. Processed 1 file and generated 50 chunks."
    }
    
    # Manually update session stats and finalize
    daily_logger.session_stats.update(sample_status)
    daily_logger.finalize_session()
    
    logger.info("   ✅ Sample log entry created")
    logger.info(f"   📁 Log location: {daily_logger.log_file}")


def setup_monitoring_system():
    """Complete setup of the monitoring system."""
    logger.info("🚀 Setting up NerdsIQ monitoring system...")
    logger.info("=" * 60)
    
    # Step 1: Create directories
    setup_directories()
    print()
    
    # Step 2: Check email configuration
    email_configured = check_email_config()
    print()
    
    # Step 3: Test email if configured
    email_working = False
    if email_configured:
        email_working = test_email_notification()
        print()
    
    # Step 4: Create sample log
    create_sample_log_entry()
    print()
    
    # Summary
    logger.info("📋 Setup Summary:")
    logger.info("=" * 30)
    
    logger.info(f"   📁 Directories: ✅ Created")
    logger.info(f"   📧 Email config: {'✅ Complete' if email_configured else '❌ Incomplete'}")
    logger.info(f"   🧪 Email test: {'✅ Passed' if email_working else '❌ Failed' if email_configured else '⏭️ Skipped'}")
    logger.info(f"   📝 Sample logs: ✅ Created")
    
    print()
    
    if email_configured and email_working:
        logger.info("🎉 Monitoring system setup completed successfully!")
        logger.info("\n📚 Usage Examples:")
        logger.info("   • View today's logs: python scripts/log_manager.py show")
        logger.info("   • Weekly report: python scripts/log_manager.py weekly")
        logger.info("   • List all log dates: python scripts/log_manager.py list")
        logger.info("   • Send test email: python scripts/log_manager.py email-test")
        logger.info("   • Run monitored indexing: python scripts/monitored_indexing.py")
        logger.info("   • Daily report: python scripts/daily_report.py")
        
        logger.info("\n🔄 Scheduling Daily Reports:")
        logger.info("   Windows (Task Scheduler):")
        logger.info("   • Task: Run python scripts/daily_report.py")
        logger.info("   • Trigger: Daily at 8:00 AM")
        logger.info("   • Working directory: D:\\dev\\nerdsiq\\backend")
        logger.info("\n   Linux/Mac (Crontab):")
        logger.info("   • Add: 0 8 * * * cd /path/to/backend && python scripts/daily_report.py")
        
    else:
        logger.warning("⚠️  Setup completed with issues!")
        if not email_configured:
            logger.warning("   • Configure email settings in .env file")
        if email_configured and not email_working:
            logger.warning("   • Test email functionality - check credentials and firewall")
        
        logger.info("\n   After fixing issues, run: python scripts/setup_monitoring.py")


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--test-email-only":
        test_email_notification()
    else:
        setup_monitoring_system()


if __name__ == "__main__":
    main()