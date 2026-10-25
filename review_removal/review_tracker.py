"""Per-client status of every review: one CSV file per client.

Statuses follow the Reviews Management Tool's own labels where Google has
one, so the tracker can be checked against what the tool shows:

  New                  imported, not looked at yet
  Reply only           matched no Google policy; reply, don't report
  Confirmed            a person confirmed the policy applies; ready to report
  Decision pending     reported; Google has not decided   (RMT: "Decision pending")
  No policy violation  Google kept it; one appeal allowed (RMT: "Report reviewed - no policy violation")
  Escalated            appealed; final answer comes by email (RMT: "Escalated - check your email for updates")
  Removed              Google took it down
  Remains live         appeal denied; Google's process is exhausted
"""
import csv
import os
import re
from datetime import date

STATUSES = [
    "New",
    "Reply only",
    "Confirmed",
    "Decision pending",
    "No policy violation",
    "Escalated",
    "Removed",
    "Remains live",
]

# Statuses an import must not overwrite: they record something a person or
# Google decided, which a re-run of the keyword screen knows nothing about.
DECIDED = set(STATUSES) - {"New", "Reply only"}

FIELDS = [
    "Review ID",
    "Reviewer",
    "Rating",
    "Review Date",
    "Review URL",
    "API Name",
    "Review Text",
    "Policies",
    "Recommendation",
    "Status",
    "Reported Date",
    "Appealed Date",
    "Replied Date",
    "Last Updated",
    "Notes",
]


def client_slug(client_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", client_name.lower()).strip("-")
    if not slug:
        raise ValueError(f"Client name {client_name!r} has no usable characters.")
    return slug


def tracker_path(tracker_dir: str, client_name: str) -> str:
    return os.path.join(tracker_dir, f"{client_slug(client_name)}.csv")


def load(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(path: str, rows: list[dict]):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDS})
    os.replace(tmp, path)


def upsert_classifications(path: str, classifications, today: date | None = None) -> list[dict]:
    """Add new reviews and refresh undecided ones. Returns the rows."""
    today = (today or date.today()).isoformat()
    rows = load(path)
    by_id = {row["Review ID"]: row for row in rows}
    for c in classifications:
        r = c.review
        row = by_id.get(r.review_id)
        if row is None:
            row = {"Review ID": r.review_id, "Status": "New"}
            rows.append(row)
            by_id[r.review_id] = row
        row.update({
            "Reviewer": r.reviewer,
            "Rating": r.rating or "",
            "Review Date": r.date,
            "Review URL": r.url or row.get("Review URL", ""),
            "API Name": r.api_name or row.get("API Name", ""),
            "Review Text": r.text,
        })
        if row["Status"] in DECIDED:
            continue
        row.update({
            "Policies": ", ".join(c.policies),
            "Recommendation": c.recommendation,
            "Status": "Reply only" if c.recommendation == "reply" else "New",
            "Last Updated": today,
        })
    save(path, rows)
    return rows


def get_row(rows: list[dict], review_id: str) -> dict:
    for row in rows:
        if row["Review ID"] == review_id:
            return row
    raise KeyError(f"No review {review_id!r} in tracker.")


def set_status(path: str, review_id: str, status: str, note: str = "",
               today: date | None = None) -> dict:
    if status not in STATUSES:
        raise ValueError(f"Unknown status {status!r}. Use one of: {', '.join(STATUSES)}")
    today = (today or date.today()).isoformat()
    rows = load(path)
    row = get_row(rows, review_id)
    row["Status"] = status
    row["Last Updated"] = today
    if status == "Decision pending" and not row.get("Reported Date"):
        row["Reported Date"] = today
    if status == "Escalated" and not row.get("Appealed Date"):
        row["Appealed Date"] = today
    if note:
        row["Notes"] = f"{row['Notes']}; {today}: {note}" if row.get("Notes") else f"{today}: {note}"
    save(path, rows)
    return row


def mark_replied(path: str, review_id: str, today: date | None = None) -> dict:
    today = (today or date.today()).isoformat()
    rows = load(path)
    row = get_row(rows, review_id)
    row["Replied Date"] = today
    row["Last Updated"] = today
    save(path, rows)
    return row


def summary(rows: list[dict]) -> dict:
    counts = {s: 0 for s in STATUSES}
    for row in rows:
        counts[row.get("Status", "New")] = counts.get(row.get("Status", "New"), 0) + 1
    return counts
