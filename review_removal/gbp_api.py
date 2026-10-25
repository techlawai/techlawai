"""Google Business Profile API: pull a client's reviews and post owner replies.

This is the automated, Google-sanctioned part of the workflow. The API can
list reviews and create/update/delete the owner's reply. It has no method to
report (flag) a review or to appeal -- those only exist in the Reviews
Management Tool's web UI; see rmt_submit.py.

Access needs, from the client's side:
1. A verified Business Profile (Google requires it to be active 60+ days).
2. A Google Cloud project approved for the Business Profile APIs -- request
   access at https://developers.google.com/my-business/content/prereqs.
   Approval is manual and can take a while.
3. An OAuth client ("Desktop app") from that project, saved as
   client_secret.json. The client (or a manager they added to the profile)
   signs in once; the token is cached in --token.
"""
import json
import os

from reviews import Review, parse_rating

SCOPES = ["https://www.googleapis.com/auth/business.manage"]

ACCOUNTS_URL = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
LOCATIONS_URL = "https://mybusinessbusinessinformation.googleapis.com/v1/{account}/locations"
REVIEWS_URL = "https://mybusiness.googleapis.com/v4/{account}/{location}/reviews"
REPLY_URL = "https://mybusiness.googleapis.com/v4/{review_name}/reply"


def authorized_session(client_secret_path: str, token_path: str):
    """Sign in as the profile owner (browser consent on first run)."""
    from google.auth.transport.requests import AuthorizedSession, Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
        creds = flow.run_local_server(port=0)
    with open(token_path, "w") as f:
        f.write(creds.to_json())
    return AuthorizedSession(creds)


def _get_json(session, url, params=None):
    resp = session.get(url, params=params or {})
    resp.raise_for_status()
    return resp.json()


def list_locations(session) -> list[dict]:
    """Every (account, location, title) the signed-in user can manage."""
    out = []
    for account in _get_json(session, ACCOUNTS_URL).get("accounts", []):
        params = {"readMask": "name,title", "pageSize": 100}
        while True:
            data = _get_json(session, LOCATIONS_URL.format(account=account["name"]), params)
            for loc in data.get("locations", []):
                out.append({"account": account["name"], "location": loc["name"],
                            "title": loc.get("title", "")})
            if not data.get("nextPageToken"):
                break
            params["pageToken"] = data["nextPageToken"]
    return out


def _to_review(raw: dict) -> Review:
    return Review(
        reviewer=(raw.get("reviewer") or {}).get("displayName") or "Anonymous",
        rating=parse_rating(raw.get("starRating")),
        text=raw.get("comment", ""),
        date=(raw.get("createTime") or "")[:10],
        review_id=raw.get("reviewId", ""),
        api_name=raw.get("name", ""),
        extra={"has_reply": bool(raw.get("reviewReply"))},
    )


def fetch_reviews(session, account: str, location: str) -> list[Review]:
    """account: 'accounts/123'; location: 'locations/456' (from list_locations)."""
    url = REVIEWS_URL.format(account=account, location=location)
    params = {"pageSize": 50}
    reviews = []
    while True:
        data = _get_json(session, url, params)
        reviews.extend(_to_review(r) for r in data.get("reviews", []))
        if not data.get("nextPageToken"):
            return reviews
        params["pageToken"] = data["nextPageToken"]


def post_reply(session, review_name: str, comment: str) -> dict:
    """Create or replace the owner's public reply. This publishes immediately."""
    resp = session.put(REPLY_URL.format(review_name=review_name),
                       data=json.dumps({"comment": comment}),
                       headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    return resp.json()
