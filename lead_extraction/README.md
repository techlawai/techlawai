# eCaseView Case Extraction → Google Sheets

Per-case tool: you look up a case on eCaseView yourself, enter what you found,
and it appends one row to a Google Sheet. It does not fetch eCaseView itself —
there's no automated crawling here, by design (see "Scope" below).

## Setup

1. `pip install -r requirements.txt`
2. Create a Google Cloud service account with the Sheets API enabled, download
   its JSON key, save it as `service_account.json` in this folder (or point
   `--creds` at another path).
3. Share your target Google Sheet with the service account's email address
   (found in the JSON key as `client_email`), with Editor access.
4. Copy the Sheet ID from its URL (`https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit`).

## Usage

Interactive, one case at a time:

    python extract.py --sheet-id <SHEET_ID> --interactive

Batch, from a JSON file (list of case objects, same fields as below):

    python extract.py --sheet-id <SHEET_ID> --json-file cases.json

Single case via flags:

    python extract.py --sheet-id <SHEET_ID> \
      --first-name "Jane" \
      --last-name "Public" \
      --charge "DUI - Unlawful Blood Alcohol Level" \
      --phone-number "" \
      --address "" \
      --arrest-date "2026-08-19"

## Fields

First Name, Last Name, Charge, Phone Number, Address, Arrest Date. Leave any
field blank if it isn't present on the case/document you're looking at.

## Tests

    pip install -r requirements-dev.txt
    python -m pytest

The tests stub out Google's client libraries, so they need no service account
key, no network, and no target sheet.

## Scope

This tool only writes what you give it — it does not visit eCaseView, so it
carries none of the site's Terms of Use restrictions on automated/bulk access
itself. You are still bound by those terms in how you use the site to gather
the input.
