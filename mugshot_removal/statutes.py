"""State-by-state booking-photograph removal statutes.

Only includes fields actually confirmed via research for this build. Where a
removal deadline or penalty wasn't confirmed, it's left as None rather than
guessed -- a demand letter citing a wrong number is worse than one that
cites the statute correctly and states the request without a fabricated
figure. VERIFY current statutory text before relying on any entry here for
real correspondence; state legislatures amend and renumber these regularly.

confidence:
  "verified"   -> citation, deadline, and penalty confirmed from research.
                  Letter asserts the deadline and the noncompliance remedy.
  "partial"    -> citation confirmed and publisher-facing, and the fee
                  prohibition confirmed; deadline/penalty NOT confirmed and
                  left as None. Letter asserts the fee prohibition and
                  carries an operator-verify note.
  "unverified" -> no statutory basis this letter can assert has been
                  confirmed. The letter cites NOTHING and claims no legal
                  entitlement -- it is a plain request to remove. The
                  citation recorded here is research signposting for whoever
                  verifies the state, not something the letter uses.

An entry being less than "verified" is not merely about missing numbers -- it
may be wrong about what the statute does at all. Every "unverified" entry
below was found citing either an unrelated statute or one that regulates
somebody other than the publisher. Confirm what a statute actually grants,
and against whom, before promoting it.

A NOTE ON DMCA: do not "fall back" to a copyright takedown for the states
without a statutory hook. A booking photograph is the arresting agency's
work, not the client's. 17 U.S.C. § 512(c)(3)(A) requires the sender to state
UNDER PENALTY OF PERJURY that they own the copyright or act for the owner,
and § 512(f) makes a knowing misrepresentation actionable for damages, costs
and fees. These letters go out in the client's own name, so that exposure
would land on the client. The unverified-state letter asks, it does not
claim.
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
    # Publisher-facing and correct. Note it bars CHARGING for removal; it does
    # not itself impose a duty to remove, which is why there is no deadline.
    # It does carry a client remedy not recorded here (reported as $1,000 per
    # violation or actual damages, plus attorney fees) -- confirm before
    # asserting it.
    "CA": {
        "name": "California",
        "citation": "Cal. Civ. Code § 1798.91.1",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "partial",
    },
    # Publisher-facing and correct. TWO CAVEATS before relying on it:
    #   - The removal right is CONDITIONAL, reported as applying where the
    #     charges were dismissed, the person was acquitted, or the record was
    #     sealed/expunged. This tool never captures the client's disposition,
    #     so it cannot tell whether a given client qualifies.
    #   - The written request is reported to require certified mail with
    #     return receipt, or statutory overnight delivery. This tool sends
    #     EMAIL, which may not perfect the request.
    # A 30-day deadline is reported but left unconfirmed here for that reason.
    "GA": {
        "name": "Georgia",
        "citation": "O.C.G.A. § 35-1-19",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "partial",
    },
    # --- unverified: letter makes no statutory claim ------------------------
    # Ch. 109 is a dispute-accuracy regime, not a booking-photo removal right.
    # Its "45 days" is 45 BUSINESS days under § 109.004 to complete an
    # investigation into information the subject DISPUTED as incomplete or
    # inaccurate; removal, where required, is "promptly." Its fee prohibition
    # is tied to that process, so it does not support a general demand to take
    # down an accurate booking photo. § 109.006's civil penalty runs to the
    # state, suable by the attorney general or a prosecuting attorney.
    # There IS a private right of action under § 109.005 -- $500/violation
    # plus injunctive relief -- but only for publishing a record covered by an
    # expunction order or an order of nondisclosure. Different letter.
    "TX": {
        "name": "Texas",
        "citation": "Tex. Bus. & Com. Code ch. 109",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "unverified",
    },
    # Regulates SHERIFFS, not publishers: a sheriff may not release a booking
    # photo to someone who will post it on a pay-to-remove site, and requesters
    # must sign a statement. It does make a pay site's fee demand "theft by
    # extortion" -- criminal, not a civil removal right the client asserts.
    # ALSO STALE: renumbered 11/6/2025 in Utah's Title 17 recodification; the
    # new section number was not determined here.
    "UT": {
        "name": "Utah",
        "citation": "Utah Code § 17-22-30 (renumbered 11/6/2025 -- new number unconfirmed)",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "unverified",
    },
    # Previously cited Or. Rev. Stat. § 30.835, which is "Action for improper
    # disclosure of private information" -- unrelated. The booking-photo
    # provision is reported to be ORS 133.875: removal within 30 calendar days
    # of request, statutory damages of $500/day past the deadline, attorney
    # fees. NOTE it reportedly permits conditioning removal on a payment of up
    # to $50, so this is NOT a flat fee prohibition.
    "OR": {
        "name": "Oregon",
        "citation": "Or. Rev. Stat. § 133.875 (unconfirmed; replaces a wrong § 30.835 cite)",
        "fee_prohibited": False,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "unverified",
    },
    # Previously cited Colo. Rev. Stat. § 18-12-105.7, which sits in the
    # criminal code's FIREARMS article -- unrelated. The booking-photo
    # provision is reported to be C.R.S. § 24-72-305.5 (HB 14-1047): removal
    # free of charge within 10 days of a written request where the person was
    # not charged, charges were dropped, or they were acquitted; up to $1,000
    # per violation plus costs; news-media sites exempt.
    "CO": {
        "name": "Colorado",
        "citation": "Colo. Rev. Stat. § 24-72-305.5 (unconfirmed; replaces a wrong § 18-12-105.7 cite)",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "unverified",
    },
    # Previously cited 730 ILCS 5/5-4-7; 730 ILCS 5 is the Unified Code of
    # Corrections and carries no such provision. The fee prohibition is
    # reported to live in the Consumer Fraud Act at 815 ILCS 505/2QQQ:
    # unlawful to solicit or accept a fee to remove or correct criminal record
    # information.
    "IL": {
        "name": "Illinois",
        "citation": "815 ILCS 505/2QQQ (unconfirmed; replaces a wrong 730 ILCS 5/5-4-7 cite)",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "unverified",
    },
    # Previously carried a placeholder, not a citation. Reported to be Wyo.
    # Stat. § 40-12-601 et seq.: removal within 30 days of request where the
    # person was not convicted, enforced under the Wyoming Consumer Protection
    # Act with attorney fees.
    "WY": {
        "name": "Wyoming",
        "citation": "Wyo. Stat. § 40-12-601 et seq. (unconfirmed; replaces a placeholder)",
        "fee_prohibited": True,
        "removal_deadline_days": None,
        "penalty_description": None,
        "confidence": "unverified",
    },
}

CONFIDENCE_LEVELS = {"verified", "partial", "unverified"}


def get_statute(state_code: str) -> dict:
    state_code = state_code.upper()
    if state_code not in STATE_STATUTES:
        raise KeyError(
            f"No statute entry for '{state_code}'. Only states actually researched for "
            f"this tool are included: {', '.join(STATE_STATUTES)}. Add an entry to "
            f"statutes.py (with real citation/confidence) before using a new state."
        )
    return STATE_STATUTES[state_code]
