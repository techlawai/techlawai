#!/usr/bin/env python3
"""CLI for the § 901.43 mugshot removal workflow: search, draft, send, track."""
import argparse
import json

from draft import generate_letter
from search import find_mugshot_pages
from send import send_removal_request
from tracker import list_overdue, log_request, open_tracker


def cmd_search(args):
    results = find_mugshot_pages(args.client_name, args.api_key, args.cx, args.num_results)
    print(json.dumps(results, indent=2))


def cmd_draft(args):
    letter = generate_letter(
        client_name=args.client_name,
        client_contact=args.client_contact,
        target_url=args.target_url,
        booking_date=args.booking_date,
        arresting_agency=args.arresting_agency,
    )
    print(letter)


def cmd_send(args):
    letter = generate_letter(
        client_name=args.client_name,
        client_contact=args.client_email,
        target_url=args.target_url,
        booking_date=args.booking_date,
        arresting_agency=args.arresting_agency,
    )
    send_removal_request(
        smtp_host=args.smtp_host,
        smtp_port=args.smtp_port,
        smtp_username=args.smtp_username,
        smtp_password=args.smtp_password,
        client_email=args.client_email,
        to_email=args.to_email,
        letter_body=letter,
    )
    print(f"Sent to {args.to_email}")

    if args.sheet_id:
        ws = open_tracker(args.sheet_id, args.creds)
        log_request(ws, args.client_name, args.target_url, args.to_email)
        print("Logged to tracker sheet.")


def cmd_check_overdue(args):
    ws = open_tracker(args.sheet_id, args.creds)
    overdue = list_overdue(ws)
    print(json.dumps(overdue, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Find pages likely hosting a client's mugshot")
    p_search.add_argument("--client-name", required=True)
    p_search.add_argument("--api-key", required=True, help="Google Custom Search API key")
    p_search.add_argument("--cx", required=True, help="Custom Search Engine ID")
    p_search.add_argument("--num-results", type=int, default=20)
    p_search.set_defaults(func=cmd_search)

    p_draft = sub.add_parser("draft", help="Generate a removal request letter")
    p_draft.add_argument("--client-name", required=True)
    p_draft.add_argument("--client-contact", required=True)
    p_draft.add_argument("--target-url", required=True)
    p_draft.add_argument("--booking-date", default="")
    p_draft.add_argument("--arresting-agency", default="")
    p_draft.set_defaults(func=cmd_draft)

    p_send = sub.add_parser("send", help="Draft, send, and log a removal request")
    p_send.add_argument("--client-name", required=True)
    p_send.add_argument("--client-email", required=True)
    p_send.add_argument("--target-url", required=True)
    p_send.add_argument("--to-email", required=True, help="Site's contact/abuse email")
    p_send.add_argument("--booking-date", default="")
    p_send.add_argument("--arresting-agency", default="")
    p_send.add_argument("--smtp-host", required=True)
    p_send.add_argument("--smtp-port", type=int, default=465)
    p_send.add_argument("--smtp-username", required=True)
    p_send.add_argument("--smtp-password", required=True)
    p_send.add_argument("--sheet-id", default=None, help="Optional: log to tracker sheet")
    p_send.add_argument("--creds", default="service_account.json")
    p_send.set_defaults(func=cmd_send)

    p_overdue = sub.add_parser("check-overdue", help="List requests past their 10-day deadline")
    p_overdue.add_argument("--sheet-id", required=True)
    p_overdue.add_argument("--creds", default="service_account.json")
    p_overdue.set_defaults(func=cmd_check_overdue)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
