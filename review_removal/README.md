# Google Review Removal Tool

Screen a client's Google Business Profile reviews against Google's content
policies, draft what to send for each one, submit the reports and the appeal,
post owner replies, and track every review's status per client.

**Read [GUIDE.md](GUIDE.md) first**: it is the step-by-step dispute process
(report → status → appeal → what's left), with appeal templates, and says
which step each command below automates.

## What is automated, and how

| Step | How | Notes |
|---|---|---|
| Pull reviews | Business Profile API (`fetch`) | Or `import` a CSV / pasted text |
| Screen against Google's policies | Keyword screen (`import`/`fetch`) | Flags candidates; a person confirms each one (`confirm`) |
| Draft report note, appeal, owner reply | `draft` | Appeals keep `[[FILL]]` items for facts only the client knows |
| **Report** a review | Reviews Management Tool, in the client's browser (`report`) | No API exists for this |
| **Appeal** declined reports | Reviews Management Tool (`appeal`) | Google allows one appeal, up to 10 reviews |
| Post owner replies | Business Profile API (`reply`) | Publishes immediately |
| Track status per client | `trackers/<client>.csv` (`status`) | Statuses match Google's labels |

Reporting and appealing are browser automation because Google offers no API
for either. The tool runs them in a browser profile the client signs in to by
hand, and it does not handle passwords or get past CAPTCHAs: when Google
challenges, it stops and waits for a person. It asks before every final
Submit unless `--auto-submit` is passed, and spaces reports 20 seconds apart.

**The browser steps were built from Google's published instructions and
tested against a mock page, not against the live Reviews Management Tool.**
Watch the first real run with prompts on. When Google's wording differs, the
run stops naming the label it couldn't find; fix it in `rmt_submit.LABELS`
(and the report reasons in `policies.py`).

## Setup

```
pip install -r requirements.txt
playwright install chromium
```

**Business Profile API** (for `fetch` and `reply`):
1. The profile must be verified and active 60+ days.
2. Request API access for a Google Cloud project:
   https://developers.google.com/my-business/content/prereqs (manual approval).
3. In that project create an OAuth client of type *Desktop app* and save it
   as `client_secret.json`. The first `fetch`/`reply` opens a browser for the
   profile owner (or a Manager) to sign in; the token is kept in `token.json`.

**Reviews Management Tool** (for `report` and `appeal`): one browser profile
folder per client.
```
python cli.py rmt-login --profile-dir profiles/acme
```
Sign in to the client's Google account in the window that opens, then press Enter.

## Usage

```
# 0. Client signs this before anything is submitted
python cli.py authorization-form --client "Acme" --business "Acme Plumbing" --operator "TKO"

# 1. Get reviews in (either)
python cli.py locations
python cli.py fetch  --client "Acme" --account accounts/123 --location locations/456
python cli.py import --client "Acme" --file acme_reviews.csv

# 2. Drafts for everything; read the report candidates
python cli.py draft --client "Acme" --business "Acme Plumbing" \
  --contact "service@acme.example" --signer "Dana, Owner" --out acme_drafts.md

# 3. Confirm the ones that really break a policy
python cli.py confirm --client "Acme" --review-id r-1a2b3c4d5e6f
python cli.py confirm --client "Acme" --review-id r-9f8e7d6c5b4a \
  --policy rating_manipulation --note "reviewer owns the competitor on 5th St"

# 4. Report them
python cli.py report --client "Acme" --business "Acme Plumbing" \
  --profile-dir profiles/acme --authorization-date 2026-10-20

# 5. Record what Google decides (check the Reviews Management Tool after a few days)
python cli.py status --client "Acme" --set r-1a2b3c4d5e6f "No policy violation"

# 6. Appeal the declined ones (fill [[FILL]] items in the draft first)
python cli.py appeal --client "Acme" --business "Acme Plumbing" --signer "Dana, Owner" \
  --profile-dir profiles/acme --authorization-date 2026-10-20 --appeal-file acme_appeal.txt

# 7. Reply to every negative review
python cli.py reply --client "Acme" --contact "service@acme.example" --signer "Dana, Owner" \
  --authorization-date 2026-10-20

python cli.py status --client "Acme"
python cli.py list-policies
```

Pasted text format for `import` (any file not ending in `.csv`): reviews
separated by a line of `---`, each optionally starting with `Reviewer:`,
`Rating:`, `Date:`, `URL:`, `ID:` lines.

## Tests

```
pip install -r requirements-dev.txt
python -m pytest
```

The browser and the API are replaced with fakes, so the suite needs no
credentials, no network, and never submits anything.

## Scope

- Only policy-based reports. A review with no policy basis gets a reply,
  not a report, because a weak report spends the client's one appeal.
- Nothing threatens a reviewer or offers them anything (FTC 16 C.F.R. Part
  465); `test_responses.py` checks every reply and appeal for it.
- Appeals assert no fact the client hasn't supplied; `appeal` refuses text
  with unfilled `[[FILL]]` items.
- `report`, `appeal` and `reply` refuse to run without the date the client
  signed the authorization form.
- Defamation and other legal removals go through Google's legal request
  process with an attorney, not through this tool.
