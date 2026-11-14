"""Technische Indikatoren (reines Python, keine Abhaengigkeiten).

Alle Funktionen liefern Listen in der Laenge der Eingabe; Stellen, fuer die
noch nicht genug Daten vorliegen, sind ``None``.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

Series = List[Optional[float]]


def sma(values: Sequence[float], period: int) -> Series:
    n = len(values)
    out: Series = [None] * n
    if period <= 0 or n < period:
        return out
    window = sum(values[:period])
    out[period - 1] = window / period
    for i in range(period, n):
        window += values[i] - values[i - period]
        out[i] = window / period
    return out


def ema(values: Sequence[float], period: int) -> Series:
    """Exponentieller gleitender Durchschnitt, Startwert = SMA der ersten Periode."""
    n = len(values)
    out: Series = [None] * n
    if period <= 0 or n < period:
        return out
    k = 2.0 / (period + 1.0)
    current = sum(values[:period]) / period
    out[period - 1] = current
    for i in range(period, n):
        current = values[i] * k + current * (1.0 - k)
        out[i] = current
    return out


def rsi(values: Sequence[float], period: int = 14) -> Series:
    """Relative-Staerke-Index nach Wilder (geglaettete Durchschnitte)."""
    n = len(values)
    out: Series = [None] * n
    if period <= 0 or n <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        delta = values[i] - values[i - 1]
        if delta > 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for i in range(period + 1, n):
        delta = values[i] - values[i - 1]
        gain = delta if delta > 0 else 0.0
        loss = -delta if delta < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_gain == 0 and avg_loss == 0:
        return 50.0  # keinerlei Bewegung: neutral
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def macd(values: Sequence[float], fast: int = 12, slow: int = 26,
         signal: int = 9) -> Tuple[Series, Series, Series]:
    """MACD-Linie, Signallinie und Histogramm."""
    n = len(values)
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)
    line: Series = [None] * n
    for i in range(n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            line[i] = ema_fast[i] - ema_slow[i]
    valid = [x for x in line if x is not None]
    offset = n - len(valid)
    signal_valid = ema(valid, signal)
    signal_line: Series = [None] * offset + signal_valid
    hist: Series = [None] * n
    for i in range(n):
        if line[i] is not None and signal_line[i] is not None:
            hist[i] = line[i] - signal_line[i]
    return line, signal_line, hist
