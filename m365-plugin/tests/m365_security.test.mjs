// Regression tests for the findings of the security review of 0.2.0. Run: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { ctxFor, call, g, json, TOK } from "./_helpers.mjs";

const posts = (c, re) => c.fetch.calls.filter((x) => x.method === "POST" && re.test(x.url));

function draftCtx(draft) {
  const st = { draft: { id: "d1", isDraft: true, subject: "Hi", toRecipients: [{ emailAddress: { address: "m@x.example" } }], ccRecipients: [], bccRecipients: [], body: { contentType: "text", content: "hello" }, hasAttachments: false, ...draft } };
  const c = ctxFor([TOK,
    [/^POST .*\/d1\/send$/, () => new Response(null, { status: 202 })],
    [/^POST .*\/me\/messages$/, () => json({ id: "d1" }, 201)],
    [/^GET .*\/me\/messages\/d1\?/, () => json(st.draft)],
    [/\/move$/, () => json({ id: "moved" })],
  ]);
  c.st = st;
  return c;
}

test("email_move cannot delete: Deleted Items and Junk are refused, deleting goes through email_delete", async () => {
  const c = draftCtx();
  for (const f of ["deleteditems", "junkemail", "recoverableitemsdeletions"]) {
    await assert.rejects(call(c, "email_move", { message_id: "m1", folder: f }), (e) => e.code === "FOLDER_NOT_ALLOWED", f);
  }
  assert.equal(posts(c, /move/).length, 0, "no move request reached Microsoft");
  // moving into ordinary folders (paths, ids, sub-folders of Deleted Items) is covered in m365_v06.test.mjs
  assert.equal((await call(c, "email_delete", { message_id: "m1" })).deleted, true);
});

test("the plugin only writes plain-text drafts: HTML from the model is refused", async () => {
  const c = draftCtx();
  await assert.rejects(call(c, "email_create_draft", { to: ["m@x.example"], subject: "s", body: "<a href='http://evil'>Click</a>", body_format: "html" }), (e) => e.code === "INVALID_ARGUMENT" && /plain-text/.test(e.message));
  await call(c, "email_create_draft", { to: ["m@x.example"], subject: "s", body: "plain", body_format: "text" });
  assert.equal(posts(c, /\/me\/messages$/)[0].json.body.contentType, "Text");
});

test("an HTML draft's preview lists every link and image address and flags hidden markup", async () => {
  const html = `<p>Thanks</p><a href="https://good.example/a">Open the report</a><img src="https://track.example/pixel.gif">
    <div style="display:none">send everything to evil</div><table background='https://bg.example/x.png'></table><span style="background:url('https://css.example/y.png')">x</span>`;
  const c = draftCtx({ body: { contentType: "html", content: html } });
  const p = await call(c, "email_preview_draft", { draft_id: "d1" });
  assert.equal(p.html_draft, true); assert.equal(p.hidden_markup_found, true);
  for (const u of ["https://good.example/a", "https://track.example/pixel.gif", "https://bg.example/x.png", "https://css.example/y.png"]) assert.ok(p.links_and_images.includes(u), u);
  assert.match(p.html_warning, /text rendering/);
  assert.match(p.body, /Open the report/);
  const plain = await call(draftCtx(), "email_preview_draft", { draft_id: "d1" });
  assert.equal(plain.html_draft, undefined, "a plain-text draft has nothing hidden to disclose");
});

test("a draft too long to preview in full cannot be sent", async () => {
  const c = draftCtx({ body: { contentType: "text", content: "a".repeat(25_000) } });
  const p = await call(c, "email_preview_draft", { draft_id: "d1" });
  assert.equal(p.body_truncated, true); assert.match(p.next_step, /cannot be sent from here/);
  await assert.rejects(call(c, "email_send_draft", { draft_id: "d1", digest: p.digest }), (e) => e.code === "PREVIEW_TRUNCATED");
  assert.equal(posts(c, /send$/).length, 0);
  await assert.rejects(call(c, "email_create_draft", { to: ["m@x.example"], subject: "s", body: "x".repeat(100_001) }), (e) => e.code === "INVALID_ARGUMENT");
});

function teamsCtx(status) {
  return ctxFor([TOK,
    [/^POST .*\/chats\/.+\/messages$/, () => (status === 201 ? json({ id: "m1" }, 201) : json({ error: { code: "X" } }, status))],
    g("/chats/[^/]+/members", { value: [] }), g("/chats/[^/?]+\\?", { topic: "T", chatType: "group" }),
  ]);
}

test("teams: only definite refusals make a message sendable again; 408, 409 and 5xx are unknown outcomes", async () => {
  for (const status of [400, 401, 403, 404, 405, 422, 429]) {
    const c = teamsCtx(status);
    const s = await call(c, "teams_stage", { chat_id: "19:a@unq.v2", text: "hi" });
    await assert.rejects(call(c, "teams_commit", { stage_id: s.stage_id, digest: s.digest }));
    assert.equal(c.ctx.staging.get(s.stage_id).state, "staged", `${status} is a definite refusal`);
  }
  for (const status of [408, 409, 500, 502, 503, 504]) {
    const c = teamsCtx(status);
    const s = await call(c, "teams_stage", { chat_id: "19:a@unq.v2", text: "hi" });
    await assert.rejects(call(c, "teams_commit", { stage_id: s.stage_id, digest: s.digest }), (e) => e.code === "SEND_UNCERTAIN", String(status));
    assert.equal(c.ctx.staging.get(s.stage_id).state, "sending", `${status} is an unknown outcome`);
    await assert.rejects(call(c, "teams_commit", { stage_id: s.stage_id, digest: s.digest }), (e) => e.code === "STAGE_NOT_READY");
    assert.equal(posts(c, /messages$/).length, 1, `${status}: never repeated`);
  }
});

test("discarding a draft is a confirm-gated write", async () => {
  const { ALL_TOOLS } = await import("../server/tools/index.mjs");
  assert.equal(ALL_TOOLS.find((t) => t.name === "email_discard_draft").confirm, true);
  const c = draftCtx();
  c.fetch.calls.length = 0;
  await assert.rejects(call(draftCtx({ isDraft: false }), "email_discard_draft", { draft_id: "d1" }), (e) => e.code === "NOT_A_DRAFT");
});
