from utils.logger import get_logger

logger = get_logger(__name__)


def render_email_to_screenshot(html: str, text_fallback: str = "") -> bytes:
    """Render email HTML to a PNG screenshot using a headless browser.

    Playwright launches a hidden Chromium browser, loads the HTML,
    and takes a full-page screenshot — exactly how an email client
    would display it. Returns PNG bytes.

    Falls back to a plain-text image via Pillow if HTML is empty.
    """
    from playwright.sync_api import sync_playwright

    content = html or text_fallback
    if not content:
        raise ValueError("Email has neither HTML body nor text body to screenshot")

    if not html and text_fallback:
        logger.debug("No HTML body — rendering plain text as image")
        return _text_to_image(text_fallback)

    logger.debug("Rendering email HTML to screenshot via Playwright")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 900, "height": 1200})

        # Wrap raw HTML in a basic page if it lacks a doctype
        if not content.strip().lower().startswith("<!doctype") and "<html" not in content.lower():
            content = f"<html><body style='font-family:sans-serif;padding:20px'>{content}</body></html>"

        page.set_content(content, wait_until="networkidle")
        screenshot = page.screenshot(full_page=True)
        browser.close()

    logger.debug(f"Screenshot captured: {len(screenshot)} bytes")
    return screenshot


def _text_to_image(text: str) -> bytes:
    """Convert plain text to a PNG image using Pillow as a last resort."""
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (900, max(400, 20 * text.count("\n") + 100)), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 20), text[:3000], fill="black", font=font)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
