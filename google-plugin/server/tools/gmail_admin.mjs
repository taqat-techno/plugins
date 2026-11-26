// Gmail mailbox and settings tools over Google's REST API (only with GOOGLE_REST_FALLBACK=1). Google's MCP tools ask the
// human for many of these and some offer only "Allow once"; REST never asks, so the plugin's own classes, hooks and the
// host's approval steps are the only brakes. Everything here is opt-in:
//   mailbox tools (trash, labels, batch modify)         GOOGLE_REST_FALLBACK=1   (gmail.modify, already granted)
//   settings tools (filters, auto-reply, forwarding,    + GOOGLE_GMAIL_SETTINGS=1 (gmail.settings.basic / .sharing)
//     IMAP / POP / language, send-as)
//   permanent delete, empty Trash / Spam                + GOOGLE_FULL_MAILBOX=1   (full mailbox scope)
// Each tool checks the saved sign-in's scopes first and fails with SCOPE_MISSING (and the sign-in hint) instead of a raw
// 403. SMTP passwords are never returned.
import { createRest } from "../rest.mjs";
import { FULL_MAILBOX_SCOPE, SCOPES } from "../config.mjs";
import { GoogleError } from "../util.mjs";

const ASK = "Ask the human first and wait for a clear yes (class confirm).";
const PERMANENT = "PERMANENT: it cannot be undone or recovered.";
const NOTE = "Google REST API (GOOGLE_REST_FALLBACK).";
const MODIFY_ANY = [SCOPES.gmailModify, FULL_MAILBOX_SCOPE];
const READ_SETTINGS = [SCOPES.gmailSettingsBasic, FULL_MAILBOX_SCOPE, SCOPES.gmailModify, SCOPES.gmailReadonly];
const BASIC = [SCOPES.gmailSettingsBasic];
const SHARING = [SCOPES.gmailSettingsSharing];
const SENDAS_PATCH = [SCOPES.gmailSettingsBasic, SCOPES.gmailSettingsSharing];
const FULL = [FULL_MAILBOX_SCOPE];
const MAX_BATCH = 1000;

const str = (v, what) => { const s = String(v ?? "").trim(); if (!s) throw new GoogleError("INVALID_ARGUMENT", `${what} is required.`); return s; };
const enc = encodeURIComponent;
const ids = (v, what) => {
  const list = [...new Set((Array.isArray(v) ? v : []).map((x) => String(x).trim()).filter(Boolean))];
  if (!list.length) throw new GoogleError("INVALID_ARGUMENT", `${what} needs at least one id.`);
  if (list.length > MAX_BATCH) throw new GoogleError("INVALID_ARGUMENT", `${what} takes at most ${MAX_BATCH} ids per call.`);
  return list;
};
const labelList = (v) => (Array.isArray(v) ? v.map((x) => String(x).trim()).filter(Boolean) : []);
const pickKeys = (obj, keys) => Object.fromEntries(keys.filter((k) => obj?.[k] !== undefined).map((k) => [k, obj[k]]));

/** Never let a password out: smtpMsa.password is dropped from any send-as object. */
const noSecrets = (o) => {
  if (Array.isArray(o)) return o.map(noSecrets);
  if (!o || typeof o !== "object") return o;
  const out = {};
  for (const [k, v] of Object.entries(o)) { if (k.toLowerCase() === "password") continue; out[k] = noSecrets(v); }
  return out;
};

function requireScopes(ctx, anyOf, tool) {
  const granted = ctx.auth.grantedScopes?.() ?? [];
  if (!anyOf.some((s) => granted.includes(s))) {
    const opt = anyOf.includes(FULL_MAILBOX_SCOPE) && anyOf.length === 1 ? "GOOGLE_FULL_MAILBOX=1" : "GOOGLE_GMAIL_SETTINGS=1";
    throw new GoogleError("SCOPE_MISSING", `${tool} needs a permission the saved sign-in does not have (${anyOf.map((s) => s.replace(/^https:\/\/www\.googleapis\.com\/auth\//, "")).join(" or ")}).`, {
      hint: `The person turns on ${opt} and signs in again: node server/cli.mjs sign-in. Do not retry before they have.`,
    });
  }
}

/** One tool definition. needs: undefined (REST switch only) | "settings" | "full". */
function tool(name, kind, needs, scopes, description, properties, required, run) {
  return {
    name, kind, module: "gmail", rest: true, ...(needs ? { needs } : {}), confirm: kind === "confirm",
    description: `${description} ${kind === "confirm" ? `${ASK} ` : ""}${NOTE}`,
    inputSchema: { type: "object", ...(required.length ? { required } : {}), properties },
    async handler(args, ctx) { requireScopes(ctx, scopes, name); ctx.limiter?.check(name, ctx.cfg.writeLimitPerHour); return run(args ?? {}, createRest(ctx), ctx); },
  };
}

const id = (d) => ({ type: "string", description: d });
const arr = (d) => ({ type: "array", items: { type: "string" }, description: d });
const labelsProps = { addLabelIds: arr("Label ids to add (system ids such as INBOX, UNREAD, STARRED, IMPORTANT, SPAM, or your own label ids)."), removeLabelIds: arr("Label ids to remove (remove INBOX = archive, UNREAD = mark read).") };

/** Every message id in a folder (TRASH or SPAM), page by page. */
async function allIds(rest, labelId) {
  const out = [];
  let pageToken;
  for (let i = 0; i < 1000; i++) {
    const j = await rest.call("gmail", "GET", "messages", { query: { labelIds: labelId, includeSpamTrash: true, maxResults: 500, pageToken } });
    out.push(...(j.messages ?? []).map((m) => m.id));
    pageToken = j.nextPageToken;
    if (!pageToken) break;
  }
  return out;
}
async function deleteMany(rest, list) {
  for (let i = 0; i < list.length; i += MAX_BATCH) await rest.call("gmail", "POST", "messages/batchDelete", { body: { ids: list.slice(i, i + MAX_BATCH) } });
  return list.length;
}

const FILTER_RISKY = (action) => Boolean(action?.forward) || labelList(action?.addLabelIds).some((l) => l.toUpperCase() === "TRASH");
const filterProps = {
  criteria: { type: "object", description: "Which mail: from, to, subject, query, negatedQuery, hasAttachment, excludeChats, size, sizeComparison (larger|smaller)." },
  action: { type: "object", description: "What to do: addLabelIds, removeLabelIds, forward (an address already verified as a forwarding address)." },
};
const SENDAS_FIELDS = ["displayName", "replyToAddress", "signature", "isDefault", "treatAsAlias", "smtpMsa"];
const sendAsProps = {
  displayName: id("Name shown to recipients."), replyToAddress: id("Reply-To address."), signature: id("HTML signature."),
  isDefault: { type: "boolean" }, treatAsAlias: { type: "boolean" },
  smtpMsa: { type: "object", description: "Outgoing SMTP server: host, port, username, password, securityMode (none|ssl|starttls). The password is sent to Google, never returned." },
};

export const tools = [
  // ------------------------------------------------------------------------------------------ mailbox (gmail.modify)
  tool("gmail_rest_trash_message", "write", undefined, MODIFY_ANY, "Move one Gmail message to Trash (recoverable for about 30 days).", { messageId: id("Message id.") }, ["messageId"],
    async (a, rest) => { const r = await rest.call("gmail", "POST", `messages/${enc(str(a.messageId, "messageId"))}/trash`); return { trashed: true, message_id: r.id, labelIds: r.labelIds }; }),
  tool("gmail_rest_untrash_message", "write", undefined, MODIFY_ANY, "Restore one Gmail message from Trash.", { messageId: id("Message id.") }, ["messageId"],
    async (a, rest) => { const r = await rest.call("gmail", "POST", `messages/${enc(str(a.messageId, "messageId"))}/untrash`); return { untrashed: true, message_id: r.id, labelIds: r.labelIds }; }),
  tool("gmail_rest_trash_thread", "write", undefined, MODIFY_ANY, "Move a whole Gmail thread to Trash (recoverable for about 30 days).", { threadId: id("Thread id.") }, ["threadId"],
    async (a, rest) => { const r = await rest.call("gmail", "POST", `threads/${enc(str(a.threadId, "threadId"))}/trash`); return { trashed: true, thread_id: r.id }; }),
  tool("gmail_rest_untrash_thread", "write", undefined, MODIFY_ANY, "Restore a whole Gmail thread from Trash.", { threadId: id("Thread id.") }, ["threadId"],
    async (a, rest) => { const r = await rest.call("gmail", "POST", `threads/${enc(str(a.threadId, "threadId"))}/untrash`); return { untrashed: true, thread_id: r.id }; }),
  tool("gmail_rest_modify_message", "write", undefined, MODIFY_ANY, "Add or remove labels on one Gmail message: mark read (remove UNREAD) or unread, archive (remove INBOX), star, important, spam (add SPAM) or not spam, or your own labels.", { messageId: id("Message id."), ...labelsProps }, ["messageId"],
    async (a, rest) => { const r = await rest.call("gmail", "POST", `messages/${enc(str(a.messageId, "messageId"))}/modify`, { body: { addLabelIds: labelList(a.addLabelIds), removeLabelIds: labelList(a.removeLabelIds) } }); return { message_id: r.id, labelIds: r.labelIds }; }),
  tool("gmail_rest_modify_thread", "write", undefined, MODIFY_ANY, "Add or remove labels on every message of a Gmail thread (read/unread, archive, star, important, spam, your own labels).", { threadId: id("Thread id."), ...labelsProps }, ["threadId"],
    async (a, rest) => { const r = await rest.call("gmail", "POST", `threads/${enc(str(a.threadId, "threadId"))}/modify`, { body: { addLabelIds: labelList(a.addLabelIds), removeLabelIds: labelList(a.removeLabelIds) } }); return { thread_id: r.id, messages: (r.messages ?? []).length }; }),
  tool("gmail_rest_batch_modify", "write", undefined, MODIFY_ANY, `Add or remove labels on up to ${MAX_BATCH} Gmail messages at once (bulk read/unread, archive, spam, labels). Returns the count and ids, never content.`, { messageIds: arr(`Up to ${MAX_BATCH} message ids.`), ...labelsProps }, ["messageIds"],
    async (a, rest) => { const list = ids(a.messageIds, "messageIds"); await rest.call("gmail", "POST", "messages/batchModify", { body: { ids: list, addLabelIds: labelList(a.addLabelIds), removeLabelIds: labelList(a.removeLabelIds) } }); return { modified: list.length, message_ids: list }; }),
  tool("gmail_rest_batch_trash", "write", undefined, MODIFY_ANY, `Move up to ${MAX_BATCH} Gmail messages to Trash (recoverable for about 30 days), one call each. Returns counts and ids, never content.`, { messageIds: arr(`Up to ${MAX_BATCH} message ids.`) }, ["messageIds"],
    async (a, rest) => {
      const list = ids(a.messageIds, "messageIds");
      const failed = [];
      for (const m of list) { try { await rest.call("gmail", "POST", `messages/${enc(m)}/trash`); } catch (e) { failed.push({ id: m, code: e.code ?? "ERROR" }); } }
      return { trashed: list.length - failed.length, failed, message_ids: list };
    }),
  tool("gmail_rest_create_label", "write", undefined, MODIFY_ANY, "Create a Gmail label (nest with '/', for example Clients/Acme). labelListVisibility: labelShow | labelShowIfUnread | labelHide; messageListVisibility: show | hide; color: {textColor, backgroundColor} from Gmail's palette.",
    { name: id("Label name."), labelListVisibility: { type: "string" }, messageListVisibility: { type: "string" }, color: { type: "object" } }, ["name"],
    async (a, rest) => { const r = await rest.call("gmail", "POST", "labels", { body: { name: str(a.name, "name"), ...pickKeys(a, ["labelListVisibility", "messageListVisibility", "color"]) } }); return { label: r }; }),
  tool("gmail_rest_update_label", "write", undefined, MODIFY_ANY, "Rename a Gmail label or change its visibility or color (only the fields given change).",
    { labelId: id("Label id."), name: { type: "string" }, labelListVisibility: { type: "string" }, messageListVisibility: { type: "string" }, color: { type: "object" } }, ["labelId"],
    async (a, rest) => { const r = await rest.call("gmail", "PATCH", `labels/${enc(str(a.labelId, "labelId"))}`, { body: pickKeys(a, ["name", "labelListVisibility", "messageListVisibility", "color"]) }); return { label: r }; }),
  tool("gmail_rest_delete_label", "write", undefined, MODIFY_ANY, "Delete a Gmail label. The messages stay; they only lose this label.", { labelId: id("Label id.") }, ["labelId"],
    async (a, rest) => { await rest.call("gmail", "DELETE", `labels/${enc(str(a.labelId, "labelId"))}`); return { deleted: true, label_id: a.labelId }; }),

  // ------------------------------------------------------------------------------------------ permanent (full mailbox)
  tool("gmail_rest_delete_message", "confirm", "full", FULL, `Delete one Gmail message for good, skipping Trash. ${PERMANENT}`, { messageId: id("Message id.") }, ["messageId"],
    async (a, rest) => { await rest.call("gmail", "DELETE", `messages/${enc(str(a.messageId, "messageId"))}`); return { deleted_permanently: true, message_id: a.messageId }; }),
  tool("gmail_rest_delete_thread", "confirm", "full", FULL, `Delete a whole Gmail thread for good, skipping Trash. ${PERMANENT}`, { threadId: id("Thread id.") }, ["threadId"],
    async (a, rest) => { await rest.call("gmail", "DELETE", `threads/${enc(str(a.threadId, "threadId"))}`); return { deleted_permanently: true, thread_id: a.threadId }; }),
  tool("gmail_rest_batch_delete", "confirm", "full", FULL, `Delete up to ${MAX_BATCH} Gmail messages for good, skipping Trash. ${PERMANENT} Returns the count and ids.`, { messageIds: arr(`Up to ${MAX_BATCH} message ids.`) }, ["messageIds"],
    async (a, rest) => { const list = ids(a.messageIds, "messageIds"); await deleteMany(rest, list); return { deleted_permanently: list.length, message_ids: list }; }),
  tool("gmail_rest_empty_trash", "confirm", "full", FULL, `Empty Gmail's Trash: every message in it is deleted for good. ${PERMANENT} Returns the count.`, {}, [],
    async (_a, rest) => ({ deleted_permanently: await deleteMany(rest, await allIds(rest, "TRASH")), folder: "TRASH" })),
  tool("gmail_rest_empty_spam", "confirm", "full", FULL, `Empty Gmail's Spam folder: every message in it is deleted for good. ${PERMANENT} Returns the count.`, {}, [],
    async (_a, rest) => ({ deleted_permanently: await deleteMany(rest, await allIds(rest, "SPAM")), folder: "SPAM" })),

  // ------------------------------------------------------------------------------------------ settings: filters
  tool("gmail_rest_list_filters", "read", "settings", READ_SETTINGS, "List Gmail filters (criteria and actions).", {}, [],
    async (_a, rest) => ({ filters: (await rest.call("gmail", "GET", "settings/filters")).filter ?? [] })),
  tool("gmail_rest_get_filter", "read", "settings", READ_SETTINGS, "Get one Gmail filter.", { filterId: id("Filter id.") }, ["filterId"],
    async (a, rest) => ({ filter: await rest.call("gmail", "GET", `settings/filters/${enc(str(a.filterId, "filterId"))}`) })),
  tool("gmail_rest_create_filter", "write", "settings", BASIC, "Create a Gmail filter that labels, archives, marks read, stars, marks important or never-spams matching mail. A filter that forwards or sends mail to Trash must use gmail_rest_create_filter_forward_or_delete (refused here).", filterProps, ["criteria", "action"],
    async (a, rest) => {
      if (FILTER_RISKY(a.action)) throw new GoogleError("NEEDS_CONFIRM_TOOL", "This filter forwards mail or sends it to Trash; nothing was created.", { hint: "Use gmail_rest_create_filter_forward_or_delete, which asks the human first." });
      return { filter: await rest.call("gmail", "POST", "settings/filters", { body: { criteria: a.criteria ?? {}, action: a.action ?? {} } }) };
    }),
  tool("gmail_rest_create_filter_forward_or_delete", "confirm", "settings", BASIC, "Create a Gmail filter that forwards matching mail to another address (which must already be a verified forwarding address) and/or sends it to Trash. Forwarding filters keep sending future mail out silently. Name the address and the criteria.", filterProps, ["criteria", "action"],
    async (a, rest) => ({ filter: await rest.call("gmail", "POST", "settings/filters", { body: { criteria: a.criteria ?? {}, action: a.action ?? {} } }) })),
  tool("gmail_rest_delete_filter", "write", "settings", BASIC, "Delete a Gmail filter (mail already filtered is not changed).", { filterId: id("Filter id.") }, ["filterId"],
    async (a, rest) => { await rest.call("gmail", "DELETE", `settings/filters/${enc(str(a.filterId, "filterId"))}`); return { deleted: true, filter_id: a.filterId }; }),

  // ------------------------------------------------------------------------------------------ settings: auto-reply, forwarding
  tool("gmail_rest_get_vacation", "read", "settings", READ_SETTINGS, "Get Gmail's auto-reply (vacation responder) settings.", {}, [],
    async (_a, rest) => ({ vacation: await rest.call("gmail", "GET", "settings/vacation") })),
  tool("gmail_rest_update_vacation", "write", "settings", BASIC, "Turn Gmail's auto-reply on or off and set it: enableAutoReply, responseSubject, responseBodyPlainText, responseBodyHtml, restrictToContacts, restrictToDomain, startTime / endTime (ms since epoch).",
    { enableAutoReply: { type: "boolean" }, responseSubject: { type: "string" }, responseBodyPlainText: { type: "string" }, responseBodyHtml: { type: "string" }, restrictToContacts: { type: "boolean" }, restrictToDomain: { type: "boolean" }, startTime: { type: "string" }, endTime: { type: "string" } }, ["enableAutoReply"],
    async (a, rest) => ({ vacation: await rest.call("gmail", "PUT", "settings/vacation", { body: pickKeys(a, ["enableAutoReply", "responseSubject", "responseBodyPlainText", "responseBodyHtml", "restrictToContacts", "restrictToDomain", "startTime", "endTime"]) }) })),
  tool("gmail_rest_get_auto_forwarding", "read", "settings", READ_SETTINGS, "Get Gmail's automatic forwarding setting (on/off, address, what happens to the copy).", {}, [],
    async (_a, rest) => ({ auto_forwarding: await rest.call("gmail", "GET", "settings/autoForwarding") })),
  tool("gmail_rest_update_auto_forwarding", "confirm", "settings", SHARING, "Turn automatic forwarding of ALL incoming mail on or off: enabled, emailAddress (must already be a verified forwarding address), disposition (leaveInInbox | archive | trash | markRead). When on, every future email is copied to that address silently. Name the address.",
    { enabled: { type: "boolean" }, emailAddress: { type: "string" }, disposition: { type: "string" } }, ["enabled"],
    async (a, rest) => ({ auto_forwarding: await rest.call("gmail", "PUT", "settings/autoForwarding", { body: pickKeys(a, ["enabled", "emailAddress", "disposition"]) }) })),
  tool("gmail_rest_list_forwarding_addresses", "read", "settings", READ_SETTINGS, "List the addresses Gmail may forward to, with their verification status.", {}, [],
    async (_a, rest) => ({ forwarding_addresses: (await rest.call("gmail", "GET", "settings/forwardingAddresses")).forwardingAddresses ?? [] })),
  tool("gmail_rest_create_forwarding_address", "confirm", "settings", SHARING, "Add an address Gmail may forward to. Google emails that address a confirmation link; once it is confirmed, filters and auto-forwarding can send mail there. Name the address.", { forwardingEmail: id("The address.") }, ["forwardingEmail"],
    async (a, rest) => ({ forwarding_address: await rest.call("gmail", "POST", "settings/forwardingAddresses", { body: { forwardingEmail: str(a.forwardingEmail, "forwardingEmail") } }) })),
  tool("gmail_rest_delete_forwarding_address", "confirm", "settings", SHARING, "Remove an address from Gmail's forwarding addresses (filters or auto-forwarding to it stop working).", { forwardingEmail: id("The address.") }, ["forwardingEmail"],
    async (a, rest) => { await rest.call("gmail", "DELETE", `settings/forwardingAddresses/${enc(str(a.forwardingEmail, "forwardingEmail"))}`); return { deleted: true, forwarding_email: a.forwardingEmail }; }),

  // ------------------------------------------------------------------------------------------ settings: IMAP, POP, language
  tool("gmail_rest_get_imap", "read", "settings", READ_SETTINGS, "Get Gmail's IMAP settings.", {}, [], async (_a, rest) => ({ imap: await rest.call("gmail", "GET", "settings/imap") })),
  tool("gmail_rest_update_imap", "write", "settings", BASIC, "Change Gmail's IMAP settings: enabled, autoExpunge, expungeBehavior (archive | trash | deleteForever), maxFolderSize.",
    { enabled: { type: "boolean" }, autoExpunge: { type: "boolean" }, expungeBehavior: { type: "string" }, maxFolderSize: { type: "integer" } }, [],
    async (a, rest) => ({ imap: await rest.call("gmail", "PUT", "settings/imap", { body: pickKeys(a, ["enabled", "autoExpunge", "expungeBehavior", "maxFolderSize"]) }) })),
  tool("gmail_rest_get_pop", "read", "settings", READ_SETTINGS, "Get Gmail's POP settings.", {}, [], async (_a, rest) => ({ pop: await rest.call("gmail", "GET", "settings/pop") })),
  tool("gmail_rest_update_pop", "write", "settings", BASIC, "Change Gmail's POP settings: accessWindow (disabled | fromNowOn | allMail), disposition (leaveInInbox | archive | trash | markRead).",
    { accessWindow: { type: "string" }, disposition: { type: "string" } }, [],
    async (a, rest) => ({ pop: await rest.call("gmail", "PUT", "settings/pop", { body: pickKeys(a, ["accessWindow", "disposition"]) }) })),
  tool("gmail_rest_get_language", "read", "settings", READ_SETTINGS, "Get Gmail's display language.", {}, [], async (_a, rest) => ({ language: await rest.call("gmail", "GET", "settings/language") })),
  tool("gmail_rest_update_language", "write", "settings", BASIC, "Change Gmail's display language (displayLanguage, an RFC 3066 tag such as en or ar).", { displayLanguage: id("Language tag.") }, ["displayLanguage"],
    async (a, rest) => ({ language: await rest.call("gmail", "PUT", "settings/language", { body: { displayLanguage: str(a.displayLanguage, "displayLanguage") } }) })),

  // ------------------------------------------------------------------------------------------ settings: send-as
  tool("gmail_rest_list_send_as", "read", "settings", READ_SETTINGS, "List the account's send-as addresses with display name, reply-to, signature, default flag and verification status (SMTP passwords are never returned).", {}, [],
    async (_a, rest) => ({ send_as: noSecrets((await rest.call("gmail", "GET", "settings/sendAs")).sendAs ?? []) })),
  tool("gmail_rest_get_send_as", "read", "settings", READ_SETTINGS, "Get one send-as address (SMTP password never returned).", { sendAsEmail: id("The address.") }, ["sendAsEmail"],
    async (a, rest) => ({ send_as: noSecrets(await rest.call("gmail", "GET", `settings/sendAs/${enc(str(a.sendAsEmail, "sendAsEmail"))}`)) })),
  tool("gmail_rest_create_send_as", "confirm", "settings", SHARING, "Add a send-as address (mail can then be sent as it): sendAsEmail plus displayName, replyToAddress, signature, isDefault, treatAsAlias, smtpMsa. Google emails the address a verification link. Name the address.",
    { sendAsEmail: id("The address."), ...sendAsProps }, ["sendAsEmail"],
    async (a, rest) => ({ send_as: noSecrets(await rest.call("gmail", "POST", "settings/sendAs", { body: { sendAsEmail: str(a.sendAsEmail, "sendAsEmail"), ...pickKeys(a, SENDAS_FIELDS) } })) })),
  // Split by effect: name and signature only change how mail looks (write); reply-to, default, alias and the SMTP server
  // decide where replies go and which server carries the mail, which can redirect it like forwarding does (confirm).
  tool("gmail_rest_update_send_as", "write", "settings", SENDAS_PATCH, "Change a send-as address's display name and/or signature (only the fields given). Reply-to, default, alias and SMTP settings need gmail_rest_update_send_as_routing.",
    { sendAsEmail: id("The address."), displayName: sendAsProps.displayName, signature: sendAsProps.signature }, ["sendAsEmail"],
    async (a, rest) => {
      const extra = ["replyToAddress", "isDefault", "treatAsAlias", "smtpMsa"].filter((k) => a[k] !== undefined);
      if (extra.length) throw new GoogleError("NEEDS_CONFIRM_TOOL", `${extra.join(", ")} decide where replies go or which server sends the mail; nothing was changed.`, { hint: "Use gmail_rest_update_send_as_routing, which asks the human first." });
      return { send_as: noSecrets(await rest.call("gmail", "PATCH", `settings/sendAs/${enc(str(a.sendAsEmail, "sendAsEmail"))}`, { body: pickKeys(a, ["displayName", "signature"]) })) };
    }),
  tool("gmail_rest_update_send_as_routing", "confirm", "settings", SENDAS_PATCH, "Change where a send-as address's replies go and how its mail is sent (only the fields given): replyToAddress (replies to mail sent as this address go there), isDefault, treatAsAlias, smtpMsa (the outgoing SMTP server; the password is sent to Google, never returned), plus displayName and signature. A changed reply-to or SMTP server can redirect mail. Name the address and each change.",
    { sendAsEmail: id("The address."), ...sendAsProps }, ["sendAsEmail"],
    async (a, rest) => ({ send_as: noSecrets(await rest.call("gmail", "PATCH", `settings/sendAs/${enc(str(a.sendAsEmail, "sendAsEmail"))}`, { body: pickKeys(a, SENDAS_FIELDS) })) })),
  tool("gmail_rest_delete_send_as", "confirm", "settings", SHARING, "Remove a send-as address (mail can no longer be sent as it).", { sendAsEmail: id("The address.") }, ["sendAsEmail"],
    async (a, rest) => { await rest.call("gmail", "DELETE", `settings/sendAs/${enc(str(a.sendAsEmail, "sendAsEmail"))}`); return { deleted: true, send_as_email: a.sendAsEmail }; }),
  tool("gmail_rest_verify_send_as", "write", "settings", SHARING, "Send (again) the verification email for a send-as address that is not verified yet.", { sendAsEmail: id("The address.") }, ["sendAsEmail"],
    async (a, rest) => { await rest.call("gmail", "POST", `settings/sendAs/${enc(str(a.sendAsEmail, "sendAsEmail"))}/verify`); return { verification_sent: true, send_as_email: a.sendAsEmail }; }),
];

/** Tools counted by the optional write limit (guards.mjs adds these names). */
export const CAPPED = ["gmail_rest_trash_message", "gmail_rest_trash_thread", "gmail_rest_batch_trash", "gmail_rest_delete_message", "gmail_rest_delete_thread", "gmail_rest_batch_delete", "gmail_rest_empty_trash", "gmail_rest_empty_spam"];
