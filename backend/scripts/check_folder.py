#!/usr/bin/env python
"""Check Google Drive folder contents."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.drive_service import DriveService

def main():
    drive = DriveService()
    folder_id = '1Z-LbB7TszXkzpZjwAcxvgUIXzPXNa0KB'
    
    print('🔍 Detailed folder inspection...')
    
    # Check folder info
    try:
        folder_info = drive.service.files().get(
            fileId=folder_id, 
            fields='id,name,mimeType'
        ).execute()
        print(f'✓ Folder name: {folder_info["name"]}')
        print(f'✓ Folder type: {folder_info["mimeType"]}')
    except Exception as e:
        print(f'❌ Error accessing folder: {e}')
        return

    # List files in root folder
    files = drive.list_files(folder_id)
    print(f'📄 Files in root folder: {len(files)}')
    
    # List files recursively
    all_files = drive.list_files_recursive()
    print(f'📁 Total files (including subfolders): {len(all_files)}')
    
    # Show first few files
    if all_files:
        print('\n📋 First few files found:')
        for i, file in enumerate(all_files[:10]):
            print(f'  {i+1}. {file["name"]} ({file["mimeType"]})')
    else:
        print('\n⚠️  No files found in the folder or its subfolders')
        print('   This could mean:')
        print('   1. The folder is empty')
        print('   2. No permission to access files')
        print('   3. Files are not supported types')

if __name__ == '__main__':
    main()