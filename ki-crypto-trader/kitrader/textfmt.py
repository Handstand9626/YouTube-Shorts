"""Deutsche Zahlen- und Zeitformatierung fuer Protokolltexte und Berichte."""
from __future__ import annotations

from datetime import datetime


def de_num(value: float, digits: int = 2) -> str:
    """1234.5 -> '1.234,50' (deutsche Schreibweise)."""
    if round(value, digits) == 0:
        value = 0.0  # vermeidet "-0,00"
    text = f"{value:,.{digits}f}"
    return text.replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")


def _minus(text: str) -> str:
    """Typografisches Minuszeichen fuer Fliesstext (nicht fuer CSV-Zahlen)."""
    return text.replace("-", "−")


def eur(value: float, digits: int = 2) -> str:
    return _minus(f"{de_num(value, digits)} €")


def signed_eur(value: float, digits: int = 2) -> str:
    sign = "+" if round(value, digits) > 0 else ""
    return _minus(f"{sign}{de_num(value, digits)} €")


def pct(value: float, digits: int = 2, signed: bool = True) -> str:
    sign = "+" if signed and round(value, digits) > 0 else ""
    return _minus(f"{sign}{de_num(value, digits)} %")


def btc(value: float) -> str:
    return f"{de_num(value, 8)} BTC"


def score_text(score: int) -> str:
    return _minus(f"{score:+d}") if score else "0"


def local_dt(ts: float, with_seconds: bool = True) -> str:
    """Zeitstempel in der lokalen Zeitzone des Rechners, z. B. 10.11.2026 16:35:02."""
    dt = datetime.fromtimestamp(ts).astimezone()
    return dt.strftime("%d.%m.%Y %H:%M:%S" if with_seconds else "%d.%m.%Y %H:%M")


def local_tz_name() -> str:
    dt = datetime.now().astimezone()
    offset = dt.strftime("%z")
    return f"UTC{offset[:3]}:{offset[3:]}" if offset else "lokale Zeit"


def duration_text(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours} Std. {minutes:02d} Min."
    if minutes:
        return f"{minutes} Min. {secs:02d} Sek."
    return f"{secs} Sek."
