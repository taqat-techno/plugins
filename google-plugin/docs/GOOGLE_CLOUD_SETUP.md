# Setting up your own Google client for the Google plugin

This plugin signs in to Gmail, Google Calendar and Google Drive with **your own** Google Cloud "OAuth client". You create
the client once, in about 15 minutes, in a web browser, and no programming is needed. At the end you have one small JSON
file on your computer. The plugin only needs to know where that file is.

Google changes the wording and layout of its console from time to time. If a button below has a slightly different
name, look for the closest match; the order of the steps stays the same.

## What you need

- The Google account whose mail, calendar and files you want to use. Sign in to it in your browser.
- A computer with a browser. Sign-in opens a browser on the computer where the plugin runs.

## Step 1: create a project

1. Open <https://console.cloud.google.com/> and sign in with your Google account.
2. At the top of the page, click the project picker, then **New project**.
3. Give it any name, for example `My assistant`, and click **Create**. Make sure the new project is selected at the
   top of the page before you continue.

## Step 2: turn on the six APIs

The plugin talks to Google's own Workspace MCP servers, which need both the product API and its MCP API. In the menu,
go to **APIs & Services** > **Library**. Search for each of these, open it, and click **Enable**:

1. **Gmail API** and **Gmail MCP API**
2. **Google Calendar API** and **Calendar MCP API**
3. **Google Drive API** and **Drive MCP API**

Source: [Configure the Google Workspace MCP servers](https://developers.google.com/workspace/guides/configure-mcp-servers), steps "Enable the APIs" and "Enable the MCP services". Enable all six even if you plan to use only one
module now; turning modules on later then needs no trip back here. If one is off, sign-in still works, but that module's
calls fail with `GOOGLE_FORBIDDEN` and Google's message says which API.

The plain APIs (not only the MCP ones) matter even more if you switch on the REST fallback (`GOOGLE_REST_FALLBACK=1`):
its tools call them directly. Their service names are `gmail.googleapis.com` (Gmail API), `drive.googleapis.com`
(Google Drive API) and `calendar-json.googleapis.com` (Google Calendar API). The **CalDAV API** in the same library is a
different API and does not count. A 403 saying "Google Calendar API has not been used in project ... or it is disabled"
means the Google Calendar API is off.

## Step 3: set up the consent screen

This is the page Google shows when you sign in ("App X wants to access your Google Account").

1. Go to **APIs & Services** > **OAuth consent screen**. On newer consoles this area is called **Google Auth Platform**,
   with pages named Branding, Audience, Clients and Data Access.
2. Fill in the app name (anything, for example `My assistant`; Google refuses names that contain "Google"), and use your email as both the support email and the
   developer contact.
3. Choose who can use the app:
   - If the console offers **Personal** mode, use it. Google's help page on unverified apps says an app created that way
     is "restricted exclusively to your Google Account, does not display the unverified app screen, and does not need to
     go through verification" ([Unverified apps](https://support.google.com/cloud/answer/7454865)).
   - Otherwise choose **External**. While the app is in **Testing**, add your own Gmail address under **Test users**.
4. You don't need to add scopes here. The plugin asks for its permissions when you sign in (see the table below).

## Step 4: create the Desktop client and download the JSON

1. Go to **APIs & Services** > **Credentials** (or **Google Auth Platform** > **Clients**).
2. Click **Create credentials** > **OAuth client ID**.
3. For **Application type**, choose **Desktop app**. This matters: a "Web application" client does not work, and the
   plugin tells you so (`CLIENT_TYPE_WRONG`).
4. Give it any name and click **Create**.
5. Open the client again and tick **Use this client for an AI-powered agent**, then save. Google's MCP servers refuse
   calls from a client without it (source: [Configure the Google Workspace MCP servers](https://developers.google.com/workspace/guides/configure-mcp-servers)).
6. Click **Download JSON**. Save the file somewhere private on your computer, for example in a folder only you use.
   Don't put it in a shared or synced folder. **Never paste its contents into a chat**, including a chat with an AI
   assistant.

Google itself says a desktop app's client secret cannot really be kept secret. Treat the file as private anyway:
whoever has it can pose as your app.

## Step 5: tell the plugin where the file is

Use one of these:

- **Claude Code:** open the plugin's settings and put the full path of the JSON file in **Google client JSON file**.
- **Any other host (agent bot, terminal):** set the environment variable `GOOGLE_CLIENT_SECRET_FILE` to the full path.

Optional settings:

- **Modules** (`GOOGLE_MODULES`): `gmail`, `calendar` and `drive`, comma-separated. Empty means all three. Every
  enabled module's permission is asked for at the same sign-in. Turning a module on later needs a new sign-in.
- **Read-only mode** (`GOOGLE_READONLY=true`): asks only for read permissions, and no tool can change your data.
- `GOOGLE_PLUGIN_HOME`: the folder where the plugin keeps your sign-in (`token-cache.json`). The default is
  `.google-plugin` in your home folder.

## The permissions it asks for

Every enabled module's permission is requested at the **first** sign-in, so you sign in once. The plugin also asks for
`openid` and `email`, which only tell it which account you signed in with.

The **class** column is how Google rates each permission. Restricted permissions need the strictest review before an app
may be offered to the public. For your own private app, they mean the "unverified app" screen at sign-in (see Step 6).

| Module | Normal mode | Read-only mode | Google's class | Source |
|---|---|---|---|---|
| Gmail | `https://www.googleapis.com/auth/gmail.modify` | `https://www.googleapis.com/auth/gmail.readonly` | **Restricted** (both) | [Gmail API scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) |
| Calendar | `https://www.googleapis.com/auth/calendar.events` | `https://www.googleapis.com/auth/calendar.events.readonly` | **Not verified**: Google's Calendar scope page lists these without a class | [Calendar API scopes](https://developers.google.com/workspace/calendar/api/auth) |
| Calendar | `https://www.googleapis.com/auth/calendar.calendarlist.readonly` (both modes) | (same) | **Not verified** (as above) | [Calendar API scopes](https://developers.google.com/workspace/calendar/api/auth) |
| Drive | `https://www.googleapis.com/auth/drive` | `https://www.googleapis.com/auth/drive.readonly` | **Restricted** (both) | [Drive API scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth) |
| (sign-in) | `openid`, `email` | (same) | **Not verified** as a class. These are the basic sign-in scopes that Google's 7-day rule names as its exception (see below). | [OAuth 2.0 overview](https://developers.google.com/identity/protocols/oauth2) |

Why these permissions and not others:

- **Gmail:** `gmail.modify` can read, label, archive and draft. Google's scope page says it "does not allow immediate,
  permanent deletion of threads and messages". The plugin **never** asks for full mailbox access
  (`https://mail.google.com/`), the only Gmail permission that can permanently delete. A test checks this.
- **Calendar:** `calendar.events` reads and edits events. It doesn't cover listing your calendars: Google's reference
  for listing calendars accepts only the calendar-list permissions or broader ones. So the narrow
  `calendar.calendarlist.readonly` is added instead of the broader `calendar.readonly`. Neither one can delete a whole
  calendar.
- **Drive:** `drive` lets the plugin search and read your existing files. The narrower `drive.file` (Non-sensitive) can
  only see files the plugin itself created or that you pick, so "search my Drive" would not work with it.

## Step 6: sign in

From the plugin folder, in a terminal:

```
node server/cli.mjs sign-in
```

A browser opens at Google's sign-in page.

1. Choose your account.
2. If Google shows **"Google hasn't verified this app"**, that is expected for an app you made yourself and haven't sent
   to Google for review. Click **Advanced**, then **Go to (your app name)**. Only do this for an app you created
   yourself.
3. On the permission page, **tick every box** (Gmail, Calendar, Drive) and click **Continue**. Any box you leave
   unticked switches that module off. Status shows which modules are usable and which permissions are missing.

The terminal then prints your address, the permissions granted and which modules are usable. In Claude Code you can ask
the assistant to run `google_sign_in` instead; the browser steps are the same.

## Step 7: check it

```
node server/cli.mjs status
```

This command really refreshes your sign-in with Google, so it shows whether the sign-in still works. It reports:

- your address;
- the requested and granted permissions;
- which modules are usable;
- when you signed in, and how many days ago (`token_age_days`);
- when the sign-in was last refreshed.

`"verified": true` means it works right now. The exit code is `0` when everything works and `3` when you need to sign in
again, so a scheduled task can alert on it. `--offline` skips the live check.

## Important: sign-ins can stop working after 7 days

Google's OAuth documentation says: a project with an **External** user type and the publishing status **"Testing"** is
issued refresh tokens that expire in **7 days**. The only exception is a project that asks for nothing but name, email
address and profile. Gmail, Calendar and Drive are not in that exception.
Source: [Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2), section
"Refresh token expiration".

What this means for you:

- If your app is **External + Testing**, expect to sign in again every week.
- **Personal mode** (if offered) or publishing the app **"In production"** are the alternatives. Google's documentation
  **does not say** whether either of them avoids the 7-day expiry. The 7-day rule is documented for Testing only, and we
  found nothing that states what happens in the other modes.
- So don't rely on it until you have checked it on your own sign-in. **Sign in, then run `status` again 8 days later.**
  `"verified": true` means your setup is not affected. `AUTH_EXPIRED` means you are on the 7-day rule.

The same documentation lists other reasons a sign-in stops working:

- you remove the app's access in your Google Account;
- the sign-in is not used for six months;
- you change your Google password (for Gmail permissions);
- one Google account can hold at most **100** sign-ins per client, and each new one silently cancels the oldest.
  Signing in on many computers with the same client can therefore log out an old one.

In all these cases the plugin reports `AUTH_EXPIRED`, and the fix is to sign in again.

## Step 8: answer Google's confirmations once (`grant`)

Google's MCP servers may ask **you** to allow a read before it happens, for example reading an email from an external
sender. The plugin never answers these questions for you. If the program using the plugin can show Google's question,
you see it there. If it can't (many agent bots can't), the call fails with `CONFIRMATION_NEEDED`, and you answer in your
own terminal instead:

```
node server/cli.mjs grant
```

It calls each read tool once on a harmless target (the first thread, draft, event or file it finds), shows Google's
question exactly as Google sends it, and sends only the number you type (`c` cancels). It prints whether Google asked
and what you chose, never your mail, events or files. `grant gmail_get_message` covers one tool only.

Google may also ask before a change, for example deleting a calendar event, even your own. `grant` can ask that
question only by doing the change: `grant calendar_delete_event --target <event id>` deletes that one event after you
type "yes", and shows Google's question for it. Use a test item.

Google may offer "Always allow for this email" (or "for this owner"): that covers only that one item, so the next
new sender or file owner is asked about again. If you answered that way and want the tool-wide answer, run
`grant --fresh <tool>`: it looks past the items you already allowed until Google asks again.

What Google says about these answers (source: [Configure the Google Workspace MCP servers](https://developers.google.com/workspace/guides/configure-mcp-servers), "Known issues"):

- **Saved approvals expire after 90 days.** Run `grant` again then, or when a bot reports `CONFIRMATION_NEEDED`.
- **You can't view or revoke saved approvals yourself.** The page names no place where a user can. A Google Workspace
  administrator has controls for AI agent access and user review (Admin Help: "Manage AI agent access & user review");
  a personal Gmail account has no administrator. So answer "Always allow" only for tools you are happy to allow for 90
  days. Removing the app's access entirely (see "Signing out") stops every call, whatever was allowed.

## Step 9 (optional): your addresses

If one mailbox receives mail for several of your addresses (aliases, or business domains forwarded to Gmail),
`gmail_message_identity` tells which one a message was sent to. List them in a JSON file and set its path in the plugin
setting **Identities file** (or `GOOGLE_IDENTITIES_FILE`); the format is in the README.

## Step 10 (optional): a folder for saved files

`gmail_get_attachment` and `drive_save_file` save files into one folder you choose, and nowhere else: set it in the
plugin setting **Folder to save files into** (or `GOOGLE_DOWNLOAD_DIR`). Without it they refuse to save.

## Signing out

```
node server/cli.mjs sign-out
```

This deletes the saved sign-in on this computer. To also remove the app's access at Google, open your Google Account >
**Security** > **Third-party connections** (Google may call it "Your connections to third-party apps & services") and
remove the app. After that no call can be made at all, whatever was allowed. Whether Google keeps your "Always allow"
answers for a later new sign-in is not documented.

## Where your sign-in lives

Your sign-in stays on your computer, in `GOOGLE_PLUGIN_HOME`. Nothing is sent anywhere except to Google.
