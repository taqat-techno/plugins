---
title: 'Odoo Testing Workflow'
read_only: false
type: 'command'
description: 'Odoo testing toolkit - generate, mock data, run, coverage, and E2E tests'
argument-hint: '[generate|data|run|coverage|e2e] [<model|module>] [args...]'
---

# /test [sub-command] [args...]

## Bare-invocation behavior (no args)

When invoked with no arguments, auto-detect the target module from `$CWD` (walk up to `__manifest__.py`) and run the full workflow: **coverage scan → report any untested methods → offer to generate skeletons → run the existing suite**. If the module cannot be detected (no manifest under `$CWD` or its parents), surface a list of direct-child modules and ask which one to operate on.

This makes `/test` work from inside any module directory without arguments.

## Routing

Parse the first token of `$ARGUMENTS` and route:

| Token | Action |
|-------|--------|
| *(empty)* | Auto-detect module + run full workflow (coverage > generate-missing > run) |
| `generate` | Generate TransactionCase/HttpCase test skeleton |
| `data` | Generate mock data factory for setUp |
| `run` | Run test suite with colored output |
| `coverage` | Scan for untested methods + coverage % |
| `e2e` | Generate/run Playwright E2E tests |
| *(other)* | Treat as module name, run full workflow |

```
/test                              Show help + offer full workflow
/test generate <model> [module]    Generate test skeleton
/test data <model> [--count N]     Generate mock data factory
/test run <module> [--tags X]      Run test suite
/test coverage <module>            Coverage analysis
/test e2e <module> [--url X]       Playwright E2E tests
```

## Execution

Use the odoo-test skill for:
- Test generation patterns (TransactionCase, HttpCase, SavepointCase)
- Mock data factory patterns (field-type-aware generation)
- Test execution with config/database auto-detection
- Coverage analysis methodology (static method comparison)
- E2E test scaffolding (Playwright + page objects)
- Azure DevOps CI integration patterns

Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/test/`:
- `test_generator.py` - Generate test skeletons from models
- `mock_data_factory.py` - Generate realistic test data
- `test_runner.py` - Execute test suites with colored output
- `coverage_reporter.py` - Test coverage analysis
