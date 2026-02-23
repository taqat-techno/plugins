---
title: 'CI/CD Setup'
read_only: false
type: 'command'
description: 'Generate GitHub Actions CI/CD workflows for an Odoo project (self-hosted or Odoo.sh)'
---

# CI/CD Setup

Generate complete GitHub Actions workflow files for an Odoo project.

## Instructions

Ask the user for the following information if not already provided:

1. **Deployment target**: Self-hosted server OR Odoo.sh
2. **Odoo version(s)**: Which version(s) are in use (14, 15, 16, 17, 18, 19)
3. **Repo structure**: Monorepo (multiple projects) OR single-project repo
4. **Notification channel**: ntfy.sh, Slack, or none

Then generate the appropriate files.

---

## Case A: Odoo.sh (Custom Addons Only)

Generate **2 files** only (Odoo.sh handles tests + deployment):

### File 1: `.github/workflows/quality-gate.yml`

```yaml
name: Quality Gate

on:
  push:
  pull_request:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  quality:
    name: Lint & Validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install tools
        run: pip install flake8 bandit lxml

      - name: Python lint (flake8)
        run: flake8 . --max-line-length=120 --exclude=__pycache__,.git

      - name: Security scan (Bandit)
        run: bandit -r . -ll --exclude ./.git -q

      - name: XML validation
        run: |
          python3 -c "
          import glob, lxml.etree as ET, sys
          errors = []
          for f in glob.glob('**/*.xml', recursive=True):
              try: ET.parse(f)
              except Exception as e: errors.append(f'{f}: {e}')
          [print(e) for e in errors]
          sys.exit(len(errors))
          "

      - name: Manifest validation
        run: |
          python3 -c "
          import glob, ast, sys
          for f in glob.glob('**/__manifest__.py', recursive=True):
              try: ast.literal_eval(open(f).read())
              except Exception as e: print(f'{f}: {e}'); sys.exit(1)
          print('All manifests valid')
          "
```

### File 2: `odoo_tests.cfg` (repo root)

```ini
[options]
test_enable = True
test_tags = standard,at_install
```

**Explanation**: Odoo.sh automatically runs tests when you push. The `quality-gate.yml`
runs fast lint checks in GitHub before Odoo.sh even receives the push.

---

## Case B: Self-Hosted Server

Generate **4 workflow files** + supporting configs:

### File 1: `.github/workflows/1-lint.yml`

```yaml
name: "Lint & Code Quality"

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    name: Pre-commit + Bandit + XML
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
          key: pre-commit-${{ hashFiles('.pre-commit-config.yaml') }}

      - run: pip install pre-commit bandit lxml

      - name: Pre-commit hooks
        run: pre-commit run --all-files || true

      - name: Bandit security scan
        run: bandit -r . -ll --exclude ./.git -q

      - name: XML validation
        run: |
          sudo apt-get install -yq libxml2-utils
          find . -name "*.xml" -not -path "*/.git/*" -not -path "*/static/*" | while read f; do
            xmllint --noout "$f" || exit 1
          done

      - name: Manifest check
        run: |
          python3 -c "
          import glob, ast, sys
          REQUIRED = ['name', 'version', 'depends', 'author', 'license']
          errors = []
          for f in glob.glob('**/__manifest__.py', recursive=True):
              try:
                  m = ast.literal_eval(open(f).read())
                  errors += [f'{f}: Missing {k}' for k in REQUIRED if k not in m]
              except Exception as e:
                  errors.append(f'{f}: {e}')
          [print(e) for e in errors]; sys.exit(len(errors))
          "
```

### File 2: `.github/workflows/2-test.yml`

```yaml
name: "Automated Tests"

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  detect-modules:
    name: Detect Changed Modules
    runs-on: ubuntu-latest
    outputs:
      changed: ${{ steps.detect.outputs.changed }}
      modules: ${{ steps.detect.outputs.modules }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - id: detect
        run: |
          CHANGED=$(git diff --name-only ${{ github.event.before || 'HEAD~1' }} HEAD \
            | grep "^projects/" \
            | awk -F/ '{print $2}' | sort -u | head -5)
          if [ -z "$CHANGED" ]; then
            echo "changed=false" >> $GITHUB_OUTPUT
          else
            echo "changed=true" >> $GITHUB_OUTPUT
            echo "modules=$(echo $CHANGED | jq -R -s -c 'split(" ") | map(select(length > 0))')" >> $GITHUB_OUTPUT
          fi

  test:
    name: "Test ${{ matrix.module }}"
    needs: detect-modules
    if: needs.detect-modules.outputs.changed == 'true'
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        module: ${{ fromJson(needs.detect-modules.outputs.modules || '[]') }}

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: odoo
          POSTGRES_PASSWORD: odoo
          POSTGRES_DB: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: System deps
        run: |
          sudo apt-get update -q
          sudo apt-get install -yq libxml2-dev libxslt1-dev libpq-dev libldap2-dev libsasl2-dev

      - name: Python deps
        run: pip install -r requirements.txt coverage

      - name: Create test database
        run: PGPASSWORD=odoo psql -h localhost -U odoo -c "CREATE DATABASE test_${{ matrix.module }}" postgres

      - name: Run tests
        run: |
          coverage run -m odoo \
            --db_host=localhost --db_user=odoo --db_password=odoo \
            -d test_${{ matrix.module }} \
            --addons-path=odoo/addons,projects \
            --test-enable --stop-after-init \
            -i ${{ matrix.module }} \
            --log-level=test 2>&1 | tee /tmp/test.log
          grep -q "FAILED\|ERROR" /tmp/test.log && exit 1 || true

      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: test-logs-${{ matrix.module }}
          path: /tmp/test.log
          retention-days: 7
```

### File 3: `.github/workflows/4-deploy-staging.yml`

```yaml
name: "Deploy to Staging"

on:
  push:
    branches: [main]

jobs:
  deploy:
    name: Deploy to Staging Server
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.yourcompany.com

    steps:
      - uses: actions/checkout@v4

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.2.0
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            set -e

            # 1. Backup database
            pg_dump -U odoo mydb | gzip > /tmp/backup_$(date +%Y%m%d_%H%M%S).sql.gz
            echo "✓ Database backed up"

            # 2. Get changed modules
            cd /opt/odoo/projects
            OLD_SHA=$(git rev-parse HEAD)
            git pull origin main
            CHANGED=$(git diff --name-only $OLD_SHA HEAD \
              | awk -F/ '{print $2}' | sort -u | tr '\n' ',')
            echo "Changed modules: $CHANGED"

            # 3. Update changed modules
            cd /opt/odoo
            python -m odoo -c conf/myproject.conf -d mydb \
              -u "${CHANGED%,}" --stop-after-init --log-level=warn

            # 4. Restart service
            sudo systemctl restart odoo
            sleep 5

            # 5. Health check
            curl -sf http://localhost:8069/web/health || exit 1
            echo "✓ Deployment complete"
```

### File 4: `.github/workflows/5-deploy-production.yml`

```yaml
name: "Deploy to Production"

on:
  push:
    tags:
      - "v*"

jobs:
  deploy:
    name: Deploy to Production (Approval Required)
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://yourcompany.com

    steps:
      - uses: actions/checkout@v4

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.2.0
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            set -e

            # 1. Backup (keep for 30 days)
            BACKUP_FILE="/backups/odoo_$(date +%Y%m%d_%H%M%S).sql.gz"
            pg_dump -U odoo mydb | gzip > $BACKUP_FILE
            echo "✓ Backup: $BACKUP_FILE"

            # 2. Pull & detect changes
            cd /opt/odoo/projects
            OLD_SHA=$(git rev-parse HEAD)
            git pull origin main
            CHANGED=$(git diff --name-only $OLD_SHA HEAD \
              | awk -F/ '{print $2}' | sort -u | tr '\n' ',')

            # 3. Update
            cd /opt/odoo
            python -m odoo -c conf/production.conf -d mydb \
              -u "${CHANGED%,}" --stop-after-init

            # 4. Restart & verify
            sudo systemctl restart odoo
            sleep 10
            curl -sf http://localhost:8069/web/health || {
              echo "Health check FAILED — rolling back"
              sudo systemctl stop odoo
              # Restore backup: gunzip -c $BACKUP_FILE | psql -U odoo mydb
              exit 1
            }
            echo "✓ Production deployment complete"
```

---

## Case B: Notify on Completion (ntfy.sh)

Add this step at the end of each deploy job:

```yaml
      - name: Notify via ntfy
        if: always()
        run: |
          STATUS="${{ job.status }}"
          ICON=$([ "$STATUS" = "success" ] && echo "✅" || echo "❌")
          curl -s \
            -H "Title: $ICON Odoo Deploy $STATUS" \
            -H "Priority: $([ "$STATUS" = "success" ] && echo 'default' || echo 'high')" \
            -H "Tags: odoo,$([ "$STATUS" = "success" ] && echo 'white_check_mark' || echo 'x')" \
            -d "Branch: ${{ github.ref_name }} | Commit: ${{ github.sha }}" \
            https://ntfy.sh/${{ secrets.NTFY_TOPIC }}
```

---

## Output Summary

After running `/ci-setup`, confirm with user:
- Files generated in `.github/workflows/`
- GitHub Secrets needed (list them clearly)
- Required GitHub Environment setup (staging, production)
- First-run checklist (SSH key setup, server paths)
