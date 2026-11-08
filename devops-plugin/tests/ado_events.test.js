// Run by tests/test_ado_events.py with: node --test tests/ado_events.test.js
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const ev = require("../scripts/ado-events.js");

const ORG = "https://dev.azure.com/contoso";
const ME = "11111111-2222-3333-4444-555555555555";
const OTHER = { id: "99999999-0000-0000-0000-000000000001", displayName: "Sara", uniqueName: "sara@contoso.example" };
const ME_ID = { id: ME, displayName: "Ahmed", uniqueName: "ahmed@contoso.example" };
const T0 = Date.parse("2026-11-06T10:00:00.000Z");
const LATER = "2026-11-06T10:30:00.000Z";
const OLD = "2026-11-06T08:00:00.000Z";

// A fake Azure DevOps. `routes` maps a regex on the URL to a response (or a function / Error).
function fakeApi(routes) {
  const calls = [];
  const handle = async (method, url, body) => {
    calls.push({ method, url, body });
    for (const [re, res] of routes) {
      if (re.test(url)) {
        const v = typeof res === "function" ? res(url, body) : res;
        if (v instanceof Error) throw v;
        return v;
      }
    }
    throw new Error("no route for " + url);
  };
  return { api: { get: (u) => handle("GET", u), post: (u, b) => handle("POST", u, b) }, calls };
}

// Specific routes first: the first matching route wins, the defaults answer "nothing".
const base = (extra) => [
  ...(extra || []),
  [/connectionData/, { authenticatedUser: { id: ME, providerDisplayName: "Ahmed", properties: { Account: { $value: "ahmed@contoso.example" } } } }],
  [/_apis\/projects/, { value: [{ name: "Alpha" }] }],
  [/_apis\/wit\/wiql/, { workItems: [] }],
  [/git\/pullrequests/, { value: [] }],
  [/\/threads/, { value: [] }],
  [/_apis\/build\/builds/, { value: [] }],
];

const run = (routes, cursor, opts, now) => {
  const f = fakeApi(routes);
  return ev.collectEvents({ orgUrl: ORG, api: f.api, now: () => now || T0 + 3600e3 }, cursor, opts).then((r) => Object.assign(r, { calls: f.calls }));
};
const cur = (over) => Object.assign({ v: 1, t: T0, rv: [], ev: [] }, over);
const types = (r) => r.events.map((e) => e.type);

const pr = (id, extra) => Object.assign({ pullRequestId: id, title: "PR " + id, createdBy: OTHER, creationDate: LATER,
  repository: { id: "repo-1", name: "app", project: { name: "Alpha" } } }, extra);

test("baseline: no events, a cursor, and existing review requests are remembered", async () => {
  const r = await run(base([[/searchCriteria\.reviewerId/, { value: [pr(7)] }]]), null, undefined, T0);
  assert.deepStrictEqual(r.events, []);
  assert.strictEqual(r.baseline, true);
  const c = ev.decodeCursor(r.cursor);
  assert.strictEqual(c.t, T0);
  assert.deepStrictEqual(c.rv, ["7"]);
  assert.ok(!r.calls.some((x) => /wiql|builds/.test(x.url)), "baseline reads nothing else");
});

test("assignment by someone else is an event; self-assignment and old ones are not", async () => {
  const routes = base([
    [/_apis\/wit\/wiql/, { workItems: [{ id: 5 }, { id: 6 }] }],
    [/_apis\/wit\/workitems\?ids/, { value: [
      { id: 5, fields: { "System.Title": "Fix login", "System.AssignedTo": ME_ID, "System.TeamProject": "Alpha", "System.CommentCount": 0 } },
      { id: 6, fields: { "System.Title": "Mine already", "System.AssignedTo": ME_ID, "System.TeamProject": "Alpha", "System.CommentCount": 0 } } ] }],
    [/workItems\/5\/updates/, { value: [
      { rev: 2, revisedBy: OTHER, revisedDate: LATER, fields: { "System.AssignedTo": { oldValue: ident(OTHER), newValue: ME_ID }, "System.ChangedDate": { newValue: LATER } } },
      { rev: 1, revisedBy: OTHER, revisedDate: OLD, fields: { "System.AssignedTo": { newValue: ME_ID } } } ] }],
    [/workItems\/6\/updates/, { value: [
      { rev: 3, revisedBy: ME_ID, revisedDate: LATER, fields: { "System.AssignedTo": { oldValue: null, newValue: ME_ID } } } ] }],
  ]);
  function ident(o) { return o; }
  const r = await run(routes, cur());
  assert.deepStrictEqual(r.events.map((e) => [e.type, e.id, e.actor.name]), [["assignment", "assignment:5:2", "Sara"]]);
  assert.match(r.events[0].url, /\/Alpha\/_workitems\/edit\/5$/);
});

test("mention in a work item comment (html markup); my own comment and plain text are ignored", async () => {
  const mention = '<div><a href="#" data-vss-mention="version:2.0,' + ME + '">@Ahmed</a> please look &amp; reply</div>';
  const routes = base([
    [/_apis\/wit\/wiql/, { workItems: [{ id: 9 }] }],
    [/_apis\/wit\/workitems\?ids/, { value: [{ id: 9, fields: { "System.Title": "T", "System.AssignedTo": OTHER, "System.TeamProject": "Alpha", "System.CommentCount": 3 } }] }],
    [/workItems\/9\/comments/, { comments: [
      { id: 1, text: mention, createdBy: OTHER, createdDate: LATER, modifiedBy: OTHER, modifiedDate: LATER },
      { id: 2, text: mention, createdBy: ME_ID, createdDate: LATER, modifiedBy: ME_ID, modifiedDate: LATER },
      { id: 3, text: "no mention of anyone", createdBy: OTHER, createdDate: LATER, modifiedBy: OTHER, modifiedDate: LATER } ] }],
  ]);
  const r = await run(routes, cur());
  assert.deepStrictEqual(types(r), ["mention"]);
  assert.strictEqual(r.events[0].summary, "@Ahmed please look & reply");
  assert.strictEqual(r.events[0].id, "mention:wi:9:1");
});

test("review request is new once; a known request is silent", async () => {
  const routes = base([[/searchCriteria\.reviewerId/, { value: [pr(7), pr(8)] }]]);
  const r = await run(routes, cur({ rv: ["7"] }));
  assert.deepStrictEqual(r.events.map((e) => e.id), ["review:8"]);
  assert.deepStrictEqual(ev.decodeCursor(r.cursor).rv.sort(), ["7", "8"]);
});

test("comment on my PR is pr-comment; system comments, my comments and old comments are ignored; mention wins", async () => {
  const routes = base([
    [/searchCriteria\.creatorId/, { value: [pr(3, { createdBy: ME_ID })] }],
    [/pullRequests\/3\/threads/, { value: [
      { id: 10, comments: [
        { id: 1, content: "Looks wrong here", author: OTHER, publishedDate: LATER, lastUpdatedDate: LATER },
        { id: 2, content: "Policy changed", author: OTHER, publishedDate: LATER, lastUpdatedDate: LATER, commentType: "system" },
        { id: 3, content: "my reply", author: ME_ID, publishedDate: LATER, lastUpdatedDate: LATER },
        { id: 4, content: "ancient", author: OTHER, publishedDate: OLD, lastUpdatedDate: OLD },
        { id: 5, content: "ping @<{" + ME.toUpperCase() + "}> thanks", author: OTHER, publishedDate: LATER, lastUpdatedDate: LATER } ] } ] }],
  ]);
  const r = await run(routes, cur());
  assert.deepStrictEqual(r.events.map((e) => e.id), ["pr-comment:pr:3:10:1", "mention:pr:3:10:5"]);
});

test("mention on a PR I only review is an event; other comments there are not", async () => {
  const routes = base([
    [/searchCriteria\.reviewerId/, { value: [pr(4)] }],
    [/pullRequests\/4\/threads/, { value: [{ id: 1, comments: [
      { id: 1, content: "chatter", author: OTHER, publishedDate: LATER, lastUpdatedDate: LATER },
      { id: 2, content: "@<" + ME + "> fyi", author: OTHER, publishedDate: LATER, lastUpdatedDate: LATER } ] }] }],
  ]);
  const r = await run(routes, cur({ rv: ["4"] }));
  assert.deepStrictEqual(types(r), ["mention"]);
});

test("failed build requested by me", async () => {
  const routes = base([[/_apis\/build\/builds/, { value: [
    { id: 70, buildNumber: "20261106.1", definition: { name: "CI" }, finishTime: LATER, sourceBranch: "refs/pull/12/merge" },
    { id: 71, buildNumber: "old", definition: { name: "CI" }, finishTime: OLD, sourceBranch: "refs/heads/main" } ] }]]);
  const r = await run(routes, cur());
  assert.deepStrictEqual(r.events.map((e) => [e.type, e.id, e.summary]), [["build-failed", "build-failed:70", "Build failed (pull request 12)"]]);
  assert.ok(r.calls.find((x) => /builds/.test(x.url)).url.includes("requestedFor=ahmed%40contoso.example"));
});

test("polling twice with the returned cursor never repeats an event", async () => {
  const routes = base([[/_apis\/build\/builds/, { value: [{ id: 70, buildNumber: "1", definition: { name: "CI" }, finishTime: LATER, sourceBranch: "refs/heads/main" }] }]]);
  const first = await run(routes, cur(), undefined, T0 + 3600e3);
  assert.strictEqual(first.events.length, 1);
  const second = await run(routes, ev.decodeCursor(first.cursor), undefined, T0 + 3600e3 + 30e3);
  assert.deepStrictEqual(second.events, []);
});

test("a failing detector is reported, the others still deliver, and the time does not advance", async () => {
  const routes = base([
    [/_apis\/build\/builds/, new Error("HTTP 500 for /Alpha/_apis/build/builds")],
    [/searchCriteria\.reviewerId/, { value: [pr(8)] }],
  ]);
  const r = await run(routes, cur({ rv: [] }));
  assert.deepStrictEqual(types(r), ["review-requested"]);
  assert.deepStrictEqual(r.errors.map((e) => e.detector), ["builds"]);
  assert.strictEqual(ev.decodeCursor(r.cursor).t, T0, "cursor time stays so builds are retried");
});

test("an ISO --since has no reviewer baseline, and a failing PR detector keeps it unset", async () => {
  const routes = base([[/searchCriteria\.reviewerId/, new Error("HTTP 500 for /x")]]);
  const r = await run(routes, { v: 1, t: T0, rv: null, ev: [] });
  assert.strictEqual(ev.decodeCursor(r.cursor).rv, null);
  const ok = await run(base([[/searchCriteria\.reviewerId/, { value: [pr(1), pr(2)] }]]), { v: 1, t: T0, rv: null, ev: [] });
  assert.deepStrictEqual(types(ok), [], "existing review requests are not announced without a baseline");
});

test("a full work item page is read oldest first and the cursor resumes after it, skipping nothing", async () => {
  const ids = Array.from({ length: 200 }, (_, i) => ({ id: i + 1 }));
  const day = (n) => "2026-11-06T10:" + n + "0:00.000Z"; // after the cursor time T0 (10:00)
  const items = ids.map((w, i) => ({ id: w.id, fields: { "System.Title": "t", "System.AssignedTo": OTHER, "System.TeamProject": "Alpha",
    "System.CommentCount": 0, "System.ChangedDate": i === 199 ? day(5) : day(4) } }));
  const routes = base([
    [/_apis\/wit\/wiql/, { workItems: ids }],
    [/_apis\/wit\/workitems\?ids/, { value: items }],
  ]);
  const r = await run(routes, cur(), undefined, Date.parse("2026-11-06T12:00:00.000Z"));
  assert.strictEqual(r.truncated, true);
  assert.strictEqual(r.more, true);
  assert.strictEqual(r.covered_until, day(5));
  assert.strictEqual(ev.decodeCursor(r.cursor).t, Date.parse(day(5)), "cursor stops at what was examined, not at now");
  assert.ok(r.calls.find((x) => /wiql/.test(x.url)).body.query.endsWith("ORDER BY [System.ChangedDate] ASC"));
});

test("a short work item page is not truncated and the cursor moves to now", async () => {
  const r = await run(base(), cur(), undefined, T0 + 3600e3);
  assert.strictEqual(r.truncated, false);
  assert.strictEqual(r.more, false);
  assert.strictEqual(r.covered_until, null);
  assert.strictEqual(ev.decodeCursor(r.cursor).t, T0 + 3600e3);
});

test("types filter limits what is read and returned", async () => {
  const routes = base([[/_apis\/build\/builds/, { value: [{ id: 70, buildNumber: "1", definition: { name: "CI" }, finishTime: LATER }] }],
    [/searchCriteria\.reviewerId/, { value: [pr(8)] }]]);
  const r = await run(routes, cur({ rv: [] }), { types: new Set(["review-requested"]) });
  assert.deepStrictEqual(types(r), ["review-requested"]);
  assert.ok(!r.calls.some((x) => /builds|threads/.test(x.url)));
});

test("wiql is time-precise and project-scoped with quoting", async () => {
  const r = await run(base(), cur(), { projects: ["A'lpha"] });
  const w = r.calls.find((x) => /wiql/.test(x.url));
  assert.ok(w.url.includes("timePrecision=true"));
  assert.ok(w.body.query.includes("[System.TeamProject] IN ('A''lpha')"));
});

test("text is stripped of markup and truncated", () => {
  assert.strictEqual(ev.plainText("<b>hi</b>&nbsp;<script>x</script> there"), "hi x there");
  assert.ok(ev.plainText("x".repeat(500)).length <= 240);
});

test("mention matching needs the real id, in either markup", () => {
  assert.ok(ev.mentionsMe('data-vss-mention="version:2.0,' + ME + '"', ME));
  assert.ok(ev.mentionsMe("@<" + ME + ">", ME));
  assert.ok(!ev.mentionsMe("@Ahmed hello " + ME, ME), "a bare id or name is not a mention");
  assert.ok(!ev.mentionsMe("", ME));
});

test("cursor round trip and rejection of garbage", () => {
  const c = { v: 1, t: 5, rv: ["1"], ev: [["a", 1]] };
  assert.deepStrictEqual(ev.decodeCursor(ev.encodeCursor(c)), c);
  assert.throws(() => ev.decodeCursor("not-a-cursor"), /not valid/);
});

test("argument parsing", () => {
  assert.throws(() => ev.parseArgs([]), /--since/);
  assert.throws(() => ev.parseArgs(["--since", "now", "--types", "bogus"]), /unknown event type/);
  const a = ev.parseArgs(["--since", "now", "--project", "A", "--project", "B", "--all-prs"]);
  assert.deepStrictEqual(a.projects, ["A", "B"]);
  assert.strictEqual(a.allPrs, true);
});

test("client: errors name the path only, never the token or query", async () => {
  const c = ev.createClient(ORG, "SECRET-PAT", async () => ({ ok: false, status: 403, json: async () => ({}) }));
  await assert.rejects(() => c.get(ORG + "/_apis/projects?x=SECRET-PAT"), (e) => /HTTP 403 for \/contoso\/_apis\/projects$/.test(e.message) && !/SECRET/.test(e.message));
});

test("client: sends Basic auth built from the PAT", async () => {
  let seen;
  const c = ev.createClient(ORG, "pat", async (u, o) => { seen = o.headers.Authorization; return { ok: true, status: 200, json: async () => ({}) }; });
  await c.get(ORG + "/_apis/projects");
  assert.strictEqual(seen, "Basic " + Buffer.from(":pat").toString("base64"));
});
