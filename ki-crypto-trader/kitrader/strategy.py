"""Handelsstrategie: fuenf Signale werden gemeinsam bewertet.

Die "KI" dieses Projekts ist ein nachvollziehbarer, regelbasierter Algorithmus.
Jedes der fuenf Signale liefert -1 (negativ), 0 (neutral) oder +1 (positiv):

  1. Trend            EMA 20 gegen EMA 50 und Lage des Kurses
  2. MACD             Histogramm und dessen Richtung
  3. RSI (14)         Momentum-Zone, ueberkauft / ueberverkauft
  4. Handelsvolumen   letzte Kerze gegen den Durchschnitt
  5. Kursbewegung     Veraenderung der letzten Kerzen bis jetzt

Gekauft wird nur, wenn die Summe mindestens ``buy_score_min`` erreicht, der
Trend nicht abwaerts zeigt und der RSI nicht ueberkauft ist - nie wegen eines
einzelnen Indikators. Jede Entscheidung enthaelt eine Begruendung im Klartext.

Die Funktionen hier sind rein (keine Ein-/Ausgabe) und damit testbar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from . import indicators as ind
from .config import Config
from .marketdata import Candle
from .textfmt import de_num, eur, pct, score_text

MIN_CANDLES_FOR_ANALYSIS = 60


@dataclass
class Signal:
    key: str
    name: str
    value: str     # gemessener Wert als Text
    score: int     # -1 / 0 / +1
    text: str      # Deutung im Klartext

    def to_dict(self) -> dict:
        return {"key": self.key, "name": self.name, "value": self.value,
                "score": self.score, "text": self.text}


@dataclass
class Analysis:
    price: float
    situation: str
    indicators: Dict[str, float]
    signals: List[Signal]
    score: int

    def signal(self, key: str) -> Signal:
        return next(s for s in self.signals if s.key == key)


@dataclass
class PositionView:
    entry_price: float
    peak_price: float
    stake_eur: float
    fee_eur: float
    btc: float
    entry_ts: float


@dataclass
class Context:
    """Alles, was die Entscheidung ausser der Marktanalyse wissen muss."""
    now: float
    end_ts: float
    cash: float
    equity: float
    start_capital: float
    bid: float
    ask: float
    position: Optional[PositionView] = None
    last_sell_ts: Optional[float] = None
    last_exit_code: str = ""
    buys_last_24h: int = 0
    halted: bool = False


@dataclass
class Decision:
    action: str                 # "NONE" | "BUY" | "SELL"
    label: str                  # "Kein Kauf" | "Kauf" | "Halten" | "Verkauf"
    signal_detected: bool
    signal_text: str
    reason: str
    risk_checks: List[dict] = field(default_factory=list)
    stake_eur: float = 0.0
    exit_code: str = ""         # STOP_LOSS | TAKE_PROFIT | TRAILING | SIGNAL | RISK_LIMIT
    halt_trading: bool = False


# ---------------------------------------------------------------------------
# Analyse
# ---------------------------------------------------------------------------

def analyze(candles: Sequence[Candle], price: float, cfg: Config) -> Analysis:
    """Berechnet Indikatoren aus ABGESCHLOSSENEN Kerzen und bewertet fuenf Signale.

    ``price`` ist der aktuelle Live-Kurs; er fliesst in Trend und Kursbewegung ein.
    """
    if len(candles) < MIN_CANDLES_FOR_ANALYSIS:
        raise ValueError("Zu wenige Kerzen fuer eine Analyse")
    closes = [c.c for c in candles]
    volumes = [c.v for c in candles]

    ema_fast = ind.ema(closes, cfg.ema_fast)[-1]
    ema_slow = ind.ema(closes, cfg.ema_slow)[-1]
    rsi_series = ind.rsi(closes, cfg.rsi_period)
    rsi_now, rsi_prev = rsi_series[-1], rsi_series[-2]
    macd_line, macd_signal, macd_hist = ind.macd(closes, cfg.macd_fast, cfg.macd_slow,
                                                 cfg.macd_signal)
    hist_now, hist_prev = macd_hist[-1], macd_hist[-2]
    if None in (ema_fast, ema_slow, rsi_now, rsi_prev, hist_now, hist_prev):
        raise ValueError("Indikatoren konnten nicht berechnet werden")

    window = volumes[-(cfg.volume_window + 1):-1]
    vol_avg = sum(window) / len(window) if window else 0.0
    vol_ratio = volumes[-1] / vol_avg if vol_avg > 0 else 0.0
    last = candles[-1]
    candle_up = last.c > last.o
    candle_down = last.c < last.o

    base = closes[-(cfg.momentum_candles + 1)]
    move_pct = (price / base - 1.0) * 100.0          # letzte n Kerzen bis jetzt
    live_pct = (price / closes[-1] - 1.0) * 100.0    # seit dem letzten Kerzenschluss
    ema_spread_pct = (ema_fast - ema_slow) / ema_slow * 100.0

    signals: List[Signal] = []

    # 1) Trend ----------------------------------------------------------------
    ema_value = (f"EMA {cfg.ema_fast}: {eur(ema_fast)} · EMA {cfg.ema_slow}: {eur(ema_slow)}")
    if ema_fast > ema_slow and price >= ema_fast:
        signals.append(Signal("trend", f"Trend (EMA {cfg.ema_fast} / EMA {cfg.ema_slow})", ema_value, 1,
                              f"EMA {cfg.ema_fast} liegt über EMA {cfg.ema_slow} und der Kurs über "
                              f"EMA {cfg.ema_fast}: Aufwärtstrend."))
    elif ema_fast < ema_slow and price < ema_fast:
        signals.append(Signal("trend", f"Trend (EMA {cfg.ema_fast} / EMA {cfg.ema_slow})", ema_value, -1,
                              f"EMA {cfg.ema_fast} liegt unter EMA {cfg.ema_slow} und der Kurs unter "
                              f"EMA {cfg.ema_fast}: Abwärtstrend."))
    else:
        if ema_fast > ema_slow:
            text = (f"EMA {cfg.ema_fast} über EMA {cfg.ema_slow}, aber der Kurs ist unter "
                    f"EMA {cfg.ema_fast} gefallen: Trend nicht bestätigt.")
        else:
            text = (f"EMA {cfg.ema_fast} unter EMA {cfg.ema_slow}, aber der Kurs liegt über "
                    f"EMA {cfg.ema_fast}: noch kein bestätigter Trendwechsel.")
        signals.append(Signal("trend", f"Trend (EMA {cfg.ema_fast} / EMA {cfg.ema_slow})", ema_value, 0, text))

    # 2) MACD -----------------------------------------------------------------
    macd_value = (f"MACD {de_num(macd_line[-1], 2)} · Signal {de_num(macd_signal[-1], 2)} · "
                  f"Histogramm {de_num(hist_now, 2)}")
    if hist_now > 0 and hist_now >= hist_prev:
        signals.append(Signal("macd", "MACD (12, 26, 9)", macd_value, 1,
                              "MACD über der Signallinie und das Histogramm wächst: "
                              "Aufwärtsdynamik nimmt zu."))
    elif hist_now < 0 and hist_now <= hist_prev:
        signals.append(Signal("macd", "MACD (12, 26, 9)", macd_value, -1,
                              "MACD unter der Signallinie und das Histogramm fällt: "
                              "Abwärtsdynamik nimmt zu."))
    elif hist_now > 0:
        signals.append(Signal("macd", "MACD (12, 26, 9)", macd_value, 0,
                              "MACD über der Signallinie, aber die Dynamik lässt nach."))
    else:
        signals.append(Signal("macd", "MACD (12, 26, 9)", macd_value, 0,
                              "MACD unter der Signallinie, aber die Abwärtsdynamik lässt nach."))

    # 3) RSI ------------------------------------------------------------------
    rsi_value = f"RSI {de_num(rsi_now, 1)}"
    if rsi_now >= cfg.rsi_overbought:
        signals.append(Signal("rsi", f"RSI ({cfg.rsi_period})", rsi_value, -1,
                              f"Über {de_num(cfg.rsi_overbought, 0)}: überkauft, erhöhtes Rückschlagrisiko."))
    elif rsi_now >= 55:
        signals.append(Signal("rsi", f"RSI ({cfg.rsi_period})", rsi_value, 1,
                              "Zwischen 55 und 70: positives Momentum, nicht überkauft."))
    elif rsi_now >= 45:
        signals.append(Signal("rsi", f"RSI ({cfg.rsi_period})", rsi_value, 0,
                              "Zwischen 45 und 55: neutral, keine klare Richtung."))
    elif rsi_now >= cfg.rsi_oversold:
        signals.append(Signal("rsi", f"RSI ({cfg.rsi_period})", rsi_value, -1,
                              "Zwischen 30 und 45: schwaches Momentum."))
    elif rsi_now > rsi_prev:
        signals.append(Signal("rsi", f"RSI ({cfg.rsi_period})", rsi_value, 1,
                              f"Unter {de_num(cfg.rsi_oversold, 0)} und steigend: überverkauft, "
                              "Gegenbewegung beginnt."))
    else:
        signals.append(Signal("rsi", f"RSI ({cfg.rsi_period})", rsi_value, 0,
                              f"Unter {de_num(cfg.rsi_oversold, 0)}: überverkauft, aber noch keine "
                              "Stabilisierung."))

    # 4) Volumen --------------------------------------------------------------
    vol_value = (f"{de_num(vol_ratio, 2)}-faches des Durchschnitts "
                 f"({de_num(volumes[-1], 3)} BTC, Ø {de_num(vol_avg, 3)} BTC)")
    if vol_ratio >= cfg.volume_confirm_ratio and candle_up:
        signals.append(Signal("volume", "Handelsvolumen", vol_value, 1,
                              "Überdurchschnittliches Volumen bei steigender Kerze: Kaufdruck bestätigt."))
    elif vol_ratio >= cfg.volume_confirm_ratio and candle_down:
        signals.append(Signal("volume", "Handelsvolumen", vol_value, -1,
                              "Überdurchschnittliches Volumen bei fallender Kerze: Verkaufsdruck."))
    else:
        signals.append(Signal("volume", "Handelsvolumen", vol_value, 0,
                              "Volumen unauffällig: keine Bestätigung für eine Bewegung."))

    # 5) Kurzfristige Kursbewegung ---------------------------------------------
    minutes = cfg.momentum_candles * cfg.candle_minutes
    move_value = (f"{pct(move_pct)} in ca. {minutes} Min. · {pct(live_pct)} seit letztem Kerzenschluss")
    threshold = cfg.momentum_threshold_pct
    if move_pct >= threshold and live_pct > -threshold / 2:
        signals.append(Signal("momentum", "Kurzfristige Kursbewegung", move_value, 1,
                              "Kurs steigt kurzfristig spürbar."))
    elif move_pct <= -threshold and live_pct < threshold / 2:
        signals.append(Signal("momentum", "Kurzfristige Kursbewegung", move_value, -1,
                              "Kurs fällt kurzfristig spürbar."))
    else:
        signals.append(Signal("momentum", "Kurzfristige Kursbewegung", move_value, 0,
                              "Keine deutliche kurzfristige Bewegung."))

    score = sum(s.score for s in signals)

    # Marktsituation in Worten ---------------------------------------------------
    if abs(ema_spread_pct) < 0.08 and abs(move_pct) < threshold:
        situation = "Seitwärtsbewegung"
    elif ema_fast > ema_slow:
        situation = "Aufwärtstrend" if price >= ema_fast else "Aufwärtstrend mit Rücksetzer"
    else:
        situation = "Abwärtstrend" if price < ema_fast else "Abwärtstrend mit Erholungsversuch"
    if rsi_now >= cfg.rsi_overbought:
        situation += ", überkauft"
    elif rsi_now <= cfg.rsi_oversold:
        situation += ", überverkauft"
    if vol_ratio >= 2.0:
        situation += ", hohes Volumen"

    return Analysis(
        price=price,
        situation=situation,
        indicators={
            "rsi": rsi_now, "rsi_prev": rsi_prev,
            "macd": macd_line[-1], "macd_signal": macd_signal[-1],
            "macd_hist": hist_now, "macd_hist_prev": hist_prev,
            "ema_fast": ema_fast, "ema_slow": ema_slow, "ema_spread_pct": ema_spread_pct,
            "volume": volumes[-1], "volume_avg": vol_avg, "volume_ratio": vol_ratio,
            "move_pct": move_pct, "live_pct": live_pct,
            "last_close": closes[-1], "last_candle_t": last.t,
        },
        signals=signals,
        score=score,
    )


# ---------------------------------------------------------------------------
# Entscheidung
# ---------------------------------------------------------------------------

def max_stake(cash: float, cfg: Config) -> float:
    """Hoechster erlaubter Einsatz: begrenzt durch Guthaben-Anteil UND Startkapital.

    Der Einsatz samt Gebuehr darf das freie Guthaben nie uebersteigen (kein Hebel,
    kein Kredit) und liegt nie ueber dem Startkapital.
    """
    by_fraction = cash * cfg.max_stake_fraction
    affordable = cash / (1.0 + cfg.fee_rate)
    return max(0.0, min(by_fraction, affordable, cfg.start_capital_eur))


def break_even_price(entry_price: float, fee_rate: float) -> float:
    """Kurs, ab dem ein Verkauf nach beiden Gebuehren ohne Verlust waere."""
    return entry_price * (1.0 + fee_rate) / (1.0 - fee_rate)


def _summary(analysis: Analysis) -> str:
    pos = [s.name for s in analysis.signals if s.score > 0]
    neg = [s.name for s in analysis.signals if s.score < 0]
    neu = [s.name for s in analysis.signals if s.score == 0]
    parts = []
    if pos:
        parts.append("positiv: " + ", ".join(pos))
    if neg:
        parts.append("negativ: " + ", ".join(neg))
    if neu:
        parts.append("neutral: " + ", ".join(neu))
    return "; ".join(parts)


def decide(analysis: Analysis, ctx: Context, cfg: Config) -> Decision:
    if ctx.position is not None:
        return _decide_in_position(analysis, ctx, cfg)
    return _decide_flat(analysis, ctx, cfg)


def _decide_flat(a: Analysis, ctx: Context, cfg: Config) -> Decision:
    rsi_now = a.indicators["rsi"]
    trend = a.signal("trend").score
    score_ok = a.score >= cfg.buy_score_min
    summary = _summary(a)

    if not score_ok:
        return Decision(
            "NONE", "Kein Kauf", False, "Kein Kaufsignal",
            f"Noch kein ausreichend starkes Kaufsignal vorhanden: Gesamtbewertung "
            f"{score_text(a.score)} von 5 (nötig: mindestens +{cfg.buy_score_min}). "
            f"Signale – {summary}.")
    if trend < 0:
        return Decision(
            "NONE", "Kein Kauf", False, "Kein Kaufsignal",
            f"Gesamtbewertung {score_text(a.score)} würde reichen, aber der übergeordnete Trend "
            f"zeigt abwärts (EMA {cfg.ema_fast} unter EMA {cfg.ema_slow}). Gegen den Trend wird "
            f"nicht gekauft. Signale – {summary}.")
    if cfg.entry_requires_uptrend and trend == 0:
        return Decision(
            "NONE", "Kein Kauf", False, "Kein Kaufsignal",
            f"Gesamtbewertung {score_text(a.score)} würde reichen, aber es liegt kein bestätigter "
            f"Aufwärtstrend vor (dafür müssen EMA {cfg.ema_fast} über EMA {cfg.ema_slow} und der Kurs "
            f"über EMA {cfg.ema_fast} liegen). Signale – {summary}.")
    if rsi_now >= cfg.rsi_overbought:
        return Decision(
            "NONE", "Kein Kauf", False, "Kein Kaufsignal",
            f"Gesamtbewertung {score_text(a.score)} würde reichen, aber der RSI ist mit "
            f"{de_num(rsi_now, 1)} überkauft. Kein Kauf in eine überhitzte Bewegung. "
            f"Signale – {summary}.")

    # Kaufsignal erkannt -> Risikopruefung entscheidet, ob wirklich gekauft wird.
    signal_text = (f"Kaufsignal: Gesamtbewertung {score_text(a.score)} von 5 "
                   f"(mindestens +{cfg.buy_score_min} nötig)")
    checks: List[dict] = []

    floor = cfg.start_capital_eur * (1.0 - cfg.max_total_loss_pct / 100.0)
    ok = not ctx.halted and ctx.equity > floor
    checks.append({"name": "Verlustlimit", "ok": ok,
                   "text": (f"Kontostand {eur(ctx.equity)} liegt über dem Limit {eur(floor)}." if ok else
                            f"Verlustlimit von {de_num(cfg.max_total_loss_pct, 0)} % erreicht – "
                            "es werden keine neuen Käufe mehr simuliert.")})

    ok = ctx.buys_last_24h < cfg.max_buys_per_24h
    checks.append({"name": "Handelshäufigkeit", "ok": ok,
                   "text": (f"{ctx.buys_last_24h} von maximal {cfg.max_buys_per_24h} Käufen in 24 Stunden."
                            if ok else
                            f"Bereits {ctx.buys_last_24h} Käufe in den letzten 24 Stunden "
                            f"(Maximum {cfg.max_buys_per_24h}).")})

    cooldown_candles = (cfg.cooldown_after_stop_candles if ctx.last_exit_code == "STOP_LOSS"
                        else cfg.cooldown_candles)
    cooldown_s = cooldown_candles * cfg.candle_seconds
    waited = None if ctx.last_sell_ts is None else ctx.now - ctx.last_sell_ts
    ok = waited is None or waited >= cooldown_s
    if waited is None:
        text = "Keine Wartezeit aktiv (noch kein vorheriger Verkauf)."
    elif ok:
        text = f"Wartezeit von {cooldown_s // 60} Min. nach dem letzten Verkauf ist abgelaufen."
    else:
        text = (f"Wartezeit nach dem letzten Verkauf läuft noch "
                f"({int((cooldown_s - waited) // 60) + 1} von {cooldown_s // 60} Min. verbleiben).")
    checks.append({"name": "Wartezeit nach Verkauf", "ok": ok, "text": text})

    remaining_min = (ctx.end_ts - ctx.now) / 60.0
    ok = remaining_min > cfg.no_entry_before_end_min
    checks.append({"name": "Restlaufzeit", "ok": ok,
                   "text": (f"Noch {int(remaining_min)} Min. bis zum Testende." if ok else
                            f"Weniger als {cfg.no_entry_before_end_min} Min. bis zum Testende – "
                            "kein neuer Einstieg mehr.")})

    spread_pct = (ctx.ask - ctx.bid) / a.price * 100.0
    ok = spread_pct <= cfg.max_spread_pct
    checks.append({"name": "Spread", "ok": ok,
                   "text": (f"Spread {de_num(spread_pct, 3)} % ist unauffällig." if ok else
                            f"Spread {de_num(spread_pct, 3)} % ist ungewöhnlich hoch "
                            f"(Grenze {de_num(cfg.max_spread_pct, 2)} %).")})

    stake = max_stake(ctx.cash, cfg)
    ok = stake >= cfg.min_order_eur
    checks.append({"name": "Einsatzgrenze", "ok": ok,
                   "text": (f"Einsatz {eur(stake)} = höchstens "
                            f"{de_num(cfg.max_stake_fraction * 100, 0)} % des freien Guthabens "
                            f"({eur(ctx.cash)}), nie mehr als {eur(cfg.start_capital_eur)}." if ok else
                            f"Möglicher Einsatz {eur(stake)} liegt unter der Mindestorder von "
                            f"{eur(cfg.min_order_eur)}.")})

    failed = [c for c in checks if not c["ok"]]
    if failed:
        return Decision(
            "NONE", "Kein Kauf", True, signal_text,
            "Kaufsignal erkannt, aber die Risikoprüfung hat den Kauf verhindert: "
            + " ".join(c["text"] for c in failed) + f" Signale – {summary}.",
            risk_checks=checks)

    return Decision(
        "BUY", "Kauf", True, signal_text,
        f"Mehrere Signale bestätigen sich gegenseitig (Gesamtbewertung {score_text(a.score)} von 5): "
        f"{summary}. Die Risikoprüfung ist bestanden. Simulierter Einsatz: {eur(stake)}.",
        risk_checks=checks, stake_eur=stake)


def _decide_in_position(a: Analysis, ctx: Context, cfg: Config) -> Decision:
    pos = ctx.position
    assert pos is not None
    bid = ctx.bid  # zu diesem Kurs koennte man jetzt verkaufen
    change_pct = (bid / pos.entry_price - 1.0) * 100.0
    stop_price = pos.entry_price * (1.0 - cfg.stop_loss_pct / 100.0)
    target_price = pos.entry_price * (1.0 + cfg.take_profit_pct / 100.0)
    trailing_active = pos.peak_price >= pos.entry_price * (1.0 + cfg.trailing_start_pct / 100.0)
    trail_price = pos.peak_price * (1.0 - cfg.trailing_gap_pct / 100.0)
    floor = cfg.start_capital_eur * (1.0 - cfg.max_total_loss_pct / 100.0)
    even = break_even_price(pos.entry_price, cfg.fee_rate)
    summary = _summary(a)

    checks = [
        {"name": "Verlustlimit", "ok": ctx.equity > floor,
         "text": f"Kontostand {eur(ctx.equity)} gegenüber Limit {eur(floor)}."},
        {"name": "Stop-Loss", "ok": bid > stop_price,
         "text": f"Verkaufskurs {eur(bid)} gegenüber Stop-Loss {eur(stop_price)} "
                 f"(−{de_num(cfg.stop_loss_pct, 1)} % ab Einstieg)."},
        {"name": "Take-Profit", "ok": bid < target_price,
         "text": f"Verkaufskurs {eur(bid)} gegenüber Gewinnziel {eur(target_price)} "
                 f"(+{de_num(cfg.take_profit_pct, 1)} % ab Einstieg)."},
        {"name": "Nachgezogener Stopp", "ok": not (trailing_active and bid <= trail_price),
         "text": (f"Aktiv: Höchstkurs {eur(pos.peak_price)}, Stopp bei {eur(trail_price)}."
                  if trailing_active else
                  f"Noch nicht aktiv (erst ab +{de_num(cfg.trailing_start_pct, 1)} % Gewinn).")},
    ]

    if ctx.equity <= floor:
        return Decision(
            "SELL", "Verkauf", True, "Verkaufssignal: Verlustlimit erreicht",
            f"Der Kontostand ({eur(ctx.equity)}) hat das Verlustlimit von "
            f"{de_num(cfg.max_total_loss_pct, 0)} % erreicht. Die Position wird geschlossen und der "
            "Handel für den Rest des Tests gestoppt.",
            risk_checks=checks, exit_code="RISK_LIMIT", halt_trading=True)
    if bid <= stop_price:
        return Decision(
            "SELL", "Verkauf", True, "Verkaufssignal: Stop-Loss erreicht",
            f"Stop-Loss ausgelöst: Der Verkaufskurs {eur(bid)} liegt {pct(change_pct)} gegenüber dem "
            f"Einstieg ({eur(pos.entry_price)}) und damit auf/unter dem Stop-Loss {eur(stop_price)}. "
            "Verlust wird begrenzt.",
            risk_checks=checks, exit_code="STOP_LOSS")
    if bid >= target_price:
        return Decision(
            "SELL", "Verkauf", True, "Verkaufssignal: Gewinnziel erreicht",
            f"Gewinnziel erreicht: Der Verkaufskurs {eur(bid)} liegt {pct(change_pct)} über dem "
            f"Einstieg ({eur(pos.entry_price)}). Gewinn wird realisiert.",
            risk_checks=checks, exit_code="TAKE_PROFIT")
    if trailing_active and bid <= trail_price:
        return Decision(
            "SELL", "Verkauf", True, "Verkaufssignal: nachgezogener Stopp erreicht",
            f"Nachgezogener Stopp ausgelöst: Nach dem Höchstkurs {eur(pos.peak_price)} ist der "
            f"Verkaufskurs auf {eur(bid)} gefallen (Stopp bei {eur(trail_price)}). Der bisherige "
            f"Gewinn ({pct(change_pct)} vor Gebühren) wird gesichert.",
            risk_checks=checks, exit_code="TRAILING")

    trend = a.signal("trend").score
    macd_score = a.signal("macd").score
    held_candles = (ctx.now - pos.entry_ts) / cfg.candle_seconds
    reversal = trend < 0 if cfg.exit_requires_downtrend else (trend < 0 or macd_score < 0)
    if (a.score <= cfg.sell_score_max and reversal
            and held_candles >= cfg.exit_min_hold_candles):
        return Decision(
            "SELL", "Verkauf", True,
            f"Verkaufssignal: Gesamtbewertung {score_text(a.score)} von 5 "
            f"(Verkauf ab {cfg.sell_score_max})",
            f"Mehrere Signale haben gedreht (Gesamtbewertung {score_text(a.score)} von 5): {summary}. "
            f"Die Position wird geschlossen, Stand {pct(change_pct)} gegenüber dem Einstieg "
            "(vor Gebühren).",
            risk_checks=checks, exit_code="SIGNAL")

    return Decision(
        "NONE", "Halten", False, "Kein Verkaufssignal",
        f"Die Position bleibt offen: Verkaufskurs {eur(bid)} = {pct(change_pct)} gegenüber dem "
        f"Einstieg ({eur(pos.entry_price)}). Stop-Loss ({eur(stop_price)}) und Gewinnziel "
        f"({eur(target_price)}) sind nicht erreicht; kein Verkaufssignal (Gesamtbewertung "
        f"{score_text(a.score)}, Verkauf erst ab {cfg.sell_score_max}). Gewinnschwelle inklusive "
        f"Gebühren: {eur(even)}.",
        risk_checks=checks)
