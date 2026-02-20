import io

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from utils.logger import get_logger

logger = get_logger(__name__)


class DriveClient:
    """Uploads files to a specific Google Drive folder."""

    def __init__(self, credentials: Credentials, folder_id: str):
        self.service = build("drive", "v3", credentials=credentials)
        self.folder_id = folder_id

    def upload_file(self, filename: str, content: bytes, mime_type: str) -> str:
        """Upload a file to the configured Drive folder.

        Args:
            filename:  The name to give the file in Drive (e.g. "02_20_26_46.pdf").
            content:   Raw file bytes (PDF or PNG).
            mime_type: "application/pdf" or "image/png".

        Returns:
            A direct link to the file in Google Drive.
            The file stays private — only visible when you're logged in to your Google account.
        """
        file_metadata = {
            "name": filename,
            "parents": [self.folder_id],
        }

        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type)

        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink",
        ).execute()

        link = file.get("webViewLink", "")
        logger.info(f"Uploaded '{filename}' → {link}")
        return link
