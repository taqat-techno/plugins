# lessons-to-plugins — recommendations

Regenerated 2026-09-12. Supersedes the 2026-08-22 edition.

This run completed P0–P9. 13 lessons were absorbed into 6 skills across 3 plugins
in one commit; everything below is what could **not** or should **not** be
absorbed, with the reason.

---

## Corpus state after this run

| | |
|---|---|
| Lessons in corpus | 452 (h2 = 136, h3 = 277) |
| Ledger entries | 153 (140 before + 13 absorbed) |
| Candidates remaining | 299 |
| Analyzed this run | 14 (13 absorbed + 1 left open, below) |

---

## New-plugin / new-skill candidates

### Visual-parity measurement — 6 lessons, 3 dates — owner APPROVED, **not implemented**

The strongest unresolved cluster. Six lessons share one domain that **no shipped
skill owns**: how to make a screenshot comparison against a reference
implementation mean anything.

| id | date | lesson |
|---|---|---|
| `120cd969880a` | 2026-08-20 | Pixel-diff ranks what to look at next; geometry probes decide whether it is fixed |
| `b32c36cb624f` | 2026-08-20 | Capture from a production build, never the Next.js dev server |
| `836d0b726568` | 2026-08-20 | Find the reference's runtime fit/zoom first; compare at zoom = 1 |
| `fe6001629221` | 2026-08-20 | Server-synced user preferences override localStorage theme seeds |
| `c71dee5fe6bd` | 2026-09-12 | Decompose a measured delta into whole source-cited values — a fractional literal means the cause is not found |
| `96f6a39b6852` | 2026-09-12 | Tailwind preflight's `line-height: 1.5` + `font: inherit` is the systemic lever, not per-element padding |

Meets the new-skill threshold (≥ 4 lessons, ≥ 2 distinct dates, no existing
owner, one plausible plugin). Proposed owner **`react-kit`**, on the
mechanism-not-observation rule: the stack is Next.js + Tailwind + a headless
capture, and `react-kit/skills/frontend-build-traps` already owns the neighbouring
stale-applied-CSS-chunk false negative. `ui-ux-mechanics/skills/design` owns
design *authoring* (wireframes, palettes, WCAG), not measurement, and is the wrong
home.

**Status: the owner and the new-skill classification are approved.** `react-kit`
owns the visual-reference-comparison / visual-parity-measurement mechanism.
Approved 2026-09-12.

**Implementation is deliberately deferred to a dedicated run.** Nothing was built
in this run: no skill directory, no `react-kit` version bump, no absorption of the
six lessons. They remain candidates with the ownership question settled, so the
future run starts from a decision rather than re-litigating it. Each is recorded
in the ledger as deferred with that reason; a deferred lesson stays a live
candidate by design, so none of them is hidden.

When built, the skill would own: what a pixel score is and is not evidence of,
capture preconditions (production build, zoom = 1, seeded deterministic data,
cleared fetch cache), the geometry-probe settlement method, and delta
decomposition into source-cited whole values.

---

## Human decisions outstanding

### `25e279e68077` — coverage is PARTIAL, so it stays unresolved

*"Validate a new linter against a reference codebase — nonzero findings there
means false positives, not findings"* (2026-08-21).

An earlier draft of this file claimed this run's rule 9 "does now cover its
mechanism." **Reading both texts side by side shows that is wrong.** The lesson
carries four distinct claims and rule 9 ships one of them:

| Claim in the lesson | Shipped? |
|---|---|
| Validate a new rule set against known-good content; a nonzero count there is a finding about the checker | **Partly.** Rule 9's closing sentence and the checklist item state the principle. The *procedure* — pick a large, well-written codebase **in the same ecosystem** (framework core, a respected OSS repo), expect near-zero, investigate every remaining hit — is not shipped |
| `^(\s+)` to detect indentation is wrong: `\s` matches newlines, so column-0 code after a blank line matches as indented and the reported line number is off by one. Use `^([ \t]+)` | **No** |
| A vendor / exclusion filter must be applied to **every** scan pass, not only the first one written (96 of 99 hits in one rule were vendored library code) | **No** |
| Test-adjacent fixture files must not be classified as test bodies, where the flagged pattern is legitimate | **No** |
| Pin the rule set in **both** directions: anti-patterns detected **and** idiomatic code silent | **No** |

**Provenance, stated exactly:** rule 9 was written from `6a75f90acab1` (the
mass-false-positive shape) and `2bb21ede13a6` (the uniform-failure shape). Those
two are its source lessons and are recorded as such. `25e279e68077` was **not** a
source lesson — its **title** was visible in the candidate listing and rule 9's
closing sentence paraphrases that headline, but its body was not used and
contributed no mechanism. It is not a duplicate of rule 9.

**Why it has no home yet.** The three concrete bugs and the bidirectional-pinning
requirement are all about **authoring** a scan rule set. `test-result-evidence`
explicitly defers authoring away ("this skill judges a result, it does not write
the test"), and `structural-assertions` — which does own writing probes, and owns
the neighbouring "a grep cannot tell code from a comment" rule — covers none of
regex scoping, per-pass filter application, file-role classification, or
two-directional pinning. So the honest outcome is **unresolved**: no ledger write,
stays a live candidate.

**Recommended next step:** treat it as the seed of a scan-rule-authoring rule set,
either as an extension of `structural-assertions` or as its own skill, and decide
that on its own merits rather than folding it into a result-judging skill.

---

## Project-specific — never crosses into a plugin

| id | lesson | Why not |
|---|---|---|
| `4174934cbc37` | Investigation prompts gate implementation behind the literal phrase "I approve implementation" | A personal working convention, not generic knowledge. Belongs in `CLAUDE.md` / User Preferences, where it already lives. Rule 1 of this skill forbids it crossing |
| `2ad6488f0996` | Never file an issue whose fix carries no code change | Same — a standing rule with a specific origin incident |

## Already covered — ledger only, no edit

| id | lesson | Confirmed at |
|---|---|---|
| `b5cc4a72b9e9` | A skill's addressable id is its DIRECTORY name, not frontmatter `name:` | `claude-plugin-builder/references/plugin-evals.md:186`; `SKILL.md:587-593` |
| `0aef6cd5b6cf` | Behavioral evals are the fourth gate (HR-20) | `claude-plugin-builder/references/house-rules.md` (HR-20), `references/quality-gates.md` (Gate 4 R0a–R0f), `references/plugin-evals.md` |

Both were shipped into `claude-plugin-builder` earlier the same day, which is why
they read as new lessons and as already-covered at once.

## Deferred

| id | lesson | Score | Why |
|---|---|---|---|
| `bd22d87a697c` | A board column driven by close automation is stale bookkeeping, not a work queue — read the item's own state | 5 | The generic rule is sound, but no plugin owns GitHub Projects: `devops` owns Azure DevOps boards specifically. Ambiguous ownership is a defer, never a guess |

## Rejected

None this run.

---

## Framework defect — investigated read-only, held out of both commits

### 147 lessons carry a wrong section label (not 81 run logs)

**This corrects what the pre-investigation draft of this file said.** It claimed
`lessons_index.py` parses `### <timestamp> — /lessons run` blocks as candidates
and that 81 candidates were run-log noise. Both claims are false, and the remedy
they implied was destructive:

- `LESSON_RE` does **not** match a full ISO timestamp — `2026-09-12T08:02:45Z`
  presents `T08:02:45Z` where the regex needs a dash. Verified against the regex.
- **Zero** of the 147 entries attributed to `Processing Log` are run logs. All are
  real lessons; the 81 candidates were legitimate.
- The real defect: `## Processing Log` (line 3657) is the **last non-dated `h2`**
  in the corpus, so the 136-lesson trailing `h2` regime plus 11 dated `h3`
  entries all inherit its label to EOF. A stale label, not bad candidates.
- Excluding that section — the fix the earlier framing implied — would have
  **dropped 147 lessons, 33% of the corpus**.

**Investigation only in this run — nothing was fixed.** No parser change, no
corpus heading, no regression test was implemented, deliberately: framework repair
does not belong in a knowledge-update commit.

Recommended fix is two parts, smallest first: insert one real section heading
above the trailing regime (no code change, fixes 136 of 147), then add a parser
guard plus a `mis_sectioned` count so it cannot recur silently. The load-bearing
regression test is that the parsed lesson count stays at **452** — the assertion
that catches the destructive version.

Full analysis, exact numbers, the `eaeadfe1ffbf` mechanism, the 11-entry human
question, and six regression tests:
`claude_plugins/.claude/docs/2026-09-12_lessons-index-section-attribution-defect.md`.
Owner: `.claude/skills/lessons-to-plugins/lib/lessons_index.py` — not a plugin
change, and deliberately not mixed into a knowledge-update commit.

---

## Counts for this run

| | |
|---|---|
| Candidates in | 312 (all legitimate; 81 carried a wrong section label - see the defect section) |
| Analyzed | 14 |
| **Absorbed** | **13** → 6 skills, 3 plugins, 8 files, +201 lines |
| New-skill candidate held | 1 (6 lessons) |
| Already covered (ledger only) | 2 |
| Project-specific | 2 |
| Deferred | 1 |
| Rejected | 0 |
| Gates passed | `validate_plugin.py` 0 errors on all 3 touched · `validate_marketplace.py` no architecture errors · `validate_evals.py` 0 FAIL/0 WARN · 0 deletions · 5/5 frontmatter parse · 5/5 descriptions byte-unchanged · noun sweep clean on all 201 added lines |
| Flagged for size | `test-result-evidence` +29.2% (168→217) and `defensive-failure-design` +15.4% (149→172); both well under the 500-line body cap. `reviewer/SKILL.md` was already at 507 lines, so all three of its rules went to `references/` and its body was not touched |
