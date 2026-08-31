"""Send a removal request by email, from the client's own email account.

The message is sent as the client (From: the client's address), not as a
third party representing them -- consistent with the letter being the
client's own first-person statutory request.
"""
import smtplib
from email.mime.text import MIMEText


def send_removal_request(
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    client_email: str,
    to_email: str,
    letter_body: str,
) -> None:
    subject, _, body = letter_body.partition("\n\n")
    subject = subject.replace("Subject: ", "", 1)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = client_email
    msg["To"] = to_email

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(smtp_username, smtp_password)
        server.sendmail(client_email, [to_email], msg.as_string())
