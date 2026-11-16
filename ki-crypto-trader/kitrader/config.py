"""Zentrale Einstellungen des Paper-Trading-Tests.

Alle Werte werden beim Start eines Tests in der Datenbank gespeichert, damit
ein Neustart exakt mit denselben Regeln weiterlaeuft.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields

# Kerzenlaengen, die alle drei Datenquellen (Kraken, Coinbase, Bitstamp) liefern.
ALLOWED_CANDLE_MINUTES = (5, 15, 60)


@dataclass
class Config:
    # --- Grundeinstellungen -------------------------------------------------
    start_capital_eur: float = 20.0   # virtuelles Startkapital
    duration_hours: float = 72.0      # Testdauer
    poll_seconds: int = 60            # Abstand der Marktpruefungen (60-300 s)
    candle_minutes: int = 60          # Kerzenlaenge fuer die Indikatoren (5, 15 oder 60)

    # --- Kosten -------------------------------------------------------------
    fee_rate: float = 0.004           # 0,40 % Gebuehr je simulierter Order

    # --- Risikomanagement ---------------------------------------------------
    max_stake_fraction: float = 0.90  # max. Anteil des freien Guthabens je Kauf
    min_order_eur: float = 5.0        # darunter wird nicht gehandelt
    stop_loss_pct: float = 1.5        # Verkauf bei -1,5 % ab Einstieg
    take_profit_pct: float = 3.0      # Verkauf bei +3,0 % ab Einstieg
    trailing_start_pct: float = 1.5   # ab diesem Gewinn wird nachgezogen
    trailing_gap_pct: float = 0.8     # Abstand des nachgezogenen Stopps
    max_buys_per_24h: int = 6         # Schutz vor Ueberhandeln
    cooldown_candles: int = 2         # Pause nach einem Verkauf (in Kerzen)
    cooldown_after_stop_candles: int = 4  # laengere Pause nach Stop-Loss
    max_total_loss_pct: float = 15.0  # Notbremse: Handel stoppt bei -15 %
    no_entry_before_end_min: int = 30  # kein Einstieg kurz vor Testende
    max_spread_pct: float = 0.25      # groesserer Spread gilt als unplausibel

    # --- Strategie ----------------------------------------------------------
    buy_score_min: int = 3            # mind. +3 von 5 Signalen fuer einen Kauf
    sell_score_max: int = -2          # ab -2 wird eine Position verkauft
    entry_requires_uptrend: bool = True   # Kauf nur im bestaetigten Aufwaertstrend
    exit_requires_downtrend: bool = True  # Signal-Verkauf nur bei bestaetigtem Abwaertstrend
    exit_min_hold_candles: int = 2        # Signal-Verkauf fruehestens nach so vielen Kerzen
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    ema_fast: int = 20
    ema_slow: int = 50
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    volume_window: int = 20
    volume_confirm_ratio: float = 1.2
    momentum_candles: int = 3
    momentum_threshold_pct: float = 0.20

    def validate(self) -> "Config":
        if not 60 <= int(self.poll_seconds) <= 300:
            raise ValueError("Das Pruefintervall muss zwischen 60 und 300 Sekunden liegen.")
        if int(self.candle_minutes) not in ALLOWED_CANDLE_MINUTES:
            raise ValueError("Kerzenlaenge muss 5, 15 oder 60 Minuten sein.")
        if self.start_capital_eur <= 0:
            raise ValueError("Startkapital muss positiv sein.")
        if self.duration_hours <= 0:
            raise ValueError("Testdauer muss positiv sein.")
        if not 0 <= self.fee_rate < 0.05:
            raise ValueError("Gebuehrensatz unplausibel.")
        if not 0 < self.max_stake_fraction <= 1:
            raise ValueError("Der maximale Einsatz muss zwischen 0 und 100 % liegen.")
        return self

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (data or {}).items() if k in known})

    @property
    def candle_seconds(self) -> int:
        return int(self.candle_minutes) * 60

    @property
    def duration_seconds(self) -> float:
        return float(self.duration_hours) * 3600.0
