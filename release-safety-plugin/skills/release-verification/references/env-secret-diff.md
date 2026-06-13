# Env-secret diff and connection-target guard — by name only

Two pre-promotion checks that must never print a secret value:

1. **Env-key diff** — does the target environment have every env key the release needs?
2. **Connection-target guard** — is the command about to run pointing at the intended remote, or has it silently fallen back to a local DB / sqlite?

Both operate on **key names, presence, and shape only**. Never echo a value.

## Part 1 — Env-key diff (source -> target)

A migration or feature that reads an env key the target lacks will **fail the deploy** — and usually mid-deploy, after some steps have already run. Catch it before promoting.

### Build the two key sets

- **Required keys** — what the new code/migration actually reads. Derive from the code/config that is being promoted (env-var reads, settings references, the deploy descriptor's declared env). Names only.
- **Target keys** — what the target environment already provides. Derive from the target's env/secret store or deploy config (`env_source_of_truth`). Names and presence only — request the *list of keys*, not their values.

### Diff and classify

```
required \ target  -> ABSENT in target   (deploy-blocking: code will read an unset key)
target  \ required  -> extra in target    (usually harmless; note it)
required ∩ target   -> present            (ok by name; value correctness is out of scope here)
```

Report each as `KEY_NAME: present | ABSENT in target`. A single ABSENT key that the release needs is a **no-go** until added.

### Redaction rule

If a tool only returns values, redact to shape before recording: `present (opaque, redacted)`, `present (URL-shaped, redacted)`, `ABSENT`. Never the literal value, never a partial value (partials still leak).

## Part 2 — Connection-target guard (print resolved host FIRST)

A command meant for a remote database can **silently fall back to a local DB or an on-disk sqlite file when the public connection URL is empty/unset**, then "succeed" against the wrong target — producing a confidently false verification.

### The deterministic guard

Before running ANY environment-touching command, resolve and print the connection **host / database name** (not the credentials):

1. Read the connection setting the command will use (e.g. the public connection URL key).
2. If it is empty/unset, the command will fall back — STOP and report `fallback-risk=yes`.
3. If set, parse out the **host and database name only** and print them: `Connection target: <host>/<db>`.
4. Compare against intent: if `intended=remote` but the resolved host is `localhost` / `127.0.0.1` / a local sqlite path -> **abort**, do not run.

### Parsing without leaking

A connection URL has the shape `scheme://user:secret@host:port/dbname`. Extract and print only `host:port/dbname`; drop the `user:secret@` userinfo entirely. Never print the scheme's credentials. If you cannot parse safely, report the host as `unparseable — do not run` rather than echoing the raw URL.

### What "intended" means

The caller states `intended=remote` (verifying/operating against a deployed environment) or `intended=local` (deliberately local). The guard only blocks the mismatch: remote-intended but locally-resolved. Local-intended-and-local is fine.

## Platform note (labeled examples only)

> Example (illustrative — not required): a maintenance command reads a public connection URL key; on a misconfigured target that key is blank, so the framework defaults to a bundled sqlite file. Without the guard, the command runs against sqlite and reports success while the real remote database is untouched. With the guard, the first line printed is `Connection target: <empty> -> fallback-risk=yes`, and the run is aborted before any false "verified."

The diff and the guard are engine- and provider-neutral: only the *key names* and the *connection setting name* differ per project; the by-name discipline and the print-target-first rule do not.
