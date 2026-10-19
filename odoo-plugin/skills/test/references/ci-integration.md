# Running Odoo tests in CI

Provider-neutral. The pipeline shape is the same on every CI service:

1. Start PostgreSQL as a service container.
2. Install Odoo's Python requirements and the module's own.
3. Run the module's tests with `--test-enable --stop-after-init`, keeping the log.
4. Turn the run into a JUnit XML file with `scripts/test/test_runner.py`.
5. Publish the JUnit file with the provider's native test-report step.
6. Fail the job on the **test count and result**, not on a grep of the log for `ERROR`
   (see "Test-invocation traps" in `running-and-coverage.md`).

Scope CI by tier: T2 (each changed module's suite) on every pull request, T3 (every
module, `FULL_SUITE=1`) on a schedule or before a release.

## The common test step

```bash
python -m odoo \
  -c conf/test.conf \
  -d test_db \
  --test-enable \
  -u my_module \
  --test-tags /my_module \
  --stop-after-init \
  --log-level=test \
  2>&1 | tee test_output.log
```

## JUnit XML from an Odoo run

`test_runner.py` wraps the call above and writes a JUnit (or JSON) report:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/test/test_runner.py" \
  --module my_module \
  --config conf/test.conf \
  --database test_db \
  --output-format junit \
  --output test_results.xml
```

In CI, copy the script into the repository (or vendor it) rather than depending on a
Claude Code install path.

## GitHub Actions

```yaml
# .github/workflows/odoo-tests.yml
jobs:
  odoo-tests:
    runs-on: ubuntu-22.04
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: odoo
          POSTGRES_PASSWORD: odoo
          POSTGRES_DB: postgres
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 5s --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -r requirements.txt
      - run: python tools/test_runner.py --module my_module --config conf/test.conf --database test_db --output-format junit --output test_results.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: odoo-test-results
          path: test_results.xml
```

Use a JUnit report action of your choice (for example `dorny/test-reporter` or
`mikepenz/action-junit-report`) to show the results on the pull request.

## GitLab CI

```yaml
# .gitlab-ci.yml
odoo-tests:
  image: python:3.10
  services:
    - name: postgres:16
      alias: db
  variables:
    POSTGRES_USER: odoo
    POSTGRES_PASSWORD: odoo
  script:
    - pip install -r requirements.txt
    - python tools/test_runner.py --module my_module --config conf/test.conf --database test_db --output-format junit --output test_results.xml
  artifacts:
    when: always
    reports:
      junit: test_results.xml
```

## Azure Pipelines

```yaml
# azure-pipelines.yml
jobs:
  - job: OdooTests
    pool:
      vmImage: ubuntu-22.04
    services:
      postgres: postgres
    steps:
      - task: UsePythonVersion@0
        inputs:
          versionSpec: "3.10"
      - script: pip install -r requirements.txt
      - script: python tools/test_runner.py --module my_module --config conf/test.conf --database test_db --output-format junit --output test_results.xml
      - task: PublishTestResults@2
        condition: always()
        inputs:
          testResultsFormat: JUnit
          testResultsFiles: test_results.xml
          failTaskOnFailedTests: true
```

(Declare the `postgres` container under `resources.containers`.) `PublishTestResults@2`
already uploads to Azure Test Plans; there is no need to call the Azure DevOps REST API
yourself. If the `devops` plugin is installed, its pipeline tools can read the published
run afterwards.

## Secrets in CI

Database passwords and API keys come from the provider's secret store (GitHub/GitLab
CI variables marked masked, Azure Pipelines secret variables). Never commit them to
`conf/test.conf`, and never print them in the job log.
