"""Look up domain registrant and hosting provider info for a target URL.

This is pre-litigation research (who to name/serve, who to contact) for
handing off to an attorney once a request has gone past its 10-day
deadline under Fla. Stat. § 901.43 -- it does not send anything or make
any legal claim itself.
"""
import socket
from urllib.parse import urlparse

import whois
from ipwhois import IPWhois


def _domain_from_url(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"http://{url}")
    return parsed.netloc or parsed.path


def get_domain_info(url: str) -> dict:
    """Registrant/registrar info from WHOIS. Many domains use privacy
    proxies, in which case registrant fields will show the proxy service
    rather than the underlying owner -- that's the WHOIS record's own
    limitation, not something this function can see past."""
    domain = _domain_from_url(url)
    try:
        w = whois.whois(domain)
    except Exception as e:
        return {"domain": domain, "error": str(e)}

    return {
        "domain": domain,
        "registrant_org": _first(w.get("org")),
        "registrant_name": _first(w.get("name")),
        "registrant_email": _first(w.get("emails")),
        "registrar": _first(w.get("registrar")),
        "creation_date": _stringify(_first(w.get("creation_date"))),
        "country": _first(w.get("country")),
    }


def get_hosting_info(url: str) -> dict:
    """Resolve the domain to an IP and look up the hosting network/ASN via
    IP WHOIS -- this identifies the hosting provider, which matters
    separately from the domain registrant for notice/safe-harbor purposes
    (the host, not just the site owner, can be put on notice)."""
    domain = _domain_from_url(url)
    try:
        ip = socket.gethostbyname(domain)
    except Exception as e:
        return {"domain": domain, "error": f"DNS resolution failed: {e}"}

    try:
        ipw = IPWhois(ip)
        result = ipw.lookup_rdap()
    except Exception as e:
        return {"domain": domain, "ip": ip, "error": str(e)}

    network = result.get("network", {})
    return {
        "domain": domain,
        "ip": ip,
        "hosting_org": network.get("name") or result.get("asn_description"),
        "asn": result.get("asn"),
        "asn_description": result.get("asn_description"),
        "abuse_email": _extract_abuse_email(result),
    }


def _extract_abuse_email(rdap_result: dict) -> str:
    for entity in rdap_result.get("objects", {}).values():
        roles = entity.get("roles") or []
        if "abuse" in roles:
            contact = entity.get("contact") or {}
            emails = contact.get("email") or []
            if emails:
                return emails[0].get("value", "")
    return ""


def _first(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _stringify(value):
    return str(value) if value is not None else None


def full_lookup(url: str) -> dict:
    return {
        "domain_info": get_domain_info(url),
        "hosting_info": get_hosting_info(url),
    }
