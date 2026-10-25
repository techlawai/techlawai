"""Google's prohibited-content policies for Maps reviews, as this tool uses them.

Source: Google Maps "Prohibited & restricted content" policy,
https://support.google.com/contributionpolicy/answer/7400114 (checked
2026-10-25). Category names below are Google's own. Google removes a review
only when it violates one of these -- not because it is negative, unfair, or
disputed. See NOT_GROUNDS.

Each entry's `signals` are regexes that make a review a *candidate* for that
category. They are deliberately conservative and are not a finding: every
match still goes in front of a person before anything is reported (see
classify.py and main.py's report command).

`report_reason` is the reason we pick in Google's report form. Google does
not publish that form's full option list -- its help page only gives "Spam"
and "Profanity" as examples -- so these labels are the options the form has
historically offered, not ones confirmed against the live form for this tool.
rmt_submit.py stops rather than guessing when a label is not on the page.
"""

POLICY_SOURCE_URL = "https://support.google.com/contributionpolicy/answer/7400114"

POLICIES = {
    "fake_engagement": {
        "name": "Fake engagement",
        "group": "Fake & Misleading Content & Behavior",
        "summary": "Content not based on a real experience at the business: invented, "
                   "paid, multi-account, or posted by someone who was never a customer.",
        "report_reason": "Spam",
        "signals": [
            r"\bnever (been|went|visited|used|tried|bought|ate|stayed|hired)\b",
            r"\b(haven'?t|have not|didn'?t|did not) (actually )?(been|go|visit|use|try|hire)\b",
            r"\b(heard|was told|i hear|people say) (that )?(they|this place|this business|it)\b",
            r"\bpaid (me|us) to (write|post|leave)\b",
        ],
    },
    "rating_manipulation": {
        "name": "Rating manipulation",
        "group": "Fake & Misleading Content & Behavior",
        "summary": "Biased or conflict-of-interest reviews: competitors, current or former "
                   "employees, owners of other businesses, or incentivized reviews.",
        "report_reason": "Conflict of interest",
        "signals": [
            r"\b(former|ex|current)[- ]?(employee|staff|worker|manager)\b",
            r"\bi (used to )?work(ed)? (here|there|for (them|this))\b",
            r"\b(go to|try|use|visit) (my|our) (shop|store|business|company|office|place) instead\b",
            r"\b(competitor|competing business)\b",
            r"\bin exchange for (a )?(discount|refund|free)\b",
        ],
    },
    "impersonation": {
        "name": "Impersonation",
        "group": "Fake & Misleading Content & Behavior",
        "summary": "Posing as another person, group, or authoritative source.",
        "report_reason": "Spam",
        "signals": [
            r"\b(as|i am|i'?m) (a|an|the) (health|building|fire) inspector\b",
            r"\bon behalf of (the )?(city|county|state|police|bbb|better business bureau)\b",
        ],
    },
    "harassment": {
        "name": "Harassment",
        "group": "Inappropriate content & behavior",
        "summary": "Threatening, targeting or bullying people or the business, or doxxing.",
        "report_reason": "Bullying or harassment",
        "signals": [
            r"\b(i'?ll|i will|we will|gonna|going to) (find|get|hurt|kill|ruin|destroy|come for) (you|him|her|them|this)\b",
            r"\b(watch your back|you'?ll regret|you will regret|burn (it|this place) down)\b",
            r"\b(tell|telling) everyone (i know )?to (avoid|boycott)\b.*\buntil\b",
            r"\bremove (this|my) review (if|when) you (pay|refund|give)\b",
        ],
    },
    "hate_speech": {
        "name": "Hate speech",
        "group": "Inappropriate content & behavior",
        "summary": "Calling for violence against, or demeaning, people based on a protected "
                   "characteristic (race, religion, disability, sex, orientation, etc.).",
        "report_reason": "Discrimination or hate speech",
        # Slurs are not enumerated here. A protected-trait reference next to a
        # demeaning term is the candidate signal; a person makes the call.
        "signals": [
            r"\b(those|these|all|filthy|dirty|stupid) (immigrants|foreigners|mexicans|muslims|jews|"
            r"christians|gays|blacks|whites|asians|arabs|indians)\b",
            r"\bgo back to (your|their) (own )?country\b",
        ],
    },
    "offensive_content": {
        "name": "Offensive content",
        "group": "Inappropriate content & behavior",
        "summary": "Personal attacks, deliberately provocative content, or unproven "
                   "accusations of wrongdoing (e.g. calling someone a criminal).",
        "report_reason": "Bullying or harassment",
        "signals": [
            r"\b(is|are|they'?re|he'?s|she'?s) (a |an )?(thie(f|ves)|crook|criminal|scammer|fraud|pedophile|predator|drug dealer)s?\b",
            r"\b(stole|steals|stealing) (from|my)\b",
            r"\b(money laundering|launders money|front for)\b",
        ],
    },
    "personal_information": {
        "name": "Personal information",
        "group": "Inappropriate content & behavior",
        "summary": "Exposing someone's private details without consent: personal phone, "
                   "home address, email, ID numbers, health information. Business "
                   "contact details are allowed.",
        "report_reason": "Personal information",
        "signals": [
            r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",
            r"\b\d{3}-\d{2}-\d{4}\b",
            r"\b[\w.+-]+@[\w-]+\.[\w.]+\b",
            r"\b(lives|living) (at|on)\b",
            r"\bhome address\b",
        ],
    },
    "obscenity_profanity": {
        "name": "Obscenity & profanity",
        "group": "Inappropriate content & behavior",
        "summary": "Profanity used to insult others or to emphasize criticism.",
        "report_reason": "Profanity",
        "signals": [
            r"\bf+u+c+k+\w*",
            r"\bsh[i1]t+\w*",
            r"\bb[i1]tch\w*",
            r"\ba(ss)?hole\w*",
            r"\bc+u+n+t+\w*",
            r"\bd[i1]ck(head)?s?\b",
            r"\bbastards?\b",
            r"\bmotherf\w*",
        ],
    },
    "sexually_explicit": {
        "name": "Sexually explicit content",
        "group": "Inappropriate content & behavior",
        "summary": "Sexual or nude material.",
        "report_reason": "Profanity",
        "signals": [r"\b(porn|nude|naked|blowjob|sex with)\b"],
    },
    "off_topic": {
        "name": "Off-topic",
        "group": "Inappropriate content & behavior",
        "summary": "Not about an experience at this location: political or social "
                   "commentary, rants about unrelated matters, or another business.",
        "report_reason": "Off topic",
        "signals": [
            r"\b(democrats?|republicans?|liberals?|conservatives?|trump|biden|harris|maga|woke)\b",
            r"\b(wrong (business|place|location)|meant to review)\b",
        ],
    },
    "advertising_solicitation": {
        "name": "Advertising & solicitation",
        "group": "Inappropriate content & behavior",
        "summary": "Promotions, offers, or contact details, social handles or links.",
        "report_reason": "Spam",
        "signals": [
            r"https?://\S+",
            r"\bwww\.\S+",
            r"\b(use (my|our|promo) code|dm me|follow (me|us) on|check out my)\b",
        ],
    },
    "unclear_content": {
        "name": "Unclear content",
        "group": "Unclear and Repetitive Content",
        "summary": "Meaningless or gibberish character strings.",
        "report_reason": "Spam",
        "signals": [r"(.)\1{7,}", r"^[^aeiouy\s]{12,}$"],
    },
    "repetitive_content": {
        "name": "Repetitive content",
        "group": "Unclear and Repetitive Content",
        "summary": "The same review posted repeatedly, from one account or several.",
        "report_reason": "Spam",
        # Detected across the batch in classify.py, not per review.
        "signals": [],
    },
}

# Things owners commonly want removed that Google's policies do not cover.
# Reporting these wastes the one appeal Google allows, and Google's help page
# says outright: "Do not report a review just because you disagree with it or
# dislike it."
NOT_GROUNDS = [
    "The review is negative, harsh, or unfair.",
    "The owner disputes the facts (wrong price, wrong date, didn't happen that way).",
    "The review is star-only with no text.",
    "The reviewer is suspected, but not shown, to be a competitor or non-customer.",
    "The review hurts the business's rating or revenue.",
]

LEGAL_ROUTE_NOTE = (
    "A review that is false and damaging (defamation), or that breaks another "
    "law, is a legal matter rather than a policy report. Google takes those "
    "through its legal removal request form, not the Reviews Management Tool. "
    "That route needs the client's own sworn statement and is a decision for "
    "an attorney; this tool does not draft or file it."
)


def get_policy(key: str) -> dict:
    try:
        return POLICIES[key]
    except KeyError:
        raise ValueError(f"Unknown policy '{key}'. Known: {', '.join(POLICIES)}")
