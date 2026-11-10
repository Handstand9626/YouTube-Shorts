import os
import tempfile
import time
import unittest
from unittest import mock

from tests.helpers import FakeData, SimClock, make_analysis, make_candles
from kitrader import engine as engine_mod
from kitrader.config import Config
from kitrader.engine import Engine
from kitrader.storage import Storage

BUY = dict(trend=1, macd=1, rsi=1, volume=1)


class Scripted:
    """Ersetzt nur die Marktanalyse; Entscheidung, Risiko und Verbuchung bleiben echt."""

    def __init__(self):
        self.scores = {}

    def __call__(self, candles, price, cfg):
        return make_analysis(price, **self.scores)


class EngineTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = os.path.join(self.tmp.name, "trader.db")
        self.clock = SimClock()
        self.data = FakeData(self.clock)
        self.script = Scripted()
        patcher = mock.patch.object(engine_mod.strategy, "analyze", self.script)
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_engine(self, cfg=None, path=None):
        storage = Storage(path or self.db_path)
        self.addCleanup(storage.close)
        return Engine(storage, cfg or Config(), data_client=self.data, clock=self.clock,
                      report_dir=os.path.join(self.tmp.name, "berichte"))

    def cycle(self, engine, seconds=60):
        ok = engine.run_cycle()
        self.clock.advance(seconds)
        return ok


class CycleTests(EngineTestCase):
    def test_new_test_starts_with_20_euro_and_72_hours(self):
        engine = self.make_engine()
        state = engine.state()
        self.assertEqual(state["mode"], "PAPER_TRADING")
        self.assertEqual(state["account"]["start_capital"], 20.0)
        self.assertEqual(state["account"]["equity"], 20.0)
        self.assertAlmostEqual(state["test"]["end_ts"] - state["test"]["start_ts"], 72 * 3600)
        self.assertEqual(state["ai"]["code"], "STARTING")

    def test_analysis_without_signal_records_decision_but_no_trade(self):
        engine = self.make_engine()
        self.assertTrue(self.cycle(engine))
        state = engine.state()
        self.assertEqual(state["counters"]["analyses"], 1)
        self.assertEqual(state["counters"]["trades"], 0)
        self.assertEqual(state["activity"]["code"], "WAITING")
        decision = engine.storage.get_decisions()[0]
        self.assertEqual((decision["decision"], decision["action"], decision["stage"]),
                         ("Kein Kauf", "NONE", 3))
        self.assertEqual(decision["result"], "Keine Transaktion simuliert.")
        stages = decision["detail"]["stages"]
        self.assertIsNotNone(stages["analyzed"])
        self.assertIsNone(stages["signal"])
        self.assertIsNotNone(stages["decided"])
        self.assertIsNone(stages["simulated"])
        codes = [s["code"] for s in decision["detail"]["steps"]]
        self.assertEqual(codes, ["FETCH", "ANALYZE", "NO_SIGNAL", "DECISION"])
        self.assertEqual(len(decision["detail"]["signals"]), 5)
        self.assertEqual(len(engine.storage.get_equity()), 1)

    def test_buy_then_stop_loss_full_round_trip(self):
        engine = self.make_engine()
        self.script.scores = BUY
        self.cycle(engine)
        state = engine.state()
        self.assertEqual(state["activity"]["code"], "HOLDING")
        self.assertAlmostEqual(state["account"]["cash"], 20.0 - 18.0 * 1.004, places=3)
        self.assertGreater(state["account"]["btc"], 0)
        buy_decision = engine.storage.get_decisions()[0]
        self.assertEqual((buy_decision["decision"], buy_decision["stage"]), ("Kauf", 4))
        self.assertIsNone(buy_decision["detail"]["stages"]["closed"])   # noch nicht abgeschlossen
        self.assertIn("noch nicht abgeschlossen", buy_decision["result"])

        self.script.scores = {}
        self.cycle(engine)                                # halten
        self.assertEqual(engine.storage.get_decisions()[0]["decision"], "Halten")

        self.data.price *= 0.98                           # -2 % -> Stop-Loss
        self.cycle(engine)
        sell_decision = engine.storage.get_decisions()[0]
        self.assertEqual((sell_decision["decision"], sell_decision["stage"]), ("Verkauf", 5))
        self.assertIsNotNone(sell_decision["detail"]["stages"]["closed"])
        trades = engine.storage.get_trades()
        self.assertEqual([t["side"] for t in trades], ["BUY", "SELL"])
        self.assertEqual(trades[1]["reason"], "Stop-Loss")
        self.assertLess(trades[1]["pnl_eur"], 0)
        self.assertEqual(trades[1]["decision_id"], sell_decision["id"])
        state = engine.state()
        self.assertEqual(state["account"]["btc"], 0.0)
        self.assertAlmostEqual(state["account"]["equity"], 20.0 + trades[1]["pnl_eur"], places=6)
        self.assertAlmostEqual(state["account"]["equity"], trades[1]["equity_after"], places=6)
        self.assertEqual(state["counters"]["closed_trades"], 1)
        self.assertGreater(state["counters"]["max_drawdown_eur"], 0)
        fees = sum(t["fee_eur"] for t in trades)
        self.assertAlmostEqual(state["account"]["fees_total"], fees, places=9)

    def test_cash_never_negative_and_stake_never_above_cash(self):
        engine = self.make_engine()
        self.script.scores = BUY
        for _ in range(5):
            self.cycle(engine)
            self.assertGreaterEqual(engine.portfolio.cash, 0.0)
        buys = [t for t in engine.storage.get_trades() if t["side"] == "BUY"]
        self.assertEqual(len(buys), 1)                    # nur eine Position gleichzeitig
        self.assertLessEqual(buys[0]["invested_eur"] + buys[0]["fee_eur"], 20.0)

    def test_blocked_signal_is_logged_as_signal_without_trade(self):
        engine = self.make_engine()
        engine.runtime["last_sell_ts"] = self.clock() - 60   # Wartezeit aktiv
        self.script.scores = BUY
        self.cycle(engine)
        decision = engine.storage.get_decisions()[0]
        self.assertTrue(decision["signal_detected"])
        self.assertEqual((decision["action"], decision["stage"]), ("NONE", 3))
        self.assertIsNotNone(decision["detail"]["stages"]["signal"])
        self.assertEqual(engine.state()["counters"]["signals"], 1)
        self.assertEqual(engine.storage.get_trades(), [])


class DataErrorTests(EngineTestCase):
    def test_data_error_pauses_and_never_trades(self):
        engine = self.make_engine()
        self.script.scores = BUY
        self.data.fail = "Verbindung fehlgeschlagen"
        self.assertFalse(self.cycle(engine))
        self.assertFalse(self.cycle(engine))
        state = engine.state()
        self.assertEqual(state["ai"]["code"], "PAUSED")
        self.assertFalse(state["ai"]["active"])
        self.assertEqual(state["activity"]["code"], "PAUSED_NO_DATA")
        self.assertEqual(state["activity"]["text"], "Pausiert aufgrund fehlender Daten")
        self.assertEqual(state["counters"]["data_errors"], 2)
        self.assertEqual(state["counters"]["analyses"], 0)
        self.assertEqual(engine.storage.get_trades(), [])
        self.assertEqual(engine.storage.get_equity(), [])
        rows = engine.storage.get_decisions()
        self.assertEqual(len(rows), 1)                    # ein Eintrag je Ausfall, kein Spam
        self.assertEqual((rows[0]["kind"], rows[0]["stage"]), ("DATA_ERROR", 0))
        self.assertIn("Kein Trade simuliert", rows[0]["result"])

        self.data.fail = None
        self.assertTrue(self.cycle(engine))
        state = engine.state()
        self.assertEqual(state["ai"]["code"], "ACTIVE")
        codes = [e["code"] for e in engine.storage.get_events()]
        self.assertIn("DATA_OUTAGE", codes)
        self.assertIn("DATA_RESTORED", codes)

    def test_storage_failure_rolls_back_the_whole_cycle(self):
        engine = self.make_engine()
        self.script.scores = BUY
        with mock.patch.object(engine.storage, "add_equity", side_effect=RuntimeError("Platte voll")):
            with self.assertRaises(RuntimeError):
                engine.run_cycle()
        self.assertIsNone(engine.portfolio.position)      # Kauf wurde NICHT halb verbucht
        self.assertEqual(engine.portfolio.cash, 20.0)
        self.assertEqual(engine.storage.get_trades(), [])
        self.assertEqual(engine.storage.get_decisions(), [])


class RestartTests(EngineTestCase):
    def test_state_is_restored_after_restart(self):
        first = self.make_engine()
        self.script.scores = BUY
        self.cycle(first)
        self.script.scores = {}
        self.cycle(first)
        before = first.state()
        first.storage.close()

        self.clock.advance(1800)                          # 30 Minuten "ausgeschaltet"
        second = self.make_engine()
        self.assertTrue(second.resumed)
        after = second.state()
        self.assertEqual(after["test"]["start_ts"], before["test"]["start_ts"])
        self.assertEqual(after["test"]["end_ts"], before["test"]["end_ts"])
        self.assertEqual(after["account"]["cash"], before["account"]["cash"])
        self.assertEqual(after["account"]["btc"], before["account"]["btc"])
        self.assertEqual(after["account"]["position"]["entry_price"],
                         before["account"]["position"]["entry_price"])
        self.assertEqual(after["counters"]["analyses"], 2)
        self.assertEqual(after["counters"]["restarts"], 1)
        self.assertGreater(after["counters"]["downtime_s"], 1700)
        self.assertEqual(after["last_decision"]["decision"], "Halten")
        event = second.storage.get_events()[0]
        self.assertEqual(event["code"], "RESTART")
        self.assertIn("nicht aktiv", event["message"])
        self.assertTrue(second.run_cycle())               # laeuft normal weiter
        self.assertEqual(len(second.storage.get_trades()), 1)

    def test_restart_keeps_original_settings(self):
        first = self.make_engine(Config(candle_minutes=15))
        first.storage.close()
        second = self.make_engine(Config(candle_minutes=60, poll_seconds=300))
        self.assertEqual(second.cfg.candle_minutes, 15)
        self.assertEqual(second.cfg.poll_seconds, 60)


class FinalizeTests(EngineTestCase):
    def test_finalize_closes_position_and_writes_report(self):
        engine = self.make_engine()
        self.script.scores = BUY
        self.cycle(engine)
        self.script.scores = {}
        self.data.price *= 1.01
        self.clock.t = engine.test["end_ts"]
        self.assertTrue(engine.finalize())

        state = engine.state()
        self.assertEqual(state["test"]["status"], "finished")
        self.assertEqual(state["ai"]["code"], "FINISHED")
        self.assertEqual(state["test"]["remaining_s"], 0.0)
        self.assertEqual(state["account"]["btc"], 0.0)
        self.assertAlmostEqual(state["test"]["elapsed_s"], 72 * 3600)
        trades = engine.storage.get_trades()
        self.assertEqual(trades[-1]["reason"], "Testende")
        report = engine.storage.get_meta("final_report")
        self.assertTrue(report["final"])
        self.assertAlmostEqual(report["end_capital"], state["account"]["equity"], places=9)
        self.assertEqual(report["closed_trades"], 1)
        files = sorted(os.listdir(os.path.join(self.tmp.name, "berichte")))
        self.assertEqual(len(files), 6)
        self.assertTrue(any(f.endswith(".pdf") for f in files))
        with open(os.path.join(self.tmp.name, "berichte", [f for f in files if f.endswith(".pdf")][0]),
                  "rb") as handle:
            self.assertTrue(handle.read().startswith(b"%PDF-1.4"))

        engine.storage.close()                            # Neustart nach Testende
        again = self.make_engine()
        self.assertEqual(again.state()["test"]["status"], "finished")
        self.assertEqual(len(again.storage.get_trades()), len(trades))

    def test_finalize_waits_when_no_price_is_available(self):
        engine = self.make_engine()
        self.clock.t = engine.test["end_ts"]
        self.data.fail = "keine Verbindung"
        self.assertFalse(engine.finalize())
        self.assertEqual(engine.test["status"], "running")
        self.data.fail = None
        self.assertTrue(engine.finalize())

    def test_late_finalize_uses_real_price_from_end_time(self):
        engine = self.make_engine()
        self.script.scores = BUY
        self.cycle(engine)
        end_ts = engine.test["end_ts"]
        self.clock.t = end_ts + 3 * 3600                  # Rechner war zum Testende aus
        fine = make_candles(400, int(self.clock.t) - int(self.clock.t) % 300, step=300, base=61000.0)
        self.data.fine_candles = fine
        self.data.price = 65000.0                         # heutiger Kurs darf NICHT gelten
        self.assertTrue(engine.finalize())
        trade = engine.storage.get_trades()[-1]
        covering = next(c for c in fine if c.t <= end_ts < c.t + 300)
        self.assertAlmostEqual(trade["price"], covering.c)
        self.assertEqual(trade["ts"], end_ts)
        self.assertIn("nicht aktiv", engine.test["final_note"])

    def test_no_entry_shortly_before_the_end(self):
        engine = self.make_engine()
        self.script.scores = BUY
        self.clock.t = engine.test["end_ts"] - 600
        self.cycle(engine)
        self.assertEqual(engine.storage.get_trades(), [])
        self.assertIn("Testende", engine.storage.get_decisions()[0]["reason"])


class RealTimeLoopTests(unittest.TestCase):
    def test_loop_ends_the_test_exactly_at_the_end_time(self):
        clock = time.time
        data = FakeData(clock)                            # keine Netzwerkzugriffe
        storage = Storage(":memory:")
        cfg = Config()
        cfg.duration_hours = 2.0 / 3600.0                 # 2 Sekunden statt 72 Stunden
        engine = Engine(storage, cfg, data_client=data, clock=clock)
        engine.start()
        deadline = time.time() + 10
        while engine.test["status"] != "finished" and time.time() < deadline:
            time.sleep(0.05)
        engine.stop()
        self.assertEqual(engine.test["status"], "finished")
        lateness = engine.test["finished_ts"] - engine.test["end_ts"]
        self.assertGreaterEqual(lateness, 0.0)
        self.assertLess(lateness, 1.0)
        self.assertEqual(engine.state()["counters"]["analyses"], 1)
        self.assertIsNotNone(storage.get_meta("final_report"))
        storage.close()


class RealStrategyIntegrationTests(unittest.TestCase):
    def test_many_cycles_with_real_strategy_code(self):
        clock = SimClock()
        data = FakeData(clock)
        engine = Engine(Storage(":memory:"), Config(), data_client=data, clock=clock)
        for i in range(30):
            data.price = 60000.0 * (1 + 0.0005 * (i % 7 - 3))
            self.assertTrue(engine.run_cycle())
            clock.advance(60)
        state = engine.state()
        self.assertEqual(state["counters"]["analyses"], 30)
        self.assertEqual(len(engine.storage.get_decisions(limit=100)), 30)
        self.assertEqual(len(engine.storage.get_equity()), 30)
        self.assertTrue(all(d["reason"] and d["detail"]["signals"]
                            for d in engine.storage.get_decisions(limit=100)))


if __name__ == "__main__":
    unittest.main()
