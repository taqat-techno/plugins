"""A small YAML-subset reader for steps.yaml.

Uses PyYAML when it is installed. When it is not, falls back to a parser that
handles exactly the subset the step-script format uses: block mappings, block
sequences, flow mappings/sequences on one line, comments, and scalars.

The fallback exists so `collect`, `build` and `publish` never require a pip
install. Anything outside the subset raises YamlSubsetError telling the user to
install PyYAML rather than silently mis-parsing their script.
"""
from __future__ import annotations

import re

__all__ = ["load", "YamlSubsetError"]


class YamlSubsetError(ValueError):
    """Raised when the fallback parser meets syntax it will not guess at."""


def load(text: str):
    try:
        import yaml  # type: ignore
    except ImportError:
        return _load_subset(text)
    return yaml.safe_load(text)


# --------------------------------------------------------------------------- #
# fallback parser
# --------------------------------------------------------------------------- #
_KEY_RE = re.compile(r"^(?P<key>[^:\s][^:]*?)\s*:(?:\s+(?P<val>.*))?$")


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            out.append(ch)
            if ch == quote and line[i - 1 : i] != "\\":
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            out.append(ch)
            continue
        if ch == "#" and (i == 0 or line[i - 1].isspace()):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _tokenize(text: str) -> list[list]:
    lines = []
    for raw in text.splitlines():
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlSubsetError("tabs used for indentation; use spaces")
        content = _strip_comment(raw)
        if not content.strip():
            continue
        if content.lstrip().startswith("---"):
            continue
        indent = len(content) - len(content.lstrip())
        lines.append([indent, content.strip()])
    return lines


def _load_subset(text: str):
    lines = _tokenize(text)
    if not lines:
        return None
    value, idx = _parse_block(lines, 0, lines[0][0])
    if idx != len(lines):
        raise YamlSubsetError(
            f"could not parse line {idx + 1}: {lines[idx][1]!r}. "
            "Install PyYAML (pip install pyyaml) for full YAML support."
        )
    return value


def _parse_block(lines: list[list], idx: int, indent: int):
    content = lines[idx][1]
    if content == "-" or content.startswith("- "):
        return _parse_sequence(lines, idx, indent)
    # Flow collections must be tested before the key regex: "{ do: click }"
    # would otherwise read as a block mapping whose key is "{ do".
    if content[:1] in "{[":
        return _scalar(content), idx + 1
    if _KEY_RE.match(content):
        return _parse_mapping(lines, idx, indent)
    return _scalar(content), idx + 1


def _parse_mapping(lines: list[list], idx: int, indent: int):
    result = {}
    while idx < len(lines) and lines[idx][0] == indent:
        match = _KEY_RE.match(lines[idx][1])
        if not match:
            break
        key = _scalar(match.group("key").strip())
        raw_val = (match.group("val") or "").strip()
        if raw_val:
            result[key] = _scalar(raw_val)
            idx += 1
            continue
        # value lives in the block below
        if idx + 1 < len(lines) and lines[idx + 1][0] > indent:
            result[key], idx = _parse_block(lines, idx + 1, lines[idx + 1][0])
        elif idx + 1 < len(lines) and lines[idx + 1][1].startswith("- ") \
                and lines[idx + 1][0] == indent:
            # sequence written at the same indent as its key
            result[key], idx = _parse_sequence(lines, idx + 1, indent)
        else:
            result[key] = None
            idx += 1
    return result, idx


def _parse_sequence(lines: list[list], idx: int, indent: int):
    result = []
    while idx < len(lines) and lines[idx][0] == indent and (
        lines[idx][1] == "-" or lines[idx][1].startswith("- ")
    ):
        body = lines[idx][1][1:].lstrip()
        if not body:
            if idx + 1 < len(lines) and lines[idx + 1][0] > indent:
                value, idx = _parse_block(lines, idx + 1, lines[idx + 1][0])
                result.append(value)
                continue
            result.append(None)
            idx += 1
            continue
        # Re-point this line at the item's own column so a multi-key item
        # ("- id: s1" then "  caption: ...") parses as one mapping.
        col = indent + (len(lines[idx][1]) - len(body))
        lines[idx] = [col, body]
        value, idx = _parse_block(lines, idx, col)
        result.append(value)
    return result, idx


def _scalar(token: str):
    token = token.strip()
    if not token:
        return None
    if token[0] in "{[":
        value, rest = _parse_flow(token)
        if rest.strip():
            raise YamlSubsetError(f"trailing characters after flow value: {rest!r}")
        return value
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    low = token.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~"):
        return None
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return token


def _parse_flow(token: str):
    """Parse a flow collection. Returns (value, remainder)."""
    if token.startswith("{"):
        return _parse_flow_container(token, "}", dict)
    if token.startswith("["):
        return _parse_flow_container(token, "]", list)
    raise YamlSubsetError(f"not a flow collection: {token!r}")


def _parse_flow_container(token: str, closer: str, kind):
    rest = token[1:]
    items: list = []
    while True:
        rest = rest.lstrip()
        if not rest:
            raise YamlSubsetError(f"unterminated flow collection, expected {closer!r}")
        if rest[0] == closer:
            rest = rest[1:]
            break
        chunk, rest = _read_flow_item(rest, closer)
        if chunk.strip():
            items.append(chunk.strip())
        rest = rest.lstrip()
        if rest[:1] == ",":
            rest = rest[1:]
    if kind is list:
        return [_scalar(i) for i in items], rest
    out = {}
    for item in items:
        if ":" not in item:
            raise YamlSubsetError(f"flow mapping entry without ':': {item!r}")
        key, _, val = item.partition(":")
        out[_scalar(key.strip())] = _scalar(val.strip())
    return out, rest


def _read_flow_item(text: str, closer: str):
    depth, quote = 0, None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote and text[i - 1 : i] != "\\":
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            if depth == 0 and ch == closer:
                return text[:i], text[i:]
            depth -= 1
        elif ch == "," and depth == 0:
            return text[:i], text[i:]
    raise YamlSubsetError("unterminated flow collection")
