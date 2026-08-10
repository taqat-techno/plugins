#!/usr/bin/env python3
"""Citation-path repair for ragtools search results (rag-plugin, WP-3).

The defect this exists for
--------------------------
ragtools builds a chunk's stored ``file_path`` as ``"{project_id}/{rel}"``
(``indexing/scanner.py::get_project_relative_path``). Its text formatter then
prefixes ``project_id/`` **again** (``retrieval/formatter.py::_loc``), so every
citation in default (non-structured) output repeats its first segment::

    stored     rag/docs/decisions.md          <- resolves
    rendered   rag/rag/docs/decisions.md      <- does not exist

Structured mode (``search_knowledge_base(..., structured=True)``) returns the
stored path and is unaffected — which is what proves the defect is in rendering,
not in storage. **Prefer structured output; this module is the fallback for the
text surfaces.**

Tracked upstream as A-02. When it ships, this module becomes a no-op rather than
wrong: a corrected path has no duplicate to strip, so :func:`normalize` is
idempotent by construction.

Why the guard is this narrow
----------------------------
Stripping "a repeated leading segment" in general would corrupt real paths. A
project genuinely containing ``docs/docs/`` is not a formatting artefact. So the
strip fires only when the first TWO segments are both exactly the project id,
happens exactly ONCE, and is always followed by an existence check.

The once-only rule is also what keeps framework citations correct. A framework
corpus stores ``odoo/odoo/addons/...`` (corpus id + a real ``odoo`` directory),
which the formatter renders as ``odoo/odoo/odoo/addons/...``. One strip yields
the true stored path; a recursive strip would eat a real directory.

Usage
-----
    from citation_path import normalize

    c = normalize("rag/rag/docs/decisions.md", project_id="rag",
                  project_root=r"/path/to/rag")
    c.stored     -> "rag/docs/decisions.md"
    c.absolute   -> "/path/to/rag/docs/decisions.md"
    c.exists     -> True
    c.trusted    -> True     # safe to cite
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

__all__ = ["Citation", "normalize", "to_native"]


@dataclass(frozen=True)
class Citation:
    """The outcome of repairing one cited path.

    ``trusted`` is the only field a caller should gate presentation on. It is
    False when the path could not be confirmed to exist, which is the honest
    answer — inventing a repair is worse than saying the citation is unusable.
    """

    raw: str
    stored: str
    absolute: Optional[str]
    stripped: bool
    exists: Optional[bool]
    reason: str

    @property
    def trusted(self) -> bool:
        return self.exists is True

    def describe(self) -> str:
        if self.trusted:
            note = " (duplicated project segment removed)" if self.stripped else ""
            return f"{self.stored}{note}"
        if self.exists is False:
            return (
                f"{self.stored} — could not be verified on disk "
                f"({self.reason}); cite the project + heading instead"
            )
        return f"{self.stored} — not verified ({self.reason})"


def _split(path: str) -> list[str]:
    """Split a cited path into segments, tolerating either separator.

    ragtools always stores POSIX separators (``Path.as_posix()``), but a path
    that has been round-tripped through a Windows shell or a copy-paste may
    arrive with backslashes.
    """
    return [s for s in path.replace("\\", "/").split("/") if s]


def normalize(
    cited: str,
    project_id: str,
    project_root: Optional[str] = None,
) -> Citation:
    """Repair one cited path and, when possible, verify it.

    Args:
        cited: the path exactly as it appeared in the tool output.
        project_id: the project the search was scoped to. The strip is keyed on
            this, so a path from a different project is never touched.
        project_root: the project's absolute root (``path`` from
            ``/api/projects/configured``). Without it the path cannot be
            verified and ``exists`` stays ``None``.

    Returns:
        A :class:`Citation`. Never raises — a bad input yields an untrusted
        result with a reason, because a citation helper that throws inside an
        answer is worse than one that says "unverified".
    """
    raw = (cited or "").strip()
    if not raw:
        return Citation(raw, "", None, False, None, "empty path")

    # Drop a "path:L12-30" provenance suffix if one came along.
    line_suffix = ""
    if ":L" in raw:
        raw_path, _, line_suffix = raw.partition(":L")
        line_suffix = ":L" + line_suffix
    else:
        raw_path = raw

    segments = _split(raw_path)
    if not segments:
        return Citation(raw, "", None, False, None, "no path segments")

    stripped = False
    pid = (project_id or "").strip()
    if pid and len(segments) >= 2 and segments[0] == pid and segments[1] == pid:
        # Exactly once. Never a loop: see the module docstring on odoo/odoo/.
        segments = segments[1:]
        stripped = True

    stored = "/".join(segments)

    if not project_root:
        return Citation(raw, stored + line_suffix, None, stripped, None,
                        "no project root supplied")

    # The stored form is "{project_id}/{rel-from-project-root}". Drop that
    # leading id to get a path relative to the project's own directory.
    rel_segments = segments[1:] if (pid and segments and segments[0] == pid) else segments
    if not rel_segments:
        return Citation(raw, stored + line_suffix, None, stripped, False,
                        "path resolved to the project root itself")

    try:
        absolute = Path(project_root).expanduser().joinpath(*rel_segments)
        exists = absolute.is_file()
        return Citation(
            raw,
            stored + line_suffix,
            absolute.as_posix(),
            stripped,
            exists,
            "" if exists else "file not found at the resolved location",
        )
    except (OSError, ValueError) as exc:
        return Citation(raw, stored + line_suffix, None, stripped, False,
                        f"could not resolve: {exc}")


def to_native(posix_path: str) -> str:
    """Convert a POSIX-separated path to this platform's separators.

    Only at the boundary where the path is handed to a file-reading tool.
    Comparison and storage stay POSIX everywhere else, so the same logic
    behaves identically on all three platforms.
    """
    if not posix_path:
        return posix_path
    return posix_path.replace("/", os.sep) if os.sep != "/" else posix_path


if __name__ == "__main__":  # pragma: no cover - manual smoke aid
    import sys

    if len(sys.argv) < 3:
        print("usage: citation_path.py <cited-path> <project-id> [project-root]")
        raise SystemExit(2)
    root = sys.argv[3] if len(sys.argv) > 3 else None
    print(normalize(sys.argv[1], sys.argv[2], root))
