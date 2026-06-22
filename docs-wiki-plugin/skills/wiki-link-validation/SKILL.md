---
name: wiki-link-validation
description: Sweep the wiki for broken internal links, missing pages referenced by sidebar / Home, filename collisions (GitHub Wiki), wrong internal-link convention (e.g. .md extension on GitHub Wiki), broken section-anchor links, visible numeric prefixes, and orphan pages. Produces a severity-tagged findings table; never auto-fixes. Activates on any wiki audit and before any wiki push. On Azure DevOps wikis, validates by link RESOLUTION (not path-existence) — flags relative /dashed links to hyphen-titled pages even when the path exists, requires the page-ID URL form, and tracks page read-failures so it never reports 0-broken on a partially-loaded wiki.
version: 0.4.0
last_reviewed: 2026-06-22
owns:
  - broken-internal-link detection
  - resolution-based (not path-existence) verdict for Azure DevOps wikis
  - dashed-relative-on-hyphen-titled-page detection (azure-devops-wiki)
  - read-failure tracking / never-false-zero gate (no "0 findings" while any page failed to load)
  - stale-old-section reference scan (after any move/rename/delete)
  - tree-namespace duplicate-concept detection
  - missing-page-from-sidebar detection
  - filename-collision audit (GitHub Wiki flat-namespace)
  - internal-link convention check (no .md extension on GitHub Wiki; tree-paths on other flavours)
  - heading-anchor slug rules (how a GitHub Wiki heading becomes a #anchor) + broken-anchor detection
  - azure-devops-wiki anchor-slug algorithm + broken-anchor detection on Azure
  - visible-numeric-prefix scan
  - orphan-page detection (page exists but not linked from anywhere)
defers_to:
  - wiki-structure (the rules being validated come from there; owns the page-ID URL form plus hub/child/sidebar conventions — this skill validates, structure defines)
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

The audit performs eight scans, each producing its own findings rows. Scans 1–6 carry the existing GitHub/GitLab/MkDocs behaviour unchanged; Scans 7–8 and the fenced `azure-devops-wiki` sub-clauses are net-new.

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
3. For internal wiki links, verify the target RESOLVES. On flat/tree flavours where the link form matches the page path, existence is sufficient; on `azure-devops-wiki` existence is NOT sufficient — a relative /dashed link to a hyphen-titled page resolves to a space path and 404s, so require the page-ID URL form (or a genuine space-titled relative link) and confirm the `{pageId}` exists.

```
BROKEN LINK: wiki/Operations.md:42 → [On-Call](On-Call-SOP)
  Target page does not exist.
  Did you mean: On-Call (different casing) | Oncall (no hyphen) | OnCall (no hyphen, camelCase)
  Severity: MEDIUM
  Fix: update link OR create the missing page
```

#### Azure DevOps — validate by resolution, not path existence [azure-devops-wiki]

GitHub/GitLab/MkDocs resolution is exactly as above — leave it untouched. On `azure-devops-wiki` only:

The single most important lesson from a real session: a **path-existence audit FALSELY PASSED while the links were actually broken.** Azure stores hyphen-titled pages with literal-hyphen path segments, but resolves a relative markdown link `[text](/Dashed-Path)` as if the hyphens were spaces (`?pagePath=/Dashed Path`) → not found → 404, **even though the path exists in the API.** So "the path exists" proves nothing here.

The only two reliably resolvable internal forms on Azure are:

1. The **page-ID URL** `.../_wiki/wikis/{WikiName}/{pageId}/{Slug}` — this FORM is owned by `wiki-structure`; this skill validates against it (confirm the `{pageId}` resolves to a real page) but does not redefine it.
2. A **genuine space-titled relative link** (a plain dashed relative link resolves ONLY when the target page is actually space-titled).

Finding type **dashed-relative-on-hyphen-page** (severity HIGH): a relative /dashed link pointing at a hyphen-titled page.

```
DASHED-RELATIVE-ON-HYPHEN-PAGE: wiki/Workflows-Overview.md:57 → [Compose contract](/Records-Workspace-and-Correspondence)
  Flavour azure-devops-wiki; target page is hyphen-titled.
  Azure resolves the dashes as spaces (?pagePath=/Records Workspace and Correspondence) → 404, despite the API path existing.
  A path-existence check would FALSE-PASS this link.
  Severity: HIGH
  Fix: rewrite to the page-ID URL form .../Archiving-System.wiki/{pageId}/Records-Workspace-and-Correspondence
       (page-ID URL form owned by wiki-structure) OR convert the target to a genuine space title.
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

On tree-namespace flavours (`gitlab-wiki`, `azure-devops-wiki`, `mkdocs-tree`), also run a **duplicate-concept** check: two distinct pages (different paths) that represent the same concept or carry the same title. This is NOT the flat-namespace basename collision of Scan 1 — folders make distinct paths legal here, so the collision is conceptual, not URL-level. Surface only; never auto-merge (merging distinct source pages destroys content).

```
DUPLICATE-CONCEPT: Core-Records-and-Processing/Correspondence and Workflows-Overview/Correspondence-Journey
  Two distinct pages appear to represent the same concept ("Correspondence").
  Severity: MEDIUM
  Note: surface only — never auto-merge. Maintainer decides whether one is a journey view of the other (keep both) or a true duplicate (consolidate).
```

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

For non-GitHub flavours, the slug algorithm differs (GitLab keeps a similar scheme; MkDocs differs on punctuation and case). When the flavour's slug rule is declared, apply it and VALIDATE the anchor; report `UNKNOWN — slug rule not declared for <flavour>` ONLY for flavours that remain undeclared (e.g. `mkdocs-tree`). Do not guess.

#### Azure DevOps anchor-slug algorithm [azure-devops-wiki]

The `azure-devops-wiki` anchor-slug rule IS declared — validate Azure anchors with it instead of reporting UNKNOWN. Replicate it EXACTLY (a naive whitespace-collapse produced a FALSE anchor mismatch in a real session). Do not reuse the GitHub algorithm.

1. Lowercase every letter.
2. Drop every character not in `[a-z0-9]`, space, or hyphen.
3. Replace each space with a single hyphen — **NO whitespace collapse**: two spaces become two hyphens.
4. Trim leading and trailing hyphens from the final slug.

Worked examples (heading → anchor, Azure):

```
## Run the deploy             → run-the-deploy
## Compose  Contract          → compose--contract          (double space → two hyphens, NOT collapsed)
## Records & Correspondence   → records--correspondence     ("&" dropped → "Records " + " Correspondence" → two spaces → two hyphens)
```

The double-space example is the one that bites: a generator that collapses runs of whitespace would expect `compose-contract` and report a false mismatch against the real `compose--contract`.

### Scan 7 — Stale old-section / deleted-section references (all flavours)

Run after any page move, rename, or delete. A move re-paths a page (and all its descendants); a delete removes a section slug — but inbound references to the OLD path/slug do not vanish on their own.

1. Inventory every pre-move path segment and every deleted-section slug (from the move/delete plan).
2. Scan all pages — plus sidebar / Home / index pages — for any surviving occurrence of those old paths/slugs.
3. Confirm ZERO remain. One finding per surviving stale reference.

This scan is **detection only**: it confirms whether stale references remain. The repointing of those references is `wiki-safe-updates`' job — defer the fix to it. On `azure-devops-wiki` the scan is **mandatory** after any move/rename/delete, because Azure NEVER auto-repoints inbound links.

```
STALE REFERENCE: wiki/Home.md:22 → [Business rules](/Business-Source-of-Truth/Business-Rules)
  "Business-Source-of-Truth" was deleted/renamed to "Rules-Audit-and-Governance" during the IA restructure.
  Severity: MEDIUM
  Fix (defer to wiki-safe-updates): repoint to the new path/page-ID URL.
```

### Scan 8 — Reachability, backlinks, sidebar/nav order (all flavours)

Confirms the navigation graph is sound after any restructure:

1. **Reachability** — every child page is reachable FROM its hub (the hub links to it, or the tree nests it).
2. **Backlink** — every child carries an explicit backlink to its hub ("Part of <hub>" link). Tree nesting ALONE is insufficient — an explicit backlink is required.
3. **Workflow coverage** — every workflow journey page is linked from the workflow index.
4. **Single master swimlane** — the master swimlane appears exactly once (on the workflow hub), never duplicated onto a child.
5. **Order** — sidebar / nav order (top-level and per-hub) matches the intended reading order.

This scan is **detection only**. The reachability / backlink / hub conventions themselves are defined by `wiki-structure`; the fixes go through `wiki-safe-updates`. This skill reports the gaps; it does not invent the conventions or apply the repairs.

```
MISSING BACKLINK: Core-Records-and-Processing/OCR-Search-and-Document-Processing
  Page is reachable from its hub but carries no explicit "Part of Core-Records-and-Processing" backlink.
  Severity: MEDIUM
  Fix (defer to wiki-safe-updates): add the hub backlink (convention owned by wiki-structure).

NAV ORDER: Workflows-Overview index lists journey pages out of reading order.
  Severity: LOW
  Fix (defer to wiki-safe-updates): reorder via .order / pagemoves newOrder to match the intended sequence.
```

## Decision framework

| Finding type | Default severity | Auto-fixable? |
|---|---|---|
| Filename collision (GitHub Wiki) | HIGH | No — requires rename + cross-reference update |
| Dashed-relative-on-hyphen-page (azure-devops-wiki) | HIGH | No — needs rewrite to the page-ID URL form (or genuine space title) |
| Broken internal link | MEDIUM | No — needs maintainer judgement (rename target? update link? create missing page?) |
| Broken section anchor | MEDIUM | No — needs maintainer judgement (was the heading renamed? is the fragment a typo?) |
| Stale old-section / deleted-section reference | MEDIUM | No — defer repoint to wiki-safe-updates |
| Duplicate-concept (tree-namespace) | MEDIUM | Never — never auto-merge distinct source pages |
| Missing backlink / reachability gap | MEDIUM | No — defer fix to wiki-safe-updates |
| Internal-link convention violation (GitHub Wiki) | MEDIUM | Sometimes — link convention fixes are mechanical but the audit still reports rather than fixing silently |
| Visible numeric prefix | MEDIUM | No — rename has cascading impact |
| Orphan page | LOW | Never — orphan may be intentional |
| Nav / sidebar order mismatch | LOW | No — defer reorder to wiki-safe-updates |

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
  Scans run: collisions, broken-links, convention, numeric-prefix, orphans, anchors, stale-references, reachability
  Pages read OK: <count> / Pages failed to load: <count>   (if any failed, "0 broken" is NOT a valid verdict)

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
- **Never** report "0 broken" (or any "0 findings") if any page failed to load. Track read-failures explicitly as a distinct blocking line in the output; a verdict is only valid once every page was read.
- **Never**, on `azure-devops-wiki`, pass a relative /dashed link to a hyphen-titled page on the grounds "the path exists" — it 404s in the browser even though the API path resolves.

## Validation checklist

Before reporting the audit:

- [ ] All eight scans ran.
- [ ] Per-scan finding counts surfaced.
- [ ] HIGH findings listed at top.
- [ ] Internal links verified by RESOLUTION on `azure-devops-wiki` (page-ID URL form, or genuine space-titled relative link) — not by path-existence.
- [ ] 0 stale old-section / deleted-section references confirmed after any move/rename/delete.
- [ ] Read-failures listed explicitly; no "0 findings" verdict declared while any page failed to load.
- [ ] Reachability + explicit hub backlink confirmed for every child (tree nesting alone is insufficient).
- [ ] No duplicate-concept pages on tree-namespace flavours (surfaced, not merged).
- [ ] On `azure-devops-wiki`, anchor slugs derived by the Azure algorithm (lowercase, drop non-`[a-z0-9 -]`, spaces→hyphens uncollapsed, trim outer hyphens) — not the GitHub rule and not whitespace-collapsed.
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
| Pass an Azure link because "the path exists" | Azure resolves dashed relatives as spaces → 404 in the browser while the API path resolves | Validate by RESOLUTION; require the page-ID URL form (or a genuine space title) |
| Report "0 broken" after read-failures | A page that never loaded can hide every broken link it contains | Track read-failures explicitly; never declare 0 until all pages read |
| Reuse the GitHub slug rule or collapse spaces on Azure | Azure has its own algorithm and does NOT collapse whitespace; collapsing produces false mismatches | Apply the Azure algorithm exactly: two spaces → two hyphens |
| Skip the stale-reference scan after a move/rename/delete | Azure never auto-repoints; old paths silently linger and 404 | Run Scan 7 every time; confirm zero stale references remain |
| Delete the `_archived/` folder because "orphan pages" | The folder is the archive — deleting it loses history | Respect explicit archive folders |

## Portability rationale

The audit logic adapts per wiki flavour. The skill does not depend on:

- A specific markdown parser (regex over markdown for `[label](target)` is sufficient)
- A specific git tooling
- A specific report sink (the maintainer reads the table)

## Cross-references

- `wiki-structure` — the rules being validated.
- `wiki-structure` — owns the Azure page-ID URL form and the hyphen-title vs space-title resolution facts; this skill validates against that form.
- `wiki-safe-updates` — the workflow for applying fixes.
- `wiki-link-auditor` (agent) — automates this audit.
- `wiki-code-vs-docs-discrepancy` — applied when a broken link reflects a code change.
- `/wiki-audit` (command) — runs this skill.
