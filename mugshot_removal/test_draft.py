"""Tests for draft.py -- the generated removal request letter."""
import re
from datetime import date

import pytest

from draft import generate_letter
from statutes import STATE_STATUTES

REQUEST_DATE = date(2026, 8, 19)

OPERATOR_NOTE_MARKER = "[NOTE TO OPERATOR:"


def recipient_text(letter):
    """The letter minus the operator note -- i.e. what the site actually reads,
    and the only part that can assert anything on the client's behalf."""
    return re.sub(r"\[NOTE TO OPERATOR:.*?\]", "", letter, flags=re.DOTALL)


def letter_for(state, **overrides):
    kwargs = dict(
        client_name="Jane Public",
        client_contact="jane@example.com",
        target_url="https://example-site.test/jane-public",
        state=state,
        request_date=REQUEST_DATE,
    )
    kwargs.update(overrides)
    return generate_letter(**kwargs)


class TestLetterContents:
    def test_includes_client_and_target_details(self):
        letter = letter_for("FL")

        assert "Jane Public" in letter
        assert "jane@example.com" in letter
        assert "https://example-site.test/jane-public" in letter

    def test_cites_the_states_statute(self):
        letter = letter_for("FL")

        assert "Fla. Stat. § 901.43" in letter

    def test_written_in_the_clients_first_person_voice(self):
        # Scope: the letter is the client's own request, not a third party
        # writing on their behalf.
        letter = letter_for("FL")

        assert "My name is Jane Public" in letter
        assert "removal of my arrest" in letter

    def test_makes_no_copyright_claim(self):
        # Stated scope: the basis is the client's statutory right, never an
        # ownership claim over the photograph.
        letter = letter_for("FL")

        assert "copyright" not in letter.lower()

    def test_includes_booking_details_when_given(self):
        letter = letter_for(
            "FL",
            booking_date="2026-07-04",
            arresting_agency="Palm Beach County Sheriff's Office",
        )

        assert "Booking date: 2026-07-04" in letter
        assert "Arresting agency: Palm Beach County Sheriff's Office" in letter

    def test_missing_booking_details_become_not_applicable(self):
        letter = letter_for("FL")

        assert "Booking date: N/A" in letter
        assert "Arresting agency: N/A" in letter


class TestDisposition:
    @pytest.mark.parametrize("state", sorted(STATE_STATUTES))
    def test_every_template_carries_the_disposition(self, state):
        # It appears in all three letter shapes, not just the statutory ones.
        assert "Case disposition: dismissed" in letter_for(
            state, disposition="dismissed"
        )

    @pytest.mark.parametrize("state", sorted(STATE_STATUTES))
    def test_omitted_disposition_reads_as_not_stated(self, state):
        letter = letter_for(state)

        assert "Case disposition: Not stated" in letter
        # Never silently blank, which would read as an answered question.
        assert "Case disposition: \n" not in letter

    def test_is_stated_not_argued(self):
        # The letter reports the disposition; it does not build a claim on it.
        letter = letter_for("GA", disposition="dismissed")

        assert "Case disposition: dismissed" in letter
        assert "because the charges" not in letter


class TestRequestDate:
    def test_uses_the_given_request_date(self):
        letter = letter_for("FL")

        assert "Date of this request: 2026-08-19" in letter

    def test_defaults_to_today(self):
        letter = generate_letter(
            client_name="Jane Public",
            client_contact="jane@example.com",
            target_url="https://example-site.test/jane",
            state="FL",
        )

        assert f"Date of this request: {date.today().isoformat()}" in letter


class TestDeadlineStates:
    def test_states_the_statutory_deadline(self):
        letter = letter_for("FL")

        assert "10 calendar days" in letter

    def test_computes_the_deadline_from_the_request_date(self):
        letter = letter_for("FL")

        # 2026-08-19 + 10 days
        assert "Deadline for removal: 2026-08-29" in letter

    def test_states_the_noncompliance_penalty(self):
        letter = letter_for("FL")

        assert STATE_STATUTES["FL"]["penalty_description"] in letter


class TestUnconfirmedDeadlineStates:
    def test_omits_a_deadline_it_does_not_have(self):
        letter = letter_for("CA")

        assert "calendar days" not in letter
        assert "Deadline for removal:" not in letter

    def test_still_asserts_the_fee_prohibition(self):
        letter = letter_for("CA")

        assert "may not charge a fee" in letter
        assert "Cal. Civ. Code § 1798.91.1" in letter

    def test_warns_the_operator_to_verify(self):
        letter = letter_for("CA")

        assert OPERATOR_NOTE_MARKER in letter
        assert "California" in letter


class TestConfidenceIsSurfaced:
    """Both the module docstring and the README promise that a state whose
    entry is not fully confirmed produces a letter saying so and asking the
    operator to verify the statute before sending. That promise has to hold
    for every "partial" state, including those that do carry a deadline."""

    @pytest.mark.parametrize(
        "state",
        sorted(s for s, v in STATE_STATUTES.items() if v["confidence"] == "partial"),
    )
    def test_partial_states_warn_the_operator(self, state):
        assert OPERATOR_NOTE_MARKER in letter_for(state)

    @pytest.mark.parametrize(
        "state",
        sorted(s for s, v in STATE_STATUTES.items() if v["confidence"] == "verified"),
    )
    def test_verified_states_do_not_warn(self, state):
        assert OPERATOR_NOTE_MARKER not in letter_for(state)


UNVERIFIED_STATES = sorted(
    s for s, v in STATE_STATUTES.items() if v["confidence"] == "unverified"
)


class TestUnverifiedStates:
    """A state with no confirmed statutory hook gets a plain request: it asks,
    it does not claim. Nothing in it may read as a legal entitlement."""

    @pytest.mark.parametrize("state", UNVERIFIED_STATES)
    def test_cites_no_statute(self, state):
        body = recipient_text(letter_for(state))

        assert STATE_STATUTES[state]["citation"] not in body
        assert "Pursuant to" not in body
        assert "Under " not in body

    @pytest.mark.parametrize("state", UNVERIFIED_STATES)
    def test_claims_no_entitlement_or_penalty(self, state):
        body = recipient_text(letter_for(state))

        assert "I am entitled" not in body
        assert "calendar days" not in body
        assert "Deadline for removal:" not in body
        assert "may not charge a fee" not in body

    @pytest.mark.parametrize("state", UNVERIFIED_STATES)
    def test_makes_no_copyright_or_dmca_claim(self, state):
        # A booking photo is the arresting agency's work, and a DMCA notice is
        # sworn under penalty of perjury (17 U.S.C. § 512(c)(3)(A)) with
        # § 512(f) exposure for misrepresentation. These letters go out in the
        # client's own name, so this must never reach the recipient.
        body = recipient_text(letter_for(state)).lower()

        assert "copyright" not in body
        assert "dmca" not in body
        assert "infring" not in body
        assert "penalty of perjury" not in body

    @pytest.mark.parametrize("state", UNVERIFIED_STATES)
    def test_still_asks_for_removal_in_the_clients_voice(self, state):
        letter = letter_for(state)

        assert "My name is Jane Public" in letter
        assert "I am the person depicted" in letter
        assert "remove that photograph" in letter
        assert "https://example-site.test/jane-public" in letter

    @pytest.mark.parametrize("state", UNVERIFIED_STATES)
    def test_warns_the_operator(self, state):
        letter = letter_for(state)

        assert OPERATOR_NOTE_MARKER in letter
        assert STATE_STATUTES[state]["name"] in letter

    @pytest.mark.parametrize("state", UNVERIFIED_STATES)
    def test_operator_note_warns_against_a_dmca_fallback(self, state):
        assert "DMCA" in letter_for(state)

    def test_carries_booking_details(self):
        letter = letter_for(
            UNVERIFIED_STATES[0],
            booking_date="2026-07-04",
            arresting_agency="Travis County Sheriff's Office",
        )

        assert "Booking date: 2026-07-04" in letter
        assert "Arresting agency: Travis County Sheriff's Office" in letter


class TestStateSelection:
    def test_defaults_to_florida(self):
        letter = generate_letter(
            client_name="Jane Public",
            client_contact="jane@example.com",
            target_url="https://example-site.test/jane",
            request_date=REQUEST_DATE,
        )

        assert "Fla. Stat. § 901.43" in letter

    def test_accepts_a_lowercase_state_code(self):
        assert letter_for("ca") == letter_for("CA")

    def test_rejects_an_unknown_state(self):
        with pytest.raises(KeyError):
            letter_for("ZZ")

    @pytest.mark.parametrize("state", sorted(STATE_STATUTES))
    def test_every_supported_state_renders(self, state):
        letter = letter_for(state)

        assert "Jane Public" in letter
        assert "https://example-site.test/jane-public" in letter
        # No unfilled template placeholders left behind.
        assert "{" not in letter

    @pytest.mark.parametrize(
        "state",
        sorted(s for s, v in STATE_STATUTES.items() if v["confidence"] != "unverified"),
    )
    def test_asserting_states_cite_their_statute(self, state):
        assert STATE_STATUTES[state]["citation"] in letter_for(state)
