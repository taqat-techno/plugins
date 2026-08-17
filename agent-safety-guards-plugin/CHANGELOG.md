# Changelog

All notable changes to the `agent-safety-guards` plugin are documented here.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

Fixed `user_invocable` -> `user-invocable` on 6 skills. The underscore form is not in Claude Code's skill frontmatter allowlist, so every one of those declarations was silently inert and the skills stayed user-invocable against their authored intent. Values preserved exactly.

## [Unreleased]

### Added

- `skills/structural-assertions` (+ `references/ast-probes.md`) — claims about the SHAPE of
  source go through the language's parser, never string containment; the `ast.walk`
  breadth-first ordering trap; the side-by-side old-file/new-file wiring probe; the negative
  universal over multi-exit functions; sweep-the-class; and reading a red pre-existing
  structural test as evidence about the design.
- `skills/test-result-evidence` — the epistemics of a test RESULT: the named discriminator,
  proving which artifact a control run imported (editable-install `sys.path` pinning), reading
  a collection-time `ImportError` as zero-tests-ran, comparing collected counts across
  versions, cleanup assertions on a closed resource rather than a deletable path, and the
  one-OS-flake reading.
- `skills/test-double-seams` — the two-sided contract at a test-double seam: the per-branch
  ledger enumerated from the production entry point, the "which side of this seam did the test
  call?" question, the seam-shape catalog, and the production-side rules (`getattr` for
  optional reads, no diagnostic with veto power over a startup path, no feature that requires
  existing doubles to grow methods).

### Changed

- `skills/agent-safety` (0.2.0) — added the consume side of the structured-output contract,
  the don't-route-around-a-permission-denial rule, refute-a-green-verdict-before-it-mutates,
  the production-data hard stops, and the reversibility test for autonomous shipping.
- `skills/workflow-reliability` (0.2.0) — added completion-gated aggregation (a crashed
  producer's zero is unverified, not clean), stale per-run artifact discard, the
  killed-subagent unknown-state rule, shared-runtime/concurrent-session standdown, and the
  recon-subagent prompt contract.

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
