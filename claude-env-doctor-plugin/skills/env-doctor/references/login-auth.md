# Claude Code Login / Auth Diagnosis

Diagnose and repair Claude Code authentication failures without ever printing a
token. This reference covers the common 401-after-login loop, how to read the
credential file shape against the org type, a safe fix pattern, the per-project
env override trap, and rules for reporting safely.

Throughout this document, never echo a token, API key, or any credential value.
Report only its **shape** (key name, prefix, length), never its contents.

## The 401-loop symptom

The hallmark of an account/credential mismatch is: **login appears to succeed,
the status line shows you as authenticated, but every actual request returns
HTTP 401.** Nothing you type works, yet re-running login keeps "succeeding."

Typical observations:

- Interactive login completes and reports success.
- The status line shows an auth label such as a logged-in account or "API key".
- The first real request (and every request after) fails with 401 Unauthorized.
- Logging out and back in does not break the loop — it re-writes the same wrong
  credential shape.

The root cause is almost never a "bad password." It is an **account-type or
credential-shape mismatch**: the credential that got written does not match the
billing/identity model the organization expects.

## Why the mismatch happens

Claude Code can authenticate through more than one flow, and each writes a
differently shaped credential:

- A **subscription / interactive OAuth** flow writes an OAuth-style token tied
  to a personal or subscription login.
- An **API / Console billing** flow expects an API key issued for that org.

A 401 loop occurs when the **written credential shape contradicts what the org
accepts**. Two mirror-image cases:

- A subscription OAuth token is present, but the org is configured for
  API/Console billing → the API rejects the OAuth token → 401 on every call.
- An API key is present (or inherited from the environment), but the active
  context expects the interactive subscription login → 401 on every call.

The login UI cannot detect this — it only confirms that *a* credential was
stored, not that the stored credential is the *right kind* for this org.

## Diagnosis: compare shape against org type

Diagnosis is a comparison, not a guess. Compare the **shape** of the stored
credential against the **org/billing type** the workspace expects. Do not read
or print any value.

Step 1 — Identify the org/billing type the request runs under:

- Look at the org banner / billing model shown for the active organization
  (subscription login vs. API / Console billing).
- Note which login method the workspace or settings pin, if any.

Step 2 — Identify the credential *shape* that is actually stored:

- Determine the credential file location for the platform (a JSON credentials
  file in the Claude config directory, or an OS keychain entry on platforms
  that use one).
- Inspect only the **shape**: which key names are present, the credential
  *kind* (OAuth-style token vs. API key), and a non-revealing prefix/length.
  Never display the value.

Step 3 — Check the status-line auth label correctly:

- The status-line auth label is a **slot name, not proof**. A label such as
  "API key" means that *slot* is selected — it does **not** prove an
  environment variable is actually set, non-empty, or valid.
- Confirm separately whether the env var the slot refers to is genuinely
  present and non-empty (report presence/shape only, never the value).

Step 4 — Compare:

| Org / billing expects | Stored credential shape | Verdict |
|---|---|---|
| Subscription / interactive | Subscription OAuth-style token | Match |
| API / Console billing | API key for that org | Match |
| Subscription / interactive | API key (often env-inherited) | Mismatch → 401 loop |
| API / Console billing | Subscription OAuth-style token | Mismatch → 401 loop |

If the row is a "Mismatch," the 401 loop is explained and the fix is to pin the
correct flow and re-login.

## Safe fix pattern

Fix the mismatch deterministically. Describe every step **without printing any
token**.

1. **Pin the login method to the correct flow in settings.** Set the workspace
   (or user) settings to force the flow the org expects — the interactive
   subscription login, or the API-key flow — so the next login cannot silently
   write the wrong shape again. Pinning is what breaks the loop.

2. **Back up the credential file before changing it.** Copy the existing
   credentials file (or export the keychain entry) to a timestamped backup so
   the prior state is recoverable. Back up the *file*; never read its contents
   into the transcript.

3. **Clear and re-login through the pinned flow.** Remove or rename the stale
   credential so the next login writes a fresh credential of the correct shape,
   then run the interactive login. Confirm success by making one real request
   and checking it returns non-401 — do not confirm by the login UI alone.

4. **Verify by shape, not by value.** After re-login, re-inspect the credential
   *shape* and confirm it now matches the org type from the diagnosis table.

Example (illustrative — not required): a workspace whose org uses API/Console
billing keeps writing a subscription OAuth token. Pin the API-key flow in
settings, back up the credentials file, clear the OAuth token, then log in with
the API-key flow. The next request returns 200 instead of 401.

## Per-project env override trap

An auth token or API key placed in a **per-project committed settings env
block** silently overrides the user's interactive login for every session
launched from that directory. The user logs in normally, but the committed env
value wins — producing a confusing 401 loop (or a wrong-identity session) that
"follows the folder."

Why this is a trap:

- It is **committed**, so it ships to everyone who clones the repo and applies
  to every session started there — not just the author's machine.
- It **silently overrides** interactive login; the status line may still show
  the logged-in account while requests actually use the committed value.
- It risks **leaking a credential into version control**, which is a secret
  exposure on its own.

Recommended alternatives:

- **Per-project LOCAL settings (gitignored).** Put any auth env in a local,
  untracked settings file (the project-local settings that are excluded from
  version control) so it stays on the developer's machine and is never
  committed.
- **Wrapper launch.** Set the auth env var in the shell or a launch wrapper
  script that starts Claude Code for that project, instead of baking it into
  committed settings. The variable lives in the session, not in the repo.
- If a committed env block already contains a credential, treat it as a leaked
  secret: remove it, rotate the credential, and move it to local settings or a
  wrapper. Report only that a credential-shaped value is present and where —
  never its value.

## Safe reporting rules

When reporting findings (to the user, a log, or a diagnostic summary), **never
echo tokens, keys, or env values.** Redact by key-name pattern and report only
an opaque shape.

Redaction rules:

- **Redact by key-name pattern.** Treat any key whose name matches
  token / key / secret / auth / password / credential (case-insensitive) as
  sensitive and never print its value.
- **Report shape, not value.** For a sensitive value, report at most:
  the **key name**, the credential **kind** (OAuth-style token vs. API key),
  a short **non-revealing prefix** plus a **length**, and **presence** (set /
  empty / absent). Never the full or partial secret beyond a non-revealing
  prefix.
- **Mask consistently.** Replace the value with a fixed placeholder so the
  output cannot be reversed.

Example (illustrative — not required) of a safe report line:

```
ANTHROPIC_API_KEY: present, kind=api-key, prefix="sk-…", length≈100  [value redacted]
credentials file: present, kind=oauth-token  [value redacted]
status-line auth label: "API key" (slot name only — not proof env var is set)
```

What the line conveys without leaking anything: which key, what kind, roughly
how long, and that it exists — enough to spot a shape mismatch, with the value
itself never shown.

Hard rules:

- Never print a credential value, even partially beyond a short non-revealing
  prefix used only to confirm kind.
- Never copy a credential file's contents into the transcript; inspect shape
  and report shape.
- Prefer presence/absence and shape comparisons over any value disclosure.
