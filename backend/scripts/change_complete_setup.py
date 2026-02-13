#!/usr/bin/env python
"""Complete Google Drive setup change - credentials, folder, and sync configuration."""

import sys
import os
import json
import asyncio
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


def get_user_input(prompt: str, required: bool = True) -> str:
    """Get user input with validation."""
    while True:
        value = input(f"{prompt}: ").strip()
        if value or not required:
            return value
        print("❌ This field is required. Please enter a value.")


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


def backup_current_setup():
    """Backup current credentials and configuration."""
    backup_dir = Path("./credentials/backup")
    backup_dir.mkdir(exist_ok=True)
    
    # Backup credentials
    creds_dir = Path("./credentials")
    for file_pattern in ["*.json", "*.token"]:
        for file_path in creds_dir.glob(file_pattern):
            if not file_path.name.startswith("backup"):
                backup_path = backup_dir / f"{file_path.name}.backup"
                if file_path.exists():
                    shutil.copy2(file_path, backup_path)
                    print(f"✅ Backed up {file_path.name}")
    
    # Backup .env
    env_file = Path(".env")
    if env_file.exists():
        shutil.copy2(env_file, backup_dir / ".env.backup")
        print("✅ Backed up .env file")
    
    print(f"📁 Backup saved to: {backup_dir.absolute()}")


def setup_service_account():
    """Set up Google Service Account authentication."""
    print("\n🔐 Service Account Setup")
    print("=" * 30)
    
    print("You need a Google Cloud Service Account JSON file.")
    print("Get it from: https://console.cloud.google.com/")
    print("• Go to IAM & Admin > Service Accounts")
    print("• Create or select a service account")
    print("• Create a JSON key")
    print("• Download the JSON file")
    
    while True:
        json_path = get_user_input("\nPath to your service account JSON file")
        json_file = Path(json_path)
        
        if not json_file.exists():
            print("❌ File not found. Please check the path.")
            continue
        
        try:
            # Validate JSON
            with open(json_file, 'r') as f:
                creds = json.load(f)
            
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in creds]
            
            if missing_fields:
                print(f"❌ Invalid service account file. Missing: {missing_fields}")
                continue
            
            if creds.get('type') != 'service_account':
                print("❌ This is not a service account file.")
                continue
            
            # Copy to credentials directory
            target_path = Path("./credentials/google-service-account.json")
            shutil.copy2(json_file, target_path)
            
            print("✅ Service account file installed successfully")
            print(f"   Project: {creds.get('project_id')}")
            print(f"   Email: {creds.get('client_email')}")
            
            return {
                "auth_method": "service_account",
                "service_account_file": str(target_path),
                "project_id": creds.get('project_id'),
                "client_email": creds.get('client_email')
            }
            
        except json.JSONDecodeError:
            print("❌ Invalid JSON file. Please check the file format.")
        except Exception as e:
            print(f"❌ Error reading file: {e}")


def setup_oauth():
    """Set up OAuth authentication (for restricted organizations)."""
    print("\n🔐 OAuth Setup")
    print("=" * 15)
    
    print("OAuth is needed for restricted Google Workspace organizations.")
    print("You need:")
    print("1. OAuth client JSON file (from Google Cloud Console)")
    print("2. To run authentication flow")
    
    # Step 1: Get OAuth client file
    while True:
        client_path = get_user_input("\nPath to your OAuth client JSON file")
        client_file = Path(client_path)
        
        if not client_file.exists():
            print("❌ File not found. Please check the path.")
            continue
        
        try:
            # Validate client JSON
            with open(client_file, 'r') as f:
                client_config = json.load(f)
            
            if 'installed' not in client_config and 'web' not in client_config:
                print("❌ Invalid OAuth client file format.")
                continue
            
            # Copy to credentials directory
            target_path = Path("./credentials/oauth-client.json")
            shutil.copy2(client_file, target_path)
            print("✅ OAuth client file installed")
            break
            
        except json.JSONDecodeError:
            print("❌ Invalid JSON file.")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Step 2: Run authentication
    print("\n🚀 Running OAuth authentication...")
    print("This will open your browser to authenticate with Google.")
    
    if not get_user_confirmation("Proceed with authentication?"):
        return None
    
    try:
        # Run the authentication script
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/authenticate_drive.py"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ OAuth authentication successful")
            token_path = Path("./credentials/oauth-token.json")
            if token_path.exists():
                return {
                    "auth_method": "oauth",
                    "client_file": str(target_path),
                    "token_file": str(token_path)
                }
        else:
            print(f"❌ Authentication failed: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None


def get_folder_setup():
    """Get Google Drive folder configuration."""
    print("\n📁 Google Drive Folder Setup")
    print("=" * 30)
    
    print("Enter your Google Drive folder information:")
    print("• You can paste the full folder URL")
    print("• Or just the folder ID")
    
    while True:
        folder_input = get_user_input("\nGoogle Drive folder URL or ID")
        
        # Extract folder ID from URL if provided
        if "drive.google.com" in folder_input:
            import re
            match = re.search(r'/folders/([a-zA-Z0-9-_]+)', folder_input)
            if match:
                folder_id = match.group(1)
            else:
                print("❌ Could not extract folder ID from URL")
                continue
        else:
            folder_id = folder_input.strip()
        
        print(f"✅ Folder ID: {folder_id}")
        
        if get_user_confirmation("Is this correct?"):
            return folder_id


async def test_setup(auth_config: dict, folder_id: str):
    """Test the new configuration."""
    print("\n🧪 Testing Configuration")
    print("=" * 25)
    
    try:
        # Update environment temporarily for testing
        os.environ["GOOGLE_DRIVE_FOLDER_ID"] = folder_id
        os.environ["GOOGLE_AUTH_METHOD"] = auth_config["auth_method"]
        
        if auth_config["auth_method"] == "service_account":
            os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = auth_config["service_account_file"]
        else:
            os.environ["GOOGLE_OAUTH_CLIENT_FILE"] = auth_config["client_file"]
            os.environ["GOOGLE_OAUTH_TOKEN_FILE"] = auth_config["token_file"]
        
        # Test Google Drive access
        from app.services.drive_service import DriveService
        drive_service = DriveService()
        
        # Get folder info
        folder_info = drive_service.service.files().get(
            fileId=folder_id,
            fields="id,name,webViewLink,modifiedTime"
        ).execute()
        
        print("✅ Google Drive connection successful")
        print(f"   Folder: {folder_info.get('name')}")
        print(f"   URL: {folder_info.get('webViewLink')}")
        
        # Test file listing
        files = drive_service.list_files_recursive()
        document_files = [f for f in files if f.get('mimeType') != 'application/vnd.google-apps.folder']
        
        print(f"✅ Found {len(document_files)} documents to index")
        
        # Show some file examples
        if document_files:
            print("   Sample files:")
            for file_info in document_files[:5]:
                print(f"   • {file_info.get('name')}")
            if len(document_files) > 5:
                print(f"   ... and {len(document_files) - 5} more files")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def update_env_file(auth_config: dict, folder_id: str, webhook_url: str = None):
    """Update .env file with new configuration."""
    print("\n📝 Updating Configuration")
    print("=" * 25)
    
    env_file = Path(".env")
    
    # Read existing .env or create new
    env_lines = []
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_lines = f.readlines()
    
    # Create dictionary of current env vars
    env_vars = {}
    for line in env_lines:
        line = line.strip()
        if line and '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            env_vars[key.strip()] = value.strip()
    
    # Update with new values
    env_vars["GOOGLE_DRIVE_FOLDER_ID"] = folder_id
    env_vars["GOOGLE_AUTH_METHOD"] = auth_config["auth_method"]
    
    if auth_config["auth_method"] == "service_account":
        env_vars["GOOGLE_SERVICE_ACCOUNT_FILE"] = auth_config["service_account_file"]
    else:
        env_vars["GOOGLE_OAUTH_CLIENT_FILE"] = auth_config["client_file"]
        env_vars["GOOGLE_OAUTH_TOKEN_FILE"] = auth_config["token_file"]
    
    if webhook_url:
        env_vars["WEBHOOK_CALLBACK_BASE_URL"] = webhook_url
    
    # Write updated .env
    with open(env_file, 'w') as f:
        f.write("# NerdsIQ Environment Configuration\n")
        f.write("# Updated by change_complete_setup.py\n\n")
        
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print("✅ Configuration file updated")
    print(f"   File: {env_file.absolute()}")


async def setup_webhooks_and_indexing(folder_id: str):
    """Set up webhooks and run initial indexing."""
    print("\n🔗 Setting Up Automation")
    print("=" * 25)
    
    # Ask about webhook URL
    print("For automatic document sync, you need a public HTTPS URL.")
    print("Examples:")
    print("• https://api.yourdomain.com")
    print("• https://your-tunnel.trycloudflare.com")
    print("• https://abc123.ngrok.io")
    
    webhook_url = get_user_input("Webhook base URL (optional)", required=False)
    
    if webhook_url:
        try:
            from app.services.webhook_service import webhook_service
            callback_url = f"{webhook_url}/api/v1/documents/webhook/drive-changes"
            await webhook_service.start_auto_renewal(callback_url)
            print("✅ Webhooks configured for automatic sync")
        except Exception as e:
            print(f"⚠️  Webhook setup failed: {e}")
            print("You can set this up later using the setup_webhooks.py script")
    else:
        print("⏭️  Skipping webhook setup (can be done later)")
    
    # Run initial indexing
    print("\n🔄 Running Initial Document Indexing")
    if get_user_confirmation("Index all documents now? (This may take a while)"):
        try:
            from scripts.index_documents import index_documents
            await index_documents()
            print("✅ Document indexing completed")
        except Exception as e:
            print(f"❌ Indexing failed: {e}")
            print("You can run indexing manually later: python scripts/index_documents.py")
    
    return webhook_url


async def main():
    """Main setup process."""
    print("🚀 Complete Google Drive Setup")
    print("=" * 40)
    print("This will completely reconfigure your Google Drive integration.")
    print("Includes: credentials, folder, webhooks, and indexing.")
    
    if not get_user_confirmation("Continue with complete setup?"):
        print("❌ Setup cancelled")
        return
    
    try:
        # Step 1: Backup current setup
        print("\n📋 STEP 1: Backup Current Setup")
        backup_current_setup()
        
        # Step 2: Choose authentication method
        print("\n📋 STEP 2: Choose Authentication Method")
        print("1. Service Account (recommended for most users)")
        print("2. OAuth (required for restricted Google Workspace)")
        
        while True:
            choice = input("\nChoose authentication method (1 or 2): ").strip()
            if choice in ['1', '2']:
                break
            print("❌ Please enter 1 or 2")
        
        if choice == '1':
            auth_config = setup_service_account()
        else:
            auth_config = setup_oauth()
        
        if not auth_config:
            print("❌ Authentication setup failed")
            return
        
        # Step 3: Configure folder
        print("\n📋 STEP 3: Configure Sync Folder")
        folder_id = get_folder_setup()
        
        # Step 4: Test configuration
        print("\n📋 STEP 4: Test Configuration")
        if not await test_setup(auth_config, folder_id):
            print("❌ Setup test failed")
            return
        
        # Step 5: Update configuration files
        print("\n📋 STEP 5: Update Configuration")
        webhook_url = await setup_webhooks_and_indexing(folder_id)
        update_env_file(auth_config, folder_id, webhook_url)
        
        # Step 6: Final verification
        print("\n📋 STEP 6: Final Verification")
        print("✅ Setup completed successfully!")
        print("\nYour new configuration:")
        print(f"   Authentication: {auth_config['auth_method']}")
        print(f"   Folder ID: {folder_id}")
        if webhook_url:
            print(f"   Webhook URL: {webhook_url}")
        
        print("\n🎉 Your NerdsIQ system is now configured!")
        print("   • Documents will be synced from the new Google Drive folder")
        print("   • Authentication is configured and tested")
        if webhook_url:
            print("   • Automatic sync is enabled via webhooks")
        print("   • Initial indexing has been completed")
        
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        logger.exception("Setup error")


if __name__ == "__main__":
    asyncio.run(main())