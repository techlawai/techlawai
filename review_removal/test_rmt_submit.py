"""Tests for rmt_submit.py's step sequences, against a recording fake UI."""
import pytest

import rmt_submit
from rmt_submit import LABELS


class FakeUI:
    def __init__(self, log=None, blocked=0, missing=()):
        self.log = log if log is not None else []
        self.blocked = blocked
        self.missing = set(missing)

    def _need(self, label):
        if label in self.missing:
            raise rmt_submit.StepNotFound(label)

    def goto(self, url):
        self.log.append(("goto", url))

    def is_blocked(self):
        if self.blocked:
            self.blocked -= 1
            return True
        return False

    def click(self, label, opens_tab=False):
        self._need(label)
        self.log.append(("click", label))
        return FakeUI(self.log, missing=self.missing) if opens_tab else self

    def click_in_row(self, row, label, opens_tab=False):
        self.log.append(("click_in_row", row, label))
        return FakeUI(self.log, missing=self.missing)

    def tick_row(self, row):
        self.log.append(("tick", row))

    def choose(self, label):
        self._need(label)
        self.log.append(("choose", label))

    def fill_text(self, text):
        self.log.append(("fill", text))

    def close(self):
        self.log.append(("close",))


def test_report_follows_googles_published_steps():
    ui = FakeUI()

    rmt_submit.report_review(ui, "Acme", "Ann", "Profanity", confirm=lambda s: True)

    assert ui.log == [
        ("goto", rmt_submit.RMT_URL),
        ("click", LABELS["confirm_account"]),
        ("click", "Acme"),
        ("click", LABELS["continue"]),
        ("click", LABELS["report_new"]),
        ("click", LABELS["continue"]),
        ("click_in_row", "Ann", LABELS["report"]),
        ("choose", "Profanity"),
        ("click", LABELS["submit"]),
        ("close",),
    ]


def test_declining_at_confirm_never_clicks_submit():
    ui = FakeUI()

    with pytest.raises(rmt_submit.Declined):
        rmt_submit.report_review(ui, "Acme", "Ann", "Profanity", confirm=lambda s: False)

    assert ("click", LABELS["submit"]) not in ui.log


def test_missing_reason_stops_instead_of_guessing():
    ui = FakeUI(missing={"Profanity"})

    with pytest.raises(rmt_submit.StepNotFound):
        rmt_submit.report_review(ui, "Acme", "Ann", "Profanity", confirm=lambda s: True)

    assert ("click", LABELS["submit"]) not in ui.log


def test_captcha_waits_for_a_person():
    ui = FakeUI(blocked=2)
    prompts = []

    rmt_submit.report_review(ui, "Acme", "Ann", "Spam", confirm=lambda s: True,
                             wait_for_human=prompts.append)

    assert len(prompts) == 2 and "CAPTCHA" in prompts[0]


def test_appeal_ticks_each_review_and_fills_form():
    ui = FakeUI()

    rmt_submit.submit_appeal(ui, "Acme", ["Ann", "Ben"], "Appeal body", confirm=lambda s: True)

    assert ("click", LABELS["check_status"]) in ui.log
    assert ("click", LABELS["appeal_eligible"]) in ui.log
    assert ("tick", "Ann") in ui.log and ("tick", "Ben") in ui.log
    assert ("fill", "Appeal body") in ui.log
    assert ui.log[-2] == ("click", LABELS["submit"])


def test_appeal_batch_limit():
    with pytest.raises(ValueError, match="at most 10"):
        rmt_submit.submit_appeal(FakeUI(), "Acme", [f"R{i}" for i in range(11)], "x",
                                 confirm=lambda s: True)
