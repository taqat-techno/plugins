#!/usr/bin/env python3
r"""Validate the shape of every plugin's `evals/` suite (HR-20, behavioural gate).

The third structural validator. `validate_plugin.py` checks one plugin's shape,
`validate_marketplace.py` checks that its components load, and this checks that the
eval suites which measure behaviour are themselves well-formed - before you spend
model tokens discovering it the expensive way.

Enforced, per case:
  * `fires-on-<kebab>` / `ignores-<kebab>` naming; only prompt.md + graders/ inside
  * prompt frontmatter keys limited to max_turns / allowed_tools / tags
  * `allowed_tools: [Skill]` exactly - a routing case that can read files spends its
    turns exploring the empty scratch workspace instead of answering
  * prompt names no component ADDRESS (multi-segment skill id, namespaced id, slash
    command). Naming the technology ("my Django view", "Odoo 19") is legitimate
  * fire case: skill-fired.md (tool_used/Skill, input_match carrying the
    `(?:[\w-]+:)?` namespace prefix and resolving to a real skill DIRECTORY name)
    plus criteria.md (llm, with explicit PASS if / FAIL if conditions)
  * ignore case: skill-not-fired.md only, with min 0, max 0, arm both, no input_match
    - without `arm: both` the grader is excluded from both arms and is decorative
  * ASCII, LF, no BOM, no trailing whitespace
  * `evals/results/` may exist but must be git-ignored (it holds run transcripts and
    absolute machine paths)

stdlib only, Python 3.10+. Run from the marketplace plugins/ directory:
    python validate_evals.py [plugin-dir ...]
Exit 0 clean, 1 on any FAIL.
"""
from __future__ import annotations
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

CASE_RE = re.compile(r"^(fires-on|ignores)-[a-z0-9]+(-[a-z0-9]+)*$")
PROMPT_KEYS = {"max_turns", "allowed_tools", "tags"}
TOOLS_OK = "[Skill]"
NS_PREFIX = r"(?:[\w-]+:)?"

fails: list[str] = []
warns: list[str] = []
stats = {"plugins": 0, "fire": 0, "ignore": 0, "files": 0}
SEEN_TARGETS: set = set()


def fail(where: str, msg: str) -> None:
    fails.append(f"FAIL {where}: {msg}")


def warn(where: str, msg: str) -> None:
    warns.append(f"WARN {where}: {msg}")


def hygiene(p: str, rel: str) -> str:
    with open(p, "rb") as fh:
        raw = fh.read()
    stats["files"] += 1
    if raw.startswith(b"\xef\xbb\xbf"):
        fail(rel, "UTF-8 BOM present")
        raw = raw[3:]
    if b"\r\n" in raw:
        fail(rel, "CRLF line endings (must be LF)")
    try:
        raw.decode("ascii")
    except UnicodeDecodeError as e:
        bad = raw.decode("utf-8", "replace")[max(0, e.start - 25):e.start + 25]
        fail(rel, f"non-ASCII byte at offset {e.start}: ...{bad!r}...")
    text = raw.decode("utf-8", "replace")
    for i, line in enumerate(text.split("\n"), 1):
        if line != line.rstrip():
            fail(rel, f"trailing whitespace on line {i}")
            break
    return text


def split_fm(text: str, rel: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        fail(rel, "missing YAML frontmatter opening ---")
        return {}, text
    end = text.find("\n---\n", 3)
    if end == -1:
        fail(rel, "unterminated frontmatter (no closing ---)")
        return {}, text
    fm: dict[str, str] = {}
    for line in text[4:end].split("\n"):
        if not line.strip():
            continue
        if ":" not in line:
            fail(rel, f"unparseable frontmatter line: {line!r}")
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip()
    return fm, text[end + 5:]


# --- forced-routing detection -------------------------------------------------
# Naming the TECHNOLOGY is legitimate and unavoidable: a real user says "my Django
# view", "Azure DevOps", "Odoo 19". What must never appear is a component ADDRESS -
# a multi-segment skill id, a namespaced id, a slash command, or the words
# skill/plugin/agent used to point at the thing under test.
ROUTING_PATTERNS = (
    (r"/[a-z][a-z0-9-]*:[a-z0-9-]+", "slash command invocation"),
    # "agent" alone is legitimate domain vocabulary for the worktree / agent-safety /
    # devops plugins ("brought in as agent 2"), so a component reference has to look
    # like an address: a named component, or an imperative aimed at skill/plugin.
    (r"\b(use|invoke|load|run|trigger|apply)\b[^.]{0,40}\b(skill|plugin)\b",
     "tells Claude which component to use"),
    (r"\bthe\s+[a-z0-9-]{3,}\s+(skill|plugin|agent)\b", "names a component explicitly"),
)

# A filename as the SUBJECT of a question is fine ("a page called Setup.md vanished").
# Asking Claude to open one is not, and neither is a real path. Technology names that
# contain a dot (Next.js, Node.js) are not filenames.
WORKSPACE_PATTERNS = (
    (r"\battached\b", "references an attachment"),
    (r"\b(look at|open|read|check|inspect|review)\s+(the\s+|my\s+|this\s+)?"
     r"(attached\s+)?(file|repo|repository|codebase|project|directory|folder|source)\b",
     "asks Claude to read something that will not exist in an empty workspace"),
    (r"[A-Za-z]:\\", "absolute Windows path"),
    (r"(?<![\w.])[\w-]+/[\w-]+\.(py|js|jsx|ts|tsx|md|json|ya?ml|xml|s?css)\b",
     "file path that will not exist"),
)


def check_prompt(path: str, rel: str, plugin: str, skill_names: set[str]) -> None:
    text = hygiene(path, rel)
    fm, body = split_fm(text, rel)
    extra = set(fm) - PROMPT_KEYS
    if extra:
        fail(rel, f"unknown frontmatter key(s) {sorted(extra)} (unknown key = load error)")
    if "allowed_tools" not in fm:
        fail(rel, "missing allowed_tools")
    elif fm["allowed_tools"] != TOOLS_OK:
        fail(rel, f"allowed_tools must be exactly {TOOLS_OK}, got {fm['allowed_tools']!r}")
    if "max_turns" not in fm:
        fail(rel, "missing max_turns")

    body = body.strip()
    if len(body) < 30:
        fail(rel, f"prompt body too short ({len(body)} chars)")
    low = body.lower()

    # Multi-segment skill ids cannot occur in natural user phrasing.
    for s in sorted((n for n in skill_names if "-" in n), key=len, reverse=True):
        if s.lower() in low:
            fail(rel, f"prompt names the skill id ({s!r}) - that forces routing")
            break
    for pat, why in ROUTING_PATTERNS:
        if re.search(pat, body, re.I):
            fail(rel, f"forced routing - {why}: /{pat}/")
    if re.search(rf"\b{re.escape(plugin)}\b[^.]{{0,25}}\b(skill|plugin)\b", body, re.I):
        fail(rel, f"forced routing - names {plugin!r} as a plugin/skill")

    for pat, why in WORKSPACE_PATTERNS:
        if re.search(pat, body, re.I):
            warn(rel, f"{why}: /{pat}/")


def check_grader(path: str, rel: str, expect_type: str) -> dict[str, str]:
    text = hygiene(path, rel)
    fm, body = split_fm(text, rel)
    if fm.get("type") != expect_type:
        fail(rel, f"type must be {expect_type!r}, got {fm.get('type')!r}")
    return {**fm, "__body__": body.strip()}


def targets_in(input_match: str) -> list[str]:
    """Every bare skill-name token an input_match can match, in any accepted form:
    ...)?name"   ...)?(?:a|b)"   ...)?(?:x-)?name"
    """
    tail = input_match
    i = tail.rfind(")?")
    if i != -1:
        tail = tail[i + 2:]
    tail = tail.split('"')[0]
    tail = re.sub(r"\(\?:|\)\?|\)", "", tail)
    return [t for t in re.split(r"[|]", tail) if re.fullmatch(r"[a-z0-9][a-z0-9-]*-?", t or "")]


def check_case(cdir: str, plugin: str, skill_names: set[str], dir_names: set[str]) -> None:
    name = os.path.basename(cdir)
    rel = f"{plugin}/evals/{name}"
    if not CASE_RE.match(name):
        fail(rel, "case directory name must match ^(fires-on|ignores)-<kebab>$")
    kind = "fire" if name.startswith("fires-on-") else "ignore"
    stats[kind] += 1

    for e in sorted(os.listdir(cdir)):
        if e not in {"prompt.md", "graders"}:
            fail(rel, f"unexpected entry {e!r} (only prompt.md and graders/ allowed)")

    p = os.path.join(cdir, "prompt.md")
    if not os.path.exists(p):
        fail(rel, "prompt.md missing")
    else:
        check_prompt(p, f"{rel}/prompt.md", plugin, skill_names)

    gdir = os.path.join(cdir, "graders")
    if not os.path.isdir(gdir):
        fail(rel, "graders/ missing")
        return
    gfiles = sorted(f for f in os.listdir(gdir) if f.endswith(".md"))
    junk = [f for f in os.listdir(gdir) if not f.endswith(".md")]
    if junk:
        fail(rel, f"non-markdown file(s) in graders/: {junk}")

    if kind == "fire":
        if set(gfiles) != {"skill-fired.md", "criteria.md"}:
            fail(rel, f"fire case needs exactly skill-fired.md + criteria.md, got {gfiles}")
        if "skill-fired.md" in gfiles:
            g = f"{rel}/graders/skill-fired.md"
            fm = check_grader(os.path.join(gdir, "skill-fired.md"), g, "tool_used")
            if fm.get("tool") != "Skill":
                fail(g, f"tool must be 'Skill', got {fm.get('tool')!r}")
            im = fm.get("input_match", "")
            if not im:
                fail(g, "input_match missing - a fire case must name the skill it expects")
            elif NS_PREFIX not in im:
                fail(g, f"input_match lacks the mandatory {NS_PREFIX} namespace prefix: {im}")
            else:
                toks = targets_in(im)
                known = [t for t in toks if t in skill_names]
                if not toks:
                    fail(g, f"cannot extract any target skill name from input_match: {im}")
                elif not known:
                    fail(g, f"input_match targets {toks} - none is a skill of this plugin")
                elif not any(t in dir_names for t in toks):
                    fail(g, f"input_match targets {toks} but matches no skill DIRECTORY name "
                            f"(the addressable id) - it would never match at runtime")
                else:
                    t0 = next(t for t in toks if t in dir_names)
                    if (plugin, t0) in SEEN_TARGETS:
                        warn(f"{plugin}/evals", f"two fire cases target the same skill {t0!r}")
                    SEEN_TARGETS.add((plugin, t0))
        if "criteria.md" in gfiles:
            g = f"{rel}/graders/criteria.md"
            fm = check_grader(os.path.join(gdir, "criteria.md"), g, "llm")
            b = fm["__body__"]
            if "PASS if" not in b:
                fail(g, "rubric must contain 'PASS if'")
            if "FAIL if" not in b:
                fail(g, "rubric must contain 'FAIL if'")
            if len(b) < 80:
                fail(g, f"rubric too vague to discriminate ({len(b)} chars)")
    else:
        if set(gfiles) != {"skill-not-fired.md"}:
            fail(rel, f"ignore case needs exactly skill-not-fired.md, got {gfiles}")
        if "skill-not-fired.md" in gfiles:
            g = f"{rel}/graders/skill-not-fired.md"
            fm = check_grader(os.path.join(gdir, "skill-not-fired.md"), g, "tool_used")
            if fm.get("tool") != "Skill":
                fail(g, f"tool must be 'Skill', got {fm.get('tool')!r}")
            if fm.get("min") != "0":
                fail(g, f"min must be 0, got {fm.get('min')!r}")
            if fm.get("max") != "0":
                fail(g, f"max must be 0, got {fm.get('max')!r}")
            if fm.get("arm") != "both":
                fail(g, "arm must be 'both' - without it the negative case is excluded "
                        "from both arms and is decorative")
            if "input_match" in fm:
                fail(g, "ignore case must have NO input_match (it asserts no skill fired at all)")


def main() -> int:
    plugin_dirs = sys.argv[1:] or sorted(
        d for d in os.listdir(".") if os.path.isdir(os.path.join(d, "evals"))
    )
    for d in plugin_dirs:
        d = d.rstrip("/\\")
        edir = os.path.join(d, "evals")
        if not os.path.isdir(edir):
            fail(d, "no evals/ directory")
            continue
        stats["plugins"] += 1
        dir_names: set[str] = set()
        skill_names: set[str] = set()
        for sp in glob.glob(os.path.join(d, "skills", "*", "SKILL.md")):
            dn = os.path.basename(os.path.dirname(sp))
            dir_names.add(dn)
            skill_names.add(dn)
            m = re.search(r"^name:\s*(.+?)\s*$",
                          open(sp, encoding="utf-8", errors="replace").read(4000), re.M)
            if m:
                skill_names.add(m.group(1).strip().strip("\"'"))
        base = os.path.basename(d)
        pname = base[:-7] if base.endswith("-plugin") else base

        for e in sorted(os.listdir(edir)):
            full = os.path.join(edir, e)
            if not os.path.isdir(full):
                fail(f"{d}/evals", f"stray file {e!r} at suite root")
            elif e == "results":
                # Legitimate run output. It must be git-ignored, never committed.
                import subprocess
                r = subprocess.run(["git", "check-ignore", "-q", full],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    fail(f"{d}/evals", "results/ exists but is NOT git-ignored - it holds run "
                                       "transcripts and absolute machine paths")
            elif e == "mocks":
                pass  # suite-wide MCP mocks are legitimate; none authored yet
            else:
                check_case(full, pname, skill_names, dir_names)

    print(f"plugins checked : {stats['plugins']}")
    print(f"fire cases      : {stats['fire']}")
    print(f"ignore cases    : {stats['ignore']}")
    print(f"files checked   : {stats['files']}")
    print()
    for w in warns:
        print(w)
    if warns:
        print()
    for f in fails:
        print(f)
    print()
    print(f"RESULT: {len(fails)} FAIL, {len(warns)} WARN")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
