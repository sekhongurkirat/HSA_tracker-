"""
HSA Tracker — entry point.

Starts one email monitor per configured IMAP account, each running in its
own background thread. When an email arrives, the HSAAgent processes it:
classify → extract → upload to Drive → log to Sheets.

Stop the agent at any time with Ctrl+C.
"""

import signal
import sys
import threading

from config import load_settings
from agent.hsa_agent import HSAAgent
from email_monitor.imap_monitor import IMAPMonitor
from email_monitor.polling_monitor import PollingMonitor
from google_services.auth import get_credentials
from google_services.drive_client import DriveClient
from google_services.sheets_client import SheetsClient
from utils.dedup_store import DedupStore
from utils.logger import get_logger, setup_logging


def main() -> None:
    # ── 1. Load config from .env ─────────────────────────────────────────────
    settings = load_settings()
    setup_logging(log_level=settings.log_level, log_file=settings.log_file or "")
    logger = get_logger(__name__)
    logger.info("HSA Tracker starting…")

    # ── 2. Authenticate with Google (opens browser on first run) ─────────────
    logger.info("Loading Google credentials…")
    credentials = get_credentials(
        credentials_path=settings.google_credentials_file,
        token_path=settings.google_token_file,
    )

    # ── 3. Build Google service clients ──────────────────────────────────────
    drive_client = DriveClient(
        credentials=credentials,
        folder_id=settings.google_drive_folder_id,
    )
    sheets_client = SheetsClient(
        credentials=credentials,
        spreadsheet_id=settings.google_sheets_spreadsheet_id,
        sheet_name=settings.google_sheets_sheet_name,
    )

    # ── 4. Build the agent ───────────────────────────────────────────────────
    dedup_store = DedupStore(db_path=settings.dedup_db_path)
    agent = HSAAgent(
        settings=settings,
        drive_client=drive_client,
        sheets_client=sheets_client,
        dedup_store=dedup_store,
    )

    # Lock so two monitors processing emails at the same time don't collide
    agent_lock = threading.Lock()

    def on_message(message):
        with agent_lock:
            try:
                agent.process(message)
            except Exception as e:
                logger.error(f"Unhandled error processing email: {e}", exc_info=True)

    # ── 5. Start one monitor per IMAP account ────────────────────────────────
    monitors = []
    for account in settings.imap_accounts:
        if settings.monitor_mode == "idle":
            monitor = IMAPMonitor(**account)
        else:
            monitor = PollingMonitor(
                **account,
                interval_minutes=settings.poll_interval_minutes,
            )

        thread = threading.Thread(
            target=monitor.start,
            args=(on_message,),
            daemon=True,
            name=f"monitor-{account['username']}",
        )
        thread.start()
        monitors.append(monitor)
        logger.info(
            f"Monitoring [{settings.monitor_mode}]: {account['username']} / {account['mailbox']}"
        )

    logger.info(f"Watching {len(monitors)} account(s). Press Ctrl+C to stop.")

    # ── 6. Wait until Ctrl+C, then shut down cleanly ─────────────────────────
    def shutdown(sig, frame):
        logger.info("Shutting down…")
        for monitor in monitors:
            monitor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep the main thread alive
    import time
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
