"""Kleiner HTTP-Server fuer Dashboard und Exporte (nur Python-Standardbibliothek).

Der Server ist rein lesend: Es gibt ausschliesslich GET-Anfragen. Ueber das
Dashboard kann nichts am Test veraendert werden.
"""
from __future__ import annotations

import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

from . import report as report_mod

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
STATIC_FILES = {"/": "index.html", "/index.html": "index.html", "/styles.css": "styles.css",
                "/app.js": "app.js", "/charts.js": "charts.js", "/favicon.svg": "favicon.svg"}


def _int(query: dict, name: str, default: Optional[int] = None) -> Optional[int]:
    try:
        return int(query[name][0])
    except (KeyError, IndexError, ValueError):
        return default


def make_handler(engine):
    storage = engine.storage

    class Handler(BaseHTTPRequestHandler):
        server_version = "KICryptoTrader/1.0"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # keine Zugriffsprotokolle auf der Konsole
            return

        # -- Antworten -----------------------------------------------------------
        def _send(self, status: int, body: bytes, content_type: str, extra: Optional[dict] = None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, data, status: int = 200):
            self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

        def _download(self, body: bytes, content_type: str, filename: str):
            self._send(200, body, content_type,
                       {"Content-Disposition": f'attachment; filename="{filename}"'})

        def _report(self) -> dict:
            if engine.test["status"] == "finished":
                stored = storage.get_meta("final_report")
                if stored:
                    return stored
            return report_mod.build_report(engine)

        # -- Routen --------------------------------------------------------------
        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            try:
                self._route()
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as exc:  # pragma: no cover
                try:
                    self._json({"error": f"Interner Fehler: {type(exc).__name__}"}, 500)
                except Exception:
                    pass

        def _route(self):
            url = urlparse(self.path)
            path = url.path
            query = parse_qs(url.query)

            if path in STATIC_FILES:
                return self._static(STATIC_FILES[path])
            if path == "/api/state":
                return self._json(engine.state())
            if path == "/api/decisions":
                flt = (query.get("filter") or ["all"])[0]
                rows = storage.get_decisions(limit=_int(query, "limit", 40) or 40,
                                             before_id=_int(query, "before"),
                                             after_id=_int(query, "after"), flt=flt)
                return self._json({"items": rows, "total": storage.count_decisions(flt)})
            if path == "/api/trades":
                return self._json({"items": storage.get_trades()})
            if path == "/api/series":
                rows = storage.get_equity(after_id=_int(query, "after", 0) or 0)
                return self._json({"points": [[r["id"], r["ts"], r["price"], r["equity"]] for r in rows]})
            if path == "/api/events":
                return self._json({"items": storage.get_events(_int(query, "limit", 30) or 30)})
            if path == "/api/report":
                return self._json(self._report())

            stamp = "test"
            if path == "/export/bericht.pdf":
                report = self._report()
                return self._download(report_mod.report_pdf(report, storage.get_trades()),
                                      "application/pdf", f"ki-crypto-trader_bericht_{stamp}.pdf")
            if path == "/export/bericht.csv":
                report = self._report()
                return self._download(report_mod.report_csv(report, storage.get_trades()).encode("utf-8"),
                                      "text/csv; charset=utf-8", f"ki-crypto-trader_bericht_{stamp}.csv")
            if path == "/export/trades.csv":
                return self._download(report_mod.trades_csv(storage.get_trades()).encode("utf-8"),
                                      "text/csv; charset=utf-8", "ki-crypto-trader_trades.csv")
            if path == "/export/entscheidungen.csv":
                return self._download(
                    report_mod.decisions_csv(storage.iter_decisions()).encode("utf-8"),
                    "text/csv; charset=utf-8", "ki-crypto-trader_entscheidungen.csv")
            if path == "/export/kontostand.csv":
                return self._download(report_mod.equity_csv(storage.get_equity()).encode("utf-8"),
                                      "text/csv; charset=utf-8", "ki-crypto-trader_kontostand.csv")
            return self._json({"error": "Nicht gefunden"}, 404)

        def _static(self, name: str):
            full = os.path.join(WEB_DIR, name)
            try:
                with open(full, "rb") as handle:
                    body = handle.read()
            except OSError:
                return self._json({"error": "Datei fehlt"}, 404)
            ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript", "image/svg+xml"):
                ctype += "; charset=utf-8"
            self._send(200, body, ctype)

    return Handler


class DashboardServer:
    def __init__(self, engine, host: str = "127.0.0.1", port: int = 8000):
        self.httpd = ThreadingHTTPServer((host, port), make_handler(engine))
        self.httpd.daemon_threads = True
        self.host, self.port = self.httpd.server_address[:2]
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self.httpd.serve_forever, name="web", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
