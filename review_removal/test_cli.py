"""End-to-end tests for cli.py with the browser and API stubbed out."""
import sys
from datetime import date, timedelta

import pytest

import cli
import review_tracker as tracker
import rmt_submit
from test_rmt_submit import FakeUI

REVIEWS = """Reviewer: Ann
Rating: 1
Date: 2026-10-01
The owner is a thief and a crook.
---
Reviewer: Ben
Rating: 2
Date: 2026-10-02
Slow service, cold food.
---
Reviewer: Cal
Rating: 1
Date: 2026-10-03
Never been there but heard they rip people off.
"""

PAST = (date.today() - timedelta(days=3)).isoformat()


@pytest.fixture
def run(monkeypatch, tmp_path):
    def _run(*argv):
        monkeypatch.setattr(sys, "argv", ["cli.py", *argv, "--tracker-dir", str(tmp_path)]
                            if argv[0] not in ("list-policies",) else ["cli.py", *argv])
        return cli.main()
    _run.tracker = lambda: tracker.load(tracker.tracker_path(str(tmp_path), "Acme"))
    return _run


@pytest.fixture
def imported(run, tmp_path):
    f = tmp_path / "reviews.txt"
    f.write_text(REVIEWS)
    run("import", "--client", "Acme", "--file", str(f))
    return {r["Reviewer"]: r for r in run.tracker()}


@pytest.fixture
def fake_browser(monkeypatch):
    ui = FakeUI()
    ui.shutdown = lambda: None
    monkeypatch.setattr(cli, "_launch_ui", lambda args: ui)
    monkeypatch.setattr(rmt_submit, "pace", lambda *a: None)
    return ui


def test_import_screens_reviews(imported):
    assert imported["Ann"]["Recommendation"] == "report"
    assert imported["Ben"]["Status"] == "Reply only"
    assert "fake_engagement" in imported["Cal"]["Policies"]


def test_draft_writes_reply_for_everything_and_appeal_only_for_candidates(run, imported, tmp_path):
    out = tmp_path / "drafts.md"
    run("draft", "--client", "Acme", "--business", "Acme Co", "--contact", "hi@acme.example",
        "--signer", "Sam", "--out", str(out))
    text = out.read_text()

    assert text.count("### Owner reply") == 3
    assert text.count("### Appeal") == 2
    assert "Recommendation: reply only" in text


def test_report_refuses_without_authorization_date(run, imported):
    with pytest.raises(SystemExit, match="Authorization date"):
        run("report", "--client", "Acme", "--business", "Acme Co", "--profile-dir", "p",
            "--authorization-date", (date.today() + timedelta(days=1)).isoformat())


def test_report_only_sends_confirmed_reviews(run, imported, fake_browser):
    run("confirm", "--client", "Acme", "--review-id", imported["Ann"]["Review ID"])
    run("report", "--client", "Acme", "--business", "Acme Co", "--profile-dir", "p",
        "--authorization-date", PAST, "--auto-submit")

    rows = {r["Reviewer"]: r for r in run.tracker()}
    assert rows["Ann"]["Status"] == "Decision pending"
    assert rows["Cal"]["Status"] == "New"  # a candidate, but never confirmed
    assert [e for e in fake_browser.log if e[0] == "click_in_row"] == [
        ("click_in_row", "Ann", "Report")]
    assert ("choose", "Bullying or harassment") in fake_browser.log


def test_cannot_confirm_reply_only_review_without_a_stated_policy(run, imported):
    with pytest.raises(SystemExit, match="matched no Google policy"):
        run("confirm", "--client", "Acme", "--review-id", imported["Ben"]["Review ID"])


def test_client_known_policy_can_be_confirmed_and_is_kept(run, imported, fake_browser):
    rid = imported["Ben"]["Review ID"]
    run("confirm", "--client", "Acme", "--review-id", rid, "--policy", "rating_manipulation",
        "--note", "reviewer owns the competing restaurant across the street")
    run("report", "--client", "Acme", "--business", "Acme Co", "--profile-dir", "p",
        "--authorization-date", PAST, "--auto-submit")

    assert ("choose", "Conflict of interest") in fake_browser.log
    row = [r for r in run.tracker() if r["Review ID"] == rid][0]
    assert "competing restaurant" in row["Notes"]


def test_appeal_refuses_unfilled_facts(run, imported, fake_browser):
    rid = imported["Cal"]["Review ID"]
    run("confirm", "--client", "Acme", "--review-id", rid)
    run("status", "--client", "Acme", "--set", rid, "No policy violation")

    with pytest.raises(SystemExit, match="FILL"):
        run("appeal", "--client", "Acme", "--business", "Acme Co", "--signer", "Sam",
            "--profile-dir", "p", "--authorization-date", PAST, "--auto-submit")
    assert not any(e[0] == "fill" for e in fake_browser.log)


def test_appeal_with_edited_text_escalates(run, imported, fake_browser, tmp_path):
    rid = imported["Cal"]["Review ID"]
    run("confirm", "--client", "Acme", "--review-id", rid)
    run("status", "--client", "Acme", "--set", rid, "No policy violation")
    appeal = tmp_path / "appeal.txt"
    appeal.write_text("We have no record of this reviewer.")

    run("appeal", "--client", "Acme", "--business", "Acme Co", "--signer", "Sam",
        "--profile-dir", "p", "--authorization-date", PAST, "--auto-submit",
        "--appeal-file", str(appeal))

    assert ("fill", "We have no record of this reviewer.") in fake_browser.log
    row = [r for r in run.tracker() if r["Review ID"] == rid][0]
    assert row["Status"] == "Escalated"


def test_reply_posts_through_api_for_fetched_reviews(run, monkeypatch, tmp_path):
    import gbp_api
    from reviews import Review

    review = Review(reviewer="Dee", rating=1, text="Slow", date="2026-10-04",
                    review_id="xyz", api_name="accounts/1/locations/2/reviews/xyz")
    posted = []
    monkeypatch.setattr(gbp_api, "authorized_session", lambda *a: "session")
    monkeypatch.setattr(gbp_api, "fetch_reviews", lambda s, a, l: [review])
    monkeypatch.setattr(gbp_api, "post_reply", lambda s, name, text: posted.append((name, text)))

    run("fetch", "--client", "Acme", "--account", "accounts/1", "--location", "locations/2")
    run("reply", "--client", "Acme", "--contact", "hi@acme.example", "--signer", "Sam",
        "--authorization-date", PAST, "--yes")

    assert posted and posted[0][0].endswith("reviews/xyz")
    assert run.tracker()[0]["Replied Date"] == date.today().isoformat()

    # A second run doesn't reply twice.
    with pytest.raises(SystemExit, match="Nothing to reply to"):
        run("reply", "--client", "Acme", "--contact", "c", "--signer", "s",
            "--authorization-date", PAST, "--yes")
