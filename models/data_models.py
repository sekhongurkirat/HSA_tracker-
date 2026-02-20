from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class Attachment:
    """A file attached to an email (e.g. a PDF bill)."""
    filename: str
    mime_type: str
    content: bytes


@dataclass
class EmailMessage:
    """Parsed representation of a raw IMAP email."""
    message_id: str
    from_address: str
    subject: str
    date: date
    body_html: str
    body_text: str
    attachments: list[Attachment] = field(default_factory=list)


@dataclass
class HSAResult:
    """What Claude returns after classifying an email for HSA eligibility."""
    is_hsa_eligible: bool
    confidence: float     # 0.0 – 1.0
    reason: str


@dataclass
class ExtractedData:
    """What Claude returns after extracting structured data from an HSA receipt."""
    purchase_date: Optional[date]
    item_name: Optional[str]
    amount: Optional[Decimal]


@dataclass
class SheetRow:
    """One row written to the Google Sheet."""
    purchase_date: str    # formatted as YYYY-MM-DD
    item_name: str
    amount: str           # formatted as "$45.60"
    drive_link: str
