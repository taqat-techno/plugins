# GitHub Integration Patterns

> **Purpose**: Patterns for integrating GitHub (`gh` CLI) with Azure DevOps work items when repos live on GitHub but tracking is in Azure DevOps.

## Linking GitHub PRs to Azure DevOps Work Items

Azure DevOps automatically detects AB# references in GitHub PR titles and commit messages:

```bash
# Create PR that links to Azure DevOps work item AB#1234
gh pr create \
  --title "feat: [AB#1234] Add payment gateway integration" \
  --body "$(cat <<'EOF'
## Summary
- Implements Eurasia Digipay v3 wallet integration
- Adds settlement reconciliation model

## Azure DevOps
Resolves AB#1234

## Test Plan
- [ ] Run integration tests against staging wallet API
- [ ] Verify settlement amounts match
EOF
)"

# Multiple work items in one PR
gh pr create \
  --title "fix: [AB#1234] [AB#1235] Fix invoice generation errors" \
  --body "Resolves AB#1234, AB#1235"
```

**Azure DevOps setup required**:
Navigate to Project Settings → GitHub Connections → Link GitHub repo → Enable "AB# mention detection"

---

## gh CLI Quick Reference

### Repository Operations
```bash
# Clone with gh (authenticates automatically)
gh repo clone taqat-techno/khairgate
gh repo clone taqat-techno/relief-center odoo19/projects/relief_center

# Create repo for new project
gh repo create taqat-techno/new-project --private --description "New Odoo project"

# List all org repos
gh repo list taqat-techno --limit 50

# View repo info
gh repo view taqat-techno/khairgate
```

### Pull Request Workflow
```bash
# Create PR with template
gh pr create --title "feat: [AB#XXXX] Feature description" --body-file .github/PULL_REQUEST_TEMPLATE.md

# List open PRs
gh pr list --state open

# View PR details
gh pr view 42

# Review PR
gh pr review 42 --approve
gh pr review 42 --request-changes --body "Please fix the access rules"

# Merge PR
gh pr merge 42 --squash --delete-branch

# Check PR status (CI)
gh pr checks 42

# Create PR from current branch linking to work item
BRANCH=$(git branch --show-current)
WORK_ITEM=$(echo $BRANCH | grep -oP 'AB#?\K\d+')
gh pr create --title "feat: [AB#${WORK_ITEM}] $(git log -1 --pretty=%s)" --body "Resolves AB#${WORK_ITEM}"
```

### Issue Operations
```bash
# List issues
gh issue list --assignee "@me"
gh issue list --label "bug" --state open

# Create issue (linked to DevOps bug)
gh issue create \
  --title "[Bug] Module installation fails on Odoo 19" \
  --body "Linked to AB#1234" \
  --label "bug"

# Close issue
gh issue close 15 --comment "Fixed in PR #42"
```

### Workflow / Actions
```bash
# List workflows
gh workflow list

# Run a workflow manually
gh workflow run "deploy-to-staging.yml" --field module=disaster

# View workflow runs
gh run list --workflow="ci.yml" --limit 10

# Watch a running workflow
gh run watch 12345
```

---

## Branching Conventions for Azure DevOps + GitHub

```bash
# Feature branch (linked to work item)
git checkout -b feature/AB1234-payment-gateway

# Bug fix branch
git checkout -b fix/AB1235-invoice-generation-error

# Release branch
git checkout -b release/v17.1.0

# Hotfix
git checkout -b hotfix/AB1236-critical-settlement-bug
```

**Naming pattern**: `type/AB{workitem_id}-short-description`

---

## Syncing DevOps Work Items with GitHub PR Status

### PowerShell: Update Work Item to "In Review" when PR opens
```powershell
# After creating PR, update Azure DevOps work item state
$PR_URL = gh pr view --json url --jq .url
$WORK_ITEM_ID = "1234"  # Extract from branch name

az boards work-item update `
    --id $WORK_ITEM_ID `
    --state "In Review" `
    --discussion "PR opened: $PR_URL"
```

### Bash: Auto-link PR to work item from branch name
```bash
#!/bin/bash
# .githooks/post-checkout or run after gh pr create

BRANCH=$(git branch --show-current)
WORK_ITEM=$(echo "$BRANCH" | grep -oP '(?<=AB)\d+')

if [ -n "$WORK_ITEM" ]; then
    PR_URL=$(gh pr view --json url --jq .url 2>/dev/null)
    if [ -n "$PR_URL" ]; then
        az boards work-item update \
            --id "$WORK_ITEM" \
            --state "In Review" \
            --discussion "GitHub PR: $PR_URL"
        echo "✓ Updated work item AB#$WORK_ITEM → In Review"
    fi
fi
```

---

## GitHub Actions + Azure DevOps Pipeline Integration

### Trigger Azure DevOps pipeline from GitHub Actions
```yaml
# .github/workflows/trigger-devops.yml
name: Trigger DevOps Pipeline
on:
  push:
    branches: [main]

jobs:
  trigger:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Azure DevOps Pipeline
        run: |
          curl -X POST \
            -H "Authorization: Basic $(echo -n :${{ secrets.AZURE_DEVOPS_PAT }} | base64)" \
            -H "Content-Type: application/json" \
            -d '{"resources": {"repositories": {"self": {"refName": "refs/heads/main"}}}}' \
            "https://dev.azure.com/YOUR-ORG/MyProject/_apis/pipelines/1/runs?api-version=6.0"
```

---

## Routing Guide: When to Use gh vs az devops

| Task | Tool | Reason |
|------|------|--------|
| Clone/push code | `gh` | Code lives on GitHub |
| Create PR | `gh pr create` | PR is a GitHub concept |
| Review code | `gh pr review` | GitHub inline review |
| Create work item | `az boards work-item create` | Tracking is in DevOps |
| Sprint planning | `az boards` / MCP | DevOps owns sprints |
| CI/CD pipelines | `az pipelines` | DevOps owns pipelines |
| View PR status | `gh pr checks` | GitHub hosts CI |
| Link PR to work item | Both | AB# in PR title (GitHub) + comment (DevOps) |

---

## GitHub Actions CI/CD Integration for Odoo Projects

### PR Status Badge in README

```markdown
![CI](https://github.com/YOUR-ORG/your-repo/actions/workflows/1-lint.yml/badge.svg)
![Tests](https://github.com/YOUR-ORG/your-repo/actions/workflows/2-test.yml/badge.svg)
```

### Require CI to Pass Before Merge

In GitHub repo → Settings → Branches → Branch protection rules → `main`:
- ✓ Require status checks to pass before merging
- Status checks to require: `Lint & Code Quality`, `Automated Tests`
- ✓ Require branches to be up to date before merging

### Trigger Azure DevOps Pipeline from GitHub Actions

```yaml
# .github/workflows/trigger-devops.yml
name: Trigger Azure DevOps Build
on:
  push:
    branches: [main]
jobs:
  trigger:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Azure DevOps Pipeline
        run: |
          curl -s -X POST \
            -H "Authorization: Basic $(echo -n :${{ secrets.AZURE_DEVOPS_PAT }} | base64)" \
            -H "Content-Type: application/json" \
            -d '{"resources": {"repositories": {"self": {"refName": "refs/heads/main"}}}}' \
            "https://dev.azure.com/YOUR-ORG/MyProject/_apis/pipelines/1/runs?api-version=6.0"
```

### Odoo-Specific Branch Naming for CI Triggers

```bash
# Feature branch linked to work item
git checkout -b feature/AB1234-payment-gateway

# Bug fix branch
git checkout -b fix/AB1235-invoice-generation-error

# Release branch (triggers production deploy)
git checkout -b release/v17.1.0  # Creates tag → triggers production pipeline

# Hotfix
git checkout -b hotfix/AB1236-critical-settlement-bug
```

### Auto-Update DevOps Work Item When GitHub Actions Completes

```yaml
# Add to end of deploy workflow
      - name: Update Azure DevOps Work Item
        if: success()
        run: |
          # Extract work item from branch name (AB#1234)
          WORK_ITEM=$(echo "${{ github.ref_name }}" | grep -oP '(?<=AB)\d+' || echo "")
          if [ -n "$WORK_ITEM" ]; then
            az boards work-item update \
              --id "$WORK_ITEM" \
              --state "Done" \
              --discussion "Deployed via GitHub Actions: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}" \
              --org https://dev.azure.com/YOUR-ORG
          fi
        env:
          AZURE_DEVOPS_EXT_PAT: ${{ secrets.AZURE_DEVOPS_PAT }}
```

### View GitHub Actions Status from CLI

```bash
# List recent CI runs
gh run list --workflow="1-lint.yml" --limit 10

# Watch a running workflow
gh run watch

# View failed run logs
gh run view --log-failed

# Re-run failed jobs only
gh run rerun --failed

# Check PR CI status
gh pr checks 42
```

---

*Part of devops-plugin v2.0 — YOUR-ORG*
