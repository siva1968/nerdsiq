#!/usr/bin/env python
"""Setup Google Drive webhooks for automatic document synchronization."""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from app.config import settings
from app.services.webhook_service import webhook_service


async def setup_webhooks():
    """Set up Google Drive webhooks for automatic document sync."""
    logger.info("🚀 Setting up Google Drive webhooks for automatic document synchronization...")
    
    # Check configuration
    if not settings.google_drive_folder_id:
        logger.error("❌ GOOGLE_DRIVE_FOLDER_ID not configured!")
        logger.info("Please set GOOGLE_DRIVE_FOLDER_ID in your .env file")
        return False
    
    if not settings.webhook_callback_base_url or settings.webhook_callback_base_url == "https://your-domain.com":
        logger.error("❌ WEBHOOK_CALLBACK_BASE_URL not configured!")
        logger.info("Please set WEBHOOK_CALLBACK_BASE_URL in your .env file to your public domain")
        return False
    
    # Construct callback URL
    callback_url = f"{settings.webhook_callback_base_url}/api/v1/documents/webhook/drive-changes"
    
    try:
        # Start auto-renewal (creates initial webhook and schedules renewals)
        await webhook_service.start_auto_renewal(callback_url)
        
        # Show status
        status = webhook_service.get_webhook_status()
        logger.info("✅ Webhook setup completed successfully!")
        logger.info(f"   Status: {status['status']}")
        
        if status['webhook']:
            webhook_info = status['webhook']
            logger.info(f"   Channel ID: {webhook_info['channel_id']}")
            logger.info(f"   Expires: {webhook_info['expiration']}")
            logger.info(f"   Time until expiry: {webhook_info['expires_in_hours']:.1f} hours")
        
        logger.info("")
        logger.info("🔄 Your NerdsIQ system will now automatically:")
        logger.info("   • Detect when files are added to Google Drive")
        logger.info("   • Detect when files are modified in Google Drive") 
        logger.info("   • Detect when files are removed from Google Drive")
        logger.info("   • Reindex documents automatically")
        logger.info("   • Clear cached queries")
        logger.info("   • Renew webhooks automatically every 6 days")
        logger.info("")
        logger.info("✨ Your knowledge base is now truly 'set and forget'!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to setup webhooks: {e}")
        logger.info("Common issues:")
        logger.info("1. Make sure your callback URL is publicly accessible via HTTPS")
        logger.info("2. Verify your Google Drive credentials have access to the folder")
        logger.info("3. Check that the Google Drive API is enabled in your project")
        return False


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Google Drive webhooks")
    parser.add_argument(
        "--callback-url",
        help="Override the callback URL from config",
    )
    
    args = parser.parse_args()
    
    if args.callback_url:
        # Override the config value
        settings.webhook_callback_base_url = args.callback_url.rstrip('/')
    
    success = asyncio.run(setup_webhooks())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()