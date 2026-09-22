#!/usr/bin/env python3
"""Stage 05 - publish: write the HTML reproduction guide.

Two files, deliberately separate:

  sprint-<id>-guide.html        shareable. Names the ROLE each step needs and
                                points at the config key holding its login.
                                Contains no secret, ever.

  credentials/<id>-credentials.html   local only, written to a gitignored
                                directory, and only when --with-credentials is
                                passed. This is a plaintext password file; it is
                                never bundled with the video.

Both the guide and the video read their step text from the same step script, so
the written instruction and the on-screen caption cannot disagree.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
from datetime import datetime, timezone
from pathlib import Path

from _common import (
    config_path, die, info, load_config, mask, read_json, recap_dir,
    resolve_target, run_dir, slugify, warn,
)
from _yaml import load as yaml_load

STATUS_LABEL = {
    "ok": ("verified", "ok"),
    "failed": ("not verified - capture failed", "bad"),
    "skipped-destructive": ("not captured - destructive action", "warn"),
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Publish the HTML reproduction guide.")
    p.add_argument("--capture-log", required=True)
    p.add_argument("--steps", help="Step script (defaults to the run's 02-script)")
    p.add_argument("--video", help="Path or URL of the rendered video")
    p.add_argument("--out", help="Output HTML path")
    p.add_argument("--with-credentials", action="store_true",
                   help="Also write the local-only credentials file")
    p.add_argument("--no-embed", action="store_true",
                   help="Link screenshots instead of embedding them")
    return p.parse_args()


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def describe(action: dict) -> str:
    """Render one action as an instruction a human can follow by hand."""
    verb = (action or {}).get("do")
    sel = esc(action.get("selector") or action.get("to") or action.get("target") or "")
    code = "<code>" + sel + "</code>"
    if verb == "goto":
        return "Go to " + code
    if verb == "click":
        return "Click " + code
    if verb == "fill":
        return "Type <strong>" + esc(action.get("value")) + "</strong> into " + code
    if verb == "select":
        return "Choose <strong>" + esc(action.get("value")) + "</strong> in " + code
    if verb == "press":
        return "Press <kbd>" + esc(action.get("key", "Enter")) + "</kbd>"
    if verb == "hover":
        return "Hover over " + code
    if verb == "scroll":
        return "Scroll to " + code
    if verb == "expect":
        return "Confirm " + code + " is visible"
    if verb == "wait":
        return "Wait " + esc(action.get("ms", 1000)) + "ms"
    return esc(verb)


def screenshot_src(path_str, embed: bool, out_dir: Path):
    if not path_str:
        return None
    path = Path(path_str)
    if not path.exists():
        return None
    if not embed:
        try:
            return path.resolve().relative_to(out_dir.resolve()).as_posix()
        except ValueError:
            return path.resolve().as_uri()
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return "data:image/png;base64," + data


CSS = """
:root{--bg:#f7f8fa;--fg:#12151c;--muted:#5b6474;--card:#fff;--line:#e3e7ee;
--accent:#2557d6;--ok:#127a45;--bad:#b3261e;--warn:#8a5a00;--code:#eef1f6;}
@media (prefers-color-scheme:dark){:root{--bg:#0b0f17;--fg:#e9edf5;--muted:#9aa4b8;
--card:#121826;--line:#232c3d;--accent:#8ab4ff;--ok:#4ade80;--bad:#ff6b6b;
--warn:#fbbf24;--code:#1a2130;}}
*{box-sizing:border-box}
body{margin:0;padding:32px 16px;background:var(--bg);color:var(--fg);
font:16px/1.6 "Segoe UI",Inter,system-ui,-apple-system,"Noto Sans Arabic",sans-serif}
.wrap{max-width:900px;margin:0 auto}
h1{font-size:2rem;margin:0 0 6px} h2{font-size:1.25rem;margin:0}
.sub{color:var(--muted);margin-bottom:28px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:20px 22px;margin-bottom:18px}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.8rem;
font-weight:600;border:1px solid currentColor}
.badge.ok{color:var(--ok)} .badge.bad{color:var(--bad)} .badge.warn{color:var(--warn)}
.pill{display:inline-block;background:var(--code);border-radius:999px;
padding:2px 10px;font-size:.82rem;color:var(--muted);margin-right:6px}
code,kbd{background:var(--code);border-radius:5px;padding:1px 6px;
font:.88em Consolas,ui-monospace,monospace;word-break:break-word}
ol.steps{list-style:none;counter-reset:s;padding:0;margin:0}
ol.steps>li{counter-increment:s;position:relative;padding:18px 0 18px 46px;
border-top:1px solid var(--line)}
ol.steps>li::before{content:counter(s);position:absolute;left:0;top:18px;
width:30px;height:30px;border-radius:50%;background:var(--accent);color:#fff;
display:flex;align-items:center;justify-content:center;font-size:.9rem;font-weight:700}
.cap{font-size:1.06rem;font-weight:600;margin-bottom:8px}
ul.actions{margin:8px 0 0;padding-left:18px;color:var(--muted);font-size:.95rem}
img.shot{width:100%;border:1px solid var(--line);border-radius:8px;margin-top:12px}
a{color:var(--accent)}
.warnbox{border-left:4px solid var(--warn);background:var(--card);
border-radius:8px;padding:14px 18px;margin-bottom:22px;color:var(--muted)}
.dangerbox{border:2px solid var(--bad);border-radius:12px;padding:18px 22px;
margin-bottom:24px;color:var(--bad);font-weight:600}
table{width:100%;border-collapse:collapse;margin-top:10px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);
font-size:.95rem} th{color:var(--muted);font-weight:600}
footer{color:var(--muted);font-size:.86rem;margin-top:30px;text-align:center}
"""


def build_guide(script, log, args, out_dir: Path, config) -> str:
    sprint = script.get("sprint") or log.get("sprint") or "Sprint"
    target = script.get("target", log.get("target", "staging"))
    base_url = log.get("base_url", "")
    rows = {r["key"]: r for r in log.get("steps", [])}
    embed = not args.no_embed

    roles_used = sorted({i.get("role") for i in script.get("items", []) if i.get("role")})
    role_rows = "".join(
        "<tr><td><code>" + esc(role) + "</code></td>"
        "<td><code>targets." + esc(target) + ".roles." + esc(role) + "</code></td></tr>"
        for role in roles_used
    )

    parts = [
        "<div class='wrap'>",
        "<h1>" + esc(sprint) + " - reproduction guide</h1>",
        "<div class='sub'>Every step below is the same text spoken and shown in "
        "the sprint video. Follow them in order to reproduce what was demonstrated."
        "</div>",
    ]

    if args.video:
        parts.append(
            "<div class='card'><h2>Video</h2><p><a href='" + esc(args.video)
            + "'>" + esc(args.video) + "</a></p></div>"
        )

    parts.append(
        "<div class='card'><h2>Before you start</h2>"
        "<table><tr><th>Environment</th><td><code>" + esc(target)
        + "</code> - <a href='" + esc(base_url) + "'>" + esc(base_url) + "</a></td></tr>"
        "</table>"
        "<h2 style='margin-top:18px;font-size:1.05rem'>Logins you need</h2>"
        "<table><tr><th>Role</th><th>Where its credentials live</th></tr>"
        + role_rows + "</table>"
        "<div class='warnbox' style='margin-top:14px'>This guide deliberately "
        "contains no passwords. Read them from <code>" + esc(config_path().name)
        + "</code> on the machine that ran the capture, or ask the team for the "
        "matching vault entry.</div></div>"
    )

    for item in script.get("items", []):
        wid = item.get("work_item")
        head = [
            "<div class='card'>",
            "<h2>#" + esc(wid) + " - " + esc(item.get("title", "")) + "</h2>",
            "<div style='margin:8px 0 4px'>",
        ]
        if item.get("parent_pbi"):
            head.append("<span class='pill'>PBI #" + esc(item["parent_pbi"]) + "</span>")
        if item.get("role"):
            head.append("<span class='pill'>as " + esc(item["role"]) + "</span>")
        head.append("</div><ol class='steps'>")
        parts.extend(head)

        for step in item.get("steps") or []:
            key = str(wid) + "-" + str(step.get("id"))
            row = rows.get(key, {})
            label, tone = STATUS_LABEL.get(row.get("status", ""), ("not captured", "warn"))
            steps_html = [
                "<li>" + describe(a) + "</li>" for a in (step.get("actions") or [])
            ]
            if step.get("show_login"):
                # The role NAME and the config key, never the credentials -
                # this page is the shareable one.
                steps_html.insert(0, (
                    "<li>Sign in as <strong>" + esc(item.get("role"))
                    + "</strong> - the username and password are the <code>"
                    + esc(item.get("role")) + "</code> entry for this target in"
                    " <code>.sprint-recap.local.json</code></li>"
                ))
            actions = "".join(steps_html)
            parts.append("<li>")
            parts.append("<div class='cap'>" + esc(step.get("caption")) + "</div>")
            parts.append(
                "<div><span class='pill'>start: <code>" + esc(step.get("start"))
                + "</code></span><span class='badge " + tone + "'>" + esc(label)
                + "</span></div>"
            )
            if actions:
                parts.append("<ul class='actions'>" + actions + "</ul>")
            if row.get("error"):
                parts.append(
                    "<div class='warnbox' style='margin-top:10px'>Capture note: "
                    + esc(row["error"]) + "</div>"
                )
            src = screenshot_src(row.get("screenshot"), embed, out_dir)
            if src:
                parts.append(
                    "<img class='shot' loading='lazy' alt='"
                    + esc(step.get("caption")) + "' src='" + src + "'>"
                )
            parts.append("</li>")
        parts.append("</ol></div>")

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts.append(
        "<footer>Generated by the sprint-recap plugin on " + generated
        + " - regenerate with <code>/sprint-recap publish</code></footer></div>"
    )
    return page(esc(sprint) + " - reproduction guide", "".join(parts))


def build_credentials(script, log, config) -> str:
    target = script.get("target", "staging")
    target_cfg = resolve_target(config, target)
    roles = target_cfg.get("roles") or {}
    used = sorted({i.get("role") for i in script.get("items", []) if i.get("role")})

    rows = []
    for role in used:
        creds = roles.get(role) or {}
        rows.append(
            "<tr><td><code>" + esc(role) + "</code></td><td><code>"
            + esc(creds.get("username", "(missing)")) + "</code></td><td><code>"
            + esc(creds.get("password", "(missing)")) + "</code></td></tr>"
        )

    body = (
        "<div class='wrap'>"
        "<div class='dangerbox'>PLAINTEXT CREDENTIALS - do not commit, email, "
        "Slack, or screen-share this file. It is written outside the run "
        "directory and its folder is gitignored. Delete it when you are done."
        "</div>"
        "<h1>" + esc(script.get("sprint", "Sprint")) + " - credentials</h1>"
        "<div class='sub'>Environment <code>" + esc(target) + "</code> - "
        + esc(target_cfg.get("base_url", "")) + "</div>"
        "<div class='card'><table><tr><th>Role</th><th>Username</th>"
        "<th>Password</th></tr>" + "".join(rows) + "</table></div>"
        "</div>"
    )
    return page("Credentials - " + esc(script.get("sprint", "Sprint")), body)


def page(title: str, body: str) -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>" + title + "</title><style>" + CSS + "</style></head>"
        "<body>" + body + "</body></html>"
    )


def main() -> int:
    args = parse_args()
    log = read_json(Path(args.capture_log))
    capture_dir = Path(args.capture_log).parent

    steps_path = Path(args.steps) if args.steps else None
    if steps_path is None:
        for candidate in (capture_dir.parent / "02-script" / "steps.yaml",
                          capture_dir.parent / "02-script" / "steps.json"):
            if candidate.exists():
                steps_path = candidate
                break
    if steps_path is None or not steps_path.exists():
        die("Step script not found; pass --steps explicitly.")
    script = yaml_load(steps_path.read_text(encoding="utf-8"))

    config = load_config()
    sprint_slug = slugify(str(script.get("sprint") or log.get("sprint") or "sprint"))
    stem = sprint_slug if sprint_slug.startswith("sprint") else "sprint-" + sprint_slug
    out = Path(args.out) if args.out else (
        capture_dir.parent / "05-publish" / (stem + "-guide.html")
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_guide(script, log, args, out.parent, config), encoding="utf-8")
    info("guide      : " + str(out))

    if args.with_credentials:
        creds_dir = recap_dir() / "credentials"
        creds_dir.mkdir(parents=True, exist_ok=True)
        creds_out = creds_dir / (sprint_slug + "-credentials.html")
        creds_out.write_text(build_credentials(script, log, config), encoding="utf-8")
        warn("credentials: " + str(creds_out)
             + "  <- plaintext, gitignored, do not share with the video")

    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
