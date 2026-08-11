"""Version-adaptive Odoo transport. Standard library only.

Two wire protocols, chosen automatically from the server version:

  Odoo 19+   POST {url}/json/2/{model}/{method}
             Authorization: Bearer <api_key>, Content-Type: application/json
             Body carries `ids`, `context` and the method's keyword arguments.

  Odoo <=18  XML-RPC. {url}/xmlrpc/2/common#authenticate to get a uid, then
             {url}/xmlrpc/2/object#execute_kw. An API key is accepted anywhere
             a password is, and this path is non-interactive so it is not
             blocked by 2FA.

Both paths execute as the authenticated Odoo user, so ir.model.access,
ir.rule and field-level groups apply exactly as they would in the web client.
Nothing here uses sudo, raw SQL, or a shell.

Portability notes baked in:
  * `name_get` was removed in 18.0 - never called; `display_name` is read instead.
  * `fields_view_get` was removed in 17.0 - `get_views` is used.
  * `read_group` is deprecated in 19.0 but still callable, so it stays the
    portable choice across 14-19.
"""

from __future__ import annotations

import json
import re
import socket
import ssl
import urllib.error
import urllib.request
import xmlrpc.client
from typing import Any, Optional

from guards import redact

JSON2_MIN_MAJOR = 19
USER_AGENT = "odoo-plugin-mcp/1.0 (+claude-code)"


class OdooError(Exception):
    """Actionable failure. The message is shown to the model, so it explains the fix."""


def _ssl_context(verify: bool):
    if verify:
        return None  # urllib default: verified
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _clean_fault(text: str) -> str:
    """Turn an Odoo traceback/fault string into its final, useful line."""
    if not text:
        return ""
    text = text.strip()
    m = re.search(
        r"odoo\.exceptions\.(\w+):\s*(.+?)(?:\n|$)", text, re.S
    )
    if m:
        return "%s: %s" % (m.group(1), m.group(2).strip())
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return text
    for ln in reversed(lines):
        if not ln.startswith(("File \"", "Traceback", "  ")):
            return ln
    return lines[-1]


class OdooClient:
    def __init__(self, profile):
        self.p = profile
        self._version: Optional[dict] = None
        self._uid: Optional[int] = None
        self._flavor: Optional[str] = None

    # -- low level ---------------------------------------------------------

    def _post_json(self, path: str, payload: dict, headers: Optional[dict] = None) -> Any:
        url = "%s%s" % (self.p.url, path)
        body = json.dumps(payload).encode("utf-8")
        hdrs = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
        try:
            with urllib.request.urlopen(
                req, timeout=self.p.timeout, context=_ssl_context(self.p.verify_ssl)
            ) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")[:2000]
            except Exception:
                pass
            raise OdooError(self._http_hint(exc.code, detail, path))
        except urllib.error.URLError as exc:
            raise OdooError(self._net_hint(exc))
        except socket.timeout:
            raise OdooError(
                "timed out after %ss calling %s. The server may be busy, or a long "
                "operation was triggered. Raise \"timeout\" in the profile if this is expected."
                % (self.p.timeout, url)
            )
        if not raw.strip():
            return None
        try:
            return json.loads(raw)
        except ValueError:
            raise OdooError(
                "expected JSON from %s but got something else (first 200 chars): %r\n"
                "This usually means the URL points at a proxy/login page rather than Odoo."
                % (url, raw[:200])
            )

    def _http_hint(self, code: int, detail: str, path: str) -> str:
        detail = (detail or "").strip()
        snippet = _clean_fault(detail)[:600]
        if code == 401:
            return (
                "401 Unauthorized from Odoo. The API key was rejected.\n"
                "Check: the key belongs to user %r on database %r, it has not been "
                "revoked, and it was created in Preferences > Account Security > "
                "Developer API Keys.\n%s"
                % (self.p.username or "(unset)", self.p.db, snippet)
            )
        if code == 404 and path.startswith("/json/2"):
            return (
                "404 from %s. The JSON-2 endpoint does not exist on this server.\n"
                "JSON-2 is new in Odoo 19; on 18 and older the MCP server should use "
                "XML-RPC. If this instance really is 19+, the `rpc` addon may be "
                "uninstalled.\n%s" % (path, snippet)
            )
        if code == 403:
            return "403 Forbidden. The user is authenticated but lacks access.\n%s" % snippet
        if code == 415:
            return "415 Unsupported Media Type - Odoo requires application/json here.\n%s" % snippet
        if code in (500, 502, 503, 504):
            return (
                "Odoo returned HTTP %d. This is a server-side error; check the Odoo log.\n%s"
                % (code, snippet)
            )
        return "HTTP %d from %s.\n%s" % (code, path, snippet)

    def _net_hint(self, exc) -> str:
        reason = getattr(exc, "reason", exc)
        base = "cannot reach Odoo at %s (%s)." % (self.p.url, reason)
        extra = (
            "\nCommon causes: the server is not running; the port is wrong; or the host "
            "is not reachable from where this MCP server runs. If Odoo runs in a VM, "
            "container or WSL while this process runs elsewhere, 'localhost' may not "
            "point at the same machine - use the reachable host address or a published port."
        )
        if isinstance(reason, ssl.SSLError) or "CERTIFICATE" in str(reason).upper():
            extra = (
                "\nTLS verification failed. For a self-signed development certificate you "
                "may set \"verify_ssl\": false in the profile. Do not do that for production."
            )
        return base + extra

    def _xmlrpc(self, endpoint: str):
        url = "%s/xmlrpc/2/%s" % (self.p.url, endpoint)
        ctx = None
        if not self.p.verify_ssl and url.lower().startswith("https"):
            ctx = _ssl_context(False)
        return xmlrpc.client.ServerProxy(url, allow_none=True, context=ctx)

    # -- capability detection ---------------------------------------------

    def version(self) -> dict:
        if self._version is not None:
            return self._version

        # Odoo 19 exposes an unauthenticated version probe.
        try:
            req = urllib.request.Request(
                "%s/json/version" % self.p.url,
                headers={"Accept": "application/json", "User-Agent": USER_AGENT},
                method="GET",
            )
            with urllib.request.urlopen(
                req, timeout=min(self.p.timeout, 15), context=_ssl_context(self.p.verify_ssl)
            ) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            if isinstance(data, dict) and data.get("server_version_info"):
                self._version = data
                return data
        except Exception:
            pass  # older server, or probe unavailable - fall through

        try:
            data = self._xmlrpc("common").version()
        except xmlrpc.client.Fault as exc:
            raise OdooError("Odoo rejected the version probe: %s" % _clean_fault(exc.faultString))
        except (urllib.error.URLError, OSError, socket.timeout) as exc:
            raise OdooError(self._net_hint(exc))
        except xmlrpc.client.ProtocolError as exc:
            raise OdooError(
                "XML-RPC protocol error %s from %s. If this instance is behind a proxy, "
                "confirm /xmlrpc/2/ is not blocked." % (getattr(exc, "errcode", "?"), self.p.url)
            )
        if not isinstance(data, dict):
            raise OdooError("unexpected version response from %s: %r" % (self.p.url, data))
        self._version = data
        return data

    @property
    def major(self) -> int:
        info = self.version().get("server_version_info") or []
        try:
            return int(info[0])
        except (IndexError, TypeError, ValueError):
            m = re.match(r"\s*(\d+)", str(self.version().get("server_version") or ""))
            return int(m.group(1)) if m else 0

    @property
    def flavor(self) -> str:
        if self._flavor is None:
            self._flavor = "json2" if self.major >= JSON2_MIN_MAJOR else "xmlrpc"
        return self._flavor

    def uid(self) -> int:
        if self._uid is not None:
            return self._uid
        if not self.p.username:
            raise OdooError(
                "this profile has no \"username\", which XML-RPC needs to authenticate.\n"
                "Add the Odoo login of the dedicated MCP user to the profile."
            )
        if not self.p.api_key:
            raise OdooError(
                "this profile has no \"api_key\".\n"
                "Create one in Odoo: Preferences > Account Security > Developer API Keys, "
                "then put it in the profile or reference it as ${ENV_VAR}."
            )
        try:
            res = self._xmlrpc("common").authenticate(
                self.p.db, self.p.username, self.p.api_key, {}
            )
        except xmlrpc.client.Fault as exc:
            msg = _clean_fault(exc.faultString)
            if "database" in msg.lower():
                raise OdooError(
                    "%s\nThe database %r may not exist on this server. "
                    "Use odoo_status to see what the server reports." % (msg, self.p.db)
                )
            raise OdooError("authentication failed: %s" % msg)
        except (urllib.error.URLError, OSError, socket.timeout) as exc:
            raise OdooError(self._net_hint(exc))

        # 17.0+ may return a dict; the MFA path yields {'uid': None}, so a bare
        # "no exception raised" check is not sufficient.
        if isinstance(res, dict):
            res = res.get("uid")
        if isinstance(res, bool) or not isinstance(res, int) or res <= 0:
            raise OdooError(
                "authentication returned no usable uid for %r on %r.\n"
                "The login or API key is wrong, the user is archived, or the key was "
                "revoked." % (self.p.username, self.p.db)
            )
        self._uid = res
        return self._uid

    # -- the one call path -------------------------------------------------

    def call(
        self,
        model: str,
        method: str,
        ids: Optional[list] = None,
        args: Optional[list] = None,
        kwargs: Optional[dict] = None,
        context: Optional[dict] = None,
    ) -> Any:
        ids = list(ids or [])
        args = list(args or [])
        kwargs = dict(kwargs or {})

        ctx = dict(self.p.base_context())
        if context:
            ctx.update(context)
        if ctx:
            kwargs["context"] = ctx

        if self.flavor == "json2":
            return self._call_json2(model, method, ids, args, kwargs)
        return self._call_xmlrpc(model, method, ids, args, kwargs)

    def _call_json2(self, model, method, ids, args, kwargs):
        if args:
            raise OdooError(
                "internal: positional arguments are not supported by the JSON-2 API "
                "(it binds keyword arguments only). This is a bug in the MCP server."
            )
        if not self.p.api_key:
            raise OdooError(
                "this profile has no \"api_key\", which the Odoo 19 JSON-2 API requires "
                "as a bearer token.\nCreate one in Odoo: Preferences > Account Security > "
                "Developer API Keys."
            )
        payload = dict(kwargs)
        if ids:
            payload["ids"] = ids
        headers = {"Authorization": "Bearer %s" % self.p.api_key}
        # Odoo selects the database from the request host / a single-db server. When
        # several databases are served, X-Odoo-Database disambiguates.
        if self.p.db:
            headers["X-Odoo-Database"] = self.p.db
        result = self._post_json("/json/2/%s/%s" % (model, method), payload, headers)
        if isinstance(result, dict) and result.get("error") and "result" not in result:
            err = result["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise OdooError("%s.%s failed: %s" % (model, method, _clean_fault(str(msg))))
        return result

    def _call_xmlrpc(self, model, method, ids, args, kwargs):
        uid = self.uid()
        positional = ([ids] if ids else []) + args
        try:
            return self._xmlrpc("object").execute_kw(
                self.p.db, uid, self.p.api_key, model, method, positional, kwargs
            )
        except xmlrpc.client.Fault as exc:
            raise OdooError(
                "%s.%s failed: %s" % (model, method, _clean_fault(exc.faultString))
            )
        except (urllib.error.URLError, OSError, socket.timeout) as exc:
            raise OdooError(self._net_hint(exc))
        except xmlrpc.client.ProtocolError as exc:
            raise OdooError("XML-RPC protocol error %s" % getattr(exc, "errcode", "?"))

    # -- typed helpers (shape differs per wire protocol) -------------------

    def search_read(self, model, domain, fields=None, limit=None, offset=0, order=None, context=None):
        kw = {"domain": domain, "offset": offset}
        if fields:
            kw["fields"] = fields
        if limit:
            kw["limit"] = limit
        if order:
            kw["order"] = order
        return self.call(model, "search_read", kwargs=kw, context=context)

    def search_count(self, model, domain, context=None):
        return self.call(model, "search_count", kwargs={"domain": domain}, context=context)

    def read_group(self, model, domain, fields, groupby, limit=None, orderby=None,
                   lazy=True, context=None):
        kw = {"domain": domain, "fields": fields, "groupby": groupby, "lazy": lazy}
        if limit:
            kw["limit"] = limit
        if orderby:
            kw["orderby"] = orderby
        return self.call(model, "read_group", kwargs=kw, context=context)

    def fields_get(self, model, attributes=None, context=None):
        kw = {}
        if attributes:
            kw["attributes"] = attributes
        return self.call(model, "fields_get", kwargs=kw, context=context)

    def create(self, model, vals_list, context=None):
        if self.flavor == "json2":
            return self.call(model, "create", kwargs={"vals_list": vals_list}, context=context)
        return self.call(model, "create", args=[vals_list], context=context)

    def write(self, model, ids, vals, context=None):
        if self.flavor == "json2":
            return self.call(model, "write", ids=ids, kwargs={"vals": vals}, context=context)
        return self.call(model, "write", args=[ids, vals], context=context)

    def unlink(self, model, ids, context=None):
        if self.flavor == "json2":
            return self.call(model, "unlink", ids=ids, context=context)
        return self.call(model, "unlink", args=[ids], context=context)

    # -- identity ----------------------------------------------------------

    def whoami(self) -> dict:
        """Who Odoo thinks we are, plus the company context. Never returns the key."""
        info = self.version()
        out = {
            "server_version": info.get("server_version"),
            "server_version_info": info.get("server_version_info"),
            "api": "JSON-2 (/json/2)" if self.flavor == "json2" else "XML-RPC (/xmlrpc/2)",
            "database": self.p.db,
        }
        try:
            if self.flavor == "xmlrpc":
                out["uid"] = self.uid()
            rows = self.search_read(
                "res.users",
                [["id", "=", self.uid()]] if self.flavor == "xmlrpc" else [],
                fields=["login", "name", "company_id", "company_ids", "share"],
                limit=1,
            )
            if self.flavor == "json2" and not rows:
                rows = self.search_read(
                    "res.users", [["login", "=", self.p.username]],
                    fields=["login", "name", "company_id", "company_ids", "share"], limit=1,
                )
            if rows:
                u = rows[0]
                out["uid"] = u.get("id", out.get("uid"))
                out["login"] = u.get("login")
                out["user"] = u.get("name")
                out["active_company"] = u.get("company_id")
                out["allowed_companies"] = u.get("company_ids")
                out["is_portal_or_public"] = u.get("share")
        except OdooError as exc:
            out["identity_error"] = redact(str(exc), self.p.secrets())
        return out
