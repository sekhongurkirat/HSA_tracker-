from models.data_models import EmailMessage
from utils.logger import get_logger

logger = get_logger(__name__)

PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}


def extract_pdfs(message: EmailMessage) -> list[bytes]:
    """Return the raw bytes of any PDF attachments found in the email.

    Most medical billing emails attach the bill as a PDF.
    Returns a list because some emails include multiple PDFs
    (e.g. itemised bill + summary).
    """
    pdfs = []
    for attachment in message.attachments:
        if attachment.mime_type.lower() in PDF_MIME_TYPES or attachment.filename.lower().endswith(".pdf"):
            if _is_valid_pdf(attachment.content):
                logger.debug(f"Found valid PDF attachment: {attachment.filename}")
                pdfs.append(attachment.content)
            else:
                logger.warning(f"Attachment '{attachment.filename}' has PDF mime type but invalid content — skipping")
    return pdfs


def _is_valid_pdf(content: bytes) -> bool:
    """Quick check that the bytes start with the PDF magic number."""
    return content[:4] == b"%PDF"
