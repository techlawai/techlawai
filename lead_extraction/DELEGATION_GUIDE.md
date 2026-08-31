# Lead Extraction Setup & Operating Guide

## Goal

Pull case data from the Palm Beach County Clerk of Courts public case search
(eCaseView) for cases involving an arrest, and record each case's Full Name,
Charge, Phone Number, Address, and Arrest Date into a Google Sheet, one row
per case, using the `extract.py` script in this folder.

Case scope: Court Type = **Felony** or **Misdemeanor** (not Criminal Traffic —
that includes citation-only tickets with no arrest). Only pull cases where the
**Arrest Date** field is actually populated. Charges of interest: DUI and
domestic battery.

---

## Legal Basis for Sourcing This Data

Under Florida's public records law (Ch. 119), booking records and arrest
affidavits/probable cause affidavits are public once created, unless a
specific statutory exemption applies (undercover officer info, certain active
investigation info, victim info in sexual offense cases, juvenile records).
There's no blanket legal bar on a phone number being visible in one of these
documents if it's actually in there — Florida court rule 2.420, which governs
what must be redacted from filed court records, requires redacting things
like SSNs and financial account numbers, but a phone number isn't on that
mandatory-redaction list. If an officer put a phone number in the narrative
or header of an arrest affidavit, it generally stays visible when that
document is scanned and filed.

This does not mean every arrest affidavit has a phone number in it — that
varies by agency template and by officer, and has to be checked document by
document (see Part 3, step 5). It means that when one is present, nothing in
Florida's public-records or court-confidentiality rules requires it to be
hidden.

Separately, eCaseView's own Terms of Use (see Notes at the end of this guide)
govern how the site itself may be used to gather this data — that's a site
usage restriction, not a public-records restriction on the underlying
document.

---

## Part 1 — Google Service Account Setup

This is a one-time setup. It creates the credentials the script uses to write
to Google Sheets.

1. Go to https://console.cloud.google.com and sign in with the Google account
   that will own this integration.
2. Create a new project (top left project dropdown → "New Project"). Name it
   something like `pbc-lead-extraction`.
3. With that project selected, go to **APIs & Services → Library**, search
   for **Google Sheets API**, and click **Enable**.
4. Go to **APIs & Services → Credentials → Create Credentials → Service
   Account**.
5. Give it a name (e.g. `sheets-writer`), click through the remaining steps
   with defaults, and click **Done**.
6. Click into the new service account → **Keys** tab → **Add Key → Create
   New Key → JSON**. This downloads a `.json` file — save it as
   `service_account.json` inside this `lead_extraction/` folder.
7. Open that JSON file in a text editor and copy the value of `client_email`
   (looks like `sheets-writer@pbc-lead-extraction.iam.gserviceaccount.com`).
8. Create (or open) the target Google Sheet. Click **Share**, paste in that
   `client_email` address, set permission to **Editor**, and send/share.
9. Copy the **Sheet ID** out of the sheet's URL:
   `https://docs.google.com/spreadsheets/d/`**`THIS_PART_IS_THE_SHEET_ID`**`/edit`

Keep `service_account.json` private — it's a credential, not something to
paste into chat, email, or commit to a public repo.

---

## Part 2 — Install the Script

1. Make sure Python 3 is installed.
2. From inside `lead_extraction/`, run:
   ```
   pip install -r requirements.txt
   ```
3. Confirm `service_account.json` is sitting in this same folder (or note its
   path to pass via `--creds`).

---

## Part 3 — Pulling Case Data from eCaseView

1. Go to `https://appsgp.mypalmbeachclerk.com/eCaseView`.
2. Click **Continue as a Guest**.
3. Under **Search Criteria**, set:
   - **Court Type**: Felony (run the whole process once for Felony, once more
     for Misdemeanor)
   - **Date range**: whatever window you're pulling (e.g. one month)
4. Run the search, go to **Search Results**, and uncheck **"one row per
   case"** if it's checked, so all docket entries show.
5. For each case in the results where you're targeting DUI or domestic
   battery charges:
   - Click the case number hyperlink to open it.
   - On the **Case Info** tab, check the **Arrest Date** field — if it's
     blank, skip this case (it's a citation, not an arrest).
   - Note First Name / Last Name from this tab.
   - Click the **Charges & Sentences** tab — note the charge description.
   - Click the **Arrests & Bonds** tab — note any address or additional
     detail shown there.
   - Click **Dockets & Documents** — open the arrest/incident report
     document (not the citation) if one is listed, and check it for a phone
     number and/or address.
6. Write down, per case: **First Name, Last Name, Charge, Phone Number,
   Address, Arrest Date**. Leave any field blank if it isn't present on that
   case — don't guess or fill it in from elsewhere.

---

## Part 4 — Loading Data into the Sheet

Three ways to run `extract.py`, from inside `lead_extraction/`:

**One case at a time, interactively** (it prompts you for each field):
```
python extract.py --sheet-id YOUR_SHEET_ID --interactive
```

**A batch of cases at once**, from a JSON file you prepare:
```json
[
  {
    "first_name": "Jane",
    "last_name": "Public",
    "charge": "DUI - Unlawful Blood Alcohol Level",
    "phone_number": "",
    "address": "",
    "arrest_date": "2026-08-19"
  },
  {
    "first_name": "John",
    "last_name": "Doe",
    "charge": "Battery - Domestic Violence",
    "phone_number": "",
    "address": "",
    "arrest_date": "2026-08-20"
  }
]
```
```
python extract.py --sheet-id YOUR_SHEET_ID --json-file cases.json
```

**A single case via command-line flags:**
```
python extract.py --sheet-id YOUR_SHEET_ID \
  --first-name "Jane" \
  --last-name "Public" \
  --charge "DUI - Unlawful Blood Alcohol Level" \
  --phone-number "" \
  --address "" \
  --arrest-date "2026-08-19"
```

If your `service_account.json` isn't in the same folder as the script, add
`--creds /path/to/service_account.json` to any of the commands above.

Each run appends new rows to a tab named **"Leads"** in your sheet (created
automatically the first time, with a header row).

---

## Notes

- This tool does not scrape eCaseView automatically — it only writes data
  that's manually collected and entered by whoever is running it. Someone has
  to look up each case and read the fields off the screen/document.
- eCaseView's own Terms of Use restrict the site to non-commercial personal
  use and require the Clerk's written permission for automated/bulk
  reproduction of its content — that applies to how the site itself is used
  to gather this data, separate from what this script does with it once
  collected.
