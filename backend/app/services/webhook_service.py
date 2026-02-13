"""Webhook management service for Google Drive notifications."""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from loguru import logger

from app.config import settings


class WebhookService:
    """Service for managing Google Drive webhooks."""
    
    def __init__(self):
        self.current_webhook: Optional[Dict] = None
        self.renewal_task: Optional[asyncio.Task] = None
    
    def _get_drive_service(self):
        """Get authenticated Google Drive service."""
        from app.services.drive_service import DriveService
        # Use the existing DriveService which handles both OAuth and Service Account
        drive_service = DriveService()
        return drive_service.service
    
    async def create_webhook(self, callback_url: str) -> Dict:
        """
        Create a new Google Drive webhook.
        
        Args:
            callback_url: HTTPS URL to receive notifications
            
        Returns:
            Webhook channel details
        """
        try:
            service = self._get_drive_service()
            
            # Create unique channel ID
            channel_id = f"nerdsiq-{uuid.uuid4().hex[:8]}"
            
            # Set expiration to 6 days (renew before 7-day limit)
            expiration = int((datetime.now() + timedelta(days=6)).timestamp() * 1000)
            
            channel = {
                "id": channel_id,
                "type": "web_hook",
                "address": callback_url,
                "expiration": expiration,
            }
            
            response = service.files().watch(
                fileId=settings.google_drive_folder_id,
                body=channel,
            ).execute()
            
            self.current_webhook = response
            
            logger.info("✅ Google Drive webhook created successfully!")
            logger.info(f"   Channel ID: {response.get('id')}")
            logger.info(f"   Resource ID: {response.get('resourceId')}")
            logger.info(f"   Expiration: {datetime.fromtimestamp(int(response.get('expiration', 0)) / 1000)}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to create webhook: {e}")
            raise
    
    async def stop_webhook(self, channel_id: str, resource_id: str) -> None:
        """Stop an existing webhook channel."""
        try:
            service = self._get_drive_service()
            
            channel = {
                "id": channel_id,
                "resourceId": resource_id,
            }
            
            service.channels().stop(body=channel).execute()
            logger.info(f"🛑 Stopped webhook channel: {channel_id}")
            
        except Exception as e:
            logger.warning(f"Failed to stop webhook {channel_id}: {e}")
    
    async def renew_webhook(self, callback_url: str) -> Dict:
        """
        Renew the current webhook by creating a new one and stopping the old one.
        
        Args:
            callback_url: HTTPS URL to receive notifications
            
        Returns:
            New webhook channel details
        """
        old_webhook = self.current_webhook
        
        try:
            # Create new webhook
            new_webhook = await self.create_webhook(callback_url)
            
            # Stop old webhook if it exists
            if old_webhook:
                await self.stop_webhook(
                    old_webhook.get("id", ""),
                    old_webhook.get("resourceId", "")
                )
            
            return new_webhook
            
        except Exception as e:
            logger.error(f"❌ Failed to renew webhook: {e}")
            # Keep the old webhook if renewal fails
            self.current_webhook = old_webhook
            raise
    
    async def start_auto_renewal(self, callback_url: str, renewal_hours: int = 144) -> None:
        """
        Start automatic webhook renewal.
        
        Args:
            callback_url: HTTPS URL to receive notifications
            renewal_hours: Hours between renewals (default: 144 = 6 days)
        """
        if self.renewal_task and not self.renewal_task.done():
            logger.info("Auto-renewal already running")
            return
        
        logger.info(f"🔄 Starting webhook auto-renewal (every {renewal_hours} hours)")
        
        # Create initial webhook
        await self.create_webhook(callback_url)
        
        # Start renewal loop
        self.renewal_task = asyncio.create_task(
            self._renewal_loop(callback_url, renewal_hours)
        )
    
    async def stop_auto_renewal(self) -> None:
        """Stop automatic webhook renewal."""
        if self.renewal_task:
            self.renewal_task.cancel()
            try:
                await self.renewal_task
            except asyncio.CancelledError:
                pass
            logger.info("🛑 Stopped webhook auto-renewal")
        
        # Stop current webhook
        if self.current_webhook:
            await self.stop_webhook(
                self.current_webhook.get("id", ""),
                self.current_webhook.get("resourceId", "")
            )
            self.current_webhook = None
    
    async def _renewal_loop(self, callback_url: str, renewal_hours: int) -> None:
        """Background loop for webhook renewal."""
        while True:
            try:
                await asyncio.sleep(renewal_hours * 3600)  # Convert hours to seconds
                logger.info("⏰ Time to renew webhook...")
                await self.renew_webhook(callback_url)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in webhook renewal loop: {e}")
                # Continue trying to renew
                await asyncio.sleep(3600)  # Retry in 1 hour
    
    def get_webhook_status(self) -> Dict:
        """Get current webhook status."""
        if not self.current_webhook:
            return {"status": "inactive", "webhook": None}
        
        expiration_ms = int(self.current_webhook.get("expiration", 0))
        expiration_dt = datetime.fromtimestamp(expiration_ms / 1000) if expiration_ms else None
        
        return {
            "status": "active",
            "webhook": {
                "channel_id": self.current_webhook.get("id"),
                "resource_id": self.current_webhook.get("resourceId"),
                "expiration": expiration_dt.isoformat() if expiration_dt else None,
                "expires_in_hours": (
                    (expiration_dt - datetime.now()).total_seconds() / 3600
                    if expiration_dt else None
                ),
            },
        }


# Global webhook service instance
webhook_service = WebhookService()