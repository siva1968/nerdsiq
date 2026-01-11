"""Google Drive integration service."""

import io
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from loguru import logger

from app.config import settings


class DriveService:
    """Service for interacting with Google Drive API."""

    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    def __init__(self) -> None:
        """Initialize Google Drive service."""
        credentials = service_account.Credentials.from_service_account_file(
            settings.google_service_account_file,
            scopes=self.SCOPES,
        )
        self.service = build("drive", "v3", credentials=credentials)

    def list_files(self, folder_id: str | None = None) -> list[dict[str, Any]]:
        """
        List all files in a folder.
        
        Args:
            folder_id: Google Drive folder ID (uses config default if not provided)
            
        Returns:
            List of file metadata dictionaries
        """
        folder_id = folder_id or settings.google_drive_folder_id
        
        query = f"'{folder_id}' in parents and trashed = false"
        
        results = self.service.files().list(
            q=query,
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, webViewLink, modifiedTime)",
        ).execute()
        
        files = results.get("files", [])
        logger.info(f"Found {len(files)} files in folder {folder_id}")
        
        return files

    def get_file_content(self, file_id: str) -> str:
        """
        Download and return file content as text.
        
        Supports Google Docs, Sheets, and plain text files.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File content as string
        """
        # Get file metadata
        file_meta = self.service.files().get(
            fileId=file_id,
            fields="mimeType, name",
        ).execute()
        
        mime_type = file_meta.get("mimeType", "")
        
        # Handle Google Docs - export as plain text
        if mime_type == "application/vnd.google-apps.document":
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType="text/plain",
            )
        # Handle Google Sheets - export as CSV
        elif mime_type == "application/vnd.google-apps.spreadsheet":
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType="text/csv",
            )
        # Handle regular files
        else:
            request = self.service.files().get_media(fileId=file_id)
        
        # Download content
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        
        done = False
        while not done:
            _, done = downloader.next_chunk()
        
        content = buffer.getvalue().decode("utf-8")
        logger.debug(f"Downloaded file: {file_meta.get('name')} ({len(content)} chars)")
        
        return content

    def get_file_url(self, file_id: str) -> str:
        """Get the web view URL for a file."""
        return f"https://drive.google.com/file/d/{file_id}/view"
