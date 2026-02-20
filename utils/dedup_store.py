import os
import sqlite3
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)


class DedupStore:
    """SQLite-backed store that tracks which email message IDs have already
    been processed. Prevents duplicate Drive uploads and Sheet rows."""

    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_messages (
                message_id   TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def already_processed(self, message_id: str) -> bool:
        """Return True if this message_id has been seen before."""
        row = self.conn.execute(
            "SELECT 1 FROM processed_messages WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        return row is not None

    def mark_processed(self, message_id: str) -> None:
        """Record that this message_id has been fully handled."""
        self.conn.execute(
            "INSERT OR IGNORE INTO processed_messages (message_id, processed_at) VALUES (?, ?)",
            (message_id, datetime.utcnow().isoformat()),
        )
        self.conn.commit()
        logger.debug(f"Marked as processed: {message_id}")

    def close(self) -> None:
        self.conn.close()
