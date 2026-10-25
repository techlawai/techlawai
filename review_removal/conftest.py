"""The review_removal tests need no fixtures beyond pytest's own: the
browser (rmt_submit.PlaywrightUI) and the API session (gbp_api) are replaced
with fakes inside the tests that touch them, and neither Playwright nor
google-auth is imported unless a real run asks for it."""
