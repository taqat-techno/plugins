# notification - architecture decisions

Binding rules for this plugin. Each entry states the rule, what would violate it,
and the only evidence that would justify reversing it. Anything that contradicts
an entry here is a regression, not a refactor.

Background investigation: `.claude/docs/2026-08-21_notification-plugin-investigation.md`.

---

## D-001 — Every hook is `async: true`

**Rule.** Every hook this plugin registers sets `"async": true`. No exceptions.

**Why.** Three of the five subscribed events are *blocking* events, and exit code
2 on them is destructive:

| Event | Effect of exit 2 |
|---|---|
| `PreToolUse` (`AskUserQuestion`) | Blocks the tool call — Claude's question is silently suppressed |
| `Stop` | Prevents Claude from stopping; the turn continues, overridden only after 8 consecutive blocks |
| `TaskCompleted` | The task is not marked completed |

Claude Code documents that async hooks "can't block or control Claude's
behavior." That converts a *convention* the script must uphold into a *structural
property* the harness enforces, and it holds even if the script is completely
broken.

**Violation looks like.** A hook entry without `async`; `asyncRewake: true`
(which wakes Claude on exit 2 — the opposite of what is wanted); any code path
that returns a `decision`, `permissionDecision` or `continue` field.

**Check.** `tests/test_notification.py::HooksManifest::test_every_hook_is_async`.

**Reverse only if.** Claude Code documents that async hooks are unavailable for
these events, or a notification channel is adopted that requires a synchronous
return value (see D-009). Reversing this requires replacing the guarantee, not
dropping it.

---

## D-002 — The notifier writes nothing to stdout in hook mode

**Rule.** In hook mode `notify.py` produces no stdout output on any path,
including success. Only `--doctor` and `--write-config` print.

**Why.** Claude Code parses hook stdout as JSON when the first non-whitespace
character is `{`. Before v2.1.202, malformed JSON from an *async* hook could
crash the session — and the crash recurred every time the session was resumed.
Emitting nothing is the only shape that is safe on every version, and it removes
any possibility of a mistyped output field.

**Violation looks like.** A stray `print()` on the hook path; a debug statement
left behind; returning a JSON decision object.

**Check.** `HookIsolation::test_exits_zero_and_silent_for_every_category`.

**Reverse only if.** The plugin adopts `terminalSequence` (D-009), which requires
JSON output — and then only for hooks converted to synchronous.

---

## D-003 — No shell, ever

**Rule.** `hooks.json` uses exec form (`command` + `args`). Every backend runs
through `subprocess.run(argv, shell=False)`. On Windows the notification text
travels in environment variables, never on a command line.

**Why.** Notification text is untrusted: it comes from question text, task
subjects, API error strings and tool arguments, and routinely contains quotes,
newlines, `$`, backticks and `&`. Exec form also removes two portability traps —
Windows shell form silently selects Git Bash *or* PowerShell depending on what is
installed, and a plugin root containing a space breaks unquoted shell form.

**Violation looks like.** A `hooks.json` entry without `args`; string
interpolation of payload text into a command; `shell=True`; building AppleScript
source by concatenating notification text (AppleScript has no escape for a
literal newline, which is exactly how these scripts break in the wild).

**Check.** `HooksManifest::test_every_hook_uses_exec_form`,
`TextSafety::test_shell_metacharacters_survive_as_literal_text`.

**Reverse only if.** Never. There is no benefit that justifies putting untrusted
text through a shell.

---

## D-004 — No `SessionStart` hook

**Rule.** The plugin registers zero `SessionStart` hooks and does no start-up
work.

**Why.** Backend detection costs about 2 ms inline (`platform.system()`, a few
environment reads, one `shutil.which`), so caching it at session start buys
nothing measurable. This repository's own `HOOK_STABILIZATION_REPORT.md` ranks
heavy `SessionStart` hooks as the number one session-breaking cause. Installing
an observability plugin must be incapable of slowing or disturbing session
startup.

**Violation looks like.** Adding `SessionStart` to warm a cache, write a session
marker, or probe capability.

**Check.** `HooksManifest::test_no_sessionstart_hook`.

**Reverse only if.** A feature genuinely requires per-session setup — the most
likely candidate is hard-crash detection (D-010) — and profiling shows the cost
is under a few milliseconds.

---

## D-005 — Persistent state lives only under `${CLAUDE_PLUGIN_DATA}`

**Rule.** Nothing is written under `${CLAUDE_PLUGIN_ROOT}`. The only file the
plugin ever writes is `${CLAUDE_PLUGIN_DATA}/config.json`, and only when the user
asks for it via `/notification:doctor --write-config`.

**Why.** `${CLAUDE_PLUGIN_ROOT}` is version-pinned and replaced on every plugin
update; anything written there is lost. `${CLAUDE_PLUGIN_DATA}` resolves to
`~/.claude/plugins/data/{id}/`, survives updates, and is removed when the plugin
is uninstalled. This is marketplace house rule HR-17, and
`validate_marketplace.py` greps for violations.

**Violation looks like.** Writing a log, cache, state file or session marker next
to the scripts.

**Check.** `Configuration::test_config_never_lands_under_the_plugin_root`;
`python validate_marketplace.py`.

**Reverse only if.** Never.

---

## D-006 — No model on any runtime path

**Rule.** No prompt hooks, agent hooks, skills, agents, MCP servers, or
transcript reads. Every character of every notification is a field the payload
already contained.

**Why.** The plugin is an observability layer, not part of Claude's
decision-making. Runtime token cost must be exactly zero, behavior must be
identical on every run, and a notification must never depend on model
availability. `transcript_path` is additionally unreliable here — Claude Code
documents that the transcript file may lag and may not contain the current turn's
final message when a hook fires, which is why `Stop` carries
`last_assistant_message` directly.

**Violation looks like.** A `type: "prompt"` or `type: "agent"` hook; summarising
a long task subject with a model; opening `transcript_path`.

**Reverse only if.** Never for the notification path. `/notification:doctor` is
exempt: it is user-invoked, runs no hooks, and costs nothing during normal
operation.

---

## D-007 — Subagent and teammate events are not signals for the human

**Rule.** Any payload carrying `agent_id` is suppressed. `TaskCompleted` carrying
`teammate_name` is suppressed by default (`suppress_teammate_tasks`).

**Why.** `agent_id` and `agent_type` appear only when a hook fires inside a
subagent or an `--agent` session. A subagent finishing a unit of work is internal
progress; notifying on it turns a useful signal into noise proportional to the
fan-out width.

**Violation looks like.** Removing the `agent_id` filter to "catch more events".

**Check.** `Suppression::test_suppresses_subagent_events`,
`::test_suppresses_teammate_tasks_by_default`.

**Reverse only if.** A user wants per-teammate progress — already available by
setting `suppress_teammate_tasks: false`. The `agent_id` filter itself stays.

---

## D-008 — A turn with work still in flight is not finished

**Rule.** `Stop` is suppressed when `background_tasks` or `session_crons` is
non-empty, or when `stop_hook_active` is true.

**Why.** Claude Code populates these arrays so hooks can "distinguish 'session is
done' from 'session is paused waiting for background work to wake it back up'."
Notifying "Claude Finished" while a background agent is still running is simply
wrong, and it is the kind of small inaccuracy that makes users stop trusting a
notifier. `stop_hook_active` means another Stop hook is driving the continuation,
so the turn is not ending either.

**Violation looks like.** Notifying on every `Stop` unconditionally.

**Check.** `Suppression::test_suppresses_turn_with_background_work`.

**Reverse only if.** Claude Code stops populating these arrays, in which case the
suppression becomes a no-op on its own.

---

## D-009 — `terminalSequence` is deliberately not used in v1

**Rule.** The plugin does not emit `terminalSequence`.

**Why.** It is genuinely attractive — Claude Code writes an allowlisted escape
sequence (OSC 9 / 99 / 777) through its own terminal write path, race-free, works
in tmux, works on Windows, needs no dependency at all. But async hooks deliver
only `additionalContext` and `systemMessage`, so using it would require making
every hook synchronous and abandoning D-001 and D-002. It also offers no
persistence or urgency control, and the most common Linux terminals (GNOME
Terminal, Konsole) and the VS Code integrated terminal do not implement these
sequences.

**Reverse only if.** It is offered as an explicitly opt-in *additional* channel,
implemented as separate synchronous hook entries, with the blocking risk
documented — never by converting the existing hooks.

---

## D-010 — Hard-crash detection is out of scope

**Rule.** The plugin does not attempt to detect Claude Code terminating
abnormally.

**Why.** A hook is a child of the process it would report on. `SessionEnd` fires
only on graceful termination and shares a 1.5-second budget across all
`SessionEnd` hooks; a SIGKILL, OOM kill or closed terminal runs nothing. The two
possible designs both fail on their own terms: an external watchdog costs a
long-lived process per session and false-fires on clean exits whenever the
`SessionEnd` marker write is truncated (contradicting D-004), and a launcher shim
cannot be installed by a marketplace plugin at all and would break `claude` on
self-update, in IDE extensions, and in Claude Desktop.

A notifier that cries wolf is worse than one that stays quiet. `StopFailure`
already covers the whole API-error family, which accounts for the large majority
of "the session died on me" experiences.

**Reverse only if.** Claude Code gains a supported out-of-process death signal,
or the watchdog can be proven not to false-fire across all four `SessionEnd`
reasons.

---

## D-011 — WSL is detected, not treated as Linux

**Rule.** WSL is detected explicitly and resolves to `unsupported`.

**Why.** WSL2 with WSLg exposes a display, so a naive Linux check passes — but
there is usually no notification daemon, so `notify-send` fails or silently
no-ops. That is the worst outcome, because it looks like it worked. Explicit
detection turns a silent lie into a documented skip that `/notification:doctor`
can explain.

**Violation looks like.** Removing `is_wsl()` because "WSLg has a display now".

**Reverse only if.** A `wsl_host` backend is added that reaches the Windows host
through interop. `backends.detect()` already returns a named key for exactly this
extension.
