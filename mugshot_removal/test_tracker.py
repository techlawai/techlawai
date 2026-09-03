"""Tests for tracker.py -- the Google Sheet request log and overdue check."""
from datetime import date, timedelta

import pytest

import tracker
from mugshot_fakes import Credentials, FakeCell, FakeWorksheet

TODAY = date.today()


def tracker_row(**overrides):
    """A get_all_records()-shaped row, defaulting to a still-pending request."""
    row = {
        "Client Name": "Jane Public",
        "State": "FL",
        "Target URL": "https://example-site.test/jane",
        "Contact Email": "abuse@example-site.test",
        "Consent Date": "2026-08-15",
        "Request Sent Date": "2026-08-19",
        "Deadline": (TODAY + timedelta(days=5)).isoformat(),
        "Status": "Pending",
        "Notes": "",
    }
    row.update(overrides)
    return row


class TestOpenTracker:
    def test_uses_existing_worksheet_and_leaves_good_header_alone(
        self, fake_sheets, tracker_worksheet
    ):
        _, client = fake_sheets({"Removal Requests": tracker_worksheet})

        worksheet = tracker.open_tracker("SHEET123", "creds.json")

        assert worksheet is tracker_worksheet
        assert client.opened == ["SHEET123"]
        assert tracker_worksheet.updates == []

    def test_writes_header_when_missing(self, fake_sheets):
        blank = FakeWorksheet(row1=[])
        fake_sheets({"Removal Requests": blank})

        tracker.open_tracker("SHEET123", "creds.json")

        assert blank.updates == [("A1", [tracker.HEADER])]

    def test_creates_worksheet_when_absent(self, fake_sheets):
        spreadsheet, _ = fake_sheets({})

        worksheet = tracker.open_tracker("SHEET123", "creds.json")

        assert spreadsheet.added == [
            {
                "title": "Removal Requests",
                "rows": 1000,
                "cols": len(tracker.HEADER),
            }
        ]
        assert worksheet.updates == [("A1", [tracker.HEADER])]

    def test_honors_custom_worksheet_name(self, fake_sheets):
        spreadsheet, _ = fake_sheets({})

        tracker.open_tracker("SHEET123", "creds.json", worksheet_name="August")

        assert spreadsheet.added[0]["title"] == "August"

    def test_loads_credentials_from_given_path(self, fake_sheets, tracker_worksheet):
        fake_sheets({"Removal Requests": tracker_worksheet})

        tracker.open_tracker("SHEET123", "/keys/service_account.json")

        assert Credentials.calls == [
            {"path": "/keys/service_account.json", "scopes": tracker.SCOPES}
        ]


class TestLogRequest:
    def test_row_matches_the_header_layout(self, tracker_worksheet):
        tracker.log_request(
            tracker_worksheet,
            "Jane Public",
            "FL",
            "https://example-site.test/jane",
            "abuse@example-site.test",
            consent_date=date(2026, 8, 15),
            deadline_days=10,
            sent_date=date(2026, 8, 19),
        )

        row, option = tracker_worksheet.appended[0]
        assert len(row) == len(tracker.HEADER)
        assert option == "USER_ENTERED"
        assert dict(zip(tracker.HEADER, row)) == {
            "Client Name": "Jane Public",
            "State": "FL",
            "Target URL": "https://example-site.test/jane",
            "Contact Email": "abuse@example-site.test",
            "Consent Date": "2026-08-15",
            "Request Sent Date": "2026-08-19",
            "Deadline": "2026-08-29",
            "Status": "Pending",
            "Notes": "",
            "Registrant Org": "",
            "Registrant Name": "",
            "Registrant Email": "",
            "Registrar": "",
            "Hosting Org": "",
            "Hosting Abuse Email": "",
        }

    def test_deadline_is_computed_from_the_sent_date(self, tracker_worksheet):
        tracker.log_request(
            tracker_worksheet, "Jane", "TX", "u", "e",
            consent_date=date(2026, 8, 15),
            deadline_days=45,
            sent_date=date(2026, 8, 19),
        )

        row, _ = tracker_worksheet.appended[0]
        assert dict(zip(tracker.HEADER, row))["Deadline"] == "2026-10-03"

    def test_unknown_deadline_is_flagged_not_guessed(self, tracker_worksheet):
        tracker.log_request(
            tracker_worksheet, "Jane", "CA", "u", "e",
            consent_date=date(2026, 8, 15),
            deadline_days=None,
        )

        row, _ = tracker_worksheet.appended[0]
        assert dict(zip(tracker.HEADER, row))["Deadline"] == "N/A (verify statute)"

    def test_sent_date_defaults_to_today(self, tracker_worksheet):
        tracker.log_request(
            tracker_worksheet, "Jane", "FL", "u", "e",
            consent_date=date(2026, 8, 15),
            deadline_days=10,
        )

        row, _ = tracker_worksheet.appended[0]
        fields = dict(zip(tracker.HEADER, row))
        assert fields["Request Sent Date"] == TODAY.isoformat()
        assert fields["Deadline"] == (TODAY + timedelta(days=10)).isoformat()

    def test_status_and_notes_are_overridable(self, tracker_worksheet):
        tracker.log_request(
            tracker_worksheet, "Jane", "FL", "u", "e",
            consent_date=date(2026, 8, 15),
            deadline_days=10,
            status="Removed",
            notes="Confirmed by email",
        )

        row, _ = tracker_worksheet.appended[0]
        fields = dict(zip(tracker.HEADER, row))
        assert fields["Status"] == "Removed"
        assert fields["Notes"] == "Confirmed by email"

    def test_consent_date_is_recorded(self, tracker_worksheet):
        # The consent date is the audit trail for "the client authorized
        # this" -- it has to land in the row.
        tracker.log_request(
            tracker_worksheet, "Jane", "FL", "u", "e",
            consent_date=date(2026, 7, 1),
            deadline_days=10,
        )

        row, _ = tracker_worksheet.appended[0]
        assert dict(zip(tracker.HEADER, row))["Consent Date"] == "2026-07-01"


class TestListOverdue:
    def test_returns_rows_past_their_deadline(self):
        overdue_row = tracker_row(Deadline=(TODAY - timedelta(days=1)).isoformat())
        worksheet = FakeWorksheet(records=[overdue_row])

        assert tracker.list_overdue(worksheet) == [overdue_row]

    def test_ignores_rows_still_within_their_deadline(self):
        worksheet = FakeWorksheet(records=[tracker_row()])

        assert tracker.list_overdue(worksheet) == []

    def test_deadline_today_is_not_yet_overdue(self):
        worksheet = FakeWorksheet(records=[tracker_row(Deadline=TODAY.isoformat())])

        assert tracker.list_overdue(worksheet) == []

    @pytest.mark.parametrize("status", ["Removed", "Escalated", "", "pending"])
    def test_ignores_rows_that_are_no_longer_pending(self, status):
        worksheet = FakeWorksheet(
            records=[
                tracker_row(
                    Status=status,
                    Deadline=(TODAY - timedelta(days=30)).isoformat(),
                )
            ]
        )

        assert tracker.list_overdue(worksheet) == []

    @pytest.mark.parametrize(
        "deadline", ["N/A (verify statute)", "", "soon", "08/29/2026"]
    )
    def test_skips_rows_without_a_real_deadline(self, deadline):
        # Unconfirmed-statute states get a non-date deadline; they must not be
        # guessed into or out of the overdue list.
        worksheet = FakeWorksheet(records=[tracker_row(Deadline=deadline)])

        assert tracker.list_overdue(worksheet) == []

    def test_skips_rows_missing_the_deadline_column(self):
        row = tracker_row()
        del row["Deadline"]
        worksheet = FakeWorksheet(records=[row])

        assert tracker.list_overdue(worksheet) == []

    def test_returns_only_the_overdue_rows_from_a_mixed_sheet(self):
        past = (TODAY - timedelta(days=3)).isoformat()
        future = (TODAY + timedelta(days=3)).isoformat()
        worksheet = FakeWorksheet(
            records=[
                tracker_row(Deadline=future),
                tracker_row(**{"Client Name": "Overdue Client", "Deadline": past}),
                tracker_row(Deadline=past, Status="Removed"),
                tracker_row(Deadline="N/A (verify statute)"),
            ]
        )

        overdue = tracker.list_overdue(worksheet)

        assert [row["Client Name"] for row in overdue] == ["Overdue Client"]


class TestRecordOwnerInfo:
    LOOKUP = {
        "domain_info": {
            "registrant_org": "Example Holdings LLC",
            "registrant_name": "Jane Registrant",
            "registrant_email": "admin@example-site.test",
            "registrar": "Example Registrar Inc",
        },
        "hosting_info": {
            "hosting_org": "Example Hosting",
            "abuse_email": "abuse@example-hosting.test",
        },
    }

    def test_writes_lookup_columns_for_the_matching_row(self):
        worksheet = FakeWorksheet()
        worksheet.set_find_results("https://example-site.test/jane", [FakeCell(row=7)])

        assert (
            tracker.record_owner_info(
                worksheet, "https://example-site.test/jane", self.LOOKUP
            )
            is True
        )
        assert worksheet.updates == [
            (
                "J7:O7",
                [
                    [
                        "Example Holdings LLC",
                        "Jane Registrant",
                        "admin@example-site.test",
                        "Example Registrar Inc",
                        "Example Hosting",
                        "abuse@example-hosting.test",
                    ]
                ],
            )
        ]

    def test_uses_the_most_recent_matching_row(self):
        worksheet = FakeWorksheet()
        worksheet.set_find_results(
            "https://example-site.test/jane",
            [FakeCell(row=3), FakeCell(row=7), FakeCell(row=12)],
        )

        tracker.record_owner_info(
            worksheet, "https://example-site.test/jane", self.LOOKUP
        )

        assert worksheet.updates[0][0] == "J12:O12"

    def test_reports_failure_when_the_url_is_not_in_the_sheet(self):
        worksheet = FakeWorksheet()

        assert (
            tracker.record_owner_info(worksheet, "https://missing.test/x", self.LOOKUP)
            is False
        )
        assert worksheet.updates == []

    def test_missing_lookup_fields_become_blank(self):
        worksheet = FakeWorksheet()
        worksheet.set_find_results("https://example-site.test/jane", [FakeCell(row=4)])

        tracker.record_owner_info(
            worksheet,
            "https://example-site.test/jane",
            {"domain_info": {"error": "no whois"}, "hosting_info": {}},
        )

        assert worksheet.updates == [("J4:O4", [["", "", "", "", "", ""]])]

    def test_handles_a_lookup_with_no_sections_at_all(self):
        worksheet = FakeWorksheet()
        worksheet.set_find_results("https://example-site.test/jane", [FakeCell(row=4)])

        tracker.record_owner_info(worksheet, "https://example-site.test/jane", {})

        assert worksheet.updates == [("J4:O4", [["", "", "", "", "", ""]])]

    def test_null_lookup_values_become_blank(self):
        # WHOIS routinely returns None for privacy-shielded fields.
        worksheet = FakeWorksheet()
        worksheet.set_find_results("https://example-site.test/jane", [FakeCell(row=4)])

        tracker.record_owner_info(
            worksheet,
            "https://example-site.test/jane",
            {
                "domain_info": {"registrant_org": None, "registrar": "R"},
                "hosting_info": {"hosting_org": None},
            },
        )

        assert worksheet.updates == [("J4:O4", [["", "", "", "R", "", ""]])]
