#!/usr/bin/env python3
"""rag-plugin resilient hook launcher — fail-open by construction (D-031).

This launcher fixes a *prompt/tool-blocking* design vulnerability in the bundled
hooks (see RAG_PLUGIN_HOOK_INVESTIGATION_REPORT.md and docs/decisions.md#d-031).

The problem (proven, present since v0.3.0)
------------------------------------------
A hook ``command`` of the form ``python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<x>.py``
exits with code **2** whenever Python cannot open the script file — i.e. when
the host fails to expand ``${CLAUDE_PLUGIN_ROOT}`` (reported on Cowork / headless
Windows), the variable is unset, or the script is missing. Per the Claude Code
hook spec, exit **2** is the (only) *blocking* code: on ``UserPromptSubmit`` it
cancels the prompt before the model request; on ``PreToolUse`` it blocks the tool
call. The target scripts already ``sys.exit(0)`` on every internal error, but
that fail-safe **cannot run if the script file never loads** — the failure is one
layer *above* the script, at the command-invocation layer.

The fix
-------
Move the resolution-failure guarantee above the target script. ``hooks.json`` no
longer names a script file on the interpreter command line; it runs a tiny inline
``-c`` bootstrap. Because ``-c`` takes no script-file argument, the
"can't open file -> exit 2" branch is structurally impossible. The bootstrap
resolves THIS launcher at runtime (``CLAUDE_PLUGIN_ROOT`` env var, with a
host-expanded path fallback) and runs it only if it exists; otherwise it exits 0.
The command also chains interpreters (``python3 || python || py``) so the hook
still runs where ``python3`` is not the interpreter name — and because the only
blocking code is exactly 2, a missing interpreter (127) or a stray parse error is
non-blocking by spec.

This launcher then resolves the real target script *beside its own* ``__file__``
(needs no env var of its own) and runs it in-process via ``runpy`` so the
target's stdin (the hook payload) and stdout (its ``additionalContext`` /
``permissionDecision`` JSON) pass through unchanged.

Two modes (per target)
----------------------
* **advisory** — injectors/reminders (``UserPromptSubmit``). They must never be
  able to influence control flow, so EVERY exit is normalized to ``0``.
* **guarded** — hooks that may legitimately influence their tool call (the
  ``PreToolUse`` lock-conflict ``permissionDecision: "ask"`` gate). Their own
  exit code is **passed through** (so an intentional decision survives), but a
  *path-resolution* failure (script missing / launcher not found) or an
  *unexpected exception* still fails open to ``0`` — a hook that cannot even be
  located, or that crashes internally, must never falsely block a tool call.

In both modes a resolution failure yields ``0``; the difference is only what
happens once the target actually runs.

Python 3 stdlib only. Cross-platform: this launcher contains no shell-specific
constructs, and the inline bootstrap that invokes it uses no shell metacharacters
inside its payload.
"""

import os
import sys

# Logical target name -> (sibling script filename, mode). Add hooks here.
#   "advisory": normalize every exit to 0 (cannot block — injectors/reminders).
#   "guarded":  pass the target's own exit code through (an intentional
#               decision survives), but fail open on path-resolution failure and
#               on unexpected exceptions.
_TARGETS = {
    "retrieval-reminder": ("prompt_retrieval_reminder.py", "advisory"),
    "project-focus": ("project_focus_inject.py", "advisory"),
    "lock-conflict": ("lock_conflict_check.py", "guarded"),
}


def _diag(msg: str) -> None:
    """Best-effort one-line diagnostic to stderr, gated on RAG_PLUGIN_HOOK_DEBUG.

    Never raises. Never writes to stdout (reserved for the target's hook JSON).
    Never includes the prompt, payload, or any user content — only control-flow
    metadata (target name, resolution outcome)."""
    if not os.environ.get("RAG_PLUGIN_HOOK_DEBUG"):
        return
    try:
        sys.stderr.write("[rag-plugin hook_launcher] " + str(msg) + "\n")
    except Exception:
        pass


def _resolve_target():
    """Return (target_path, mode). target_path is None when the target cannot be
    located (unknown name / missing file) — the caller fails open in that case."""
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    entry = _TARGETS.get(name)
    if not entry:
        _diag("unknown or missing target name: " + repr(name))
        return None, "advisory"
    filename, mode = entry
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, filename)
    if not os.path.isfile(target):
        _diag("target script not found: " + target)
        return None, mode
    return target, mode


def main() -> int:
    """Run the resolved target and return an exit code that can never falsely
    block. Path-resolution failures fail open in BOTH modes; once the target
    runs, advisory normalizes to 0 while guarded passes the target's code through.
    """
    target, mode = _resolve_target()
    if target is None:
        # Could not even locate the target (unresolved root / missing file /
        # unknown name). Fail open in BOTH modes — a hook that cannot be located
        # must never block a prompt or a tool call.
        return 0
    try:
        import runpy

        # run_name="__main__" so the target's `if __name__ == "__main__"` block
        # fires and runpy sets the target's __file__ correctly (its own
        # __file__-relative logic keeps working). stdin/stdout pass through.
        runpy.run_path(target, run_name="__main__")
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 0
        if mode == "guarded":
            # Preserve the target's intentional exit code (e.g. a deliberate
            # block). A guarded hook is allowed to influence its tool call.
            return code
        # advisory: a target that ever exited non-zero (even 2) must not block.
        if code != 0:
            _diag("advisory target exited %r; normalizing to 0" % (code,))
        return 0
    except BaseException as exc:  # noqa: BLE001 — intentional catch-all
        # Unexpected error in EITHER mode -> fail open. The targets catch their
        # own known errors; this backstops the unexpected so an internal hook
        # bug never blocks the prompt or the tool call.
        _diag("target raised %s; failing open" % type(exc).__name__)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
