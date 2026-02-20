from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from models.data_models import SheetRow
from utils.logger import get_logger

logger = get_logger(__name__)


class SheetsClient:
    """Appends rows to a Google Sheet."""

    def __init__(
        self,
        credentials: Credentials,
        spreadsheet_id: str,
        sheet_name: str = "Sheet1",
    ):
        self.service = build("sheets", "v4", credentials=credentials)
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name

    def append_row(self, row: SheetRow) -> None:
        """Add one row to the bottom of the sheet.

        Columns (in order): Date | Item | Amount | Drive Link
        """
        values = [[
            row.purchase_date,   # e.g. "2026-02-20"
            row.item_name,       # e.g. "Pharmacy copay"
            row.amount,          # e.g. "$45.60"
            row.drive_link,      # clickable Drive URL
        ]]

        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{self.sheet_name}!A:D",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()

        logger.info(
            f"Logged → {row.purchase_date} | {row.item_name} | {row.amount}"
        )
