"""Track sent removal requests and their compliance deadline in a Google
Sheet, across whichever state's statute applies to each request."""
from datetime import date, timedelta

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

REQUEST_FIELDS = [
    "Client Name",
    "State",
    "Target URL",
    "Contact Email",
    "Consent Date",
    "Disposition",
    "Request Sent Date",
    "Deadline",
    "Status",
    "Notes",
]

# Columns filled in by check-overdue's registrant/hosting lookup, in the order
# record_owner_info() writes them. Each pairs a section of full_lookup()'s
# result with the key to read from it, so the sheet layout and the write stay
# in step -- they drifted apart once already.
LOOKUP_FIELDS = [
    ("Registrant Org", "domain_info", "registrant_org"),
    ("Registrant Name", "domain_info", "registrant_name"),
    ("Registrant Email", "domain_info", "registrant_email"),
    ("Registrar", "domain_info", "registrar"),
    ("Registrant Country", "domain_info", "country"),
    ("Hosting Org", "hosting_info", "hosting_org"),
    ("Hosting Abuse Email", "hosting_info", "abuse_email"),
    ("Hosting Country", "hosting_info", "hosting_country"),
    ("Hosting Address", "hosting_info", "hosting_address"),
]

HEADER = REQUEST_FIELDS + [label for label, _, _ in LOOKUP_FIELDS]


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
                 consent_date: date, deadline_days: int | None, sent_date: date | None = None,
                 status: str = "Pending", notes: str = "", disposition: str = ""):
    """consent_date is required: a request must not be logged (or sent --
    see main.py) without a recorded date the client authorized it."""
    sent_date = sent_date or date.today()
    deadline = (sent_date + timedelta(days=deadline_days)).isoformat() if deadline_days else "N/A (verify statute)"
    ws.append_row([
        client_name,
        state,
        target_url,
        contact_email,
        consent_date.isoformat(),
        disposition,
        sent_date.isoformat(),
        deadline,
        status,
        notes,
        *[""] * len(LOOKUP_FIELDS),
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


def _column_letter(index: int) -> str:
    """0-based column index to its A1 letter (A, B, ... Z, AA, ...)."""
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def record_owner_info(ws, target_url: str, lookup_result: dict):
    """Write registrant/hosting lookup results into the row matching
    target_url (the most recent matching row if there are several)."""
    cell = None
    matches = ws.findall(target_url)
    if matches:
        cell = matches[-1]
    if cell is None:
        return False

    values = [
        (lookup_result.get(section) or {}).get(key) or ""
        for _, section, key in LOOKUP_FIELDS
    ]

    row = cell.row
    first = _column_letter(len(REQUEST_FIELDS))
    last = _column_letter(len(HEADER) - 1)
    ws.update(range_name=f"{first}{row}:{last}{row}", values=[values])
    return True
