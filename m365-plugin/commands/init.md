---
description: Set up Microsoft 365 for this user - check the app settings, sign in, build the local profile (who you are, time zone, working hours) and choose the people and chats to remember.
argument-hint: "[status | signin | profile | contacts]"
---

# /m365:init

Set up the Microsoft 365 plugin for this user. Everything is stored on this computer in the user's
profile folder; nothing needs admin rights or system environment variables. Run the steps in order
and skip a step that is already done. With no argument, run all of them.

| Argument | Does |
|---|---|
| (none) | all steps |
| `status` | steps 1-2 only, report and stop |
| `signin` | step 2 |
| `profile` | step 3 |
| `contacts` | step 4 |

## 1. Check the app settings

Call `m365_auth_status`.

- If `configured` is false, the plugin has no Microsoft app (client) ID. Tell the user to enter it in the
  plugin's settings ("Microsoft app (client) ID"), or set `M365_CLIENT_ID`, and point to
  `docs/APP_REGISTRATION.md` in this plugin: an admin registers one app for the company, once. Stop here.

## 2. Sign in

If `signed_in` is true, say who is signed in and continue.

Otherwise call `m365_sign_in` (no arguments). Tell the user exactly what the result says:
a browser window opens for the work account, or, for a device code, the page and the code to type.
Then call `m365_auth_status` every few seconds until `signed_in` is true or `sign_in.state` is `failed`.

On a failure show `sign_in.error.message` and its `hint` as they are:
- `CONSENT_NEEDED`: an admin must approve the app's permissions. Give the user the hint to forward.
- `PUBLIC_CLIENT_NOT_ENABLED` / `REDIRECT_URI_MISMATCH`: the app registration needs a setting changed; show the hint.
- No browser available: retry with `m365_sign_in` `mode: "device-code"`.

## 3. Build the profile

1. Call `profile_refresh_me`. It fills name, email and language from the account and sets the time zone to this
   computer's zone. Show the user the time zone it chose and ask whether it is right; if not, call `profile_set` with the correct IANA name (for example `Africa/Cairo`).
2. Ask which days and hours they work (many users work Sunday to Thursday). Call `profile_set` with
   `working_days`, `work_start`, `work_end`. Ask their usual meeting length and set `meeting_minutes`.

## 4. Choose people to remember

1. Call `profile_suggest_contacts`. Show the list (name and email) as a short numbered list.
2. Ask which ones to keep and whether any should get a nickname or another spelling (aliases, for example the
   Arabic spelling). Call `profile_remember_contact` once per confirmed person. Never add anyone the user did not confirm.
3. Offer to remember a Teams chat: ask for a person or topic, use `teams_find_chat`, and after the user picks one call `profile_remember_chat` with a friendly name.

## 5. Finish

Call `profile_get` and give a three-line summary: signed-in account, time zone and working hours, number of
remembered contacts and chats. Tell the user that "email Mahmoud" and "message the project group" will now
resolve from the profile, and that `/m365:profile` shows or edits it any time.

Do not read mail, calendar or chats beyond what these steps need.
