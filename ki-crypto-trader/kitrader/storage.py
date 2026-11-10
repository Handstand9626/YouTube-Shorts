"""Dauerhafte Speicherung in einer SQLite-Datei.

Jeder Analysezyklus wird in EINER Transaktion gespeichert (Entscheidung, Trade,
Kontostand, Zaehler). Bricht das Programm mittendrin ab, bleibt der letzte
vollstaendige Zustand erhalten und wird beim Neustart wiederhergestellt.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Iterator, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL NOT NULL,
    kind            TEXT NOT NULL,      -- ANALYSIS | DATA_ERROR | FINAL
    price           REAL,
    source          TEXT,
    situation       TEXT,
    score           INTEGER,
    signal_detected INTEGER NOT NULL DEFAULT 0,
    action          TEXT NOT NULL,      -- NONE | BUY | SELL
    decision        TEXT NOT NULL,
    reason          TEXT NOT NULL,
    result          TEXT NOT NULL,
    stage           INTEGER NOT NULL,   -- hoechste erreichte Stufe 0-5
    trade_id        INTEGER,
    detail          TEXT NOT NULL       -- JSON: Indikatoren, Signale, Risiko, Schritte
);
CREATE TABLE IF NOT EXISTS trades (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    side         TEXT NOT NULL,         -- BUY | SELL (immer simuliert)
    price        REAL NOT NULL,         -- Ausfuehrungskurs (ask bzw. bid)
    market_price REAL NOT NULL,         -- letzter gehandelter Kurs
    btc          REAL NOT NULL,
    invested_eur REAL NOT NULL,
    proceeds_eur REAL,
    fee_eur      REAL NOT NULL,
    pnl_eur      REAL,
    pnl_pct      REAL,
    cash_after   REAL NOT NULL,
    btc_after    REAL NOT NULL,
    equity_after REAL NOT NULL,
    reason       TEXT NOT NULL,
    exit_code    TEXT,
    source       TEXT NOT NULL,
    position_id  INTEGER,
    decision_id  INTEGER
);
CREATE TABLE IF NOT EXISTS equity (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts     REAL NOT NULL,
    price  REAL NOT NULL,
    equity REAL NOT NULL,
    cash   REAL NOT NULL,
    btc    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      REAL NOT NULL,
    level   TEXT NOT NULL,              -- info | warn | error | trade
    code    TEXT NOT NULL,
    message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_decisions_stage ON decisions(stage);
CREATE INDEX IF NOT EXISTS idx_decisions_kind ON decisions(kind);
"""

DECISION_FILTERS = {
    "all": "1=1",
    "signal": "signal_detected = 1",
    "trade": "action != 'NONE'",
    "error": "kind = 'DATA_ERROR'",
}


class Storage:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            if path != ":memory:":
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Alles oder nichts: bei einem Fehler wird nichts gespeichert."""
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise
            else:
                self._conn.execute("COMMIT")

    # -- meta ------------------------------------------------------------------
    def get_meta(self, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def set_meta(self, key: str, value: Any) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, json.dumps(value, ensure_ascii=False)))

    # -- Schreiben ---------------------------------------------------------------
    def add_decision(self, row: dict) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO decisions(ts, kind, price, source, situation, score, signal_detected, "
                "action, decision, reason, result, stage, trade_id, detail) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (row["ts"], row["kind"], row.get("price"), row.get("source"), row.get("situation"),
                 row.get("score"), 1 if row.get("signal_detected") else 0, row["action"],
                 row["decision"], row["reason"], row["result"], row["stage"], row.get("trade_id"),
                 json.dumps(row.get("detail", {}), ensure_ascii=False)))
            return int(cur.lastrowid)

    def set_decision_trade(self, decision_id: int, trade_id: int) -> None:
        with self._lock:
            self._conn.execute("UPDATE decisions SET trade_id = ? WHERE id = ?",
                               (trade_id, decision_id))

    def add_trade(self, row: dict) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO trades(ts, side, price, market_price, btc, invested_eur, proceeds_eur, "
                "fee_eur, pnl_eur, pnl_pct, cash_after, btc_after, equity_after, reason, exit_code, "
                "source, position_id, decision_id) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (row["ts"], row["side"], row["price"], row["market_price"], row["btc"],
                 row["invested_eur"], row.get("proceeds_eur"), row["fee_eur"], row.get("pnl_eur"),
                 row.get("pnl_pct"), row["cash_after"], row["btc_after"], row["equity_after"],
                 row["reason"], row.get("exit_code"), row["source"], row.get("position_id"),
                 row.get("decision_id")))
            return int(cur.lastrowid)

    def add_equity(self, ts: float, price: float, equity: float, cash: float, btc: float) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO equity(ts, price, equity, cash, btc) VALUES(?, ?, ?, ?, ?)",
                (ts, price, equity, cash, btc))
            return int(cur.lastrowid)

    def add_event(self, ts: float, level: str, code: str, message: str) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO events(ts, level, code, message) VALUES(?, ?, ?, ?)",
                (ts, level, code, message))
            return int(cur.lastrowid)

    # -- Lesen -------------------------------------------------------------------
    @staticmethod
    def _decision_dict(row: sqlite3.Row) -> dict:
        data = dict(row)
        data["signal_detected"] = bool(data["signal_detected"])
        data["detail"] = json.loads(data["detail"]) if data.get("detail") else {}
        return data

    def get_decisions(self, limit: int = 50, before_id: Optional[int] = None,
                      after_id: Optional[int] = None, flt: str = "all") -> List[dict]:
        where = [DECISION_FILTERS.get(flt, DECISION_FILTERS["all"])]
        params: list = []
        if before_id is not None:
            where.append("id < ?")
            params.append(before_id)
        if after_id is not None:
            where.append("id > ?")
            params.append(after_id)
        params.append(max(1, min(int(limit), 500)))
        with self._lock:
            rows = self._conn.execute(
                f"SELECT * FROM decisions WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT ?",
                params).fetchall()
        return [self._decision_dict(r) for r in rows]

    def iter_decisions(self) -> List[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM decisions ORDER BY id ASC").fetchall()
        return [self._decision_dict(r) for r in rows]

    def get_decision(self, decision_id: int) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM decisions WHERE id = ?",
                                     (decision_id,)).fetchone()
        return self._decision_dict(row) if row else None

    def count_decisions(self, flt: str = "all") -> int:
        with self._lock:
            row = self._conn.execute(
                f"SELECT COUNT(*) AS n FROM decisions WHERE {DECISION_FILTERS.get(flt, '1=1')}"
            ).fetchone()
        return int(row["n"])

    def get_trades(self) -> List[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM trades ORDER BY id ASC").fetchall()
        return [dict(r) for r in rows]

    def get_equity(self, after_id: int = 0) -> List[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, ts, price, equity, cash, btc FROM equity WHERE id > ? ORDER BY id ASC",
                (after_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_events(self, limit: int = 50) -> List[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 500)),)).fetchall()
        return [dict(r) for r in rows]

    def max_id(self, table: str) -> int:
        if table not in ("decisions", "trades", "equity", "events"):
            raise ValueError(table)
        with self._lock:
            row = self._conn.execute(f"SELECT COALESCE(MAX(id), 0) AS n FROM {table}").fetchone()
        return int(row["n"])
