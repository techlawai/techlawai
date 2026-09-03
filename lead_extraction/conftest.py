"""Fixtures for the extract.py tests.

The stubs themselves live in lead_fakes, which installs them at import time --
importing it here guarantees they are in place before any test module imports
the code under test.
"""
import sys

import pytest

from lead_fakes import Credentials, FakeClient, FakeSpreadsheet, FakeWorksheet, extract


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
