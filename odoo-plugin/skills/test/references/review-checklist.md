# Odoo Test Review Checklist & Anti-Pattern Catalogue

Use this when reviewing existing module tests or gating release-readiness. Score each item PASS / GAP / FAIL and turn GAP/FAIL into concrete required changes.

## A. Structure & discovery

- [ ] Every `test_*.py` is imported exactly once in `tests/__init__.py` (a file not imported never runs).
- [ ] `tests/__init__.py` contains only trivial relative imports (`from . import test_x`).
- [ ] Each test class is exactly **one** of `at_install` / `post_install`.
- [ ] Shared fixtures live in a `common.py` base; individual tests are small.

## B. Base classes & imports

- [ ] `TransactionCase` for unit/integration; `HttpCase` for routes/tours; correct base for the version (see `odoo-version-matrix.md`).
- [ ] `Form` used for onchange/view-driven behavior (not raw `create()` where onchange matters).
- [ ] Correct `Command` API / legacy tuples for the version.

## C. Data setup

- [ ] Fixtures built in `setUpClass` with `super().setUpClass()`; no reliance on dirty DB rows.
- [ ] No unguarded demo-data dependency (guarded with `loaded_demo_data` + `skipTest` if needed).
- [ ] Users/groups/companies created explicitly; multi-company via `with_company`/`allowed_company_ids`.

## D. Security

- [ ] Permission-sensitive models have ACL tests run as a **non-admin** (`with_user`/`@users`).
- [ ] Both the allowed path and the forbidden path (`AccessError`) are asserted.
- [ ] Record rules assert the visible vs hidden record sets.
- [ ] Cache invalidated between privilege levels (no admin-cached false pass).
- [ ] `sudo()` is used only to deliberately bypass — never to make a failing test pass.

## E. Business logic

- [ ] Constraints (`@api.constrains` → `ValidationError`; `_sql_constraints` → `IntegrityError` under `mute_logger`).
- [ ] Computed/related fields and recompute-on-change.
- [ ] State transitions assert `state` after each step + illegal transitions raise.
- [ ] Edge and negative cases — not only the happy path.
- [ ] Generated records / sequences / side-effects verified.

## F. Wizards / controllers / reports / mail (when present)

- [ ] Wizards launched via `with_context(active_ids=…)` / `Form`; assert real side-effects + ACL + error path.
- [ ] Controllers use `HttpCase`, assert the response contract, are `post_install`.
- [ ] Reports assert rendered content / report values, not brittle full-PDF bytes.
- [ ] Mail/activity mocked; messages/followers/activities/tracking asserted; expected logs muted.

## G. Regression & traceability

- [ ] A bugfix ships a regression test that would FAIL on the pre-fix code.
- [ ] If derived from an issue/Acceptance Criteria, each requirement maps to a test.

## H. Run & honesty

- [ ] CLI commands provided (disposable DB, `--stop-after-init`).
- [ ] Runtime status reported honestly: verified-runtime vs static-author-only. Import success ≠ tested.

## I. Genericness / privacy (for shared/reusable tests & docs)

- [ ] No hardcoded client/project name, production URL, private host, real DB name, credential, or absolute machine path.

---

## Anti-pattern catalogue (problem → why it's bad → fix)

| Anti-pattern | Why it's bad | Fix |
|---|---|---|
| Relying on existing/dirty DB data | Passes only on a primed DB; flaky elsewhere | Build every record in `setUpClass`; snapshot pre-existing rows if the model is global |
| Assuming an empty DB | Other modules/demo may have rows | Filter by your own fixtures or snapshot baseline counts |
| `sudo()` everywhere | Hides real permission bugs; security never exercised | Test as a non-admin with `with_user`; reserve `sudo()` for deliberate bypass |
| Happy-path only | Misses constraints, ACL, edge cases | Add negative/error/edge tests |
| Broad, fragile tests | One change breaks many; failures hard to localize | Small focused methods; assert specific values |
| Sleeps / time assumptions | Slow and flaky | Use `freeze_time` for date logic; never `time.sleep` |
| Accidental install-order dependence | Test passes only after another test ran | Use `TransactionCase` (isolated); avoid `SingleTransactionCase` for normal tests |
| Direct SQL where ORM is under test | Bypasses the code being tested | Exercise via the ORM; reserve SQL for setup you can't do via ORM |
| Testing local migration scripts as product behavior | Migrations don't ship to a vanilla deploy | Test the product code; keep data-repair migrations out of product assertions |
| Exact full-HTML/PDF comparisons | Break on any template wording change | Assert key substrings / report values |
| Hardcoded magic state strings everywhere | Break on selection changes | Centralize constants; assert via the model where possible |
| Real network/email in tests | Slow, flaky, can leak | Mock the gateway / external service |
| `cr.commit()` inside a test | Breaks isolation; forbidden by the framework | Rely on per-test rollback; never commit |
| Hardcoding client/project data | Not reusable; leaks private info | Use generic fixtures and placeholders |
| Skipping security tests on permission-sensitive modules | Ships ACL/rule regressions silently | Always add ACL + record-rule tests there |
| Treating "module installs / imports" as coverage | Proves nothing about behavior | Assert actual behavior |
| Empty test files to look complete | False sense of coverage | Only create relevant files with real assertions |
| Claiming runtime/browser/upgrade validation not actually run | Dishonest; misleads release review | State exactly what was run; mark unverified honestly |
