"""Shared fixtures for the extract.py tests.

extract.py imports gspread and google-auth at module scope, and open_sheet()
authenticates against Google. These stubs replace both libraries before
extract is imported, so the suite is hermetic: no service account key, no
network, and no dependency on the real client libraries being importable.

gspread.authorize() defaults to raising, so any test that reaches the sheet
without asking for it fails loudly. Tests that do expect sheet access take the
`fake_sheets` fixture, which installs a fake client for the duration.
"""
import sys
import types

import pytest


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

import extract  # noqa: E402  (must be imported after the stubs above)


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
        if name not in self.worksheets:
            raise WorksheetNotFound(name)
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


@pytest.fixture(autouse=True)
def reset_credential_calls():
    Credentials.calls.clear()
    yield
    Credentials.calls.clear()


@pytest.fixture
def fake_sheets(monkeypatch):
    """Install a fake gspread client. Returns (spreadsheet, client)."""

    def _install(worksheets=None):
        spreadsheet = FakeSpreadsheet(worksheets)
        client = FakeClient(spreadsheet)
        monkeypatch.setattr(extract.gspread, "authorize", lambda creds: client)
        return spreadsheet, client

    return _install


@pytest.fixture
def leads_worksheet():
    """A worksheet that already carries the expected header row."""
    return FakeWorksheet(row1=extract.HEADER)


@pytest.fixture
def feed_input(monkeypatch):
    """Feed a scripted sequence of answers to input()."""

    def _feed(values):
        answers = iter(values)
        monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    return _feed


@pytest.fixture
def run_main(monkeypatch):
    """Run extract.main() with the given CLI arguments."""

    def _run(argv):
        monkeypatch.setattr(sys, "argv", ["extract.py", *argv])
        return extract.main()

    return _run
