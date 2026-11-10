"""Echte BTC/EUR-Kursdaten aus oeffentlichen Boersen-APIs (nur lesend).

Quellen in dieser Reihenfolge: Kraken, Coinbase, Bitstamp. Es werden
ausschliesslich oeffentliche Marktdaten per HTTP GET abgerufen - ohne Konto,
ohne API-Schluessel, ohne jede Moeglichkeit, Orders zu senden.

Jede Antwort wird streng geprueft. Schlaegt eine Pruefung fehl, wird eine
``MarketDataError`` ausgeloest; der Aufrufer darf dann NICHT handeln. Es werden
niemals Kurse geschaetzt oder erfunden.
"""
from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Callable, Dict, List, Optional, Tuple

USER_AGENT = "ki-crypto-trader/1.0 (paper trading; public market data only)"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MIN_CLOSED_CANDLES = 120      # genug Vorlauf fuer EMA 50 und MACD
MAX_KEPT_CANDLES = 600
MAX_FILLABLE_GAP = 3          # fehlende Kerzen (kein Handel) hoechstens so oft auffuellen
MAX_TICKER_SPREAD_PCT = 1.0
MAX_PRICE_VS_CANDLE_PCT = 8.0


class MarketDataError(Exception):
    """Kursdaten fehlen, sind veraltet oder unplausibel."""


@dataclass
class Candle:
    t: int      # Beginn der Kerze (Unix-Sekunden)
    o: float
    h: float
    l: float
    c: float
    v: float    # gehandeltes Volumen in BTC


@dataclass
class MarketSnapshot:
    source: str
    fetched_ts: float           # lokale Uhrzeit des Abrufs
    price: float                # letzter gehandelter Kurs
    bid: float                  # bester Kaufkurs im Orderbuch (zu dem man verkauft)
    ask: float                  # bester Verkaufskurs im Orderbuch (zu dem man kauft)
    candles: List[Candle]       # nur ABGESCHLOSSENE Kerzen, alt -> neu
    live: Optional[Candle]      # laufende, noch nicht abgeschlossene Kerze
    candle_minutes: int
    latency_ms: int
    clock_skew_s: float = 0.0   # Abweichung lokale Uhr <-> Boersenzeit
    filled_gaps: int = 0        # aufgefuellte Kerzen ohne Handel

    @property
    def spread_pct(self) -> float:
        return (self.ask - self.bid) / self.price * 100.0 if self.price else 0.0


HttpGet = Callable[[str], Tuple[object, Optional[float]]]


def http_get_json(url: str, timeout: float = 10.0) -> Tuple[object, Optional[float]]:
    """GET -> (JSON, Serverzeit aus dem Date-Header oder None)."""
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise MarketDataError(f"HTTP-Status {response.status}")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            date_header = response.headers.get("Date")
    except MarketDataError:
        raise
    except urllib.error.HTTPError as exc:
        raise MarketDataError(f"HTTP-Fehler {exc.code}") from exc
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise MarketDataError(f"Verbindung fehlgeschlagen ({reason})") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise MarketDataError("Antwort zu gross")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise MarketDataError("Antwort ist kein gueltiges JSON") from exc
    server_ts = None
    if date_header:
        try:
            server_ts = parsedate_to_datetime(date_header).timestamp()
        except (TypeError, ValueError):
            server_ts = None
    return data, server_ts


# ---------------------------------------------------------------------------
# Datenquellen
# ---------------------------------------------------------------------------

class KrakenSource:
    name = "Kraken"

    def fetch_raw(self, minutes: int, http: HttpGet):
        ohlc, _ = http(f"https://api.kraken.com/0/public/OHLC?pair=XBTEUR&interval={minutes}")
        if ohlc.get("error"):
            raise MarketDataError(f"API-Fehler: {ohlc['error']}")
        result = ohlc["result"]
        key = next(k for k in result if k != "last")
        candles = [Candle(int(r[0]), float(r[1]), float(r[2]), float(r[3]),
                          float(r[4]), float(r[6])) for r in result[key]]
        tick, server_ts = http("https://api.kraken.com/0/public/Ticker?pair=XBTEUR")
        if tick.get("error"):
            raise MarketDataError(f"API-Fehler: {tick['error']}")
        t = next(iter(tick["result"].values()))
        ticker = {"price": float(t["c"][0]), "bid": float(t["b"][0]), "ask": float(t["a"][0])}
        return candles, ticker, server_ts


class CoinbaseSource:
    name = "Coinbase"

    def fetch_raw(self, minutes: int, http: HttpGet):
        rows, _ = http("https://api.exchange.coinbase.com/products/BTC-EUR/candles"
                       f"?granularity={minutes * 60}")
        # Format: [Zeit, Tief, Hoch, Eroeffnung, Schluss, Volumen], neueste zuerst
        candles = [Candle(int(r[0]), float(r[3]), float(r[2]), float(r[1]),
                          float(r[4]), float(r[5])) for r in rows]
        t, server_ts = http("https://api.exchange.coinbase.com/products/BTC-EUR/ticker")
        ticker = {"price": float(t["price"]), "bid": float(t["bid"]), "ask": float(t["ask"])}
        return candles, ticker, server_ts


class BitstampSource:
    name = "Bitstamp"

    def fetch_raw(self, minutes: int, http: HttpGet):
        data, _ = http("https://www.bitstamp.net/api/v2/ohlc/btceur/"
                       f"?step={minutes * 60}&limit=400")
        candles = [Candle(int(r["timestamp"]), float(r["open"]), float(r["high"]),
                          float(r["low"]), float(r["close"]), float(r["volume"]))
                   for r in data["data"]["ohlc"]]
        t, server_ts = http("https://www.bitstamp.net/api/v2/ticker/btceur/")
        ticker = {"price": float(t["last"]), "bid": float(t["bid"]), "ask": float(t["ask"])}
        return candles, ticker, server_ts


DEFAULT_SOURCES = (KrakenSource, CoinbaseSource, BitstampSource)


# ---------------------------------------------------------------------------
# Pruefung und Aufbereitung
# ---------------------------------------------------------------------------

def build_snapshot(source: str, raw_candles: List[Candle], ticker: Dict[str, float],
                   candle_minutes: int, now_ref: float, fetched_ts: float,
                   latency_ms: int = 0, clock_skew_s: float = 0.0) -> MarketSnapshot:
    """Prueft Rohdaten und liefert einen verlaesslichen Schnappschuss.

    ``now_ref`` ist die Referenzzeit (Boersenzeit, falls bekannt), nach der
    entschieden wird, welche Kerzen abgeschlossen sind und ob Daten veraltet sind.
    """
    step = candle_minutes * 60
    if not raw_candles:
        raise MarketDataError("Keine Kerzendaten erhalten")

    by_time: Dict[int, Candle] = {}
    for candle in raw_candles:
        if not (candle.o > 0 and candle.h > 0 and candle.l > 0 and candle.c > 0):
            raise MarketDataError("Unplausible Kerze (Kurs <= 0)")
        if candle.v < 0 or candle.h + 1e-9 < candle.l:
            raise MarketDataError("Unplausible Kerze (Hoch/Tief/Volumen)")
        if candle.t % step != 0:
            raise MarketDataError("Kerzenzeit passt nicht zum Intervall")
        if candle.t > now_ref + step:
            continue  # liegt in der Zukunft: nicht verwenden
        by_time[candle.t] = candle
    ordered = [by_time[t] for t in sorted(by_time)][-MAX_KEPT_CANDLES:]
    if not ordered:
        raise MarketDataError("Keine verwertbaren Kerzen erhalten")

    # Luecken: Intervalle ohne Handel fehlen bei manchen Boersen. Solche Kerzen
    # sind flach (Kurs unveraendert, Volumen 0) - das ist eine Tatsache, keine
    # Schaetzung. Groessere Luecken gelten als Datenfehler.
    filled: List[Candle] = [ordered[0]]
    gaps = 0
    for index in range(1, len(ordered)):
        candle = ordered[index]
        missing = (candle.t - filled[-1].t) // step - 1
        if missing > MAX_FILLABLE_GAP:
            if len(ordered) - index <= MIN_CLOSED_CANDLES + 5:
                raise MarketDataError(f"Luecke von {missing} Kerzen in den Kursdaten")
            filled = []  # alte Luecke ausserhalb des benoetigten Fensters: neu beginnen
            gaps = 0
        elif missing > 0:
            prev = filled[-1]
            for i in range(1, missing + 1):
                filled.append(Candle(prev.t + i * step, prev.c, prev.c, prev.c, prev.c, 0.0))
                gaps += 1
        filled.append(candle)

    closed = [c for c in filled if c.t + step <= now_ref]
    live = next((c for c in filled if c.t <= now_ref < c.t + step), None)
    if len(closed) < MIN_CLOSED_CANDLES:
        raise MarketDataError(
            f"Zu wenige abgeschlossene Kerzen ({len(closed)} von mindestens {MIN_CLOSED_CANDLES})")

    age = now_ref - (closed[-1].t + step)
    if age > step + 180:
        raise MarketDataError(
            f"Kursdaten veraltet (letzte abgeschlossene Kerze ist {int(age // 60)} Min. alt)")

    try:
        price, bid, ask = float(ticker["price"]), float(ticker["bid"]), float(ticker["ask"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MarketDataError("Ticker unvollstaendig") from exc
    if not (price > 0 and bid > 0 and ask > 0):
        raise MarketDataError("Ticker unplausibel (Kurs <= 0)")
    if bid > ask * 1.0005:
        raise MarketDataError("Ticker unplausibel (Geldkurs ueber Briefkurs)")
    spread_pct = (ask - bid) / price * 100.0
    if spread_pct > MAX_TICKER_SPREAD_PCT:
        raise MarketDataError(f"Ticker unplausibel (Spread {spread_pct:.2f} %)")
    if not (bid * 0.995 <= price <= ask * 1.005):
        raise MarketDataError("Ticker unplausibel (letzter Kurs weit ausserhalb des Orderbuchs)")
    deviation = abs(price / closed[-1].c - 1.0) * 100.0
    if deviation > MAX_PRICE_VS_CANDLE_PCT:
        raise MarketDataError(
            f"Kurssprung unplausibel ({deviation:.1f} % gegenueber der letzten Kerze)")

    return MarketSnapshot(source=source, fetched_ts=fetched_ts, price=price, bid=bid, ask=ask,
                          candles=closed, live=live, candle_minutes=candle_minutes,
                          latency_ms=latency_ms, clock_skew_s=clock_skew_s, filled_gaps=gaps)


class MarketDataClient:
    """Fragt die Quellen der Reihe nach ab und liefert den ersten gueltigen Schnappschuss."""

    def __init__(self, sources=None, clock: Callable[[], float] = time.time,
                 http: HttpGet = http_get_json):
        self.sources = list(sources) if sources is not None else [cls() for cls in DEFAULT_SOURCES]
        self.clock = clock
        self.http = http

    @property
    def source_names(self) -> List[str]:
        return [s.name for s in self.sources]

    def fetch(self, candle_minutes: int) -> MarketSnapshot:
        errors = []
        for source in self.sources:
            try:
                return self._fetch_from(source, candle_minutes)
            except MarketDataError as exc:
                errors.append(f"{source.name}: {exc}")
        raise MarketDataError("Keine Datenquelle lieferte gueltige Kursdaten – " + " | ".join(errors))

    def _fetch_from(self, source, candle_minutes: int) -> MarketSnapshot:
        started = self.clock()
        try:
            candles, ticker, server_ts = source.fetch_raw(candle_minutes, self.http)
        except MarketDataError:
            raise
        except (KeyError, IndexError, TypeError, ValueError, AttributeError, StopIteration) as exc:
            raise MarketDataError(f"Unerwartetes Antwortformat ({type(exc).__name__})") from exc
        finished = self.clock()
        skew = (server_ts - finished) if server_ts is not None else 0.0
        now_ref = server_ts if server_ts is not None else finished
        return build_snapshot(source.name, candles, ticker, candle_minutes, now_ref=now_ref,
                              fetched_ts=finished,
                              latency_ms=int(round((finished - started) * 1000)),
                              clock_skew_s=skew)
