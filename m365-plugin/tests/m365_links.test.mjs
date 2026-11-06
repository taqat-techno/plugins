// The HTML-draft preview must disclose every address the body can reach. Run: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { ctxFor, call, json, TOK } from "./_helpers.mjs";
import { extractLinks } from "../server/tools/mail_write.mjs";

test("extractLinks finds quoted, unquoted, srcset, formaction, css, import, meta refresh and entity-encoded addresses", () => {
  const html = `
    <a href=https://unquoted.example/a>x</a>
    <a HREF = 'https://single.example/b'>x</a>
    <img src="https://img.example/c.gif" srcset="https://s1.example/1.png 1x, https://s2.example/2.png 2x">
    <button formaction="https://form.example/d">x</button>
    <video poster=https://poster.example/e.jpg></video>
    <a href="&#104;ttps://encoded.example/f">x</a><a href="https://amp.example/?a=1&amp;b=2">x</a>
    <svg><use xlink:href="https://svg.example/g"/></svg>
    <style>@import "https://imp.example/h.css"; .a{background:url(https://cssunq.example/i.png)} .b{background:url('https://cssq.example/j.png')}</style>
    <meta http-equiv="refresh" content="0; url=https://meta.example/k">`;
  const got = new Set(extractLinks(html));
  for (const u of ["https://unquoted.example/a", "https://single.example/b", "https://img.example/c.gif", "https://s1.example/1.png", "https://s2.example/2.png",
    "https://form.example/d", "https://poster.example/e.jpg", "https://encoded.example/f", "https://amp.example/?a=1&b=2", "https://svg.example/g",
    "https://imp.example/h.css", "https://cssunq.example/i.png", "https://cssq.example/j.png", "https://meta.example/k"]) assert.ok(got.has(u), `missed ${u}`);
});

function ctxWith(body) {
  const draft = { id: "d1", isDraft: true, subject: "s", toRecipients: [{ emailAddress: { address: "m@x.com" } }], ccRecipients: [], bccRecipients: [], body: { contentType: "html", content: body }, hasAttachments: false };
  return ctxFor([TOK,
    [/^POST .*\/d1\/send$/, () => new Response(null, { status: 202 })],
    [/^GET .*\/me\/messages\/d1\?/, () => json(draft)]]);
}

test("preview reports the count; more than 200 links cannot be sent and is never silently cut", async () => {
  const many = Array.from({ length: 250 }, (_, i) => `<a href=https://l${i}.example/>x</a>`).join("");
  const c = ctxWith(many);
  const p = await call(c, "email_preview_draft", { draft_id: "d1" });
  assert.equal(p.link_count, 250); assert.equal(p.links_truncated, true); assert.equal(p.links_and_images.length, 200);
  assert.match(p.next_step, /cannot be sent from here/);
  await assert.rejects(call(c, "email_send_draft", { draft_id: "d1", digest: p.digest }), (e) => e.code === "PREVIEW_TRUNCATED" && /links or images/.test(e.message));
  assert.equal(c.fetch.calls.filter((x) => /send$/.test(x.url)).length, 0);
});

test("a normal HTML reply with a few links previews fully and can be sent after approval", async () => {
  const c = ctxWith(`<p>Thanks</p><a href="https://ok.example/doc">doc</a>`);
  const p = await call(c, "email_preview_draft", { draft_id: "d1" });
  assert.deepEqual(p.links_and_images, ["https://ok.example/doc"]); assert.equal(p.links_truncated, false);
  assert.equal((await call(c, "email_send_draft", { draft_id: "d1", digest: p.digest })).sent, true);
});
