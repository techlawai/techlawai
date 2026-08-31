# Mugshot Removal Tool (Fla. Stat. § 901.43)

Search, draft, send, and track booking-photo removal requests. Each request
is generated and sent as the client's own first-person statutory request
(the client is the "From" address and the signer) — not as a third party
representing them.

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

Preview a letter without sending:
```
python main.py draft --client-name "Jane Public" --client-contact "jane@example.com" \
  --target-url "https://example-mugshot-site.com/jane-public" \
  --booking-date "2026-08-19" --arresting-agency "Palm Beach County Sheriff's Office"
```

Send it and log to a tracker sheet:
```
python main.py send --client-name "Jane Public" --client-email "jane@example.com" \
  --target-url "https://example-mugshot-site.com/jane-public" \
  --to-email "abuse@example-mugshot-site.com" \
  --booking-date "2026-08-19" --arresting-agency "Palm Beach County Sheriff's Office" \
  --smtp-host smtp.gmail.com --smtp-port 465 \
  --smtp-username jane@example.com --smtp-password APP_PASSWORD \
  --sheet-id YOUR_SHEET_ID
```

Check which requests are past their 10-day deadline with no removal:
```
python main.py check-overdue --sheet-id YOUR_SHEET_ID
```
That's the point at which Fla. Stat. § 901.43 lets the client seek an
injunction, a $1,000/day penalty, and attorney fees — that step itself
still needs an actual attorney to file, this tool just tells you when a
given request has crossed that line.

## Scope

- Each letter is the client's own request, in their own name — this tool
  doesn't send correspondence asserting representation of the client.
- No claim of copyright ownership over the photograph is made anywhere in
  the letter; the basis is the client's own right under § 901.43.
- Finding pages uses Google's Custom Search API, not scraped search results.
