---
description: Set or inspect the sprint-recap target — base URL per environment, the login flow selectors, and the role credentials the capture stage logs in with. Credentials are written to .sprint-recap.local.json (gitignored) and are never printed back unmasked.
argument-hint: "[check | set | show]"
author: TAQAT Techno
version: 0.1.0
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# /sprint-recap-target

Manage `.sprint-recap.local.json` at the project root. `$ARGUMENTS` selects the
mode; the default is `check`, which is read-only.

## check (default)

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/check_config.py"
```

Verifies the config parses, git is not tracking it, `.gitignore` covers both the
config and `.sprint-recap/credentials/`, and no target points at production.
Passwords are printed masked. Report failures verbatim — a tracked config means
every role password is one push from being public, and the fix is
`git rm --cached` plus rotating those credentials.

## set

Write or update the config. Shape:

```json
{
  "targets": {
    "staging": {
      "base_url": "https://staging.example.com",
      "login": {
        "path": "/login",
        "username_selector": "input[name='username']",
        "password_selector": "input[name='password']",
        "submit_selector": "button[type='submit']",
        "success_selector": "text=Dashboard"
      },
      "roles": {
        "qa_admin": { "username": "qa.admin@example.com", "password": "..." }
      }
    }
  },
  "production_markers": ["prod", "production", "live"]
}
```

Before writing it:

1. Confirm `.sprint-recap.local.json` and `.sprint-recap/credentials/` are in
   `.gitignore`. Add them if missing — this is the only thing standing between a
   password file and the repo history.
2. Use disposable QA/staging accounts. Say so if the user offers anything that
   looks like a personal or production login.
3. Never echo a password back into the transcript. Confirm by role name.

## show

Print the parsed config with every password masked. There is no mode that prints
a secret — read the file directly if you genuinely need one.
