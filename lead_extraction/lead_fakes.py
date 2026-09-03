"""Stubs and fakes for the extract.py tests.

extract.py imports gspread and google-auth at module scope, and open_sheet()
authenticates against Google. These stubs replace both libraries at import
time, before extract is imported below, so the suite is hermetic: no service
account key, no network, and no dependency on the real client libraries being
importable.

gspread.authorize() defaults to raising, so any test that reaches the sheet
without asking for it fails loudly. Tests that do expect sheet access take the
`fake_sheets` fixture, which installs a fake client for the duration.

This lives in its own module rather than in conftest.py because the repo has
more than one test package: `from conftest import ...` resolves by sys.path
and would bind whichever conftest happened to be imported first.
"""
import sys
import types


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

# Imported only after every stub above is in place.
import extract  # noqa: E402


class FakeWorksheet:
    def __init__(self, title="Leads", row1=None):
        self.title = title
        self._row1 = list(row1) if row1 is not None else []
        self.appended = []
        self.updates = []

    def row_values(self, index):
        assert index == 1, "extract only reads the header row"
        return list(self._row1)

    def update(self, range_name=None, values=None):
        self.updates.append((range_name, values))
        if range_name == "A1" and values:
            self._row1 = list(values[0])

    def append_rows(self, rows, value_input_option=None):
        self.appended.append((rows, value_input_option))


class FakeSpreadsheet:
    def __init__(self, worksheets=None):
        self.worksheets = dict(worksheets or {})
        self.added = []

    def worksheet(self, name):
        # Raise whatever extract.py will actually catch.
        if name not in self.worksheets:
            raise extract.gspread.WorksheetNotFound(name)
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
