#!/usr/bin/env python
"""Check current Google Drive configuration and provide status."""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_credentials():
    """Check what Google Drive credentials are available."""
    print("🔐 Authentication Status")
    print("=" * 25)
    
    creds_dir = Path("./credentials")
    service_account_file = creds_dir / "google-service-account.json"
    oauth_client_file = creds_dir / "oauth-client.json" 
    oauth_token_file = creds_dir / "oauth-token.json"
    
    auth_methods = []
    
    # Check service account
    if service_account_file.exists():
        try:
            with open(service_account_file, 'r') as f:
                creds = json.load(f)
            print("✅ Service Account Found:")
            print(f"   Project: {creds.get('project_id', 'Unknown')}")
            print(f"   Email: {creds.get('client_email', 'Unknown')}")
            print(f"   File: {service_account_file}")
            auth_methods.append("service_account")
        except Exception as e:
            print(f"⚠️  Service Account file exists but invalid: {e}")
    
    # Check OAuth
    oauth_available = oauth_client_file.exists() and oauth_token_file.exists()
    if oauth_available:
        try:
            with open(oauth_token_file, 'r') as f:
                token_data = json.load(f)
            print("✅ OAuth Credentials Found:")
            print(f"   Client file: {oauth_client_file}")
            print(f"   Token file: {oauth_token_file}")
            if 'expiry' in token_data:
                print(f"   Token expires: {token_data['expiry']}")
            auth_methods.append("oauth")
        except Exception as e:
            print(f"⚠️  OAuth files exist but invalid: {e}")
    
    if not auth_methods:
        print("❌ No valid Google Drive credentials found")
        print("   Run the complete setup script to configure authentication")
    
    return auth_methods


def check_configuration():
    """Check current configuration from .env file."""
    print("\n⚙️  Configuration Status")
    print("=" * 25)
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ No .env file found")
        return {}
    
    config = {}
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        
        # Show relevant config
        relevant_keys = [
            'GOOGLE_DRIVE_FOLDER_ID',
            'GOOGLE_AUTH_METHOD', 
            'GOOGLE_SERVICE_ACCOUNT_FILE',
            'GOOGLE_OAUTH_CLIENT_FILE',
            'GOOGLE_OAUTH_TOKEN_FILE',
            'WEBHOOK_CALLBACK_BASE_URL'
        ]
        
        for key in relevant_keys:
            value = config.get(key, 'Not set')
            status = "✅" if value and value != 'Not set' else "❌"
            print(f"   {status} {key}: {value}")
        
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
    
    return config


async def test_google_drive_access():
    """Test actual Google Drive access."""
    print("\n🧪 Google Drive Access Test")
    print("=" * 30)
    
    try:
        from app.services.drive_service import DriveService
        from app.config import settings
        
        if not settings.google_drive_folder_id:
            print("❌ No folder ID configured")
            return False
        
        print(f"Testing access to folder: {settings.google_drive_folder_id}")
        
        drive_service = DriveService()
        
        # Test folder access
        folder_info = drive_service.service.files().get(
            fileId=settings.google_drive_folder_id,
            fields="id,name,webViewLink,modifiedTime"
        ).execute()
        
        print("✅ Google Drive access successful")
        print(f"   Folder name: {folder_info.get('name')}")
        print(f"   Folder URL: {folder_info.get('webViewLink')}")
        print(f"   Last modified: {folder_info.get('modifiedTime')}")
        
        # Test file listing
        files = drive_service.list_files_recursive()
        document_files = [f for f in files if f.get('mimeType') != 'application/vnd.google-apps.folder']
        folder_count = len(files) - len(document_files)
        
        print(f"✅ Found {len(document_files)} documents in {folder_count} folders")
        
        # Show some examples
        if document_files:
            print("   Recent documents:")
            for file_info in document_files[:3]:
                print(f"   • {file_info.get('name')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Google Drive access failed: {e}")
        return False


async def check_webhook_status():
    """Check webhook status."""
    print("\n🔗 Webhook Status")
    print("=" * 18)
    
    try:
        from app.services.webhook_service import webhook_service
        status = webhook_service.get_webhook_status()
        
        if status["status"] == "active":
            webhook_info = status["webhook"]
            print("✅ Webhook is active")
            print(f"   Channel ID: {webhook_info['channel_id']}")
            print(f"   Expires: {webhook_info['expiration']}")
            print(f"   Time left: {webhook_info['expires_in_hours']:.1f} hours")
        else:
            print("❌ No active webhook")
            print("   Automatic sync is disabled")
            
    except Exception as e:
        print(f"❌ Cannot check webhook status: {e}")


async def main():
    """Main status check."""
    print("📊 NerdsIQ Google Drive Status Check")
    print("=" * 45)
    
    # Check what's available
    auth_methods = check_credentials()
    config = check_configuration()
    
    # Test access if configured
    if auth_methods and config.get('GOOGLE_DRIVE_FOLDER_ID'):
        access_ok = await test_google_drive_access()
        if access_ok:
            await check_webhook_status()
    else:
        print("\n⚠️  Cannot test Google Drive access - missing credentials or folder ID")
    
    # Provide recommendations
    print("\n💡 Recommendations")
    print("=" * 18)
    
    if not auth_methods:
        print("• Run: python scripts/change_complete_setup.py")
        print("  (To set up Google Drive authentication)")
    elif not config.get('GOOGLE_DRIVE_FOLDER_ID'):
        print("• Set GOOGLE_DRIVE_FOLDER_ID in your .env file")
    elif not config.get('WEBHOOK_CALLBACK_BASE_URL'):
        print("• Set WEBHOOK_CALLBACK_BASE_URL for automatic sync")
        print("• Run: python scripts/setup_webhooks.py")
    else:
        print("✅ Setup looks good!")
        print("• To change folder: python scripts/change_sync_folder.py")
        print("• To change credentials: python scripts/change_complete_setup.py")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())