import math
from datetime import date
from decimal import Decimal


def format_filename(purchase_date: date, amount: Decimal, extension: str = "") -> str:
    """Produce the Drive filename from a date and amount.

    Format: mm_dd_yy_price
    Example: date=2026-02-20, amount=45.60 -> "02_20_26_46"
    Price is always rounded UP to the nearest whole dollar (ceiling).

    Args:
        purchase_date: The date of the purchase.
        amount:        The bill amount as a Decimal.
        extension:     Optional file extension e.g. ".pdf" or ".png".

    Returns:
        Filename string e.g. "02_20_26_46.pdf"
    """
    mm = purchase_date.strftime("%m")
    dd = purchase_date.strftime("%d")
    yy = purchase_date.strftime("%y")
    price = math.ceil(float(amount))
    name = f"{mm}_{dd}_{yy}_{price}"
    return f"{name}{extension}" if extension else name
