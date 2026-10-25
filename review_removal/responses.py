"""Draft the text that goes to Google and to the public for one review:

- report_note: what the policy report says (the report form itself is a
  reason picker; this is kept in the tracker and reused for the appeal).
- appeal_text: the explanation for Google's one-time appeal.
- owner_reply: the public reply posted under the review.

Everything here is written as the business owner, about Google's own
policies. Nothing claims a legal right, threatens the reviewer, or offers
anything for removal -- those are what get businesses penalised (Google's
policies and the FTC's 16 C.F.R. Part 465 both bar suppressing reviews by
threat or incentive).
"""
from classify import Classification
from policies import POLICIES, POLICY_SOURCE_URL

# Bracketed text a person must fill in or delete before anything is sent.
# rmt_submit.py and gbp_api.py refuse text that still contains one.
PLACEHOLDER_MARK = "[[FILL:"

REPORT_NOTE_TEMPLATE = """\
Review by "{reviewer}" ({rating}, {date}) on {business_name}'s Business Profile.
Policy: {policy_names} -- {policy_url}
Quoted: {evidence}
"""

APPEAL_TEMPLATE = """\
We are appealing the decision on the review by "{reviewer}" posted {date} on
the Business Profile for {business_name}.

This review violates Google Maps' {policy_names} policy
({policy_url}):

{policy_points}
{facts}
We are not asking for removal because the review is negative. We are asking
because the content above falls under the policy named, which Google's
policy states is grounds for removal.

Thank you for taking a second look.
{signer}
"""

# Facts the reviewer's text does not show by itself, which only the client
# can supply. Kept as fill-ins: the appeal must not assert them unless true.
FACT_PROMPTS = {
    "fake_engagement": "[[FILL: what the business's records show, e.g. 'We have no record of a "
                       "customer by this name or of any visit on or around this date.' Delete "
                       "if you cannot confirm it.]]",
    "rating_manipulation": "[[FILL: how the conflict is known, e.g. 'The reviewer is a former "
                           "employee who left on <date>' or 'The reviewer owns <competitor>.' "
                           "Delete if you cannot confirm it.]]",
    "impersonation": "[[FILL: who the reviewer is claiming to be and why that is false. Delete "
                     "if you cannot confirm it.]]",
}

POLICY_POINT = '- {name}: "{evidence}" -- {summary}'

REPLY_TEMPLATES = {
    "default": (
        "Thank you for taking the time to share this. We're sorry to hear your "
        "experience fell short. We'd like to understand what happened and make it "
        "right where we can -- please contact us directly at {contact} so we can "
        "talk it through.\n\n{signer}"
    ),
    "fake_engagement": (
        "Thank you for the feedback. We take every review seriously, but we're unable "
        "to find this experience in our records. If you did visit us, please contact "
        "us at {contact} so we can look into it.\n\n{signer}"
    ),
    "rating_manipulation": (
        "We welcome honest feedback from our customers. We don't believe this review "
        "reflects a customer experience with us, and we've asked Google to look at it "
        "under its review policies. Anyone with a concern about our service is welcome "
        "to reach us at {contact}.\n\n{signer}"
    ),
    "harassment": (
        "We're sorry to see this. We want every customer to have a good experience, and "
        "we're glad to discuss any concern respectfully at {contact}.\n\n{signer}"
    ),
    "personal_information": (
        "To protect the privacy of the people involved, we won't discuss specifics "
        "here. We've asked Google to review this post. Please contact us at {contact} "
        "and we'll be glad to help.\n\n{signer}"
    ),
    "off_topic": (
        "Thank you for sharing your view. We focus here on the service we provide, and "
        "we're happy to hear about your experience with us at {contact}.\n\n{signer}"
    ),
}
# Profanity, hate speech, offensive content and the rest all get the calm
# harassment reply: restating or arguing with the content only amplifies it.
for _key in POLICIES:
    REPLY_TEMPLATES.setdefault(_key, REPLY_TEMPLATES["harassment"])


def _rating_label(rating):
    return f"{rating}-star" if rating else "unrated"


def _policy_names(c: Classification) -> str:
    return " / ".join(POLICIES[p]["name"] for p in c.policies)


def report_note(c: Classification, business_name: str) -> str:
    r = c.review
    return REPORT_NOTE_TEMPLATE.format(
        reviewer=r.reviewer,
        rating=_rating_label(r.rating),
        date=r.date or "date unknown",
        business_name=business_name,
        policy_names=_policy_names(c) or "none matched",
        policy_url=POLICY_SOURCE_URL,
        evidence=" | ".join(m.evidence for m in c.matches) or "-",
    )


def appeal_text(c: Classification, business_name: str, signer: str) -> str:
    if not c.is_candidate:
        raise ValueError(
            f"Review {c.review.review_id} matched no Google policy, so there is "
            f"nothing to appeal on. Reply to it instead."
        )
    points = "\n".join(
        POLICY_POINT.format(
            name=POLICIES[m.policy]["name"],
            evidence=m.evidence,
            summary=POLICIES[m.policy]["summary"],
        )
        for m in c.matches
    )
    facts = "".join(f"\n{FACT_PROMPTS[p]}\n" for p in c.policies if p in FACT_PROMPTS)
    return APPEAL_TEMPLATE.format(
        reviewer=c.review.reviewer,
        date=c.review.date or "(date unknown)",
        business_name=business_name,
        policy_names=_policy_names(c),
        policy_url=POLICY_SOURCE_URL,
        policy_points=points,
        facts=facts,
        signer=signer,
    )


def owner_reply(c: Classification, contact: str, signer: str) -> str:
    template = REPLY_TEMPLATES[c.primary_policy or "default"]
    return template.format(contact=contact, signer=signer)


def has_placeholders(text: str) -> bool:
    return PLACEHOLDER_MARK in text
