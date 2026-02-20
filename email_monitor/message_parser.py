import email
import email.policy
from datetime import date, datetime
from email.message import EmailMessage as StdEmailMessage

from models.data_models import Attachment, EmailMessage
from utils.logger import get_logger

logger = get_logger(__name__)


def parse_message(raw_bytes: bytes) -> EmailMessage:
    """Parse raw IMAP message bytes into a clean EmailMessage dataclass.

    Extracts:
    - message_id, from address, subject, date
    - HTML body (preferred) and plain-text body
    - Any PDF or image attachments
    """
    msg: StdEmailMessage = email.message_from_bytes(
        raw_bytes, policy=email.policy.default
    )

    message_id = msg.get("Message-ID", "").strip()
    from_address = msg.get("From", "").strip()
    subject = msg.get("Subject", "(no subject)").strip()
    received_date = _parse_date(msg.get("Date", ""))

    body_html = ""
    body_text = ""
    attachments: list[Attachment] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in disposition:
                filename = part.get_filename() or "attachment"
                content = part.get_payload(decode=True) or b""
                attachments.append(Attachment(
                    filename=filename,
                    mime_type=content_type,
                    content=content,
                ))
            elif content_type == "text/html" and not body_html:
                body_html = part.get_payload(decode=True).decode("utf-8", errors="replace")
            elif content_type == "text/plain" and not body_text:
                body_text = part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True) or b""
        if content_type == "text/html":
            body_html = payload.decode("utf-8", errors="replace")
        else:
            body_text = payload.decode("utf-8", errors="replace")

    logger.debug(f"Parsed email: subject='{subject}' from='{from_address}' attachments={len(attachments)}")

    return EmailMessage(
        message_id=message_id,
        from_address=from_address,
        subject=subject,
        date=received_date,
        body_html=body_html,
        body_text=body_text,
        attachments=attachments,
    )


def _parse_date(date_str: str) -> date:
    """Parse the email Date header into a Python date.
    Falls back to today if unparseable."""
    if not date_str:
        return datetime.today().date()
    try:
        parsed = email.utils.parsedate_to_datetime(date_str)
        return parsed.date()
    except Exception:
        return datetime.today().date()
