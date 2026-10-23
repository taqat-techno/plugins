"""A tiny fake Odoo 17 for MCP tests: XML-RPC (common + object) and the
/web/database/list JSON route, on 127.0.0.1.

Each serve() gets its own handler class, so two fake servers in one test keep
separate state (live_db, key_valid).
"""

from __future__ import annotations

import json
import threading
import xmlrpc.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeOdoo(BaseHTTPRequestHandler):
    live_db = "acme-stage-2002"
    key_valid = True

    def log_message(self, *a):
        pass

    def _send(self, body, ctype):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        cls = type(self)
        if self.path == "/web/database/list":
            return self._send(json.dumps({"jsonrpc": "2.0", "result": [cls.live_db]}),
                              "application/json")
        params, method = xmlrpc.client.loads(raw)
        try:
            if method == "version":
                result = {"server_version": "17.0", "server_version_info": [17, 0, 0, "final", 0]}
            elif method == "authenticate":
                db = params[0]
                if db != cls.live_db:
                    raise xmlrpc.client.Fault(
                        1, 'psycopg2.OperationalError: FATAL:  database "%s" does not exist' % db)
                result = 2 if cls.key_valid else False
            elif method == "execute_kw":
                if params[0] != cls.live_db:   # like Odoo: every object call names its db
                    raise xmlrpc.client.Fault(
                        1, 'psycopg2.OperationalError: FATAL:  database "%s" does not exist'
                        % params[0])
                result = [{"id": 7, "name": "Acme"}] if params[4] == "search_read" else 1
            elif method == "list":
                result = [cls.live_db]
            else:
                raise xmlrpc.client.Fault(1, "unknown method %s" % method)
            body = xmlrpc.client.dumps((result,), methodresponse=True, allow_none=True)
        except xmlrpc.client.Fault as fault:
            body = xmlrpc.client.dumps(fault, methodresponse=True)
        self._send(body, "text/xml")


def serve(live_db: str):
    """Start a fake Odoo serving `live_db`; returns (server, base url). Stop it with
    server.shutdown(). Change its state through server.RequestHandlerClass."""
    handler = type("FakeOdoo_" + live_db.replace("-", "_"), (FakeOdoo,),
                   {"live_db": live_db, "key_valid": True})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:%d" % server.server_address[1]
