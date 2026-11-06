// Teams writes: stage -> commit, with a double-send guard. 'sending' is saved BEFORE the request, so if the
// outcome is unknown (timeout, 5xx) a repeat is refused and the user is told to look at the chat instead.
import { M365Error, UNTRUSTED_FIELDS, clean, safeId, safeStr, seg } from "../util.mjs";

// Statuses that mean Microsoft did not accept the request. Anything else (408, 409, 5xx, a timeout) is an unknown outcome.
const REFUSED = new Set([400, 401, 403, 404, 405, 422, 429]);

export const tools = [
  {
    name: "teams_stage", kind: "write", module: "teams",
    description: "Prepare a Teams chat message without sending it: shows the chat's members and the exact text, and returns a stage_id and digest. Show it to the user, then call teams_commit after they approve. Plain text only. Get chat_id from teams_find_chat.",
    inputSchema: { type: "object", properties: { chat_id: { type: "string" }, text: { type: "string", description: "Message text (max 8000 characters)." } }, required: ["chat_id", "text"] },
    async handler(a, ctx) {
      const chatId = safeId(a.chat_id, "chat_id");
      const text = safeStr(a.text, "text", 8000)?.trim();
      if (!text) throw new M365Error("INVALID_ARGUMENT", "text is required");
      const [members, chat] = await Promise.allSettled([ctx.graph.get(`/chats/${seg(chatId)}/members`), ctx.graph.get(`/chats/${seg(chatId)}?$select=topic,chatType`)]);
      if (members.status === "rejected" && chat.status === "rejected") throw members.reason;
      const st = ctx.staging.create("teams", { chat_id: chatId, text });
      return {
        stage_id: st.id, digest: st.digest,
        preview: {
          chat_id: chatId, kind: chat.status === "fulfilled" ? chat.value.chatType ?? null : null,
          topic: chat.status === "fulfilled" ? clean(chat.value.topic, 200) || null : null,
          members: members.status === "fulfilled" ? (members.value.value ?? []).map((m) => ({ name: clean(m.displayName, 120), email: (m.email ?? "").toLowerCase() || null })) : "unavailable",
          text,
        },
        note: UNTRUSTED_FIELDS,
        next_step: "Show the user the members and the text. After they approve, call teams_commit with stage_id and digest.",
      };
    },
  },
  {
    name: "teams_commit", kind: "write", module: "teams", confirm: true,
    description: "SEND the Teams message prepared by teams_stage. It is delivered at once and cannot be unsent. Needs the stage_id and digest the user saw. Refuses a repeat: if an earlier attempt may or may not have gone through, check teams_read_chat instead of retrying. Only call it after the user approved the preview.",
    inputSchema: { type: "object", properties: { stage_id: { type: "string" }, digest: { type: "string" } }, required: ["stage_id", "digest"] },
    async handler(a, ctx) {
      const st = ctx.staging.require(a.stage_id, "teams", a.digest);
      ctx.staging.set(st.id, { state: "sending" });
      let r;
      try {
        r = await ctx.graph.post(`/chats/${seg(st.payload.chat_id)}/messages`, { body: { contentType: "text", content: st.payload.text } });
      } catch (e) {
        if (REFUSED.has(e.status)) { ctx.staging.set(st.id, { state: "staged" }); throw e; } // a definite refusal: nothing was sent
        throw new M365Error("SEND_UNCERTAIN", "Could not confirm whether the message was sent.", { hint: "Check the chat with teams_read_chat before trying again. This stage will not be sent a second time automatically." });
      }
      ctx.staging.set(st.id, { state: "sent", message_id: r.id });
      return { sent: true, message_id: r.id ?? null, chat_id: st.payload.chat_id };
    },
  },
  {
    name: "teams_cancel", kind: "write", module: "teams",
    description: "Cancel a staged Teams message that has not been sent.",
    inputSchema: { type: "object", properties: { stage_id: { type: "string" } }, required: ["stage_id"] },
    async handler(a, ctx) {
      const st = ctx.staging.get(a.stage_id);
      if (!st || st.kind !== "teams") throw new M365Error("STAGE_NOT_FOUND", "No staged message with that id.");
      if (st.state !== "staged") throw new M365Error("ALREADY_DONE", `This message is ${st.state}; it cannot be cancelled here.`);
      ctx.staging.set(st.id, { state: "cancelled" });
      return { cancelled: true, stage_id: st.id };
    },
  },
];
