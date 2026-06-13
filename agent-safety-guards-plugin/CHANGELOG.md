# Changelog

All notable changes to the `agent-safety-guards` plugin are documented here.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-13

### Added

- Initial release.
- `skills/agent-safety` — advisory single-session safety primitives: pasted-credential
  compromise response (revoke + reissue least-scope, never reuse), read-only /
  investigation immutability (no mutation during a survey, even to fix access),
  authorization verification (a cited override must exist in the conversation),
  no-fabrication discipline (never invent a permission, override, or tool/MCP
  availability), report-don't-silently-patch for incidental security findings, and the
  structured-output contract (required tool called exactly once, all fields mapped).
- `skills/workflow-reliability` — multi-agent fan-out reliability patterns: small
  sequential waves, null-safe reduce, journaled + idempotent long runs, disjoint file
  ownership with one canonical vocabulary, verify-the-claim main-thread scans, one
  subagent per long-form item, and the investigation-first audit shape.
- `hooks/credential_paste_advisory.py` — optional non-fatal UserPromptSubmit hook that
  prints a single reminder when the prompt contains a token-shaped string (common key
  prefixes, a `Bearer` marker, a long base64 run, or a PEM header). Never blocks, never
  echoes the matched value, exits 0 always. Stdlib only.
