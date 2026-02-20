import ssl
import threading
import time
from typing import Callable

from imapclient import IMAPClient
from tenacity import retry, stop_after_attempt, wait_exponential

from email_monitor.base_monitor import BaseMonitor
from email_monitor.message_parser import parse_message
from models.data_models import EmailMessage
from utils.logger import get_logger

logger = get_logger(__name__)

IDLE_REFRESH_SECONDS = 20 * 60   # refresh IDLE every 20 min (server limit ~29 min)


class IMAPMonitor(BaseMonitor):
    """Monitors an inbox in real-time using IMAP IDLE.

    IMAP IDLE keeps a persistent connection open. The mail server sends
    a notification the moment a new message arrives — no polling needed.
    CPU usage between emails is effectively zero.
    """

    def __init__(self, host: str, port: int, username: str, password: str, mailbox: str = "INBOX"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.mailbox = mailbox
        self._client: IMAPClient | None = None
        self._stop_event = threading.Event()

    def start(self, on_message: Callable[[EmailMessage], None]) -> None:
        """Connect and begin IDLE loop. Blocks until stop() is called."""
        logger.info(f"Starting IMAP IDLE monitor for {self.username} on {self.host}")
        while not self._stop_event.is_set():
            try:
                self._run_idle_loop(on_message)
            except Exception as e:
                logger.error(f"IMAP connection error: {e}. Reconnecting in 30s...")
                time.sleep(30)

    def stop(self) -> None:
        self._stop_event.set()
        if self._client:
            try:
                self._client.logout()
            except Exception:
                pass
        logger.info(f"IMAP monitor stopped for {self.username}")

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=60))
    def _connect(self) -> IMAPClient:
        context = ssl.create_default_context()
        client = IMAPClient(self.host, port=self.port, ssl=True, ssl_context=context)
        client.login(self.username, self.password)
        client.select_folder(self.mailbox)
        logger.info(f"Connected to {self.host} as {self.username}")
        return client

    def _run_idle_loop(self, on_message: Callable[[EmailMessage], None]) -> None:
        self._client = self._connect()

        # Process any unread messages that arrived while we were offline
        self._fetch_unseen(on_message)

        while not self._stop_event.is_set():
            self._client.idle()
            logger.debug("Entered IDLE mode — waiting for new mail...")

            # Wait for server push or timeout after IDLE_REFRESH_SECONDS
            responses = self._client.idle_check(timeout=IDLE_REFRESH_SECONDS)
            self._client.idle_done()

            if responses:
                logger.debug(f"IDLE response received: {responses}")
                self._fetch_unseen(on_message)
            else:
                # Timeout — send IDLE refresh so server doesn't drop connection
                logger.debug("IDLE timeout — refreshing connection")

    def _fetch_unseen(self, on_message: Callable[[EmailMessage], None]) -> None:
        """Fetch UNSEEN messages received today or later only."""
        from datetime import date
        today = date.today().strftime("%d-%b-%Y")   # e.g. "20-Feb-2026"
        uids = self._client.search(["UNSEEN", "SINCE", today])
        if not uids:
            return
        logger.info(f"Found {len(uids)} unseen message(s) since {today}")
        for uid, data in self._client.fetch(uids, ["RFC822"]).items():
            raw = data.get(b"RFC822")
            if not raw:
                continue
            try:
                message = parse_message(raw)
                on_message(message)
            except Exception as e:
                logger.error(f"Failed to parse message UID {uid}: {e}")
