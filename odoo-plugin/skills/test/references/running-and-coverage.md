# Running Odoo tests, invocation traps, output, and coverage

Moved out of `SKILL.md` to keep the skill body small. Load this file when the task needs it.

## Running Tests

### By Module

```bash
# Install and test a module
python -m odoo -c conf/project17.conf -d project17 \
    --test-enable -i my_module --stop-after-init

# Update and test an existing module
python -m odoo -c conf/project17.conf -d project17 \
    --test-enable -u my_module --stop-after-init

# Test multiple modules
python -m odoo -c conf/project17.conf -d project17 \
    --test-enable -u module1,module2 --stop-after-init
```

### By Tags

```bash
# Run only post_install tagged tests of one module
# (a bare --test-tags=post_install runs them for EVERY installed module - T3)
python -m odoo -c conf/project17.conf -d project17 \
    --test-enable --test-tags=post_install/my_module --stop-after-init

# Run standard tests of one module
python -m odoo -c conf/project17.conf -d project17 \
    --test-enable --test-tags=standard/my_module --stop-after-init

# Run tests for a specific module - the leading "/" makes it a MODULE filter;
# --test-tags=my_module would select a TAG named my_module and match nothing
python -m odoo -c conf/project17.conf -d project17 \
    --test-enable --test-tags=/my_module --stop-after-init
```

### By Class or Method

```bash
# Run a specific test class
python -m odoo -c conf/project17.conf -d project17 \
    --test-enable --test-tags=/my_module:TestMyModel --stop-after-init

# Run a specific test method
python -m odoo -c conf/project17.conf -d project17 \
    --test-enable --test-tags=/my_module:TestMyModel.test_create --stop-after-init

# Exclude a tag within one module
python -m odoo -c conf/project17.conf -d project17 \
    --test-enable --test-tags=/my_module,-slow --stop-after-init
```

### Test-invocation traps

Four ways a run reports success without running your tests. All four are environment, none
of them are code.

**1. Pin `--db-filter` to the exact test database.** With `--db-filter='.*'` (or none) and a
second database visible, every `HttpCase` request 303s to `/web/database/selector` and the
whole HTTP half of the suite "fails" with `303 != 200`. Always pass
`--db-filter='^<exact_test_db>$'` on a test run — the database-selector trap applies to test
invocations exactly as it does to a browser.

**2. `--test-tags /module` intersects with the modules being updated — but only when
`-i`/`-u` is present.** With `-i`/`-u`, tag selection is restricted to the modules updated in
*that* run, so `-i other_module --test-tags /my_module` runs **zero** tests and prints
`0 failed, 0 error(s) of 0 tests`. Install prerequisites in one run, then test in a second.
Without `-i`/`-u`/`--reinit`, `post_install` tests run for **all installed modules** and are
filtered by `--test-tags` down to `/module:Class.method` — so on a warm database (Odoo 19)
targeted tests need **no `-u` at all**, which is the fast local loop. The cost of dropping
`-u` is that `at_install`-tagged (and untagged-class) tests become unselectable.

**3. A leading `/` in a selector is mangled by MSYS shells on Windows.**
`--test-tags=/my_module` run through Git Bash has its leading slash path-converted into a
Windows path, so the selector matches nothing and the run reports
`0 failed, 0 error(s) of 0 tests` **with exit 0** — a vacuous pass that looks green. Run
selectors from PowerShell, or prefix with `MSYS_NO_PATHCONV=1`. **Any Odoo test run reporting
"of 0 tests" is a failed invocation, never a pass.**

**4. The first frontend HTTP request of a session builds the routing map under
`_registry_test_lock`.** On a slow filesystem (a Windows mount seen from WSL) that takes
minutes inside a server thread holding the lock; the 60 s re-acquire in `release_test_lock`
raises `SystemExit` into the test, and *subsequent* tests then fail with
`RuntimeError: cannot release un-acquired lock` until the server thread finishes. The
signature is a run of consecutive errors that "heals" on its own. Warm it up once in the
first `HttpCase` that touches frontend routes:

```python
def setUp(self):
    super().setUp()
    self.url_open('/web/login', timeout=600)   # throwaway: builds the routing map
```

Related: with `website` installed, `/web/login` becomes a **frontend** route
(`is_frontend=True`), so any is_frontend-based deny logic must carve out `/web` and `/odoo`
by path or it 404s the recovery login.

### Test Output Interpretation

```
[INFO] odoo.tests.result: STARTING tests
[INFO] odoo.tests: Computed test module list for test runner
[OK] odoo.tests: my_module.tests.test_my_model.TestMyModel.test_create_minimal
[OK] odoo.tests: my_module.tests.test_my_model.TestMyModel.test_create_full
[FAIL] odoo.tests: my_module.tests.test_my_model.TestMyModel.test_constraint_fails
  AssertionError: ValidationError not raised
[ERROR] odoo.tests: my_module.tests.test_my_model.TestMyModel.test_db_access
  psycopg2.OperationalError: database connection closed

[INFO] Ran 3 tests in 4.231s
[ERROR] 1 error, 1 failure
```

**The verdict is the summary line plus the process exit code — never an ERROR-line scan.**
Expected-exception tests legitimately log at ERROR: an `assertRaises` around a NOT NULL probe
emits `odoo.sql_db: bad query` unless it is wrapped in `mute_logger`, so a strict ERROR grep
fails a perfectly green suite. Read `N failed, N error(s) of N tests` (it always prints —
including `of 0 tests`, at WARNING, when the selector matched nothing) together with the exit
code. Strict ERROR/CRITICAL log scans belong to **boot and load gates**, where no tests run;
see the odoo-stack-doctor skill for that side.

**A schema-removal refactor strands NOT NULL columns until `-u` runs.** Deleting a required
field from a model leaves the column *and its constraint* in every database created while the
field existed, so every ORM `create()` in that database raises `NotNullViolation` — including
in tests that have nothing to do with the removed field. The tree is correct and the database
is stale. Run `-u <module>` on the dev DB, every reused clone, and any template DB after such
a refactor, or recreate them from the post-refactor tree.

### Log Level for Test Debugging

```bash
# Verbose test output
python -m odoo -c conf/project17.conf -d project17 \
    --test-enable -u my_module \
    --log-level=debug --log-handler=odoo.tests:DEBUG \
    --stop-after-init

# Show test SQL queries
python -m odoo -c conf/project17.conf -d project17 \
    --test-enable -u my_module \
    --log-level=debug --log-handler=odoo.sql_db:DEBUG \
    --stop-after-init
```

## Coverage Analysis

### Manual Coverage Inspection Pattern

To find untested methods in your module:

1. List all public methods in your model files
2. Cross-reference against test files
3. Calculate coverage percentage

```python
# Example: Find methods without tests using coverage_reporter.py
python "${CLAUDE_PLUGIN_ROOT}/scripts/test/coverage_reporter.py" \
    --module /path/to/my_module \
    --output report.json
```

### Python Coverage with odoo-coverage

```bash
# Install coverage tool
pip install coverage

# Run with coverage measurement
coverage run --source=my_module \
    -m odoo -c conf/project17.conf -d project17 \
    --test-enable -u my_module --stop-after-init

# Generate HTML report
coverage html -d htmlcov/

# Generate terminal report
coverage report --show-missing
```

### Coverage Configuration (.coveragerc)

```ini
[run]
source = my_module
omit =
    my_module/tests/*
    my_module/migrations/*
    my_module/__manifest__.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if TYPE_CHECKING:
    @abstractmethod

[html]
directory = htmlcov
title = My Module Test Coverage
```

### Coverage Targets by Code Type

| Code Type | Target Coverage | Rationale |
|-----------|----------------|-----------|
| Business logic methods | 90%+ | Critical paths must be tested |
| Compute fields | 85%+ | Core data integrity |
| Constraints | 100% | Security and data integrity |
| Controllers (HTTP routes) | 80%+ | API contract validation |
| Wizards | 75%+ | User workflow coverage |
| XML views | N/A | Tested via integration |
| `__manifest__.py` | N/A | Not executable logic |
