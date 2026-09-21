#!/usr/bin/env python3
"""Stage 03 - capture: drive the real app and record one clip per step.

Why one clip per step rather than one long recording:
Playwright starts a video when a PAGE is created and finalises it when the
context closes. Giving every step its own context therefore yields a clip whose
boundaries are exactly the step's boundaries -- so a caption can be pinned to a
clip instead of to a timestamp on a long take. Caption drift stops being a
timing problem and becomes structurally impossible.

The cost is that each step must be able to start on its own, which is why every
step declares `start` (a URL). Authentication is carried across steps by
storage state captured once per role, so the login flow is not re-recorded.

Safety, inherited from qa-browser's discipline:
  * production-looking base URLs are refused unless --allow-production
  * destructive-looking selectors are skipped unless the step opts in
  * credentials are redacted out of every artifact this stage writes
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from _common import (
    DESTRUCTIVE_PATTERN, die, info, is_production, load_config, mask, redact,
    resolve_role, resolve_target, run_dir, slugify, warn, write_json,
)
from _yaml import load as yaml_load

ACTIONS = {"goto", "click", "fill", "select", "press", "hover", "scroll",
           "expect", "wait"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Capture one clip per step.")
    p.add_argument("--steps", required=True, help="Path to steps.yaml")
    p.add_argument("--out", help="Capture output dir (default: run dir 03-capture)")
    p.add_argument("--headed", action="store_true", help="Show the browser")
    p.add_argument("--slow-mo", type=int, default=250,
                   help="ms between actions; keeps the video readable")
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--timeout", type=int, default=15000, help="per-action ms")
    p.add_argument("--only", help="Capture a single work item ID")
    p.add_argument("--allow-production", action="store_true")
    p.add_argument("--dry-run", action="store_true",
                   help="Validate the script without launching a browser")
    return p.parse_args()


# --------------------------------------------------------------------------- #
# validation (runs with or without Playwright installed)
# --------------------------------------------------------------------------- #
def load_steps(path: Path) -> dict:
    if not path.exists():
        die("Step script not found: " + str(path))
    try:
        data = yaml_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - surface any parse failure plainly
        die("Could not parse " + str(path) + ": " + str(exc))
    if not isinstance(data, dict) or not data.get("items"):
        die("Step script has no `items`.")
    return data


def validate(script: dict) -> list[str]:
    problems = []
    for item in script.get("items", []):
        wid = item.get("work_item", "?")
        if not item.get("role"):
            problems.append("item " + str(wid) + ": missing `role`")
        steps = item.get("steps") or []
        if not steps:
            problems.append("item " + str(wid) + ": no steps")
        seen = set()
        for step in steps:
            sid = step.get("id")
            label = "item " + str(wid) + " step " + str(sid)
            if not sid:
                problems.append("item " + str(wid) + ": a step has no `id`")
            elif sid in seen:
                problems.append(label + ": duplicate step id")
            seen.add(sid)
            if not step.get("caption"):
                problems.append(label + ": missing `caption` (it is the video "
                                          "text AND the guide instruction)")
            if not step.get("start"):
                problems.append(label + ": missing `start` URL")
            for action in step.get("actions") or []:
                verb = (action or {}).get("do")
                if verb not in ACTIONS:
                    problems.append(
                        label + ": unknown action " + repr(verb)
                        + " (expected one of " + ", ".join(sorted(ACTIONS)) + ")"
                    )
    return problems


def is_destructive(step: dict) -> str | None:
    if step.get("allow_destructive"):
        return None
    for action in step.get("actions") or []:
        for field in ("selector", "value", "to", "key"):
            blob = str((action or {}).get(field) or "")
            hit = DESTRUCTIVE_PATTERN.search(blob)
            if hit:
                return hit.group(0)
    return None


# --------------------------------------------------------------------------- #
# capture
# --------------------------------------------------------------------------- #
def require_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError:
        die(
            "Playwright is not installed. The capture stage needs it:\n"
            "    pip install playwright\n"
            "    python -m playwright install chromium\n"
            "Other stages (collect / build / publish) do not require it."
        )
    return sync_playwright


def login(context, target_cfg: dict, creds: dict, timeout: int) -> None:
    """Perform the configured login flow in a throwaway page."""
    flow = target_cfg.get("login") or {}
    page = context.new_page()
    page.set_default_timeout(timeout)
    page.goto(target_cfg["base_url"].rstrip("/") + flow.get("path", "/login"))
    if flow.get("username_selector"):
        page.fill(flow["username_selector"], creds["username"])
    if flow.get("password_selector"):
        page.fill(flow["password_selector"], creds["password"])
    if flow.get("submit_selector"):
        page.click(flow["submit_selector"])
    if flow.get("success_selector"):
        page.wait_for_selector(flow["success_selector"], timeout=timeout)
    else:
        page.wait_for_load_state("networkidle")
    page.close()


def storage_for_role(playwright, browser, target_cfg, config, target, role,
                     state_dir: Path, timeout: int) -> Path:
    """Log in once per role and cache the storage state on disk."""
    state_path = state_dir / (slugify(role) + ".json")
    if state_path.exists():
        return state_path
    creds = resolve_role(config, target, role)
    context = browser.new_context(ignore_https_errors=True)
    context.set_default_timeout(timeout)
    try:
        login(context, target_cfg, creds, timeout)
        context.storage_state(path=str(state_path))
        info("logged in as " + role + " (" + mask(creds["password"]) + ")")
    finally:
        context.close()
    return state_path


def run_actions(page, step: dict, timeout: int) -> None:
    for action in step.get("actions") or []:
        verb = action.get("do")
        if verb == "goto":
            page.goto(action["target"])
        elif verb == "click":
            page.click(action["selector"])
        elif verb == "fill":
            page.fill(action["selector"], str(action.get("value", "")))
        elif verb == "select":
            page.select_option(action["selector"], str(action.get("value", "")))
        elif verb == "press":
            page.keyboard.press(action.get("key", "Enter"))
        elif verb == "hover":
            page.hover(action["selector"])
        elif verb == "scroll":
            page.locator(action["to"]).scroll_into_view_if_needed()
        elif verb == "expect":
            page.wait_for_selector(action["selector"], timeout=timeout)
        elif verb == "wait":
            page.wait_for_timeout(int(action.get("ms", 1000)))


def capture_step(browser, item, step, target_cfg, state_path, out_dir, args,
                 secrets) -> dict:
    """Record exactly one step. Returns its row for the capture log."""
    step_key = str(item.get("work_item")) + "-" + str(step.get("id"))
    clip_dir = out_dir / "clips" / step_key
    clip_dir.mkdir(parents=True, exist_ok=True)

    console_errors, failed_requests = [], []
    started = time.monotonic()

    context = browser.new_context(
        storage_state=str(state_path) if state_path else None,
        viewport={"width": args.width, "height": args.height},
        record_video_dir=str(clip_dir),
        record_video_size={"width": args.width, "height": args.height},
        ignore_https_errors=True,
    )
    context.set_default_timeout(args.timeout)
    page = context.new_page()
    page.on("console", lambda m: (
        console_errors.append(redact(m.text, secrets)[:500])
        if m.type == "error" else None
    ))
    page.on("requestfailed", lambda r: failed_requests.append(
        redact(r.url, secrets)[:300]
    ))

    video = page.video
    screenshot = out_dir / "screenshots" / (step_key + ".png")
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    status, error = "ok", None

    try:
        url = target_cfg["base_url"].rstrip("/") + str(step.get("start", "/"))
        page.goto(url)
        run_actions(page, step, args.timeout)
        page.wait_for_timeout(int(step.get("hold_ms", 1200)))
        page.screenshot(path=str(screenshot), full_page=False)
    except Exception as exc:  # noqa: BLE001 - one bad step must not kill the run
        status, error = "failed", redact(str(exc).split("\n")[0][:400], secrets)
        try:
            page.screenshot(path=str(screenshot), full_page=False)
        except Exception:  # noqa: BLE001
            screenshot = None
    finally:
        page.close()
        context.close()

    wall_ms = int((time.monotonic() - started) * 1000)
    clip = None
    if video:
        try:
            produced = Path(video.path())
            if produced.exists():
                clip = clip_dir / (step_key + ".webm")
                produced.replace(clip)
        except Exception as exc:  # noqa: BLE001
            warn("no video for " + step_key + ": " + str(exc))

    return {
        "work_item": item.get("work_item"),
        "step_id": step.get("id"),
        "key": step_key,
        "caption": step.get("caption"),
        "role": item.get("role"),
        "start": step.get("start"),
        "actions": step.get("actions") or [],
        "status": status,
        "error": error,
        "clip": str(clip) if clip else None,
        "screenshot": str(screenshot) if screenshot else None,
        "wall_ms": wall_ms,
        "console_errors": console_errors[:20],
        "failed_requests": failed_requests[:20],
    }


def main() -> int:
    args = parse_args()
    script_path = Path(args.steps)
    script = load_steps(script_path)

    problems = validate(script)
    if problems:
        for problem in problems:
            print("  - " + problem, file=sys.stderr)
        die(str(len(problems)) + " problem(s) in the step script; fix and re-run.")

    config = load_config()
    target = script.get("target", "staging")
    target_cfg = resolve_target(config, target)
    base_url = target_cfg["base_url"]

    if is_production(base_url, config) and not args.allow_production:
        die(
            "Refusing to capture against a production-looking URL: " + base_url
            + "\nPoint `target` at staging, or pass --allow-production if you "
            "are certain this data is disposable."
        )

    out_dir = Path(args.out) if args.out else run_dir(
        script.get("sprint", "sprint")) / "03-capture"
    out_dir.mkdir(parents=True, exist_ok=True)

    items = script["items"]
    if args.only:
        items = [i for i in items if str(i.get("work_item")) == str(args.only)]
        if not items:
            die("No work item " + args.only + " in the step script.")

    planned = sum(len(i.get("steps") or []) for i in items)
    if args.dry_run:
        info("dry run: step script is valid.")
        info("  target     : " + target + " -> " + base_url)
        info("  work items : " + str(len(items)))
        info("  steps      : " + str(planned))
        for item in items:
            for step in item.get("steps") or []:
                flag = is_destructive(step)
                if flag:
                    warn("  would SKIP " + str(item.get("work_item")) + "-"
                         + str(step.get("id")) + ": destructive (" + flag + ")")
        return 0

    sync_playwright = require_playwright()
    secrets = [
        creds.get("password", "")
        for creds in (target_cfg.get("roles") or {}).values()
    ]
    state_dir = out_dir / ".auth"
    state_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=not args.headed, slow_mo=args.slow_mo
        )
        try:
            states = {}
            for item in items:
                role = item.get("role")
                if role not in states:
                    states[role] = storage_for_role(
                        playwright, browser, target_cfg, config, target, role,
                        state_dir, args.timeout,
                    )
                for step in item.get("steps") or []:
                    flag = is_destructive(step)
                    key = str(item.get("work_item")) + "-" + str(step.get("id"))
                    if flag:
                        warn("skipping " + key + ": destructive selector (" + flag
                             + "); set allow_destructive: true to override")
                        rows.append({
                            "work_item": item.get("work_item"),
                            "step_id": step.get("id"), "key": key,
                            "caption": step.get("caption"), "role": role,
                            "status": "skipped-destructive", "error": flag,
                            "clip": None, "screenshot": None, "wall_ms": 0,
                            "console_errors": [], "failed_requests": [],
                            "actions": step.get("actions") or [],
                            "start": step.get("start"),
                        })
                        continue
                    info("capturing " + key + " - " + str(step.get("caption")))
                    rows.append(capture_step(
                        browser, item, step, target_cfg, states[role],
                        out_dir, args, secrets,
                    ))
        finally:
            browser.close()

    log = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sprint": script.get("sprint"),
        "target": target,
        "base_url": base_url,
        "viewport": {"width": args.width, "height": args.height},
        "steps": rows,
        "summary": {
            "total": len(rows),
            "ok": sum(1 for r in rows if r["status"] == "ok"),
            "failed": sum(1 for r in rows if r["status"] == "failed"),
            "skipped": sum(1 for r in rows if r["status"].startswith("skipped")),
        },
    }
    log_path = out_dir / "capture-log.json"
    write_json(log_path, log)

    info("captured " + str(log["summary"]["ok"]) + "/" + str(len(rows))
         + " steps (" + str(log["summary"]["failed"]) + " failed, "
         + str(log["summary"]["skipped"]) + " skipped)")
    print(log_path)
    return 0 if log["summary"]["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
