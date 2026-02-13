"""Test file type filtering."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.index_documents import should_index_file

# Test cases
test_files = [
    # Should be indexed
    {"name": "document.pdf", "mimeType": "application/pdf"},
    {"name": "spreadsheet.xlsx", "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    {"name": "data.csv", "mimeType": "text/csv"},
    {"name": "page.html", "mimeType": "text/html"},
    {"name": "readme.txt", "mimeType": "text/plain"},
    {"name": "Google Doc", "mimeType": "application/vnd.google-apps.document"},
    
    # Should NOT be indexed
    {"name": "image.png", "mimeType": "image/png"},
    {"name": "photo.jpg", "mimeType": "image/jpeg"},
    {"name": "video.mp4", "mimeType": "video/mp4"},
    {"name": "audio.mp3", "mimeType": "audio/mpeg"},
    {"name": "logo.svg", "mimeType": "image/svg+xml"},
    {"name": "folder", "mimeType": "application/vnd.google-apps.folder"},
    {"name": "shortcut", "mimeType": "application/vnd.google-apps.shortcut"},
]

print("File Type Filtering Test:")
print("=" * 60)

for file_info in test_files:
    result = should_index_file(file_info)
    status = "✅ INDEX" if result else "❌ SKIP"
    print(f"{status:12} | {file_info['name']:20} | {file_info['mimeType']}")

print("=" * 60)
