"""Tests for extract.py.

No network or credentials are involved — see conftest.py for the gspread and
google-auth stubs these tests run against.
"""
import json

import pytest

import extract
from lead_fakes import Credentials, FakeWorksheet


def write_cases(tmp_path, cases):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(cases))
    return str(path)


COMPLETE_CASE = {
    "first_name": "Jane",
    "last_name": "Public",
    "charge": "DUI - Unlawful Blood Alcohol Level",
    "phone_number": "561-555-0100",
    "address": "1 Main St",
    "arrest_date": "2026-08-19",
}


class TestSchemaInvariants:
    def test_header_and_field_keys_line_up(self):
        assert len(extract.HEADER) == len(extract.FIELD_KEYS)

    def test_required_fields_are_real_fields(self):
        assert set(extract.REQUIRED_FIELDS) <= set(extract.FIELD_KEYS)

    def test_required_fields_match_build_spec(self):
        assert extract.REQUIRED_FIELDS == ["first_name", "last_name", "charge"]


class TestMissingRequired:
    def test_complete_case_is_satisfied(self):
        assert extract.missing_required(COMPLETE_CASE) == []

    def test_optional_fields_are_not_required(self):
        case = {"first_name": "Jane", "last_name": "Public", "charge": "DUI"}
        assert extract.missing_required(case) == []

    @pytest.mark.parametrize("field", ["first_name", "last_name", "charge"])
    def test_absent_required_field_is_reported(self, field):
        case = {key: value for key, value in COMPLETE_CASE.items() if key != field}
        assert extract.missing_required(case) == [field]

    @pytest.mark.parametrize("field", ["first_name", "last_name", "charge"])
    def test_empty_required_field_is_reported(self, field):
        case = dict(COMPLETE_CASE, **{field: ""})
        assert extract.missing_required(case) == [field]

    @pytest.mark.parametrize("blank", [" ", "   ", "\t", "\n"])
    def test_whitespace_only_counts_as_missing(self, blank):
        case = dict(COMPLETE_CASE, last_name=blank)
        assert extract.missing_required(case) == ["last_name"]

    def test_all_missing_reported_in_field_order(self):
        assert extract.missing_required({}) == ["first_name", "last_name", "charge"]

    def test_non_string_value_is_accepted(self):
        # A JSON batch can carry a number where a string was expected; it is
        # present, so it is not "missing".
        case = dict(COMPLETE_CASE, charge=316193)
        assert extract.missing_required(case) == []

    def test_none_value_counts_as_missing(self):
        case = dict(COMPLETE_CASE, charge=None)
        assert extract.missing_required(case) == ["charge"]


class TestCaseToRow:
    def test_row_follows_field_key_order(self):
        assert extract.case_to_row(COMPLETE_CASE) == [
            "Jane",
            "Public",
            "DUI - Unlawful Blood Alcohol Level",
            "561-555-0100",
            "1 Main St",
            "2026-08-19",
        ]

    def test_absent_optional_fields_become_blank(self):
        case = {"first_name": "Jane", "last_name": "Public", "charge": "DUI"}
        assert extract.case_to_row(case) == ["Jane", "Public", "DUI", "", "", ""]

    def test_unknown_keys_are_ignored(self):
        case = dict(COMPLETE_CASE, case_number="50-2026-CF-001234")
        assert len(extract.case_to_row(case)) == len(extract.HEADER)

    def test_null_optional_field_becomes_blank(self):
        # A JSON batch may carry an explicit null rather than omitting a field;
        # it should land as an empty cell, not the string "None".
        case = dict(COMPLETE_CASE, phone_number=None, address=None)
        row = extract.case_to_row(case)
        assert row[3] == ""
        assert row[4] == ""


class TestOpenSheet:
    def test_uses_existing_worksheet_and_leaves_good_header_alone(
        self, fake_sheets, leads_worksheet
    ):
        _, client = fake_sheets({"Leads": leads_worksheet})

        worksheet = extract.open_sheet("SHEET123", "creds.json", "Leads")

        assert worksheet is leads_worksheet
        assert client.opened == ["SHEET123"]
        assert leads_worksheet.updates == []

    def test_writes_header_when_missing(self, fake_sheets):
        blank = FakeWorksheet(row1=[])
        fake_sheets({"Leads": blank})

        extract.open_sheet("SHEET123", "creds.json", "Leads")

        assert blank.updates == [("A1", [extract.HEADER])]

    def test_rewrites_header_when_it_does_not_match(self, fake_sheets):
        wrong = FakeWorksheet(row1=["Name", "Charge"])
        fake_sheets({"Leads": wrong})

        extract.open_sheet("SHEET123", "creds.json", "Leads")

        assert wrong.updates == [("A1", [extract.HEADER])]

    def test_creates_worksheet_when_absent(self, fake_sheets):
        spreadsheet, _ = fake_sheets({})

        worksheet = extract.open_sheet("SHEET123", "creds.json", "Leads")

        assert spreadsheet.added == [
            {"title": "Leads", "rows": 1000, "cols": len(extract.HEADER)}
        ]
        assert worksheet.updates == [("A1", [extract.HEADER])]

    def test_honors_custom_worksheet_name(self, fake_sheets):
        spreadsheet, _ = fake_sheets({})

        extract.open_sheet("SHEET123", "creds.json", "August")

        assert spreadsheet.added[0]["title"] == "August"

    def test_loads_credentials_from_given_path(self, fake_sheets, leads_worksheet):
        fake_sheets({"Leads": leads_worksheet})

        extract.open_sheet("SHEET123", "/keys/service_account.json", "Leads")

        assert Credentials.calls == [
            {"path": "/keys/service_account.json", "scopes": extract.SCOPES}
        ]


class TestBatchMode:
    def test_valid_batch_is_appended(
        self, tmp_path, fake_sheets, leads_worksheet, run_main
    ):
        _, client = fake_sheets({"Leads": leads_worksheet})
        path = write_cases(
            tmp_path,
            [
                COMPLETE_CASE,
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "charge": "Battery - Domestic Violence",
                    "arrest_date": "2026-08-20",
                },
            ],
        )

        run_main(["--sheet-id", "SHEET123", "--json-file", path])

        assert leads_worksheet.appended == [
            (
                [
                    extract.case_to_row(COMPLETE_CASE),
                    ["John", "Doe", "Battery - Domestic Violence", "", "", "2026-08-20"],
                ],
                "USER_ENTERED",
            )
        ]
        assert client.opened == ["SHEET123"]

    def test_batch_with_invalid_case_aborts(self, tmp_path, run_main, capsys):
        # fake_sheets is deliberately not installed: reaching the sheet at all
        # would trip the guard in conftest.
        path = write_cases(
            tmp_path,
            [COMPLETE_CASE, {"first_name": "John", "charge": "Battery"}],
        )

        with pytest.raises(SystemExit) as exit_info:
            run_main(["--sheet-id", "SHEET123", "--json-file", path])

        assert exit_info.value.code == 1
        stderr = capsys.readouterr().err
        assert "case #1" in stderr
        assert "last_name" in stderr

    def test_every_invalid_case_is_reported(self, tmp_path, run_main, capsys):
        path = write_cases(
            tmp_path,
            [
                {"first_name": "Jane"},
                COMPLETE_CASE,
                {"last_name": "Doe", "charge": "DUI"},
            ],
        )

        with pytest.raises(SystemExit):
            run_main(["--sheet-id", "SHEET123", "--json-file", path])

        stderr = capsys.readouterr().err
        assert "case #0" in stderr
        assert "case #2" in stderr
        assert "case #1" not in stderr

    def test_empty_batch_writes_nothing(self, tmp_path, run_main, capsys):
        path = write_cases(tmp_path, [])

        with pytest.raises(SystemExit) as exit_info:
            run_main(["--sheet-id", "SHEET123", "--json-file", path])

        assert exit_info.value.code == 0
        assert "Nothing to add." in capsys.readouterr().out


class TestSingleCaseMode:
    def test_flags_produce_one_row(self, fake_sheets, leads_worksheet, run_main):
        fake_sheets({"Leads": leads_worksheet})

        run_main(
            [
                "--sheet-id",
                "SHEET123",
                "--first-name",
                "Jane",
                "--last-name",
                "Public",
                "--charge",
                "DUI",
                "--arrest-date",
                "2026-08-19",
            ]
        )

        assert leads_worksheet.appended == [
            ([["Jane", "Public", "DUI", "", "", "2026-08-19"]], "USER_ENTERED")
        ]

    def test_incomplete_flags_are_rejected(self, run_main):
        with pytest.raises(SystemExit) as exit_info:
            run_main(["--sheet-id", "SHEET123", "--first-name", "Jane"])

        assert exit_info.value.code == 2

    def test_no_mode_selected_is_rejected(self, run_main):
        with pytest.raises(SystemExit) as exit_info:
            run_main(["--sheet-id", "SHEET123"])

        assert exit_info.value.code == 2


class TestInteractiveMode:
    def test_complete_case_is_appended(
        self, fake_sheets, leads_worksheet, feed_input, run_main
    ):
        fake_sheets({"Leads": leads_worksheet})
        feed_input(
            ["Jane", "Public", "DUI", "561-555-0100", "1 Main St", "2026-08-19", "n"]
        )

        run_main(["--sheet-id", "SHEET123", "--interactive"])

        assert leads_worksheet.appended == [
            (
                [["Jane", "Public", "DUI", "561-555-0100", "1 Main St", "2026-08-19"]],
                "USER_ENTERED",
            )
        ]

    def test_incomplete_case_is_rejected(self, feed_input, run_main, capsys):
        feed_input(["Jane", "", "DUI", "", "", "", "n"])

        with pytest.raises(SystemExit) as exit_info:
            run_main(["--sheet-id", "SHEET123", "--interactive"])

        assert exit_info.value.code == 0
        out = capsys.readouterr().out
        assert "Missing required field(s)" in out
        assert "last_name" in out
        assert "Nothing to add." in out

    def test_blank_entry_is_skipped_quietly(self, feed_input, run_main, capsys):
        feed_input(["", "", "", "", "", "", "n"])

        with pytest.raises(SystemExit) as exit_info:
            run_main(["--sheet-id", "SHEET123", "--interactive"])

        assert exit_info.value.code == 0
        out = capsys.readouterr().out
        assert "Missing required field(s)" not in out
        assert "Nothing to add." in out

    def test_loop_collects_multiple_cases(
        self, fake_sheets, leads_worksheet, feed_input, run_main
    ):
        fake_sheets({"Leads": leads_worksheet})
        feed_input(
            [
                "Jane", "Public", "DUI", "", "", "2026-08-19", "y",
                "John", "Doe", "Battery", "", "", "2026-08-20", "n",
            ]
        )

        run_main(["--sheet-id", "SHEET123", "--interactive"])

        rows, _ = leads_worksheet.appended[0]
        assert rows == [
            ["Jane", "Public", "DUI", "", "", "2026-08-19"],
            ["John", "Doe", "Battery", "", "", "2026-08-20"],
        ]

    def test_rejected_case_does_not_block_later_ones(
        self, fake_sheets, leads_worksheet, feed_input, run_main
    ):
        fake_sheets({"Leads": leads_worksheet})
        feed_input(
            [
                "Jane", "", "DUI", "", "", "2026-08-19", "y",
                "John", "Doe", "Battery", "", "", "2026-08-20", "n",
            ]
        )

        run_main(["--sheet-id", "SHEET123", "--interactive"])

        rows, _ = leads_worksheet.appended[0]
        assert rows == [["John", "Doe", "Battery", "", "", "2026-08-20"]]
