# Scoped testing — plan (2026-09-27)

**Problem.** During development Claude creates many local test files and re-runs whole
suites after small changes. That costs minutes per edit.

**Goal.** Test the change, not the system, without losing accuracy.

## User decisions (2026-09-27)

| Question | Decision |
|---|---|
| Enforcement | Hook: deny a full-suite command, override with `FULL_SUITE=1` |
| When the full suite runs | **Only when the user asks, or in CI.** No automatic T3 |
| Bare test commands | Changed-scope by default; `--all` for everything; Odoo skeleton generation becomes opt-in |
| Pending lesson edits | Committed first, separately (`e302c75`) |

## Root causes found (survey)

1. Bare `/odoo:test`, `/django-test` and `/fastapi-test` run the whole module or project.
   `/odoo:test` also offers to generate skeleton test files.
2. `odoo scripts/test/test_runner.py` always adds `-u`/`-i`, so the warm-DB loop is
   impossible. It also reports "ALL PASSED" when 0 tests ran and ignores Odoo's exit code.
3. Unqualified full-suite rules:
   - `test-double-seams:152`
   - `workflow-reliability:92`
   - `odoo i18n-audit:174`
   - `react19-migration:40,120-132`
4. No shipped guidance on change-scoped selection for pytest, vitest, jest or playwright.
5. The existing stderr-plus-exit-0 hook advisories do not reach the model. Only a
   `permissionDecision: deny` reason does, and that works even in bypass mode.

## Design — single owner per layer

| Layer | Owner | Content |
|---|---|---|
| Policy (tiers, triggers, hygiene, reporting) | `agent-safety-guards/skills/test-scope` (new) | T0 static → T1 targeted → T2 affected → T3 full, which runs only when asked or in CI |
| Generic runner recipes | `test-scope/references/runner-recipes.md` | pytest, vitest, jest, playwright, npm scripts |
| Framework selection | `odoo/test`, `django/django-testing`, `fastapi/fastapi-testing` | Framework-specific selectors |
| Enforcement | `agent-safety-guards/hooks/test_scope_guard.py` | `track` (PostToolUse, async) and `check` (PreToolUse Bash\|PowerShell) |
| Commands | odoo `test`, django `django-test`, fastapi `fastapi-test` | Bare invocation = changed-scope; `--all` runs everything |

Evidence rules keep their current owner, `test-result-evidence`:
- 0 tests collected is a failure.
- The verdict comes from the summary line plus the exit code.
- When a narrow run and a wide run disagree, the wide one wins.
- A regression test must fail before the fix.

## Checklist

- [x] Survey, decisions, lessons commit plus ledger
- [x] agent-safety-guards: skill, reference, hook, hook tests, `D-001`, evals, rewordings, 0.3.0
- [x] odoo: runner fix plus warm mode, command, skill section and example fixes, memories, i18n-audit, generator footer
- [x] django: command plus skill section
- [x] fastapi: command plus skill section
- [x] react-kit: react19-migration rewording
- [x] worktree: integrate `[release]` gate uses `FULL_SUITE=1`
- [x] Versions, CHANGELOGs, README table, wiki catalog
- [x] Gates: `validate_plugin` ×6, `validate_marketplace`, `validate_evals`, hook self-test plus unit tests, noun sweep

## Result

- Gates: `validate_plugin` exit 0 on all 6 touched plugins; `validate_marketplace` exit 0;
  `validate_evals` 0 FAIL / 0 WARN; hook `--self-test` 46/46; hook end-to-end tests 10/10;
  django 65 and fastapi 70 existing tests still pass; noun sweep clean; 0 deletions.
- **Open: HR-20 behavioural Δ was not measured.** `claude plugin eval` refuses an untrusted
  plugin directory in a non-interactive run, and passing `--trust-plugin` would assert trust
  on the user's behalf. The user runs it once from a terminal.
