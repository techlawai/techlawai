#!/usr/bin/env python3
"""CLI for Google review removal: import, screen, draft, report, appeal, reply, track."""
import argparse
import json

from authorization import generate_authorization_form, validate_authorization_date
from classify import Match, classify_reviews
from policies import LEGAL_ROUTE_NOTE, NOT_GROUNDS, POLICIES, get_policy
from responses import appeal_text, has_placeholders, owner_reply, report_note
from reviews import Review, load_reviews
import review_tracker as tracker


def _tracker(args):
    return tracker.tracker_path(args.tracker_dir, args.client)


def _checked_authorization(args):
    try:
        return validate_authorization_date(args.authorization_date)
    except ValueError as e:
        raise SystemExit(
            f"Refusing to run: {e}\n--authorization-date must be the date the client "
            f"signed the authorization form (see `authorization-form`)."
        )


def _classified_rows(path):
    """Tracker rows paired with a fresh classification of each row's text."""
    rows = tracker.load(path)
    reviews = [
        Review(reviewer=r["Reviewer"], rating=int(r["Rating"]) if r["Rating"] else None,
               text=r["Review Text"], date=r["Review Date"], url=r["Review URL"],
               review_id=r["Review ID"], api_name=r["API Name"])
        for r in rows
    ]
    classifications = classify_reviews(reviews)
    for row, c in zip(rows, classifications):
        # A person's choice of policy (from `confirm --policy`) goes first.
        # It may be one the keyword screen missed, e.g. a competitor the
        # client recognises by name.
        chosen = [p for p in row["Policies"].split(", ") if p]
        if row["Status"] in tracker.DECIDED and chosen:
            if chosen[0] not in c.policies:
                c.matches.insert(0, Match(chosen[0], "identified by the client (see tracker notes)"))
            c.matches.sort(key=lambda m: m.policy != chosen[0])
    return rows, classifications


def _ask(prompt):
    return input(f"{prompt} [y/N] ").strip().lower() == "y"


def _print_table(rows):
    for row in rows:
        print(f"{row['Review ID']:<16} {row['Rating'] or '-':>2}* {row['Status']:<20} "
              f"{row['Policies'] or '-':<35} {row['Reviewer']}")
    print(json.dumps(tracker.summary(rows)))


def cmd_import(args):
    reviews = load_reviews(args.file)
    rows = tracker.upsert_classifications(_tracker(args), classify_reviews(reviews))
    print(f"Imported {len(reviews)} review(s) into {_tracker(args)}")
    _print_table(rows)


def cmd_locations(args):
    import gbp_api

    session = gbp_api.authorized_session(args.client_secret, args.token)
    print(json.dumps(gbp_api.list_locations(session), indent=2))


def cmd_fetch(args):
    import gbp_api

    session = gbp_api.authorized_session(args.client_secret, args.token)
    reviews = gbp_api.fetch_reviews(session, args.account, args.location)
    rows = tracker.upsert_classifications(_tracker(args), classify_reviews(reviews))
    print(f"Fetched {len(reviews)} review(s) into {_tracker(args)}")
    _print_table(rows)


def cmd_draft(args):
    rows, classifications = _classified_rows(_tracker(args))
    out = [f"# Review drafts: {args.business}\n"]
    for row, c in zip(rows, classifications):
        if c.recommendation == "none":
            continue
        out.append(f"## {row['Reviewer']} ({row['Rating'] or '?'}-star, {row['Review Date'] or 'no date'}) "
                   f"`{row['Review ID']}`\n")
        out.append(f"Status: {row['Status']}\n\n> " + row["Review Text"].replace("\n", "\n> ") + "\n")
        if c.is_candidate:
            policy = get_policy(c.primary_policy)
            out.append(f"**Recommendation: report** as *{policy['name']}* "
                       f"(report-form reason: \"{policy['report_reason']}\"). "
                       f"Confirm it applies, then `cli.py confirm --review-id {row['Review ID']}`.\n")
            out.append("### Report note\n```\n" + report_note(c, args.business) + "```\n")
            out.append("### Appeal (use only if Google keeps it)\n```\n"
                       + appeal_text(c, args.business, args.signer) + "```\n")
        else:
            out.append("**Recommendation: reply only.** No Google policy matched; a report "
                       "would be declined and spend the appeal.\n")
        out.append("### Owner reply\n```\n" + owner_reply(c, args.contact, args.signer) + "\n```\n")
    text = "\n".join(out)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote drafts to {args.out}")
    else:
        print(text)


def cmd_confirm(args):
    path = _tracker(args)
    rows, classifications = _classified_rows(path)
    for row, c in zip(rows, classifications):
        if row["Review ID"] != args.review_id:
            continue
        if not c.is_candidate and not args.policy:
            raise SystemExit(f"{args.review_id} matched no Google policy. Reply to it instead, or, "
                             f"if the client knows a policy applies (e.g. the reviewer is a "
                             f"competitor), pass --policy and say how it's known with --note.")
        policies = c.policies
        if args.policy:
            get_policy(args.policy)  # rejects unknown keys
            policies = [args.policy] + [p for p in policies if p != args.policy]
        row["Policies"] = ", ".join(policies)
        tracker.save(path, rows)
        note = f"confirmed as {get_policy(policies[0])['name']}"
        tracker.set_status(path, args.review_id, "Confirmed",
                           note=f"{note}: {args.note}" if args.note else note)
        print(f"{args.review_id} confirmed for report as {get_policy(policies[0])['name']}.")
        return
    raise SystemExit(f"No review {args.review_id!r} in {path}.")


def _launch_ui(args):
    import rmt_submit

    return rmt_submit.PlaywrightUI.launch(args.profile_dir)


def cmd_rmt_login(args):
    import rmt_submit

    ui = _launch_ui(args)
    ui.goto(rmt_submit.RMT_URL)
    input("Sign in to the client's Google account in the browser window, "
          "then press Enter here to save the session.")
    ui.shutdown()


def cmd_report(args):
    import rmt_submit

    _checked_authorization(args)
    path = _tracker(args)
    rows, classifications = _classified_rows(path)
    queue = [(r, c) for r, c in zip(rows, classifications) if r["Status"] == "Confirmed"]
    if not queue:
        raise SystemExit("Nothing to report: no reviews are Confirmed. Run `confirm` first.")
    confirm = (lambda summary: True) if args.auto_submit else _ask
    ui = _launch_ui(args)
    try:
        for i, (row, c) in enumerate(queue):
            reason = get_policy(c.primary_policy)["report_reason"]
            try:
                rmt_submit.report_review(ui, args.business, row["Reviewer"], reason, confirm)
            except rmt_submit.Declined:
                print(f"Skipped {row['Review ID']}.")
                continue
            except rmt_submit.StepNotFound as e:
                raise SystemExit(f"Stopped at {row['Review ID']}: {e}")
            tracker.set_status(path, row["Review ID"], "Decision pending",
                               note=f'reported as "{reason}"')
            print(f"Reported {row['Review ID']} ({row['Reviewer']}).")
            if i < len(queue) - 1:
                rmt_submit.pace()
    finally:
        ui.shutdown()


def cmd_appeal(args):
    import rmt_submit

    _checked_authorization(args)
    path = _tracker(args)
    rows, classifications = _classified_rows(path)
    queue = [(r, c) for r, c in zip(rows, classifications)
             if r["Status"] == "No policy violation" and c.is_candidate]
    if args.review_id:
        queue = [(r, c) for r, c in queue if r["Review ID"] in args.review_id]
    if not queue:
        raise SystemExit('Nothing to appeal: no candidate reviews are at "No policy violation".')
    queue = queue[:rmt_submit.APPEAL_BATCH_MAX]

    if args.appeal_file:
        with open(args.appeal_file, encoding="utf-8") as f:
            body = f.read()
    else:
        body = "\n\n".join(appeal_text(c, args.business, args.signer) for _, c in queue)
    if has_placeholders(body):
        raise SystemExit(
            "Refusing to appeal: the appeal still has [[FILL: ...]] items -- facts only the "
            "client can confirm. Run `draft`, fill them in or delete them, save the text, and "
            "pass it with --appeal-file."
        )
    confirm = (lambda summary: True) if args.auto_submit else _ask
    ui = _launch_ui(args)
    try:
        rmt_submit.submit_appeal(ui, args.business, [r["Reviewer"] for r, _ in queue], body, confirm)
    except rmt_submit.Declined:
        raise SystemExit("Appeal not submitted.")
    except rmt_submit.StepNotFound as e:
        raise SystemExit(f"Stopped: {e}")
    finally:
        ui.shutdown()
    for row, _ in queue:
        tracker.set_status(path, row["Review ID"], "Escalated", note="appeal submitted")
    print(f"Appealed {len(queue)} review(s). Google's answer comes by email; record it with "
          f"`status --set <id> Removed` or `status --set <id> \"Remains live\"`.")


def cmd_reply(args):
    import gbp_api

    _checked_authorization(args)
    path = _tracker(args)
    rows, classifications = _classified_rows(path)
    queue = [(r, c) for r, c in zip(rows, classifications)
             if c.is_negative and r["API Name"] and not r["Replied Date"]
             and r["Status"] != "Removed"]
    if args.review_id:
        queue = [(r, c) for r, c in queue if r["Review ID"] in args.review_id]
    if not queue:
        raise SystemExit("Nothing to reply to. (Replies need reviews pulled with `fetch`, "
                         "which carries the API id a reply is posted to.)")
    session = gbp_api.authorized_session(args.client_secret, args.token)
    for row, c in queue:
        text = owner_reply(c, args.contact, args.signer)
        print(f"\n--- {row['Reviewer']} ({row['Rating']}-star) ---\n{row['Review Text']}\n\nReply:\n{text}")
        if not args.yes and not _ask("Post this reply publicly?"):
            continue
        gbp_api.post_reply(session, row["API Name"], text)
        tracker.mark_replied(path, row["Review ID"])
        print("Posted.")


def cmd_status(args):
    path = _tracker(args)
    if args.set:
        review_id, status = args.set
        tracker.set_status(path, review_id, status, note=args.note)
    _print_table(tracker.load(path))


def cmd_list_policies(args):
    print(json.dumps({"policies": {k: {f: v for f, v in p.items() if f != "signals"}
                                   for k, p in POLICIES.items()},
                      "not_grounds": NOT_GROUNDS,
                      "legal_route": LEGAL_ROUTE_NOTE}, indent=2))


def cmd_authorization_form(args):
    print(generate_authorization_form(args.client, args.business, args.operator))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, func, help_, client=True, business=False):
        p = sub.add_parser(name, help=help_)
        if client:
            p.add_argument("--client", required=True, help="Client name (one tracker per client)")
            p.add_argument("--tracker-dir", default="trackers")
        if business:
            p.add_argument("--business", required=True,
                           help="Business name exactly as Google shows it in the Reviews Management Tool")
        p.set_defaults(func=func)
        return p

    def add_api(p):
        p.add_argument("--client-secret", default="client_secret.json")
        p.add_argument("--token", default="token.json")

    def add_browser(p):
        p.add_argument("--profile-dir", required=True,
                       help="The client's Chrome profile folder for this tool (see rmt-login)")
        p.add_argument("--authorization-date", required=True,
                       help="Date (YYYY-MM-DD) the client signed the authorization form")
        p.add_argument("--auto-submit", action="store_true",
                       help="Don't ask before each final Submit")

    p = add("import", cmd_import, "Load reviews from a CSV or pasted-text file and screen them")
    p.add_argument("--file", required=True)

    p = add("locations", cmd_locations, "List Business Profile locations the signed-in account manages",
            client=False)
    add_api(p)

    p = add("fetch", cmd_fetch, "Pull reviews from the Business Profile API and screen them")
    p.add_argument("--account", required=True, help="accounts/... (see locations)")
    p.add_argument("--location", required=True, help="locations/... (see locations)")
    add_api(p)

    p = add("draft", cmd_draft, "Write report notes, appeals and owner replies", business=True)
    p.add_argument("--contact", required=True, help="How reviewers should reach the business")
    p.add_argument("--signer", required=True, help="Name/title replies and appeals are signed with")
    p.add_argument("--out", default="")

    p = add("confirm", cmd_confirm, "Confirm a candidate review really breaks the policy")
    p.add_argument("--review-id", required=True)
    p.add_argument("--policy", default="", help="Policy key to report under (see list-policies)")
    p.add_argument("--note", default="", help="How the client knows, for a policy the screen didn't match")

    p = add("rmt-login", cmd_rmt_login, "Open the browser profile so the client can sign in once",
            client=False)
    p.add_argument("--profile-dir", required=True)

    p = add("report", cmd_report, "Report Confirmed reviews through the Reviews Management Tool",
            business=True)
    add_browser(p)

    p = add("appeal", cmd_appeal, "File Google's one-time appeal for declined reports", business=True)
    add_browser(p)
    p.add_argument("--signer", required=True)
    p.add_argument("--appeal-file", default="", help="Edited appeal text (required if drafts have [[FILL]] items)")
    p.add_argument("--review-id", action="append", default=[], help="Limit to these (repeatable)")

    p = add("reply", cmd_reply, "Post owner replies through the Business Profile API")
    add_api(p)
    p.add_argument("--contact", required=True)
    p.add_argument("--signer", required=True)
    p.add_argument("--authorization-date", required=True)
    p.add_argument("--review-id", action="append", default=[])
    p.add_argument("--yes", action="store_true", help="Post without asking per reply")

    p = add("status", cmd_status, "Show (or set) each review's status")
    p.add_argument("--set", nargs=2, metavar=("REVIEW_ID", "STATUS"),
                   help=f"Statuses: {', '.join(tracker.STATUSES)}")
    p.add_argument("--note", default="")

    add("list-policies", cmd_list_policies, "Show Google's policy categories as this tool uses them",
        client=False)

    p = add("authorization-form", cmd_authorization_form, "Print the client authorization form",
            business=True)
    p.add_argument("--operator", required=True, help="Who will act on the profile")

    args = parser.parse_args()
    try:
        args.func(args)
    except (KeyError, ValueError) as e:
        raise SystemExit(str(e).strip("'\""))


if __name__ == "__main__":
    main()
