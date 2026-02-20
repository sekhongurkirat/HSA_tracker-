import base64
import json

import anthropic

from agent.prompts import CLASSIFICATION_PROMPT
from models.data_models import HSAResult
from utils.logger import get_logger

logger = get_logger(__name__)


class Classifier:
    """Sends an email screenshot or PDF to Claude and asks:
    'Is there an HSA-eligible expense in this document?'
    """

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def classify(self, content: bytes, mime_type: str) -> HSAResult:
        """Classify a single image or PDF.

        Args:
            content:   Raw bytes of a PNG screenshot or PDF.
            mime_type: Either "image/png" or "application/pdf".

        Returns:
            HSAResult with is_hsa_eligible, confidence, and reason.
        """
        logger.info(f"Classifying document ({mime_type}, {len(content)} bytes)")

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
                        {"type": "text", "text": CLASSIFICATION_PROMPT},
                    ],
                }
            ],
        )

        raw = response.content[0].text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        logger.debug(f"Classifier raw response: {raw}")

        try:
            data = json.loads(raw)
            result = HSAResult(
                is_hsa_eligible=bool(data["is_hsa_eligible"]),
                confidence=float(data["confidence"]),
                reason=str(data.get("reason", "")),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse classifier response: {e} — raw: {raw}")
            result = HSAResult(is_hsa_eligible=False, confidence=0.0, reason="Parse error")

        logger.info(
            f"Classification result: eligible={result.is_hsa_eligible} "
            f"confidence={result.confidence:.2f} reason='{result.reason}'"
        )
        return result
