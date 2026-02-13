#!/usr/bin/env python
"""Check authentication and folder access."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.drive_service import DriveService

def main():
    # Extract folder ID from URL
    url = 'https://drive.google.com/drive/folders/1Z-LbB7TszXkzpZjwAcxvgUIXzPXNa0KB'
    folder_id = url.split('/folders/')[-1]
    print(f'📁 Extracted folder ID: {folder_id}')
    
    # Check authentication
    drive = DriveService()
    try:
        about = drive.service.about().get(fields='user').execute()
        user = about.get('user', {})
        print(f'🔐 Authenticated as: {user.get("emailAddress", "Unknown")}')
        print(f'📧 Display name: {user.get("displayName", "Unknown")}')
    except Exception as e:
        print(f'❌ Could not get user info: {e}')
        return
    
    # Try to list some accessible files to verify service works
    print('\n🔍 Testing service by listing recent files...')
    try:
        results = drive.service.files().list(
            pageSize=5,
            fields="files(id, name, mimeType)"
        ).execute()
        files = results.get('files', [])
        print(f'✓ Service working - found {len(files)} accessible files:')
        for file in files:
            print(f'  - {file["name"]} ({file["mimeType"]})')
    except Exception as e:
        print(f'❌ Service test failed: {e}')

if __name__ == '__main__':
    main()