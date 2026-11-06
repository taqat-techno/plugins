---
description: Show or edit the local Microsoft 365 profile - remembered contacts, aliases, Teams chats, time zone and working hours.
argument-hint: "[show | add <name> <email> | forget <name> | chat <name> | set <field> <value>]"
---

# /m365:profile

Works on the user's local profile only (a JSON file on this computer, no secrets in it). With no argument it
runs `show`.

| Usage | Does |
|---|---|
| `show` (default) | `profile_get`, then a short readable summary: identity, time zone, working hours, contacts (name, email, aliases), chats |
| `add <name> <email> [aliases]` | `profile_remember_contact`. If no email is given, `people_resolve` the name, show the match and save only after the user confirms |
| `forget <name or email>` | `profile_forget_contact`, then say how many were removed |
| `chat <name>` | find it with `teams_find_chat`, let the user pick, then `profile_remember_chat` with a friendly name |
| `forget-chat <name>` | `profile_forget_chat` |
| `set <field> <value>` | `profile_set` for name, email, timezone, language, meeting_minutes, working_days, work_start, work_end |

If the user is not signed in, say so and suggest `/m365:init`; `show`, `forget` and `set` still work without a sign-in.
Never invent an email address: only save one the user typed or confirmed.
