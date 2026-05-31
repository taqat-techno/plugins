---
name: react19-migration
description: Safe, behavior-preserving React 19 migration moves — forwardRef to ref-as-prop, useContext to use(Ctx), and the server/client split for attaching server-only metadata to a 'use client' layout. Owns the gate that each move is verified with a type-check then a build, and that no runtime behavior change is bundled into a migration commit. Activates when upgrading a React or Next codebase to React 19, when a linter flags a deprecated React API such as forwardRef, or when a metadata-export rule fires on a client component.
version: 0.1.0
last_reviewed: 2026-05-31
owns:
  - forwardRef to ref-as-prop conversion rule (use component-props type, destructure ref, drop redundant displayName)
  - useContext(Ctx) to use(Ctx) drop-in rule
  - server/client split pattern for server-only metadata on a 'use client' file
  - the behavior-preserving gate (type-check then build; no behavior change in a migration commit)
  - the "verify the codemod, never assume it is complete" rule
defers_to:
  - react-lint-triage (which deprecated-API findings exist and their severity)
  - admin-shell (layout / shell structure where the metadata split lands)
  - admin-forms (form components where forwardRef and ref-as-prop commonly appear)
  - project type-check + build tooling (the exact commands are adapter inputs)
user_invocable: false
---

# react19-migration

## Purpose

React 19 removes the need for `forwardRef`, ships `use(Context)` as a replacement for the `useContext` hook, and (in Next-style frameworks) tightens where server-only metadata may be exported. Each is a mechanical move that is easy to get subtly wrong by smuggling a behavior change into the same diff. This skill defines the safe pattern for each move and the gate that proves it was behavior-preserving.

## When to use

Activate when:

- Upgrading a React or Next codebase to React 19.
- A linter flags a deprecated React API (`forwardRef`, `useContext` where `use` is preferred, legacy ref handling).
- A metadata-export rule fires on a file marked `'use client'`.
- A codemod has run and you need to verify it rather than trust it.

Do NOT activate to add new features, change UX, or refactor for taste — those are separate commits.

## Inputs (adapter)

1. **React / Next version** — the target major (e.g. React 19.x) and whether a Next-style framework is present. Determines whether the metadata-split move applies at all.
2. **Language mode** — TypeScript or plain JavaScript. In TS, ref-as-prop uses the framework's component-props type; in JS, the gate is the build alone (no type-check), so lean harder on tests.
3. **Type-check command** — the project's no-emit type-check (named input, e.g. `<type-check-cmd>`). Never hardcode a specific invocation.
4. **Build command** — the project's production build (named input, e.g. `<build-cmd>`).
5. **Component-props type name** — the framework/library type that, in React 19, already includes `ref` as a prop (named input, e.g. `<component-props-type>`).

## Read-only investigation steps

1. **Confirm the installed React major.** Ref-as-prop and `use(Ctx)` are only safe on React 19+. If the lockfile still resolves React 18, the move is premature — stop.
2. **List the deprecated-API hits.** Take the findings from `react-lint-triage`; do not re-scan. Each hit is one migration unit.
3. **For each `forwardRef` site, read how `ref` is used.** Forwarded straight to a DOM node? Attached to an imperative handle? Conditionally? The usage dictates whether the move is a pure rename or needs care.
4. **For each `useContext` site, confirm it is at top-level hook scope.** `use(Ctx)` is a drop-in only at the same call sites a hook is legal.
5. **For each metadata-export lint hit, read the file's directive.** Is it `'use client'`? Does it currently export `metadata`? That combination is the only one the split targets.

## Decision framework

Each move below is behavior-preserving. The gate for every move is the same: run `<type-check-cmd>`, then run `<build-cmd>`. Do not proceed to the next file until both pass.

### Move 1 — `forwardRef` to ref-as-prop

In React 19, `ref` is an ordinary prop. The component can accept it directly.

```
Before (React 18)                      After (React 19)
─────────────────                      ─────────────────
const Input = forwardRef<              function Input({
  HTMLInputElement,                      ref,
  Props                                  ...props
>(function Input(props, ref) {         }: <component-props-type>) {
  return <input ref={ref} {...props}/>   return <input ref={ref} {...props}/>
});                                    }
Input.displayName = 'Input';           // displayName redundant — drop it
```

| Step | Rule |
|---|---|
| Type | Annotate props with `<component-props-type>` (includes `ref` in React 19 types). |
| Destructure | Pull `ref` out of props; spread the rest onto the element as before. |
| displayName | Drop it on a **named** function component — the name supplies it. Keep it only if the component is an anonymous expression with no inferable name. |
| Imperative handle | If the old ref drove `useImperativeHandle`, keep that hook unchanged — only the wrapper changes. |
| Gate | `<type-check-cmd>` first (catches a wrong props type before a slow build), then `<build-cmd>`. |

### Move 2 — `useContext(Ctx)` to `use(Ctx)`

```
Before:  const value = useContext(ThemeCtx);
After:   const value = use(ThemeCtx);
```

- Safe drop-in at top-level hook scope (the same places `useContext` was legal).
- Import `use` from `react`; remove the now-unused `useContext` import.
- Do NOT move the call into a conditional or loop "because `use` allows it" — that is a behavior change, not a migration. Keep the call site identical.
- Gate: `<type-check-cmd>` then `<build-cmd>`.

### Move 3 — server/client split for metadata

To attach server-only `metadata` to a layout that must stay `'use client'`, split the file. Do not delete the client directive and do not rewrite the logic.

```
layout.tsx ('use client', exports metadata)   ← lint error
        │  split, no logic change
        ▼
layout.tsx  (server, thin)            layout.client.tsx ('use client')
──────────────────────────            ────────────────────────────────
export const metadata = {...};        'use client';
import Client from                    // VERBATIM old component body —
  './layout.client';                  // hooks, state, handlers unchanged
export default function Layout(p){     export default function LayoutClient(p){
  return <Client {...p}/>;              ... old logic ...
}                                      }
```

| Rule | Detail |
|---|---|
| Thin server file | Only the `metadata` export + a render of the client sibling. No hooks, no state. |
| Verbatim client file | The old component body moves over byte-for-byte under `'use client'`. |
| Props pass-through | Forward all props/children unchanged so the boundary is invisible at runtime. |
| Scope discipline | A per-page metadata lint rule **ignores layout inheritance** — do NOT restructure the layout tree just to silence it. Split the one file; leave inheritance alone. |
| Gate | `<type-check-cmd>` then `<build-cmd>` — the build is what validates the server/client boundary. |

### Sequencing

```
one finding ──► apply the matching move ──► <type-check-cmd> ──► <build-cmd> ──► commit ──► next finding
                                                 │ fail              │ fail
                                                 ▼                   ▼
                                            revert this file, diagnose, retry
```

One move per commit. Never batch unrelated moves; a failed gate must point at exactly one change.

## Safety gates

- **Never** migrate without a passing type-check (TS) — in JS, never migrate without a passing build and green tests.
- **Never** change runtime behavior inside a migration step (no new conditionals, no reordered effects, no "while I'm here" tweaks).
- **Never** assume a codemod finished the job — re-read each touched file and run the gate.
- **Never** apply ref-as-prop or `use(Ctx)` while the lockfile still resolves React 18.
- **Never** delete a `'use client'` directive to satisfy a metadata rule — split the file instead.
- **Never** restructure a layout tree to satisfy a per-page metadata rule that ignores inheritance.
- **Never** bundle multiple unrelated migration moves into one commit.

## Validation checklist

Before committing a migration change:

- [ ] Installed React major is 19+ (lockfile confirmed) for ref-as-prop and `use(Ctx)`.
- [ ] `forwardRef` removed; props typed with `<component-props-type>`; `ref` destructured; spread preserved.
- [ ] Redundant `displayName` dropped on named function components only.
- [ ] `useContext` call sites unchanged except the `useContext` to `use` rename; imports cleaned.
- [ ] Metadata split leaves the client logic verbatim and forwards all props/children.
- [ ] Layout inheritance was NOT restructured to satisfy a per-page rule.
- [ ] `<type-check-cmd>` passes (TS).
- [ ] `<build-cmd>` passes.
- [ ] Diff contains zero behavior changes (review the diff, not just the result).
- [ ] One move per commit.

## Output format

Emit one MIGRATION CHECKLIST per file:

```
MIGRATION CHECKLIST — <relative/path/to/file>
  Move: <forwardRef→ref-as-prop | useContext→use | metadata server/client split>
  Trigger: <lint rule id or finding from react-lint-triage>
  Edits:
    - <one line per mechanical edit, e.g. "remove forwardRef wrapper, type props as <component-props-type>">
    - <e.g. "drop redundant displayName">
  Behavior change: NONE  (required — anything else blocks the commit)
  Gate:
    [ ] <type-check-cmd>  → pass/fail
    [ ] <build-cmd>       → pass/fail
  Commit: <one move, one file group>
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Apply ref-as-prop while React 18 is still installed | `ref` is not a prop in 18 — silently broken refs | Confirm React 19+ in the lockfile first |
| Keep `displayName` after converting a named function component | Redundant; the function name already provides it | Drop it on named components |
| Move `use(Ctx)` into a conditional during migration | That is a behavior change disguised as a rename | Keep the identical call site; defer any logic change |
| Skip the type-check and go straight to build | A wrong props type surfaces late and slow | Type-check first, then build |
| Trust the codemod output without reading the files | Codemods miss imperative handles, anonymous components, edge cases | Re-read each touched file and run the gate |
| Delete `'use client'` to allow a `metadata` export | Breaks every hook/state/handler in the file at runtime | Split into thin server file + verbatim client sibling |
| Restructure the layout tree to satisfy a per-page metadata rule | The rule ignores layout inheritance; you broke structure for a lint | Split the single file; leave inheritance untouched |
| Batch forwardRef + use(Ctx) + metadata split in one commit | A failed gate cannot be traced to one change | One move per commit |

## Portability rationale

The moves are React/Next-version facts, not project facts. Everything project-specific is an adapter input: the React/Next version, the language mode, the type-check command, the build command, and the component-props type name. The skill names them and never hardcodes a tool invocation, a file path, or a project's naming convention — so it applies to any React 19 upgrade in any workspace.

## Cross-references

- `react-lint-triage` — supplies the deprecated-API findings (forwardRef, useContext) and their severity; this skill consumes them, it does not re-scan.
- `admin-shell` — the layout/shell structure where the metadata server/client split typically lands.
- `admin-forms` — form input components where `forwardRef` and ref-as-prop most commonly appear.
- `react-doctor` (skill) — broader diagnostic scan that may route a deprecated-API hit here.
