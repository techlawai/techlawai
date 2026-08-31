# BUILD_SPEC: eCaseView Lead Extraction Tool

```yaml
target: python3
package: lead_extraction
entry_point: extract.py
purpose: append_structured_case_records_to_google_sheet
```

## 1. DATA_SCHEMA

```json
{
  "type": "object",
  "properties": {
    "first_name":   { "type": "string" },
    "last_name":    { "type": "string" },
    "charge":       { "type": "string" },
    "phone_number": { "type": "string" },
    "address":      { "type": "string" },
    "arrest_date":  { "type": "string", "format": "date" }
  },
  "required": ["first_name", "last_name", "charge"]
}
```

Sheet header row, in column order:
```
["First Name", "Last Name", "Charge", "Phone Number", "Address", "Arrest Date"]
```

## 2. INPUT_MODES

```
MODE_1: interactive
  trigger: --interactive
  behavior: loop { prompt each field in DATA_SCHEMA order -> buffer row -> ask "add another? y/N" }

MODE_2: batch
  trigger: --json-file <path>
  behavior: load JSON array of objects matching DATA_SCHEMA -> map each to row

MODE_3: single
  trigger: --first-name --last-name --charge [--phone-number --address --arrest-date]
  behavior: construct one row from flags
```

## 3. OUTPUT_TARGET

```
sink: google_sheets
auth: service_account (google.oauth2.service_account.Credentials)
scope: https://www.googleapis.com/auth/spreadsheets
lib: gspread>=6.0.0
write_op: worksheet.append_rows(rows, value_input_option="USER_ENTERED")
worksheet_name: "Leads"
on_missing_worksheet: create(rows=1000, cols=len(header))
on_missing_header: write_header_row_at_A1
```

CLI contract:
```
--sheet-id      required, str
--worksheet     optional, str, default="Leads"
--creds         optional, str, default="service_account.json"
```

## 4. UPSTREAM_DATA_SOURCE (informational — not a fetch target)

```
source_system: "Palm Beach County Clerk of Courts — eCaseView"
source_url: "https://appsgp.mypalmbeachclerk.com/eCaseView"
access_method: HUMAN_MANUAL_ENTRY_ONLY
```

```
CONSTRAINT[NETWORK]: This codebase MUST NOT issue HTTP(S) requests, headless-
browser sessions, or any programmatic fetch against mypalmbeachclerk.com or
any subdomain of it. No requests/httpx/playwright/selenium/scrapy dependency
targeting that host is permitted in this package.

REASON: site Terms of Use restrict the site to non-commercial personal use
and require the site operator's prior written permission for automated
reproduction/redistribution of site content. No such permission exists as of
this spec's authoring. Programmatic access is disallowed until that changes.

IMPLICATION: DATA_SCHEMA field values are supplied exclusively by a human
operator who has independently viewed eCaseView in a browser and is typing
observed values into MODE_1/MODE_2/MODE_3 inputs. This package has zero
coupling to eCaseView's DOM, API, or network layer.
```

## 5. UPSTREAM_FIELD_SOURCE_MAP (for the human operator, not the code)

```
first_name    <- eCaseView Case Info tab
last_name     <- eCaseView Case Info tab
charge        <- eCaseView Charges & Sentences tab
address       <- eCaseView Arrests & Bonds tab, or arrest/PC affidavit document
phone_number  <- arrest/PC affidavit document only (not present in Case Info schema)
arrest_date   <- eCaseView Case Info tab; NULL/blank => EXCLUDE record (citation, not arrest)
```

```
FILTER: court_type IN {"Felony", "Misdemeanor"}
FILTER: arrest_date IS NOT NULL
FILTER: charge MATCHES {"DUI", "domestic battery"} (case-insensitive substring or statute-code match)
```

## 6. LEGAL_BASIS (for inclusion in operator-facing docs, informational)

```
jurisdiction: Florida
statute: Fla. Stat. Ch. 119 (public records)
rule: Fla. R. Jud. Admin. 2.420 (confidential info in court records)
finding: phone_number is not in Rule 2.420's mandatory-redaction category set
         (unlike SSN, financial account number). If present in a filed
         affidavit, no redaction requirement applies.
caveat: presence of phone_number in any given affidavit is NOT guaranteed;
        verify per-document.
site_terms: separate from public-records status; governs ACCESS METHOD only
            (see section 4 CONSTRAINT[NETWORK]).
```

## 7. SECRETS

```
service_account.json:
  type: credential
  handling: filesystem only, gitignored, never logged, never printed, never
            transmitted outside google-auth's TLS session to googleapis.com
```

## 8. NON_GOALS

```
- No scheduling/cron/unattended execution.
- No eCaseView network client of any kind.
- No PII validation, deduplication, or enrichment beyond what's listed above.
```
