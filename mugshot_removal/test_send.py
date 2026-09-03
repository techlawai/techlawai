"""Tests for send.py -- turning a letter into an email and handing it to SMTP.

Nothing here opens a socket; see the fake_smtp fixture in conftest.py.
"""
from email import message_from_string
from email.header import decode_header, make_header

import send


def header(message, name):
    """Decode a header back to text; a non-ASCII subject arrives RFC 2047 encoded."""
    return str(make_header(decode_header(message[name])))

LETTER = """\
Subject: Request for Removal of Booking Photograph Pursuant to Fla. Stat. § 901.43

To Whom It May Concern:

My name is Jane Public.

Sincerely,
Jane Public
"""


def send_letter(letter=LETTER, **overrides):
    kwargs = dict(
        smtp_host="smtp.example.test",
        smtp_port=465,
        smtp_username="jane@example.com",
        smtp_password="app-password",
        client_email="jane@example.com",
        to_email="abuse@example-site.test",
        letter_body=letter,
    )
    kwargs.update(overrides)
    return send.send_removal_request(**kwargs)


class TestMessageConstruction:
    def test_subject_comes_from_the_letters_subject_line(self, fake_smtp):
        send_letter()

        _, _, raw = fake_smtp.instances[0].sent[0]
        message = message_from_string(raw)
        assert header(message, "Subject") == (
            "Request for Removal of Booking Photograph Pursuant to "
            "Fla. Stat. § 901.43"
        )

    def test_subject_line_is_not_repeated_in_the_body(self, fake_smtp):
        send_letter()

        _, _, raw = fake_smtp.instances[0].sent[0]
        body = message_from_string(raw).get_payload(decode=True).decode()
        assert not body.startswith("Subject:")
        assert "To Whom It May Concern:" in body

    def test_body_keeps_the_rest_of_the_letter(self, fake_smtp):
        send_letter()

        _, _, raw = fake_smtp.instances[0].sent[0]
        body = message_from_string(raw).get_payload(decode=True).decode()
        assert "My name is Jane Public." in body
        assert "Sincerely," in body

    def test_sent_as_the_client_not_a_third_party(self, fake_smtp):
        # Stated scope: the request goes out as the client's own, so the
        # client's address is both the From header and the envelope sender.
        send_letter()

        smtp = fake_smtp.instances[0]
        envelope_from, recipients, raw = smtp.sent[0]
        message = message_from_string(raw)

        assert message["From"] == "jane@example.com"
        assert message["To"] == "abuse@example-site.test"
        assert envelope_from == "jane@example.com"
        assert recipients == ["abuse@example-site.test"]

    def test_letter_without_a_subject_line_still_sends(self, fake_smtp):
        send_letter(letter="No subject here\n\nBody text.\n")

        _, _, raw = fake_smtp.instances[0].sent[0]
        message = message_from_string(raw)
        assert message["Subject"] == "No subject here"
        assert "Body text." in message.get_payload(decode=True).decode()


class TestSmtpUsage:
    def test_connects_to_the_given_host_and_port(self, fake_smtp):
        send_letter(smtp_host="smtp.gmail.com", smtp_port=587)

        smtp = fake_smtp.instances[0]
        assert (smtp.host, smtp.port) == ("smtp.gmail.com", 587)

    def test_authenticates_with_the_given_credentials(self, fake_smtp):
        send_letter()

        assert fake_smtp.instances[0].logins == [("jane@example.com", "app-password")]

    def test_username_may_differ_from_the_client_address(self, fake_smtp):
        send_letter(smtp_username="relay@example.com")

        smtp = fake_smtp.instances[0]
        assert smtp.logins == [("relay@example.com", "app-password")]
        # The message is still from the client, not the relay account.
        assert smtp.sent[0][0] == "jane@example.com"

    def test_connection_is_closed(self, fake_smtp):
        send_letter()

        smtp = fake_smtp.instances[0]
        assert smtp.entered is True
        assert smtp.exited is True

    def test_sends_exactly_one_message(self, fake_smtp):
        send_letter()

        assert len(fake_smtp.instances) == 1
        assert len(fake_smtp.instances[0].sent) == 1
