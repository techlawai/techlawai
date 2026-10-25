"""Client authorization to act on their Google Business Profile.

Reporting, appealing and replying all happen from the client's Google
account, or one they added as a Manager, under their business's name. That needs their written go-ahead on
file first; the cli's report, appeal and reply commands refuse to run
without the date they signed it.
"""
from datetime import date

AUTHORIZATION_FORM_TEMPLATE = """\
AUTHORIZATION TO MANAGE GOOGLE REVIEWS

I, {client_name}, authorize {operator} to act on the Google Business Profile
for {business_name}, using my own Google account or an account of theirs
that I have added as a Manager of the profile, to:

  1. Report reviews to Google that appear to violate Google's published
     review policies, and check the status of those reports;
  2. File Google's one-time appeal for reported reviews Google declined to
     remove; and
  3. Post public owner replies to reviews, in the business's name.

I understand that:
  - Google decides whether any review is removed, and only removes reviews
    that violate its policies -- not reviews that are merely negative.
  - Nothing will be offered to any reviewer, and no reviewer will be
    threatened, to have a review changed or removed.
  - Any statement of fact in an appeal (for example, that the business has
    no record of a reviewer) will be one I have confirmed is true.

Signature: _______________________________
Printed name: {client_name}
Date: _______________________________
"""


def generate_authorization_form(client_name: str, business_name: str, operator: str) -> str:
    return AUTHORIZATION_FORM_TEMPLATE.format(
        client_name=client_name, business_name=business_name, operator=operator,
    )


def validate_authorization_date(date_str: str) -> date:
    """Raises ValueError if the string isn't a real date or is in the future."""
    parsed = date.fromisoformat(date_str)
    if parsed > date.today():
        raise ValueError(f"Authorization date {date_str} is in the future.")
    return parsed
