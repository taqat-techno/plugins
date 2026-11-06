# Field-tested test traps (reference)

Read this when an Odoo test passes or fails for a reason the code under test does not
explain. Each entry: rule, why, how to check or fix. The high-impact traps (cron code, raw SQL
on stored computes, `--dev=xml` and record rules, `url_open` and tour time limits) are in
`SKILL.md` and `running-and-coverage.md`, not repeated here.

---

## Writing the test

**Don't assert on the top override only (MRO-blind tests).** A test that inspects the
top-most override of a method passes while an override lower or higher in the chain skips
`super()` and breaks the feature in a real install. Assert the behaviour, or walk
`type(record).__mro__` and check that every class defining the method above the owner calls
`super()`. Run the test with the module set the release will actually install.

**`Form` used as a context manager saves on exit.** `with Form(model) as f:` calls `save()`
when the block ends, so a case meant to end in an invalid state raises at the wrong line.
For that case use `f = Form(model)` without `with` and assert on the form, or call
`f.save()` inside `assertRaises`.

**Monetary widgets split the amount across elements.** QWeb `monetary` / label-price
widgets render the integer and decimal parts in separate nodes, so `assertIn("99.00", html)`
cannot match. Parse the HTML and assert on the element's `text_content()`, normalising
whitespace and the currency symbol.

**Pillow inside Odoo has fewer formats.** Odoo calls `Image.preinit()`, which registers only
the common plugins, so WebP and TIFF saves fail inside Odoo while working in a plain Python
shell. Import the plugin explicitly (`from PIL import WebPImagePlugin`), verify inside
`odoo-bin shell`, and assert the stored bytes and `mimetype`, not just that no exception was
raised.

**Odoo 17 POS session lifecycle.** Close a session in the same order the UI does:
`set_cashbox_pos` → order + payment → `post_closing_cash_details` →
`close_session_from_ui`. `action_pos_session_closing_control` skips the cash steps and closes
straight through, and a cash-control session waits in `opening_control` until the cashbox is
set. Base the class on the POS test helpers (`TestPoSCommon`) rather than building config
by hand.

## Isolation

**A `cr.commit()` inside a business method breaks TransactionCase.** The commit releases the
test savepoint, so later tests fail with `InvalidSavepointSpecification` and fixtures leak
into the database permanently. Grep the code under test (and its dependencies) for
`cr.commit()` before trusting a run; patch the method or the commit in the test, and fix the
module if it is yours (business methods must not commit).

## Gates

**Boot gate before targeted tests.** Order the checks so each one is cheap relative to the
next: parse every changed `.py`/`.xml` (T0) → **boot gate**: `-u <all changed modules>
--stop-after-init` on a disposable clone, judged by the log-level count and `Modules loaded`
(see the stack-doctor skill) → targeted tests (T1) → the module suites (T2) → a full
regression with the real module set only as a release gate (T3). Never edit the tree while a
full run is in progress: the run loads files at different times and reports a mix.
