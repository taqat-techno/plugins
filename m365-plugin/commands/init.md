---
description: Set up Microsoft 365 for this user - choose how to get access (a client ID from the admin, a message asking the admin for one, or reusing a sign-in another tool already holds), sign in, build the local profile, and choose the people and chats to remember.
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

The plugin signs the user in through a Microsoft app that the company's admin registers once. Ask ONE question and
let the user pick the situation that fits them:

1. **"My admin gave me a client ID"** -> ask for the Application (client) ID, and the tenant ID or domain if the admin
   gave one. Call `m365_setup_save` with `client_id` (and `tenant`). Claude Code asks the user to confirm it.
2. **"I don't have one yet"** -> call `m365_access_request`. Show the user the `message` it returns exactly as it is,
   tell them to send it to their IT or Microsoft 365 admin, and stop here. When the admin sends back the client ID,
   the user runs `/m365:init` again and picks the first option. This is the normal route for a new user: the request
   lists exactly the permissions needed for the features they enabled, and nothing more.
3. **"My own bot or another tool already signs in as me, and I want to reuse it (on my own computer)"** -> ask for:
   the client ID and tenant that tool uses, the PATH of the file holding its refresh token, and the PATH of the file
   holding the app's secret (if the app has one). **You cannot save file paths yourself, on purpose: only the person
   at the keyboard may point the plugin at a credential file.** Give the user this command to run in their own terminal
   (replace the placeholders; never paste a token or secret into the chat):
   `node "<plugin folder>/server/cli.mjs" setup --client-id <id> --tenant <id> --token-file <path> --secret-file <path>`
   (the plugin folder is where this plugin is installed; the same values can instead go in the plugin settings
   "Shared token file" and "App secret file"). The command checks each file looks like a token or secret and never shows
   it. No new admin approval is needed, because that tool's sign-in was already approved. Then call `m365_auth_status`:
   it picks the change up without a restart. The plugin writes a renewed token back to the same file, as its owner does.
   Skip step 3.
4. **"An approved app exists, but sign-in still asks for approval"** -> `m365_setup_save` with `scope_mode: "app"`
   (use the permissions already approved for the app) and go to step 3.

After saving, call `m365_auth_status` again to confirm it is configured.

## 3. Sign in

Skip this if the status shows a shared token (`auth_source: "shared token file"`): there is no sign-in in that mode.

Call `m365_sign_in` (no arguments). Tell the user exactly what the result says: a browser window opens for the work
account, or a page and a code to type. Then call `m365_auth_status` every few seconds until `signed_in` is true or
`sign_in.state` is `failed`.

On a failure show `sign_in.error.message` and its `hint` as they are, and offer the matching step:
- `SIGN_IN_DECLINED`, `CONSENT_NEEDED`, or the Microsoft page said "Need admin approval" -> the app's permissions are not approved yet.
  Call `m365_access_request`, show the message for the user to send to the admin, and stop. If the user knows an
  approved app exists, offer option 4 of step 2.
- `PUBLIC_CLIENT_NOT_ENABLED` / `REDIRECT_URI_MISMATCH` -> the app registration needs a setting changed; show the hint
  (or give the user `m365_access_request`'s message for the admin).
- No browser available -> retry with `m365_sign_in` `mode: "device-code"`.

## 4. Build the profile

1. Call `profile_refresh_me`. It fills name, email and language from the account and sets the time zone to this
   computer's zone. Show the user the time zone it chose and ask whether it is right; if not, call `profile_set` with the correct IANA name (for example `Africa/Cairo`).
2. Ask which days and hours they work (many users work Sunday to Thursday). Call `profile_set` with
   `working_days`, `work_start`, `work_end`. Ask their usual meeting length and set `meeting_minutes`.

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
