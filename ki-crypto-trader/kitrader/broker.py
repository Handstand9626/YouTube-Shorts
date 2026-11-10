"""Paper-Broker: fuehrt ein rein virtuelles Konto.

Hier wird nichts an eine Boerse gesendet. ``buy`` und ``sell`` verrechnen nur
Zahlen im Speicher. Regeln, die technisch erzwungen werden:

* kein Hebel, kein Kredit: Ein Kauf darf samt Gebuehr nie mehr kosten als das
  freie Guthaben;
* kein Leerverkauf: Verkauft wird nur, was vorher (simuliert) gekauft wurde;
* Gebuehren werden bei jedem Kauf und Verkauf abgezogen;
* gekauft wird zum Briefkurs (ask), verkauft zum Geldkurs (bid) - also zu den
  Kursen, die man an der Boerse in diesem Moment tatsaechlich bekommen haette.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Optional

SATOSHI = 1e-8


class BrokerError(Exception):
    """Regelverstoss im simulierten Konto (z. B. Einsatz hoeher als Guthaben)."""


@dataclass
class Position:
    id: int
    entry_ts: float
    entry_price: float   # Kaufkurs (ask)
    btc: float
    stake_eur: float     # investierter Betrag ohne Gebuehr
    fee_eur: float       # Kaufgebuehr
    peak_price: float    # hoechster Verkaufskurs seit Einstieg
    source: str = ""

    @property
    def cost_eur(self) -> float:
        return self.stake_eur + self.fee_eur


class Portfolio:
    def __init__(self, start_capital: float, fee_rate: float):
        self.start_capital = float(start_capital)
        self.fee_rate = float(fee_rate)
        self.cash = float(start_capital)
        self.btc = 0.0
        self.position: Optional[Position] = None
        self.fees_total = 0.0
        self.realized_pnl = 0.0
        self.next_position_id = 1

    # -- Bewertung -----------------------------------------------------------
    def btc_value(self, price: float) -> float:
        return self.btc * price

    def equity(self, price: float) -> float:
        """Kontostand = freies Guthaben + Marktwert des BTC-Bestands."""
        return self.cash + self.btc * price

    # -- Simulierte Orders -----------------------------------------------------
    def buy(self, ts: float, ask: float, stake_eur: float, source: str = "") -> dict:
        if self.position is not None:
            raise BrokerError("Es ist bereits eine Position offen.")
        if ask <= 0 or stake_eur <= 0:
            raise BrokerError("Ungültiger Kurs oder Einsatz.")
        if stake_eur > self.start_capital + 1e-9:
            raise BrokerError("Einsatz übersteigt das Startkapital.")
        if stake_eur * (1.0 + self.fee_rate) > self.cash + 1e-9:
            raise BrokerError("Einsatz samt Gebühr übersteigt das freie Guthaben (kein Hebel).")
        # auf ganze Satoshi abrunden (Rundung davor faengt Gleitkomma-Ungenauigkeit ab)
        btc = math.floor(round(stake_eur / ask / SATOSHI, 4)) / 1e8
        if btc <= 0:
            raise BrokerError("Einsatz zu klein.")
        invested = btc * ask
        fee = invested * self.fee_rate
        self.cash -= invested + fee
        self.btc = btc
        self.fees_total += fee
        self.position = Position(id=self.next_position_id, entry_ts=ts, entry_price=ask, btc=btc,
                                 stake_eur=invested, fee_eur=fee, peak_price=ask, source=source)
        self.next_position_id += 1
        return {"side": "BUY", "ts": ts, "price": ask, "btc": btc, "invested_eur": invested,
                "proceeds_eur": None, "fee_eur": fee, "pnl_eur": None, "pnl_pct": None,
                "position_id": self.position.id, "cash_after": self.cash, "btc_after": self.btc}

    def sell(self, ts: float, bid: float) -> dict:
        pos = self.position
        if pos is None or self.btc <= 0:
            raise BrokerError("Keine Position zum Verkaufen (kein Leerverkauf).")
        if bid <= 0:
            raise BrokerError("Ungültiger Kurs.")
        gross = self.btc * bid
        fee = gross * self.fee_rate
        net = gross - fee
        pnl = net - pos.cost_eur
        pnl_pct = pnl / pos.cost_eur * 100.0 if pos.cost_eur else 0.0
        sold_btc = self.btc
        self.cash += net
        self.btc = 0.0
        self.fees_total += fee
        self.realized_pnl += pnl
        self.position = None
        return {"side": "SELL", "ts": ts, "price": bid, "btc": sold_btc,
                "invested_eur": pos.stake_eur, "proceeds_eur": gross, "fee_eur": fee,
                "pnl_eur": pnl, "pnl_pct": pnl_pct, "position_id": pos.id,
                "buy_fee_eur": pos.fee_eur, "entry_price": pos.entry_price, "entry_ts": pos.entry_ts,
                "cash_after": self.cash, "btc_after": self.btc}

    # -- Speicherung -----------------------------------------------------------
    def to_dict(self) -> dict:
        return {"start_capital": self.start_capital, "fee_rate": self.fee_rate, "cash": self.cash,
                "btc": self.btc, "fees_total": self.fees_total, "realized_pnl": self.realized_pnl,
                "next_position_id": self.next_position_id,
                "position": asdict(self.position) if self.position else None}

    @classmethod
    def from_dict(cls, data: dict) -> "Portfolio":
        portfolio = cls(data["start_capital"], data["fee_rate"])
        portfolio.cash = float(data["cash"])
        portfolio.btc = float(data["btc"])
        portfolio.fees_total = float(data.get("fees_total", 0.0))
        portfolio.realized_pnl = float(data.get("realized_pnl", 0.0))
        portfolio.next_position_id = int(data.get("next_position_id", 1))
        if data.get("position"):
            portfolio.position = Position(**data["position"])
        return portfolio
