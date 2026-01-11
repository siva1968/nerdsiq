#!/usr/bin/env python
"""Renew Google Drive webhook for real-time updates."""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from loguru import logger

from app.config import settings


def renew_webhook(callback_url: str) -> dict:
    """
    Create or renew Google Drive webhook for folder changes.
    
    Args:
        callback_url: HTTPS URL to receive webhook notifications
        
    Returns:
        Webhook channel details
    """
    credentials = service_account.Credentials.from_service_account_file(
        settings.google_service_account_file,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    
    service = build("drive", "v3", credentials=credentials)
    
    # Create unique channel ID
    channel_id = f"nerdsiq-{uuid.uuid4().hex[:8]}"
    
    # Expiration: 7 days (maximum allowed)
    expiration = int((datetime.now() + timedelta(days=7)).timestamp() * 1000)
    
    channel = {
        "id": channel_id,
        "type": "web_hook",
        "address": callback_url,
        "expiration": expiration,
    }
    
    try:
        response = service.files().watch(
            fileId=settings.google_drive_folder_id,
            body=channel,
        ).execute()
        
        logger.info(f"✅ Webhook created successfully!")
        logger.info(f"   Channel ID: {response.get('id')}")
        logger.info(f"   Resource ID: {response.get('resourceId')}")
        logger.info(f"   Expiration: {datetime.fromtimestamp(int(response.get('expiration', 0)) / 1000)}")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Failed to create webhook: {e}")
        raise


def main() -> None:
    """Run webhook renewal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Renew Google Drive webhook")
    parser.add_argument(
        "--callback-url",
        "-u",
        required=True,
        help="HTTPS callback URL for webhook notifications",
    )
    
    args = parser.parse_args()
    
    if not args.callback_url.startswith("https://"):
        logger.error("Callback URL must use HTTPS!")
        sys.exit(1)
    
    renew_webhook(args.callback_url)


if __name__ == "__main__":
    main()
