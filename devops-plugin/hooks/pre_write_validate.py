#!/usr/bin/env python3
"""PreToolUse hook: validation context for Azure DevOps write operations.

Reads the PreToolUse JSON payload on stdin (tool_name + tool_input).

Process-aware: the active process preset comes from the profile's `process:` field
(${CLAUDE_PLUGIN_DATA}/profile.md, legacy ~/.claude/devops.md) and is looked up in data/state_machine.json `processPresets`.
Role rules (`roleRules`) and Task naming rules (`taskNaming`) apply ONLY when the
active preset - or a profile override - defines them. The stock presets (basic,
agile, scrum, cmmi) define none. No profile, no `process:` field, or an unknown
preset name -> generic behavior: reminders only.

  Exit 0 + JSON ask   policy violation (role rule / naming rule) or a target state
                      the active preset does not define. permissionDecision "ask"
                      with the reason, so the user decides. Default enforcement.
  Exit 2 + stderr     hard block, only for:
                        * a policy violation when the profile sets `enforcement: block`
                        * a comment with unresolved @mentions (a correctness guard)
  Exit 0 + JSON       soft reminder as hookSpecificOutput.additionalContext (also the
                      channel for violations under `enforcement: advise`). Both
                      hookEventName and additionalContext are always emitted.

Design: hooks inject REMINDERS and surface clear violations. The LLM + rules/ +
data/ do the full validation (the hook cannot see an item's current state or type
on an update, so from -> to validity is checked by the model against the preset).

Every field is read from the parsed tool_input (the target state from the
JSON-Patch update whose path is /fields/System.State). Profile:
${CLAUDE_PLUGIN_DATA}/profile.md, else the legacy ~/.claude/devops.md.
Stdlib-only plus the vendored hooklib. Fail-OPEN on any error or after 8 seconds.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

_GUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


def _str_field(tool_input, key):
    """A top-level string field of tool_input, or ""."""
    value = tool_input.get(key)
    return value.strip() if isinstance(value, str) else ""


def _profile_path():
    """The profile: ${CLAUDE_PLUGIN_DATA}/profile.md, else the legacy ~/.claude/devops.md."""
    data = os.environ.get("CLAUDE_PLUGIN_DATA", "").strip()
    if data:
        current = Path(data) / "profile.md"
        if current.is_file():
            return current
    return Path.home() / ".claude" / "devops.md"


_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "state_machine.json"
_OFF_VALUES = ("off", "none", "false", "null", "~", "no", "[]", "{}")
_ENFORCEMENT_VALUES = ("ask", "block", "advise")


def _scalar(value):
    return value.strip().strip("'\"").strip()


def _override(value, frontmatter, key):
    """A roleRules/taskNaming override: dict, False (explicitly off) or None (absent).

    Inline JSON / YAML flow form (`taskNaming: {"prefixes": ["[Dev]"]}`) is parsed with
    the stdlib; a block-YAML mapping is parsed only if PyYAML happens to be installed.
    """
    v = value.strip()
    if not v:
        try:
            import yaml  # optional; stdlib-only otherwise
            data = yaml.safe_load(frontmatter) or {}
            got = data.get(key) if isinstance(data, dict) else None
            return got if isinstance(got, dict) else None
        except Exception:
            return None
    if _scalar(v).lower() in _OFF_VALUES:
        return False
    try:
        got = json.loads(v)
    except ValueError:
        return None
    return got if isinstance(got, dict) else None


def _load_profile(profile):
    """Parse the fields the hook needs from ~/.claude/devops.md, or None if absent."""
    if not profile.is_file():
        return None
    try:
        text = profile.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    lines = text.splitlines()
    front = text
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), len(lines))
        front = "\n".join(lines[1:end])
    info = {"role": _user_role(lines), "process": "", "enforcement": "ask",
            "roleRules": None, "taskNaming": None}
    for line in front.splitlines():
        if not line or line[0] in " \t#" or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key == "process":
            info["process"] = _scalar(value).lower()
        elif key == "enforcement":
            enf = _scalar(value).lower()
            if enf in _ENFORCEMENT_VALUES:
                info["enforcement"] = enf
        elif key in ("roleRules", "taskNaming"):
            info[key] = _override(value, front, key)
    return info


def _load_preset(name):
    """(preset dict, all-preset dict) for a preset name; preset is None if unknown."""
    try:
        data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        presets = data.get("processPresets") or {}
    except (OSError, ValueError, AttributeError):
        return None, {}
    preset = presets.get(name) if name else None
    return (preset if isinstance(preset, dict) else None), presets


def _preset_states(preset):
    states = set()
    for cfg in (preset.get("workItemTypes") or {}).values():
        if isinstance(cfg, dict):
            states.update(s for s in cfg.get("states") or [] if isinstance(s, str))
    return states


class _Context:
    """Active process + profile-derived rules for one hook invocation."""

    def __init__(self, profile_path):
        self.profile = _load_profile(profile_path)
        p = self.profile or {}
        self.role = p.get("role", "")
        self.process = p.get("process", "")
        self.enforcement = p.get("enforcement", "ask")
        self.preset, _ = _load_preset(self.process)
        base = self.preset or {}
        self.role_rules = self._pick(p.get("roleRules"), base.get("roleRules"))
        self.task_naming = self._pick(p.get("taskNaming"), base.get("taskNaming"))

    @staticmethod
    def _pick(override, preset_value):
        if override is False:
            return {}
        if isinstance(override, dict):
            return override
        return preset_value if isinstance(preset_value, dict) else {}

    @property
    def label(self):
        return f"process preset '{self.process}'" if self.preset else "generic rules"


def _user_role(lines):
    """Role from the profile: YAML `role:` line first, else the Markdown table row."""
    for line in lines:
        if line.startswith("role:"):
            role = line[len("role:"):].strip().replace('"', "")
            if role:
                return role
            break
    for line in lines:
        if "primary role" in line.lower():
            role = re.sub(r".*\|\s*\*\*Primary Role\*\*\s*\|\s*", "", line)
            return re.sub(r"\s*\|.*", "", role).strip()
    return ""


# Role labels people actually write in a profile, mapped to the canonical
# lower-case role ids used by data/state_machine.json.
_ROLE_ALIASES = {
    "project manager": "pm",
    "product manager": "pm",
    "team lead": "lead",
    "tech lead": "lead",
    "technical lead": "lead",
}


def _normalize_role(role):
    """Case-insensitive canonical role id ("PM" -> "pm", "Tech Lead" -> "lead")."""
    norm = " ".join(str(role or "").strip().strip("'\"").lower().split())
    return _ROLE_ALIASES.get(norm, norm)


# An @mention is "@" + letter NOT preceded by a word char or dot, so the "@" inside
# an e-mail address (jane.doe@example.com) is not mistaken for a mention.
_MENTION_RE = re.compile(r"(?<![\w.])@[A-Za-z]")


def _comment_text(tool_input):
    """The comment body from tool_input.comment; falls back to the whole tool_input."""
    comment = tool_input.get("comment")
    return comment if isinstance(comment, str) else json.dumps(tool_input, ensure_ascii=False)


def _advise(text):
    hooklib.context("PreToolUse", text)


def _ask(reason, context=""):
    out = {"hookEventName": "PreToolUse",
           "permissionDecision": "ask",
           "permissionDecisionReason": reason}
    if context:
        out["additionalContext"] = context
    print(json.dumps({"hookSpecificOutput": out}, ensure_ascii=False))


def _decide(ctx, violations, unknown, reminder):
    """Route policy violations / unknown-state findings by the enforcement setting.

    violations: org-policy findings (role / naming rules) -> ask | block | advise.
    unknown:    data-gap findings (state not in the preset) -> always ask.
    """
    if violations and ctx.enforcement == "block":
        _block("[DevOps] BLOCKED: " + " ".join(violations)
               + " (profile enforcement: block; see data/state_machine.json processPresets.)")
    asks = list(unknown) + (violations if ctx.enforcement == "ask" else [])
    notes = violations if ctx.enforcement == "advise" else []
    context = " ".join([reminder] + [f"[DevOps] Policy note: {v}" for v in notes]).strip()
    if asks:
        _ask("[DevOps] Confirm: " + " ".join(asks), context)
    elif context:
        _advise(context)


def _roles(values):
    return {_normalize_role(r) for r in values or [] if isinstance(r, str)}


def _block(text):
    print(text, file=sys.stderr)
    sys.exit(2)


def _target_state(tool_input):
    """Value of the update whose JSON-Patch path is System.State, or "".

    wit_update_work_item sends updates=[{op, path: "/fields/System.State", value}].
    The bash hook grepped for a quoted "System.State" token and then took the
    first "value" in the payload, so it never matched the real path and would
    have read the wrong value whenever another field was updated first.
    """
    updates = tool_input.get("updates") or []
    if not isinstance(updates, list):
        return ""
    for upd in updates:
        if not isinstance(upd, dict):
            continue
        path = str(upd.get("path") or "").strip().lower()
        if path.rstrip("/").endswith("system.state"):
            value = upd.get("value")
            return value.strip() if isinstance(value, str) else ""
    return ""


def _update_work_item(tool_input, ctx):
    target_state = _target_state(tool_input)
    if not target_state:
        return

    reminder = (
        f"[DevOps] State change to '{target_state}' detected ({ctx.label}). Follow "
        "data/state_machine.json pre-flight for the active process preset: check the "
        "transition, required fields, and confirm via rules/write-gate.md."
    )
    violations, unknown = [], []

    # Data gap: the active preset does not define this state (custom process?).
    if ctx.preset is not None and target_state not in _preset_states(ctx.preset):
        unknown.append(
            f"State '{target_state}' is not defined in {ctx.label}. The project may use a "
            "customized process - confirm the state is valid, or re-run /init profile to "
            "re-detect the process."
        )

    # Policy: restricted states, only when the preset/profile defines roleRules.
    rule = (ctx.role_rules.get("restrictedStates") or {}).get(target_state)
    if isinstance(rule, dict) and ctx.role:
        allowed = _roles(rule.get("allowedRoles"))
        if allowed and _normalize_role(ctx.role) not in allowed:
            violations.append(
                f"Role '{ctx.role}' moving a work item to '{target_state}' - "
                f"{rule.get('rule') or 'restricted to ' + ', '.join(sorted(allowed))} "
                f"({ctx.label} roleRules)."
            )

    _decide(ctx, violations, unknown, reminder)


def _create_title(tool_input):
    """System.Title from wit_create_work_item tool_input.fields, or ""."""
    fields = tool_input.get("fields")
    if isinstance(fields, dict):
        value = fields.get("System.Title") or fields.get("Title")
        return value.strip() if isinstance(value, str) else ""
    for item in fields if isinstance(fields, list) else []:
        if isinstance(item, dict) and str(item.get("name", "")).lower() in (
                "system.title", "title"):
            value = item.get("value")
            return value.strip() if isinstance(value, str) else ""
    return ""


def _prefixes(naming):
    out = []
    for p in naming.get("prefixes") or []:
        value = p.get("prefix") if isinstance(p, dict) else p
        if isinstance(value, str) and value.strip():
            out.append(value.strip())
    return out


def _create_work_item(tool_input, ctx):
    wi_type = _str_field(tool_input, "workItemType")
    violations = []

    # Policy: create restrictions, only when the preset/profile defines roleRules.
    rule = (ctx.role_rules.get("createRestrictions") or {}).get(wi_type)
    if isinstance(rule, dict) and ctx.role:
        role = _normalize_role(ctx.role)
        denied, allowed = _roles(rule.get("deniedRoles")), _roles(rule.get("allowedRoles"))
        if role in denied or (allowed and role not in allowed):
            violations.append(
                f"Role '{ctx.role}' creating a {wi_type} - "
                f"{rule.get('rule') or 'restricted'}. {rule.get('redirect') or ''}".strip()
                + f" ({ctx.label} roleRules)."
            )

    # Policy: title prefixes, only when the preset/profile defines taskNaming.
    applies = ctx.task_naming.get("appliesTo") or ["Task"]
    prefixes = _prefixes(ctx.task_naming)
    title = _create_title(tool_input)
    if prefixes and wi_type in applies and title and not any(
            title.startswith(p) for p in prefixes):
        violations.append(
            f"{wi_type} title '{title}' does not start with a required prefix "
            f"({', '.join(prefixes)}) ({ctx.label} taskNaming)."
        )

    if wi_type in ("Task", "Bug", "Enhancement"):
        parent = "User Story/PBI/Requirement/Issue"
    elif wi_type in ("User Story", "Product Backlog Item", "Requirement"):
        parent = "Feature"
    elif wi_type == "Feature":
        parent = "Epic"
    else:
        parent = ""
    reminder = (
        f"[DevOps] Creating {wi_type} - ensure parent {parent} is linked per "
        "data/hierarchy_rules.json." if parent else ""
    )
    _decide(ctx, violations, [], reminder)


def _add_comment(tool_input):
    # HARD BLOCK: unresolved @mentions. Only the comment body is inspected, and an
    # e-mail address is not a mention. This is a correctness guard (a plain "@name"
    # notifies nobody), so there is no override: resolve the mention and retry.
    text = _comment_text(tool_input)
    if _MENTION_RE.search(text) and "data-vss-mention" not in text:
        _block(
            "[DevOps] BLOCKED: Unresolved @mentions detected. Resolve to GUIDs and use HTML "
            "format before posting. See rules/guards.md Guard 2."
        )


def _create_pull_request(tool_input):
    repo_id = _str_field(tool_input, "repositoryId")
    if repo_id and not _GUID_RE.match(repo_id):
        _advise(
            f"[DevOps] repositoryId '{repo_id}' is not a GUID. Resolve per "
            "rules/guards.md Guard 3."
        )


def main():
    hooklib.watchdog(8.0)  # fail open: a hang must not freeze every ADO write
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    # Namespace-agnostic: plugin tools are "mcp__plugin_devops_azure-devops__<tool>",
    # legacy ones "mcp__azure-devops__<tool>". Keep only the bare tool segment.
    tool = str(payload.get("tool_name") or "").rsplit("azure-devops__", 1)[-1]
    tool_input = hooklib.tool_input(payload)
    if tool == "wit_update_work_item":
        _update_work_item(tool_input, _Context(_profile_path()))
    elif tool == "wit_create_work_item":
        _create_work_item(tool_input, _Context(_profile_path()))
    elif tool == "wit_add_work_item_comment":
        _add_comment(tool_input)
    elif tool == "repo_create_pull_request":
        _create_pull_request(tool_input)
    return 0


if __name__ == "__main__":
    hooklib.run(main)
