"""Generate a booking-photo removal request under a given state's statute.

Written in the client's own first-person voice, asserting the client's own
statutory right -- not as a representative acting on the client's behalf,
and not asserting ownership of the photograph itself.
"""
from datetime import date, timedelta

from statutes import get_statute

TEMPLATE_WITH_DEADLINE = """\
Subject: Request for Removal of Booking Photograph Pursuant to {citation}

To Whom It May Concern:

My name is {client_name}. I am writing to request the removal of my arrest
booking photograph, which currently appears on your website at the following
URL:

{target_url}

Under {citation}, a person or entity that publishes an arrest booking
photograph may not charge a fee to remove it, and must remove it within
{deadline_days} calendar days of receiving a written request from the person
depicted. This letter constitutes that written request.

Booking date: {booking_date}
Arresting agency: {arresting_agency}

Please confirm removal in writing. If the photograph is not removed within
{deadline_days} calendar days of the date of this request, I am entitled
under {citation} to pursue: {penalty_description}.
{operator_note}
Sincerely,
{client_name}
{client_contact}

Date of this request: {request_date}
Deadline for removal: {deadline}
"""

TEMPLATE_NO_DEADLINE = """\
Subject: Request for Removal of Booking Photograph Pursuant to {citation}

To Whom It May Concern:

My name is {client_name}. I am writing to request the removal of my arrest
booking photograph, which currently appears on your website at the following
URL:

{target_url}

Under {citation}, a person or entity that publishes an arrest booking
photograph may not charge a fee to remove, correct, or refrain from
publishing it. This letter constitutes my written request for removal.

Booking date: {booking_date}
Arresting agency: {arresting_agency}

Please confirm removal in writing. [NOTE TO OPERATOR: this state's specific
removal deadline and noncompliance penalty were not confirmed for this tool
-- verify current statutory text for {state_name} before sending, and add
the specific deadline/penalty language before relying on this letter.]

Sincerely,
{client_name}
{client_contact}

Date of this request: {request_date}
"""

# Used with TEMPLATE_WITH_DEADLINE for states whose entry carries a deadline
# but is not fully confirmed -- the deadline/penalty figures still get stated,
# but not as though they'd been verified.
UNCONFIRMED_STATUTE_NOTE = """
[NOTE TO OPERATOR: {state_name}'s entry is marked "{confidence}" -- its
deadline and penalty figures were not confirmed for this tool. Verify current
statutory text for {state_name} before sending, and correct the figures above
if they are wrong.]
"""


def generate_letter(
    client_name: str,
    client_contact: str,
    target_url: str,
    state: str = "FL",
    booking_date: str = "",
    arresting_agency: str = "",
    request_date: date | None = None,
) -> str:
    statute = get_statute(state)
    request_date = request_date or date.today()

    common = dict(
        citation=statute["citation"],
        client_name=client_name,
        client_contact=client_contact,
        target_url=target_url,
        booking_date=booking_date or "N/A",
        arresting_agency=arresting_agency or "N/A",
        request_date=request_date.isoformat(),
        state_name=statute["name"],
    )

    if statute["removal_deadline_days"] is not None:
        deadline = request_date + timedelta(days=statute["removal_deadline_days"])
        operator_note = ""
        if statute["confidence"] != "verified":
            operator_note = UNCONFIRMED_STATUTE_NOTE.format(
                state_name=statute["name"], confidence=statute["confidence"]
            )
        return TEMPLATE_WITH_DEADLINE.format(
            **common,
            deadline_days=statute["removal_deadline_days"],
            penalty_description=statute["penalty_description"] or "the remedies available under this statute",
            deadline=deadline.isoformat(),
            operator_note=operator_note,
        )

    return TEMPLATE_NO_DEADLINE.format(**common)
