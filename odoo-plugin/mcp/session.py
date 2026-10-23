"""Per-session routing for the Odoo MCP server. One server process = one session.

Every tool call names an instance ("prod", or "project/instance" for another
project) or gets the project's default. The session keeps only:

  - one cached client per instance definition (rebuilt when the definition changes);
  - the database picked for "db": "auto", in memory only - nothing is written;
  - production unlocks, per instance, expiring.

The developer's file decides what an instance may do ("access"). Local and stage
instances work at that level directly; a prod instance stays read-only until the
developer's verbatim yes unlocks it for a while. Nothing here can exceed "access",
and nothing here changes another session.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import replace
from pathlib import Path
from typing import Optional

import config as C
from odoo_client import OdooClient

UNLOCK_DEFAULT_MIN = 30
UNLOCK_MAX_MIN = 120
AUDIT_MAX_BYTES = 1_000_000

SETUP_HELP = """No Odoo connections are configured: ~/.odoo-mcp/profiles.json does not exist.

LOCAL Odoo on this machine - connect without asking; from the project folder run
  python "<odoo-plugin>/scripts/mcp/odoo_mcp.py" local
STAGING / PRODUCTION - add an instance (the key is read from a prompt or stdin):
  python "<odoo-plugin>/scripts/mcp/odoo_mcp.py" add <project> <instance> --url <url> --tier stage|prod --db <db|auto> --username <login> --key-stdin
No restart is needed: the next call sees the file. Details: /mcp-setup.

API keys: Odoo > Preferences > Account Security > Developer API Keys. For Odoo.sh staging,
create the key in PRODUCTION so it survives staging rebuilds."""


class ApprovalError(Exception):
    """A refusal whose message says exactly what the developer must do."""


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def _hhmm(ts: float) -> str:
    return time.strftime("%H:%MZ", time.gmtime(ts))


def audit(event: dict) -> None:
    """Append one JSON line to <home>/audit.log, rotating at AUDIT_MAX_BYTES.
    Never raises; never records keys or record values."""
    try:
        path = C.home() / "audit.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if path.stat().st_size >= AUDIT_MAX_BYTES:
                os.replace(path, path.with_name("audit.log.1"))
        except OSError:
            pass
        entry = {"ts": _iso(time.time()), "pid": os.getpid()}
        entry.update(event)
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def pick_database(found: list, pattern: str) -> Optional[str]:
    """The one database behind a url, or the one matching `pattern`; else None."""
    cands = list(found or [])
    if pattern:
        cands = [d for d in cands if re.search(pattern, d)]
    return cands[0] if len(cands) == 1 else None


class Session:
    def __init__(self, folder, loader: "C.Loader", client_factory=OdooClient, clock=time.time):
        self.folder = Path(folder)
        self.folders = C.session_folders(self.folder)
        self.loader = loader
        self._factory = client_factory
        self._clock = clock
        self._clients: dict = {}       # qualified -> (fingerprint, client)
        self._unlocks: dict = {}       # qualified -> expiry (epoch seconds)
        self._warnings: list = []
        self.notices: list = []
        self.current = None            # (instance, client or None) of the call in progress

    # ---- configuration -------------------------------------------------------

    def config(self) -> "C.Config":
        cfg, warnings = self.loader.get()
        self._warnings = warnings
        if cfg is None:
            raise C.ConfigError(SETUP_HELP)
        return cfg

    def warnings(self) -> list:
        return list(self._warnings)

    def project(self) -> Optional["C.Project"]:
        return self.config().match(self.folders)

    def resolve(self, ref: Optional[str]) -> "C.Instance":
        cfg = self.config()
        return cfg.lookup(ref, cfg.match(self.folders))

    # ---- effective mode --------------------------------------------------------

    def unlocked_until(self, inst: "C.Instance") -> float:
        until = self._unlocks.get(inst.qualified, 0.0)
        if until and until <= self._clock():
            del self._unlocks[inst.qualified]
            self.notices.append("production unlock of %s expired; it is read-only again."
                                % inst.qualified)
            audit({"action": "expire", "instance": inst.qualified})
            return 0.0
        return until

    def effective(self, inst: "C.Instance") -> "C.Instance":
        """The instance with this session's mode: its access, except a prod instance,
        which is read-only unless unlocked."""
        if inst.tier != "prod" or self.unlocked_until(inst):
            return replace(inst, mode=C.ACCESS_TO_MODE[inst.access])
        return replace(inst, mode="read")

    def target(self, ref: Optional[str]):
        inst = self.effective(self.resolve(ref))
        return inst, self.client(inst)

    # ---- clients -----------------------------------------------------------------

    def client(self, inst: "C.Instance"):
        fp = inst.fingerprint()
        hit = self._clients.get(inst.qualified)
        if hit and hit[0] == fp:
            return hit[1]
        if inst.db_auto:
            probe = self._factory(replace(inst, db=""))
            found = probe.list_databases()
            if found is None and getattr(probe, "flavor", "") == "json2":
                client = probe              # listing disabled: the host selects the database
            else:
                db = pick_database(found or [], inst.db_pattern)
                if db is None:
                    raise C.ConfigError(
                        '%s: db is "auto" but %s serves %s; set "db_pattern" or a fixed "db"'
                        % (inst.qualified, inst.url,
                           ", ".join(found) if found else "no databases (listing disabled)"))
                client = self._factory(replace(inst, db=db))
        else:
            client = self._factory(inst)
        self._clients[inst.qualified] = (fp, client)
        return client

    def drop_client(self, inst: "C.Instance") -> None:
        self._clients.pop(inst.qualified, None)

    # ---- production unlock -----------------------------------------------------------

    def unlock(self, ref: Optional[str], approved_by_user, minutes=None) -> dict:
        inst = self.resolve(ref)
        q = inst.qualified
        if inst.tier != "prod":
            raise ApprovalError("%s is %s: writes follow its access (%s); no unlock needed."
                                % (q, inst.tier, inst.access))
        if inst.access == "read":
            raise ApprovalError(
                "%s has access 'read' in profiles.json, so an unlock cannot allow writes. "
                "To widen it, ask the developer, then run: odoo_mcp.py add %s %s --access write "
                "--approved-by \"<their answer>\"" % (q, inst.project, inst.name))
        answer = approved_by_user.strip() if isinstance(approved_by_user, str) else ""
        if len(answer) < 2:
            raise ApprovalError(
                "unlocking production instance %s (%s) for writes needs the developer's explicit "
                "yes. Ask them - name the instance and its url - and pass their answer verbatim "
                "as approved_by_user. Never reuse an earlier yes." % (q, inst.url))
        try:
            m = UNLOCK_DEFAULT_MIN if minutes in (None, "") else int(minutes)
        except (TypeError, ValueError):
            raise ApprovalError("minutes must be a whole number")
        m = max(1, min(m, UNLOCK_MAX_MIN))
        until = self._clock() + m * 60
        self._unlocks[q] = until
        audit({"action": "unlock", "instance": q, "url": inst.url, "db": inst.db,
               "minutes": m, "approved_by_user": answer[:200]})
        return {"unlocked": q, "until": _hhmm(until), "minutes": m,
                "mode": C.ACCESS_TO_MODE[inst.access]}

    def lock(self, ref: Optional[str] = None) -> dict:
        if ref:
            q = self.resolve(ref).qualified
            names = [q] if self._unlocks.pop(q, None) else []
        else:
            names = sorted(self._unlocks)
            self._unlocks.clear()
        audit({"action": "lock", "instances": names})
        return {"locked": names}
