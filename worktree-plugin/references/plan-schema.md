# Plan schema for parallel execution

A plan is **delegation-ready** when the Main Agent can answer these without
re-reading prose:

```
What is ready?   What is blocked?   What can run concurrently?
Who owns each component?   Which packages overlap?
Whose test is it?   What is done?   What must never be built?
What must integrate before something else starts?
```

Eight fields per work package. Nothing else. **The plan does not become an
orchestration database** — anything git, the filesystem, or the session list can
answer is deliberately absent.

## The eight fields

| Field | Answers | Required |
|---|---|---|
| `id` | identity | always |
| **Prerequisites** | *what is ready?* — package level | always (`—` if none) |
| **Owns** | *what can run concurrently?* — the collision key | always |
| **Laneable** | *may this be delegated at all?* | always |
| Tasks + `depends_on` | order inside the package | always |
| **Tests**, each tagged `[lane]` / `[integration]` / `[release]` | *whose test is it?* | always |
| **Acceptance** | definition of done | always |
| **Must NOT be built** | negative scope | always (`—` if none) |
| **Integration contract** | what the other side of a shared seam may assume | only where a seam exists |

### Owns — the field that decides concurrency

`Owns` is a set of **components**, not file paths: modules, packages,
directories, services, schemas, registries. Semantic ownership, not textual
collision.

> **Two work packages may not run concurrently if their `Owns` sets intersect**,
> unless an explicit integration contract governs the shared surface.

This is the single most load-bearing field. Without it, concurrency is a
judgement call made under time pressure, repeatedly, by whoever is delegating.

### Laneable — the field most often missing

`yes` · `no — integration` · `no — acceptance` · `no — external dependency`

Some work must run on the trunk: cross-cutting composition, release acceptance,
anything touching every component. Marking it at plan time stops a lane being
provisioned for work that can never be isolated — and stops the Main Agent
rediscovering that fact halfway through a wave.

### Test levels

| Tag | Owner | Runs |
|---|---|---|
| `[lane]` | the worker | inside its own worktree, before reporting |
| `[integration]` | Main Agent | after two or more lanes converge |
| `[release]` | Main Agent | on the integrated trunk, against a stated expectation |

**State the release expectation as a number.** A run that reports the *old*
component count is a false pass: the new component simply did not build, and
nothing in the output says so.

## Readiness

Exactly one rule, computable, no ambiguity:

```
ready(task) ⇔ every package Prerequisite is complete
            ∧ every task depends_on is complete
            ∧ no unresolved external blocker
```

**Both levels, always.** Dependencies split across two documents with no stated
join rule is the defect that most reliably produces a wrongly-started lane —
computing readiness from the task level alone assigns work whose *package* is
several levels deep in unmet prerequisites.

If the plan cannot support this computation, **the Main Agent must report the
ambiguity and refuse to dispatch.** It must not guess.

## Worked example

```markdown
## WP-07 — Session token rotation · GATE 3

**Objective.** Refresh tokens rotate on use and a replayed token is rejected.

**Prerequisites.** WP-02 (auth schema), WP-05 (audit log)
**Owns.** `auth/tokens`, `auth/middleware`
**Laneable.** yes

| Task | Description | Depends on |
|---|---|---|
| WP-07-T01 | Rotation on refresh; old token marked spent | — |
| WP-07-T02 | Replay of a spent token returns 401 and writes an audit row | T01 |
| WP-07-T03 | Concurrent-refresh race resolves to one live token | T01 |

**Tests.**
- `[lane]`        rotation issues a new token and marks the old spent
- `[lane]`        NEGATIVE: a replayed spent token is rejected — assert the refusal, not a status code
- `[lane]`        `auth/tokens` builds and tests with no `auth/middleware` present
- `[integration]` an in-flight session survives rotation end-to-end through the gateway
- `[release]`     full suite; expected component count 14 — a run reporting 13 is a FALSE PASS

**Acceptance — Gate 3.**
1. A refresh always invalidates its predecessor.
2. A replayed token never authenticates and always audits.
3. No token state is stored outside `auth/tokens`.

**Integration contract.** `auth/middleware` may assume `validate(token)` raises
`TokenSpent`; it must not inspect token storage directly. Seam owner: WP-07.

**Must NOT be built.** No new session store. No client-side token cache.
No change to the login flow.
```

About thirty lines, and every delegation question is answered.

## Audit checks

Run over an existing plan, these find the defects that cost the most:

| Check | Why |
|---|---|
| Package has no `Owns` | concurrency is unknowable — **report it, never guess it** |
| Prerequisites at two levels with no join rule | the wrongly-started-lane defect |
| Two packages with intersecting `Owns` scheduled together | a collision that has already happened |
| No `Laneable` verdict | a lane may be provisioned for un-isolatable work |
| Tests present but untagged | test ownership is undefined at exactly the moment it matters |
| **A blocker note that never names its own row's subject** | boilerplate copied from a sibling row. Both such rows once turned out to be startable — one blocker was an *instruction* (*"inspect the localisation first"*), not a bar |
| `Must NOT be built` absent on a package with a tempting adjacent feature | scope drift has no brake |

## Proportion

Do not apply this to a plan that will not be executed in parallel. One phase, or
no independent packages, means the overhead buys nothing. **Add only the
metadata that makes safe delegation computable** — and add it as you write, not
as a retrofit.
