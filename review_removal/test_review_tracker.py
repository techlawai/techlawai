"""Tests for review_tracker.py -- per-client status CSV."""
from datetime import date

import pytest

import review_tracker as tracker
from classify import classify_reviews
from reviews import Review

TODAY = date(2026, 10, 25)


def batch(*texts):
    return classify_reviews([Review(reviewer=f"R{i}", rating=1, text=t, date="2026-10-01")
                             for i, t in enumerate(texts)])


@pytest.fixture
def path(tmp_path):
    return tracker.tracker_path(str(tmp_path), "Acme Plumbing, LLC")


def test_one_file_per_client(tmp_path):
    assert tracker.tracker_path(str(tmp_path), "Acme Plumbing, LLC").endswith("acme-plumbing-llc.csv")


def test_import_sets_initial_status(path):
    rows = tracker.upsert_classifications(path, batch("The owner is a thief", "Slow"), today=TODAY)

    assert [r["Status"] for r in rows] == ["New", "Reply only"]
    assert rows[0]["Policies"] == "offensive_content"
    assert rows[0]["Review Text"] == "The owner is a thief"


def test_reimport_does_not_duplicate_or_undo_decisions(path):
    rows = tracker.upsert_classifications(path, batch("The owner is a thief"), today=TODAY)
    tracker.set_status(path, rows[0]["Review ID"], "Decision pending", today=TODAY)

    rows = tracker.upsert_classifications(path, batch("The owner is a thief"), today=TODAY)

    assert len(rows) == 1
    assert rows[0]["Status"] == "Decision pending"


def test_status_dates_and_notes(path):
    [row] = tracker.upsert_classifications(path, batch("The owner is a thief"), today=TODAY)
    rid = row["Review ID"]
    tracker.set_status(path, rid, "Decision pending", note="reported", today=TODAY)
    row = tracker.set_status(path, rid, "Escalated", note="appealed", today=date(2026, 11, 2))

    assert row["Reported Date"] == "2026-10-25"
    assert row["Appealed Date"] == "2026-11-02"
    assert row["Notes"] == "2026-10-25: reported; 2026-11-02: appealed"


def test_unknown_status_rejected(path):
    [row] = tracker.upsert_classifications(path, batch("x"), today=TODAY)
    with pytest.raises(ValueError, match="Unknown status"):
        tracker.set_status(path, row["Review ID"], "Deleted")


def test_summary_counts(path):
    rows = tracker.upsert_classifications(path, batch("The owner is a thief", "Slow", "Cold"))

    assert tracker.summary(rows)["Reply only"] == 2
