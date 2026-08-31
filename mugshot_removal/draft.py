"""Generate a Fla. Stat. § 901.43 booking-photo removal request.

Written in the client's own first-person voice, asserting the client's own
statutory right -- not as a representative acting on the client's behalf, and
not asserting ownership of the photograph itself.
"""
from datetime import date, timedelta

TEMPLATE = """\
Subject: Request for Removal of Booking Photograph Pursuant to Fla. Stat. § 901.43

To Whom It May Concern:

My name is {client_name}. I am writing to request the removal of my arrest
booking photograph, which currently appears on your website at the following
URL:

{target_url}

Under Florida Statute § 901.43, a person or entity that publishes an arrest
booking photograph must remove it, without charge, within 10 calendar days
of receiving a written request from the person depicted, and may not
thereafter republish or redisseminate the photograph. This letter constitutes
that written request.

Booking date: {booking_date}
Arresting agency: {arresting_agency}

Please confirm removal in writing. If the photograph is not removed within
10 calendar days of the date of this request, I am entitled under Fla. Stat.
§ 901.43 to seek injunctive relief, a civil penalty of up to $1,000 per day
of continued noncompliance, and my reasonable attorney fees and costs.

Sincerely,
{client_name}
{client_contact}

Date of this request: {request_date}
Deadline for removal: {deadline}
"""


def generate_letter(
    client_name: str,
    client_contact: str,
    target_url: str,
    booking_date: str = "",
    arresting_agency: str = "",
    request_date: date | None = None,
) -> str:
    request_date = request_date or date.today()
    deadline = request_date + timedelta(days=10)
    return TEMPLATE.format(
        client_name=client_name,
        client_contact=client_contact,
        target_url=target_url,
        booking_date=booking_date or "N/A",
        arresting_agency=arresting_agency or "N/A",
        request_date=request_date.isoformat(),
        deadline=deadline.isoformat(),
    )
