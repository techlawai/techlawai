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
      --full-name "Jane Q Public" \
      --address "" \
      --charge "DUI - Unlawful Blood Alcohol Level" \
      --statute "316.193(1)" \
      --case-number "2026CF012345" \
      --arrest-date "2026-08-19" \
      --offense-date "2026-08-19" \
      --filing-date "2026-08-31" \
      --case-status "Open"

## Fields

Full Name, Address, Charge, Statute, Case Number, Arrest Date, Offense Date,
Filing Date, Case Status. Leave Address blank if it isn't present on the case
you're looking at — it often isn't at the Case Info / Party Names level.

## Scope

- No field for phone number. It isn't collected by this tool.
- This tool only writes what you give it — it does not visit eCaseView, so it
  carries none of the site's Terms of Use restrictions on automated/bulk
  access itself. You are still bound by those terms in how you use the site
  to gather the input.
