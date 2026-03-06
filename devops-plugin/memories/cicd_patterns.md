# CI/CD Patterns for Odoo Projects

> **Purpose**: Complete GitHub Actions workflow patterns for Odoo ERP projects.
> Source: Research report ODOO-CICD-2026-002 + session knowledge on Odoo.sh.

---

## Odoo.sh vs Self-Hosted Decision Table

| Factor | Odoo.sh | Self-Hosted GitHub Actions |
|--------|---------|---------------------------|
| Cost | Additional subscription | Free (public) / $0.008/min (private) |
| Odoo core | Injected automatically | You provide via Docker/server |
| PostgreSQL | Managed | You configure (service container) |
| Test runner | Auto on every push | Configure in YAML |
| Staging env | Auto per-branch | Configure SSH deploy |
| Custom addons repo | **Perfect fit** | Supports any structure |
| Multi-version (14-19) | One version per project | Full matrix support |
| Vendor lock-in | Yes | No |

**Recommendation**: Use Odoo.sh for single-version SaaS projects. Use self-hosted GitHub Actions for multi-version enterprise installations.

---

## Odoo.sh Custom-Addons Pattern

When repo contains ONLY custom addons (Odoo.sh injects core):

```
your-repo/
├── .github/
│   └── workflows/
│       └── quality-gate.yml   ← Lint only (Odoo.sh handles tests)
├── odoo_tests.cfg             ← Controls Odoo.sh test behavior
├── requirements.txt           ← Auto-installed by Odoo.sh
├── my_module_1/
├── my_module_2/
└── my_module_3/
```

**`odoo_tests.cfg`** (place at repo root for Odoo.sh):
```ini
[options]
test_enable = True
test_tags = standard,at_install
```

**GitHub Actions for Odoo.sh** (quality gate only — Odoo.sh handles the rest):
```yaml
# .github/workflows/quality-gate.yml
name: Quality Gate
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Lint
        run: |
          pip install flake8 bandit
          flake8 . --max-line-length=120 --exclude=__pycache__
          bandit -r . -ll --exclude ./.git
      - name: Validate XML
        run: |
          pip install lxml
          python3 -c "
          import glob, lxml.etree as ET, sys
          errors = []
          for f in glob.glob('**/*.xml', recursive=True):
              try: ET.parse(f)
              except Exception as e: errors.append(f'{f}: {e}')
          [print(e) for e in errors]; sys.exit(len(errors))
          "
      - name: Validate manifests
        run: |
          python3 -c "
          import glob, ast, sys
          for f in glob.glob('**/__manifest__.py', recursive=True):
              try: ast.literal_eval(open(f).read())
              except Exception as e:
                  print(f'{f}: {e}'); sys.exit(1)
          "
```

---

## Self-Hosted: 5-Stage Pipeline Architecture

```
PR / Push
    │
    ▼ Stage 1 (~3-5 min)
┌─────────────────────────┐
│  Lint & Quality Gate    │
│  pre-commit hooks       │
│  pylint-odoo            │
│  XML validation         │
│  manifest check         │
│  Bandit SAST            │
└──────────┬──────────────┘
           │ (lint passes)
    ▼ Stage 2 (~10-20 min)
┌─────────────────────────┐
│  Automated Tests        │
│  Changed module detect  │
│  PostgreSQL container   │
│  odoo-bin --test-enable │
│  Coverage report        │
└──────────┬──────────────┘
           │ (merge to main)
    ▼ Stage 3 (~5-10 min)
┌─────────────────────────┐
│  Docker Build & Push    │
│  Multi-version matrix   │
│  Push to GHCR           │
│  Trivy vuln scan        │
└──────────┬──────────────┘
           │ (auto)
    ▼ Stage 4 (environment-gated)
┌─────────────────────────┐
│  Deploy                 │
│  staging: auto on main  │
│  production: tag + 2    │
│  approvers required     │
│  SSH: backup→pull→      │
│  update→restart→health  │
└──────────┬──────────────┘
           │
    ▼ Stage 5
┌─────────────────────────┐
│  Notify (ntfy/Slack)    │
│  on success or failure  │
└─────────────────────────┘
```

---

## Stage 1: Lint Workflow (`.github/workflows/1-lint.yml`)

```yaml
name: "Code Quality & Lint"
on:
  pull_request:
    branches: [main, develop]
    paths:
      - "odoo17/projects/**"
      - "odoo18/projects/**"
      - "odoo19/projects/**"
      - ".pre-commit-config.yaml"
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: actions/cache@v4
        with:
          path: ~/.cache/pre-commit
          key: pre-commit-${{ runner.os }}-${{ hashFiles('.pre-commit-config.yaml') }}
      - run: pip install pre-commit
      - run: pre-commit run --from-ref ${{ github.event.pull_request.base.sha }} --to-ref ${{ github.event.pull_request.head.sha }}

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install bandit[toml]
      - run: |
          bandit -r odoo17/projects odoo18/projects odoo19/projects \
            -f sarif -o bandit-results.sarif --skip B101,B311 -ll --exit-zero
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: bandit-results.sarif

  xml-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get install -y libxml2-utils
      - run: |
          find odoo17/projects odoo18/projects odoo19/projects \
            -name "*.xml" -not -path "*/static/*" | while read -r f; do
            xmllint --noout "$f" || exit 1
          done

  manifest-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: |
          python3 -c "
          import ast, os, sys
          REQUIRED = ['name', 'version', 'depends', 'author', 'license']
          errors = []
          for root, dirs, files in os.walk('.'):
              if '/projects/' not in root: continue
              if '__manifest__.py' in files:
                  p = os.path.join(root, '__manifest__.py')
                  try:
                      m = ast.literal_eval(open(p).read())
                      for k in REQUIRED:
                          if k not in m: errors.append(f'{p}: Missing {k}')
                  except Exception as e:
                      errors.append(f'{p}: {e}')
          [print(e) for e in errors]; sys.exit(len(errors))
          "
```

---

## Stage 2: Changed Module Detection

```bash
# Get changed Odoo module names from git diff
CHANGED_MODULES=$(git diff --name-only HEAD~1 HEAD \
  | grep "^odoo17/projects/" \
  | awk -F/ '{print $3}' \
  | sort -u \
  | tr '\n' ',')

# Use in odoo update command
python -m odoo -c conf/myproject.conf -d mydb \
  -u "${CHANGED_MODULES%,}" --stop-after-init
```

**With `dorny/paths-filter@v3`** (recommended for PRs):
```yaml
- uses: dorny/paths-filter@v3
  id: filter
  with:
    filters: |
      odoo17:
        - 'odoo17/projects/**'
      odoo18:
        - 'odoo18/projects/**'
```

---

## Stage 3: Docker Build (`.github/workflows/3-docker-build.yml`)

```yaml
name: "Docker Build & Push"
on:
  push:
    branches: [main]
    tags: ["v*"]
env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ${{ github.repository_owner }}/odoo
jobs:
  build-and-push:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        version: ["17", "18", "19"]
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_PREFIX }}${{ matrix.version }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=sha,prefix=sha-
            type=raw,value=latest,enable={{is_default_branch}}
      - uses: docker/build-push-action@v6
        with:
          context: ./odoo${{ matrix.version }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha,scope=odoo${{ matrix.version }}
          cache-to: type=gha,mode=max,scope=odoo${{ matrix.version }}
```

---

## GitHub Environments Configuration

Configure in: `GitHub → Settings → Environments`

| Environment | Branch rule | Protection | Secrets |
|-------------|-------------|------------|---------|
| `development` | Any | None | `DEV_SSH_KEY`, `DEV_HOST` |
| `staging` | `main` only | None | `STAGING_SSH_KEY`, `STAGING_HOST` |
| `production` | `v*` tags only | 2 required reviewers | `PROD_SSH_KEY`, `PROD_HOST` |

---

## Pre-commit Config (`.pre-commit-config.yaml`)

```yaml
default_language_version:
  python: python3.11
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
        exclude: ".*\\.po$"
      - id: end-of-file-fixer
        exclude: ".*\\.po$"
      - id: check-yaml
      - id: check-merge-conflict
      - id: check-added-large-files
        args: ["--maxkb=1000"]

  - repo: https://github.com/OCA/pylint-odoo
    rev: v9.3.0
    hooks:
      - id: pylint-odoo
        args: ["--rcfile=.pylintrc-odoo"]
        files: "odoo1[4-9]/projects/.*\\.py$"

  - repo: https://github.com/OCA/odoo-pre-commit-hooks
    rev: v0.0.24
    hooks:
      - id: oca-checks-odoo-module
      - id: oca-checks-po
        files: ".*\\.(po|pot)$"
```

---

## Repository Structure for Monorepo CI/CD

```
C:\TQ-WorkSpace\odoo\  (or your repo root)
├── .github\
│   ├── workflows\
│   │   ├── 1-lint.yml
│   │   ├── 2-test.yml
│   │   ├── 3-docker-build.yml
│   │   ├── 4-deploy-staging.yml
│   │   └── 5-deploy-production.yml
│   └── filters.yaml
├── .pre-commit-config.yaml
├── .pylintrc-odoo
├── odoo17\projects\
├── odoo18\projects\
└── odoo19\projects\
```

---

## Multi-Version Odoo CI Matrix

```yaml
# Python version per Odoo version
strategy:
  matrix:
    include:
      - odoo_version: "14"
        python_version: "3.8"
        pg_version: "13"
      - odoo_version: "15"
        python_version: "3.10"
        pg_version: "13"
      - odoo_version: "16"
        python_version: "3.10"
        pg_version: "14"
      - odoo_version: "17"
        python_version: "3.11"
        pg_version: "15"
      - odoo_version: "18"
        python_version: "3.12"
        pg_version: "15"
      - odoo_version: "19"
        python_version: "3.12"
        pg_version: "16"
```

---

## Stage 2.5: E2E Tests with Playwright

Runs AFTER Python unit tests pass, AGAINST a live Odoo instance (staging or Odoo.sh).

### Option A: Against Odoo.sh Staging URL

```yaml
# .github/workflows/e2e-tests.yml
name: "E2E Tests (Playwright)"

on:
  push:
    branches-ignore: [main]  # Odoo.sh staging branches
  workflow_dispatch:

jobs:
  e2e:
    name: Playwright E2E
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: 'npm'

      - run: npm ci

      - run: npx playwright install --with-deps chromium

      - name: Run E2E tests against Odoo.sh staging
        run: npx playwright test
        env:
          PLAYWRIGHT_BASE_URL: ${{ secrets.ODOO_STAGING_URL }}
          ODOO_USER: ${{ secrets.ODOO_TEST_USER }}
          ODOO_PASSWORD: ${{ secrets.ODOO_TEST_PASSWORD }}

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 14
```

### Option B: Self-Hosted (Start Odoo in CI)

```yaml
# Add PostgreSQL service + start Odoo before running Playwright
jobs:
  e2e:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: odoo
          POSTGRES_PASSWORD: odoo
          POSTGRES_DB: postgres
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 10s --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: actions/setup-node@v4
        with:
          node-version: "20"

      - run: pip install -r requirements.txt
      - run: npm ci
      - run: npx playwright install --with-deps chromium

      - name: Create E2E test database
        run: PGPASSWORD=odoo psql -h localhost -U odoo -c "CREATE DATABASE e2e_test" postgres

      - name: Start Odoo in background
        run: |
          python -m odoo \
            --db_host=localhost --db_user=odoo --db_password=odoo \
            -d e2e_test --addons-path=odoo/addons,projects \
            --without-demo=False --http-port=8069 &

          # Wait for Odoo to be ready
          for i in $(seq 1 30); do
            curl -sf http://localhost:8069/web/health && break || true
            echo "Waiting for Odoo... ($i/30)"
            sleep 5
          done

      - name: Run Playwright E2E tests
        run: npx playwright test
        env:
          PLAYWRIGHT_BASE_URL: http://localhost:8069
          ODOO_USER: admin
          ODOO_PASSWORD: admin

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 14
```

### Required GitHub Secrets for E2E

| Secret | Description |
|--------|-------------|
| `ODOO_STAGING_URL` | `https://your-project.odoo.com` (Odoo.sh staging) |
| `ODOO_TEST_USER` | Dedicated test user (NOT admin, use a test account) |
| `ODOO_TEST_PASSWORD` | Test user password |

---

## Related Commands & Memories

- `/ci-setup` — Generate complete `.github/workflows/` for an Odoo project
- `/e2e-test` — Generate Playwright test scaffolds for an Odoo module
- `automation_templates.md` — Build monitor, PR auto-merge, release notes scripts
- `github_integration.md` — GitHub + Azure DevOps bidirectional linking
- `odoo-service-plugin/memories/deployment_patterns.md` — SSH deployment scripts
- `odoo-test-plugin/memories/testing_patterns.md` — CI test runner patterns
- `odoo-test-plugin/memories/playwright_e2e_patterns.md` — Full Playwright E2E reference
