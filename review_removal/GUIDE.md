# Google review disputes: step by step

How a review gets removed from a Google Business Profile, what to do at each
stage, and what to send. The `cli.py` commands that automate a step are
named beside it; everything here can also be done by hand.

Sources: Google's [Manage customer reviews](https://support.google.com/business/answer/4596773)
help page and [Prohibited & restricted content](https://support.google.com/contributionpolicy/answer/7400114)
policy (both checked 2026-10-25). Google changes both; recheck before relying on a detail.

## The one rule that decides everything

Google removes a review only when it breaks one of its content policies. It
does **not** remove reviews for being negative, unfair, inaccurate, or bad
for business, and its help page says so: *"Do not report a review just
because you disagree with it or dislike it."* Google also allows **one
appeal**. A report on a review that breaks no policy will be declined, and
spending the appeal on it leaves nothing for later.

So the first step is always sorting: report the reviews with a policy basis,
reply to the rest.

## Stage 0: before touching the client's profile

1. Get the client's signed authorization (`cli.py authorization-form`). Every
   report, appeal and reply is made from their account, in their business's name.
2. Get access to the profile: the client either adds you as a **Manager** in
   Business Profile (business.google.com → ⋮ → Business Profile settings →
   Managers), or signs in themselves on the machine running the tool.

## Stage 1: collect and sort the reviews

- `cli.py fetch` (API) or `cli.py import --file reviews.csv` (CSV/pasted).
- Each review comes out as **report** (matches a policy), **reply** (negative,
  no policy basis) or nothing.
- `cli.py draft` writes everything for each review: the report reason, the
  appeal text, and the owner reply.
- Read every *report* candidate. Confirm the policy really applies, then
  `cli.py confirm --review-id ...`. If the client knows something the text
  doesn't show (the reviewer is a competitor, an ex-employee, never a
  customer), confirm with `--policy` and `--note` saying how they know.

### Which policy fits

| What the review does | Google policy | Report reason to pick |
|---|---|---|
| Reviewer never did business with the client; paid or fake review | Fake engagement | Spam |
| Written by a competitor, current/ex-employee, or for an incentive | Rating manipulation | Conflict of interest |
| Threats, bullying, extortion ("remove it if you refund me") | Harassment | Bullying or harassment |
| Calls someone a thief, criminal, scammer without proof; personal attacks | Offensive content | Bullying or harassment |
| Slurs or demeaning talk about race, religion, disability, etc. | Hate speech | Discrimination or hate speech |
| Someone's phone, home address, email, health details | Personal information | Personal information |
| Swearing used to insult or emphasize | Obscenity & profanity | Profanity |
| Politics, social rants, or about a different business | Off-topic | Off topic |
| Links, promo codes, "follow me", contact details | Advertising & solicitation | Spam |
| Gibberish, or the same text posted more than once | Unclear / Repetitive content | Spam |

Not grounds, however strongly the client feels: a harsh opinion, a disputed
fact, a star-only review, a suspected (unproven) competitor.

## Stage 2: report

**Automated:** `cli.py report` (after `cli.py rmt-login` once). It opens the
client's own browser profile and clicks through the steps below, asking
before each final Submit unless `--auto-submit` is set, and paces reports 20
seconds apart.

**By hand, from Business Profile:**
1. Go to business.google.com and select **Read reviews**.
2. Next to the review, select the **Report** icon (flag / ⋮).
3. Pick the reason from the table above and select **Send report**.

**By hand, from the Reviews Management Tool**
(<https://support.google.com/business/workflow/9945796>):
1. Select **Confirm** (or **Switch account** if the email isn't the profile's).
2. Select the business, then **Continue**.
3. Select **Report a new review for removal**, then **Continue**.
4. Next to the review, select **Report**. A new tab opens.
5. Pick the reason and select **Submit**.

Record it: status **Decision pending**.

## Stage 3: check the status

Google says evaluation "typically takes several days". Check back in the
Reviews Management Tool: **Check the status of a review I reported previously
and appeal options** → **Continue**. It shows one of:

| Google shows | Meaning | Record with `cli.py status --set ID ...` |
|---|---|---|
| Decision pending | Not evaluated yet | `"Decision pending"` |
| Report reviewed - no policy violation | Google kept it; you may appeal once | `"No policy violation"` |
| Escalated - check your email for updates | Appeal is with a specialist | `Escalated` |
| (review gone from the profile) | Removed | `Removed` |

Suggested rhythm: check at 3 days, 7 days, then weekly.

## Stage 4: appeal (once)

Only for reviews at **Report reviewed - no policy violation**. Up to 10
reviews go in one appeal, so batch them.

**Automated:** `cli.py appeal`. It refuses while the appeal text still has
`[[FILL: ...]]` items, which are facts only the client can confirm (e.g. "we
have no record of this customer"). Fill or delete those in the draft, save
it, and pass it with `--appeal-file`.

**By hand:**
1. Reviews Management Tool → **Confirm** → business → **Continue**.
2. **Check the status of a review I reported previously and appeal options** → **Continue**.
3. At the bottom, select **Appeal eligible reviews**.
4. Tick the reviews (up to 10), then **Continue**.
5. Select **Submit an appeal**. A form opens in a new tab.
6. Paste the appeal text and select **Submit**.

What makes an appeal work: name Google's policy by its own name, quote the
exact words that break it, add verifiable facts (dates, records), and say
plainly that you aren't appealing because the review is negative. What
sinks one: arguing the review is unfair, threatening legal action, or
asserting facts the client can't back up.

### Appeal templates

`cli.py draft` fills these in per review. The shape:

**Policy visible in the text** (profanity, harassment, personal info, off-topic, links):
> We are appealing the decision on the review by "[name]" posted [date] on the
> Business Profile for [business]. This review violates Google Maps'
> [policy] policy (https://support.google.com/contributionpolicy/answer/7400114):
> "[quoted words]" -- [what the policy prohibits]. We are not asking for
> removal because the review is negative. We are asking because the content
> above falls under the policy named. Thank you for taking a second look.

**Not a real customer** (fake engagement) adds a fact from the client's records:
> ...We have no record of a customer by this name, or of any visit, booking
> or purchase on or around [date]. The reviewer states "[quote]".

**Conflict of interest** (rating manipulation) adds how the conflict is known:
> ...The reviewer is [a former employee who left on (date) / the owner of
> (competitor), (distance) away]. [Evidence: e.g. their profile links to that business.]

Afterwards Google emails its decision. Record **Removed** or **Remains live**.

## Stage 5: when Google says no for good

The review is **Remains live** and Google's own process is exhausted. What's left:

- **Reply.** Every negative review should have a calm, short owner reply,
  whatever happens to the report (`cli.py reply` posts them through the
  API). Readers judge the reply as much as the review.
- **Extortion.** If someone is posting reviews to demand money or refunds,
  that is its own Google process: <https://support.google.com/business/answer/16404809>.
- **Legal removal.** A review that is false and damaging (defamation) or
  breaks another law goes through Google's legal removal request, not the
  Reviews Management Tool. That's for an attorney to assess; this tool does
  not draft or file it.
- **Wrongly removed good reviews** (Google's spam filter): <https://support.google.com/business/gethelp>.

## What never to do

These get reviews kept, profiles penalised, or the client in legal trouble:

- Offer the reviewer anything (refund, discount, gift) to change or remove a
  review, or threaten them. The FTC's rule on consumer reviews (16 C.F.R.
  Part 465) bars suppressing reviews by threat or incentive.
- Mass-report, or report from several accounts. Google treats bursts and
  coordinated flags as abuse.
- Disclose anything about the customer in a reply, including confirming
  they were a customer. For health-care clients, that can be a HIPAA violation.
