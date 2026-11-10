#!/usr/bin/env python3
"""Rückblick-Test (Backtest) mit ECHTEN historischen BTC/EUR-Kursen.

    python backtest.py                 die letzten 72 Stunden nachspielen
    python backtest.py --stunden 24    kürzerer Zeitraum

Das Skript lädt echte 1-Minuten-Kurse der Börse Bitstamp, baut daraus die
Kerzen für die Indikatoren und lässt exakt dieselbe Engine wie im Live-Test
im Zeitraffer darüber laufen (eine Prüfung pro Minute). So lässt sich prüfen,
dass alles funktioniert, ohne 72 Stunden zu warten.

Wichtig: Ein Backtest ist KEIN Ersatz für den Live-Test und keine Prognose.
Er verändert den Live-Test nicht (eigene Datenbank nur im Arbeitsspeicher).
"""
from __future__ import annotations

import argparse
import bisect
import os
import sys
import time
from typing import List

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kitrader import report as report_mod  # noqa: E402
from kitrader.config import ALLOWED_CANDLE_MINUTES, Config  # noqa: E402
from kitrader.engine import Engine  # noqa: E402
from kitrader.marketdata import (Candle, MarketDataError, MarketSnapshot,  # noqa: E402
                                 MIN_CLOSED_CANDLES, http_get_json)
from kitrader.storage import Storage  # noqa: E402
from kitrader.textfmt import duration_text, eur, local_dt, pct, signed_eur  # noqa: E402

ASSUMED_SPREAD_PCT = 0.02   # historischer Geld-/Briefkurs ist nicht abrufbar -> Annahme


def fetch_minute_history(hours: float) -> List[Candle]:
    """Lädt 1-Minuten-Kerzen von Bitstamp, seitenweise rückwärts in die Vergangenheit."""
    needed = int(hours * 60) + 5
    end = int(time.time())
    by_time = {}
    while len(by_time) < needed:
        url = f"https://www.bitstamp.net/api/v2/ohlc/btceur/?step=60&limit=1000&end={end}"
        data, _ = http_get_json(url, timeout=20)
        rows = data["data"]["ohlc"]
        if not rows:
            break
        for r in rows:
            by_time[int(r["timestamp"])] = Candle(int(r["timestamp"]), float(r["open"]),
                                                  float(r["high"]), float(r["low"]),
                                                  float(r["close"]), float(r["volume"]))
        oldest = min(int(r["timestamp"]) for r in rows)
        if oldest >= end:
            break
        end = oldest - 60
        time.sleep(0.25)   # die öffentliche API nicht unnötig belasten
    return [by_time[t] for t in sorted(by_time)]


def aggregate(minutes: List[Candle], step: int) -> List[Candle]:
    """Fasst 1-Minuten-Kerzen zu Kerzen der Länge ``step`` Sekunden zusammen."""
    out: List[Candle] = []
    for c in minutes:
        bucket = c.t - c.t % step
        if out and out[-1].t == bucket:
            last = out[-1]
            last.h, last.l, last.c, last.v = max(last.h, c.h), min(last.l, c.l), c.c, last.v + c.v
        else:
            out.append(Candle(bucket, c.o, c.h, c.l, c.c, c.v))
    return out


class SimClock:
    def __init__(self, start: float):
        self.t = float(start)

    def __call__(self) -> float:
        return self.t


class ReplayData:
    """Liefert zu jedem simulierten Zeitpunkt nur Daten, die damals schon bekannt waren."""

    def __init__(self, minute_candles: List[Candle], candle_minutes: int, clock: SimClock):
        self.minute = minute_candles
        self.minute_close_times = [c.t + 60 for c in minute_candles]
        self.step = candle_minutes * 60
        self.candles = aggregate(minute_candles, self.step)
        self.close_times = [c.t + self.step for c in self.candles]
        self.clock = clock
        self.source_names = ["Bitstamp (historisch)"]

    def fetch(self, candle_minutes: int) -> MarketSnapshot:
        now = self.clock()
        closed_n = bisect.bisect_right(self.close_times, now)
        minute_n = bisect.bisect_right(self.minute_close_times, now)
        if closed_n < MIN_CLOSED_CANDLES or minute_n == 0:
            raise MarketDataError("Zu wenig Historie für diesen Zeitpunkt")
        price = self.minute[minute_n - 1].c
        half = price * ASSUMED_SPREAD_PCT / 200.0
        return MarketSnapshot(source="Bitstamp (historisch)", fetched_ts=now, price=price,
                              bid=price - half, ask=price + half,
                              candles=self.candles[max(0, closed_n - 400):closed_n], live=None,
                              candle_minutes=candle_minutes, latency_ms=0)


def run_backtest(minute_candles: List[Candle], cfg: Config, report_dir=None, quiet=False):
    """Spielt die Engine über die Historie ab. Gibt (engine, report) zurück."""
    warmup_s = (MIN_CLOSED_CANDLES + 2) * cfg.candle_seconds
    first, last = minute_candles[0].t, minute_candles[-1].t + 60
    start = last - cfg.duration_seconds
    if start - warmup_s < first:
        raise SystemExit("Nicht genug Historie geladen für diese Dauer und Kerzenlänge.")
    start -= start % 60

    clock = SimClock(start)
    data = ReplayData(minute_candles, cfg.candle_minutes, clock)
    engine = Engine(Storage(":memory:"), cfg, data_client=data, clock=clock, report_dir=report_dir)
    end_ts = engine.test["end_ts"]
    cycles = 0
    while clock.t < end_ts:
        engine.run_cycle()
        cycles += 1
        clock.t = min(clock.t + cfg.poll_seconds, end_ts)
        if not quiet and cycles % 720 == 0:
            print(f"  … {cycles} Analysen simuliert", flush=True)
    if not engine.finalize():
        raise SystemExit("Abschluss fehlgeschlagen (keine Kursdaten am Ende).")
    return engine, engine.storage.get_meta("final_report")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Backtest mit echten historischen BTC/EUR-Kursen.")
    parser.add_argument("--stunden", type=float, default=72.0, help="Zeitraum (Standard: 72)")
    parser.add_argument("--kerze", type=int, default=60, choices=ALLOWED_CANDLE_MINUTES)
    parser.add_argument("--intervall", type=int, default=60, help="Prüfabstand in Sekunden (60–300)")
    parser.add_argument("--ohne-dateien", action="store_true", help="keine Berichtsdateien schreiben")
    args = parser.parse_args(argv)

    cfg = Config(duration_hours=args.stunden, candle_minutes=args.kerze,
                 poll_seconds=args.intervall).validate()
    history_hours = args.stunden + (MIN_CLOSED_CANDLES + 4) * args.kerze / 60.0
    print(f"Lade echte 1-Minuten-Kurse (BTC/EUR, Bitstamp) für {history_hours:.0f} Stunden …", flush=True)
    try:
        minutes = fetch_minute_history(history_hours)
    except MarketDataError as exc:
        print(f"Kursdaten konnten nicht geladen werden: {exc}")
        return 1
    print(f"{len(minutes)} Minuten-Kerzen geladen: {local_dt(minutes[0].t)} bis {local_dt(minutes[-1].t)}")

    report_dir = None if args.ohne_dateien else os.path.join(HERE, "data", "backtest")
    started = time.time()
    engine, r = run_backtest(minutes, cfg, report_dir)
    print(f"Fertig in {time.time() - started:.1f} s.\n")

    print("=" * 66)
    print(" BACKTEST (Rückblick mit historischen Kursen – kein Live-Test)")
    print("=" * 66)
    print(f" Zeitraum          : {local_dt(r['start_ts'])} bis {local_dt(r['end_ts'])}")
    print(f" Startkapital      : {eur(r['start_capital'])}")
    print(f" Endkapital        : {eur(r['end_capital'], 4)}")
    print(f" Gewinn / Verlust  : {signed_eur(r['pnl_eur'], 4)} ({pct(r['return_pct'])})")
    bench = r.get("benchmark")
    if bench:
        print(f" Kaufen und Halten : {eur(bench['value'], 4)} ({pct(bench['return_pct'])})")
    print(f" Analysen          : {r['analyses']}   Signale: {r['signals']}")
    print(f" Orders            : {r['orders_total']} ({r['buys']} Käufe, {r['sells']} Verkäufe)")
    print(f" Abgeschl. Trades  : {r['closed_trades']} (erfolgreich {r['wins']}, erfolglos {r['losses']})")
    print(f" Gebühren          : {eur(r['fees_total'], 4)}")
    print(f" Max. Drawdown     : {eur(r['max_drawdown_eur'], 4)} ({pct(r['max_drawdown_pct'], signed=False)})")
    print(f" Bewertung         : {r['evaluation']['verdict']}")
    print("-" * 66)
    for t in engine.storage.get_trades():
        kind = "Kauf   " if t["side"] == "BUY" else "Verkauf"
        pnl = "" if t["pnl_eur"] is None else f"  G/V {signed_eur(t['pnl_eur'], 4)}"
        print(f" {local_dt(t['ts'], False)}  {kind} {eur(t['price'])}  {t['reason']}{pnl}")
    print("-" * 66)
    print(f" Annahmen: Gebühr {cfg.fee_rate * 100:.2f} % je Order, Spread {ASSUMED_SPREAD_PCT} %, "
          f"Dauer {duration_text(cfg.duration_seconds)}.")
    if report_dir:
        print(f" Berichtsdateien (PDF/CSV): {report_dir}")
    print(" Vergangene Ergebnisse sagen nichts über die Zukunft aus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
