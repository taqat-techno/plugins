"""Per-session connection state: which profile, which mode, for how long.

Everything here lives in memory for the life of ONE MCP server process, which is
one Claude Code session. Nothing is written to a developer's config file, so a
switch or an elevation in one session can never change another session - the
failure the shared-default design caused (lesson 2026-09-27).

The developer's profile decides the CEILING and the APPROVAL needed to raise the
mode. This module moves the session within those limits:

  approval "none"   local profiles: Claude switches freely.
  approval "chat"   Claude must ask the developer and pass their verbatim answer
                    (approved_by_user). Procedural: the transcript is the record.
  approval "human"  needs a grant written by odoo_mcp_ctl.py, which refuses to run
                    without an interactive terminal (Claude's shell tool has none).
                    The grant is HMAC-SHA256 signed with a key in <home>/grant.key
                    that only odoo_mcp_ctl.py creates, and is bound to the profile's
                    url and database. A grant file written by hand (or by Claude's
                    Write tool) has no valid signature and is ignored.

Limits, stated plainly: the signature stops a forged JSON file and an injected
"write this grant" instruction. It does not stop a process that runs as the
developer from READING grant.key and signing its own grant - an agent with an
unrestricted shell could do that deliberately, in several visible steps. The
hard limit is the profile's `ceiling`, which only the developer can raise by
editing the profile; keep production at `ceiling: read` unless writes are needed.

Every switch, elevation, refusal and non-local write is appended to audit.log.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional

import profiles as P

DEFAULT_TTL = {"local": 0, "staging": 60, "production": 30}   # minutes; 0 = session
MAX_TTL = {"local": 0, "staging": 480, "production": 120}


class ApprovalError(Exception):
    """Refusal whose message tells Claude exactly what the developer must do."""


def _now() -> float:
    return time.time()


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def audit(event: dict) -> None:
    """Append one JSON line. Never raises; never records secrets or record values."""
    try:
        path = P.audit_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"ts": _iso(_now()), "pid": os.getpid()}
        entry.update(event)
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# --------------------------------------------------------------------------
# Grants (human approval)
# --------------------------------------------------------------------------


GRANT_KEY_FILE = "grant.key"
_SIGNED_FIELDS = ("profile", "mode", "created_at", "expires_at", "url", "db")


def grant_path(profile_name: str):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", profile_name)[:80]
    return P.grants_dir() / (safe + ".json")


def grant_key_path():
    return P.home() / GRANT_KEY_FILE


def _load_key(create: bool = False) -> Optional[bytes]:
    """The grant-signing key. Only odoo_mcp_ctl.py passes create=True; the server
    never creates it, so a missing key means no grant can be valid."""
    path = grant_key_path()
    try:
        key = bytes.fromhex(path.read_text(encoding="ascii").strip())
        if len(key) >= 32:
            return key
    except (OSError, ValueError):
        pass
    if not create:
        return None
    key = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(key.hex(), encoding="ascii")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, path)
    return key


def _signature(grant: dict, key: bytes) -> str:
    body = json.dumps({k: grant.get(k) for k in _SIGNED_FIELDS}, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=True)
    return hmac.new(key, body.encode("ascii"), hashlib.sha256).hexdigest()


def write_grant(prof: "P.Profile", mode: str, ttl_minutes: int, by: str = "") -> dict:
    """Sign and store a grant. Called by odoo_mcp_ctl.py after its TTY checks."""
    key = _load_key(create=True)
    now = _now()
    grant = {"profile": prof.name, "mode": mode, "created_at": now,
             "expires_at": now + int(ttl_minutes) * 60, "url": prof.url,
             "db": prof.db or "", "by": by}
    grant["sig"] = _signature(grant, key)
    path = grant_path(prof.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(grant, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return grant


def read_grant(profile_name: str, prof: "Optional[P.Profile]" = None) -> Optional[dict]:
    """A valid, signed, unexpired grant for exactly this profile, or None.

    With `prof`, the grant must also name that profile's url and database and must
    not outlive the tier's maximum TTL."""
    try:
        data = json.loads(grant_path(profile_name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("profile") != profile_name:
        return None
    if data.get("mode") not in P.MODES:
        return None
    key = _load_key()
    sig = data.get("sig")
    if key is None or not isinstance(sig, str) or not hmac.compare_digest(sig, _signature(data, key)):
        return None
    try:
        created = float(data.get("created_at", 0))
        expires = float(data.get("expires_at", 0))
    except (TypeError, ValueError):
        return None
    now = _now()
    if expires <= now or created > now + 60:
        return None
    if prof is not None:
        if data.get("url") != prof.url or (data.get("db") or "") != (prof.db or ""):
            return None
        cap = MAX_TTL.get(prof.tier) or 480
        if expires - created > cap * 60 + 60:
            return None
    return data


# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------


@dataclass
class SessionState:
    override: Optional[str] = None            # profile chosen with odoo_session use
    elevated_profile: Optional[str] = None    # which profile the elevation belongs to
    mode: Optional[str] = None
    expires_at: float = 0.0                   # 0 = until the session ends / reset
    scope: frozenset = frozenset()
    reason: str = ""
    notices: list = field(default_factory=list)   # one-shot messages for the next tool result

    # ---- effective mode -------------------------------------------------

    def effective(self, prof: "P.Profile") -> "P.Profile":
        """The profile with the session's mode applied (clamped to the ceiling)."""
        mode = prof.start
        scope = frozenset()
        if self.mode and self.elevated_profile == prof.name:
            if self.expires_at and self.expires_at <= _now():
                self.notices.append(
                    "Elevation of %r to %s expired; back to %s." % (prof.name, self.mode, prof.start)
                )
                audit({"action": "expire", "profile": prof.name, "tier": prof.tier,
                       "from": self.mode, "to": prof.start})
                self.clear_elevation()
            else:
                mode = self.mode
                scope = self.scope
        if P.RANK[mode] > P.RANK[prof.ceiling]:
            mode = prof.ceiling
        return prof.with_mode(mode, scope)

    def clear_elevation(self) -> None:
        self.elevated_profile = None
        self.mode = None
        self.expires_at = 0.0
        self.scope = frozenset()
        self.reason = ""

    def describe(self) -> dict:
        if not self.mode:
            return {}
        out = {"elevated_mode": self.mode, "for_profile": self.elevated_profile}
        if self.expires_at:
            out["expires_at"] = _iso(self.expires_at)
            out["minutes_left"] = max(0, int((self.expires_at - _now()) / 60))
        if self.scope:
            out["write_scope"] = sorted(self.scope)
        if self.reason:
            out["reason"] = self.reason
        return out

    # ---- approval --------------------------------------------------------

    @staticmethod
    def check_approval(prof: "P.Profile", action: str, target: str, approved_by_user) -> str:
        """Return a short label of how this was approved, or raise ApprovalError."""
        kind = prof.approval
        if kind == "none":
            return "none-required (%s tier)" % prof.tier
        if kind == "chat":
            answer = (approved_by_user or "").strip() if isinstance(approved_by_user, str) else ""
            if len(answer) < 2:
                raise ApprovalError(
                    "%s %r to %s needs the developer's explicit approval (profile approval: chat).\n"
                    "Ask the developer - name the profile, tier, url and the mode - and repeat the "
                    "call with approved_by_user set to their answer, verbatim. Do not assume "
                    "approval from earlier messages." % (action, prof.name, target)
                )
            return "chat"
        # human
        grant = read_grant(prof.name, prof)
        if grant and P.RANK[grant["mode"]] >= P.RANK[target]:
            return "human-grant until %s" % _iso(float(grant["expires_at"]))
        raise ApprovalError(
            "%s %r (%s) to %s needs HUMAN approval, which Claude cannot give.\n"
            "Ask the developer to run this in their own terminal (it refuses to run from a "
            "non-interactive shell):\n\n"
            "    python \"<odoo-plugin>/scripts/mcp/odoo_mcp_ctl.py\" approve %s %s --ttl 30\n\n"
            "Then retry. Do not run that command yourself."
            % (action, prof.name, prof.tier, target, prof.name, target)
        )

    # ---- actions -------------------------------------------------------------

    def set_mode(self, prof: "P.Profile", target: str, ttl_minutes=None, models=None,
                 reason: str = "", approved_by_user=None) -> dict:
        if target not in P.MODES:
            raise ApprovalError("mode must be one of %s" % ", ".join(P.MODES))
        if P.RANK[target] > P.RANK[prof.ceiling]:
            audit({"action": "refused", "profile": prof.name, "tier": prof.tier,
                   "requested": target, "why": "above ceiling"})
            raise ApprovalError(
                "profile %r has ceiling %r, set by the developer in %s. %s is above it, so no "
                "approval can unlock it in a session. Only the developer can raise the ceiling, "
                "by editing that profile." % (prof.name, prof.ceiling, prof.source, target)
            )
        current = self.effective(prof).mode
        scope = frozenset(str(m).strip() for m in (models or []) if str(m).strip())

        if target == prof.start and not scope:
            self.clear_elevation()
            audit({"action": "mode", "profile": prof.name, "tier": prof.tier,
                   "from": current, "to": target, "approval": "not needed (back to start)"})
            return {"mode": target, "profile": prof.name}

        approval = "not needed (lowering)"
        if P.RANK[target] > P.RANK[prof.start]:
            try:
                approval = self.check_approval(prof, "raising", target, approved_by_user)
            except ApprovalError:
                audit({"action": "refused", "profile": prof.name, "tier": prof.tier,
                       "requested": target, "why": "approval missing (%s)" % prof.approval})
                raise

        ttl = DEFAULT_TTL[prof.tier] if ttl_minutes in (None, "") else int(ttl_minutes)
        cap = MAX_TTL[prof.tier]
        if cap:
            ttl = max(1, min(ttl, cap))
        self.elevated_profile = prof.name
        self.mode = target
        self.expires_at = _now() + ttl * 60 if (cap and ttl) else 0.0
        self.scope = scope
        self.reason = (reason or "")[:200]
        audit({
            "action": "mode", "profile": prof.name, "tier": prof.tier, "from": current,
            "to": target, "approval": approval,
            "approved_by_user": (approved_by_user or "")[:200] if isinstance(approved_by_user, str) else "",
            "ttl_minutes": ttl if self.expires_at else None, "scope": sorted(scope), "reason": self.reason,
        })
        out = {"mode": target, "profile": prof.name, "approval": approval}
        out.update(self.describe())
        return out

    def use(self, prof: "P.Profile", approved_by_user=None) -> dict:
        approval = "none-required"
        if prof.tier == "production":
            approval = self._production_read_approval(prof, approved_by_user)
        self.override = prof.name
        self.clear_elevation()
        audit({"action": "use", "profile": prof.name, "tier": prof.tier, "approval": approval,
               "approved_by_user": (approved_by_user or "")[:200] if isinstance(approved_by_user, str) else ""})
        return {"active": prof.name, "tier": prof.tier, "mode": prof.start, "approval": approval}

    @staticmethod
    def _production_read_approval(prof, approved_by_user) -> str:
        """Switching a session onto production (read-only) needs the developer's yes in
        chat whatever the profile's approval setting: that setting guards WRITES, but
        pointing a session at production must still be deliberate."""
        answer = (approved_by_user or "").strip() if isinstance(approved_by_user, str) else ""
        if len(answer) < 2:
            raise ApprovalError(
                "switching this session to production profile %r needs the developer's explicit "
                "yes. Ask them (name the profile and url) and repeat with approved_by_user set to "
                "their answer. The session stays READ-ONLY there; writes need a separate "
                "approval." % prof.name
            )
        return "chat (production read)"

    def reset(self) -> None:
        self.override = None
        self.clear_elevation()
        audit({"action": "reset"})
