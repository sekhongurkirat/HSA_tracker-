import base64
import json
from datetime import date, datetime
from decimal import Decimal

import anthropic

from agent.prompts import EXTRACTION_PROMPT
from models.data_models import ExtractedData
from utils.logger import get_logger

logger = get_logger(__name__)


class Extractor:
    """Sends a confirmed HSA receipt to Claude and extracts:
    - Date of purchase
    - Item / service name
    - Total amount
    """

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def extract(self, content: bytes, mime_type: str, fallback_date: date) -> ExtractedData:
        """Extract structured data from an HSA receipt image or PDF.

        Args:
            content:       Raw bytes of a PNG screenshot or PDF.
            mime_type:     Either "image/png" or "application/pdf".
            fallback_date: The email received date — used if Claude
                           cannot find the purchase date in the document.

        Returns:
            ExtractedData with purchase_date, item_name, and amount.
        """
        logger.info(f"Extracting data from document ({mime_type})")

        encoded = base64.standard_b64encode(content).decode("utf-8")

        if mime_type == "application/pdf":
            content_block = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": encoded,
                },
            }
        else:
            content_block = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": encoded,
                },
            }

        response = self.client.messages.create(
            model=self.model,
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": [
                        content_block,
                        {"type": "text", "text": EXTRACTION_PROMPT},
                    ],
                }
            ],
        )

        raw = response.content[0].text.strip()
        logger.debug(f"Extractor raw response: {raw}")

        try:
            data = json.loads(raw)

            # Parse date — fall back to email received date if null or invalid
            purchase_date = fallback_date
            if data.get("purchase_date"):
                try:
                    purchase_date = datetime.strptime(data["purchase_date"], "%Y-%m-%d").date()
                except ValueError:
                    logger.warning(f"Could not parse date '{data['purchase_date']}' — using email date")

            item_name = data.get("item_name") or "Unknown item"
            amount = Decimal(str(data["amount"])) if data.get("amount") is not None else None

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse extractor response: {e} — raw: {raw}")
            return ExtractedData(purchase_date=fallback_date, item_name="Unknown item", amount=None)

        result = ExtractedData(
            purchase_date=purchase_date,
            item_name=item_name,
            amount=amount,
        )
        logger.info(f"Extracted: date={result.purchase_date} item='{result.item_name}' amount={result.amount}")
        return result
