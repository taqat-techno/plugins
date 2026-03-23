"""
Shared utilities for odoo-i18n scripts.

Provides unified PoEntry, PoParser, escape functions, plural forms,
and configurable branding constants used across all i18n tools.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Configurable branding (override via environment variables)
# ---------------------------------------------------------------------------

PO_COPYRIGHT_HOLDER = os.environ.get("ODOO_I18N_COPYRIGHT", "ORGANIZATION")
PO_BUGS_ADDRESS = os.environ.get("ODOO_I18N_BUGS_EMAIL", "")


# ---------------------------------------------------------------------------
# Plural forms table (expanded)
# ---------------------------------------------------------------------------

PLURAL_FORMS: Dict[str, str] = {
    # Arabic (all variants) — 6 forms
    "ar": "nplurals=6; plural=n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5;",
    "ar_SA": "nplurals=6; plural=n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5;",
    "ar_AE": "nplurals=6; plural=n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5;",
    "ar_EG": "nplurals=6; plural=n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5;",
    # English
    "en": "nplurals=2; plural=(n != 1);",
    "en_US": "nplurals=2; plural=(n != 1);",
    "en_GB": "nplurals=2; plural=(n != 1);",
    # French
    "fr": "nplurals=2; plural=(n > 1);",
    "fr_FR": "nplurals=2; plural=(n > 1);",
    "fr_BE": "nplurals=2; plural=(n > 1);",
    "fr_CA": "nplurals=2; plural=(n > 1);",
    # German
    "de": "nplurals=2; plural=(n != 1);",
    "de_DE": "nplurals=2; plural=(n != 1);",
    # Spanish
    "es": "nplurals=2; plural=(n != 1);",
    "es_ES": "nplurals=2; plural=(n != 1);",
    "es_MX": "nplurals=2; plural=(n != 1);",
    # Portuguese
    "pt": "nplurals=2; plural=(n > 1);",
    "pt_BR": "nplurals=2; plural=(n > 1);",
    "pt_PT": "nplurals=2; plural=(n != 1);",
    # Italian
    "it": "nplurals=2; plural=(n != 1);",
    # Dutch
    "nl": "nplurals=2; plural=(n != 1);",
    # Turkish
    "tr": "nplurals=2; plural=(n != 1);",
    # Russian
    "ru": "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);",
    # Ukrainian
    "uk": "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);",
    # Polish
    "pl": "nplurals=3; plural=(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);",
    # Czech
    "cs": "nplurals=3; plural=(n==1 ? 0 : (n>=2 && n<=4) ? 1 : 2);",
    # Romanian
    "ro": "nplurals=3; plural=(n==1 ? 0 : (n==0 || (n%100>0 && n%100<20)) ? 1 : 2);",
    # Chinese (all variants) — 1 form
    "zh": "nplurals=1; plural=0;",
    "zh_CN": "nplurals=1; plural=0;",
    "zh_TW": "nplurals=1; plural=0;",
    # Japanese
    "ja": "nplurals=1; plural=0;",
    # Korean
    "ko": "nplurals=1; plural=0;",
    # Indonesian / Malay
    "id": "nplurals=1; plural=0;",
    "ms": "nplurals=1; plural=0;",
    # Hindi
    "hi": "nplurals=2; plural=(n != 1);",
    # Persian / Farsi
    "fa": "nplurals=2; plural=(n > 1);",
    # Hebrew
    "he": "nplurals=2; plural=(n != 1);",
    # Urdu
    "ur": "nplurals=2; plural=(n != 1);",
    # Thai
    "th": "nplurals=1; plural=0;",
    # Vietnamese
    "vi": "nplurals=1; plural=0;",
}

DEFAULT_PLURAL_FORMS = "nplurals=2; plural=(n != 1);"


# ---------------------------------------------------------------------------
# Escape / unescape for .po format
# ---------------------------------------------------------------------------

def escape_po_string(s: str) -> str:
    """Escape special characters for .po file format."""
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    s = s.replace("\t", "\\t")
    return s


def unescape_po_string(s: str) -> str:
    """Unescape a .po file string back to its original form."""
    s = s.replace('\\"', '"')
    s = s.replace("\\n", "\n")
    s = s.replace("\\t", "\t")
    s = s.replace("\\r", "\r")
    s = s.replace("\\\\", "\\")
    return s


# ---------------------------------------------------------------------------
# PoEntry — unified data structure
# ---------------------------------------------------------------------------

@dataclass
class PoEntry:
    """A single .po file entry (msgid/msgstr pair with metadata)."""
    msgid: str = ""
    msgstr: str = ""
    comments: List[str] = field(default_factory=list)
    extracted_comments: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    is_fuzzy: bool = False
    is_obsolete: bool = False
    is_header: bool = False
    line_start: int = 0

    @property
    def is_translated(self) -> bool:
        return bool(self.msgstr) and not self.is_fuzzy

    def clone_empty(self) -> "PoEntry":
        """Return a copy with empty msgstr (for merge operations)."""
        return PoEntry(
            msgid=self.msgid,
            msgstr="",
            comments=list(self.comments),
            extracted_comments=list(self.extracted_comments),
            locations=list(self.locations),
            flags=[f for f in self.flags if f != "fuzzy"],
            is_fuzzy=False,
            is_obsolete=self.is_obsolete,
            is_header=self.is_header,
        )


# ---------------------------------------------------------------------------
# PoParser — unified parser
# ---------------------------------------------------------------------------

class PoParser:
    """
    Line-by-line .po file parser.

    Args:
        content: The .po file text content.
        strict: If True, malformed strings raise ValueError and are
                recorded in parse_errors. If False, they return empty
                string silently. Use strict=True for validation,
                strict=False for merge/convert/reporting.
    """

    def __init__(self, content: str, strict: bool = False):
        self.lines = content.splitlines()
        self.entries: List[PoEntry] = []
        self.parse_errors: List[Tuple[int, str]] = []
        self.strict = strict

    def parse(self) -> List[PoEntry]:
        entries: List[PoEntry] = []
        current: Optional[PoEntry] = None
        mode: Optional[str] = None
        i = 0

        while i < len(self.lines):
            lineno = i + 1
            raw_line = self.lines[i]
            line = raw_line.strip()

            # Empty line — finalize current entry
            if not line:
                if current is not None and (current.msgid or current.is_header):
                    if not current.msgid:
                        current.is_header = True
                    entries.append(current)
                    current = None
                    mode = None
                i += 1
                continue

            # Comment / flag lines
            if line.startswith("#"):
                if current is None:
                    current = PoEntry(line_start=lineno)

                if line.startswith("#,"):
                    flags_str = line[2:].strip()
                    current.flags = [f.strip() for f in flags_str.split(",")]
                    if "fuzzy" in current.flags:
                        current.is_fuzzy = True
                elif line.startswith("#:"):
                    locs = line[2:].strip()
                    current.locations.extend(locs.split())
                elif line.startswith("#."):
                    current.extracted_comments.append(line[2:].strip())
                elif line.startswith("#~"):
                    current.is_obsolete = True
                    current.comments.append(line)
                else:
                    current.comments.append(line)
                i += 1
                continue

            # msgid
            if line.startswith("msgid "):
                if current is not None and mode is not None:
                    # Flush previous if a new msgid starts without blank line
                    if current.msgid or current.is_header:
                        entries.append(current)
                if current is None:
                    current = PoEntry(line_start=lineno)
                mode = "msgid"
                val = self._parse_string(line[6:], lineno)
                if val is not None:
                    current.msgid = val
                    if val == "":
                        current.is_header = True
                i += 1
                continue

            # msgstr
            if line.startswith("msgstr "):
                mode = "msgstr"
                val = self._parse_string(line[7:], lineno)
                if val is not None and current is not None:
                    current.msgstr = val
                i += 1
                continue

            # Continuation string (starts with ")
            if line.startswith('"') and mode in ("msgid", "msgstr") and current is not None:
                val = self._parse_string(line, lineno)
                if val is not None:
                    if mode == "msgid":
                        current.msgid += val
                        if current.msgid == "":
                            current.is_header = True
                    else:
                        current.msgstr += val
                i += 1
                continue

            # Unknown line
            if self.strict:
                self.parse_errors.append((lineno, f"Unexpected content: {raw_line!r}"))
            i += 1

        # Finalize last entry
        if current is not None and (current.msgid or current.is_header):
            if not current.msgid:
                current.is_header = True
            entries.append(current)

        self.entries = entries
        return entries

    def _parse_string(self, raw: str, lineno: int) -> Optional[str]:
        """Parse a quoted string from a .po line."""
        raw = raw.strip()
        if not raw.startswith('"') or not raw.endswith('"'):
            if self.strict:
                msg = f"Malformed string at line {lineno}: {raw!r}"
                self.parse_errors.append((lineno, msg))
            return "" if not self.strict else None
        inner = raw[1:-1]
        return unescape_po_string(inner)
