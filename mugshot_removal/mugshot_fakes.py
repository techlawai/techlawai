"""Stubs and fakes for the mugshot_removal tests.

Every outbound integration this package has -- Google Sheets, Google Custom
Search, WHOIS, RDAP, DNS, SMTP -- is stubbed here, at import time, before the
modules under test are imported below. The suite therefore needs no
credentials, no API keys, and no network, and it never sends mail or writes to
a real sheet.

The stubs are deliberately dumb: they record what they were called with so
tests can assert on it, and they raise if a test reaches something it did not
ask for.

This lives in its own module rather than in conftest.py because the repo has
more than one test package: `from conftest import ...` resolves by sys.path
and would bind whichever conftest happened to be imported first.
"""
import sys
import types


# --- gspread / google-auth (tracker.py) ------------------------------------


class WorksheetNotFound(Exception):
    """Stand-in for gspread.WorksheetNotFound."""


def _unexpected_authorize(creds):
    raise AssertionError(
        "gspread.authorize() was called, but this test expected no sheet "
        "access. Use the fake_sheets fixture if the sheet should be opened."
    )


_gspread = types.ModuleType("gspread")
_gspread.WorksheetNotFound = WorksheetNotFound
_gspread.authorize = _unexpected_authorize
sys.modules["gspread"] = _gspread


class Credentials:
    """Stand-in for google.oauth2.service_account.Credentials."""

    calls = []

    @classmethod
    def from_service_account_file(cls, path, scopes=None):
        cls.calls.append({"path": path, "scopes": scopes})
        return f"creds:{path}"


_google = types.ModuleType("google")
_oauth2 = types.ModuleType("google.oauth2")
_service_account = types.ModuleType("google.oauth2.service_account")
_service_account.Credentials = Credentials
_google.oauth2 = _oauth2
_oauth2.service_account = _service_account
sys.modules["google"] = _google
sys.modules["google.oauth2"] = _oauth2
sys.modules["google.oauth2.service_account"] = _service_account


# --- googleapiclient (search.py) -------------------------------------------


class FakeCseQuery:
    def __init__(self, cse, kwargs):
        self._cse = cse
        self._kwargs = kwargs

    def execute(self):
        self._cse.calls.append(self._kwargs)
        if self._cse.responses:
            return self._cse.responses.pop(0)
        return {}


class FakeCse:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def list(self, **kwargs):
        return FakeCseQuery(self, kwargs)


class FakeSearchService:
    def __init__(self, responses=None):
        self._cse = FakeCse(responses)

    def cse(self):
        return self._cse


def _unexpected_build(*args, **kwargs):
    raise AssertionError(
        "googleapiclient.discovery.build() was called, but this test expected "
        "no search API access. Use the fake_search fixture."
    )


_googleapiclient = types.ModuleType("googleapiclient")
_discovery = types.ModuleType("googleapiclient.discovery")
_discovery.build = _unexpected_build
_googleapiclient.discovery = _discovery
sys.modules["googleapiclient"] = _googleapiclient
sys.modules["googleapiclient.discovery"] = _discovery


# --- whois / ipwhois (owner_lookup.py) -------------------------------------


def _unexpected_whois(domain):
    raise AssertionError(
        "whois.whois() was called, but this test expected no WHOIS lookup."
    )


_whois = types.ModuleType("whois")
_whois.whois = _unexpected_whois
sys.modules["whois"] = _whois


class _UnexpectedIPWhois:
    def __init__(self, ip):
        raise AssertionError(
            "IPWhois() was constructed, but this test expected no RDAP lookup."
        )


_ipwhois = types.ModuleType("ipwhois")
_ipwhois.IPWhois = _UnexpectedIPWhois
sys.modules["ipwhois"] = _ipwhois


# Imported only after every stub above is in place.
import draft  # noqa: E402,F401
import main  # noqa: E402,F401
import owner_lookup  # noqa: E402
import search  # noqa: E402,F401
import send  # noqa: E402,F401
import tracker  # noqa: E402


# --- sheet fakes ------------------------------------------------------------


class FakeWorksheet:
    def __init__(self, title="Removal Requests", row1=None, records=None):
        self.title = title
        self._row1 = list(row1) if row1 is not None else []
        self._records = list(records or [])
        self.appended = []
        self.updates = []
        self.findall_argument = None
        self._find_cells = {}

    def row_values(self, index):
        assert index == 1, "tracker only reads the header row"
        return list(self._row1)

    def update(self, range_name=None, values=None):
        self.updates.append((range_name, values))
        if range_name == "A1" and values:
            self._row1 = list(values[0])

    def append_row(self, row, value_input_option=None):
        self.appended.append((row, value_input_option))

    def get_all_records(self):
        return list(self._records)

    def set_find_results(self, target, cells):
        self._find_cells[target] = cells

    def findall(self, target):
        self.findall_argument = target
        return list(self._find_cells.get(target, []))


class FakeCell:
    def __init__(self, row, col=3):
        self.row = row
        self.col = col


class FakeSpreadsheet:
    def __init__(self, worksheets=None):
        self.worksheets = dict(worksheets or {})
        self.added = []

    def worksheet(self, name):
        # Raise whatever tracker.py will actually catch.
        if name not in self.worksheets:
            raise tracker.gspread.WorksheetNotFound(name)
        return self.worksheets[name]

    def add_worksheet(self, title, rows, cols):
        self.added.append({"title": title, "rows": rows, "cols": cols})
        worksheet = FakeWorksheet(title=title)
        self.worksheets[title] = worksheet
        return worksheet


class FakeClient:
    def __init__(self, spreadsheet):
        self.spreadsheet = spreadsheet
        self.opened = []

    def open_by_key(self, sheet_id):
        self.opened.append(sheet_id)
        return self.spreadsheet


# --- SMTP fake --------------------------------------------------------------


class FakeSMTP:
    """Records what a send would have done. Never opens a socket."""

    instances = []

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.logins = []
        self.sent = []
        self.entered = False
        self.exited = False
        FakeSMTP.instances.append(self)

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *exc_info):
        self.exited = True
        return False

    def login(self, username, password):
        self.logins.append((username, password))

    def sendmail(self, from_addr, to_addrs, message):
        self.sent.append((from_addr, to_addrs, message))
