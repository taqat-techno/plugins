// 0.8.0: formatted drafts. The model writes plain text with a fixed set of marks; the plugin alone turns them into fixed
// tags on escaped text, with or without a signature, and the preview shows the same marks. Run: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { ctxFor, call, g, json, TOK } from "./_helpers.mjs";
import { formatText } from "../server/signature.mjs";
import { htmlToMarkedText } from "../server/util.mjs";

const calls = (c, method, re) => c.fetch.calls.filter((x) => x.method === method && re.test(x.url));
const HL = '<span style="background-color:#ffff00;mso-highlight:yellow">';

test("marks become fixed tags; lists; plain text stays unformatted", () => {
  const { html, formatted } = formatText("A **b** *i* __u__ ==h== ~~s~~\n\n- one\n- **two**\n\n1. first\n2) second");
  assert.equal(formatted, true);
  assert.match(html, /A <b>b<\/b> <i>i<\/i> <u>u<\/u> <span[^>]*>h<\/span> <s>s<\/s>/);
  assert.ok(html.includes(`${HL}h</span>`));
  assert.match(html, /<ul[^>]*><li>one<\/li><li><b>two<\/b><\/li><\/ul>/);
  assert.match(html, /<ol[^>]*><li>first<\/li><li>second<\/li><\/ol>/);
  assert.equal(formatText("Just a line.\n\nAnd another: a==b, snake__case__x, 2*3*4, ** loose **").formatted, false);
});

test("nothing the model writes becomes a link, image, style or event handler", () => {
  const evil = '**<a href="https://evil">x</a>** ==<img src=x onerror=alert(1)>== *" style="display:none* __</span><script>__\n- <b>not bold</b>';
  const { html } = formatText(evil);
  assert.ok(!/<(a|img|script)\b/i.test(html), html);
  assert.ok(!/<[^>]*(onerror|display)/i.test(html), "attribute text stays escaped text, never inside a tag");
  assert.equal((html.match(/style="/g) ?? []).length, (html.match(/<(p|ul|ol) style=|<span style="background-color:#ffff00;mso-highlight:yellow">/g) ?? []).length, "only the plugin's own styles");
  assert.match(html, /&lt;b&gt;not bold&lt;\/b&gt;/);
});

test("preview text shows the same marks the draft was written with", () => {
  const src = "Hi **team**, the ==deadline is Thursday==.\n\n- *one*\n- __two__\n\n1. a\n2. ~~b~~";
  const shown = htmlToMarkedText(formatText(src).html);
  for (const m of ["**team**", "==deadline is Thursday==", "- *one*", "- __two__", "1. a", "2. ~~b~~"]) assert.ok(shown.includes(m), `${m} in ${shown}`);
  assert.match(htmlToMarkedText('<p>x <strong>y</strong> <span style="background:yellow">z</span> <span style="background-color:#ffffff">w</span></p>'), /x \*\*y\*\* ==z== w/);
});

function draftCtx(extraEnv = {}) {
  const state = {};
  const c = ctxFor([TOK,
    [/^POST .*\/me\/messages$/, ({ body }) => { state.body = JSON.parse(body).body; return json({ id: "n1" }, 201); }],
    [/^GET .*\/me\/messages\/n1\?/, () => json({ id: "n1", isDraft: true, subject: "S", toRecipients: [{ emailAddress: { address: "m@x.com" } }], ccRecipients: [], bccRecipients: [], body: state.body, hasAttachments: false })],
  ], extraEnv);
  c.state = state;
  return c;
}

test("a draft with marks is HTML even without a signature; without marks it stays plain text", async () => {
  const c = draftCtx();
  const r = await call(c, "email_create_draft", { to: ["m@x.com"], subject: "S", body: "Please **review** the ==numbers==." });
  assert.equal(r.formatted, true); assert.equal(r.signature, false);
  assert.equal(c.state.body.contentType, "HTML");
  assert.ok(c.state.body.content.includes("<b>review</b>") && c.state.body.content.includes(`${HL}numbers</span>`));
  const p = await call(c, "email_preview_draft", { draft_id: "n1" });
  assert.equal(p.html_draft, true); assert.deepEqual(p.links_and_images, []); assert.equal(p.hidden_markup_found, false);
  assert.match(p.body, /Please \*\*review\*\* the ==numbers==\./);
  const plain = await call(c, "email_create_draft", { to: ["m@x.com"], subject: "S", body: "No formatting here." });
  assert.equal(plain.formatted, false); assert.equal(c.state.body.contentType, "Text");
});

test("a formatted reply without a signature goes on top of Outlook's quoted original", async () => {
  let patched;
  const c = ctxFor([TOK, [/createReply$/, () => json({ id: "r1" }, 201)],
    g("/me/messages/r1\\?\\$select=body", { body: { contentType: "html", content: '<html><body><div id="divRplyFwdMsg">From: Sara</div></body></html>' } }),
    [/^PATCH .*\/me\/messages\/r1$/, ({ body }) => { patched = JSON.parse(body); return json({}); }]]);
  const r = await call(c, "email_create_reply_draft", { message_id: "m1", comment: "Thanks, **approved**." });
  assert.equal(r.formatted, true);
  assert.deepEqual(calls(c, "POST", /createReply$/)[0].json, {});
  const html = patched.body.content;
  assert.ok(html.indexOf("<b>approved</b>") < html.indexOf("divRplyFwdMsg"));
  const c2 = ctxFor([TOK, [/createReply$/, () => json({ id: "r2" }, 201)]]);
  await call(c2, "email_create_reply_draft", { message_id: "m1", comment: "Thanks." });
  assert.deepEqual(calls(c2, "POST", /createReply$/)[0].json, { comment: "Thanks." }, "plain replies are unchanged");
});
