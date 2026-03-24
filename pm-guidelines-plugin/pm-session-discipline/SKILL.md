---
name: pm-session-discipline
description: |
  PM session workflow discipline — memory vs tasks distinction, lesson capture protocol, session log updates, and git-pull-before-analysis rituals. Use when managing session state, capturing lessons, or deciding what goes into memory vs todo lists.


  <example>
  Context: User asks to save something to memory
  user: "Remember this for next time"
  assistant: "I will use the pm-session-discipline skill to determine if this belongs in memory (future conversations) or tasks (current session), and save it to the right place."
  <commentary>Memory decision trigger - classify what goes where.</commentary>
  </example>

  <example>
  Context: Session is ending after significant work
  user: "We're done for today"
  assistant: "I will use the pm-session-discipline skill to capture session lessons, update the session log in MEMORY.md, and record any corrections or validated approaches."
  <commentary>Session end trigger - proactive lesson capture.</commentary>
  </example>

  <example>
  Context: User wants to analyze repo data
  user: "Analyze the latest deliverables in the repo"
  assistant: "I will use the pm-session-discipline skill to ensure we pull latest before analyzing, check git diff after pull, and record the session context."
  <commentary>Analysis start trigger - pull-before-analyze ritual.</commentary>
  </example>
license: "MIT"
metadata:
  version: "1.0.0"
  priority: 50
  filePattern:
    - "**/MEMORY.md"
    - "**/memory/**"
    - "**/lessons.md"
    - "**/tasks/todo.md"
  bashPattern:
    - "git pull"
    - "git diff"
  promptSignals:
    phrases:
      - "save lesson"
      - "remember this"
      - "session log"
      - "capture lessons"
      - "update memory"
      - "end of session"
      - "we're done"
      - "pull before"
    minScore: 6
---

# PM Session Discipline

## Rule 36: Save Lessons at End of Every Session

Don't wait for the user to ask. At the end of each working session, proactively:

1. **Identify corrections** — Did the user correct your approach? Save the pattern to prevent repeating.
2. **Identify validations** — Did a non-obvious approach work well? Save positive patterns too.
3. **Update project memory** — Record key decisions, team composition changes, estimation methodology used.
4. **Update global lessons** — If the lesson applies across projects, add to `researches/PM-guidelines.md`.

### What to Capture

| Capture | Example |
|---------|---------|
| Corrections | "User said: don't use abbreviations in board reports" |
| Validated approaches | "Single bundled PR was the right call for this refactor" |
| Key decisions | "v2 plan reduced from 9 months to 4 months" |
| Team context | "Backend team at 80% allocation through Q2" |

### What NOT to Capture

| Skip | Why |
|------|-----|
| Current debug state | Ephemeral — only useful right now |
| Temp file paths | Will change next session |
| Code patterns | Derivable from reading the code |
| Git history | Use `git log` / `git blame` |

## Rule 37: Memory is for Future Conversations

### Decision Matrix

| Information Type | Save To | Why |
|-----------------|---------|-----|
| Task breakdown for current work | `tasks/todo.md` (TodoWrite) | Only useful this session |
| Correction that applies to future work | Memory file | Prevents repeating mistakes |
| Project estimation methodology | Memory file | Context for future estimates |
| Current file being debugged | Nowhere (ephemeral) | Changes constantly |
| Team member allocation percentages | Memory file | Informs future planning |
| Build command that just worked | Nowhere (in CLAUDE.md already) | Documented elsewhere |

### The Test

Before saving to memory, ask: **"Will future-me need this to understand the project, or is this only useful right now?"**

- If only useful now → tasks/todo.md or don't save
- If useful in future → memory file with clear description

## Rule 38: Update Session Log After Every Pull

When working with repos that receive external updates:

### The Pull Ritual

```
1. git pull                          # Get latest
2. git diff --stat HEAD~1           # See what changed (files + line counts)
3. git log --oneline -5             # See recent commit messages
4. Record in session context:
   - Date: 2026-03-24
   - Commits pulled: abc1234..def5678
   - Files changed: proposal_v2.html (+45), backlog.xlsx (+12)
   - Key changes: "v2 reduced duration from 9 to 4 months"
```

### Why This Matters

- Commit messages like "design modifications" are vague
- `git diff --stat` tells you EXACTLY what changed and how much
- Without this, you risk analyzing stale data or missing important changes

## Pull-Before-Analysis Checklist

Before reading ANY data/analysis file from a git repo:

- [ ] `git pull` run this session
- [ ] `git diff --stat` reviewed to understand changes
- [ ] Session log updated with pull details
- [ ] Version files checked for internal consistency (v2 file shouldn't contain v1 data)
