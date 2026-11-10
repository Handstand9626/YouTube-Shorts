"""Hilfen fuer die automatischen Tests.

Die hier erzeugten Kurse sind kuenstliche Testdaten. Sie werden ausschliesslich
in den Tests verwendet - das Programm selbst arbeitet nur mit echten Kursen.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kitrader.marketdata import Candle, MarketDataError, MarketSnapshot  # noqa: E402
from kitrader.strategy import Analysis, Signal  # noqa: E402

STEP = 3600


class SimClock:
    def __init__(self, start: float = 1_800_000_000.0):
        self.t = float(start)

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def make_candles(count: int, end_t: int, step: int = STEP, base: float = 60000.0,
                 pattern=(0.0,), volume: float = 10.0):
    """``pattern`` = prozentuale Veraenderung je Kerze, wird zyklisch wiederholt."""
    candles = []
    price = base
    start = end_t - count * step
    for i in range(count):
        change = pattern[i % len(pattern)] / 100.0
        open_, close = price, price * (1.0 + change)
        candles.append(Candle(start + i * step, open_, max(open_, close) * 1.0005,
                              min(open_, close) * 0.9995, close, volume))
        price = close
    return candles


class FakeData:
    """Datenquelle fuer Tests: liefert vorgegebene Kerzen und einen einstellbaren Kurs."""
    source_names = ["Testquelle"]

    def __init__(self, clock: SimClock, base: float = 60000.0):
        self.clock = clock
        self.price = base
        self.spread = 2.0
        self.fail = None          # Fehlermeldung -> MarketDataError
        self.calls = 0
        self.fine_candles = None  # optionale 5-Minuten-Kerzen fuer verspaeteten Abschluss

    def fetch(self, candle_minutes: int) -> MarketSnapshot:
        self.calls += 1
        if self.fail:
            raise MarketDataError(self.fail)
        now = self.clock()
        step = candle_minutes * 60
        if candle_minutes == 5 and self.fine_candles is not None:
            candles = [c for c in self.fine_candles if c.t + step <= now]
        else:
            end_t = int(now) - int(now) % step
            candles = make_candles(150, end_t, step, base=self.price)
        return MarketSnapshot(source="Testquelle", fetched_ts=now, price=self.price,
                              bid=self.price - self.spread / 2, ask=self.price + self.spread / 2,
                              candles=candles, live=None, candle_minutes=candle_minutes,
                              latency_ms=5)


def make_analysis(price: float, trend=0, macd=0, rsi=0, volume=0, momentum=0,
                  rsi_value: float = 55.0) -> Analysis:
    """Baut eine Analyse mit vorgegebenen Signalwerten (fuer Entscheidungstests)."""
    scores = {"trend": trend, "macd": macd, "rsi": rsi, "volume": volume, "momentum": momentum}
    names = {"trend": "Trend (EMA 20 / EMA 50)", "macd": "MACD (12, 26, 9)", "rsi": "RSI (14)",
             "volume": "Handelsvolumen", "momentum": "Kurzfristige Kursbewegung"}
    signals = [Signal(k, names[k], "Testwert", v, "Testtext") for k, v in scores.items()]
    return Analysis(price=price, situation="Testsituation",
                    indicators={"rsi": rsi_value, "rsi_prev": rsi_value, "macd": 0.0,
                                "macd_signal": 0.0, "macd_hist": 0.0, "macd_hist_prev": 0.0,
                                "ema_fast": price, "ema_slow": price, "ema_spread_pct": 0.0,
                                "volume": 1.0, "volume_avg": 1.0, "volume_ratio": 1.0,
                                "move_pct": 0.0, "live_pct": 0.0, "last_close": price,
                                "last_candle_t": 0},
                    signals=signals, score=sum(scores.values()))
