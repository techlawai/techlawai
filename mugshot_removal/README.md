# Mugshot Removal Tool (multi-state)

Search, draft, send, and track booking-photo removal requests across states
with a fee-prohibition/removal statute. Each request is generated and sent
as the client's own first-person statutory request (the client is the
"From" address and the signer) — not as a third party representing them.

## Supported states

See `statutes.py`. Every entry carries a `confidence` level, and that level
decides what the letter is allowed to assert:

| Level | States | Letter asserts |
|---|---|---|
| `verified` | FL | The statute, its removal deadline, and the noncompliance remedy |
| `partial` | CA, GA | The statute and its fee prohibition, plus an operator-verify note |
| `unverified` | TX, UT, OR, CO, IL, WY | **Nothing.** No statute is cited and no entitlement is claimed — it is a plain request to remove, plus an operator-verify note |

An `unverified` entry is not just missing numbers — it means no statutory
basis this letter could assert has been confirmed for that state. A 2026
audit found all six citing either an unrelated statute (OR pointed at
Oregon's improper-disclosure action, CO at the criminal code's firearms
article, IL at the Unified Code of Corrections, WY at a placeholder) or one
that regulates somebody other than the publisher (UT binds sheriffs; TX ch.
109 is a dispute-accuracy regime). Each entry records the citation research
now points to, as a starting point for whoever verifies it — the letter does
not use it. Run `python main.py list-states` for the full data.

Adding a state, or promoting one, means confirming against primary statutory
text what the statute grants **and against whom** — not extrapolating from
another state's numbers, and not from secondary summaries.

Two live caveats on the `partial` states, both recorded in `statutes.py`:
CA bars charging for removal but imposes no duty to remove; GA's right is
conditional on the disposition of the charges and its written request may
have to go by certified mail, which this tool does not do.

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

**Where the publisher sits** is recorded alongside that: the tracker's
`Registrant Country`, `Hosting Country` and `Hosting Address` columns come
from the same WHOIS/RDAP pass. That matters for two decisions the attorney
makes — venue, and which state's law actually reaches the publisher, which
need not be the state the client was arrested in. Treat it as a lead, not a
finding: registrant country comes from a WHOIS record that is frequently
privacy-shielded, and the hosting country is where the *network* is
registered, which is often a CDN or a datacenter rather than the operator.

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
  statute, or — for `unverified` states — no legal basis is claimed at all.
- **Never fall back to a DMCA takedown.** The booking photograph is the
  arresting agency's work; the client does not own it. 17 U.S.C.
  § 512(c)(3)(A) requires the sender to state *under penalty of perjury*
  that they own the copyright or act for the owner, and § 512(f) makes a
  knowing misrepresentation actionable for damages, costs and fees. These
  letters go out in the client's own name, so that exposure would land on
  the client. `test_draft.py` enforces this on every generated letter.
- Finding pages uses Google's Custom Search API, not scraped search results.
