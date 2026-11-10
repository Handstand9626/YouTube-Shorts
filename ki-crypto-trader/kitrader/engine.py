"""Die Engine: steuert den automatischen 72-Stunden-Test.

Ablauf eines Analysezyklus (alle ``poll_seconds``):

  1. Kursdaten abrufen und pruefen          -> bei Fehlern: Pause, KEIN Trade
  2. Markt analysieren (fuenf Signale)      -> Stufe 1 "Markt wird analysiert"
  3. Handelssignal pruefen                  -> Stufe 2 "Handelssignal wurde erkannt"
  4. Risiko pruefen und entscheiden         -> Stufe 3 "Entscheidung wurde getroffen"
  5. ggf. Kauf/Verkauf simulieren           -> Stufe 4 "Trade wurde simuliert"
  6. bei Verkauf: Position ist geschlossen  -> Stufe 5 "Trade wurde abgeschlossen"

Der Status, den das Dashboard anzeigt, wird ausschliesslich hier gesetzt - und
zwar in dem Moment, in dem der jeweilige Schritt wirklich ausgefuehrt wird.
"""
from __future__ import annotations

import os
import threading
import time
import traceback
from typing import Callable, List, Optional

from . import report as report_mod
from . import strategy
from .broker import BrokerError, Portfolio
from .config import Config
from .marketdata import MarketDataClient, MarketDataError, MarketSnapshot
from .storage import Storage
from .textfmt import btc as fmt_btc
from .textfmt import duration_text, eur, local_dt, pct, score_text, signed_eur

EXIT_LABELS = {
    "STOP_LOSS": "Stop-Loss",
    "TAKE_PROFIT": "Gewinnziel erreicht",
    "TRAILING": "Nachgezogener Stopp",
    "SIGNAL": "Verkaufssignal (mehrere Indikatoren)",
    "RISK_LIMIT": "Verlustlimit erreicht",
    "END": "Testende",
}
OUTAGE_LOG_EVERY_S = 900
RETRY_AFTER_ERROR_S = 30
HEARTBEAT_EVERY_S = 5


def default_runtime(start_capital: float) -> dict:
    return {
        "analyses": 0, "signals": 0, "data_errors": 0, "trades": 0, "closed_trades": 0,
        "last_alive_ts": None, "last_sell_ts": None, "last_exit_code": "", "buy_ts": [],
        "halted": False, "outage_since": None, "outage_logged_ts": None,
        "consecutive_errors": 0, "last_error": None,
        "peak_equity": start_capital, "max_drawdown_eur": 0.0, "max_drawdown_pct": 0.0,
        "downtime_total_s": 0.0, "restarts": 0,
        "last_decision_id": None, "last_data_ts": None, "last_price": None,
        "last_bid": None, "last_ask": None, "last_source": None, "last_latency_ms": None,
        "clock_skew_s": 0.0,
    }


class Engine:
    def __init__(self, storage: Storage, cfg: Optional[Config] = None,
                 data_client: Optional[MarketDataClient] = None,
                 clock: Callable[[], float] = time.time, report_dir: Optional[str] = None):
        self.storage = storage
        self.clock = clock
        self.data = data_client or MarketDataClient(clock=clock)
        self.report_dir = report_dir
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._next_check_ts: Optional[float] = None
        self._last_decision: Optional[dict] = None
        self._activity = {"code": "STARTING", "text": "Startet",
                          "detail": "Lädt den gespeicherten Zustand.", "since": clock()}
        self.resumed = False
        self._load_or_create(cfg)

    # ------------------------------------------------------------------
    # Zustand laden / anlegen
    # ------------------------------------------------------------------
    def _load_or_create(self, cfg: Optional[Config]) -> None:
        now = self.clock()
        test = self.storage.get_meta("test")
        if test is None:
            self.cfg = (cfg or Config()).validate()
            self.test = {
                "start_ts": now, "end_ts": now + self.cfg.duration_seconds, "status": "running",
                "config": self.cfg.to_dict(), "first_price": None, "bench_btc": None,
                "finished_ts": None, "final_note": None,
            }
            self.portfolio = Portfolio(self.cfg.start_capital_eur, self.cfg.fee_rate)
            self.runtime = default_runtime(self.cfg.start_capital_eur)
            self.runtime["last_alive_ts"] = now
            with self.storage.transaction():
                self.storage.set_meta("test", self.test)
                self.storage.set_meta("portfolio", self.portfolio.to_dict())
                self.storage.set_meta("runtime", self.runtime)
                self.storage.add_event(
                    now, "info", "TEST_START",
                    f"Test gestartet (Paper-Trading, Dauer {self._duration_label()}). Virtuelles "
                    f"Startkapital {eur(self.cfg.start_capital_eur)}. Es wird kein echtes Geld "
                    "eingesetzt und es werden keine echten Orders ausgeführt.")
            return

        self.resumed = True
        self.test = test
        self.cfg = Config.from_dict(test["config"])
        self.portfolio = Portfolio.from_dict(self.storage.get_meta("portfolio"))
        self.runtime = default_runtime(self.cfg.start_capital_eur)
        self.runtime.update(self.storage.get_meta("runtime", {}) or {})
        if self.runtime.get("last_decision_id"):
            self._last_decision = self.storage.get_decision(self.runtime["last_decision_id"])

        if self.test["status"] == "running":
            heartbeat = self.storage.get_meta("heartbeat")
            last_alive = max(x for x in (self.runtime.get("last_alive_ts"), heartbeat,
                                         self.test["start_ts"]) if x is not None)
            gap = max(0.0, min(now, self.test["end_ts"]) - last_alive)
            self.runtime["restarts"] = int(self.runtime.get("restarts", 0)) + 1
            if gap > self.cfg.poll_seconds:
                self.runtime["downtime_total_s"] = float(self.runtime.get("downtime_total_s", 0)) + gap
                message = (f"Programm neu gestartet, gespeicherter Zustand wiederhergestellt. Das System "
                           f"war {duration_text(gap)} nicht aktiv (seit {local_dt(last_alive)}). In "
                           "dieser Zeit wurden keine Marktdaten geprüft und keine Trades simuliert.")
            else:
                message = "Programm neu gestartet, gespeicherter Zustand wiederhergestellt."
            if self.portfolio.position is not None:
                message += " Eine offene simulierte Position wird weiter überwacht."
            self.runtime["last_alive_ts"] = now
            with self.storage.transaction():
                self.storage.set_meta("runtime", self.runtime)
                self.storage.add_event(now, "warn", "RESTART", message)
        else:
            self._set_activity("FINISHED", "Test beendet",
                               "Der Abschlussbericht liegt vor. Es finden keine Analysen mehr statt.")

    def _duration_label(self) -> str:
        hours = self.cfg.duration_hours
        if abs(hours - round(hours)) < 1e-9:
            return f"{int(round(hours))} Stunden"
        return duration_text(hours * 3600)

    # ------------------------------------------------------------------
    # Thread-Steuerung
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="engine", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 15.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)

    def _run(self) -> None:
        while not self._stop.is_set():
            if self.test["status"] == "finished":
                break
            started = self.clock()
            if started >= self.test["end_ts"]:
                try:
                    if self.finalize():
                        break
                except Exception:  # pragma: no cover - Schutz fuer den Dauerbetrieb
                    self._log_internal_error("Abschluss")
                self._next_check_ts = started + 20
                self._sleep_until(self._next_check_ts)
                continue
            try:
                ok = self.run_cycle()
            except Exception:  # pragma: no cover - Schutz fuer den Dauerbetrieb
                ok = False
                self._log_internal_error("Analysezyklus")
            delay = self.cfg.poll_seconds if ok else min(self.cfg.poll_seconds, RETRY_AFTER_ERROR_S)
            self._next_check_ts = min(started + delay, self.test["end_ts"])
            self._sleep_until(self._next_check_ts)

    def _sleep_until(self, target: float) -> None:
        last_beat = 0.0
        while not self._stop.is_set():
            now = self.clock()
            if now >= target:
                return
            if now - last_beat >= HEARTBEAT_EVERY_S:
                last_beat = now
                try:
                    self.storage.set_meta("heartbeat", now)
                except Exception:  # pragma: no cover
                    pass
            self._stop.wait(min(target - now, 0.5))

    def _log_internal_error(self, where: str) -> None:
        text = traceback.format_exc(limit=3).strip().splitlines()[-1]
        self._reload_state()
        now = self.clock()
        self._set_activity("ERROR", "Interner Fehler – neuer Versuch folgt",
                           f"{where} abgebrochen ({text}). Es wurde kein Trade simuliert.")
        try:
            self.storage.add_event(now, "error", "INTERNAL_ERROR",
                                   f"{where} abgebrochen: {text}. Es wurde kein Trade simuliert.")
        except Exception:  # pragma: no cover
            pass

    def _reload_state(self) -> None:
        """Verwirft nicht gespeicherte Aenderungen und laedt den letzten festen Stand."""
        try:
            with self._lock:
                self.test = self.storage.get_meta("test") or self.test
                self.portfolio = Portfolio.from_dict(self.storage.get_meta("portfolio"))
                runtime = default_runtime(self.cfg.start_capital_eur)
                runtime.update(self.storage.get_meta("runtime", {}) or {})
                self.runtime = runtime
        except Exception:  # pragma: no cover
            pass

    def _set_activity(self, code: str, text: str, detail: str = "") -> None:
        with self._lock:
            self._activity = {"code": code, "text": text, "detail": detail, "since": self.clock()}

    # ------------------------------------------------------------------
    # Ein Analysezyklus
    # ------------------------------------------------------------------
    def run_cycle(self) -> bool:
        """Fuehrt genau einen Zyklus aus. Rueckgabe False = keine gueltigen Daten."""
        cfg = self.cfg
        steps: List[dict] = []

        def step(code: str, text: str) -> float:
            ts = self.clock()
            steps.append({"ts": ts, "code": code, "text": text})
            return ts

        self._set_activity("FETCHING", "Prüft aktuelle Kursbewegungen",
                           "Ruft aktuelle BTC/EUR-Kursdaten ab (" +
                           ", ersatzweise ".join(self.data.source_names) + ").")
        try:
            snap = self.data.fetch(cfg.candle_minutes)
        except MarketDataError as exc:
            self._on_data_error(str(exc), steps)
            return False
        step("FETCH", f"Kursdaten von {snap.source} geladen ({snap.latency_ms} ms): BTC/EUR "
                      f"{eur(snap.price)}, {len(snap.candles)} abgeschlossene "
                      f"{cfg.candle_minutes}-Minuten-Kerzen.")

        self._set_activity("ANALYZING", "Analysiert gerade den Bitcoin-Markt",
                           "Berechnet RSI, MACD, EMA 20, EMA 50, Handelsvolumen und kurzfristige "
                           "Kursbewegung.")
        try:
            analysis = strategy.analyze(snap.candles, snap.price, cfg)
        except ValueError as exc:
            self._on_data_error(f"Analyse nicht möglich: {exc}", steps)
            return False

        with self._lock:
            return self._decide_and_record(snap, analysis, steps, step)

    def _decide_and_record(self, snap: MarketSnapshot, analysis: strategy.Analysis,
                           steps: List[dict], step: Callable[[str, str], float]) -> bool:
        cfg, pf, rt = self.cfg, self.portfolio, self.runtime
        now = self.clock()
        stages = {"analyzed": None, "signal": None, "decided": None, "simulated": None, "closed": None}
        stages["analyzed"] = step(
            "ANALYZE", f"Markt analysiert: {analysis.situation}. Gesamtbewertung der fünf Signale: "
                       f"{score_text(analysis.score)}.")

        recovered_after = None
        if rt.get("outage_since"):
            recovered_after = now - rt["outage_since"]

        position_view = None
        if pf.position is not None:
            pf.position.peak_price = max(pf.position.peak_price, snap.bid)
            p = pf.position
            position_view = strategy.PositionView(p.entry_price, p.peak_price, p.stake_eur,
                                                  p.fee_eur, p.btc, p.entry_ts)
            self._set_activity("RISK", "Überprüft das Risiko",
                               "Prüft Stop-Loss, Gewinnziel, nachgezogenen Stopp und Verkaufssignale "
                               "der offenen Position.")
        else:
            self._set_activity("SCANNING", "Untersucht mögliche Kaufgelegenheiten",
                               "Bewertet die fünf Signale gemeinsam und prüft die Risikoregeln.")

        buys_24h = [t for t in rt.get("buy_ts", []) if t >= now - 86400]
        ctx = strategy.Context(
            now=now, end_ts=self.test["end_ts"], cash=pf.cash, equity=pf.equity(snap.price),
            start_capital=cfg.start_capital_eur, bid=snap.bid, ask=snap.ask, position=position_view,
            last_sell_ts=rt.get("last_sell_ts"), last_exit_code=rt.get("last_exit_code", ""),
            buys_last_24h=len(buys_24h), halted=bool(rt.get("halted")))
        decision = strategy.decide(analysis, ctx, cfg)

        if decision.signal_detected:
            stages["signal"] = step("SIGNAL", f"Handelssignal erkannt – {decision.signal_text}.")
        else:
            step("NO_SIGNAL", f"{decision.signal_text}.")
        if decision.risk_checks:
            failed = [c["name"] for c in decision.risk_checks if not c["ok"]]
            if position_view is not None:
                triggered = ", ".join(failed) if failed else "keine Grenze ausgelöst"
                step("RISK", f"Risiko geprüft ({len(decision.risk_checks)} Regeln): {triggered}.")
            elif failed:
                step("RISK", f"Risiko geprüft ({len(decision.risk_checks)} Regeln): nicht bestanden – "
                             + ", ".join(failed) + ".")
            else:
                step("RISK", f"Risiko geprüft ({len(decision.risk_checks)} Regeln): alle bestanden.")
        stages["decided"] = step("DECISION", f"Entscheidung getroffen: {decision.label}.")

        fill = None
        result = "Keine Transaktion simuliert."
        stage = 3  # Entscheidung getroffen; 4/5 nur, wenn wirklich ein Trade simuliert wurde
        events: List[tuple] = []
        try:
            if decision.action == "BUY":
                self._set_activity("SIM_BUY", "Simuliert einen Kauf",
                                   f"Verbucht einen virtuellen Kauf über {eur(decision.stake_eur)}.")
                fill = pf.buy(now, snap.ask, decision.stake_eur, snap.source)
                result = (f"Kauf simuliert: {fmt_btc(fill['btc'])} für {eur(fill['invested_eur'])} zum "
                          f"Kurs {eur(fill['price'])} (Gebühr {eur(fill['fee_eur'], 4)}). Die Position "
                          "ist offen – der Trade ist noch nicht abgeschlossen.")
                stages["simulated"] = step("TRADE", "Kauf simuliert (Paper-Trading, keine echte Order).")
                stage = 4
                rt["buy_ts"] = buys_24h + [now]
                events.append(("trade", "SIM_BUY", result))
            elif decision.action == "SELL":
                self._set_activity("SIM_SELL", "Simuliert einen Verkauf",
                                   "Verbucht einen virtuellen Verkauf der offenen Position.")
                fill = pf.sell(now, snap.bid)
                result = (f"Verkauf simuliert: {fmt_btc(fill['btc'])} zum Kurs {eur(fill['price'])}, "
                          f"Erlös {eur(fill['proceeds_eur'])}, Gebühr {eur(fill['fee_eur'], 4)}. Trade "
                          f"abgeschlossen mit {signed_eur(fill['pnl_eur'], 4)} "
                          f"({pct(fill['pnl_pct'])}) nach allen Gebühren.")
                ts = step("TRADE", "Verkauf simuliert (Paper-Trading, keine echte Order).")
                stages["simulated"] = ts
                stages["closed"] = step(
                    "CLOSED", f"Trade abgeschlossen: {signed_eur(fill['pnl_eur'], 4)} nach Gebühren.")
                stage = 5
                rt["last_sell_ts"] = now
                rt["last_exit_code"] = decision.exit_code
                rt["closed_trades"] = int(rt.get("closed_trades", 0)) + 1
                events.append(("trade", "SIM_SELL", result))
                if decision.halt_trading:
                    rt["halted"] = True
                    events.append(("warn", "RISK_HALT",
                                   "Verlustlimit erreicht: Der Handel ist für den Rest des Tests "
                                   "gestoppt. Der Markt wird weiter beobachtet."))
        except BrokerError as exc:
            fill = None
            stage = 3
            result = f"Keine Transaktion simuliert – Schutzregel des virtuellen Kontos: {exc}"
            events.append(("error", "BROKER_RULE", result))

        if decision.signal_detected and fill is None and decision.action == "NONE":
            events.append(("info", "SIGNAL_BLOCKED",
                           f"{decision.signal_text}. Die Risikoprüfung hat den Kauf verhindert."))
        if decision.signal_detected:
            rt["signals"] = int(rt.get("signals", 0)) + 1

        equity_after = pf.equity(snap.price)
        rt["analyses"] = int(rt.get("analyses", 0)) + 1
        if fill:
            rt["trades"] = int(rt.get("trades", 0)) + 1
        rt["peak_equity"] = max(float(rt.get("peak_equity", cfg.start_capital_eur)), equity_after)
        drawdown = rt["peak_equity"] - equity_after
        if drawdown > float(rt.get("max_drawdown_eur", 0.0)):
            rt["max_drawdown_eur"] = drawdown
            rt["max_drawdown_pct"] = drawdown / rt["peak_equity"] * 100.0
        rt.update({"last_alive_ts": now, "last_data_ts": snap.fetched_ts, "last_price": snap.price,
                   "last_bid": snap.bid, "last_ask": snap.ask, "last_source": snap.source,
                   "last_latency_ms": snap.latency_ms, "clock_skew_s": snap.clock_skew_s,
                   "outage_since": None, "outage_logged_ts": None, "consecutive_errors": 0,
                   "last_error": None})
        if recovered_after is not None:
            events.append(("info", "DATA_RESTORED",
                           f"Kursdaten wieder verfügbar ({snap.source}) nach "
                           f"{duration_text(recovered_after)}. Die Analyse läuft weiter."))
        if self.test.get("first_price") is None:
            self.test["first_price"] = snap.ask
            self.test["bench_btc"] = cfg.start_capital_eur / (1.0 + cfg.fee_rate) / snap.ask

        detail = {
            "bid": snap.bid, "ask": snap.ask, "latency_ms": snap.latency_ms,
            "candle_minutes": cfg.candle_minutes, "candles": len(snap.candles),
            "indicators": analysis.indicators,
            "signals": [s.to_dict() for s in analysis.signals],
            "signal_text": decision.signal_text,
            "risk_checks": decision.risk_checks,
            "in_position": position_view is not None,
            "exit_code": decision.exit_code,
            "steps": steps, "stages": stages,
            "equity_after": equity_after,
        }
        row = {"ts": now, "kind": "ANALYSIS", "price": snap.price, "source": snap.source,
               "situation": analysis.situation, "score": analysis.score,
               "signal_detected": decision.signal_detected, "action": decision.action if fill else "NONE",
               "decision": decision.label if (fill or decision.action == "NONE") else "Kein Trade",
               "reason": decision.reason, "result": result, "stage": stage, "detail": detail}

        try:
            with self.storage.transaction():
                decision_id = self.storage.add_decision(row)
                if fill:
                    trade_id = self.storage.add_trade({
                        **fill, "market_price": snap.price, "equity_after": equity_after,
                        "reason": (decision.signal_text if fill["side"] == "BUY"
                                   else EXIT_LABELS.get(decision.exit_code, "Verkauf")),
                        "exit_code": decision.exit_code or None, "source": snap.source,
                        "decision_id": decision_id})
                    self.storage.set_decision_trade(decision_id, trade_id)
                    row["trade_id"] = trade_id
                self.storage.add_equity(now, snap.price, equity_after, pf.cash, pf.btc)
                rt["last_decision_id"] = decision_id
                for level, code, message in events:
                    self.storage.add_event(now, level, code, message)
                self.storage.set_meta("portfolio", pf.to_dict())
                self.storage.set_meta("runtime", rt)
                self.storage.set_meta("test", self.test)
        except Exception:
            self._reload_state()
            raise

        row["id"] = decision_id
        self._last_decision = row
        self._set_waiting_activity()
        return True

    def _set_waiting_activity(self) -> None:
        if self.runtime.get("halted"):
            self._set_activity("HALTED", "Handel gestoppt – beobachtet nur noch den Markt",
                               "Das Verlustlimit wurde erreicht. Es werden keine neuen Käufe simuliert.")
        elif self.portfolio.position is not None:
            self._set_activity("HOLDING", "Hält eine simulierte Position",
                               "Überwacht Stop-Loss, Gewinnziel und Verkaufssignale bis zur nächsten "
                               "Marktprüfung.")
        else:
            self._set_activity("WAITING", "Wartet auf ein Handelssignal",
                               "Kein Kaufsignal in der letzten Analyse. Die nächste Marktprüfung folgt "
                               "automatisch.")

    # ------------------------------------------------------------------
    # Datenfehler
    # ------------------------------------------------------------------
    def _on_data_error(self, message: str, steps: List[dict]) -> None:
        with self._lock:
            rt = self.runtime
            now = self.clock()
            first = rt.get("outage_since") is None
            if first:
                rt["outage_since"] = now
            rt["data_errors"] = int(rt.get("data_errors", 0)) + 1
            rt["consecutive_errors"] = int(rt.get("consecutive_errors", 0)) + 1
            rt["last_error"] = message
            rt["last_alive_ts"] = now
            steps.append({"ts": now, "code": "DATA_ERROR",
                          "text": "Keine gültigen Kursdaten – Analyse abgebrochen, kein Trade simuliert."})
            log_row = first or (now - (rt.get("outage_logged_ts") or 0) >= OUTAGE_LOG_EVERY_S)
            with self.storage.transaction():
                if log_row:
                    rt["outage_logged_ts"] = now
                    decision_id = self.storage.add_decision({
                        "ts": now, "kind": "DATA_ERROR", "price": None, "source": None,
                        "situation": "Unbekannt – keine gültigen Kursdaten", "score": None,
                        "signal_detected": False, "action": "NONE",
                        "decision": "Keine Entscheidung",
                        "reason": f"Kursdaten fehlen oder sind unplausibel: {message}",
                        "result": "Kein Trade simuliert. Bei Datenfehlern wird grundsätzlich nicht "
                                  "gehandelt und es werden keine Kurse geschätzt.",
                        "stage": 0, "detail": {"steps": steps, "error": message, "stages": {}}})
                    rt["last_decision_id"] = decision_id
                    self._last_decision = self.storage.get_decision(decision_id)
                if first:
                    self.storage.add_event(now, "warn", "DATA_OUTAGE",
                                           f"Pausiert aufgrund fehlender Daten: {message}")
                self.storage.set_meta("runtime", rt)
            self._set_activity(
                "PAUSED_NO_DATA", "Pausiert aufgrund fehlender Daten",
                f"{message} Solange keine gültigen Kursdaten vorliegen, wird kein Trade simuliert. "
                "Ein neuer Abruf folgt automatisch.")

    # ------------------------------------------------------------------
    # Testende
    # ------------------------------------------------------------------
    def finalize(self) -> bool:
        """Beendet den Test: offene Position glattstellen, Bericht erzeugen."""
        cfg = self.cfg
        steps: List[dict] = []
        self._set_activity("FINALIZING", "Beendet den Test",
                           "Ruft den Schlusskurs ab und erstellt den Abschlussbericht.")
        try:
            snap = self.data.fetch(cfg.candle_minutes)
        except MarketDataError as exc:
            self._on_data_error(f"Schlusskurs nicht abrufbar: {exc}", steps)
            return False

        with self._lock:
            pf, rt = self.portfolio, self.runtime
            now = self.clock()
            end_ts = self.test["end_ts"]
            price, bid, ask, ts, note = snap.price, snap.bid, snap.ask, now, None
            if now - end_ts > max(2 * cfg.poll_seconds, 180):
                fine_minutes, pool = self._candles_around_end(snap)
                step_s = fine_minutes * 60
                candle = next((c for c in pool if c.t <= end_ts < c.t + step_s), None)
                if candle is not None:
                    price = bid = ask = candle.c
                    ts = end_ts
                    note = (f"Das Programm war zum Testende ({local_dt(end_ts)}) nicht aktiv. Als "
                            f"Schlusskurs wurde der Schlusskurs der {fine_minutes}-Minuten-Kerze "
                            f"verwendet, in der das Testende lag ({eur(price)}, Quelle {snap.source}).")
                else:
                    note = (f"Das Programm war zum Testende ({local_dt(end_ts)}) nicht aktiv und der "
                            "damalige Kurs war nicht mehr abrufbar. Verwendet wurde der Kurs beim "
                            f"Neustart ({eur(price)}, {local_dt(now)}).")
            steps.append({"ts": now, "code": "FETCH",
                          "text": f"Schlusskurs ermittelt ({snap.source}): {eur(price)}."})

            fill = None
            stages = {"analyzed": None, "signal": None, "decided": now, "simulated": None, "closed": None}
            if pf.position is not None:
                fill = pf.sell(ts, bid)
                result = (f"Verkauf simuliert: {fmt_btc(fill['btc'])} zum Kurs {eur(fill['price'])}, "
                          f"Erlös {eur(fill['proceeds_eur'])}, Gebühr {eur(fill['fee_eur'], 4)}. Trade "
                          f"abgeschlossen mit {signed_eur(fill['pnl_eur'], 4)} "
                          f"({pct(fill['pnl_pct'])}) nach allen Gebühren.")
                reason = ("Die Testdauer ist abgelaufen. Die offene Position wird zum Schlusskurs "
                          "glattgestellt, damit das Endkapital feststeht.")
                label, stage = "Verkauf (Testende)", 5
                stages["simulated"] = stages["closed"] = now
                steps.append({"ts": now, "code": "TRADE",
                              "text": "Verkauf zum Testende simuliert (Paper-Trading)."})
                rt["trades"] = int(rt.get("trades", 0)) + 1
                rt["closed_trades"] = int(rt.get("closed_trades", 0)) + 1
                rt["last_sell_ts"] = ts
                rt["last_exit_code"] = "END"
            else:
                result = "Keine Transaktion simuliert – es war keine Position offen."
                reason = "Die Testdauer ist abgelaufen. Der simulierte Handel wird beendet."
                label, stage = "Testende", 3
            if note:
                reason += " " + note

            equity_after = pf.equity(price)
            rt["peak_equity"] = max(float(rt.get("peak_equity", cfg.start_capital_eur)), equity_after)
            drawdown = rt["peak_equity"] - equity_after
            if drawdown > float(rt.get("max_drawdown_eur", 0.0)):
                rt["max_drawdown_eur"] = drawdown
                rt["max_drawdown_pct"] = drawdown / rt["peak_equity"] * 100.0
            rt.update({"last_alive_ts": now, "last_data_ts": snap.fetched_ts, "last_price": price,
                       "last_bid": bid, "last_ask": ask, "last_source": snap.source,
                       "outage_since": None, "outage_logged_ts": None, "consecutive_errors": 0,
                       "last_error": None})
            self.test.update({"status": "finished", "finished_ts": now, "final_note": note,
                              "final_price": price, "final_bid": bid})
            row = {"ts": ts, "kind": "FINAL", "price": price, "source": snap.source,
                   "situation": "Testende", "score": None, "signal_detected": False,
                   "action": "SELL" if fill else "NONE", "decision": label, "reason": reason,
                   "result": result, "stage": stage,
                   "detail": {"steps": steps, "stages": stages, "bid": bid, "ask": ask,
                              "exit_code": "END" if fill else "", "equity_after": equity_after}}
            try:
                with self.storage.transaction():
                    decision_id = self.storage.add_decision(row)
                    if fill:
                        trade_id = self.storage.add_trade({
                            **fill, "market_price": price, "equity_after": equity_after,
                            "reason": EXIT_LABELS["END"], "exit_code": "END", "source": snap.source,
                            "decision_id": decision_id})
                        self.storage.set_decision_trade(decision_id, trade_id)
                        row["trade_id"] = trade_id
                        self.storage.add_event(ts, "trade", "SIM_SELL", result)
                    self.storage.add_equity(ts, price, equity_after, pf.cash, pf.btc)
                    rt["last_decision_id"] = decision_id
                    self.storage.set_meta("portfolio", pf.to_dict())
                    self.storage.set_meta("runtime", rt)
                    self.storage.set_meta("test", self.test)
                    final_report = report_mod.build_report(self, now=now)
                    self.storage.set_meta("final_report", final_report)
                    self.storage.add_event(
                        now, "info", "TEST_END",
                        f"Test beendet. Endkapital {eur(final_report['end_capital'])} "
                        f"({signed_eur(final_report['pnl_eur'])}, {pct(final_report['return_pct'])}). "
                        "Der Abschlussbericht wurde erstellt.")
            except Exception:
                self._reload_state()
                raise
            row["id"] = decision_id
            self._last_decision = row
            self._next_check_ts = None
            self._set_activity("FINISHED", "Test beendet",
                               "Der Abschlussbericht liegt vor. Es finden keine Analysen mehr statt.")

        self._write_report_files()
        return True

    def _candles_around_end(self, snap: MarketSnapshot):
        """Fuer einen verspaeteten Abschluss: moeglichst feine echte Kerzen um das Testende."""
        if self.cfg.candle_minutes > 5:
            try:
                fine = self.data.fetch(5)
                return 5, list(fine.candles) + ([fine.live] if fine.live else [])
            except MarketDataError:
                pass
        return self.cfg.candle_minutes, list(snap.candles) + ([snap.live] if snap.live else [])

    def _write_report_files(self) -> None:
        if not self.report_dir:
            return
        try:
            paths = report_mod.write_report_files(self, self.report_dir)
            self.storage.add_event(self.clock(), "info", "REPORT_FILES",
                                   "Berichtsdateien gespeichert: " + ", ".join(
                                       os.path.basename(p) for p in paths) +
                                   f" (Ordner {self.report_dir}).")
        except Exception as exc:  # Dateien sind Zusatz; der Bericht liegt in der Datenbank
            self.storage.add_event(self.clock(), "error", "REPORT_FILES",
                                   f"Berichtsdateien konnten nicht geschrieben werden: {exc}")

    # ------------------------------------------------------------------
    # Zustand fuer das Dashboard
    # ------------------------------------------------------------------
    def state(self) -> dict:
        with self._lock:
            cfg, pf, rt, test = self.cfg, self.portfolio, self.runtime, self.test
            now = self.clock()
            price = rt.get("last_price")
            finished = test["status"] == "finished"
            equity = pf.equity(price) if price else pf.cash
            btc_value = pf.btc_value(price) if price else 0.0
            pnl = equity - cfg.start_capital_eur

            position = None
            if pf.position is not None:
                p = pf.position
                bid = rt.get("last_bid") or price or p.entry_price
                trailing_active = p.peak_price >= p.entry_price * (1 + cfg.trailing_start_pct / 100)
                position = {
                    "entry_ts": p.entry_ts, "entry_price": p.entry_price, "btc": p.btc,
                    "stake_eur": p.stake_eur, "fee_eur": p.fee_eur,
                    "stop_price": p.entry_price * (1 - cfg.stop_loss_pct / 100),
                    "target_price": p.entry_price * (1 + cfg.take_profit_pct / 100),
                    "trail_price": p.peak_price * (1 - cfg.trailing_gap_pct / 100) if trailing_active else None,
                    "break_even_price": strategy.break_even_price(p.entry_price, cfg.fee_rate),
                    "change_pct": (bid / p.entry_price - 1) * 100,
                    "unrealized_eur": p.btc * bid * (1 - cfg.fee_rate) - p.cost_eur,
                }

            if finished:
                ai = {"code": "FINISHED", "text": "Beendet", "active": False,
                      "reason": "Die Testdauer ist abgelaufen."}
            elif rt.get("outage_since"):
                ai = {"code": "PAUSED", "text": "Pausiert", "active": False,
                      "reason": "Keine gültigen Kursdaten seit " +
                                duration_text(now - rt["outage_since"]) + ". " +
                                (rt.get("last_error") or "")}
            elif not rt.get("analyses"):
                ai = {"code": "STARTING", "text": "Startet", "active": True,
                      "reason": "Die erste Marktanalyse läuft."}
            elif rt.get("halted"):
                ai = {"code": "ACTIVE", "text": "Aktiv (nur Beobachtung)", "active": True,
                      "reason": "Verlustlimit erreicht – es werden keine neuen Käufe simuliert."}
            else:
                ai = {"code": "ACTIVE", "text": "Aktiv", "active": True, "reason": ""}

            elapsed = (test.get("finished_ts") or now) - test["start_ts"]
            elapsed = max(0.0, min(elapsed, test["end_ts"] - test["start_ts"]))
            last = self._last_decision
            last_summary = None
            if last:
                last_summary = {
                    "id": last.get("id"), "ts": last["ts"], "kind": last["kind"],
                    "decision": last["decision"], "reason": last["reason"], "result": last["result"],
                    "situation": last.get("situation"), "score": last.get("score"),
                    "price": last.get("price"), "stage": last["stage"],
                    "signal_detected": bool(last.get("signal_detected")),
                    "action": last["action"],
                    "steps": (last.get("detail") or {}).get("steps", []),
                    "stages": (last.get("detail") or {}).get("stages", {}),
                }
            return {
                "server_now": now,
                "mode": "PAPER_TRADING",
                "pair": "BTC/EUR",
                "test": {"start_ts": test["start_ts"], "end_ts": test["end_ts"],
                         "status": test["status"], "finished_ts": test.get("finished_ts"),
                         "duration_hours": cfg.duration_hours, "elapsed_s": elapsed,
                         "remaining_s": 0.0 if finished else max(0.0, test["end_ts"] - now),
                         "final_note": test.get("final_note"),
                         "is_standard_duration": abs(cfg.duration_hours - 72.0) < 1e-9},
                "ai": ai,
                "activity": dict(self._activity,
                                 next_check_ts=None if finished else self._next_check_ts),
                "account": {
                    "start_capital": cfg.start_capital_eur, "equity": equity, "pnl_eur": pnl,
                    "pnl_pct": pnl / cfg.start_capital_eur * 100.0, "cash": pf.cash, "btc": pf.btc,
                    "btc_value": btc_value, "fees_total": pf.fees_total,
                    "realized_pnl": pf.realized_pnl, "position": position,
                },
                "market": {"price": price, "bid": rt.get("last_bid"), "ask": rt.get("last_ask"),
                           "source": rt.get("last_source"), "updated_ts": rt.get("last_data_ts"),
                           "latency_ms": rt.get("last_latency_ms"),
                           "clock_skew_s": rt.get("clock_skew_s", 0.0),
                           "sources": self.data.source_names},
                "benchmark": {"first_price": test.get("first_price"), "bench_btc": test.get("bench_btc"),
                              "value": (test["bench_btc"] * price)
                              if (test.get("bench_btc") and price) else None},
                "counters": {"analyses": rt.get("analyses", 0), "signals": rt.get("signals", 0),
                             "trades": rt.get("trades", 0), "closed_trades": rt.get("closed_trades", 0),
                             "data_errors": rt.get("data_errors", 0), "restarts": rt.get("restarts", 0),
                             "downtime_s": rt.get("downtime_total_s", 0.0),
                             "max_drawdown_eur": rt.get("max_drawdown_eur", 0.0),
                             "max_drawdown_pct": rt.get("max_drawdown_pct", 0.0)},
                "last_decision": last_summary,
                "config": cfg.to_dict(),
                "rev": {"decisions": self.storage.max_id("decisions"),
                        "trades": self.storage.max_id("trades"),
                        "equity": self.storage.max_id("equity"),
                        "events": self.storage.max_id("events")},
            }
