# Runner recipes - selecting the tests for a change

Generic runners only. Odoo (`odoo-bin`), Django (`manage.py test`) and FastAPI-specific
selection live in their framework skills. Every recipe here maps to a tier of the
ladder in `../SKILL.md`.

## pytest

| Need | Command |
|---|---|
| One test (T1) | `pytest path/to/test_mod.py::TestClass::test_name` |
| One module or class (T1) | `pytest path/to/test_mod.py` or `path/to/test_mod.py::TestClass` |
| By name across files (T1) | `pytest -k "refund and not slow"` |
| Re-run only what failed | `pytest --lf` (with `-x` to stop at the first failure) |
| Failures first, then the rest | `pytest --ff` - this still runs everything, so treat it as T3 |
| One package (T2) | `pytest path/to/package/` |
| Changed-code selection | `pytest --testmon` (plugin `pytest-testmon`): runs tests whose covered code changed. Needs one baseline run first |

Notes:
- `--lf` with no recorded failures runs **everything** by default
  (`--last-failed-no-failures all`). Add `--lfnf=none` when you mean "only failures".
- For a cross-version control run, disable the cache (`-p no:cacheprovider`) so `--lf`
  state from the other version cannot leak in. See `test-result-evidence`.
- `-m "not slow"` narrows by marker but is still suite-wide, so treat it as T3.

## vitest

| Need | Command |
|---|---|
| Tests that import the changed files (T1) | `npx vitest related --run src/a.ts src/b.tsx` |
| Tests affected by uncommitted changes (T1) | `npx vitest run --changed` (or `--changed <ref>`) |
| One file or name (T1) | `npx vitest run src/cart.test.ts -t "applies coupon"` |
| One folder (T2) | `npx vitest run src/features/cart` |

**Watch-mode trap:** bare `vitest` and many `npm test` scripts start **watch mode** and
never exit. Always pass `run` or `--run` from an agent session.

## jest

| Need | Command |
|---|---|
| Tests related to the changed files (T1) | `npx jest --findRelatedTests src/a.ts src/b.ts` |
| Tests related to uncommitted changes (T1) | `npx jest -o` (`--onlyChanged`, needs git) |
| Since a branch point (T2) | `npx jest --changedSince=origin/main` |
| One file or name (T1) | `npx jest src/cart.test.ts -t "applies coupon"` |

## playwright

| Need | Command |
|---|---|
| One spec (T1) | `npx playwright test e2e/checkout.spec.ts` |
| By title (T1) | `npx playwright test --grep "guest checkout"` |
| Only failures from the last run | `npx playwright test --last-failed` |
| Specs touched by uncommitted changes (T1) | `npx playwright test --only-changed` (or `--only-changed=<ref>`) |
| One project/browser | add `--project chromium` |

End-to-end suites are the slowest tier to run in full. Keep them at T1 (the flow you
changed) unless the user asks.

## npm / pnpm / yarn scripts

`npm test` runs whatever the `test` script says, which is usually the whole suite and
often watch mode. Pass selectors through after `--`:

```
npm test -- src/cart.test.ts
npm run test -- --run src/cart
pnpm test -- -t "applies coupon"
```

Read `package.json` first so you know which runner the script calls, then use that
runner's selector above.

## Mapping a changed file to its tests

1. The changed file is itself a test: run it.
2. A sibling or mirrored test exists (`foo.py` -> `test_foo.py` / `tests/test_foo.py`;
   `Cart.tsx` -> `Cart.test.tsx`): run it.
3. Otherwise grep the test tree for the module path, class or exported symbol name, and
   run what matches.
4. JS: prefer `vitest related` / `jest --findRelatedTests`, which follow the import
   graph for you.
5. Nothing matches: the change has no covering test. Write one in the right module. Do not
   fall back to the full suite.
