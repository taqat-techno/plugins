---
name: figma-mcp-mechanics
description: >-
  Tool-execution mechanics for safely reading and writing a Figma file through the Figma MCP
  (use_figma / get_metadata / get_screenshot) and the Figma REST API. Use BEFORE planning any
  Figma write: probe write access net-zero, treat get_metadata as lossy, find component-instance
  nodes via a live page query, QA geometry not just text, respect auto-layout child-order and
  resize/variant-swap ordering, load EVERY font (incl. Latin/email tokens embedded in RTL frames)
  before an atomic text write or the whole script aborts, set an explicit target font on blank/cloned
  RTL nodes so they do not render tofu, clone a real reaction (never hand-build one) for setReactionsAsync
  and mirror EN→RTL prototype edges at the frame level, prove prototype wiring by BFS reachability from
  the flow start rather than a reaction count, triage a "systemic" audit finding before mass-editing,
  wait for page load before trusting
  page.children.length, relabel by node-id or full title phrase and return old→new, verify each finding
  by before/after capture, rely on atomic-write rollback, keep repositioning prototype-safe,
  and reach the REST API with an X-Figma-Token PAT. Companion to the design-oriented
  figma-workflow skill — that one teaches WHAT to build, this one teaches HOW the tools behave.
  Also use when get_metadata reports a multi-page file looks empty, an auto-layout list collapses
  after a resize, a variant swap loses cell text, a cloned RTL frame renders boxes/tofu, a font-not-loaded
  error rolls back a write, setReactionsAsync rejects a hand-built action, a page.children.length read
  falsely signals "structure changed", a design "keeps looking corrupted" (often a broken export),
  prototype links might break, or a plain web-fetch of the Figma API returns 401/403. Requires the Figma MCP plugin.

  <example>
  Context: User asks to edit an existing Figma file.
  user: "Update the spacing on every card in this Figma file: <figma-url>"
  assistant: "I will use the figma-mcp-mechanics skill: first run a net-zero write-access probe (create a throwaway frame, delete it) to confirm the seat can actually write, then enumerate frames before editing."
  <commentary>Write-access probe trigger — never plan edits on an unverified seat.</commentary>
  </example>

  <example>
  Context: get_metadata returns almost nothing for a known-populated file.
  user: "The Figma file looks empty — get_metadata returns one page with no children."
  assistant: "I will use the figma-mcp-mechanics skill: get_metadata with only a fileKey is lossy. I will probe a known nodeId for its subtree, or an invalid nodeId to dump the full page list, before concluding the file is empty."
  <commentary>Metadata-lossiness trigger — a thin metadata result is not proof of an empty file.</commentary>
  </example>

  <example>
  Context: An auto-layout list collapsed to tiny after a script ran.
  user: "After my Figma script the menu list shrank to one row."
  assistant: "I will use the figma-mcp-mechanics skill: resize() after setting sizing modes can override AUTO. I will re-apply the AUTO sizing mode last and re-check child order."
  <commentary>Auto-layout mechanics trigger — resize/sizing-mode ordering bug.</commentary>
  </example>
version: 0.1.0
last_reviewed: 2026-07-23
owns:
  - the net-zero write-access PROBE (create-then-delete a throwaway frame before planning edits)
  - the get_metadata lossiness rule (fileKey-only is lossy; probe a known/invalid nodeId)
  - the instance-vs-source discovery rule (live page query, fix the source component once)
  - the "systemic" audit-finding triage (master defect vs wrong instance props vs false positive, before any mass edit)
  - the geometry-and-locale QA rule (screenshot every frame group; assert layout, not just text)
  - the auto-layout child-order / resize / variant-swap ordering rules
  - the atomic-write expectation (a failed script rolls back; no manual cleanup)
  - the prototype-link-safe repositioning rule (verify dangling-reaction count is 0)
  - the REST-API X-Figma-Token PAT-over-curl rule
  - the font-loading-before-write rule (load every font incl. mixed-script Latin/email tokens; the atomic script aborts on one missing font)
  - the RTL-tofu rule (set an explicit target/Arabic font on blank/cloned nodes or they render boxes)
  - the setReactionsAsync clone-don't-construct rule (clone a real reaction and concat the existing ones — the call replaces the array; mirror EN→RTL prototype edges at the frame level; match twin nodes by name)
  - the prototype-wiring proof rule (BFS reachability from page.flowStartingPoints, not a reaction count)
  - the page.children.length load-timing rule (count only after the page has finished loading)
  - the relabel-by-node-id / full-title-phrase rule (dump candidates with id + absolute position first; never a positional selector; return old→new)
  - the per-finding before/after capture rule (revert when the captured `was` disproves the finding; layer names are not rendered text; a "still corrupted" design is often a broken export, proved by paired token counts)
defers_to:
  - figma-workflow skill — design-to-code / code-to-design WORKFLOW and token mapping
  - design skill — visual design theory, layout, accessibility
  - the /figma-use skill (Figma MCP) — the canonical Plugin API contract for use_figma
  - the Figma MCP server — actual tool execution
user-invocable: false
---
<!-- Last updated: 2026-07-23 -->

# Figma MCP Execution Mechanics

## Purpose

The Figma MCP is forgiving about *syntax* and unforgiving about *semantics*. A call can succeed, return
clean XML, pass a text-only check — and still have changed nothing, hidden half the file, or silently
collapsed a layout. This skill encodes the tool-behavior traps so a write session never ships a no-op,
misreads an "empty" file, breaks a prototype link, or edits one node a thousand times when it should fix
one source.

This is the **mechanics** companion to `figma-workflow`. `figma-workflow` owns the design *workflow*
(parse URL, get context, map tokens, generate code). This skill owns *how the tools actually behave*
underneath that workflow. Load both for any non-trivial write.

> If the Figma MCP exposes a `/figma-use` skill, load it first — it is the canonical Plugin API
> contract. This skill layers the failure-mode discipline on top; it does not restate the API.

## When to use

Activate before or during any Figma session that involves:

- **Any write** — creating, editing, moving, resizing, reordering, or variant-swapping nodes.
- A `get_metadata` result that looks empty, thin, or single-page on a file you believe is populated.
- Repeated near-identical edits across many component instances (smells like a source-component fix).
- An audit finding labelled "systemic" that would otherwise trigger a sweep across every frame.
- A layout that visually broke (overlap, collapse, clipping) while text/reaction checks "passed".
- An auto-layout list that collapsed to fixed/tiny size after a resize.
- A variant swap that needs to preserve text the swap will delete.
- **Any text write**, especially mixed-script (an RTL body with Latin/email/number tokens) or into blank/cloned nodes.
- Mirroring or duplicating prototype navigation (e.g. an EN flow onto an RTL clone) via `setReactionsAsync`.
- A structure or child-count check that might have raced the page load (a suspected "nodes disappeared").
- Renaming/relabeling nodes, or auditing a design that "keeps looking corrupted".
- Any re-layout where prototype reactions/links must survive.
- A need to read data the MCP read tools do not expose, requiring the Figma REST API directly.

Do NOT use this skill for pure design theory or code generation — that is `design` / `figma-workflow`.

## The fifteen mechanics

### 1. Net-zero write-access PROBE before planning any edits

A seat can authenticate and read perfectly while **silently failing every write** — a "View"/"Can view"
seat is the classic case: no error, no exception, the node simply never appears.

**Probe (net-zero):** before planning edits, create a throwaway frame at a harmless location, confirm it
exists, then immediately delete it. If creation does not stick (the node is absent on re-read) or deletion
errors, treat the seat as **read-only** and stop — report that an editor seat is required. Never plan a
multi-step edit on an unverified seat; you will produce a confident no-op.

- The probe must leave the file byte-identical (create then delete the same node).
- Run it once at session start, not before every call.
- `whoami` confirms *authentication*, not *write capability* — they are different failures.

### 2. `get_metadata` with only a fileKey is LOSSY

Called with just a `fileKey`, `get_metadata` can report **only the first page** of a multi-page file —
so a fully populated file can look empty or tiny.

**Before concluding a file is empty or small:**

- Probe a **known `nodeId`** (any node URL the user gave you, or the first page's id) — it returns that
  node's **subtree**, which is the real content.
- Or probe an **invalid `nodeId`** on purpose — the **error message dumps the full page list**, revealing
  every page the bare call hid.

Never report "the file is empty" from a fileKey-only metadata call. That is a tool artifact, not a fact.

### 3. Component-instance / internal nodes are invisible to `get_metadata` XML

Nodes *inside* component instances (and other internal children) frequently **do not appear** in the
`get_metadata` XML, yet they are present and editable. Searching the metadata tree for them returns
nothing and tempts you to recreate or to edit every instance.

**Instead:** run a **live page query** inside the file context (e.g. via `use_figma` / the Plugin API:
`findAll` / `findAllWithCriteria` against the current page) to locate the real nodes. When the target is a
shared component rendered as many instances, **fix the SOURCE component once** — every instance updates —
rather than editing each instance. Editing instances one-by-one is slow, drifts, and is usually wrong.

**Triage a "systemic" audit finding BEFORE mass-editing.** An audit that labels a defect "systemic / affects every
frame" is stating a hypothesis, not a fact — it usually inferred the defect from one render or one layer name. The
master may be a `COMPONENT_SET` whose relevant variant is already correct, and the instances may already carry the
right variant props, in which case the "systemic" finding is a misread and a per-frame sweep injects real defects
into a correct file. Inspect the master and sample the instance props first, then pick exactly one of:

- **(i) Component-master defect** — the master/variant itself is wrong → fix the master (or the one variant) once.
- **(ii) Wrong instance variant props** — the master is fine but instances point at the wrong variant → sweep
  `instance.setProperties({...})` across the instances; a sweep that reports `fixed = 0` means the props were
  already correct and the finding was never real.
- **(iii) False positive** — confirm with a **zoomed** `get_screenshot` of the rendered node and do nothing.

Do not per-frame-edit until (i) and (iii) are ruled out.

### 4. Text/reaction QA can pass while the layout is visually broken

A check that only asserts "the text says X" or "the reaction points to Y" will pass on a frame that is
overlapping, clipped, off-canvas, or rendering the wrong locale/variant.

**QA contract:** `get_screenshot` **every frame group** you touched and assert:

- **Geometry** — no overlap, no clipping, expected x/y/width/height, children within parent bounds.
- **Locale / variant** — the correct language string and the correct variant rendered (RTL/LTR, theme,
  state), not merely that *some* text exists.

Text presence is necessary, not sufficient. The screenshot is the ground truth.

### 5. Enumerate frames/components — never skip by name assumption

Do not assume a page/section is absent (or present) because of its name. Names lie, drift, and duplicate.

**Always enumerate** the pages, frames, and components programmatically and iterate the actual list. Never
short-circuit with "there's probably no Settings page" or "the one called Home is the only home." Skipping
by name assumption is how whole sections get missed in a sync.

### 6. Auto-layout mechanics

Auto-layout has three ordering traps that produce silent breakage:

- **Child ORDER governs position, not `x`.** In an auto-layout frame, position is determined by the
  child's **index** in the parent, not its coordinates. To place a node, **insert it at the right index**
  (`insertChild(index, node)` / append at the correct position) — setting `x` does nothing useful.
- **`resize()` after setting sizing modes can collapse the layout.** Calling `resize()` (or
  `resizeWithoutConstraints`) after you have set `layoutSizingHorizontal` / `layoutSizingVertical` can
  override AUTO/HUG back to a fixed, tiny size — collapsing an auto-layout list. **Re-apply the AUTO
  (HUG / FILL) sizing mode LAST**, after any resize, so it wins.
- **READ all cell/badge text BEFORE a variant swap.** Swapping a component/variant **deletes the old
  text nodes**; any text you needed is gone after the swap. Capture every cell/label/badge string first,
  then swap, then re-write the captured text into the new variant's nodes.

### 7. Writes are ATOMIC — a failed script rolls the whole edit back

A Figma write script runs as one transaction: if it throws partway, the **entire edit is rolled back** —
the file returns to its pre-script state. There is **no half-applied mess to clean up manually**.

- Do not write defensive "undo what I just did" cleanup code for a failed run; the rollback already did it.
- Do verify success by re-reading (screenshot/metadata) after the script returns, since a rollback means
  *nothing* changed, not *some things* changed.
- Prefer one cohesive script over many tiny calls so partial-progress states never become observable.

### 8. Repositioning frames is PROTOTYPE-LINK-SAFE

Prototype reactions/links key off **node IDs**, not coordinates. Moving, re-laying-out, or re-parenting a
frame **does not** break its prototype links as long as the node keeps its ID (which a move/reorder does).

- Re-layout freely; you are not severing interactions by moving frames.
- **But verify**: after any re-layout, confirm the **dangling-reaction count is 0** (no reaction now
  points at a deleted node). A *delete* (not a move) is what orphans a reaction — so if your edit deleted
  and recreated a node, its inbound reactions are now dangling and must be re-pointed.

### 9. The Figma REST API needs an `X-Figma-Token` PAT via curl

When you need data the MCP read tools do not expose, call the **Figma REST API** directly. It requires a
custom auth header, and a plain web-fetch tool **cannot send custom headers** — so it will 401/403.

- Use `curl` (or any client that sends headers) with a Personal Access Token:
  `curl -H "X-Figma-Token: <PAT>" "https://api.figma.com/v1/files/<fileKey>"`.
- The PAT is the user's own token — source it from the environment / the user; **never hardcode, echo, or
  commit it**. Redact it in any output.
- If a web-fetch attempt returns 401/403 on the Figma API, the cause is the missing header, not bad creds
  — switch to curl rather than re-requesting the token.

### 10. Load EVERY font BEFORE a text write — one missing font aborts the whole atomic script

A `use_figma` write that sets text (characters, font, or a mixed-script run) requires every font it touches to be
**already loaded** (`loadFontAsync` per family+style). Because the write is **atomic** (mechanic 7), a **single**
unloaded font **throws and rolls the ENTIRE script back** — not just the offending node. The trap is mixed-script
content: an RTL frame commonly carries **Latin/email/URL/number tokens** (an address, a brand word, a phone number)
in a *different* font from the Arabic body, and it is the overlooked Latin token — not the obvious body font — that
aborts the run.

- **Enumerate every distinct (family, style)** across **all** text nodes the script will touch — including the small
  Latin/email/number tokens embedded inside RTL frames — and `loadFontAsync` **all of them up front**, before the
  first `characters`/font assignment.
- A font used by only one placeholder still counts. "Most fonts loaded" is a failed run: the atomic rollback means
  a near-complete script that hits one missing font ships **nothing**.
- After the run, re-read (mechanic 7) — a rollback means the text was never written, not partially written.

### 11. Blank/cloned RTL nodes render TOFU without an explicit target font

A text node that was **blank, a placeholder, or cloned into an RTL frame** has no *resolved* font for the target
script. Writing an Arabic (or other non-Latin) string into it **without setting an explicit font** renders **tofu**
(□□□ / boxes) even though the string value is correct — the QA text check passes while the frame is visibly broken.

- **Set the target font explicitly** on any blank/cloned node before writing its characters; do **not** rely on
  inheritance from the frame or the source of the clone.
- This is a locale-QA case of mechanic 4: screenshot the frame and assert the **glyphs render**, not merely that
  `characters` equals the expected string. Correct text + boxes on screen = wrong font, not wrong string.

### 12. `setReactionsAsync` rejects a hand-built action — CLONE a real reaction

`setReactionsAsync` will **reject a hand-constructed** reaction/action object (a synthetic `{ trigger, action }`
you assembled from scratch) — the accepted shape has fields the API populates that a hand-built object omits or
malforms. A NODE navigation action carries required fields beyond `type`/`destinationId`/`navigation` (the stored
shape also includes `transition` and `resetVideoPosition`), and omitting them fails **every** write with
`Property "reactions" failed validation: Expected [0].actions[0] to be one of the following`. The index in that
message points at the offending array slot — if the target node had no prior reactions, `[0]` is *yours*, which is
the tell that your object is malformed rather than an existing one. Mirroring prototype navigation (e.g. duplicating
an EN flow onto an RTL clone) by *building* the action fails silently or errors.

- **Clone a REAL reaction** off an existing working node, **retarget** its destination node id, and set *that* —
  never author the action object by hand. Reactions are plain serializable objects, so a deep clone
  (`JSON.parse(JSON.stringify(reaction))`) reproduces the exact valid shape; swap `destinationId` in **both**
  `.action` and every entry of `.actions[]`.
- **`setReactionsAsync` REPLACES the whole array — there is no append API.** Setting only your new reaction wipes
  every interaction the node already had. Clone the node's existing reactions too and `concat` the new one.
- **Mirror EN→RTL prototype edges at the FRAME level.** The navigation reaction lives on the frame/instance, not on
  a deep child; copy edges frame-to-frame so the mirrored flow matches the source flow node-for-node.
- **Match mirrored child nodes by NAME, not by index path.** An RTL twin reorders its children (a topbar control at
  path `0/0/0` in the LTR source is a *different* node in the clone), so a positional lookup retargets the wrong
  node silently. Resolve the twin's counterpart with `findAll(n => n.name === '<name>')` inside the twin instead.
- **Validate the wiring by BFS reachability from the flow start — not by counting reactions.** A reaction count only
  proves edges *exist*; it reports a mis-wired edge (one pointing at the wrong twin) as healthy, and it cannot tell
  you which frames are still orphaned. Take `page.flowStartingPoints` as the roots, build frame→frame adjacency from
  every node's `.reactions` NODE actions, and BFS. Frames that should be reachable and are not are the real defects
  — including pre-existing mis-wires a same-trigger conflict guard correctly declined to overwrite. Re-run
  reachability after **every** batch; it is the ground truth.
- This composes with mechanic 8: a move preserves reactions, but *recreating* a node orphans them — re-point by
  cloning the original reaction, then verify dangling-reaction count is 0.

### 13. `page.children.length` is unreliable until the page finishes loading

A child-count read (`page.children.length`, or any structure diff) taken **before the page has fully loaded** returns
a **partial** number. Gating a "the structure changed / nodes disappeared" alarm on that racey count produces a
**false** corruption report — the nodes are there, the page just had not finished loading when you counted.

- **Await the page load** (`page.loadAsync()` / ensure the page is the fully-loaded current page) **before** counting
  children or diffing structure.
- Never conclude "nodes were deleted" or "the structure changed" from a count that may have raced the load — re-read
  after load and compare again before raising it.

### 14. Relabel by node-id or full title phrase — never a positional selector — and return old→new

When renaming/relabeling nodes, **target by explicit node-id or the full title phrase**. A positional or heuristic
selector — "the first non-standard text node", a bare word, "the one that looks like a heading" — silently matches
the **wrong** node, and the mislabel is invisible until much later.

- **Dump the candidates BEFORE editing.** List every candidate node with its **id + absolute position + parent**,
  then pick the exact id from that list. Absolute position is what separates look-alikes a predicate cannot: a panel
  heading and the chip row beneath it both match "a text node that is not in the standard set", and only their
  absolute Y tells them apart. Skipping the dump is how a "restore this chip label" edit renames the section heading
  on every frame instead.
- **Select by node-id** (preferred) or the **complete title string**; never by ordinal position or a partial/bare word.
- **Return the old→new pair for every relabel.** If the reported *old* value is not what you expected to be changing,
  you hit the wrong target — the old→new echo is the cheap check that catches it immediately. Revert, re-read the
  structure, and re-target by id rather than adjusting the predicate.

### 15. Verify each audit finding by before/after capture — a "still corrupted" design may be a broken EXPORT

When auditing or repairing, capture a **before AND an after** screenshot **per finding** and diff them. A design that
"keeps looking corrupted" **after** a correct fix is frequently a broken **export/render** — a stale exported PNG, a
cached render, a bad export setting — **not** a corrupt source.

- Before re-editing a source that already looks right in a fresh capture, **check the export path**: re-export /
  re-render and compare against a live `get_screenshot` of the source.
- **Settle export-vs-source with PAIRED COUNTS, not assertion.** Find the cited export on disk (a reviewer's PDF is
  usually still in Downloads), extract its text (`pdftotext -enc UTF-8 "<file>.pdf"`), and count occurrences of the
  broken token in the **export** against the same token in the **live source**. A token that is complete 31× /
  truncated 0× in the file but truncated 17× in the PDF closes the case in one pass; an extractor warning like
  `Illegal entry in bfchar block in ToUnicode CMap` is the smoking gun that the exporter's glyph→Unicode map is
  malformed. Trusting the rendered complaint instead of extracting the artifact is what keeps the loop running.
- **RTL exports fail in a specific, diagnosable way.** An Arabic (or other RTL) page exported **without the font
  embedded and without bidi-aware handling** reverses RTL runs and splits LTR tokens that the source correctly
  isolates with `U+2066`/`U+2069` — so a clean source produces doubled/reversed words and truncated identifiers in
  the export only. The fix is an export-tooling step (embed or outline the RTL font, export bidi-aware); say so
  loudly and early, because it is the loop-breaker and it is not something the design edit can deliver.
- **Reversed-but-valid RTL text is NOT mojibake.** Every character is a legitimate codepoint in the wrong visual
  order, so grepping for replacement characters or `Ã` / `â€` mis-decoding artifacts finds nothing and "proves"
  the text is fine. Read the stored strings or screenshot; encoding-artifact greps cannot detect this class.
- **Audits generate false positives from layer NAMES.** `get_metadata` reports a node's `name` — the layer label,
  routinely an English developer string on a node whose rendered text is correct — so an audit that reads names
  files phantom defects (a correct back-link flagged from a layer named for a breadcrumb, correct localized copy
  flagged from a layer named for a default value). Confirm any suspected *text* defect with a screenshot of the
  rendered node before filing or fixing it.
- **Make the edit script capable of undoing its own finding.** Have it return the `was` value with the `now` value
  (mechanic 14) and **revert when `was` shows the finding was wrong** — that is the check that stops a false
  positive from becoming a real regression in a file that was already correct.
- Do **not** re-"fix" a source that a stale export is misrepresenting — you will churn a correct file chasing an
  artifact that lives in the export, not the design. Confirm source-vs-export before touching the source again.
  Rebuilding correct RTL content to satisfy a broken export injects genuine errors into a clean file.

## Decision flow

```
Figma task
  |
  +-- WRITE intended? --yes--> [1] net-zero write-access probe (create+delete throwaway)
  |                                  |-- write fails silently --> STOP: read-only seat, ask for editor
  |                                  `-- write sticks --> proceed
  |
  +-- File looks empty/thin? -----> [2] probe known nodeId (subtree) OR invalid nodeId (page-list dump)
  |
  +-- Target is inside instances? -> [3] live page query; fix SOURCE component once
  |                                       "systemic" finding? triage master-defect / wrong props / false positive first
  |
  +-- Editing layout? ------------> [6] order=position; insert at index; re-apply AUTO last;
  |                                       read cell text BEFORE variant swap
  |
  +-- Writing TEXT? --------------> [10] load EVERY font up front (incl. Latin/email tokens in RTL) — atomic aborts on one miss
  |                                  [11] set explicit target font on blank/cloned RTL nodes (else tofu)
  |
  +-- Mirroring prototype edges? -> [12] clone a REAL reaction (never hand-build) + concat existing (set REPLACES);
  |                                       mirror EN→RTL at the frame level; match twins by name; then BFS-reach from
  |                                       page.flowStartingPoints — reachability, not reaction count, is the proof
  |
  +-- Re-laying-out frames? ------> [8] safe (IDs preserved); then assert dangling-reactions == 0
  |
  +-- Counting/diffing structure? -> [13] await page load before trusting page.children.length
  |
  +-- Relabeling nodes? ----------> [14] dump candidates (id + absolute position + parent) first;
  |                                       target by node-id / full title phrase; return old→new
  |
  +-- Need data MCP can't read? --> [9] curl + X-Figma-Token PAT (web-fetch can't send headers)
  |
  `-- Before "done" -------------> [4] screenshot every touched frame group; assert geometry + locale/variant
                                    [5] enumeration was exhaustive (no page/section skipped by name)
                                    [7] verify via re-read (atomic: a failure changed nothing)
                                    [15] before/after capture per finding — a "still corrupted" look is often a broken EXPORT
                                         (prove it with paired token counts: extracted export vs live source)
```

## Safety gates

- **Never** plan or execute a multi-step edit on a seat whose write capability has not been probed net-zero.
- **Never** conclude a file is empty/small from a fileKey-only `get_metadata` call.
- **Never** edit instances one-by-one when a single source-component fix is the correct change.
- **Never** act on a "systemic" audit finding before triaging it: master defect, wrong instance props, or false positive.
- **Never** sign off a write on text/reaction checks alone — screenshot and assert geometry + locale/variant.
- **Never** skip a page/section because its name implies it is irrelevant — enumerate and iterate.
- **Never** set `x` to reposition an auto-layout child — insert at the correct index.
- **Never** call `resize()` after sizing modes without re-applying AUTO last.
- **Never** variant-swap before capturing the old cell/badge text you need.
- **Never** hand-write rollback cleanup for a failed script — the write was atomic.
- **Never** start a text write before loading **every** font it touches — including the Latin/email tokens inside an RTL frame; one miss aborts the whole atomic script.
- **Never** write an Arabic/non-Latin string into a blank or cloned node without setting an explicit target font — it renders tofu.
- **Never** hand-build a reaction for `setReactionsAsync` — clone a real one and mirror EN→RTL edges at the frame level.
- **Never** call `setReactionsAsync` with only the new reaction — it replaces the whole array; clone the existing ones and concat.
- **Never** locate a node in an RTL twin by index path — twins reorder children; match by name.
- **Never** declare prototype wiring done from a reaction count — BFS reachability from `page.flowStartingPoints` is the proof.
- **Never** trust `page.children.length` (or a structure diff) before the page has finished loading — it raises false "structure changed" alarms.
- **Never** relabel by a positional/bare-word selector ("first non-standard text") — target by node-id / full title phrase and return old→new.
- **Never** pick a relabel target without first dumping the candidates with id + absolute position + parent.
- **Never** file or fix a text defect read from a layer `name` — the layer label routinely disagrees with the rendered text; screenshot first.
- **Never** re-edit a source that a fresh capture shows is fine — a "still corrupted" look is often a broken export; verify source-vs-export first.
- **Never** argue export-vs-source — extract the cited export and compare paired token counts against the live source.
- **Never** hardcode, echo, or commit a Figma PAT; redact it everywhere.

## Validation checklist

- [ ] Write-access probed net-zero (throwaway frame created then deleted; file byte-identical) before edits.
- [ ] If the file looked empty, a known/invalid `nodeId` probe confirmed real contents before any claim.
- [ ] Target nodes located via live page query when absent from `get_metadata` XML; source fixed once.
- [ ] Any "systemic" finding triaged (master defect / wrong instance props / false positive) before a single mass edit.
- [ ] Every touched frame group screenshotted; geometry + locale/variant asserted (not just text).
- [ ] Pages/frames/components enumerated programmatically; nothing skipped by name assumption.
- [ ] Auto-layout: children placed by index; AUTO sizing re-applied last; cell text captured before swap.
- [ ] Text writes: every (family, style) — including Latin/email tokens in RTL frames — loaded up front before any `characters` assignment.
- [ ] Blank/cloned RTL nodes given an explicit target font; screenshot confirms real glyphs, not tofu.
- [ ] Prototype edges mirrored by cloning a real reaction (not hand-built); EN→RTL edges copied at the frame level.
- [ ] Existing reactions cloned and concat-ed (the set call replaces the array); twin nodes matched by name, not index path.
- [ ] Prototype wiring proved by BFS reachability from `page.flowStartingPoints`, re-run after every batch — not by a reaction count.
- [ ] `page.children.length` / structure diffs read only after the page finished loading (no false "structure changed").
- [ ] Relabel candidates dumped with id + absolute position + parent before the target was chosen.
- [ ] Relabels targeted by node-id / full title phrase; old→new returned and the old value matched the intended target.
- [ ] Suspected text defects confirmed by screenshot of the rendered node, never from a layer `name`.
- [ ] Each audit finding verified by before/after capture; the script reverted wherever the captured `was` disproved the finding.
- [ ] A persistent "corrupted" look settled with paired token counts (extracted export vs live source) before re-editing the source.
- [ ] Post-write re-read confirms the change (remembering a failed script changed nothing — atomic).
- [ ] After any re-layout, dangling-reaction count verified == 0.
- [ ] REST API (if used) called via curl with `X-Figma-Token`; PAT never echoed or committed.

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Plan a 20-step edit, then discover the seat is View-only | Every write silently no-ops; the plan was wasted | Net-zero probe (create+delete) first; require an editor seat |
| "File is empty" after a fileKey-only `get_metadata` | Bare call reports only the first page | Probe a known nodeId (subtree) or invalid nodeId (page dump) |
| Edit all 50 instances of a card to change padding | Slow, drifts, and the instances inherit from a source | Fix the SOURCE component once; instances update |
| Sweep 16 frames because the audit called the finding "systemic" | "Systemic" is the audit's hypothesis; the master variant and instance props are often already correct | Triage first: master defect / wrong instance props / false positive (zoomed screenshot) |
| Mark done because the text reads correctly | Layout can be overlapping/clipped/wrong-variant yet pass | Screenshot every frame group; assert geometry + locale/variant |
| "No Settings page — the names don't show one" | Names lie/drift; the section may exist under another name | Enumerate pages/frames; iterate the real list |
| Set `x` to move an auto-layout child | Order, not coordinates, governs position there | Insert/reorder at the target index |
| `resize()` after setting sizing modes, then stop | resize can override AUTO and collapse the list | Re-apply AUTO/HUG/FILL sizing mode last |
| Variant-swap, then look for the old label text | The swap deleted the old text nodes | Capture all cell/badge text BEFORE the swap |
| Hand-write "undo my partial edit" after a throw | The write was atomic; it already rolled back | Re-read to confirm nothing changed; fix and re-run |
| Load the body font, write text, hit a font error on a Latin email token | The atomic script aborts on the one missing font; nothing ships | Enumerate and load EVERY (family, style) — incl. Latin/email tokens in RTL — up front |
| Write the Arabic string into a cloned node; text is right but shows boxes | A blank/cloned node has no resolved font → tofu | Set the explicit target font on the node before writing characters |
| Hand-build a `{trigger, action}` and pass it to `setReactionsAsync` | The API rejects a synthetic action shape | Clone a real reaction, retarget it, mirror EN→RTL at the frame level |
| Set just the new reaction on a node that already had one | The call replaces the whole array — the prior interaction is gone | Clone the existing reactions too and concat the new one |
| Find the twin's counterpart by the source's index path | RTL twins reorder children, so the same path is a different node | Match by name inside the twin (`findAll(n => n.name === …)`) |
| Report the flow wired because the reaction count went up | A count cannot see orphaned frames or an edge aimed at the wrong twin | BFS from `page.flowStartingPoints` over the reaction graph after every batch |
| Alarm "structure changed — nodes gone" from a `children.length` read | The count raced the page load and returned a partial number | Await page load, then count/diff |
| Relabel "the first non-standard text node" | Matches the wrong node silently | Target by node-id / full title phrase; return old→new to catch a miss |
| Pick the relabel target straight from a predicate match | A heading and the chip row below it satisfy the same predicate; only absolute Y separates them | Dump candidates with id + absolute position + parent, then edit the exact id |
| File a text defect read off a node's layer `name` | Layer labels are developer strings and routinely disagree with correct rendered text | Screenshot the rendered node before filing; revert when the captured `was` disproves it |
| Grep the export text for `?`/`Ã` to confirm "mojibake" | Reversed RTL runs are valid codepoints in the wrong order — no mis-decoding artifact to find | Read stored strings / screenshot; diagnose bidi + missing embedded font in the exporter |
| Re-fix a source that "keeps looking corrupted" | The corruption is often in a stale export, not the source | Before/after capture per finding; verify source-vs-export first |
| Assert "it's the export" without evidence | The claim keeps returning each review cycle and nothing closes it | Extract the export and compare paired token counts against the live source |
| Move a frame and assume the prototype broke | Reactions key off node IDs; a move preserves them | Re-layout freely; then assert dangling-reactions == 0 |
| web-fetch the Figma REST API, get 401, re-ask for token | web-fetch cannot send the `X-Figma-Token` header | Use curl with the header; redact the PAT |

## Cross-references

- `figma-workflow` (skill) — design-to-code / code-to-design workflow, token mapping, asset rules.
- `design` (skill) — visual design theory, layout patterns, accessibility.
- `/figma-use` (Figma MCP skill) — canonical Plugin API contract; load before `use_figma`.
- `/ui-ux-mechanics figma ...` (command) — entry point for Figma sub-commands.
