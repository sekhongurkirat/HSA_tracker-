import ssl
import time
from typing import Callable

from imapclient import IMAPClient

from email_monitor.base_monitor import BaseMonitor
from email_monitor.message_parser import parse_message
from models.data_models import EmailMessage
from utils.logger import get_logger

logger = get_logger(__name__)


class PollingMonitor(BaseMonitor):
    """Monitors an inbox by checking for new mail every N minutes.

    Use this when IMAP IDLE is not available or when running in an
    environment where persistent connections are unreliable.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        mailbox: str = "INBOX",
        interval_minutes: int = 15,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.mailbox = mailbox
        self.interval_seconds = interval_minutes * 60
        self._running = False

    def start(self, on_message: Callable[[EmailMessage], None]) -> None:
        logger.info(
            f"Starting polling monitor for {self.username} — "
            f"checking every {self.interval_seconds // 60} minutes"
        )
        self._running = True
        while self._running:
            try:
                self._check_inbox(on_message)
            except Exception as e:
                logger.error(f"Polling error: {e}")
            time.sleep(self.interval_seconds)

    def stop(self) -> None:
        self._running = False
        logger.info(f"Polling monitor stopped for {self.username}")

    def _check_inbox(self, on_message: Callable[[EmailMessage], None]) -> None:
        context = ssl.create_default_context()
        with IMAPClient(self.host, port=self.port, ssl=True, ssl_context=context) as client:
            client.login(self.username, self.password)
            client.select_folder(self.mailbox)
            from datetime import date
            today = date.today().strftime("%d-%b-%Y")
            uids = client.search(["UNSEEN", "SINCE", today])
            if not uids:
                logger.debug("No new messages")
                return
            logger.info(f"Found {len(uids)} new message(s) since {today}")
            for uid, data in client.fetch(uids, ["RFC822"]).items():
                raw = data.get(b"RFC822")
                if not raw:
                    continue
                try:
                    message = parse_message(raw)
                    on_message(message)
                except Exception as e:
                    logger.error(f"Failed to parse message UID {uid}: {e}")
