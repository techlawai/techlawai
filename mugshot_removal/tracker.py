"""Track sent removal requests and their compliance deadline in a Google
Sheet, across whichever state's statute applies to each request."""
from datetime import date, timedelta

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADER = [
    "Client Name",
    "State",
    "Target URL",
    "Contact Email",
    "Request Sent Date",
    "Deadline",
    "Status",
    "Notes",
    "Registrant Org",
    "Registrant Name",
    "Registrant Email",
    "Registrar",
    "Hosting Org",
    "Hosting Abuse Email",
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


def log_request(ws, client_name: str, state: str, target_url: str, contact_email: str,
                 deadline_days: int | None, sent_date: date | None = None,
                 status: str = "Pending", notes: str = ""):
    sent_date = sent_date or date.today()
    deadline = (sent_date + timedelta(days=deadline_days)).isoformat() if deadline_days else "N/A (verify statute)"
    ws.append_row([
        client_name,
        state,
        target_url,
        contact_email,
        sent_date.isoformat(),
        deadline,
        status,
        notes,
        "", "", "", "", "", "",
    ], value_input_option="USER_ENTERED")


def list_overdue(ws) -> list[dict]:
    """Return rows whose deadline has passed and status is still Pending.
    Rows with a non-date deadline (unconfirmed-statute states) are skipped
    rather than guessed at."""
    today = date.today()
    rows = ws.get_all_records()
    overdue = []
    for row in rows:
        if row.get("Status") != "Pending":
            continue
        try:
            deadline = date.fromisoformat(row["Deadline"])
        except (ValueError, KeyError):
            continue
        if deadline < today:
            overdue.append(row)
    return overdue


def record_owner_info(ws, target_url: str, lookup_result: dict):
    """Write registrant/hosting lookup results into the row matching
    target_url (the most recent matching row if there are several)."""
    domain_info = lookup_result.get("domain_info", {})
    hosting_info = lookup_result.get("hosting_info", {})

    cell = None
    matches = ws.findall(target_url)
    if matches:
        cell = matches[-1]
    if cell is None:
        return False

    row = cell.row
    ws.update(range_name=f"I{row}:N{row}", values=[[
        domain_info.get("registrant_org") or "",
        domain_info.get("registrant_name") or "",
        domain_info.get("registrant_email") or "",
        domain_info.get("registrar") or "",
        hosting_info.get("hosting_org") or "",
        hosting_info.get("abuse_email") or "",
    ]])
    return True
