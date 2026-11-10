import unittest

from tests.helpers import make_candles
from kitrader.marketdata import (Candle, MarketDataClient, MarketDataError, build_snapshot)

NOW = 1_800_000_000 + 1234          # mitten in einer Stundenkerze
END = NOW - NOW % 3600              # Beginn der laufenden Kerze
TICKER = {"price": 60000.0, "bid": 59999.0, "ask": 60001.0}


def snapshot(candles=None, ticker=None, now=NOW):
    candles = make_candles(200, END) if candles is None else candles
    return build_snapshot("Test", candles, ticker or TICKER, 60, now_ref=now, fetched_ts=now)


class BuildSnapshotTests(unittest.TestCase):
    def test_valid_data(self):
        live = Candle(END, 60000, 60010, 59990, 60000, 1.0)
        snap = snapshot(make_candles(200, END) + [live])
        self.assertEqual(len(snap.candles), 200)
        self.assertEqual(snap.live.t, END)
        self.assertEqual(snap.candles[-1].t, END - 3600)
        self.assertTrue(all(a.t < b.t for a, b in zip(snap.candles, snap.candles[1:])))
        self.assertAlmostEqual(snap.spread_pct, 2 / 60000 * 100)

    def test_unsorted_and_duplicate_candles_are_cleaned(self):
        candles = make_candles(200, END)
        snap = snapshot(list(reversed(candles)) + candles[:5])
        self.assertEqual(len(snap.candles), 200)

    def test_stale_data_is_rejected(self):
        with self.assertRaisesRegex(MarketDataError, "veraltet"):
            snapshot(make_candles(200, END - 3 * 3600))

    def test_too_few_candles(self):
        with self.assertRaisesRegex(MarketDataError, "Zu wenige"):
            snapshot(make_candles(50, END))

    def test_bad_ticker_values(self):
        bad = [{"price": 0, "bid": 1, "ask": 2}, {"price": 60000, "bid": 60500, "ask": 60000},
               {"price": 60000, "bid": 59000, "ask": 61000}, {"price": 70000, "bid": 59999, "ask": 60001},
               {"price": 60000}, {"price": "x", "bid": 1, "ask": 2}]
        for ticker in bad:
            with self.assertRaises(MarketDataError, msg=str(ticker)):
                snapshot(ticker=ticker)

    def test_price_jump_against_candles_is_rejected(self):
        with self.assertRaisesRegex(MarketDataError, "Kurssprung"):
            snapshot(ticker={"price": 70000.0, "bid": 69999.0, "ask": 70001.0})

    def test_implausible_candle_is_rejected(self):
        candles = make_candles(200, END)
        candles[100].c = -5.0
        with self.assertRaises(MarketDataError):
            snapshot(candles)

    def test_small_gap_is_filled_with_flat_zero_volume_candles(self):
        candles = make_candles(200, END)
        removed = candles[150:152]
        del candles[150:152]
        snap = snapshot(candles)
        self.assertEqual(snap.filled_gaps, 2)
        filled = [c for c in snap.candles if c.t in {r.t for r in removed}]
        self.assertEqual(len(filled), 2)
        self.assertTrue(all(c.v == 0.0 and c.o == c.c == c.h == c.l for c in filled))

    def test_large_recent_gap_is_rejected(self):
        candles = make_candles(200, END)
        del candles[150:160]
        with self.assertRaisesRegex(MarketDataError, "Luecke"):
            snapshot(candles)


class GoodSource:
    name = "Gut"

    def fetch_raw(self, minutes, http):
        return make_candles(200, END), dict(TICKER), float(NOW)


class BrokenSource:
    name = "Kaputt"

    def fetch_raw(self, minutes, http):
        raise MarketDataError("nicht erreichbar")


class WrongFormatSource:
    name = "Format"

    def fetch_raw(self, minutes, http):
        return {}["fehlt"]


class ClientTests(unittest.TestCase):
    def test_fallback_to_next_source(self):
        client = MarketDataClient(sources=[BrokenSource(), WrongFormatSource(), GoodSource()],
                                  clock=lambda: float(NOW))
        self.assertEqual(client.fetch(60).source, "Gut")
        self.assertEqual(client.source_names, ["Kaputt", "Format", "Gut"])

    def test_all_sources_failing_raises_and_names_them(self):
        client = MarketDataClient(sources=[BrokenSource(), WrongFormatSource()],
                                  clock=lambda: float(NOW))
        with self.assertRaises(MarketDataError) as caught:
            client.fetch(60)
        self.assertIn("Kaputt", str(caught.exception))
        self.assertIn("Unerwartetes Antwortformat", str(caught.exception))

    def test_exchange_time_is_used_when_local_clock_is_wrong(self):
        client = MarketDataClient(sources=[GoodSource()], clock=lambda: float(NOW) + 7200)
        snap = client.fetch(60)
        self.assertAlmostEqual(snap.clock_skew_s, -7200.0)


if __name__ == "__main__":
    unittest.main()
