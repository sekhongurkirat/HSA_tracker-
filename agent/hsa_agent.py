from config import Settings
from agent.classifier import Classifier
from agent.extractor import Extractor
from capture.pdf_handler import extract_pdfs
from capture.screenshot import render_email_to_screenshot
from google_services.drive_client import DriveClient
from google_services.sheets_client import SheetsClient
from models.data_models import EmailMessage, SheetRow
from utils.dedup_store import DedupStore
from utils.filename_formatter import format_filename
from utils.logger import get_logger

logger = get_logger(__name__)


class HSAAgent:
    """Orchestrates the full pipeline for a single email:

    1. Skip if already processed
    2. Capture — extract PDF or render screenshot
    3. Classify — ask Claude if HSA-eligible
    4. Extract — ask Claude for date, item, amount
    5. Upload — save file to Google Drive
    6. Log — append row to Google Sheet
    7. Mark as processed in dedup store
    """

    def __init__(
        self,
        settings: Settings,
        drive_client: DriveClient,
        sheets_client: SheetsClient,
        dedup_store: DedupStore,
    ):
        self.settings = settings
        self.classifier = Classifier(api_key=settings.anthropic_api_key, model=settings.claude_model)
        self.extractor = Extractor(api_key=settings.anthropic_api_key, model=settings.claude_model)
        self.drive_client = drive_client
        self.sheets_client = sheets_client
        self.dedup = dedup_store

    def process(self, message: EmailMessage) -> None:
        """Process a single incoming email message."""
        logger.info(f"Processing: '{message.subject}' from {message.from_address}")

        # ── Step 1: Skip duplicates ──────────────────────────────────────
        if self.dedup.already_processed(message.message_id):
            logger.info(f"Already processed — skipping: {message.message_id}")
            return

        # ── Step 2: Capture ──────────────────────────────────────────────
        # Prefer attached PDFs; fall back to HTML screenshot
        captures: list[tuple[bytes, str]] = []  # (content, mime_type)

        pdfs = extract_pdfs(message)
        if pdfs:
            logger.info(f"Using {len(pdfs)} PDF attachment(s)")
            for pdf in pdfs:
                captures.append((pdf, "application/pdf"))
        else:
            logger.info("No PDF found — rendering email as screenshot")
            try:
                screenshot = render_email_to_screenshot(message.body_html, message.body_text)
                captures.append((screenshot, "image/png"))
            except Exception as e:
                logger.error(f"Screenshot failed: {e} — skipping email")
                return

        # ── Steps 3–6: Classify → Extract → Upload → Log ────────────────
        any_eligible = False
        for content, mime_type in captures:
            result = self.classifier.classify(content, mime_type)

            if not result.is_hsa_eligible:
                logger.info(f"Not HSA-eligible (confidence={result.confidence:.2f}): {result.reason}")
                continue

            if result.confidence < self.settings.hsa_confidence_threshold:
                logger.info(
                    f"HSA-eligible but confidence {result.confidence:.2f} below "
                    f"threshold {self.settings.hsa_confidence_threshold} — skipping"
                )
                continue

            any_eligible = True

            # ── Step 4: Extract ──────────────────────────────────────────
            extracted = self.extractor.extract(content, mime_type, fallback_date=message.date)

            if extracted.amount is None:
                logger.warning(f"Could not extract amount from '{message.subject}' — skipping upload")
                continue

            # ── Step 5: Upload to Google Drive ───────────────────────────
            extension = ".pdf" if mime_type == "application/pdf" else ".png"
            filename = format_filename(extracted.purchase_date, extracted.amount, extension)

            drive_link = self.drive_client.upload_file(
                filename=filename,
                content=content,
                mime_type=mime_type,
            )
            logger.info(f"Uploaded to Drive: {filename} → {drive_link}")

            # ── Step 6: Log to Google Sheet ──────────────────────────────
            row = SheetRow(
                purchase_date=extracted.purchase_date.strftime("%Y-%m-%d"),
                item_name=extracted.item_name,
                amount=f"${extracted.amount:.2f}",
                drive_link=drive_link,
            )
            self.sheets_client.append_row(row)
            logger.info(f"Logged to Sheet: {row.purchase_date} | {row.item_name} | {row.amount}")

        # ── Step 7: Mark as processed ────────────────────────────────────
        if any_eligible:
            self.dedup.mark_processed(message.message_id)
            logger.info(f"Done: {message.subject}")
        else:
            # Still mark as processed so we don't re-check non-HSA emails
            self.dedup.mark_processed(message.message_id)
            logger.info(f"No HSA-eligible items found in: '{message.subject}'")
