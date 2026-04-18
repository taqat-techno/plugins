---
name: ragtools-release
description: Maintainer-facing release-lifecycle checklist for the upstream ragtools product. Activates on maintainer release phrasing — "pre-release check", "release checklist", "ready to ship ragtools", "v2.5.x pre-flight", "verify release invariants", "release go/no-go", "RELEASE_LIFECYCLE", "ragtools release audit", "about to tag ragtools", "cutting a ragtools release". Walks the six permanent release invariants (data/install-dir boundary, schema versioning, dev-mode isolation, upgrade-path manual test, uninstall opt-in prompt, RELEASE_LIFECYCLE.md accuracy) with structured ack or hold per item. Never ships or promotes a release itself — pure gating and documentation. Separate from the operator-facing ragtools-ops skill.
version: 0.1.0
---

# ragtools-release

Maintainer-facing release-lifecycle checklist for the upstream **ragtools** product. When a new ragtools version is about to ship, this skill walks the six permanent release invariants one at a time, gathers an explicit ack or hold from the maintainer on each, and summarizes the release state (green / blocked / ship-with-flags).

This is a **gating** skill, not a doing skill. It does not build, tag, upload, publish, or promote a release. It enforces the checklist before any of those actions happen.

## When the skill activates

On maintainer-release phrasing:
- "pre-release check", "release checklist"
- "ready to ship ragtools", "v2.5.x pre-flight"
- "verify release invariants", "release go/no-go"
- "RELEASE_LIFECYCLE"
- "ragtools release audit"
- "about to tag ragtools", "cutting a ragtools release"

Not on operator-facing phrasing like "why isn't my file indexed" or "diagnose ragtools" — those belong to `ragtools-ops`.

## The six permanent invariants

Loaded from `references/release-checklist.md`. Every ragtools release must pass all six, or ship with the specific flags indicated. Supersede only by an explicit ADR in `docs/RELEASE_LIFECYCLE.md` in the upstream product.

| # | Invariant | Source-of-truth file in upstream |
|---|---|---|
| 1 | No new code path writes user data into the install directory | `src/ragtools/config.py` (`get_config_write_path()`) + installer scripts |
| 2 | Any schema change bumped its version AND ships a migration step | `src/ragtools/config.py` (`CONFIG_VERSION`), `src/ragtools/state/schema.py` (`PRAGMA user_version`), `src/ragtools/embed/*` (encoder dim) |
| 3 | Dev-mode startup does not touch `%LOCALAPPDATA%\RAGTools\` or register a Startup task | `run.py` (`is_packaged()` guard) |
| 4 | Installer manually tested on a machine that already has the previous version installed — upgrade path preserves user data | Manual — downloaded installer vs fresh VM |
| 5 | Uninstall manually tested with opt-in prompt (YES full wipe / NO keep data) — both paths correct | Inno Setup `[UninstallRun]` + installer script |
| 6 | `docs/RELEASE_LIFECYCLE.md` still accurate for this version | Upstream product repo |

## Phase 1 — Ground the release

Before walking the checklist, gather structured context from the maintainer. Ask, one at a time:

1. **Version being verified.** `vX.Y.Z` (e.g. `v2.5.1`).
2. **Previous version on disk.** If this is an upgrade path (e.g. `v2.5.0 → v2.5.1`), capture it.
3. **Change class for this release.** Patch (bug fixes only) / minor (new capability, backward-compatible) / major (breaking). Match against the changes actually present per the upstream CHANGELOG.
4. **Schema-touching changes?** Quick yes/no — config, state DB, Qdrant collection, encoder output dim. Any yes → item 2 becomes load-bearing.
5. **Installer-touching changes?** Quick yes/no — Inno Setup script, `ForceKillRagProcesses`, upgrade routine. Any yes → items 1 + 4 become load-bearing.
6. **Any user-data boundary changes?** New files written, new directories touched. Any yes → item 1 becomes load-bearing.

Record the answers. They are the input to Phase 2.

## Phase 2 — Walk the six invariants

For each of the six items, present:

```
Invariant N — <title>

What the invariant means:
  <plain-English statement of the rule>

Source of truth in upstream:
  <file path + what to look for>

What changed in this release:
  <one-line summary, derived from Phase 1 + the upstream CHANGELOG>

Claude's pre-check (heuristic):
  <pass | uncertain | fail> — <one-line rationale>

Your ack?
  Options: yes | no, block | conditional (explain)
```

### Per-item pre-check heuristics

**Invariant 1 (no user data into install dir):**
- If Phase 1 reported "no user-data boundary changes" → pre-check = PASS.
- If any new file-write path was added → pre-check = UNCERTAIN; maintainer must confirm it targets `get_config_write_path()` or an equivalent persistent-user-data path, never `{app}\`.
- Ask the maintainer to name the new writer files if uncertain.

**Invariant 2 (schema version + migration):**
- If Phase 1 reported "no schema-touching changes" → pre-check = PASS (no change needed).
- If yes → pre-check = UNCERTAIN; maintainer must confirm each changed schema bumped its version constant AND shipped a migration step (forward-only is fine; reverse migrations are optional).

**Invariant 3 (dev-mode isolation):**
- Always ask: "Does the release change `is_packaged()` or any of its callers in `run.py`?"
- If no → pre-check = PASS.
- If yes → pre-check = UNCERTAIN; maintainer must confirm dev-mode still does not touch `%LOCALAPPDATA%\RAGTools\` or register a Startup task.

**Invariant 4 (upgrade-path manual test):**
- This is **always manual**. Pre-check is always UNCERTAIN at minimum, because the built installer has not yet been exercised on the target upgrade path until the maintainer does so.
- **Two acceptable acks:**
  - `yes, will manually test before promote` → skill recommends **ship as pre-release**, do not promote to latest until the installer has been exercised on a `<previous> → <current>` machine.
  - `yes, already tested` → skill asks for the test evidence (machine name, install date, outcome) to record in the release ack log.
- Any other answer → block.

**Invariant 5 (uninstall manually tested):**
- If Phase 1 reported "no installer-touching changes" → pre-check = PASS (same code path as the previous validated release).
- If installer touched the uninstall path → pre-check = UNCERTAIN; maintainer must exercise both uninstall branches (full wipe / keep data).

**Invariant 6 (RELEASE_LIFECYCLE.md accurate):**
- If Phase 1 reported no boundary changes AND no new platforms/artifact types → pre-check = PASS.
- If new platforms shipped (e.g. Linux arm) → pre-check = UNCERTAIN; maintainer must confirm the boundary model in the doc covers the new platform.

## Phase 3 — Summarize

After all six items have an ack (or a block), produce a compact release-gate summary:

```
Release gate: ragtools v<X.Y.Z>
  Previous version: v<X.Y.Z-prev>
  Change class:     patch | minor | major

  Invariant 1 (data/install boundary):     [✅ yes | ⚠ conditional | ❌ blocked]
  Invariant 2 (schema version + migration): [...]
  Invariant 3 (dev-mode isolation):         [...]
  Invariant 4 (upgrade-path manual test):   [...]
  Invariant 5 (uninstall opt-in):           [...]
  Invariant 6 (RELEASE_LIFECYCLE accurate): [...]

  Result: <GREEN — ship> | <PRE-RELEASE — ship with pre-release flag, manually test before promote> | <BLOCKED — must resolve N/N invariants before shipping>

  Required follow-ups:
    - <if any>

  Release ack log line (JSONL — append to data/release-acks.jsonl if the maintainer opts in):
    {"ts": "<iso8601>", "version": "vX.Y.Z", "prev": "vX.Y.Z-prev", "gate": "<green|pre-release|blocked>",
     "invariants": [true, true, true, "conditional", true, true], "notes": "..."}
```

## Phase 4 — Hand off

After the summary:

- **GREEN** → "Safe to tag `vX.Y.Z` and promote. Next steps (maintainer runs): git tag, push tag, trigger release workflow."
- **PRE-RELEASE** → "Build the artifact, publish as pre-release (GitHub release → 'Set as a pre-release'), manually install on a `<prev> → <current>` machine, then promote to latest. Re-run the `ragtools-release` skill with evidence once manual test passes."
- **BLOCKED** → "Do not ship. Resolve the named invariants; re-run the skill."

The skill never tags, never pushes, never triggers a workflow. Handoff is verbal/textual only.

## Interaction discipline

- **One item at a time.** Do not dump all six at once. The maintainer needs to think about each.
- **Record acks verbatim.** If the maintainer says "yes, I'll manually test before promote," that specific text goes in the release ack log — do not paraphrase.
- **No inference on schema changes.** If the maintainer says "no schema changes" and Phase 1 heuristics disagree, ask explicitly which file has the apparent change. Never override the maintainer's statement silently; never accept it silently when the evidence contradicts it.
- **No fallback to auto-pass.** Every ack is explicit. An unresponsive skill invocation is a block, not a pass.
- **Distinguish "conditional yes" from "unqualified yes".** "Yes, assuming I manually test" is conditional — that's the pre-release path, not the green path.

## Extending the checklist

When a new permanent invariant is needed (not a one-off — truly permanent), add it to `references/release-checklist.md`:

1. Pick the next item number (N+1).
2. Write the invariant statement + source-of-truth file + pre-check heuristic.
3. Add an ADR to the upstream `docs/RELEASE_LIFECYCLE.md` explaining why this invariant is now permanent.
4. Bump the plugin version (minor bump — user-visible gate surface changed).
5. Walk the new invariant alongside the existing six in the next release gate.

One-off release-specific checks are **not** added to the checklist — they're discussed in the release notes, not promoted to permanent invariants.

## Does NOT do

- Does not tag, push, or promote a release.
- Does not build the installer, run test suites, or validate binaries. These are upstream responsibilities.
- Does not modify `src/ragtools/` — maintainer's repo, outside the plugin's scope.
- Does not ack invariants on the maintainer's behalf. Every ack is explicit.
- Does not override blocks. If the maintainer says "blocked", the summary says blocked. The plugin doesn't argue.

## See also

- `references/release-checklist.md` — the six invariants + rationale + source-of-truth files
- `references/release-ack-log.md` — optional JSONL log format for keeping a history of release gates
- Upstream `docs/RELEASE_LIFECYCLE.md` in the `rag` product repo — the canonical release-lifecycle document this skill enforces against
- The operator-facing `ragtools-ops` skill (sibling) — never confuse the two; different audiences, different workflows
- `docs/decisions.md` in this plugin — binding decisions, appended to per release
