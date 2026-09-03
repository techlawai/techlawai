"""Tests for main.py -- CLI wiring, and the consent gate on `send`."""
import json
from datetime import date, timedelta

import pytest

import main

TOMORROW = (date.today() + timedelta(days=1)).isoformat()

SEND_ARGS = [
    "send",
    "--client-name", "Jane Public",
    "--client-email", "jane@example.com",
    "--target-url", "https://example-site.test/jane",
    "--to-email", "abuse@example-site.test",
    "--smtp-host", "smtp.example.test",
    "--smtp-username", "jane@example.com",
    "--smtp-password", "app-password",
]


@pytest.fixture
def sent(monkeypatch):
    """Capture send_removal_request calls instead of sending anything."""
    calls = []
    monkeypatch.setattr(main, "send_removal_request", lambda **kw: calls.append(kw))
    return calls


@pytest.fixture
def logged(monkeypatch):
    """Capture tracker interactions instead of touching a sheet."""
    calls = {"open": [], "log": []}
    sentinel = object()

    def _open_tracker(sheet_id, creds):
        calls["open"].append({"sheet_id": sheet_id, "creds": creds})
        return sentinel

    def _log_request(ws, *args, **kwargs):
        calls["log"].append({"ws": ws, "args": args, "kwargs": kwargs})

    monkeypatch.setattr(main, "open_tracker", _open_tracker)
    monkeypatch.setattr(main, "log_request", _log_request)
    calls["sentinel"] = sentinel
    return calls


class TestSendConsentGate:
    """`send` must refuse without a real, past-dated consent date -- this is
    the enforcement point for having the client's written authorization on
    file, so a refusal must happen before anything is transmitted."""

    def test_future_consent_date_refuses_to_send(self, run_main, sent):
        with pytest.raises(SystemExit) as exit_info:
            run_main([*SEND_ARGS, "--consent-date", TOMORROW])

        assert "Refusing to send" in str(exit_info.value)
        assert sent == []

    @pytest.mark.parametrize(
        "garbage", ["", "not-a-date", "08/25/2026", "2026-13-01", "2026-02-30"]
    )
    def test_unparseable_consent_date_refuses_to_send(self, run_main, sent, garbage):
        with pytest.raises(SystemExit) as exit_info:
            run_main([*SEND_ARGS, "--consent-date", garbage])

        assert "Refusing to send" in str(exit_info.value)
        assert sent == []

    def test_refusal_explains_what_the_date_means(self, run_main, sent):
        with pytest.raises(SystemExit) as exit_info:
            run_main([*SEND_ARGS, "--consent-date", TOMORROW])

        message = str(exit_info.value)
        assert "consent-form" in message
        assert "signed" in message

    def test_consent_date_is_mandatory(self, run_main, sent):
        with pytest.raises(SystemExit) as exit_info:
            run_main(SEND_ARGS)

        # argparse rejects the missing required flag before any work happens.
        assert exit_info.value.code == 2
        assert sent == []

    def test_nothing_is_logged_when_the_send_is_refused(self, run_main, sent, logged):
        with pytest.raises(SystemExit):
            run_main([*SEND_ARGS, "--consent-date", TOMORROW, "--sheet-id", "SHEET1"])

        assert logged["open"] == []
        assert logged["log"] == []


class TestSend:
    def test_sends_with_a_valid_consent_date(self, run_main, sent, capsys):
        run_main([*SEND_ARGS, "--consent-date", "2026-08-25"])

        assert len(sent) == 1
        assert "Sent to abuse@example-site.test" in capsys.readouterr().out

    def test_passes_smtp_and_address_details_through(self, run_main, sent):
        run_main([*SEND_ARGS, "--consent-date", "2026-08-25"])

        call = sent[0]
        assert call["smtp_host"] == "smtp.example.test"
        assert call["smtp_port"] == 465
        assert call["smtp_username"] == "jane@example.com"
        assert call["smtp_password"] == "app-password"
        assert call["client_email"] == "jane@example.com"
        assert call["to_email"] == "abuse@example-site.test"

    def test_sends_the_generated_letter(self, run_main, sent):
        run_main([*SEND_ARGS, "--consent-date", "2026-08-25"])

        body = sent[0]["letter_body"]
        assert "Jane Public" in body
        assert "https://example-site.test/jane" in body
        assert "Fla. Stat. § 901.43" in body

    def test_state_selects_the_statute(self, run_main, sent):
        run_main([*SEND_ARGS, "--consent-date", "2026-08-25", "--state", "CA"])

        assert "Cal. Civ. Code § 1798.91.1" in sent[0]["letter_body"]

    def test_no_sheet_id_means_no_tracker_write(self, run_main, sent, logged):
        run_main([*SEND_ARGS, "--consent-date", "2026-08-25"])

        assert logged["open"] == []
        assert logged["log"] == []

    def test_logs_to_the_tracker_when_a_sheet_is_given(
        self, run_main, sent, logged, capsys
    ):
        run_main([*SEND_ARGS, "--consent-date", "2026-08-25", "--sheet-id", "SHEET1"])

        assert logged["open"] == [{"sheet_id": "SHEET1", "creds": "service_account.json"}]
        entry = logged["log"][0]
        assert entry["ws"] is logged["sentinel"]
        assert entry["args"] == (
            "Jane Public",
            "FL",
            "https://example-site.test/jane",
            "abuse@example-site.test",
        )
        assert entry["kwargs"]["consent_date"] == date(2026, 8, 25)
        assert entry["kwargs"]["deadline_days"] == 10
        assert "Logged to tracker sheet." in capsys.readouterr().out

    def test_logs_the_states_own_deadline(self, run_main, sent, logged):
        run_main(
            [*SEND_ARGS, "--consent-date", "2026-08-25", "--sheet-id", "S", "--state", "CA"]
        )

        assert logged["log"][0]["kwargs"]["deadline_days"] is None


class TestDraft:
    def test_prints_the_letter(self, run_main, capsys):
        run_main([
            "draft",
            "--client-name", "Jane Public",
            "--client-contact", "jane@example.com",
            "--target-url", "https://example-site.test/jane",
        ])

        out = capsys.readouterr().out
        assert "My name is Jane Public" in out
        assert "Fla. Stat. § 901.43" in out

    def test_defaults_to_florida(self, run_main, capsys):
        run_main([
            "draft",
            "--client-name", "Jane Public",
            "--client-contact", "jane@example.com",
            "--target-url", "https://example-site.test/jane",
        ])

        assert "Fla. Stat. § 901.43" in capsys.readouterr().out

    def test_includes_optional_booking_details(self, run_main, capsys):
        run_main([
            "draft",
            "--client-name", "Jane Public",
            "--client-contact", "jane@example.com",
            "--target-url", "https://example-site.test/jane",
            "--booking-date", "2026-07-04",
            "--arresting-agency", "PBSO",
        ])

        out = capsys.readouterr().out
        assert "Booking date: 2026-07-04" in out
        assert "Arresting agency: PBSO" in out

    def test_unknown_state_is_an_error(self, run_main):
        with pytest.raises(KeyError):
            run_main([
                "draft",
                "--client-name", "Jane Public",
                "--client-contact", "jane@example.com",
                "--target-url", "https://example-site.test/jane",
                "--state", "ZZ",
            ])


class TestConsentForm:
    def test_prints_the_form_with_the_states_citation(self, run_main, capsys):
        run_main([
            "consent-form",
            "--client-name", "Jane Public",
            "--client-email", "jane@example.com",
            "--target-url", "https://example-site.test/jane",
            "--state", "CA",
        ])

        out = capsys.readouterr().out
        assert "AUTHORIZATION TO SEND BOOKING PHOTOGRAPH REMOVAL REQUEST" in out
        assert "Cal. Civ. Code § 1798.91.1" in out
        assert "jane@example.com" in out


class TestListStates:
    def test_prints_every_state_as_json(self, run_main, capsys):
        run_main(["list-states"])

        printed = json.loads(capsys.readouterr().out)
        assert printed == main.STATE_STATUTES


class TestSearch:
    def test_prints_results_as_json(self, run_main, monkeypatch, capsys):
        results = [{"title": "T", "link": "L", "snippet": "S"}]
        calls = []

        def _find(client_name, api_key, cx, num_results):
            calls.append((client_name, api_key, cx, num_results))
            return results

        monkeypatch.setattr(main, "find_mugshot_pages", _find)

        run_main([
            "search",
            "--client-name", "Jane Public",
            "--api-key", "KEY",
            "--cx", "CX",
        ])

        assert calls == [("Jane Public", "KEY", "CX", 20)]
        assert json.loads(capsys.readouterr().out) == results


class TestLookupOwner:
    def test_prints_the_lookup_as_json(self, run_main, monkeypatch, capsys):
        lookup = {"domain_info": {"domain": "example-site.test"}, "hosting_info": {}}
        monkeypatch.setattr(main, "full_lookup", lambda url: lookup)

        run_main(["lookup-owner", "--target-url", "https://example-site.test/jane"])

        assert json.loads(capsys.readouterr().out) == lookup


class TestCheckOverdue:
    def test_attaches_owner_lookup_to_each_overdue_row(
        self, run_main, monkeypatch, capsys
    ):
        rows = [
            {"Client Name": "Jane", "Target URL": "https://a.test/j"},
            {"Client Name": "John", "Target URL": "https://b.test/j"},
        ]
        lookups = {
            "https://a.test/j": {"domain_info": {"domain": "a.test"}},
            "https://b.test/j": {"domain_info": {"domain": "b.test"}},
        }
        recorded = []

        monkeypatch.setattr(main, "open_tracker", lambda sheet_id, creds: "WS")
        monkeypatch.setattr(main, "list_overdue", lambda ws: rows)
        monkeypatch.setattr(main, "full_lookup", lambda url: lookups[url])
        monkeypatch.setattr(
            main,
            "record_owner_info",
            lambda ws, url, result: recorded.append((ws, url, result)),
        )

        run_main(["check-overdue", "--sheet-id", "SHEET1"])

        printed = json.loads(capsys.readouterr().out)
        assert [row["owner_lookup"] for row in printed] == [
            lookups["https://a.test/j"],
            lookups["https://b.test/j"],
        ]
        assert [url for _, url, _ in recorded] == [
            "https://a.test/j",
            "https://b.test/j",
        ]

    def test_empty_when_nothing_is_overdue(self, run_main, monkeypatch, capsys):
        monkeypatch.setattr(main, "open_tracker", lambda sheet_id, creds: "WS")
        monkeypatch.setattr(main, "list_overdue", lambda ws: [])

        run_main(["check-overdue", "--sheet-id", "SHEET1"])

        assert json.loads(capsys.readouterr().out) == []


class TestArgumentParsing:
    def test_a_subcommand_is_required(self, run_main):
        with pytest.raises(SystemExit) as exit_info:
            run_main([])

        assert exit_info.value.code == 2

    def test_unknown_subcommand_is_rejected(self, run_main):
        with pytest.raises(SystemExit) as exit_info:
            run_main(["deliver"])

        assert exit_info.value.code == 2
