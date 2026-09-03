"""Tests for owner_lookup.py -- WHOIS/RDAP research on a target site.

DNS, WHOIS and RDAP are all stubbed (see conftest.py); nothing resolves or
queries a real registry here.
"""
import pytest

import owner_lookup
from owner_lookup import (
    _domain_from_url,
    _extract_abuse_email,
    full_lookup,
    get_domain_info,
    get_hosting_info,
)


class TestDomainFromUrl:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://example-site.test/jane-public", "example-site.test"),
            ("http://example-site.test", "example-site.test"),
            ("example-site.test", "example-site.test"),
            ("example-site.test/jane", "example-site.test"),
            ("https://www.example-site.test/a/b?c=d", "www.example-site.test"),
            ("https://example-site.test:8080/jane", "example-site.test:8080"),
        ],
    )
    def test_extracts_the_host(self, url, expected):
        assert _domain_from_url(url) == expected


class TestGetDomainInfo:
    def test_maps_registrant_fields(self, fake_whois):
        fake_whois(
            {
                "org": "Example Holdings LLC",
                "name": "Jane Registrant",
                "emails": "admin@example-site.test",
                "registrar": "Example Registrar Inc",
                "creation_date": "2015-01-01",
                "country": "US",
            }
        )

        info = get_domain_info("https://example-site.test/jane")

        assert info == {
            "domain": "example-site.test",
            "registrant_org": "Example Holdings LLC",
            "registrant_name": "Jane Registrant",
            "registrant_email": "admin@example-site.test",
            "registrar": "Example Registrar Inc",
            "creation_date": "2015-01-01",
            "country": "US",
        }

    def test_looks_up_the_host_not_the_full_url(self, fake_whois):
        calls = fake_whois({})

        get_domain_info("https://example-site.test/jane-public")

        assert calls == ["example-site.test"]

    def test_takes_the_first_of_a_list_valued_field(self, fake_whois):
        # WHOIS records routinely return lists for these fields.
        fake_whois(
            {
                "emails": ["abuse@example-site.test", "admin@example-site.test"],
                "org": ["Example Holdings LLC"],
            }
        )

        info = get_domain_info("example-site.test")

        assert info["registrant_email"] == "abuse@example-site.test"
        assert info["registrant_org"] == "Example Holdings LLC"

    def test_empty_list_becomes_none(self, fake_whois):
        fake_whois({"emails": [], "org": []})

        info = get_domain_info("example-site.test")

        assert info["registrant_email"] is None
        assert info["registrant_org"] is None

    def test_absent_fields_become_none(self, fake_whois):
        # A privacy-shielded record simply omits most of this.
        fake_whois({})

        info = get_domain_info("example-site.test")

        assert info["registrant_org"] is None
        assert info["registrant_name"] is None
        assert info["registrar"] is None

    def test_creation_date_is_stringified(self, fake_whois):
        from datetime import datetime

        fake_whois({"creation_date": datetime(2015, 1, 1, 12, 30)})

        info = get_domain_info("example-site.test")

        assert info["creation_date"] == "2015-01-01 12:30:00"

    def test_lookup_failure_is_reported_not_raised(self, fake_whois):
        fake_whois(error=Exception("no whois server"))

        info = get_domain_info("https://example-site.test/jane")

        assert info == {"domain": "example-site.test", "error": "no whois server"}


class TestGetHostingInfo:
    RDAP = {
        "network": {"name": "EXAMPLE-HOSTING-NET"},
        "asn": "64500",
        "asn_description": "EXAMPLE-HOSTING, US",
        "objects": {
            "ABUSE-EX": {
                "roles": ["abuse"],
                "contact": {"email": [{"value": "abuse@example-hosting.test"}]},
            }
        },
    }

    def test_maps_hosting_fields(self, fake_rdap):
        fake_rdap(ip="203.0.113.10", rdap=self.RDAP)

        info = get_hosting_info("https://example-site.test/jane")

        assert info == {
            "domain": "example-site.test",
            "ip": "203.0.113.10",
            "hosting_org": "EXAMPLE-HOSTING-NET",
            "asn": "64500",
            "asn_description": "EXAMPLE-HOSTING, US",
            "abuse_email": "abuse@example-hosting.test",
        }

    def test_resolves_the_host_then_looks_up_the_ip(self, fake_rdap):
        calls = fake_rdap(ip="203.0.113.10", rdap=self.RDAP)

        get_hosting_info("https://example-site.test/jane-public")

        assert calls["dns"] == ["example-site.test"]
        assert calls["rdap"] == ["203.0.113.10"]

    def test_falls_back_to_asn_description_for_hosting_org(self, fake_rdap):
        fake_rdap(rdap={"asn_description": "EXAMPLE-HOSTING, US", "network": {}})

        info = get_hosting_info("example-site.test")

        assert info["hosting_org"] == "EXAMPLE-HOSTING, US"

    def test_dns_failure_is_reported_not_raised(self, fake_rdap):
        fake_rdap(dns_error=OSError("Name or service not known"))

        info = get_hosting_info("https://example-site.test/jane")

        assert info["domain"] == "example-site.test"
        assert "DNS resolution failed" in info["error"]
        assert "ip" not in info

    def test_rdap_failure_still_reports_the_resolved_ip(self, fake_rdap):
        fake_rdap(ip="203.0.113.10", rdap_error=Exception("RDAP unavailable"))

        info = get_hosting_info("example-site.test")

        assert info == {
            "domain": "example-site.test",
            "ip": "203.0.113.10",
            "error": "RDAP unavailable",
        }


class TestExtractAbuseEmail:
    def test_finds_the_abuse_contact(self):
        result = {
            "objects": {
                "REG": {"roles": ["registrant"], "contact": {"email": [{"value": "a@x.test"}]}},
                "AB": {"roles": ["abuse"], "contact": {"email": [{"value": "abuse@x.test"}]}},
            }
        }

        assert _extract_abuse_email(result) == "abuse@x.test"

    def test_returns_blank_when_no_abuse_role_exists(self):
        result = {"objects": {"REG": {"roles": ["registrant"], "contact": {}}}}

        assert _extract_abuse_email(result) == ""

    @pytest.mark.parametrize(
        "result",
        [
            {},
            {"objects": {}},
            {"objects": {"AB": {"roles": None}}},
            {"objects": {"AB": {"roles": ["abuse"], "contact": None}}},
            {"objects": {"AB": {"roles": ["abuse"], "contact": {"email": None}}}},
            {"objects": {"AB": {"roles": ["abuse"], "contact": {"email": []}}}},
        ],
    )
    def test_handles_missing_or_null_structure(self, result):
        assert _extract_abuse_email(result) == ""

    def test_takes_the_first_abuse_address(self):
        result = {
            "objects": {
                "AB": {
                    "roles": ["abuse"],
                    "contact": {
                        "email": [
                            {"value": "abuse@x.test"},
                            {"value": "second@x.test"},
                        ]
                    },
                }
            }
        }

        assert _extract_abuse_email(result) == "abuse@x.test"


class TestFullLookup:
    def test_combines_both_lookups(self, fake_whois, fake_rdap):
        fake_whois({"org": "Example Holdings LLC"})
        fake_rdap(ip="203.0.113.10", rdap={"network": {"name": "EXAMPLE-NET"}})

        result = full_lookup("https://example-site.test/jane")

        assert result["domain_info"]["registrant_org"] == "Example Holdings LLC"
        assert result["hosting_info"]["hosting_org"] == "EXAMPLE-NET"

    def test_one_side_failing_does_not_lose_the_other(self, fake_whois, fake_rdap):
        fake_whois(error=Exception("no whois server"))
        fake_rdap(ip="203.0.113.10", rdap={"network": {"name": "EXAMPLE-NET"}})

        result = full_lookup("https://example-site.test/jane")

        assert result["domain_info"]["error"] == "no whois server"
        assert result["hosting_info"]["hosting_org"] == "EXAMPLE-NET"

    def test_has_both_sections_even_when_both_fail(self, fake_whois, fake_rdap):
        fake_whois(error=Exception("boom"))
        fake_rdap(dns_error=OSError("nope"))

        result = full_lookup("example-site.test")

        assert set(result) == {"domain_info", "hosting_info"}
        assert "error" in result["domain_info"]
        assert "error" in result["hosting_info"]
