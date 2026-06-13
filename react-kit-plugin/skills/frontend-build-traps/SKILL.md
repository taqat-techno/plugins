---
name: frontend-build-traps
description: A catalog of recurring React / Next.js build-and-tooling traps that cost hours because the symptom points at the wrong layer — Turbopack HMR stale-module 500s, vitest/rolldown-vite jsx-preserve breaking tsx test imports, lockfile package-manager-major mismatches that only fail in CI, TipTap addAttributes casing + renderHTML serialization scope, ORM client-vs-schema drift mistaken for a real type error, and the lint-the-new-file-before-push discipline. Each entry gives the deterministic recovery, not a guess. Activates when an HMR reload throws "module factory is not available", a tsx test fails to import after a vitest/vite upgrade, CI rejects a lockfile or hoists deps differently than local, a TipTap attribute won't persist, an ORM type error appears right after a schema change, or whole-repo lint passes but a new file is broken.
version: 0.1.0
last_reviewed: 2026-06-13
owns:
  - the build/tooling trap catalog (HMR stale-module, vitest jsx-preserve, lockfile PM-major, TipTap attribute casing, ORM client/schema drift, lint-new-file-before-push)
  - the "symptom layer != cause layer" discipline for build/dev-server/test/CI failures
  - the deterministic full-reset recipe for Turbopack HMR stale-module 500s
  - the drift-vs-real-error decision (compare generated-client mtime against schema before calling it drift)
defers_to:
  - react-lint-triage (analyzer/linter finding classification and the false-positive catalog)
  - data-fetching-states (runtime loading/error/empty state verdicts)
  - react19-migration (deprecated/removed-API migration verdicts)
  - env-doctor (generic broken-local-environment diagnosis: spawn / auth / missing-binary / version / DNS / encoding / config-shadowing)
  - the project's own package-manager, bundler, and ORM configuration (the source of truth for versions and paths)
user_invocable: false
---

# frontend-build-traps

## Purpose

Most React / Next.js build-and-tooling failures waste time because the error surfaces in one layer while the cause lives in another: a browser reload 500s but the bug is in the dev server's in-memory module graph; a test import breaks but the cause is a tsconfig flag a new transformer started honoring; CI rejects a lockfile but local installs cleanly. This skill is a catalog of those traps, each with the *deterministic* recovery, so the agent stops guessing and applies the known fix.

It is a sibling to `react-lint-triage` (which judges analyzer findings) — this skill judges build, dev-server, test-runner, package-manager, and ORM-codegen failures.

## When to use

Activate when any of these surface:

- A browser reload throws `module factory is not available, deleted in an HMR update` (or a 500 that survives a plain reload) after you removed a previously-imported symbol.
- A `.tsx` test file fails to import/transform right after a vitest or vite (including rolldown-vite) upgrade.
- CI rejects a lockfile that installs fine locally, or local and CI resolve different optional/peer deps.
- A TipTap (ProseMirror) custom attribute won't persist, or serializes but doesn't show while editing.
- A type error against an ORM client appears immediately after a schema change, or an inline ORM mock returns `undefined` from a method.
- Whole-repo lint exits 0 but a file you just added is actually broken.

Do NOT use this for application logic bugs, runtime state bugs (see `data-fetching-states`), analyzer-finding triage (see `react-lint-triage`), or generic environment breakage like a missing binary or auth loop (see `env-doctor`).

## Inputs (adapter)

Every project-specific value is a named adapter input. Nothing below is hardcoded.

1. **PACKAGE_MANAGER + CI_PM_MAJOR** — the package manager and, critically, the MAJOR version CI runs. Local and CI majors must match.
2. **BUILD_CACHE_DIR** — the bundler/framework build-cache directory to clear on a full HMR reset (e.g. a `.next`-style cache or a bundler cache folder). Project-supplied; never assume the name.
3. **DEV_SERVER_CMD** — how the project starts exactly one dev server, so a reset doesn't leave two running on different ports.
4. **TEST_RUNNER + COVERAGE_PKG** — the test runner and its coverage package, with their majors (must match each other).
5. **ORM + GENERATED_CLIENT_PATH + SCHEMA_PATH** — the ORM, where its client is generated, and the schema file, so client-vs-schema drift can be checked by mtime.

If an adapter value is unknown, discover it read-only (read the lockfile, the framework config, `package.json` scripts) before acting.

## The trap catalog

### 1. Turbopack HMR stale-module 500 — `module factory is not available`

**Symptom.** After you delete or rename a symbol that was previously imported, the page 500s with `module factory is not available, deleted in an HMR update`. A plain browser reload does NOT clear it — the dev server's in-memory module graph still references the deleted factory, and an automation/browser cache may hold the stale chunk too.

**Why a reload fails.** The fault is server-side (stale HMR graph) and client-side (cached chunk), not in the file you're looking at. Editing the source again often does not evict the dead factory.

**Deterministic full reset (do all four, in order):**

1. Kill the dev server process (not just Ctrl-reload the page).
2. Delete the **BUILD_CACHE_DIR**.
3. Restart exactly **one** dev server via **DEV_SERVER_CMD** (two servers on two ports masks the fix).
4. Clear the browser / automation cache (hard reload, or a fresh automation context) so the stale chunk is re-fetched.

Skipping any one of the four commonly leaves the 500 in place and makes it look like the code change "didn't work."

### 2. vitest 4.x (rolldown-vite) honors tsconfig `jsx: preserve` and breaks `.tsx` test imports

**Symptom.** After upgrading to vitest 4.x on rolldown-vite, `.tsx` test files fail to import/transform, often with raw JSX reaching the runtime un-transformed.

**Cause.** rolldown-vite uses **oxc** (not esbuild) for transforms, and it **respects the tsconfig `jsx` setting**. If tsconfig has `"jsx": "preserve"`, oxc leaves JSX un-transformed for tests.

**Fix.** Set the oxc jsx-automatic transform in the vite/vitest config — do NOT reach for the esbuild jsx option, which rolldown-vite **ignores**. Illustrative (not required), in the vite/vitest config:

```js
// rolldown-vite: oxc owns the JSX transform; esbuild.jsx is ignored here
export default {
  oxc: { jsx: { runtime: 'automatic' } },
}
```

**Companion rule.** Keep the test runner and its coverage package on the **same major** (TEST_RUNNER major == COVERAGE_PKG major) — a coverage package one major behind the runner pulls an incompatible internal API and fails in confusing ways.

### 3. Lockfile must be regenerated with the CI package-manager MAJOR

**Symptom.** `install --frozen-lockfile` (or the CI equivalent) rejects a lockfile that installs cleanly on your machine; or local and CI end up with different optional/peer dependencies present.

**Cause.** Different package-manager MAJORS hoist optional deps differently and write incompatible lockfile formats — a lockfile written by one major can be rejected (or silently re-resolved) by another.

**Fix.** Regenerate the lockfile with the **CI_PM_MAJOR**, commit that lockfile, and verify a clean frozen install reproduces CI's tree. Do not hand-edit the lockfile and do not bump the local PM major past what CI runs.

### 4. TipTap / ProseMirror — `addAttributes` casing and `renderHTML` scope

Two distinct traps in one extension API:

- **`addAttributes` keys must be camelCase.** ProseMirror attribute names are JS object keys; a kebab-case or snake_case key won't bind to the attribute the rest of the extension reads. Use `myAttr`, map to a DOM attribute (e.g. `data-my-attr`) inside `renderHTML`/`parseHTML` if needed.
- **`renderHTML` affects serialization only, not the live editing DOM.** Changing `renderHTML` changes the HTML the editor *outputs* (copy, getHTML, save). It does NOT change what you see while editing — that is the node/mark view. If an attribute "doesn't show" in the editor, `renderHTML` is the wrong place; if it "doesn't save", `renderHTML` is the right place.

### 5. ORM client vs schema drift — verify before believing it

**Symptom.** A TypeScript error against the ORM client (a missing model, field, or method) appears right after a schema change. The instinct is "the generated client drifted from the schema."

**Verify drift first (don't assume):**

1. Compare **GENERATED_CLIENT_PATH** mtime against **SCHEMA_PATH** mtime. If the client is OLDER than the schema, it is genuinely stale — regenerate it, then re-check.
2. If the client is NEWER than the schema (already regenerated) and the error persists, it is **not** drift — the type error is real (a renamed field, a wrong call, a relation that doesn't exist).

**Inline-mock corollary.** If the failing code path uses an inline ORM mock (in a test or a stub) and a model **method is missing from the mock**, the call returns a resolved `undefined` rather than throwing — the failure shows up downstream as "got undefined" far from the mock. Audit the mock for the method before chasing the consumer.

### 6. Lint the SPECIFIC new file before push

**Symptom.** Whole-repo lint exits 0 in CI/pre-push, yet a file you just added has real lint errors.

**Cause.** Repo-wide lint can be scoped by ignore globs, cache, or a `lint-changed`-style config that misses an untracked/new path, so a green whole-repo run hides a broken new file.

**Rule.** Lint the **specific new file by path** before push (`<linter> path/to/NewFile.tsx`), in addition to any whole-repo run. A targeted lint on the exact new path is the only reliable signal that the new file is clean.

## Decision framework

```
build/dev/test/CI failure
   │
   ├─ reload 500 "module factory is not available"? ── full 4-step HMR reset (trap 1)
   ├─ .tsx test import broke after vitest/vite upgrade? ── oxc jsx-automatic, NOT esbuild (trap 2)
   ├─ CI rejects lockfile / different deps than local? ── regen lockfile with CI_PM_MAJOR (trap 3)
   ├─ TipTap attr won't persist / won't show? ── camelCase key + renderHTML is serialization-only (trap 4)
   ├─ ORM type error after schema change? ── mtime(client) vs mtime(schema) BEFORE calling it drift (trap 5)
   └─ whole-repo lint green but new file broken? ── lint the new file by path (trap 6)
```

The unifying rule: **the layer that shows the error is often not the layer that holds the cause.** Identify the real layer (dev-server graph, transformer config, lockfile format, serialization vs editing DOM, codegen freshness, lint scope) before editing source.

## Safety gates

- **Never** treat a Turbopack stale-module 500 as a source bug before doing the full 4-step reset — you will rewrite working code chasing a phantom.
- **Never** restart more than one dev server during a reset; two on two ports hides whether the fix worked.
- **Never** fix the vitest jsx-preserve break with the esbuild jsx option — rolldown-vite ignores it; use oxc.
- **Never** mix test-runner and coverage-package majors.
- **Never** hand-edit a lockfile or push one generated by a different PM major than CI runs.
- **Never** call an ORM type error "drift" without comparing client mtime to schema mtime first.
- **Never** trust a green whole-repo lint as proof a new file is clean — lint the new file by path.
- **Never** delete a file because a reload 500 names it — the symbol may be live; see `react-lint-triage` before any deletion.

## Validation checklist

- [ ] For an HMR 500: all four reset steps done (kill server, clear BUILD_CACHE_DIR, one fresh DEV_SERVER_CMD, clear browser/automation cache).
- [ ] For a tsx-test break: oxc jsx-automatic set; esbuild jsx NOT used; runner and coverage on the same major.
- [ ] For a lockfile failure: lockfile regenerated with CI_PM_MAJOR; frozen install reproduces CI's tree.
- [ ] For a TipTap attribute: key is camelCase; renderHTML used only for serialization, not to fix editor display.
- [ ] For an ORM error: client-vs-schema mtime compared; classified as stale-regenerate vs real-error; inline mocks audited for missing methods.
- [ ] Before push: the specific new file linted by path (not only whole-repo).

## Output format

The skill emits one trap-resolution block:

```
BUILD TRAP
  Symptom:        <verbatim error / observed behavior>
  Apparent layer: <where the error showed>
  Real layer:     <where the cause actually lives>
  Trap:           <1..6 from the catalog>
  Recovery:       <the deterministic steps applied>
  Verified by:    <command/observation proving it's fixed>
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Re-edit source to clear `module factory is not available` | Fault is the stale HMR graph + cached chunk, not the file | Full 4-step reset: kill server, clear cache dir, one fresh server, clear browser cache |
| Plain browser reload to fix the HMR 500 | The dead factory survives a reload | Kill the dev server and clear the build cache dir |
| Add the esbuild jsx option to fix tsx tests on rolldown-vite | rolldown-vite uses oxc and ignores esbuild here | Set oxc jsx-automatic |
| Upgrade only the test runner, leave coverage a major behind | Incompatible internal API; confusing failures | Bump runner and coverage together to the same major |
| Hand-fix or commit a lockfile from the local PM major | Different majors hoist + format incompatibly; CI rejects it | Regenerate with CI_PM_MAJOR; verify frozen install |
| Put a kebab/snake key in TipTap `addAttributes` | Won't bind to the camelCase attribute the extension reads | Use camelCase keys; map to a DOM attribute in renderHTML/parseHTML |
| Edit `renderHTML` to make an attribute show while editing | renderHTML is serialization-only | Fix the node/mark view for editor display; renderHTML for output |
| Call an ORM type error "drift" and regenerate blindly | If the client is newer than the schema, it's a real error | Compare mtimes first; regenerate only if client is older |
| Trust whole-repo lint exit 0 | Ignore globs/cache/changed-scope can skip a new file | Lint the new file by its path before push |

## Portability rationale

This skill hardcodes no project, path, version number, package-manager name, or product term. The package manager, CI major, build-cache directory, dev-server command, test runner, coverage package, ORM, and codegen/schema paths are all named adapter inputs. The traps encode tooling behavior (Turbopack's HMR module graph, rolldown-vite/oxc transform precedence, package-manager lockfile hoisting, ProseMirror attribute semantics, ORM codegen freshness, lint scoping) that holds across any codebase using those tools; code samples are labeled illustrative so the principle ports, not the snippet.

## Cross-references

- `react-lint-triage` — analyzer/linter finding classification and the false-positive catalog (incl. never auto-deleting a file on an alias-blind dead-file signal); this skill defers all finding-judgment there.
- `data-fetching-states` — runtime loading/error/empty state verdicts (not build failures).
- `react19-migration` — deprecated/removed-API migration verdicts.
- `env-doctor` (claude-env-doctor-plugin) — generic broken-local-environment diagnosis (spawn / auth / missing-binary / version / DNS / encoding / config-shadowing); use it when the failure is environmental rather than a build/tooling trap.
- The project's package-manager, bundler, and ORM config — the source of truth for versions, cache paths, and codegen/schema locations.
