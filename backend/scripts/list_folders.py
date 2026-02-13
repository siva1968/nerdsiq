#!/usr/bin/env python
"""Find accessible folders in Google Drive."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.drive_service import DriveService

def main():
    drive = DriveService()
    
    print('📁 Finding your accessible folders...')
    
    results = drive.service.files().list(
        q="mimeType='application/vnd.google-apps.folder'",
        pageSize=10,
        fields='files(id, name, webViewLink)'
    ).execute()

    folders = results.get('files', [])
    print(f'Found {len(folders)} accessible folders:')
    
    for folder in folders:
        print(f'📁 {folder["name"]}')
        print(f'   ID: {folder["id"]}')
        print(f'   URL: {folder["webViewLink"]}')
        print()

if __name__ == '__main__':
    main()