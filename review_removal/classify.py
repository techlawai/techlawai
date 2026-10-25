"""Sort reviews into: candidate for a policy report, or reply-only.

This is a keyword screen, not a judgment. A review it marks as a candidate
still needs a person to confirm the policy really applies before it is
reported (main.py's `report` command requires that confirmation per review),
because Google allows a single appeal and a weak report spends it.
"""
import re
from collections import defaultdict
from dataclasses import dataclass, field

from policies import POLICIES
from reviews import Review

NEGATIVE_MAX_RATING = 3


@dataclass
class Match:
    policy: str
    evidence: str


@dataclass
class Classification:
    review: Review
    matches: list[Match] = field(default_factory=list)

    @property
    def is_candidate(self) -> bool:
        return bool(self.matches)

    @property
    def is_negative(self) -> bool:
        # Unrated (e.g. pasted without stars) counts as negative so it is
        # looked at rather than silently skipped.
        return self.review.rating is None or self.review.rating <= NEGATIVE_MAX_RATING

    @property
    def policies(self) -> list[str]:
        seen = []
        for m in self.matches:
            if m.policy not in seen:
                seen.append(m.policy)
        return seen

    @property
    def primary_policy(self) -> str | None:
        return self.policies[0] if self.policies else None

    @property
    def recommendation(self) -> str:
        if self.is_candidate:
            return "report"
        if self.is_negative:
            return "reply"
        return "none"


def _snippet(text: str, start: int, end: int, pad: int = 40) -> str:
    lo, hi = max(0, start - pad), min(len(text), end + pad)
    return ("..." if lo else "") + text[lo:hi].replace("\n", " ") + ("..." if hi < len(text) else "")


def classify_review(review: Review) -> Classification:
    result = Classification(review)
    for key, policy in POLICIES.items():
        for pattern in policy["signals"]:
            m = re.search(pattern, review.text, re.I | re.M)
            if m:
                result.matches.append(Match(key, _snippet(review.text, m.start(), m.end())))
                break
    return result


def _fingerprint(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def classify_reviews(reviews: list[Review]) -> list[Classification]:
    results = [classify_review(r) for r in reviews]

    # Repetitive content can only be seen across the batch: the same text
    # under more than one review.
    by_text = defaultdict(list)
    for result in results:
        fp = _fingerprint(result.review.text)
        if len(fp) >= 20:
            by_text[fp].append(result)
    for group in by_text.values():
        if len(group) > 1:
            names = ", ".join(r.review.reviewer for r in group)
            for result in group:
                result.matches.append(Match(
                    "repetitive_content",
                    f"Same text posted {len(group)} times (by: {names})",
                ))
    return results
