"""Tests for gbp_api.py, against a fake authorized session (no network)."""
import json

import gbp_api


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, pages):
        self.pages = pages  # url -> list of responses, popped in order
        self.calls = []

    def get(self, url, params=None):
        self.calls.append(("GET", url, dict(params or {})))
        return FakeResponse(self.pages[url].pop(0))

    def put(self, url, data=None, headers=None):
        self.calls.append(("PUT", url, json.loads(data)))
        return FakeResponse({"comment": json.loads(data)["comment"]})


def test_fetch_reviews_pages_and_maps_fields():
    url = gbp_api.REVIEWS_URL.format(account="accounts/1", location="locations/2")
    session = FakeSession({url: [
        {"reviews": [{"reviewId": "abc", "name": "accounts/1/locations/2/reviews/abc",
                      "reviewer": {"displayName": "Ann"}, "starRating": "ONE",
                      "comment": "Bad", "createTime": "2026-10-01T12:00:00Z"}],
         "nextPageToken": "t2"},
        {"reviews": [{"reviewId": "def", "name": "accounts/1/locations/2/reviews/def",
                      "starRating": "FIVE", "createTime": "2026-10-02T00:00:00Z",
                      "reviewReply": {"comment": "Thanks"}}]},
    ]})

    ann, anon = gbp_api.fetch_reviews(session, "accounts/1", "locations/2")

    assert (ann.reviewer, ann.rating, ann.text, ann.date) == ("Ann", 1, "Bad", "2026-10-01")
    assert ann.review_id == "abc" and ann.api_name.endswith("reviews/abc")
    assert anon.reviewer == "Anonymous" and anon.extra["has_reply"]
    assert session.calls[1][2]["pageToken"] == "t2"


def test_post_reply_puts_comment_to_review_reply_endpoint():
    session = FakeSession({})

    gbp_api.post_reply(session, "accounts/1/locations/2/reviews/abc", "Thank you")

    method, url, body = session.calls[0]
    assert method == "PUT"
    assert url == "https://mybusiness.googleapis.com/v4/accounts/1/locations/2/reviews/abc/reply"
    assert body == {"comment": "Thank you"}


def test_list_locations_walks_accounts():
    loc_url = gbp_api.LOCATIONS_URL.format(account="accounts/1")
    session = FakeSession({
        gbp_api.ACCOUNTS_URL: [{"accounts": [{"name": "accounts/1"}]}],
        loc_url: [{"locations": [{"name": "locations/2", "title": "Acme"}]}],
    })

    assert gbp_api.list_locations(session) == [
        {"account": "accounts/1", "location": "locations/2", "title": "Acme"}]
