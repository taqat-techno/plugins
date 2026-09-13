# notification - architecture decisions

Binding rules for this plugin. Each entry states the rule, what would violate it,
and the only evidence that would justify reversing it. Anything that contradicts
an entry here is a regression, not a refactor.

Background investigation: `.claude/docs/2026-08-21_notification-plugin-investigation.md`.

---

## D-001 — Every hook is `async: true`

**Rule.** Every hook this plugin registers sets `"async": true`. No exceptions.

**Why.** Five of the seven subscribed events are *blocking* events, and exit code
2 on them is destructive:

| Event | Effect of exit 2 |
|---|---|
| `PreToolUse` (`AskUserQuestion`) | Blocks the tool call — Claude's question is silently suppressed |
| `PostToolUse` (`AskUserQuestion`) | Feeds stderr back to Claude as if the answer had failed |
| `UserPromptSubmit` | Blocks the prompt and erases it from the input |
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

**Rule.** Nothing is written under `${CLAUDE_PLUGIN_ROOT}`. The plugin writes
exactly two things, both under `${CLAUDE_PLUGIN_DATA}`: `config.json`, only when
the user asks for it via `/notification:doctor --write-config`, and the
short-lived question markers in `state/` (D-013). The Windows app identity in
HKCU (D-014) is a registry registration, not plugin state.

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

## D-012 — No eval suite: there is no routing surface to measure

**Rule.** This plugin ships no `skills/` and no `agents/`, so it ships no `evals/`
suite. HR-20's eval path does not apply, and this entry is the recorded N/A.

**Why.** `claude plugin eval` measures `Δ` — the score of a run with the plugin
loaded minus the score of the same run with nothing loaded — on prompts a user
would type. Every capability this plugin has is a hook that fires on a *harness
event*, never on a prompt. There is no routing decision for the plugin to win, so
no case could produce a non-zero `Δ`: a suite here would report `Δ = 0` on every
case and document nothing. Worse, it would not even be inert — an eval run loads a
plugin's hooks and executes them as the user, outside the agent's sandbox, so
evaluating this plugin fires real desktop notifications as a side effect of
measuring nothing.

**Violation looks like.** An `evals/` directory added here to satisfy a checklist,
containing cases whose `Δ` is structurally 0; or broadening HR-20 so that
hooks-only and commands-only plugins are required to carry suites.

**Check.** `ls notification-plugin/skills notification-plugin/agents` — neither
exists. Behavioural coverage for this plugin lives in `tests/test_notification.py`,
which exercises the hook manifest and the notifier directly, where the behaviour
actually is.

**Reverse only if.** The plugin gains a skill or an agent — any component a user
prompt can route to. At that point the eval path applies (one must-fire case, one
must-not-fire case, released on a recorded `Δ > 0`) and this entry is superseded.

---

---

## D-013 — One question, one notification

**Rule.** A question that has been notified suppresses the `permission_prompt`
notification it raises. The bridge is a per-session marker file,
`${CLAUDE_PLUGIN_DATA}/state/question-<session_id>`: written by the `question`
verb just before sending, read by the `permission` verb, deleted by `answered`
(`PostToolUse` on `AskUserQuestion`), `prompted` (`UserPromptSubmit`), `turn` and
`failure`, and ignored once it is older than 120 seconds. Markers older than a day are swept on every write.

**Why.** Claude Code presents `AskUserQuestion` through its permission-prompt
path. Captured live on 2026-09-13, the second event raised by a single question
was:

    {"hook_event_name": "Notification", "notification_type": "permission_prompt",
     "message": "Claude needs your permission", ...}

It names no tool, so no payload-only rule can tell it apart from a genuine
permission prompt, and the user saw two notifications for one question. The
question notification is the one to keep: it arrives immediately instead of
after the idle delay, and it carries the question text.

**Failure direction.** Every failure fails toward notifying. An unwritable data
directory means no marker, so the permission notification appears — a duplicate,
never a lost alert. A question suppressed by config or by D-007 writes no marker,
so the permission prompt remains the fallback alert. A question dismissed with Esc
fires no `PostToolUse`, but the user's next prompt clears it; only a genuine
permission prompt arriving before that prompt, inside the 120-second window, can
be lost.

**Violation looks like.** Suppressing `permission` by matching its message text;
writing the marker when no question notification was built; clearing the marker
from a subagent's `PostToolUse`; removing the time window.

**Check.** `tests/test_notification.py::QuestionDeduplication`, which uses the
captured payload.

**Reverse only if.** Claude Code stops raising `permission_prompt` for
`AskUserQuestion`, or starts naming the tool in the Notification payload. Then
replace the marker with a payload rule and delete `state.py`.

---

## D-014 — Windows toasts use a per-user "Claude Code" app identity

**Rule.** `win_toast.ps1` shows toasts under the AppUserModelID
`TaqaTechno.ClaudeCode.Notifications`, registered idempotently under
`HKCU\Software\Classes\AppUserModelId\` with `DisplayName` "Claude Code",
`ShowInSettings` 1, and `IconUri` pointing at `hooks/icon.png` - written before the
first toast, because Windows caches an app's header icon the first time it sees
the app. The icon appears in the header only, not inside the toast. If
registration fails, the toast falls back to Windows PowerShell's identity and is
still shown.

**Why.** Under PowerShell's identity every toast was headed "Windows PowerShell"
with the PowerShell icon, was grouped with unrelated PowerShell notifications, and
could only be muted together with them. A registry-registered AUMID needs no
Start Menu shortcut and no admin rights, gets its own switch in Settings >
Notifications, and lets the plugin withdraw its own stale toasts from
Notification Center.

**Cost.** One registry key under HKCU that uninstalling the plugin does not
remove; it is inert without the plugin. `IconUri` is re-pointed on each run, so
an upgrade that moves the install directory heals itself.

**Violation looks like.** Writing under HKLM; creating a Start Menu shortcut;
failing the toast because registration failed.

**Check.** `WindowsBackend::test_toast_script_parses`; `/notification:doctor`.

**Reverse only if.** Windows stops honouring registry-registered AUMIDs for
unpackaged applications.

---

## D-015 — Waiting-for-you notifications stay until closed

**Rule.** `question`, `permission`, `failure` and `turn` stay on screen until the
user closes them (config `persistent`, per category); `task` stays transient.
Notifications never replace each other — every toast has its own tag — and the
plugin withdraws them only in response to the user: an answered question
(`PostToolUse`), and every waiting toast of the session when the user sends the
next prompt (`UserPromptSubmit`). A new notification never removes an older one.

**Why.** Each of these means Claude has stopped and is waiting for the person. A
banner that disappears after a few seconds is missed exactly when the user has
stepped away — the only time the plugin is useful. Withdrawal is what keeps
persistence from turning into clutter: a toast still on screen after the user
has already replied in the terminal would be wrong.

**Platform cost.** Windows keeps a toast on screen only with the `reminder`
scenario, which it silently ignores unless the toast shows a button with a
background action, so persistent toasts carry a Close button. The same action
placed only in the toast's … menu (`placement="contextMenu"`) was tested live on
Windows 11 on 2026-09-13, side by side with the button version, and does not keep
the toast on screen. Linux uses critical urgency. macOS has
no programmatic persistence; the Alerts style is a user setting.

**Violation looks like.** Making `task` persistent by default; persisting without
the withdrawal hooks; keeping `scenario="reminder"` but removing its visible
button or moving it to the context menu (the toast then silently stops
persisting); a new notification replacing or withdrawing an older one.

**Check.** `Configuration::test_waiting_categories_persist_and_tasks_do_not`,
`WindowsBackend::test_persistence_brings_a_visible_close_button`, `NeverReplace`.

**Reverse only if.** Windows gains a way to keep a toast on screen without a
visible button — then drop the button, keep the rule.
