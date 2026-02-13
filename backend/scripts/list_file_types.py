"""Script to list all file types in the Google Drive folder."""

import sys
from pathlib import Path
from collections import Counter

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from app.services.drive_service import DriveService
from app.config import settings


def scan_file_types() -> None:
    """Scan Google Drive folder and list all file types with counts."""
    logger.info("🔍 Scanning Google Drive for file types...")
    
    drive_service = DriveService()
    folder_id = settings.google_drive_folder_id
    
    # Get all files recursively
    all_files = drive_service.list_files_recursive(folder_id)
    
    if not all_files:
        logger.warning("No files found in the folder")
        return
    
    # Count file types
    mime_types = Counter()
    extensions = Counter()
    file_details = []
    
    for file in all_files:
        mime_type = file.get("mimeType", "unknown")
        name = file.get("name", "")
        file_id = file.get("id", "")
        
        mime_types[mime_type] += 1
        
        # Get extension
        if "." in name:
            ext = "." + name.rsplit(".", 1)[1].lower()
            extensions[ext] += 1
        else:
            extensions["(no extension)"] += 1
        
        file_details.append({
            "name": name,
            "mime_type": mime_type,
            "id": file_id
        })
    
    # Print results
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 SCAN RESULTS: {len(all_files)} total files")
    logger.info(f"{'='*80}\n")
    
    # MIME types
    logger.info("📋 FILE TYPES (by MIME type):")
    logger.info(f"{'-'*80}")
    for mime_type, count in mime_types.most_common():
        logger.info(f"  {count:>4} files  │  {mime_type}")
    
    # Extensions
    logger.info(f"\n📁 FILE EXTENSIONS:")
    logger.info(f"{'-'*80}")
    for ext, count in extensions.most_common():
        logger.info(f"  {count:>4} files  │  {ext}")
    
    # Currently supported types
    supported_types = {
        "application/vnd.google-apps.document": "✅ Google Docs (supported)",
        "application/vnd.google-apps.spreadsheet": "✅ Google Sheets (supported)",
        "application/vnd.google-apps.presentation": "✅ Google Slides (supported)",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "✅ Word .docx (supported)",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "✅ PowerPoint .pptx (supported)",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "✅ Excel .xlsx (supported)",
        "application/pdf": "✅ PDF (supported)",
        "text/plain": "✅ Plain text (supported)",
        "text/csv": "✅ CSV (supported)",
        "text/html": "✅ HTML (supported)",
        "application/msword": "✅ Old Word .doc (supported)",
    }
    
    logger.info(f"\n🎯 INDEXING STATUS:")
    logger.info(f"{'-'*80}")
    
    supported_count = 0
    unsupported_count = 0
    
    for mime_type, count in mime_types.most_common():
        status = supported_types.get(mime_type, "❌ Not currently supported")
        logger.info(f"  {count:>4} files  │  {status}")
        logger.info(f"              │  {mime_type}")
        logger.info(f"{'-'*80}")
        
        if mime_type in supported_types:
            supported_count += count
        else:
            unsupported_count += count
    
    logger.info(f"\n📈 SUMMARY:")
    logger.info(f"  ✅ Supported files: {supported_count} ({supported_count/len(all_files)*100:.1f}%)")
    logger.info(f"  ❌ Unsupported files: {unsupported_count} ({unsupported_count/len(all_files)*100:.1f}%)")
    
    # Show sample of unsupported files
    unsupported_files = [f for f in file_details if f["mime_type"] not in supported_types]
    if unsupported_files:
        logger.info(f"\n⚠️  UNSUPPORTED FILES (samples):")
        logger.info(f"{'-'*80}")
        for file in unsupported_files[:10]:
            logger.info(f"  📄 {file['name']}")
            logger.info(f"     Type: {file['mime_type']}")
            logger.info(f"     ID: {file['id']}")
            logger.info(f"{'-'*80}")
        
        if len(unsupported_files) > 10:
            logger.info(f"  ... and {len(unsupported_files) - 10} more unsupported files")


if __name__ == "__main__":
    logger.info("🚀 Starting file type scan...")
    scan_file_types()
    logger.info("✅ Scan complete!")
