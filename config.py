import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return val


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _load_imap_accounts() -> list[dict]:
    """Load one or more IMAP account configs from env vars.
    Account 1 uses plain keys (IMAP_HOST, etc.).
    Additional accounts use suffixed keys (IMAP_HOST_2, IMAP_HOST_3, etc.).
    """
    accounts = []
    for suffix in ["", "_2", "_3", "_4", "_5"]:
        host = os.getenv(f"IMAP_HOST{suffix}")
        if not host:
            continue
        accounts.append({
            "host": host,
            "port": int(os.getenv(f"IMAP_PORT{suffix}", "993")),
            "username": _require(f"IMAP_USERNAME{suffix}"),
            "password": _require(f"IMAP_PASSWORD{suffix}"),
            "mailbox": os.getenv(f"IMAP_MAILBOX{suffix}", "INBOX"),
        })
    if not accounts:
        raise EnvironmentError("No IMAP accounts configured. Set at least IMAP_HOST, IMAP_USERNAME, IMAP_PASSWORD.")
    return accounts


@dataclass
class Settings:
    # Claude
    anthropic_api_key: str
    claude_model: str

    # Email
    imap_accounts: list[dict]

    # Monitoring
    monitor_mode: str           # "idle" or "poll"
    poll_interval_minutes: int

    # Google
    google_credentials_file: str
    google_token_file: str
    google_drive_folder_name: str
    google_drive_folder_id: str
    google_sheets_spreadsheet_id: str
    google_sheets_sheet_name: str

    # Agent
    hsa_confidence_threshold: float

    # Storage
    dedup_db_path: str

    # Logging
    log_level: str
    log_file: str


def load_settings() -> Settings:
    return Settings(
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        claude_model=_optional("CLAUDE_MODEL", "claude-opus-4-6"),
        imap_accounts=_load_imap_accounts(),
        monitor_mode=_optional("MONITOR_MODE", "idle").lower(),
        poll_interval_minutes=int(_optional("POLL_INTERVAL_MINUTES", "15")),
        google_credentials_file=_optional("GOOGLE_CREDENTIALS_FILE", "credentials/google_credentials.json"),
        google_token_file=_optional("GOOGLE_TOKEN_FILE", "credentials/google_token.json"),
        google_drive_folder_name=_optional("GOOGLE_DRIVE_FOLDER_NAME", "HSA Receipts"),
        google_drive_folder_id=_optional("GOOGLE_DRIVE_FOLDER_ID", ""),
        google_sheets_spreadsheet_id=_require("GOOGLE_SHEETS_SPREADSHEET_ID"),
        google_sheets_sheet_name=_optional("GOOGLE_SHEETS_SHEET_NAME", "HSA Log"),
        hsa_confidence_threshold=float(_optional("HSA_CONFIDENCE_THRESHOLD", "0.75")),
        dedup_db_path=_optional("DEDUP_DB_PATH", "data/processed_messages.db"),
        log_level=_optional("LOG_LEVEL", "INFO"),
        log_file=_optional("LOG_FILE", ""),
    )
