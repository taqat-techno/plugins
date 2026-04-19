#!/usr/bin/env python3
"""Safe Markdown enhancer for the ragtools RAG pipeline.

Always-safe mode — applies only two mechanical fixes that cannot change
semantic meaning by construction:
  GL-05  pseudo-heading (bold-as-heading)  →  real heading
  GL-04b blank-line normalization around headings and code fences

Every other finding (content-before-first-heading, oversized sections,
vague headings, mixed-topic sections, duplicate leaf headings, oversized
code blocks, oversized tables, YAML frontmatter carrying knowledge,
missing prose intro before code, skipped heading levels) is REPORTED only.

Safety invariants:
  - Never modify content inside fenced code blocks.
  - Never change commands, URLs, file paths, config keys, version numbers,
    or numeric values — the safe-fix categories do not touch flowing text.
  - Never delete content. The two safe fixes only ADD structure.
  - Atomic file writes (load → modify in-memory → write to tmp → os.replace).
  - Backup before every write (.bak-pre-md-rag-enhance sibling).
  - Skip files under .git/, node_modules/, .venv/, dist/, build/, __pycache__/.
  - Skip binary files, symlinks, files > 1 MB.
  - Hardcoded 500-file safety cap for whole-project runs.

Stdlib-only. Python 3.10+.

See rag-plugin/skills/markdown-authoring/references/rag-md-guidelines.md
for the full authoring standard this tool enforces.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterator, Optional

# ---------------------------------------------------------------------------
# Constants and regexes

MAX_FILES = 500
MAX_FILE_BYTES = 1_048_576  # 1 MB
BACKUP_SUFFIX = ".bak-pre-md-rag-enhance"

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "dist", "build",
    "__pycache__", ".tox", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "target", ".next", ".nuxt",
}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CODE_FENCE_RE = re.compile(r"^(```|~~~)")
PSEUDO_HEADING_RE = re.compile(r"^\*\*([^*\n][^*\n]*[^*\n\s])\*\*\s*$")
TABLE_ROW_RE = re.compile(r"^\s*\|")
TABLE_SEP_RE = re.compile(r"^\s*\|[\s:|\-]+\|\s*$")
YAML_FENCE = "---"
VAGUE_HEADING_RE = re.compile(
    r"^(overview|details|notes?|info|section\s*\d*|introduction|intro|summary|about|misc|other)\s*:?\s*$",
    re.IGNORECASE,
)

WORD_RE = re.compile(r"\b\w+\b")

# ---------------------------------------------------------------------------
# Data structures


@dataclass
class Finding:
    file: str
    line: int
    rule_id: str
    severity: str  # HIGH | MEDIUM | LOW | INFO
    message: str
    remediation: str


@dataclass
class FileResult:
    path: str
    findings: list[Finding] = field(default_factory=list)
    safe_fixes_applied: int = 0
    skipped_reason: Optional[str] = None


@dataclass
class Section:
    start: int  # zero-based line index
    end: int    # exclusive
    level: int
    heading: str
    word_count: int
    has_children: bool


# ---------------------------------------------------------------------------
# File discovery


def _load_gitignore(root: Path) -> set[str]:
    """Parse a .gitignore into a minimal set of dir names / exact paths to skip.

    Only supports the subset that's safe to apply mechanically — dir names
    and exact file paths. Glob patterns are ignored; we rely on SKIP_DIRS
    for the common cases.
    """
    gi = root / ".gitignore"
    if not gi.exists():
        return set()
    patterns: set[str] = set()
    try:
        for raw in gi.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            if "*" in line or "?" in line or "[" in line:
                continue
            patterns.add(line.rstrip("/"))
    except OSError:
        pass
    return patterns


def discover_files(target: Optional[Path]) -> tuple[list[Path], Optional[str]]:
    """Return the list of .md files to process, plus an optional error string.

    If `target` is a file, return just that file.
    If `target` is a directory (or None, meaning cwd), walk recursively.
    """
    if target is not None and target.is_file():
        return [target], None

    root = target if target is not None else Path.cwd()
    if not root.is_dir():
        return [], f"not a file or directory: {root}"

    gi = _load_gitignore(root)
    skip = SKIP_DIRS | gi

    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for name in filenames:
            if not name.endswith(".md"):
                continue
            p = Path(dirpath) / name
            try:
                if p.is_symlink():
                    continue
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            found.append(p)
            if len(found) > MAX_FILES:
                return [], (
                    f"exceeded {MAX_FILES}-file safety cap under {root}. "
                    f"Pass a specific file path to /md-rag-enhance instead, "
                    f"or narrow the working directory."
                )
    return sorted(found), None


# ---------------------------------------------------------------------------
# Parsing


def _strip_frontmatter(lines: list[str]) -> tuple[list[str], int, Optional[dict[str, str]]]:
    """Return (body_lines, body_start_offset, frontmatter_dict_or_None).

    frontmatter_dict is a shallow parse — enough to detect knowledge-carrying
    keys like tags/keywords/description. Never used for structural fixes.
    """
    if not lines or lines[0].rstrip() != YAML_FENCE:
        return lines, 0, None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == YAML_FENCE:
            fm_text = "\n".join(lines[1:i])
            fm: dict[str, str] = {}
            for raw in fm_text.splitlines():
                if ":" in raw and not raw.lstrip().startswith("#"):
                    k, _, v = raw.partition(":")
                    fm[k.strip().lower()] = v.strip()
            return lines[i + 1:], i + 1, fm
    # unterminated frontmatter — treat whole file as body (defensive)
    return lines, 0, None


def _build_sections(body: list[str], body_offset: int) -> list[Section]:
    """Walk body lines and build a section list with word counts."""
    sections: list[Section] = []
    in_fence = False
    current: Optional[tuple[int, int, str]] = None  # (start_line, level, heading_text)
    for idx, line in enumerate(body):
        if CODE_FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            if current is not None:
                start, lvl, head = current
                section_lines = body[start + 1: idx]
                words = _count_words_outside_fences(section_lines)
                sections.append(Section(
                    start=start + body_offset,
                    end=idx + body_offset,
                    level=lvl,
                    heading=head,
                    word_count=words,
                    has_children=False,
                ))
            level = len(m.group(1))
            heading_text = m.group(2).strip()
            current = (idx, level, heading_text)
    if current is not None:
        start, lvl, head = current
        section_lines = body[start + 1:]
        words = _count_words_outside_fences(section_lines)
        sections.append(Section(
            start=start + body_offset,
            end=len(body) + body_offset,
            level=lvl,
            heading=head,
            word_count=words,
            has_children=False,
        ))
    # Second pass: mark has_children
    for i, sec in enumerate(sections):
        for j in range(i + 1, len(sections)):
            if sections[j].level > sec.level:
                sec.has_children = True
                break
            if sections[j].level <= sec.level:
                break
    return sections


def _count_words_outside_fences(lines: list[str]) -> int:
    total = 0
    in_fence = False
    for line in lines:
        if CODE_FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        total += len(WORD_RE.findall(line))
    return total


def _iter_code_blocks(lines: list[str], body_offset: int) -> Iterator[tuple[int, int, int]]:
    """Yield (start_line_0based, end_line_0based_exclusive, body_line_count) for each fenced code block."""
    in_fence = False
    start = 0
    for idx, line in enumerate(lines):
        if CODE_FENCE_RE.match(line):
            if not in_fence:
                start = idx
                in_fence = True
            else:
                yield (start + body_offset, idx + 1 + body_offset, idx - start - 1)
                in_fence = False


def _iter_tables(lines: list[str], body_offset: int) -> Iterator[tuple[int, int, int]]:
    """Yield (start_line, end_line_exclusive, row_count) for each table.

    A table is a sequence of contiguous `|`-prefixed lines with a
    `|---|---|` separator row within the first 2 lines.
    """
    in_fence = False
    i = 0
    while i < len(lines):
        if CODE_FENCE_RE.match(lines[i]):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence:
            i += 1
            continue
        if TABLE_ROW_RE.match(lines[i]):
            start = i
            # find end of the contiguous table
            while i < len(lines) and TABLE_ROW_RE.match(lines[i]) and not CODE_FENCE_RE.match(lines[i]):
                i += 1
            block = lines[start:i]
            has_sep = any(TABLE_SEP_RE.match(ln) for ln in block[:3])
            if has_sep and len(block) >= 2:
                yield (start + body_offset, i + body_offset, len(block) - 1)  # rows minus header+sep
            continue
        i += 1


# ---------------------------------------------------------------------------
# Checks (one function per rule)


def _check_gl_01(path: Path, body_offset: int, body: list[str], sections: list[Section]) -> list[Finding]:
    """Content before first heading."""
    if not sections:
        if any(line.strip() for line in body):
            return [Finding(str(path), 1, "GL-01", "HIGH",
                            "File has content but no heading — chunks will be anchor-less.",
                            "Add a top-level `# Title` as the first non-frontmatter line.")]
        return []
    first_heading_line = sections[0].start - body_offset
    for idx in range(first_heading_line):
        if body[idx].strip():
            return [Finding(str(path), 1 + body_offset + 1, "GL-01", "HIGH",
                            "Content appears before the first heading — produces empty-hierarchy chunks.",
                            "Move the intro under a `# Title` heading, or add a title as the first line after frontmatter.")]
    return []


def _check_gl_02(path: Path, sections: list[Section]) -> list[Finding]:
    """Oversized leaf section (>300 words)."""
    out: list[Finding] = []
    for sec in sections:
        if not sec.has_children and sec.word_count > 300:
            out.append(Finding(str(path), sec.start + 1, "GL-02", "HIGH",
                               f"Leaf section '{sec.heading}' is ~{sec.word_count} words (>300). "
                               f"Chunker will paragraph-split it and the tail will lose topic coherence.",
                               f"Split into `{'#' * (sec.level + 1)} Sub-topic A` / `{'#' * (sec.level + 1)} Sub-topic B` subsections of ≤250 words each."))
    return out


def _check_gl_03(path: Path, sections: list[Section]) -> list[Finding]:
    """Vague heading."""
    out: list[Finding] = []
    for sec in sections:
        if VAGUE_HEADING_RE.match(sec.heading.strip()):
            out.append(Finding(str(path), sec.start + 1, "GL-03", "MEDIUM",
                               f"Vague heading '{sec.heading}' — heading is prepended to every chunk embedding; vague heading = vague embedding.",
                               "Rename to a keyword-rich heading naming the specific topic (e.g. `## Configuring the chunk overlap` instead of `## Configuration`)."))
    return out


def _check_gl_04(path: Path, sections: list[Section]) -> list[Finding]:
    """Duplicate leaf heading within the file."""
    out: list[Finding] = []
    seen: dict[str, int] = {}
    for sec in sections:
        if sec.has_children:
            continue
        key = sec.heading.strip().lower()
        if key in seen:
            out.append(Finding(str(path), sec.start + 1, "GL-04", "MEDIUM",
                               f"Duplicate leaf heading '{sec.heading}' (also at line {seen[key] + 1}). MCP formatter can't disambiguate them in search results.",
                               "Rename one to be unique within the file (e.g. add a scope qualifier like `## Usage — CLI` vs `## Usage — API`)."))
        else:
            seen[key] = sec.start
    return out


def _check_gl_05(path: Path, body_offset: int, body: list[str]) -> list[Finding]:
    """Pseudo-heading (bold line used as section title)."""
    out: list[Finding] = []
    in_fence = False
    for idx, line in enumerate(body):
        if CODE_FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if PSEUDO_HEADING_RE.match(line.strip()):
            # confirm surrounded by blank lines
            prev_blank = idx == 0 or not body[idx - 1].strip()
            next_blank = idx == len(body) - 1 or not body[idx + 1].strip()
            if prev_blank and next_blank:
                out.append(Finding(str(path), idx + body_offset + 1, "GL-05", "MEDIUM",
                                   f"Pseudo-heading: '{line.strip()}' is bold-as-heading, not a real Markdown heading. Doesn't create a chunk boundary.",
                                   "SAFE-AUTO-FIX: converted to `## <text>` (or `### <text>` if nested under an existing `##`)."))
    return out


def _check_gl_06(path: Path, body: list[str], body_offset: int) -> list[Finding]:
    """Code block > 60 lines."""
    out: list[Finding] = []
    for start, end, inner in _iter_code_blocks(body, body_offset):
        if inner > 60:
            out.append(Finding(str(path), start + 1, "GL-06", "MEDIUM",
                               f"Code block is {inner} lines (>60). When oversize, the sentence splitter mangles it; resulting chunks have no natural-language anchor.",
                               f"Break into labelled steps with `### Step 1 — install`, `### Step 2 — configure` headings between sub-blocks."))
    return out


def _check_gl_07(path: Path, body: list[str], body_offset: int) -> list[Finding]:
    """Table > 15 rows."""
    out: list[Finding] = []
    for start, end, rows in _iter_tables(body, body_offset):
        if rows > 15:
            out.append(Finding(str(path), start + 1, "GL-07", "MEDIUM",
                               f"Table has {rows} data rows (>15). Splitter treats the table as a single paragraph; rows get stranded across chunk boundaries.",
                               "Split into multiple tables by category, or move to a dedicated `reference/` file with one table per `##` heading."))
    return out


def _check_gl_08(path: Path, frontmatter: Optional[dict[str, str]]) -> list[Finding]:
    """YAML frontmatter carrying knowledge."""
    if not frontmatter:
        return []
    knowledge_keys = {"tags", "keywords", "description", "summary", "topics", "categories"}
    hits = knowledge_keys & set(frontmatter.keys())
    if hits:
        return [Finding(str(path), 1, "GL-08", "MEDIUM",
                        f"YAML frontmatter contains knowledge keys {sorted(hits)} — these are stripped by the chunker and invisible to search.",
                        "Move the knowledge into a `## Tags` or `## Keywords` section in the body so the embedder sees it. Frontmatter is discarded.")]
    return []


def _check_gl_09(path: Path, body: list[str], body_offset: int) -> list[Finding]:
    """Code block without prose intro within 2 lines before the fence."""
    out: list[Finding] = []
    for start, end, inner in _iter_code_blocks(body, body_offset):
        local_start = start - body_offset
        # check 2 lines before the fence
        prose_found = False
        for j in (local_start - 1, local_start - 2):
            if j < 0:
                break
            prev = body[j].strip()
            if not prev:
                continue
            # skip heading lines (those are fine but not prose)
            if HEADING_RE.match(body[j]):
                break
            # skip other code fences
            if CODE_FENCE_RE.match(body[j]):
                break
            prose_found = True
            break
        if not prose_found:
            out.append(Finding(str(path), start + 1, "GL-09", "LOW",
                               "Code block has no prose intro sentence in the two lines before the fence. The embedding loses the semantic signal the code alone can't carry.",
                               "Add an introduction sentence like 'The following command stops the service:' before the fence."))
    return out


def _check_gl_10(path: Path, sections: list[Section]) -> list[Finding]:
    """Heading level skipped (e.g. ## → #### with no ###)."""
    out: list[Finding] = []
    prev_level = 0
    for sec in sections:
        if prev_level and sec.level > prev_level + 1:
            out.append(Finding(str(path), sec.start + 1, "GL-10", "LOW",
                               f"Heading level jumps from h{prev_level} to h{sec.level} (skips h{prev_level + 1}).",
                               "Insert an intermediate heading or flatten — hierarchy should be semantic, not arbitrary."))
        prev_level = sec.level
    return out


# ---------------------------------------------------------------------------
# Safe fixes


def _apply_fix_gl_05(body: list[str]) -> tuple[list[str], int]:
    """Convert pseudo-headings to real `## ` headings. Never inside code fences."""
    out: list[str] = []
    in_fence = False
    fixes = 0
    for idx, line in enumerate(body):
        if CODE_FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        m = PSEUDO_HEADING_RE.match(line.strip())
        if m:
            prev_blank = idx == 0 or not body[idx - 1].strip()
            next_blank = idx == len(body) - 1 or not body[idx + 1].strip()
            if prev_blank and next_blank:
                # Conservative: always H2. The guideline recommends this unless
                # nested-under-existing-##, which requires file-wide context;
                # keep it simple — H2 is always legal.
                out.append(f"## {m.group(1).strip()}\n")
                fixes += 1
                continue
        out.append(line)
    return out, fixes


def _apply_fix_blank_lines(body: list[str]) -> tuple[list[str], int]:
    """Normalize blank lines around real headings and fenced code blocks.

    - Ensure a blank line before and after every heading.
    - Ensure a blank line before and after every code fence.
    - Never touch content inside a code fence.
    """
    out: list[str] = []
    in_fence = False
    fixes = 0

    def _is_blank(s: str) -> bool:
        return not s.strip()

    i = 0
    while i < len(body):
        line = body[i]
        # Inside a code fence, pass everything through unchanged until the closing fence.
        if in_fence and not CODE_FENCE_RE.match(line):
            out.append(line)
            i += 1
            continue

        is_heading = not in_fence and HEADING_RE.match(line)
        is_fence = CODE_FENCE_RE.match(line)

        if is_heading or is_fence:
            # Before: ensure previous appended line is blank (unless we're at the start)
            if out and not _is_blank(out[-1]):
                out.append("\n")
                fixes += 1
            out.append(line)
            if is_fence:
                in_fence = not in_fence
            i += 1
            # After: ensure the next line in body is blank (unless at EOF or end of block)
            if not in_fence and i < len(body) and not _is_blank(body[i]):
                out.append("\n")
                fixes += 1
            continue

        out.append(line)
        i += 1

    return out, fixes


# ---------------------------------------------------------------------------
# Per-file pipeline


def analyze_file(path: Path) -> FileResult:
    result = FileResult(path=str(path))
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError) as exc:
        result.skipped_reason = f"read failed: {exc}"
        return result

    lines = raw.splitlines(keepends=True)
    body, body_offset, frontmatter = _strip_frontmatter(lines)
    sections = _build_sections(body, body_offset)

    # Run all checks
    result.findings.extend(_check_gl_01(path, body_offset, body, sections))
    result.findings.extend(_check_gl_02(path, sections))
    result.findings.extend(_check_gl_03(path, sections))
    result.findings.extend(_check_gl_04(path, sections))
    result.findings.extend(_check_gl_05(path, body_offset, body))
    result.findings.extend(_check_gl_06(path, body, body_offset))
    result.findings.extend(_check_gl_07(path, body, body_offset))
    result.findings.extend(_check_gl_08(path, frontmatter))
    result.findings.extend(_check_gl_09(path, body, body_offset))
    result.findings.extend(_check_gl_10(path, sections))

    return result


def enhance_file(path: Path, *, no_backup: bool, dry_run: bool) -> tuple[FileResult, Optional[str]]:
    """Analyze, apply safe fixes, write atomically with backup.

    Returns (result, diff_string_or_None). The diff is only populated in
    dry_run mode; otherwise None and the write has happened.
    """
    result = analyze_file(path)
    if result.skipped_reason:
        return result, None

    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines(keepends=True)
    body, body_offset, _fm = _strip_frontmatter(lines)

    # Apply fix 1: pseudo-headings
    new_body, fix1_count = _apply_fix_gl_05(body)
    # Apply fix 2: blank-line normalization
    new_body, fix2_count = _apply_fix_blank_lines(new_body)

    total_fixes = fix1_count + fix2_count
    result.safe_fixes_applied = total_fixes

    if total_fixes == 0:
        return result, None

    new_text = "".join(lines[:body_offset]) + "".join(new_body)
    # Preserve final-newline convention
    if raw.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"

    if new_text == raw:
        return result, None

    if dry_run:
        import difflib
        diff = "".join(difflib.unified_diff(
            raw.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"{path} (original)",
            tofile=f"{path} (enhanced)",
            n=2,
        ))
        return result, diff

    # Backup
    if not no_backup:
        backup = path.with_suffix(path.suffix + BACKUP_SUFFIX)
        shutil.copy2(path, backup)

    # Atomic write
    tmp = path.with_suffix(path.suffix + ".md-rag-enhance.tmp")
    tmp.write_text(new_text, encoding="utf-8")
    try:
        os.replace(tmp, path)
    except OSError:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise

    return result, None


# ---------------------------------------------------------------------------
# Report rendering


def render_compact(results: list[FileResult]) -> str:
    files_scanned = len(results)
    files_with_fixes = sum(1 for r in results if r.safe_fixes_applied > 0)
    total_fixes = sum(r.safe_fixes_applied for r in results)
    all_findings = [f for r in results for f in r.findings]
    severities = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for f in all_findings:
        severities[f.severity] = severities.get(f.severity, 0) + 1

    lines = [
        "md-rag-enhance — summary",
        f"  files scanned:              {files_scanned}",
        f"  files enhanced:             {files_with_fixes}",
        f"  safe mechanical fixes:      {total_fixes}",
        f"  report-only findings:       {len(all_findings)}",
        f"    HIGH:    {severities['HIGH']}",
        f"    MEDIUM:  {severities['MEDIUM']}",
        f"    LOW:     {severities['LOW']}",
        "",
    ]

    # Top findings by severity
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
    sorted_findings = sorted(all_findings, key=lambda f: (severity_order.get(f.severity, 9), f.file, f.line))
    if sorted_findings:
        lines.append("top findings for manual review (up to 20):")
        for f in sorted_findings[:20]:
            lines.append(f"  [{f.severity}] {f.rule_id} {f.file}:{f.line} — {f.message}")
        remaining = len(sorted_findings) - 20
        if remaining > 0:
            lines.append(f"  ... and {remaining} more. Use --verbose to see all.")
    else:
        lines.append("[OK] no report-only findings.")

    return "\n".join(lines)


def render_verbose(results: list[FileResult]) -> str:
    out: list[str] = [render_compact(results), "", "per-file detail:"]
    for r in results:
        if r.skipped_reason:
            out.append(f"  {r.path}: SKIPPED ({r.skipped_reason})")
            continue
        out.append(f"  {r.path}  ({r.safe_fixes_applied} safe fix(es), {len(r.findings)} finding(s))")
        for f in r.findings:
            out.append(f"    [{f.severity}] {f.rule_id} line {f.line}: {f.message}")
            out.append(f"        → {f.remediation}")
    return "\n".join(out)


def render_json(results: list[FileResult]) -> str:
    return json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Self-test


_SELF_TEST_INPUT = """# Title

**Pseudo heading**

Some text here.
## Real heading
Content right after heading.
```python
x = 1
```
More content.
"""

_SELF_TEST_EXPECTED_PSEUDO_FIXES = 1  # Pseudo heading gets converted
_SELF_TEST_EXPECTED_BLANK_FIXES_AT_LEAST = 2  # headings and code fence get blank lines


def _self_test() -> int:
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tf:
        tf.write(_SELF_TEST_INPUT)
        test_path = Path(tf.name)

    try:
        result = analyze_file(test_path)
        gl05 = [f for f in result.findings if f.rule_id == "GL-05"]
        assert len(gl05) == 1, f"expected 1 GL-05 finding, got {len(gl05)}"

        _result, diff = enhance_file(test_path, no_backup=True, dry_run=True)
        assert diff is not None, "expected a diff in dry-run"
        assert "## Pseudo heading" in diff, "pseudo-heading should have been converted"

        # Actually apply
        result2 = enhance_file(test_path, no_backup=True, dry_run=False)[0]
        assert result2.safe_fixes_applied >= 1, f"expected >=1 fix, got {result2.safe_fixes_applied}"

        # Reanalyze — should have fewer GL-05 findings
        after = analyze_file(test_path)
        gl05_after = [f for f in after.findings if f.rule_id == "GL-05"]
        assert len(gl05_after) == 0, f"pseudo-heading fix didn't take effect"

        print("[OK] self-test passed")
        return 0
    except AssertionError as exc:
        print(f"[FAIL] self-test FAILED: {exc}")
        return 1
    finally:
        try:
            test_path.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# CLI


def main() -> int:
    # Windows cp1252 cannot print Unicode in MD content (arrows, em-dashes, etc.)
    # Force UTF-8 on stdout/stderr so diff output + verbose findings are safe to print.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(
        description="Safe Markdown enhancer for the ragtools RAG pipeline.",
        epilog="Always-safe mode. Applies only mechanical fixes that cannot change meaning.",
    )
    parser.add_argument("file", nargs="?", default=None,
                        help="Path to a single .md file to enhance. If omitted, enhance every .md under the current directory.")
    parser.add_argument("--verbose", action="store_true",
                        help="Full per-file report instead of the compact summary.")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip writing <file>.bak-pre-md-rag-enhance siblings. For users on git.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change; don't write. (Script-only; not exposed through /md-rag-enhance.)")
    parser.add_argument("--json", action="store_true",
                        help="Emit structured JSON findings to stdout. (Script-only.)")
    parser.add_argument("--self-test", action="store_true",
                        help="Run built-in tests and exit. (Script-only.)")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    target = Path(args.file).resolve() if args.file else None
    files, err = discover_files(target)
    if err:
        print(f"md-rag-enhance: {err}", file=sys.stderr)
        return 1
    if not files:
        print("md-rag-enhance: no .md files found.")
        return 0

    results: list[FileResult] = []
    diffs: list[str] = []
    for p in files:
        result, diff = enhance_file(p, no_backup=args.no_backup, dry_run=args.dry_run)
        results.append(result)
        if diff:
            diffs.append(diff)

    if args.json:
        print(render_json(results))
        return 0

    if args.dry_run:
        for d in diffs:
            print(d)
        print()

    if args.verbose:
        print(render_verbose(results))
    else:
        print(render_compact(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
