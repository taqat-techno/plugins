---
description: Sweep for code-vs-wiki discrepancies. For each wiki page in scope, check its claims against the source-of-truth roots (typically src/, services/, schema files, CI workflows). Produces a discrepancy table classified as doc-drift / code-drift / intentional gap / unknown. NEVER auto-resolves; the user picks each direction.
argument-hint: "[<wiki-path>] [--page <name>] [--roots path1,path2,...] [--out path]"
author: TAQAT Editorial
version: 0.2.0
allowed-tools: Read, Glob, Grep, Bash, Write
---

# /wiki-drift

You are running a code-vs-wiki discrepancy sweep. Apply `wiki-code-vs-docs-discrepancy` for the never-silently-choose rule and classification vocabulary.

This command READS both sides and reports contradictions. It does NOT pick winners and does NOT edit either side.

## Step 0 — Resolve scope

- `<wiki-path>` from arg or adapter cache.
- Source-of-truth roots from `--roots` or adapter cache `sourceOfTruthRoots`.

If no source-of-truth roots configured:

```
DRIFT SWEEP REQUIRES SOURCE-OF-TRUTH ROOTS

The wiki cannot be compared to code without knowing which folders authoritatively
describe runtime behavior. Typical answer: src/, services/, prisma/schema.prisma,
.github/workflows/, the main route handlers folder.

Configure via /wiki-init or by editing .docs-wiki.local.json:
  "sourceOfTruthRoots": ["src/", "services/", ...]

Then re-run /wiki-drift.
```

If `--page <name>`: sweep only that page. Otherwise: sweep every wiki page.

## Step 1 — Build the comparison set

For each wiki page in scope:

1. Read the page; extract claims that look behavior-asserting (lines mentioning paths, function names, endpoint paths, role names, permissions, deploy steps, configuration keys, schema fields).
2. For each claim, identify the source-of-truth root most likely to contain the actual implementation (heuristic; the user confirms).

Build the comparison set as `[(wiki-claim, code-location)]` tuples.

## Step 2 — Read the code side

For each `code-location`:

1. Read the file(s) at that location.
2. Extract the actual current behavior (the function signature, the role check, the endpoint definition, the schema field, the workflow step).

## Step 3 — Classify per `wiki-code-vs-docs-discrepancy`

For each tuple:

| Outcome | Class |
|---|---|
| Wiki and code agree | (omit from report — no discrepancy) |
| Wiki claims X; code does Y; code is more recently modified than wiki | proposed: doc-drift |
| Wiki claims X; code does Y; wiki is more recently modified than code | proposed: code-drift |
| Wiki says "X (planned)" or "X (target state)"; code does not yet do X | proposed: intentional gap |
| Insufficient evidence (e.g., the wiki claim is too vague to verify) | proposed: unknown |

## Step 4 — Produce the report

Per the `wiki-code-vs-docs-discrepancy` block format, one block per discrepancy:

```
DISCREPANCY 1
  Topic: deploy procedure
  Wiki claim (Deploy-SOP.md:42, last modified 2025-09-14):
    "Run ./deploy.sh from the build server."
  Code reality (.github/workflows/deploy.yml:88, last modified 2026-04-22):
    "uses: ./.github/actions/deploy@v3"
    (deploy.sh removed in commit abc123 on 2026-04-22; CI workflow replaced it)
  Classification (proposed): doc-drift
  Reasoning: CI workflow shows deploy moved from manual deploy.sh to GitHub Actions
  in 2026-04; wiki SOP was not updated.

  Direction (NOT applied):
    A) Update Deploy-SOP.md to describe the GitHub Actions flow.
    B) Restore deploy.sh and revert the workflow change.
    C) Annotate Deploy-SOP.md as "historical; superseded by GitHub Actions".

  Recommended (proposed; user decides): A
```

Group discrepancies by classification in the summary:

```
WIKI DRIFT SWEEP — <wiki-path> — <date>
  Pages swept: <count>
  Code roots: <list>
  Total discrepancies: <count>

CLASSIFICATION SUMMARY
  doc-drift (wiki out of date):       <count>
  code-drift (code out of policy):    <count>
  intentional gap (target state):     <count>
  unknown (insufficient evidence):    <count>

DISCREPANCIES (per-block detail follows)
  ...
```

## Step 5 — Output

Print the summary inline. Write the full per-block report to:

```
<wiki-path>/_drift/<YYYY-MM-DD>.md
```

OR `--out <path>` to override.

Suggest next steps:

- For each block, the user picks a direction (A / B / C / D — investigate).
- The plugin DOES NOT apply directions automatically. Wiki updates go through `/wiki-update`; code changes are outside the plugin's scope.

## Safety

- Read-only.
- Does NOT silently classify (every block surfaces the evidence + reasoning).
- Does NOT silently apply a direction.
- Does NOT include unredacted PII / secrets from either the wiki or code in the report (scan + redact).
- Respects retired folders (wiki-side) and project ignores (code-side).
- Does NOT call external services.

## Modes

- `--page <name>` — sweep only one wiki page.
- `--roots path1,path2,...` — override the source-of-truth roots for this run.
- `--out <path>` — write the full report to a specific path.

## What NOT to do

- Do NOT pick a side automatically — even when the answer "feels obvious".
- Do NOT update the wiki to match the code on the audit's say-so.
- Do NOT update the code to match the wiki on the audit's say-so.
- Do NOT report a discrepancy when both sides simply use different terms for the same concept (stylistic, not behavioral).
- Do NOT report retired-folder pages as drift.
