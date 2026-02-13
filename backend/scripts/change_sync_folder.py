#!/usr/bin/env python
"""Change Google Drive sync folder with step-by-step confirmation."""

import sys
import asyncio
import re
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from app.config import settings
from app.services.drive_service import DriveService
from app.services.webhook_service import webhook_service
from app.services.cache_service import CacheService


def extract_folder_id(folder_input: str) -> str:
    """Extract folder ID from URL or return as-is if already an ID."""
    # If it's a URL, extract the folder ID
    if "drive.google.com" in folder_input:
        match = re.search(r'/folders/([a-zA-Z0-9-_]+)', folder_input)
        if match:
            return match.group(1)
        else:
            raise ValueError("Could not extract folder ID from URL")
    
    # Otherwise assume it's already a folder ID
    return folder_input.strip()


def get_user_confirmation(message: str) -> bool:
    """Get user confirmation for an action."""
    while True:
        response = input(f"{message} (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no', '']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")


async def verify_folder_access(folder_id: str) -> dict:
    """Verify that we can access the folder and get its info."""
    try:
        drive_service = DriveService()
        folder_info = drive_service.service.files().get(
            fileId=folder_id,
            fields="id,name,webViewLink,modifiedTime"
        ).execute()
        
        # Test listing files
        files = drive_service.list_files(folder_id)
        file_count = len([f for f in files if f.get('mimeType') != 'application/vnd.google-apps.folder'])
        
        return {
            "accessible": True,
            "name": folder_info.get("name"),
            "url": folder_info.get("webViewLink"),
            "file_count": file_count,
            "last_modified": folder_info.get("modifiedTime")
        }
        
    except Exception as e:
        return {
            "accessible": False,
            "error": str(e)
        }


async def change_sync_folder():
    """Interactive process to change the sync folder."""
    print("🔄 Google Drive Sync Folder Manager")
    print("=" * 50)
    
    # Step 1: Show current folder
    print("\n📁 STEP 1: Current Sync Folder")
    try:
        current_info = await verify_folder_access(settings.google_drive_folder_id)
        if current_info["accessible"]:
            print(f"   Name: {current_info['name']}")
            print(f"   ID: {settings.google_drive_folder_id}")
            print(f"   Files: {current_info['file_count']}")
            print(f"   URL: {current_info['url']}")
        else:
            print(f"   ❌ Current folder not accessible: {current_info['error']}")
    except Exception as e:
        print(f"   ❌ Error accessing current folder: {e}")
    
    # Step 2: Get new folder
    print("\n📁 STEP 2: New Folder Selection")
    print("Enter the new Google Drive folder:")
    print("• Folder URL: https://drive.google.com/drive/folders/YOUR_FOLDER_ID")
    print("• Or just the folder ID: 1ABC123XYZ789...")
    
    while True:
        folder_input = input("\nEnter folder URL or ID: ").strip()
        if not folder_input:
            print("❌ Folder input cannot be empty")
            continue
        
        try:
            new_folder_id = extract_folder_id(folder_input)
            print(f"\n✅ Extracted folder ID: {new_folder_id}")
            break
        except ValueError as e:
            print(f"❌ {e}")
            continue
    
    # Step 3: Verify access to new folder
    print("\n🔍 STEP 3: Verifying Access")
    print("Checking access to new folder...")
    
    folder_info = await verify_folder_access(new_folder_id)
    
    if not folder_info["accessible"]:
        print(f"❌ Cannot access folder: {folder_info['error']}")
        print("\nPossible issues:")
        print("• Folder ID is incorrect")
        print("• Google credentials don't have access to this folder")
        print("• Folder doesn't exist or is private")
        return False
    
    print("✅ Folder is accessible!")
    print(f"   Name: {folder_info['name']}")
    print(f"   Files: {folder_info['file_count']}")
    print(f"   URL: {folder_info['url']}")
    
    # Step 4: Confirmation
    print("\n⚠️  STEP 4: Confirmation")
    print("This will:")
    print("• Stop the current webhook")
    print("• Clear all cached queries") 
    print("• Switch to the new folder")
    print("• Create a new webhook")
    print("• Reindex all documents from the new folder")
    
    if not get_user_confirmation("Proceed with folder change?"):
        print("❌ Operation cancelled")
        return False
    
    # Step 5: Execute change
    print("\n🚀 STEP 5: Executing Change")
    
    try:
        # Stop current webhook
        print("🛑 Stopping current webhook...")
        await webhook_service.stop_auto_renewal()
        print("✅ Current webhook stopped")
        
        # Update folder ID
        old_folder_id = settings.google_drive_folder_id
        settings.google_drive_folder_id = new_folder_id
        print(f"📁 Updated folder ID: {old_folder_id} → {new_folder_id}")
        
        # Clear cache
        print("💨 Clearing cache...")
        cache_service = CacheService()
        await cache_service.invalidate_all()
        print("✅ Cache cleared")
        
        # Start new webhook
        print("🔗 Setting up webhook for new folder...")
        if settings.webhook_callback_base_url and settings.webhook_callback_base_url != "https://your-domain.com":
            callback_url = f"{settings.webhook_callback_base_url}/api/v1/documents/webhook/drive-changes"
            await webhook_service.start_auto_renewal(callback_url)
            print("✅ Webhook created for new folder")
        else:
            print("⚠️  Webhook not set up - WEBHOOK_CALLBACK_BASE_URL not configured")
        
        # Trigger reindexing
        print("🔄 Starting document reindexing...")
        from scripts.index_documents import index_documents
        await index_documents()
        print("✅ Document reindexing completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during folder change: {e}")
        # Restore old folder ID
        settings.google_drive_folder_id = old_folder_id
        print(f"🔄 Restored original folder ID: {old_folder_id}")
        return False


async def verify_setup():
    """Verify the setup after folder change."""
    print("\n🔍 STEP 6: Verification")
    
    # Check folder access
    folder_info = await verify_folder_access(settings.google_drive_folder_id)
    if folder_info["accessible"]:
        print(f"✅ Folder accessible: {folder_info['name']}")
        print(f"   Files indexed: {folder_info['file_count']}")
    else:
        print(f"❌ Folder access issue: {folder_info['error']}")
    
    # Check webhook status
    webhook_status = webhook_service.get_webhook_status()
    if webhook_status["status"] == "active":
        webhook_info = webhook_status["webhook"]
        print(f"✅ Webhook active: {webhook_info['channel_id']}")
        print(f"   Expires in: {webhook_info['expires_in_hours']:.1f} hours")
    else:
        print("⚠️  Webhook inactive")
    
    print("\n🎉 SETUP COMPLETE!")
    print("Your NerdsIQ system is now syncing with the new Google Drive folder.")
    print("Changes to files in this folder will be automatically detected and indexed.")


async def main():
    """Main function."""
    try:
        success = await change_sync_folder()
        if success:
            await verify_setup()
            print("\n✨ Folder change completed successfully!")
        else:
            print("\n❌ Folder change was not completed.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())