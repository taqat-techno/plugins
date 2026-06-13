---
name: wiki-link-validation
description: Sweep the wiki for broken internal links, missing pages referenced by sidebar / Home, filename collisions (GitHub Wiki), wrong internal-link convention (e.g. .md extension on GitHub Wiki), broken section-anchor links, visible numeric prefixes, and orphan pages. Produces a severity-tagged findings table; never auto-fixes. Activates on any wiki audit and before any wiki push.
version: 0.3.0
last_reviewed: 2026-06-13
owns:
  - broken-internal-link detection
  - missing-page-from-sidebar detection
  - filename-collision audit (GitHub Wiki flat-namespace)
  - internal-link convention check (no .md extension on GitHub Wiki; tree-paths on other flavours)
  - heading-anchor slug rules (how a GitHub Wiki heading becomes a #anchor) + broken-anchor detection
  - visible-numeric-prefix scan
  - orphan-page detection (page exists but not linked from anywhere)
defers_to:
  - wiki-structure (the rules being validated come from there)
  - wiki-safe-updates (any fix goes through that workflow)
  - wiki-link-auditor (agent) (this skill describes the workflow; the agent runs it)
user_invocable: false
---

# wiki-link-validation

## Purpose

A wiki with broken links is worse than a wiki with no links. Readers learn to distrust the navigation; the wiki stops being a usable surface. This skill catches the four common rot patterns — broken links, missing pages, filename collisions, and visible numeric prefixes — and surfaces them in a findings table the maintainer can act on.

This skill describes the audit. The `wiki-link-auditor` agent automates it.

## When to use

Activate when:

- Running `/wiki-audit`.
- Before any wiki push (a pre-push check catches drift early).
- After a wiki rename (the rename invalidates inbound links).
- On a periodic schedule (weekly / monthly) to catch slow rot.
- Investigating a "the wiki is broken" complaint.

Skip when:

- The wiki repo is empty (nothing to validate).
- The wiki is mid-migration to a different flavour (run after migration completes).

## Inputs

- Wiki repo path (from adapter cache or `/wiki-init`).
- Wiki flavour (from adapter cache; default `github-wiki`).
- Optional: the project's retired-folder list (folders deliberately archived — see `wiki-vs-stray-docs`).

## Read-only investigation steps

The audit performs six scans, each producing its own findings rows.

### Scan 1 — Filename collisions (GitHub Wiki only)

1. Enumerate every `.md` file in the wiki repo (recursively).
2. Group by basename (lowercase, with spaces normalised to hyphens — match the GitHub Wiki URL slug).
3. Any group with 2+ files is a collision.

```
COLLISION: basename "deploy"
  Files:
    sop/deploy.md          (last modified 2025-08-12)
    runbooks/deploy.md     (last modified 2026-02-04)
  Effect on GitHub Wiki: only one URL https://github.com/<OWNER>/<REPO>/wiki/Deploy
  Severity: HIGH
  Fix: rename to disambiguating filenames (Deploy-SOP.md + Deploy-Runbook.md)
```

### Scan 2 — Broken internal links

1. Enumerate every Markdown link in every `.md` file.
2. For each link target, classify:
   - **Internal wiki link**: resolves to a basename in the wiki (GitHub Wiki) OR a wiki-relative path (other flavours).
   - **External link** (`http://`, `https://`, `mailto:`): not validated by this skill (use a third-party link checker if needed).
   - **Code-repo link**: pointing into the main repo (`../<repo>/path`). Validate the path exists if the main repo is accessible.
3. For internal wiki links, verify the target page exists.

```
BROKEN LINK: wiki/Operations.md:42 → [On-Call](On-Call-SOP)
  Target page does not exist.
  Did you mean: On-Call (different casing) | Oncall (no hyphen) | OnCall (no hyphen, camelCase)
  Severity: MEDIUM
  Fix: update link OR create the missing page
```

### Scan 3 — Internal-link convention violations

Per `wiki-structure`'s convention rules, by flavour:

For `github-wiki`:

- Links MUST NOT include `.md` extension.
- Links MUST NOT include folder paths.
- Links to anchored sections use `#section-name` (lowercase, hyphenated, no `.md`).

```
CONVENTION VIOLATION: wiki/Home.md:14 → [Deploy](sop/deploy.md)
  GitHub Wiki link uses folder path + .md extension; will 404.
  Severity: MEDIUM
  Fix: change to [Deploy](Deploy-SOP) (after rename for collision resolution)
```

For `gitlab-wiki`, `azure-devops-wiki`, `mkdocs-tree`: folder paths and `.md` extensions are valid per platform; flag only when the link is genuinely broken (Scan 2).

### Scan 4 — Visible numeric prefixes

Per `wiki-structure`'s no-numeric-prefix-in-visible-labels rule:

1. Scan filenames for `NN-` or `NNN-` prefixes (`01-Home.md`, `02-Deploy.md`).
2. Scan sidebar and Home for visible numeric prefixes in link labels.

```
NUMERIC PREFIX: filename "02-Deploy.md"
  URL becomes "02-Deploy" (numeric prefix in URL)
  Sidebar label becomes "02 Deploy" by default
  Severity: MEDIUM
  Fix: rename to Deploy.md OR Deploy-SOP.md; update sidebar order to use prose order, not numbers
```

### Scan 5 — Orphan pages

1. Enumerate every wiki page.
2. Build the inbound-link graph by scanning every page for links.
3. Pages with zero inbound links AND not the Home page AND not referenced in `_Sidebar.md` are orphans.

```
ORPHAN: wiki/Old-Architecture-Plan.md
  Last modified: 2024-11-10
  Inbound links: 0
  In sidebar: no
  Severity: LOW
  Likely cause: superseded by Architecture.md; stale draft
  Fix: confirm with maintainer — either link from somewhere OR archive (move to wiki/_archived/)
```

Orphan severity is LOW because orphans are sometimes intentional (drafts, work-in-progress). The audit surfaces; the maintainer decides.

### Scan 6 — Broken section-anchor links

A link like `[Steps](Deploy-SOP#run-the-deploy)` points at a heading *inside* a page. The page can exist while the anchor does not — a renamed heading silently breaks every inbound `#anchor` link, and the link still resolves to the page so Scan 2 misses it. This scan validates the fragment.

To validate an anchor you must first know how the platform turns a heading into a slug. The GitHub Wiki (and GitHub-flavoured Markdown generally) slug rules are deterministic:

1. Take the heading text (the rendered text, after stripping Markdown like `**bold**` or backticks).
2. Lowercase every letter (`A-Z` → `a-z`).
3. Drop every character that is **not** `a-z`, `0-9`, space, or hyphen. (Punctuation — `.,:;!?()[]{}'"/\@#&` etc. — is removed, not replaced.)
4. Replace each remaining space with a single hyphen. Spaces are **not** collapsed first: two spaces become two hyphens.
5. Trim leading and trailing hyphens from the final slug. **Internal** multi-hyphen runs are preserved.
6. If two headings on the same page produce the same slug, the second gets `-1`, the third `-2`, and so on (the de-duplication suffix).

Worked examples (heading → anchor):

```
## Run the deploy            → run-the-deploy
## Step 2: Verify (health)   → step-2-verify-health        (":" and "()" dropped, not hyphenated)
## CI / CD pipeline          → ci--cd-pipeline             (space-/-space → three chars → hyphen, dropped /, hyphen → "--")
## -- internal note --       → internal-note               (leading/trailing hyphens trimmed; internal "--" kept)
## FAQ                       → faq
## FAQ                       → faq-1                        (second identical heading → -1 suffix)
```

The two rules that trip people up most:

- **Punctuation is dropped, not replaced.** `Verify (health)` becomes `verify-health`, NOT `verify--health-` and NOT `verify-health-`. Only spaces become hyphens.
- **Leading/trailing hyphens are trimmed; internal multi-hyphens are kept.** A link anchor must never *start* with a hyphen — `#-run-the-deploy` will never match any heading because the leading hyphen is trimmed off the heading's slug. `#ci--cd-pipeline` (internal `--`) is legitimate.

Validation procedure:

1. For each link with a `#fragment`, resolve the target page (same page if the link is `#fragment` only; another page for `Page#fragment`).
2. If the target page is missing, that is a Scan 2 broken-link finding (not this scan).
3. Build the set of valid anchors for the target page by applying the slug rules above to every heading, including the de-dup suffixes.
4. If the link's fragment is not in that set, it is a broken anchor.

```
BROKEN ANCHOR: wiki/Operations.md:88 → [Steps](Deploy-SOP#run-the-deploy)
  Target page Deploy-SOP exists; anchor "run-the-deploy" not found.
  Page headings produce anchors: deploy-overview, run-the-deployment, verification
  Did you mean: #run-the-deployment (heading "Run the deployment" was renamed)
  Severity: MEDIUM
  Fix: update the fragment to #run-the-deployment OR restore the heading text

ANCHOR STARTS WITH HYPHEN: wiki/Home.md:31 → [Notes](Guide#-internal-note)
  A heading slug never starts with a hyphen (leading hyphens are trimmed).
  The matching heading "-- internal note --" produces anchor "internal-note".
  Severity: MEDIUM
  Fix: change fragment to #internal-note
```

For non-GitHub flavours, the slug algorithm differs (GitLab keeps a similar scheme; Azure DevOps and MkDocs differ on punctuation and case). When the flavour is not `github-wiki`, apply the adapter's slug rule if declared; otherwise report anchors as `UNKNOWN — slug rule not declared for <flavour>` rather than guessing.

## Decision framework

| Finding type | Default severity | Auto-fixable? |
|---|---|---|
| Filename collision (GitHub Wiki) | HIGH | No — requires rename + cross-reference update |
| Broken internal link | MEDIUM | No — needs maintainer judgement (rename target? update link? create missing page?) |
| Broken section anchor | MEDIUM | No — needs maintainer judgement (was the heading renamed? is the fragment a typo?) |
| Internal-link convention violation (GitHub Wiki) | MEDIUM | Sometimes — link convention fixes are mechanical but the audit still reports rather than fixing silently |
| Visible numeric prefix | MEDIUM | No — rename has cascading impact |
| Orphan page | LOW | Never — orphan may be intentional |

The audit NEVER auto-fixes. The maintainer reads the findings and decides.

## Suggesting fixes (without applying them)

For each finding, the audit may suggest a fix:

```
BROKEN LINK: ... → [Deploy](Deploy-SOP)
  Target does not exist.
  Suggested fix: target page found at Deploy-Runbook.md — did you mean [Deploy](Deploy-Runbook)?
```

Fuzzy match strategy:

- Levenshtein distance ≤ 3 from existing page basename.
- Plural / singular variant.
- Casing variant (`OnCall` ↔ `On-Call`).
- Common synonym (`Oncall` ↔ `On-Call`).

Report the suggestion but DO NOT apply. The maintainer confirms.

## Output format

```
WIKI LINK VALIDATION — <wiki-path> — <date>
  Flavour: github-wiki
  Pages: <count>
  Scans run: collisions, broken-links, convention, anchors, numeric-prefix, orphans

SCAN RESULTS

Collisions (HIGH severity)
| ID | Basename | Files | Fix |
|----|----------|-------|-----|
| C-1 | deploy | sop/deploy.md, runbooks/deploy.md | rename one |

Broken Internal Links (MEDIUM severity)
| ID | Source | Target | Suggested fix |
|----|--------|--------|---------------|
| B-1 | Home.md:14 | Deploy (does not exist) | Did you mean Deploy-SOP? |

Convention Violations (MEDIUM severity)
| ID | Source | Issue | Fix |
|----|--------|-------|-----|
| V-1 | Home.md:14 | uses .md extension + folder path | rewrite per flavour |

Broken Section Anchors (MEDIUM severity)
| ID | Source | Target#fragment | Suggested fix |
|----|--------|-----------------|---------------|
| A-1 | Operations.md:88 | Deploy-SOP#run-the-deploy | #run-the-deployment |

Numeric Prefixes (MEDIUM severity)
| ID | Item | Issue | Fix |
|----|------|-------|-----|
| N-1 | 02-Deploy.md | numeric prefix in URL slug | rename without prefix |

Orphan Pages (LOW severity)
| ID | Page | Last modified | Note |
|----|------|---------------|------|
| O-1 | Old-Architecture-Plan.md | 2024-11-10 | possibly superseded |

SUMMARY
  HIGH: <count> — listed first; block push until resolved
  MEDIUM: <count>
  LOW: <count>
  Recommended order of fixes: <ID-1, ID-2, ...>
```

## Safety gates

- **Never** auto-fix any finding.
- **Never** flag external links as broken (third-party tooling required for that).
- **Never** delete an "orphan" page on the audit's say-so; orphans are sometimes intentional.
- **Never** rename a page without surfacing every inbound link that needs updating.
- **Never** treat a fuzzy-match suggestion as a fix — it is a hint for the maintainer.
- **Never** run against a wiki path that is not in the adapter cache or explicitly provided.

## Validation checklist

Before reporting the audit:

- [ ] All six scans ran.
- [ ] Per-scan finding counts surfaced.
- [ ] HIGH findings listed at top.
- [ ] Anchor slugs were derived by the documented rule (drop punctuation, spaces→hyphens uncollapsed, trim outer hyphens) — not guessed.
- [ ] No reported anchor fragment starts with a hyphen unless the maintainer is shown why it can never match.
- [ ] Fuzzy-match suggestions are tagged as suggestions, not fixes.
- [ ] Orphan section explicitly notes "orphan may be intentional".
- [ ] No PII / secrets visible in any quoted line.
- [ ] No file outside the wiki repo audited.

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Auto-fix broken links by Levenshtein-matching to existing pages | Suggestions are sometimes wrong; auto-fix erases intent | Suggest only; let maintainer apply |
| Treat every orphan as a delete candidate | Drafts and intentional archives count | Surface; maintainer decides |
| Skip the collision scan because "we use folders" | Folders silently overwrite on GitHub Wiki | Audit anyway; surface |
| Validate external links by hitting them | Flaky; rate-limited; out-of-scope | External link checker is a separate tool |
| Report `.md` extension as a violation on a GitLab wiki | GitLab supports `.md` in links | Adapter-aware |
| Build an anchor by hyphenating punctuation (`verify-(health)` → `verify--health-`) | GitHub drops punctuation; it never becomes a hyphen | Drop non-`[a-z0-9 -]`; only spaces become hyphens |
| Collapse double spaces before slugging | GitHub maps each space to its own hyphen | Two spaces → two hyphens; trim only the outer ones |
| Author a link anchor that starts with a hyphen (`#-notes`) | The heading's leading hyphen is trimmed, so it can never match | Trim outer hyphens from the expected slug; never lead with `-` |
| Delete the `_archived/` folder because "orphan pages" | The folder is the archive — deleting it loses history | Respect explicit archive folders |

## Portability rationale

The audit logic adapts per wiki flavour. The skill does not depend on:

- A specific markdown parser (regex over markdown for `[label](target)` is sufficient)
- A specific git tooling
- A specific report sink (the maintainer reads the table)

## Cross-references

- `wiki-structure` — the rules being validated.
- `wiki-safe-updates` — the workflow for applying fixes.
- `wiki-link-auditor` (agent) — automates this audit.
- `wiki-code-vs-docs-discrepancy` — applied when a broken link reflects a code change.
- `/wiki-audit` (command) — runs this skill.
