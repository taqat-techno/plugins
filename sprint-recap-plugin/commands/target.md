---
description: Set or inspect the sprint-recap target — base URL per environment, the login flow selectors, and the role credentials the capture stage logs in with. Credentials are written to .sprint-recap.local.json (gitignored) and are never printed back unmasked.
argument-hint: "[check | set | show]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# /sprint-recap:target

Manage `.sprint-recap.local.json` at the project root. `$ARGUMENTS` selects the
mode; the default is `check`, which is read-only.

## check (default)

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_config.py"
```

Verifies the config parses, git is not tracking it, `.gitignore` covers the
config, `.sprint-recap/credentials/` and `.sprint-recap/**/.auth/`, no target points at production,
and each non-local target has opted in with `"allow_capture": true`.
Passwords are printed masked. Report failures verbatim — a tracked config means
every role password is one push from being public, and the fix is
`git rm --cached` plus rotating those credentials.

## set

Write or update the config, **without ever taking a password in chat**: anything
typed into the conversation is stored in the session transcript. Write each role
with `"password": "<edit this file to add it>"` and tell the user to open
`.sprint-recap.local.json` in their editor and fill the passwords in themselves.
If the user pastes a password anyway, do not use or repeat it; tell them to
change it. Shape:

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
      "allow_capture": true,
      "roles": {
        "qa_admin": { "username": "qa.admin@example.com", "password": "<edit this file to add it>" },
        "sso_user": { "storage_state": "~/secrets/staging-sso-user.json" }
      }
    }
  },
  "production_markers": ["prod", "production", "live"]
}
```

Before writing it:

1. Confirm `.sprint-recap.local.json` and the whole `.sprint-recap/` folder
   (credential pages, run evidence, and any `.sprint-recap/**/.auth/` session
   cookies left by versions before 0.4) are in `.gitignore`. Add them if missing:
   this is the only thing standing between a password file and the repo history.
2. Add `"allow_capture": true` to a target only when the user confirms it is a
   disposable test environment. `localhost`, `*.localhost` and `*.test` hosts need
   no opt-in.
3. For SSO or MFA logins the form flow cannot drive, a role may instead name a
   Playwright storage state the user saved after signing in by hand
   (`storage_state`). Keep that file outside the repository.
4. Use disposable QA/staging accounts. Say so if the user offers anything that
   looks like a personal or production login.
5. Never echo a password back into the transcript. Confirm by role name.

## show

Print the parsed config with every password masked. There is no mode that prints
a secret — read the file directly if you genuinely need one.
