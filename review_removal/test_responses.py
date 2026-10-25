"""Tests for responses.py -- report notes, appeals and owner replies."""
import re

import pytest

from classify import classify_review
from policies import POLICIES, POLICY_SOURCE_URL
from responses import appeal_text, has_placeholders, owner_reply, report_note
from reviews import Review

FORBIDDEN = [
    r"\bsue\b", r"\blawsuit\b", r"\blegal action\b", r"\battorney\b", r"\bdefamat",
    r"\brefund\b", r"\bdiscount\b", r"\bgift card\b", r"\bremove (your|the|this) review\b",
]


def classified(text, rating=1):
    return classify_review(Review(reviewer="Pat", rating=rating, text=text, date="2026-10-01"))


CASES = [
    classified("Never been here but heard bad things"),
    classified("The owner is a thief"),
    classified("Call him at 555-123-4567"),
    classified("Slow service and cold food"),
]


@pytest.mark.parametrize("c", CASES)
def test_replies_never_threaten_or_offer_anything(c):
    # FTC 16 CFR 465 and Google's policies: no review suppression by threat
    # or incentive.
    reply = owner_reply(c, "help@biz.example", "Sam, Owner")

    for pattern in FORBIDDEN:
        assert not re.search(pattern, reply, re.I), pattern
    assert "help@biz.example" in reply


def test_reply_does_not_repeat_personal_information():
    c = classified("Call him at 555-123-4567")

    assert "555-123-4567" not in owner_reply(c, "help@biz.example", "Sam")


def test_appeal_cites_policy_and_quotes_evidence():
    c = classified("The owner is a thief")
    text = appeal_text(c, "Biz Co", "Sam, Owner")

    assert "Offensive content" in text
    assert POLICY_SOURCE_URL in text
    assert "thief" in text
    assert "not asking for removal because the review is negative" in text


@pytest.mark.parametrize("c", CASES)
def test_appeal_makes_no_legal_threat(c):
    if not c.is_candidate:
        return
    text = appeal_text(c, "Biz Co", "Sam")
    for pattern in FORBIDDEN[:5]:
        assert not re.search(pattern, text, re.I), pattern


def test_facts_only_the_client_knows_are_left_as_fill_ins():
    # "We have no record of this customer" must not be asserted unless true.
    text = appeal_text(classified("Never been here but heard bad things"), "Biz Co", "Sam")

    assert has_placeholders(text)


def test_appeal_on_text_evidence_alone_needs_no_fill_ins():
    assert not has_placeholders(appeal_text(classified("The owner is a thief"), "Biz Co", "Sam"))


def test_cannot_appeal_a_review_with_no_policy_basis():
    with pytest.raises(ValueError, match="matched no Google policy"):
        appeal_text(classified("Slow service and cold food"), "Biz Co", "Sam")


def test_report_note_names_policy():
    note = report_note(classified("The owner is a thief"), "Biz Co")

    assert "Offensive content" in note and "Biz Co" in note


def test_every_policy_has_a_reply_template():
    for key in POLICIES:
        c = classified("x")
        from classify import Match
        c.matches = [Match(key, "x")]
        assert owner_reply(c, "c", "s")
