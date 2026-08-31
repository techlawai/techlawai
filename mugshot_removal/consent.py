"""Client authorization record: written permission for a removal request to
be sent from the client's own name and email address.

This is what makes a letter genuinely the client's own request rather than
someone else acting for them -- it needs to exist, in writing, before any
real letter goes out. generate_consent_form() gives the client something to
sign/return; the CLI's send command refuses to run without a recorded
consent date (see main.py).
"""
from datetime import date

CONSENT_FORM_TEMPLATE = """\
AUTHORIZATION TO SEND BOOKING PHOTOGRAPH REMOVAL REQUEST

I, {client_name}, authorize the sending of a written request for removal of
my arrest booking photograph, under {citation}, from the following email
address on my behalf and in my name:

  {client_email}

Target page to be addressed: {target_url}

I understand this request will be sent as my own first-person statutory
request, signed with my name, and that I am the person entitled to enforce
the rights described in it.

Signature: _______________________________
Printed name: {client_name}
Date: _______________________________
"""


def generate_consent_form(client_name: str, client_email: str, target_url: str, citation: str) -> str:
    return CONSENT_FORM_TEMPLATE.format(
        client_name=client_name,
        client_email=client_email,
        target_url=target_url,
        citation=citation,
    )


def validate_consent_date(consent_date_str: str) -> date:
    """Parse and sanity-check a claimed consent date. Raises ValueError if
    the string isn't a real date or is in the future."""
    parsed = date.fromisoformat(consent_date_str)
    if parsed > date.today():
        raise ValueError(f"Consent date {consent_date_str} is in the future.")
    return parsed
