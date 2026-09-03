# Mugshot Removal Tool (multi-state)

Search, draft, send, and track booking-photo removal requests across states
with a fee-prohibition/removal statute. Each request is generated and sent
as the client's own first-person statutory request (the client is the
"From" address and the signer) — not as a third party representing them.

## Supported states

See `statutes.py`. Each entry is either `"verified"` (citation, deadline,
and penalty all confirmed) or `"partial"` (citation and fee-prohibition
confirmed; deadline/penalty not confirmed and left blank rather than
guessed). Every `"partial"` state's letter says so explicitly and asks the
operator to verify current statutory text before sending. Note that a
`"partial"` entry may be wrong about what its statute does at all, not just
missing numbers — see the TX note in `statutes.py`. Currently: FL (verified),
CA, TX, GA, UT, OR, CO, IL, WY (partial). Run `python main.py list-states`
for the full data. Adding a new state means adding a real, sourced entry to
`statutes.py` — not extrapolating from another state's numbers.

## Setup

```
pip install -r requirements.txt
```

**Search** (Google Custom Search API):
1. https://programmablesearchengine.google.com/ → create a search engine
   scoped to the entire web → copy its Search Engine ID (`cx`).
2. https://console.cloud.google.com → enable "Custom Search API" → create an
   API key.

**Send** (SMTP): use the client's own email account (or an account they've
authorized you to send from as them), with an app password if the provider
requires one (e.g. Gmail).

**Track** (optional, Google Sheets): same service-account setup as
`lead_extraction/` — see that folder's README for the steps. Share the
tracking sheet with the service account's `client_email`.

## Usage

Find candidate pages:
```
python main.py search --client-name "Jane Public" --api-key KEY --cx CX_ID
```

Preview a letter without sending (defaults to `--state FL`):
```
python main.py draft --client-name "Jane Public" --client-contact "jane@example.com" \
  --target-url "https://example-mugshot-site.com/jane-public" \
  --state FL \
  --booking-date "2026-08-19" --arresting-agency "Palm Beach County Sheriff's Office"
```

**Before sending anything real**, get the client's written authorization to
send from their name/email. Generate the form:
```
python main.py consent-form --client-name "Jane Public" \
  --client-email "jane@example.com" \
  --target-url "https://example-mugshot-site.com/jane-public" \
  --state FL
```
Have the client sign and return it, and keep it on file. `send` will not
run without `--consent-date` set to the date they actually signed it — a
future or garbage date is rejected outright, not just logged.

Send it and log to a tracker sheet:
```
python main.py send --client-name "Jane Public" --client-email "jane@example.com" \
  --target-url "https://example-mugshot-site.com/jane-public" \
  --to-email "abuse@example-mugshot-site.com" \
  --state FL \
  --consent-date "2026-08-25" \
  --booking-date "2026-08-19" --arresting-agency "Palm Beach County Sheriff's Office" \
  --smtp-host smtp.gmail.com --smtp-port 465 \
  --smtp-username jane@example.com --smtp-password APP_PASSWORD \
  --sheet-id YOUR_SHEET_ID
```

Check which requests are past their 10-day deadline with no removal —
this also looks up each overdue site's domain registrant and hosting
provider (WHOIS + IP RDAP) and writes that into the tracker sheet:
```
python main.py check-overdue --sheet-id YOUR_SHEET_ID
```
That's the point at which Fla. Stat. § 901.43 lets the client seek an
injunction, a $1,000/day penalty, and attorney fees — that step itself
still needs an actual attorney to file. This tool's job stops at handing
that attorney the request's overdue status plus who to name/contact
(registrant and hosting org, where WHOIS/RDAP data isn't privacy-shielded).

Look up registrant/hosting info for a single URL directly:
```
python main.py lookup-owner --target-url "https://example-mugshot-site.com/jane-public"
```

## Tests

```
pip install -r requirements-dev.txt
python -m pytest
```

The tests stub out every outbound integration (Sheets, Custom Search, WHOIS,
RDAP, DNS, SMTP), so they need no credentials or API keys, touch no network,
and never send mail.

## Scope

- Each letter is the client's own request, in their own name — this tool
  doesn't send correspondence asserting representation of the client.
- `send` is gated on a recorded, past-dated consent date; it will not send
  without one.
- No claim of copyright ownership over the photograph is made anywhere in
  the letter; the basis is the client's own right under the applicable
  statute.
- Finding pages uses Google's Custom Search API, not scraped search results.
