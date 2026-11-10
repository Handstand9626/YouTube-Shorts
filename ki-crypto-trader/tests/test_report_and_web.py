import json
import unittest
import urllib.error
import urllib.request
from unittest import mock

from tests.helpers import FakeData, SimClock, make_analysis
from kitrader import engine as engine_mod
from kitrader import report as report_mod
from kitrader.config import Config
from kitrader.engine import Engine
from kitrader.pdfwriter import PdfDoc, text_width
from kitrader.storage import Storage
from kitrader.webserver import DashboardServer

BUY = dict(trend=1, macd=1, rsi=1, volume=1)


def played_engine():
    """Zwei abgeschlossene Trades: ein Gewinn (Gewinnziel) und ein Verlust (Stop-Loss)."""
    clock = SimClock()
    data = FakeData(clock)
    scores = {}
    patcher = mock.patch.object(engine_mod.strategy, "analyze",
                                lambda candles, price, cfg: make_analysis(price, **scores))
    patcher.start()
    engine = Engine(Storage(":memory:"), Config(), data_client=data, clock=clock)

    def cycle(seconds=60):
        engine.run_cycle()
        clock.advance(seconds)

    scores.update(BUY)
    cycle()                                   # Kauf 1
    scores.clear()
    data.price *= 1.035
    cycle(3 * 3600)                           # Gewinnziel
    scores.update(BUY)
    cycle()                                   # Kauf 2
    scores.clear()
    data.price *= 0.975
    cycle()                                   # Stop-Loss
    return engine, clock, patcher


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.engine, self.clock, patcher = played_engine()
        self.addCleanup(patcher.stop)
        self.report = report_mod.build_report(self.engine)

    def test_key_figures_are_consistent(self):
        r = self.report
        trades = self.engine.storage.get_trades()
        sells = [t for t in trades if t["side"] == "SELL"]
        self.assertEqual((r["orders_total"], r["closed_trades"], r["wins"], r["losses"]), (4, 2, 1, 1))
        self.assertAlmostEqual(r["win_rate_pct"], 50.0)
        self.assertAlmostEqual(r["pnl_eur"], sum(t["pnl_eur"] for t in sells), places=9)
        self.assertAlmostEqual(r["end_capital"], 20.0 + r["pnl_eur"], places=9)
        self.assertAlmostEqual(r["return_pct"], r["pnl_eur"] / 20.0 * 100, places=9)
        self.assertAlmostEqual(r["fees_total"], sum(t["fee_eur"] for t in trades), places=9)
        self.assertAlmostEqual(r["avg_win_eur"], sells[0]["pnl_eur"])
        self.assertAlmostEqual(r["avg_loss_eur"], sells[1]["pnl_eur"])
        self.assertAlmostEqual(r["max_win_eur"], sells[0]["pnl_eur"])
        self.assertAlmostEqual(r["max_loss_eur"], sells[1]["pnl_eur"])
        self.assertGreater(r["max_drawdown_eur"], 0)
        self.assertAlmostEqual(r["profit_factor"], sells[0]["pnl_eur"] / -sells[1]["pnl_eur"])
        self.assertEqual(r["exit_reasons"], {"Gewinnziel erreicht": 1, "Stop-Loss": 1})
        self.assertFalse(r["final"])
        self.assertIn("vorläufig", r["evaluation"]["verdict"])
        self.assertTrue(any("kleine Stichprobe" in p for p in r["evaluation"]["paragraphs"]))

    def test_max_drawdown_matches_equity_curve(self):
        points = self.engine.storage.get_equity()
        peak, worst = 20.0, 0.0
        for p in points:
            peak = max(peak, p["equity"])
            worst = max(worst, peak - p["equity"])
        self.assertAlmostEqual(self.report["max_drawdown_eur"], worst, places=9)

    def test_report_without_trades_is_not_rated(self):
        engine = Engine(Storage(":memory:"), Config(), data_client=FakeData(SimClock()),
                        clock=SimClock())
        r = report_mod.build_report(engine)
        self.assertEqual(r["evaluation"]["verdict_code"], "NOT_RATEABLE")
        self.assertIsNone(r["avg_win_eur"])
        self.assertIsNone(r["win_rate_pct"])
        self.assertEqual(r["end_capital"], 20.0)

    def test_csv_exports(self):
        trades = self.engine.storage.get_trades()
        text = report_mod.report_csv(self.report, trades)
        self.assertTrue(text.startswith("﻿"))
        for needle in ("Startkapital;20,00 €", "Größter Gewinn", "Maximaler Drawdown",
                       "Handelsgebühren gesamt", "Bewertung der Strategie", "Stop-Loss"):
            self.assertIn(needle, text)
        self.assertEqual(len(report_mod.trades_csv(trades).strip().splitlines()), 5)
        decisions = report_mod.decisions_csv(self.engine.storage.iter_decisions())
        self.assertEqual(len(decisions.strip().split("\r\n")), 5)
        self.assertIn("5 – Trade abgeschlossen", decisions)
        self.assertEqual(len(report_mod.equity_csv(self.engine.storage.get_equity()).strip().splitlines()), 5)

    def test_pdf_export(self):
        pdf = report_mod.report_pdf(self.report, self.engine.storage.get_trades())
        self.assertTrue(pdf.startswith(b"%PDF-1.4"))
        self.assertTrue(pdf.rstrip().endswith(b"%%EOF"))
        try:
            from pypdf import PdfReader
        except ImportError:
            self.skipTest("pypdf nicht installiert – Inhaltsprüfung übersprungen")
        import io
        reader = PdfReader(io.BytesIO(pdf))
        text = "\n".join(page.extract_text() for page in reader.pages)
        for needle in ("KI Crypto Trader", "Zwischenbericht", "Startkapital", "20,00 €",
                       "Bewertung der Strategie", "Größter Verlust", "Paper-Trading"):
            self.assertIn(needle, text)

    def test_pdf_writer_basics(self):
        self.assertAlmostEqual(text_width("0000", 10), 4 * 5.56)
        doc = PdfDoc("Test")
        for i in range(120):
            doc.paragraph(f"Zeile {i} mit Umlauten äöüß und Eurozeichen €")
        self.assertGreater(len(doc.pages), 1)
        self.assertTrue(doc.build().startswith(b"%PDF"))


class WebServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine, cls.clock, cls.patcher = played_engine()
        cls.server = DashboardServer(cls.engine, "127.0.0.1", 0)
        cls.server.start()
        cls.base = f"http://127.0.0.1:{cls.server.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.patcher.stop()

    def get(self, path):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(self.base + path, timeout=10) as response:
            return response.status, response.headers, response.read()

    def test_dashboard_files_are_served(self):
        for path, marker in (("/", b"<!doctype html"), ("/styles.css", b"--"), ("/app.js", b"fetch"),
                             ("/charts.js", b"svg")):
            status, _, body = self.get(path)
            self.assertEqual(status, 200, path)
            self.assertIn(marker, body.lower(), path)

    def test_state_endpoint(self):
        status, headers, body = self.get("/api/state")
        state = json.loads(body)
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(state["mode"], "PAPER_TRADING")
        self.assertEqual(state["counters"]["trades"], 4)
        for key in ("account", "activity", "ai", "test", "market", "last_decision", "rev"):
            self.assertIn(key, state)

    def test_list_endpoints(self):
        decisions = json.loads(self.get("/api/decisions?limit=2")[2])
        self.assertEqual(len(decisions["items"]), 2)
        self.assertEqual(decisions["total"], 4)
        older = json.loads(self.get(f"/api/decisions?before={decisions['items'][-1]['id']}")[2])
        self.assertEqual(len(older["items"]), 2)
        only_trades = json.loads(self.get("/api/decisions?filter=trade")[2])
        self.assertEqual(only_trades["total"], 4)
        self.assertEqual(len(json.loads(self.get("/api/trades")[2])["items"]), 4)
        series = json.loads(self.get("/api/series")[2])["points"]
        self.assertEqual(len(series), 4)
        self.assertEqual(json.loads(self.get(f"/api/series?after={series[1][0]}")[2])["points"], series[2:])
        self.assertTrue(json.loads(self.get("/api/events")[2])["items"])
        self.assertEqual(json.loads(self.get("/api/report")[2])["closed_trades"], 2)

    def test_exports(self):
        status, headers, body = self.get("/export/bericht.pdf")
        self.assertEqual(headers["Content-Type"], "application/pdf")
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertTrue(body.startswith(b"%PDF"))
        for path in ("/export/bericht.csv", "/export/trades.csv", "/export/entscheidungen.csv",
                     "/export/kontostand.csv"):
            status, headers, body = self.get(path)
            self.assertEqual(status, 200)
            self.assertIn("text/csv", headers["Content-Type"])
            self.assertTrue(body.startswith(b"\xef\xbb\xbf"))

    def test_unknown_path_and_write_requests_are_refused(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.get("/api/gibtsnicht")
        self.assertEqual(caught.exception.code, 404)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.get("/../start.py")
        self.assertEqual(caught.exception.code, 404)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        request = urllib.request.Request(self.base + "/api/state", data=b"{}", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            opener.open(request, timeout=10)
        self.assertEqual(caught.exception.code, 501)      # der Server kennt nur Lesezugriffe


if __name__ == "__main__":
    unittest.main()
