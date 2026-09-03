"""State-by-state booking-photograph removal statutes.

Only includes fields actually confirmed via research for this build. Where a
removal deadline or penalty wasn't confirmed, it's left as None rather than
guessed -- a demand letter citing a wrong number is worse than one that
cites the statute correctly and states the request without a fabricated
figure. VERIFY current statutory text before relying on any entry here for
real correspondence; state legislatures amend and renumber these regularly.

confidence:
  "verified"   -> citation, deadline, and penalty confirmed from research
  "partial"    -> citation and fee-prohibition confirmed; deadline/penalty
                  NOT confirmed. Left as None where research turned up
                  nothing; where an unconfirmed figure is recorded anyway
                  (TX), it is still unverified. Either way the generated
                  letter carries a note telling the operator to verify the
                  statute before sending -- see draft.py.
"""

STATE_STATUTES = {
    "FL": {
        "name": "Florida",
        "citation": "Fla. Stat. § 901.43",
        "fee_prohibited": True,
        "removal_deadline_days": 10,
        "penalty_description": "civil penalty up to $1,000/day of noncompliance with an injunction, plus attorney fees and costs",
        "confidence": "verified",
    },
    "CA": {
        "name": "California",
        "citation": "Cal. Civ. Code § 1798.91.1",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "partial",
    },
    "TX": {
        "name": "Texas",
        "citation": "Tex. Bus. & Com. Code ch. 109",
        "fee_prohibited": True,
        "removal_deadline_days": 45,
        "penalty_description": "civil action for noncompliance; damages and other legal remedies per statute",
        "confidence": "partial",
    },
    "GA": {
        "name": "Georgia",
        "citation": "O.C.G.A. § 35-1-19 (HB 845)",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "partial",
    },
    "UT": {
        "name": "Utah",
        "citation": "Utah Code § 17-22-30",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "partial",
    },
    "OR": {
        "name": "Oregon",
        "citation": "Or. Rev. Stat. § 30.835",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "partial",
    },
    "CO": {
        "name": "Colorado",
        "citation": "Colo. Rev. Stat. § 18-12-105.7",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "partial",
    },
    "IL": {
        "name": "Illinois",
        "citation": "730 ILCS 5/5-4-7",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "partial",
    },
    "WY": {
        "name": "Wyoming",
        "citation": "Wyoming booking-photograph removal statute (2021 session laws)",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "partial",
    },
}


def get_statute(state_code: str) -> dict:
    state_code = state_code.upper()
    if state_code not in STATE_STATUTES:
        raise KeyError(
            f"No statute entry for '{state_code}'. Only states actually researched for "
            f"this tool are included: {', '.join(STATE_STATUTES)}. Add an entry to "
            f"statutes.py (with real citation/confidence) before using a new state."
        )
    return STATE_STATUTES[state_code]
