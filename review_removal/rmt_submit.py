"""Drive Google's Reviews Management Tool in the client's own signed-in browser
to report reviews and file the one-time appeal.

Google offers no API for either (gbp_api.py covers what the API does), so
this clicks through the same pages a person would, following Google's
published steps (https://support.google.com/business/answer/4596773):

  Report:  RMT -> Confirm -> pick business -> Continue -> "Report a new review
           for removal" -> Continue -> Report (next to the review) -> reason
           -> Submit
  Appeal:  RMT -> Confirm -> pick business -> Continue -> "Check the status of
           a review I reported previously and appeal options" -> Continue ->
           "Appeal eligible reviews" -> tick up to 10 -> Continue -> "Submit
           an appeal" -> fill the form -> Submit

What it will not do:
- Sign in. The browser profile is the client's own; they sign in to it by
  hand once (`python cli.py rmt-login`). No password passes through here.
- Get past a CAPTCHA, "unusual traffic" page, or sign-in challenge. It stops
  and waits for a person to clear it in the open window.
- Guess. Google's labels change; when one in LABELS is not on the page the
  run stops with the label it was looking for, so LABELS can be corrected.
- Go fast. Reports are paced (PACE_SECONDS) -- bursts of reports from one
  account are what Google's abuse systems look for.

LABELS were written from Google's help page, not tested against the live
tool. The first real run should be watched with confirm prompts on.
"""
import time

RMT_URL = "https://support.google.com/business/workflow/9945796"
APPEAL_BATCH_MAX = 10
PACE_SECONDS = 20

LABELS = {
    "confirm_account": "Confirm",
    "continue": "Continue",
    "report_new": "Report a new review for removal",
    "check_status": "Check the status of a review I reported previously and appeal options",
    "report": "Report",
    "submit": "Submit",
    "appeal_eligible": "Appeal eligible reviews",
    "submit_appeal": "Submit an appeal",
}

BLOCK_MARKERS = ["unusual traffic", "recaptcha", "verify it's you", "confirm it's you"]


class StepNotFound(RuntimeError):
    """A label we expected is not on the page -- Google changed the UI, or
    the page is not the one we think it is."""


class Declined(RuntimeError):
    """The person at the keyboard said no at the final Submit."""


def _check_unblocked(ui, wait_for_human):
    while ui.is_blocked():
        wait_for_human(
            "Google is showing a sign-in, CAPTCHA, or unusual-traffic page in the "
            "browser window. Clear it there by hand, then press Enter to continue."
        )


def _open_business(ui, business_name, wait_for_human):
    ui.goto(RMT_URL)
    _check_unblocked(ui, wait_for_human)
    ui.click(LABELS["confirm_account"])
    ui.click(business_name)
    ui.click(LABELS["continue"])


def report_review(ui, business_name: str, reviewer: str, reason: str,
                  confirm, wait_for_human=input) -> None:
    """Report one review. `confirm(summary) -> bool` is asked right before
    the final Submit; returning False aborts without submitting."""
    _open_business(ui, business_name, wait_for_human)
    ui.click(LABELS["report_new"])
    ui.click(LABELS["continue"])
    _check_unblocked(ui, wait_for_human)
    form = ui.click_in_row(reviewer, LABELS["report"], opens_tab=True)
    _check_unblocked(form, wait_for_human)
    form.choose(reason)
    if not confirm(f'Report review by "{reviewer}" on {business_name} as "{reason}"?'):
        form.close()
        raise Declined(reviewer)
    form.click(LABELS["submit"])
    form.close()


def submit_appeal(ui, business_name: str, reviewers: list[str], appeal_body: str,
                  confirm, wait_for_human=input) -> None:
    """File the one-time appeal for up to APPEAL_BATCH_MAX reviews."""
    if not reviewers:
        raise ValueError("No reviews to appeal.")
    if len(reviewers) > APPEAL_BATCH_MAX:
        raise ValueError(f"Google takes at most {APPEAL_BATCH_MAX} reviews per appeal; got {len(reviewers)}.")
    _open_business(ui, business_name, wait_for_human)
    ui.click(LABELS["check_status"])
    ui.click(LABELS["continue"])
    _check_unblocked(ui, wait_for_human)
    ui.click(LABELS["appeal_eligible"])
    for reviewer in reviewers:
        ui.tick_row(reviewer)
    ui.click(LABELS["continue"])
    form = ui.click(LABELS["submit_appeal"], opens_tab=True)
    _check_unblocked(form, wait_for_human)
    form.fill_text(appeal_body)
    if not confirm(f"Submit Google's one-time appeal for {len(reviewers)} review(s) on {business_name}? "
                   f"Reviews: {', '.join(reviewers)}"):
        form.close()
        raise Declined(", ".join(reviewers))
    form.click(LABELS["submit"])
    form.close()


def pace(seconds: float = PACE_SECONDS):
    time.sleep(seconds)


class PlaywrightUI:
    """The real browser, via Playwright, on a persistent profile directory.

    Every lookup is by visible text/role so it survives Google's markup
    churn better than CSS selectors -- but it is still a guess at the live
    page until someone has watched it run.
    """

    TIMEOUT_MS = 15000

    def __init__(self, page):
        self.page = page

    @classmethod
    def launch(cls, profile_dir: str):
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        context = pw.chromium.launch_persistent_context(profile_dir, headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        ui = cls(page)
        ui._pw, ui._context = pw, context
        return ui

    def shutdown(self):
        self._context.close()
        self._pw.stop()

    def goto(self, url):
        self.page.goto(url)

    def is_blocked(self) -> bool:
        if "accounts.google.com" in self.page.url:
            return True
        body = self.page.inner_text("body").lower()
        return any(marker in body for marker in BLOCK_MARKERS)

    def _find(self, label, scope=None):
        scope = scope or self.page
        for locator in (
            scope.get_by_role("button", name=label, exact=True),
            scope.get_by_role("link", name=label, exact=True),
            scope.get_by_role("radio", name=label, exact=True),
            scope.get_by_text(label, exact=True),
        ):
            if locator.count():
                return locator.first
        raise StepNotFound(f'Could not find "{label}" on {self.page.url}. '
                           f"Update rmt_submit.LABELS if Google renamed it.")

    def _click(self, locator, opens_tab):
        if not opens_tab:
            locator.click(timeout=self.TIMEOUT_MS)
            self.page.wait_for_load_state()
            return self
        with self.page.context.expect_page(timeout=self.TIMEOUT_MS) as new:
            locator.click(timeout=self.TIMEOUT_MS)
        tab = new.value
        tab.wait_for_load_state()
        return PlaywrightUI(tab)

    def click(self, label, opens_tab=False):
        return self._click(self._find(label), opens_tab)

    def _row(self, text):
        rows = self.page.locator("li, tr, [role=listitem], [role=row]").filter(has_text=text)
        if not rows.count():
            raise StepNotFound(f'No review by "{text}" is listed on {self.page.url}.')
        if rows.count() > 1:
            raise StepNotFound(f'More than one review by "{text}" is listed; report it by hand.')
        return rows.first

    def click_in_row(self, row_text, label, opens_tab=False):
        return self._click(self._find(label, scope=self._row(row_text)), opens_tab)

    def tick_row(self, row_text):
        self._row(row_text).get_by_role("checkbox").first.check(timeout=self.TIMEOUT_MS)

    def choose(self, label):
        self._find(label).click(timeout=self.TIMEOUT_MS)

    def fill_text(self, text):
        boxes = self.page.locator("textarea")
        if not boxes.count():
            raise StepNotFound(f"No free-text box on the appeal form at {self.page.url}.")
        boxes.first.fill(text)

    def close(self):
        if self.page is not self.page.context.pages[0]:
            self.page.close()
