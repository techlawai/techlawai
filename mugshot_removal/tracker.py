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

# Where a request can stand. "Pending" is the only one list_overdue() acts on,
# so anything that closes or hands off a request must move it off "Pending".
STATUSES = ("Pending", "Removed", "Refused", "Escalated", "Withdrawn")


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


def _same_client(row: dict, client_name: str) -> bool:
    return str(row.get("Client Name", "")).strip().lower() == client_name.strip().lower()


def validate_status(status: str) -> str:
    """Match a status case-insensitively to one in STATUSES. Raises
    ValueError otherwise -- a typo must not silently take a request off the
    overdue check."""
    for known in STATUSES:
        if (status or "").strip().lower() == known.lower():
            return known
    raise ValueError(f"Unknown status '{status}'. Use one of: {', '.join(STATUSES)}.")


def update_status(ws, client_name: str, target_url: str, status: str,
                  note: str = "", on: date | None = None) -> bool:
    """Set the Status of this client's request for target_url (the most recent
    matching row if there are several), appending a dated note to Notes so
    the row keeps its history. Returns False if no row matches."""
    status = validate_status(status)
    on = on or date.today()
    rows = ws.get_all_records()
    match = None
    for index, row in enumerate(rows):
        if _same_client(row, client_name) and row.get("Target URL") == target_url:
            match = (index, row)
    if match is None:
        return False

    index, row = match
    entry = f"{on.isoformat()}: {status}" + (f" -- {note}" if note else "")
    notes = str(row.get("Notes") or "")
    notes = f"{notes}; {entry}" if notes else entry

    # Row 1 is the header, so record i sits on sheet row i + 2. Status and
    # Notes are adjacent, so one range write covers both.
    sheet_row = index + 2
    first = _column_letter(REQUEST_FIELDS.index("Status"))
    last = _column_letter(REQUEST_FIELDS.index("Notes"))
    ws.update(range_name=f"{first}{sheet_row}:{last}{sheet_row}", values=[[status, notes]])
    return True


def client_report(ws, client_name: str, today: date | None = None) -> list[dict]:
    """Every request logged for one client, each with how it stands against
    its deadline: days_remaining (negative once overdue) and overdue. Both
    are None where the deadline isn't a real date or the request is closed."""
    today = today or date.today()
    report = []
    for row in ws.get_all_records():
        if not _same_client(row, client_name):
            continue
        entry = {field: row.get(field, "") for field in REQUEST_FIELDS}
        entry["days_remaining"] = None
        entry["overdue"] = None
        if row.get("Status") == "Pending":
            try:
                deadline = date.fromisoformat(row["Deadline"])
            except (ValueError, KeyError):
                deadline = None
            if deadline is not None:
                entry["days_remaining"] = (deadline - today).days
                entry["overdue"] = deadline < today
        report.append(entry)
    return report


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
