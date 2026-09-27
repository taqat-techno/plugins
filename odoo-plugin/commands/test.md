---
title: 'Odoo Testing Workflow'
read_only: false
type: 'command'
description: 'Odoo testing - runs the tests for what changed by default; --all, generate, data, run, coverage, e2e'
argument-hint: '[--all | generate|data|run|coverage|e2e] [<model|module>] [args...]'
---

# /test [sub-command] [args...]

## Bare-invocation behavior (no args)

With no arguments, test **what changed**, not the whole module:

1. Collect the changed files: the files edited in this session. If there are none,
   use `git status --porcelain` plus `git diff --name-only` against the upstream branch.
2. Map each file to its module by walking up to `__manifest__.py`. Map each changed
   `models/*.py` or `wizards/*.py` file to the test classes that exercise it, found by
   grepping that module's `tests/` for the model or class name.
3. Choose the run mode:
   - Only `.py` logic changed → warm database, no `-u`:
     `test_runner.py --module <m> --no-update [--test-class <C>]`.
   - A manifest, XML, CSV/ACL, `.po` or model field changed → update the module:
     `test_runner.py --module <m> [--test-class <C>]`.
4. Run T1 (the mapped classes plus any new tests). If it is green, run T2: each changed
   module's whole suite, once.
5. Report per the `test-scope` report block, and say that the full suite was not run.

If nothing changed and no module can be detected from `$CWD`, list the direct-child
modules and ask which one to test. Bare `/test` never generates test files and never
runs every installed module.

## Routing

Parse the first token of `$ARGUMENTS` and route:

| Token | Action |
|-------|--------|
| *(empty)* | Changed-scope run (above) |
| `--all` | Full workflow for the detected (or named) module: coverage, then run the whole module suite. For **every** module, only when the user explicitly asks: prefix the command with `FULL_SUITE=1` |
| `generate` | Generate a TransactionCase/HttpCase test skeleton. **Opt-in only** - extend an existing test module first (`test-scope` hygiene) |
| `data` | Generate a mock data factory for setUp |
| `run` | Run a module's tests. `--tags X`, `--class C`, `--method m`, `--warm` (no `-u`) |
| `coverage` | Scan for untested methods and report coverage % (read-only; offers `generate` for gaps) |
| `e2e` | Generate/run Playwright E2E tests for the changed flow |
| *(other)* | Treat as a module name → changed-scope run inside that module |

```
/test                              Test what changed (T1, then T2)
/test --all [module]               Whole module suite + coverage
/test generate <model> [module]    Generate test skeleton (opt-in)
/test data <model> [--count N]     Generate mock data factory
/test run <module> [--tags X] [--warm]   Run a module's tests
/test coverage <module>            Coverage analysis
/test e2e <module> [--url X]       Playwright E2E tests
```

## Execution

Use the odoo-plugin `test` skill for:
- Scoped selection (`--test-tags /module:Class.method`, the warm-database loop and its limits)
- Test generation patterns (TransactionCase, HttpCase)
- Mock data factory patterns (field-type-aware generation)
- Coverage analysis methodology (static method comparison)
- E2E test scaffolding (Playwright + page objects)
- Azure DevOps CI integration patterns

Tier policy and test-file hygiene come from the `test-scope` skill (agent-safety-guards
plugin), when it is installed.

Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/test/`:
- `test_runner.py` - execute tests. `--no-update` gives the warm loop. A run that
  collected 0 tests, or where Odoo exits non-zero, is reported as a failure
- `test_generator.py` - generate test skeletons from models
- `mock_data_factory.py` - generate realistic test data
- `coverage_reporter.py` - test coverage analysis
