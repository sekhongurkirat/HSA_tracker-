from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from utils.logger import get_logger

logger = get_logger(__name__)

# Permissions we ask Google for — Drive (upload only) + Sheets (read/write)
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_credentials(credentials_path: str, token_path: str) -> Credentials:
    """Load saved Google credentials, refreshing or re-authorising as needed.

    First run:
        Opens a browser window where you log in to Google and grant access.
        Saves a token.json so you never have to do this again.

    Subsequent runs:
        Reads token.json and silently refreshes it in the background.

    Args:
        credentials_path: Path to the credentials.json downloaded from
                          Google Cloud Console.
        token_path:       Where to store (and later read) the saved token.
    """
    creds = None
    token_file = Path(token_path)

    # Try to load a previously saved token
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    # If there's no valid token, get one
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token exists but expired — refresh silently
            logger.info("Refreshing expired Google token…")
            creds.refresh(Request())
        else:
            # No token at all — open browser for first-time login
            logger.info("Opening browser for Google authorisation…")
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the token so we don't need to log in again
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json())
        logger.info(f"Google token saved to {token_file}")

    return creds
