"""Fixtures for the mugshot_removal tests.

The stubs themselves live in mugshot_fakes, which installs them at import
time -- importing it here guarantees they are in place before any test module
imports the code under test.
"""
import sys

import pytest

from mugshot_fakes import (
    Credentials,
    FakeClient,
    FakeSMTP,
    FakeSearchService,
    FakeSpreadsheet,
    main,
    owner_lookup,
    search,
    send,
    tracker,
)


@pytest.fixture(autouse=True)
def reset_recorders():
    Credentials.calls.clear()
    FakeSMTP.instances.clear()
    yield
    Credentials.calls.clear()
    FakeSMTP.instances.clear()


@pytest.fixture
def fake_sheets(monkeypatch):
    """Install a fake gspread client. Returns (spreadsheet, client)."""

    def _install(worksheets=None):
        spreadsheet = FakeSpreadsheet(worksheets)
        client = FakeClient(spreadsheet)
        monkeypatch.setattr(tracker.gspread, "authorize", lambda creds: client)
        return spreadsheet, client

    return _install


@pytest.fixture
def tracker_worksheet():
    """A worksheet that already carries the tracker's header row."""
    from mugshot_fakes import FakeWorksheet

    return FakeWorksheet(row1=tracker.HEADER)


@pytest.fixture
def fake_search(monkeypatch):
    """Install a fake Custom Search service. Returns (service, build_calls)."""

    def _install(responses=None):
        service = FakeSearchService(responses)
        build_calls = []

        def _build(name, version, developerKey=None):
            build_calls.append(
                {"name": name, "version": version, "developerKey": developerKey}
            )
            return service

        monkeypatch.setattr(search, "build", _build)
        return service, build_calls

    return _install


@pytest.fixture
def fake_smtp(monkeypatch):
    """Route send.py's SMTP_SSL at the recording fake."""
    monkeypatch.setattr(send.smtplib, "SMTP_SSL", FakeSMTP)
    return FakeSMTP


@pytest.fixture
def fake_whois(monkeypatch):
    """Install a whois.whois() replacement returning the given record."""

    def _install(record=None, error=None):
        calls = []

        def _whois(domain):
            calls.append(domain)
            if error is not None:
                raise error
            return record

        monkeypatch.setattr(owner_lookup.whois, "whois", _whois)
        return calls

    return _install


@pytest.fixture
def fake_rdap(monkeypatch):
    """Install DNS resolution and IPWhois replacements."""

    def _install(ip="203.0.113.10", rdap=None, dns_error=None, rdap_error=None):
        calls = {"dns": [], "rdap": []}

        def _gethostbyname(domain):
            calls["dns"].append(domain)
            if dns_error is not None:
                raise dns_error
            return ip

        class _IPWhois:
            def __init__(self, address):
                self.address = address

            def lookup_rdap(self):
                calls["rdap"].append(self.address)
                if rdap_error is not None:
                    raise rdap_error
                return rdap or {}

        monkeypatch.setattr(owner_lookup.socket, "gethostbyname", _gethostbyname)
        monkeypatch.setattr(owner_lookup, "IPWhois", _IPWhois)
        return calls

    return _install


@pytest.fixture
def run_main(monkeypatch):
    """Run main.main() with the given CLI arguments."""

    def _run(argv):
        monkeypatch.setattr(sys, "argv", ["main.py", *argv])
        return main.main()

    return _run
