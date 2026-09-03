"""Tests for statutes.py -- the state statute table and its lookup."""
import pytest

from statutes import (
    CONFIDENCE_LEVELS,
    DISPOSITIONS,
    STATE_STATUTES,
    disposition_qualifies,
    get_statute,
    validate_disposition,
)

REQUIRED_KEYS = {
    "name",
    "citation",
    "fee_prohibited",
    "removal_deadline_days",
    "penalty_description",
    "qualifying_dispositions",
    "confidence",
}


class TestGetStatute:
    def test_returns_entry_for_known_state(self):
        assert get_statute("FL") is STATE_STATUTES["FL"]

    def test_state_code_is_case_insensitive(self):
        assert get_statute("fl") is STATE_STATUTES["FL"]
        assert get_statute("Fl") is STATE_STATUTES["FL"]

    def test_unknown_state_raises(self):
        with pytest.raises(KeyError):
            get_statute("ZZ")

    def test_unknown_state_message_lists_supported_states(self):
        with pytest.raises(KeyError) as exc_info:
            get_statute("ZZ")

        message = str(exc_info.value)
        assert "ZZ" in message
        for state in STATE_STATUTES:
            assert state in message


class TestValidateDisposition:
    @pytest.mark.parametrize("value", DISPOSITIONS)
    def test_accepts_every_known_disposition(self, value):
        assert validate_disposition(value) == value

    def test_normalises_case_and_padding(self):
        assert validate_disposition("  Dismissed  ") == "dismissed"

    @pytest.mark.parametrize(
        "value", ["", "droppped", "nolle", "not guilty", "DISMISSED!", None]
    )
    def test_rejects_anything_else(self, value):
        # A typo must never read as a qualifying outcome.
        with pytest.raises(ValueError):
            validate_disposition(value)

    def test_error_lists_the_valid_values(self):
        with pytest.raises(ValueError) as exc_info:
            validate_disposition("nolle")

        message = str(exc_info.value)
        for value in DISPOSITIONS:
            assert value in message


class TestDispositionQualifies:
    def test_state_without_a_condition_accepts_anything(self):
        florida = STATE_STATUTES["FL"]

        assert disposition_qualifies(florida, "convicted") is True
        assert disposition_qualifies(florida, "") is True
        assert disposition_qualifies(florida, None) is True

    @pytest.mark.parametrize(
        "value", ["not-charged", "dismissed", "acquitted", "sealed", "expunged"]
    )
    def test_conditional_state_accepts_qualifying_outcomes(self, value):
        assert disposition_qualifies(STATE_STATUTES["GA"], value) is True

    @pytest.mark.parametrize("value", ["convicted", "pending", "unknown"])
    def test_conditional_state_rejects_the_rest(self, value):
        assert disposition_qualifies(STATE_STATUTES["GA"], value) is False

    def test_conditional_state_rejects_an_absent_disposition(self):
        # Not knowing how the case ended is not the same as qualifying.
        assert disposition_qualifies(STATE_STATUTES["GA"], "") is False
        assert disposition_qualifies(STATE_STATUTES["GA"], None) is False


class TestStatuteTable:
    @pytest.mark.parametrize("state", sorted(STATE_STATUTES))
    def test_entry_has_every_field(self, state):
        assert set(STATE_STATUTES[state]) == REQUIRED_KEYS

    @pytest.mark.parametrize("state", sorted(STATE_STATUTES))
    def test_confidence_is_a_known_level(self, state):
        assert STATE_STATUTES[state]["confidence"] in CONFIDENCE_LEVELS

    @pytest.mark.parametrize("state", sorted(STATE_STATUTES))
    def test_citation_is_present(self, state):
        assert STATE_STATUTES[state]["citation"].strip()

    @pytest.mark.parametrize(
        "state",
        sorted(s for s, v in STATE_STATUTES.items() if v["confidence"] != "unverified"),
    )
    def test_asserting_states_prohibit_a_fee(self, state):
        # A letter that asserts the fee prohibition must be backed by a state
        # that actually has one. Unverified states assert nothing, so they are
        # exempt -- OR reportedly permits a fee of up to $50.
        assert STATE_STATUTES[state]["fee_prohibited"] is True

    @pytest.mark.parametrize(
        "state",
        sorted(s for s, v in STATE_STATUTES.items() if v["confidence"] == "unverified"),
    )
    def test_unverified_states_assert_no_figures(self, state):
        # Nothing may be carried that the letter could state as fact.
        assert STATE_STATUTES[state]["removal_deadline_days"] is None
        assert STATE_STATUTES[state]["penalty_description"] is None

    @pytest.mark.parametrize("state", sorted(STATE_STATUTES))
    def test_state_codes_are_two_letters(self, state):
        assert len(state) == 2
        assert state.isupper()

    def test_verified_entries_carry_deadline_and_penalty(self):
        # "verified" means the deadline and penalty were confirmed, so a
        # verified entry missing either one is a data error.
        for state, statute in STATE_STATUTES.items():
            if statute["confidence"] != "verified":
                continue
            assert statute["removal_deadline_days"] is not None, state
            assert statute["penalty_description"], state

    def test_deadline_days_are_positive_when_set(self):
        for state, statute in STATE_STATUTES.items():
            days = statute["removal_deadline_days"]
            if days is not None:
                assert isinstance(days, int) and days > 0, state

    def test_florida_is_the_verified_reference_entry(self):
        florida = STATE_STATUTES["FL"]
        assert florida["confidence"] == "verified"
        assert florida["removal_deadline_days"] == 10
        assert "901.43" in florida["citation"]
