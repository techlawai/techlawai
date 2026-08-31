"""Track sent removal requests and their 10-day compliance deadline in a
Google Sheet."""
from datetime import date, timedelta

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADER = [
    "Client Name",
    "Target URL",
    "Contact Email",
    "Request Sent Date",
    "Deadline (10 days)",
    "Status",
    "Notes",
]


def open_tracker(sheet_id: str, creds_path: str, worksheet_name: str = "Removal Requests"):
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)
    try:
        ws = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=len(HEADER))
    if ws.row_values(1) != HEADER:
        ws.update(range_name="A1", values=[HEADER])
    return ws


def log_request(ws, client_name: str, target_url: str, contact_email: str,
                 sent_date: date | None = None, status: str = "Pending", notes: str = ""):
    sent_date = sent_date or date.today()
    deadline = sent_date + timedelta(days=10)
    ws.append_row([
        client_name,
        target_url,
        contact_email,
        sent_date.isoformat(),
        deadline.isoformat(),
        status,
        notes,
    ], value_input_option="USER_ENTERED")


def list_overdue(ws) -> list[dict]:
    """Return rows whose deadline has passed and status is still Pending."""
    today = date.today()
    rows = ws.get_all_records()
    overdue = []
    for row in rows:
        if row.get("Status") == "Pending":
            deadline = date.fromisoformat(row["Deadline (10 days)"])
            if deadline < today:
                overdue.append(row)
    return overdue
