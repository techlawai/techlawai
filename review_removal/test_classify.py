"""Tests for classify.py -- the keyword screen."""
import pytest

from classify import classify_review, classify_reviews
from reviews import Review


def review(text, rating=1, reviewer="Pat"):
    return Review(reviewer=reviewer, rating=rating, text=text, date="2026-10-01")


@pytest.mark.parametrize("text,policy", [
    ("Never been here but heard they are awful", "fake_engagement"),
    ("I used to work here, the manager is lazy", "rating_manipulation"),
    ("Go to my shop instead, way cheaper", "rating_manipulation"),
    ("Watch your back, you'll regret this", "harassment"),
    ("The owner is a thief and a crook", "offensive_content"),
    ("Call the owner at 555-123-4567 and complain", "personal_information"),
    ("This place is f***ing shit", "obscenity_profanity"),
    ("Typical liberals running this place", "off_topic"),
    ("Get better deals at https://other.example", "advertising_solicitation"),
    ("aaaaaaaaaaaaaaaa", "unclear_content"),
])
def test_flags_policy_candidates(text, policy):
    result = classify_review(review(text))

    assert policy in result.policies
    assert result.recommendation == "report"


@pytest.mark.parametrize("text", [
    "Food was cold and the wait was 45 minutes. Very disappointed.",
    "Overpriced for what you get. Would not recommend.",
    "They charged me twice and never fixed it.",
])
def test_ordinary_bad_experience_is_reply_only(text):
    # Negative and unfair-feeling is not a Google policy violation.
    result = classify_review(review(text))

    assert not result.is_candidate
    assert result.recommendation == "reply"


def test_positive_review_needs_nothing():
    assert classify_review(review("Lovely staff", rating=5)).recommendation == "none"


def test_unrated_counts_as_negative_so_it_is_looked_at():
    assert classify_review(review("Meh", rating=None)).recommendation == "reply"


def test_evidence_quotes_the_matching_text():
    result = classify_review(review("Honestly I never visited, but my friend said it's bad"))

    assert "never visited" in result.matches[0].evidence


def test_repetitive_content_across_batch():
    text = "Worst company ever, do not use them for anything at all"
    results = classify_reviews([review(text, reviewer="A"), review(text, reviewer="B"),
                                review("Different text entirely here", reviewer="C")])

    assert "repetitive_content" in results[0].policies
    assert "repetitive_content" in results[1].policies
    assert "repetitive_content" not in results[2].policies
