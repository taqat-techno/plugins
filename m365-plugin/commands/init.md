---
description: Set up Microsoft 365 for this user - enter the client ID from the admin (or get a message asking the admin for one), sign in with the browser, build the local profile, and choose the people and chats to remember.
argument-hint: "[status | setup | signin | profile | contacts]"
---

# /m365:init

Set up the Microsoft 365 plugin for this user. Everything is stored on this computer in the user's profile folder;
nothing needs admin rights or system environment variables. Run the steps in order and skip a step that is already
done. With no argument, run all of them. This is the first-run procedure: a new user is taken through it once.

| Argument | Does |
|---|---|
| (none) | all steps |
| `status` | step 1 only, report and stop |
| `setup` | step 2 |
| `signin` | step 3 |
| `profile` | step 4 |
| `contacts` | step 5 |

## 1. Where things stand

Call `m365_auth_status` and read it:

- `configured: true` and `signed_in: true` -> say who is signed in (and `auth_source` if it is a shared token) and go to step 4.
- `configured: true`, `signed_in: false` -> go to step 3.
- `configured: false` -> go to step 2.

## 2. Get access set up (first run)

The plugin signs the user in with their own work account, in the browser, through a Microsoft app that the company's
admin registers once. A user needs exactly two things: the app's **client ID** (and the tenant, if the admin gave one)
and their own sign-in. Ask ONE question: "Do you have the client ID from your admin?"

1. **Yes** -> ask for the Application (client) ID, and the tenant ID or domain if they have it. Call `m365_setup_save`
   with `client_id` (and `tenant`). Claude Code asks the user to confirm it. Then go to step 3 (sign in).
2. **No** -> call `m365_access_request`. Show the user the `message` it returns exactly as it is, tell them to send it to
   their IT or Microsoft 365 admin, and stop here. When the admin sends back the client ID, the user runs `/m365:init`
   again. The request lists exactly the permissions needed for the features they enabled, and nothing more.

**Another computer of the same user** is set up the same way: the same client ID and tenant, and the user signs in again
on that computer. Each computer holds its own sign-in.

**Never ask for, mention or suggest a token, a token file, an app secret, or copying another tool's or computer's sign-in.**
A normal user has none of these and must never be led to look for one. The only exception is the advanced setup below,
and only when the user brings it up themselves.

After saving, call `m365_auth_status` again to confirm it is configured.

### Advanced: only when the user says it themselves

Use these only when the user, unprompted, says the situation applies. Do not list them as choices.

- **"An app is already approved, but sign-in still asks for approval"** -> `m365_setup_save` with `scope_mode: "app"`
  (use the permissions already approved for the app) and go to step 3.
- **The app allows only one exact redirect address** (the sign-in failed with `REDIRECT_URI_MISMATCH` and the user or
  admin knows the address, for example `http://localhost:8400/callback`) -> `m365_setup_save` with `redirect_uri`, then
  `m365_sign_in` `mode: "interactive"`. If that app also needs a secret, the right fix is the admin turning on public
  client flows (`m365_access_request` gives the message); a secret file is something only the user may set, in their own
  terminal, and you never ask for it.
- **The user runs their own bot on THIS computer that already signs in as them, and asks to reuse its sign-in** -> they
  point the plugin at the bot's files themselves, in their own terminal (you cannot save file paths, on purpose):
  `node "<plugin folder>/server/cli.mjs" setup --client-id <id> --tenant <id> --token-file <path> --secret-file <path>`
  (or the plugin settings "Shared token file" and "App secret file"). Never ask them to paste a token or secret, and never
  suggest copying these files to another computer: another computer signs in on its own (above). Then call
  `m365_auth_status`; skip step 3.

## 3. Sign in

Skip this if the status shows a shared token (`auth_source: "shared token file"`): there is no sign-in in that mode.

Call `m365_sign_in` (no arguments). Tell the user exactly what the result says: a browser window opens for the work
account, or a page and a code to type. Then call `m365_auth_status` every few seconds until `signed_in` is true or
`sign_in.state` is `failed`.

On a failure show `sign_in.error.message` and its `hint` as they are, and offer the matching step:
- `SIGN_IN_DECLINED`, `CONSENT_NEEDED`, or the Microsoft page said "Need admin approval" -> the app's permissions are not approved yet.
  Call `m365_access_request`, show the message for the user to send to the admin, and stop. If the user says an
  approved app exists, use the `scope_mode: "app"` setup in step 2's advanced section.
- `PUBLIC_CLIENT_NOT_ENABLED` / `REDIRECT_URI_MISMATCH` -> the app registration needs a setting changed by the admin.
  Call `m365_access_request` and show its message for the user to send to the admin (it asks for exactly that setting),
  and stop. Do not offer a token, a secret or another tool's sign-in as a way around it.
- No browser available -> retry with `m365_sign_in` `mode: "device-code"`.

## 4. Build the profile

1. Call `profile_refresh_me`. It fills name, email, language, time zone and working days/hours from the account and
   from Outlook's own settings. Show the user the time zone and working hours it found, and any `notes` (for example
   when Outlook's display zone and working-hours zone disagree). Ask whether they are right; correct them with
   `profile_set` (an IANA zone such as `Africa/Cairo`, `working_days`, `work_start`, `work_end`). Values set that way are
   the user's own and are never overwritten by Outlook later. Ask their usual meeting length and set `meeting_minutes`.
2. Optional, only the user can set these (plugin settings, or `cli.mjs setup` in their own terminal):
   **"Email signature file"** (an HTML file; drafts then go out as HTML with that signature) and
   **"Files that may be attached"** (anywhere, the default: any file except keys and tokens, shown to the user before it is
   added; or folders: only the folders in "Folders files may be attached from"). Images pasted into the chat can always be
   attached. Mention these once; never ask for a path to set yourself.

## 5. Choose people to remember

1. Call `profile_suggest_contacts`. Show the list (name and email) as a short numbered list.
2. Ask which ones to keep and whether any should get a nickname or another spelling (aliases, for example the
   Arabic spelling). Call `profile_remember_contact` once per confirmed person. Never add anyone the user did not confirm.
3. Offer to remember a Teams chat: ask for a person or topic, use `teams_find_chat`, and after the user picks one call `profile_remember_chat` with a friendly name.

## 6. Finish

Call `profile_get` and give a three-line summary: signed-in account, time zone and working hours, number of
remembered contacts and chats. Tell the user that "email Mahmoud" and "message the project group" will now
resolve from the profile, and that `/m365:profile` shows or edits it any time.

Do not read mail, calendar or chats beyond what these steps need.
