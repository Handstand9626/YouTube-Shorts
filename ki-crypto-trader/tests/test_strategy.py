import unittest

from tests.helpers import STEP, make_analysis, make_candles
from kitrader import strategy
from kitrader.config import Config
from kitrader.strategy import Context, PositionView

CFG = Config()
NOW = 1_800_000_000.0


def ctx(**kw):
    base = dict(now=NOW, end_ts=NOW + 48 * 3600, cash=20.0, equity=20.0, start_capital=20.0,
                bid=59999.0, ask=60001.0)
    base.update(kw)
    return Context(**base)


def position(entry=60000.0, peak=None, held_h=5.0):
    return PositionView(entry_price=entry, peak_price=peak or entry, stake_eur=18.0, fee_eur=0.072,
                        btc=0.0003, entry_ts=NOW - held_h * 3600)


class AnalyzeTests(unittest.TestCase):
    def test_five_signals_and_score_sum(self):
        candles = make_candles(150, int(NOW), pattern=(0.3, -0.2))
        a = strategy.analyze(candles, candles[-1].c, CFG)
        self.assertEqual([s.key for s in a.signals], ["trend", "macd", "rsi", "volume", "momentum"])
        self.assertEqual(a.score, sum(s.score for s in a.signals))
        self.assertTrue(all(s.score in (-1, 0, 1) for s in a.signals))
        self.assertTrue(all(s.text and s.value for s in a.signals))

    def test_uptrend_is_recognised(self):
        candles = make_candles(150, int(NOW), pattern=(0.3, -0.2))
        price = candles[-1].c * 1.004
        a = strategy.analyze(candles, price, CFG)
        self.assertEqual(a.signal("trend").score, 1)
        self.assertEqual(a.signal("momentum").score, 1)
        self.assertIn("Aufwärtstrend", a.situation)
        self.assertGreater(a.indicators["ema_fast"], a.indicators["ema_slow"])

    def test_downtrend_is_recognised(self):
        candles = make_candles(150, int(NOW), pattern=(-0.3, 0.2))
        a = strategy.analyze(candles, candles[-1].c * 0.996, CFG)
        self.assertEqual(a.signal("trend").score, -1)
        self.assertEqual(a.signal("momentum").score, -1)
        self.assertIn("Abwärtstrend", a.situation)

    def test_flat_market_is_sideways_and_neutral(self):
        candles = make_candles(150, int(NOW), pattern=(0.02, -0.02))
        a = strategy.analyze(candles, candles[-1].c, CFG)
        self.assertEqual(a.situation, "Seitwärtsbewegung")
        self.assertLess(abs(a.score), CFG.buy_score_min)

    def test_volume_confirms_direction(self):
        candles = make_candles(150, int(NOW), pattern=(0.3, -0.2))
        candles[-1].v = 50.0
        candles[-1].c = candles[-1].o * 1.004
        self.assertEqual(strategy.analyze(candles, candles[-1].c, CFG).signal("volume").score, 1)
        candles[-1].c = candles[-1].o * 0.996
        self.assertEqual(strategy.analyze(candles, candles[-1].c, CFG).signal("volume").score, -1)

    def test_too_few_candles_raise(self):
        with self.assertRaises(ValueError):
            strategy.analyze(make_candles(30, int(NOW)), 60000.0, CFG)


class EntryTests(unittest.TestCase):
    def test_buy_needs_several_confirming_signals(self):
        d = strategy.decide(make_analysis(60000, trend=1, macd=1, rsi=1), ctx(), CFG)
        self.assertEqual(d.action, "BUY")
        self.assertTrue(d.signal_detected)
        self.assertTrue(all(c["ok"] for c in d.risk_checks))
        self.assertAlmostEqual(d.stake_eur, 18.0)        # 90 % von 20 EUR
        self.assertIn("Gesamtbewertung +3", d.reason)

    def test_single_indicator_is_never_enough(self):
        for key in ("trend", "macd", "rsi", "volume", "momentum"):
            d = strategy.decide(make_analysis(60000, **{key: 1}), ctx(), CFG)
            self.assertEqual(d.action, "NONE", key)
            self.assertEqual(d.label, "Kein Kauf")
            self.assertFalse(d.signal_detected)

    def test_no_buy_against_or_without_trend(self):
        d = strategy.decide(make_analysis(60000, trend=-1, macd=1, rsi=1, volume=1, momentum=1),
                            ctx(), CFG)
        self.assertEqual(d.action, "NONE")
        self.assertIn("abwärts", d.reason)
        d = strategy.decide(make_analysis(60000, trend=0, macd=1, rsi=1, volume=1), ctx(), CFG)
        self.assertEqual(d.action, "NONE")
        self.assertIn("kein bestätigter Aufwärtstrend", d.reason)

    def test_no_buy_when_overbought(self):
        d = strategy.decide(make_analysis(60000, trend=1, macd=1, volume=1, momentum=1, rsi=-1,
                                          rsi_value=75.0), ctx(), CFG)
        self.assertEqual(d.action, "NONE")
        self.assertIn("überkauft", d.reason)

    def test_risk_checks_can_block_a_signal(self):
        good = dict(trend=1, macd=1, rsi=1, volume=1)
        cases = {
            "Wartezeit nach Verkauf": ctx(last_sell_ts=NOW - 600),
            "Handelshäufigkeit": ctx(buys_last_24h=CFG.max_buys_per_24h),
            "Verlustlimit": ctx(halted=True),
            "Restlaufzeit": ctx(end_ts=NOW + 600),
            "Spread": ctx(bid=59000.0, ask=60001.0),
            "Einsatzgrenze": ctx(cash=3.0),
        }
        for name, context in cases.items():
            d = strategy.decide(make_analysis(60000, **good), context, CFG)
            self.assertEqual(d.action, "NONE", name)
            self.assertTrue(d.signal_detected, name)      # Signal erkannt, aber nicht gehandelt
            failed = [c["name"] for c in d.risk_checks if not c["ok"]]
            self.assertEqual(failed, [name])
            self.assertIn("Risikoprüfung", d.reason)

    def test_longer_cooldown_after_stop_loss(self):
        good = dict(trend=1, macd=1, rsi=1, volume=1)
        waited = CFG.cooldown_candles * STEP + 60
        self.assertEqual(strategy.decide(make_analysis(60000, **good),
                                         ctx(last_sell_ts=NOW - waited), CFG).action, "BUY")
        self.assertEqual(strategy.decide(make_analysis(60000, **good),
                                         ctx(last_sell_ts=NOW - waited, last_exit_code="STOP_LOSS"),
                                         CFG).action, "NONE")

    def test_stake_is_capped(self):
        self.assertAlmostEqual(strategy.max_stake(20.0, CFG), 18.0)
        self.assertAlmostEqual(strategy.max_stake(100.0, CFG), 20.0)   # nie ueber Startkapital
        self.assertEqual(strategy.max_stake(0.0, CFG), 0.0)
        full = Config(max_stake_fraction=1.0)
        stake = strategy.max_stake(20.0, full)
        self.assertLessEqual(stake * (1 + full.fee_rate), 20.0 + 1e-9)  # Gebuehr bleibt bezahlbar


class ExitTests(unittest.TestCase):
    def test_hold_without_trigger(self):
        d = strategy.decide(make_analysis(60300), ctx(bid=60300.0, ask=60302.0, position=position()), CFG)
        self.assertEqual((d.action, d.label), ("NONE", "Halten"))
        self.assertFalse(d.signal_detected)
        self.assertIn("Gewinnschwelle", d.reason)
        self.assertEqual(len(d.risk_checks), 4)

    def test_stop_loss(self):
        d = strategy.decide(make_analysis(59000), ctx(bid=59000.0, ask=59002.0, position=position()), CFG)
        self.assertEqual((d.action, d.exit_code), ("SELL", "STOP_LOSS"))

    def test_take_profit(self):
        d = strategy.decide(make_analysis(61900), ctx(bid=61900.0, ask=61902.0,
                                                      position=position(peak=61900.0)), CFG)
        self.assertEqual((d.action, d.exit_code), ("SELL", "TAKE_PROFIT"))

    def test_trailing_stop_only_after_activation(self):
        pos = position(peak=61200.0)                      # +2 % erreicht -> aktiv
        d = strategy.decide(make_analysis(60650), ctx(bid=60650.0, ask=60652.0, position=pos), CFG)
        self.assertEqual((d.action, d.exit_code), ("SELL", "TRAILING"))
        pos = position(peak=60500.0)                      # nur +0,83 % -> nicht aktiv
        d = strategy.decide(make_analysis(60010), ctx(bid=60010.0, ask=60012.0, position=pos), CFG)
        self.assertEqual(d.action, "NONE")

    def test_signal_exit_needs_confirmed_downtrend_and_holding_time(self):
        bearish = make_analysis(59800, trend=-1, macd=-1)
        c = ctx(bid=59800.0, ask=59802.0, position=position())
        self.assertEqual(strategy.decide(bearish, c, CFG).exit_code, "SIGNAL")
        weak = make_analysis(59800, macd=-1, rsi=-1)      # Score -2, aber kein Abwaertstrend
        self.assertEqual(strategy.decide(weak, c, CFG).action, "NONE")
        fresh = ctx(bid=59800.0, ask=59802.0, position=position(held_h=0.5))
        self.assertEqual(strategy.decide(bearish, fresh, CFG).action, "NONE")

    def test_loss_limit_closes_and_halts(self):
        d = strategy.decide(make_analysis(59900), ctx(bid=59900.0, ask=59902.0, equity=16.9,
                                                      position=position()), CFG)
        self.assertEqual((d.action, d.exit_code), ("SELL", "RISK_LIMIT"))
        self.assertTrue(d.halt_trading)

    def test_break_even_covers_both_fees(self):
        even = strategy.break_even_price(60000.0, 0.004)
        cost = 1.0 * 60000.0 * 1.004
        proceeds = 1.0 * even * 0.996
        self.assertAlmostEqual(proceeds, cost, places=6)


if __name__ == "__main__":
    unittest.main()
