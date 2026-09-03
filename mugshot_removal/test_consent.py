"""Tests for consent.py -- the client authorization form and date gate."""
from datetime import date, timedelta

import pytest

from consent import generate_consent_form, validate_consent_date


class TestGenerateConsentForm:
    def test_includes_every_supplied_detail(self):
        form = generate_consent_form(
            "Jane Public",
            "jane@example.com",
            "https://example-site.test/jane-public",
            "Fla. Stat. § 901.43",
        )

        assert "Jane Public" in form
        assert "jane@example.com" in form
        assert "https://example-site.test/jane-public" in form
        assert "Fla. Stat. § 901.43" in form

    def test_has_signature_and_date_lines(self):
        form = generate_consent_form("Jane Public", "j@example.com", "u", "cite")

        assert "Signature:" in form
        assert "Date:" in form
        assert "Printed name: Jane Public" in form

    def test_describes_the_letter_as_the_clients_own_request(self):
        # The tool's stated scope is that the letter is the client's own
        # first-person request, so the authorization has to say that.
        form = generate_consent_form("Jane Public", "j@example.com", "u", "cite")

        assert "first-person" in form
        assert "in my name" in form


class TestValidateConsentDate:
    def test_accepts_a_past_date(self):
        assert validate_consent_date("2026-08-19") == date(2026, 8, 19)

    def test_accepts_today(self):
        today = date.today()
        assert validate_consent_date(today.isoformat()) == today

    def test_rejects_a_future_date(self):
        tomorrow = date.today() + timedelta(days=1)

        with pytest.raises(ValueError) as exc_info:
            validate_consent_date(tomorrow.isoformat())

        assert "future" in str(exc_info.value)

    def test_rejects_a_far_future_date(self):
        with pytest.raises(ValueError):
            validate_consent_date("2999-01-01")

    @pytest.mark.parametrize(
        "garbage",
        ["", "not-a-date", "08/19/2026", "2026-13-01", "2026-02-30", "yesterday"],
    )
    def test_rejects_unparseable_input(self, garbage):
        with pytest.raises(ValueError):
            validate_consent_date(garbage)

    def test_returns_a_date_object(self):
        assert isinstance(validate_consent_date("2026-08-19"), date)
