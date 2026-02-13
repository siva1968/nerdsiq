#!/usr/bin/env python
"""Test Google Drive folder access for a specific folder ID."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_folder_access(folder_id: str):
    """Test access to a specific Google Drive folder."""
    try:
        from app.services.drive_service import DriveService
        
        print(f"🧪 Testing access to folder: {folder_id}")
        
        drive_service = DriveService()
        
        # Test folder access
        folder_info = drive_service.service.files().get(
            fileId=folder_id,
            fields="id,name,webViewLink,modifiedTime,owners,permissions"
        ).execute()
        
        print("✅ Folder access successful!")
        print(f"   Name: {folder_info.get('name')}")
        print(f"   URL: {folder_info.get('webViewLink')}")
        print(f"   Last modified: {folder_info.get('modifiedTime')}")
        
        # Test file listing
        files = drive_service.list_files_recursive(folder_id)
        document_files = [f for f in files if f.get('mimeType') != 'application/vnd.google-apps.folder']
        folder_count = len(files) - len(document_files)
        
        print(f"✅ Found {len(document_files)} documents in {folder_count} folders")
        
        # Show structure
        folders = [f for f in files if f.get('mimeType') == 'application/vnd.google-apps.folder']
        if folders:
            print("   📁 Folder structure:")
            for folder in folders[:10]:  # Show first 10 folders
                print(f"   • {folder.get('name')}")
            if len(folders) > 10:
                print(f"   ... and {len(folders) - 10} more folders")
        
        return True
        
    except Exception as e:
        print(f"❌ Access failed: {e}")
        return False


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Google Drive folder access")
    parser.add_argument("folder_id", help="Google Drive folder ID to test")
    
    args = parser.parse_args()
    
    success = test_folder_access(args.folder_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()