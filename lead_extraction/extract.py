#!/usr/bin/env python3
"""Append case leads (name/address/charge/case number/dates) to a Google Sheet.

This script does not fetch anything from eCaseView or any other website. You
look up a case yourself and feed its fields in here, either interactively,
via CLI flags for a single case, or via a JSON file for a batch of cases
you've already collected.
"""
import argparse
import json
import sys

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

HEADER = [
    "Full Name",
    "Address",
    "Charge",
    "Statute",
    "Case Number",
    "Arrest Date",
    "Offense Date",
    "Filing Date",
    "Case Status",
]

FIELD_KEYS = [
    "full_name",
    "address",
    "charge",
    "statute",
    "case_number",
    "arrest_date",
    "offense_date",
    "filing_date",
    "case_status",
]


def open_sheet(sheet_id: str, creds_path: str, worksheet_name: str):
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


def case_to_row(case: dict) -> list:
    return [case.get(key, "") for key in FIELD_KEYS]


def prompt_for_case() -> dict:
    print("Enter case details (leave blank and press Enter to skip a field):")
    case = {}
    prompts = [
        ("full_name", "Full Name"),
        ("address", "Address"),
        ("charge", "Charge"),
        ("statute", "Statute"),
        ("case_number", "Case Number"),
        ("arrest_date", "Arrest Date"),
        ("offense_date", "Offense Date"),
        ("filing_date", "Filing Date"),
        ("case_status", "Case Status"),
    ]
    for key, label in prompts:
        case[key] = input(f"  {label}: ").strip()
    return case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet-id", required=True, help="Google Sheet ID")
    parser.add_argument("--worksheet", default="Leads", help="Worksheet/tab name (default: Leads)")
    parser.add_argument("--creds", default="service_account.json", help="Path to service account JSON key")
    parser.add_argument("--interactive", action="store_true", help="Prompt for one case at a time")
    parser.add_argument("--json-file", help="Path to a JSON file containing a list of case objects")
    parser.add_argument("--full-name")
    parser.add_argument("--address", default="")
    parser.add_argument("--charge")
    parser.add_argument("--statute", default="")
    parser.add_argument("--case-number")
    parser.add_argument("--arrest-date", default="")
    parser.add_argument("--offense-date", default="")
    parser.add_argument("--filing-date", default="")
    parser.add_argument("--case-status", default="")
    args = parser.parse_args()

    ws = open_sheet(args.sheet_id, args.creds, args.worksheet)

    rows_to_add = []

    if args.interactive:
        while True:
            case = prompt_for_case()
            if any(case.values()):
                rows_to_add.append(case_to_row(case))
            again = input("Add another case? [y/N]: ").strip().lower()
            if again != "y":
                break
    elif args.json_file:
        with open(args.json_file) as f:
            cases = json.load(f)
        for case in cases:
            rows_to_add.append(case_to_row(case))
    elif args.full_name and args.charge and args.case_number:
        case = {
            "full_name": args.full_name,
            "address": args.address,
            "charge": args.charge,
            "statute": args.statute,
            "case_number": args.case_number,
            "arrest_date": args.arrest_date,
            "offense_date": args.offense_date,
            "filing_date": args.filing_date,
            "case_status": args.case_status,
        }
        rows_to_add.append(case_to_row(case))
    else:
        parser.error("Provide --interactive, --json-file, or at minimum --full-name/--charge/--case-number")

    if not rows_to_add:
        print("Nothing to add.")
        sys.exit(0)

    ws.append_rows(rows_to_add, value_input_option="USER_ENTERED")
    print(f"Added {len(rows_to_add)} row(s) to worksheet '{args.worksheet}'.")


if __name__ == "__main__":
    main()
