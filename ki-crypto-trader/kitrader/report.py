"""Zwischen- und Abschlussbericht samt CSV- und PDF-Export.

Alle Kennzahlen stammen aus den gespeicherten, simulierten Trades und dem
gespeicherten Kontostandsverlauf - es wird nichts geschaetzt.
"""
from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime
from typing import List, Optional

from .pdfwriter import GRAY, MARGIN_X, MUTED, PdfDoc
from .textfmt import de_num, duration_text, eur, local_dt, local_tz_name, pct, signed_eur

DISCLAIMER = ("Paper-Trading-Simulation: Es wurde kein echtes Geld eingesetzt und es wurden keine "
              "echten Kauf- oder Verkaufsaufträge ausgeführt. Kein Hebel, kein Margin, keine Kredite. "
              "Die Kurse stammen aus öffentlichen Börsendaten. Dieses Ergebnis ist keine "
              "Anlageberatung und keine Aussage über zukünftige Ergebnisse.")


# ---------------------------------------------------------------------------
# Kennzahlen
# ---------------------------------------------------------------------------

def build_report(engine, now: Optional[float] = None) -> dict:
    cfg, test, pf, rt = engine.cfg, engine.test, engine.portfolio, engine.runtime
    now = engine.clock() if now is None else now
    final = test["status"] == "finished"
    price = rt.get("last_price")
    start = cfg.start_capital_eur
    equity = pf.equity(price) if price else pf.cash
    pnl = equity - start

    trades = engine.storage.get_trades()
    buys = [t for t in trades if t["side"] == "BUY"]
    sells = [t for t in trades if t["side"] == "SELL"]
    wins = [t for t in sells if (t["pnl_eur"] or 0) > 0]
    losses = [t for t in sells if (t["pnl_eur"] or 0) <= 0]
    gross_profit = sum(t["pnl_eur"] for t in wins)
    gross_loss = -sum(t["pnl_eur"] for t in losses)
    fees = sum(t["fee_eur"] for t in trades)
    exit_reasons: dict = {}
    for t in sells:
        exit_reasons[t["reason"]] = exit_reasons.get(t["reason"], 0) + 1

    hold_seconds = []
    buy_by_position = {t["position_id"]: t for t in buys}
    for t in sells:
        opened = buy_by_position.get(t["position_id"])
        if opened:
            hold_seconds.append(t["ts"] - opened["ts"])

    first_price = test.get("first_price")
    bench = None
    if first_price and test.get("bench_btc") and price:
        # Vergleich "einmal kaufen und halten": Kauf zum Teststart inkl. Kaufgebuehr.
        # Im Abschlussbericht wird - wie bei der Strategie - auch der Verkauf am Ende
        # samt Gebuehr eingerechnet, damit beide Werte vergleichbar sind.
        sell_price = test.get("final_bid") or rt.get("last_bid") or price
        value = (test["bench_btc"] * sell_price * (1 - cfg.fee_rate)) if final \
            else test["bench_btc"] * price
        bench = {"first_price": first_price, "value": value, "pnl_eur": value - start,
                 "return_pct": (value - start) / start * 100.0, "liquidated": final}

    elapsed = (test.get("finished_ts") or now) - test["start_ts"]
    elapsed = max(0.0, min(elapsed, test["end_ts"] - test["start_ts"]))
    report = {
        "generated_ts": now,
        "final": final,
        "title": "Abschlussbericht" if final else "Zwischenbericht",
        "mode": "Paper-Trading (Simulation, kein echtes Geld)",
        "pair": "BTC/EUR",
        "start_ts": test["start_ts"], "end_ts": test["end_ts"],
        "finished_ts": test.get("finished_ts"),
        "duration_hours": cfg.duration_hours, "elapsed_s": elapsed,
        "start_capital": start, "end_capital": equity, "pnl_eur": pnl,
        "return_pct": pnl / start * 100.0,
        "cash": pf.cash, "btc": pf.btc, "btc_value": pf.btc_value(price) if price else 0.0,
        "open_position": pf.position is not None,
        "orders_total": len(trades), "buys": len(buys), "sells": len(sells),
        "closed_trades": len(sells), "wins": len(wins), "losses": len(losses),
        "win_rate_pct": (len(wins) / len(sells) * 100.0) if sells else None,
        "avg_win_eur": (gross_profit / len(wins)) if wins else None,
        "avg_loss_eur": (-gross_loss / len(losses)) if losses else None,
        "max_win_eur": max((t["pnl_eur"] for t in wins), default=None),
        "max_loss_eur": min((t["pnl_eur"] for t in losses), default=None),
        "avg_trade_eur": (sum(t["pnl_eur"] for t in sells) / len(sells)) if sells else None,
        "gross_profit": gross_profit, "gross_loss": gross_loss,
        "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else None,
        "avg_hold_s": (sum(hold_seconds) / len(hold_seconds)) if hold_seconds else None,
        "max_drawdown_eur": float(rt.get("max_drawdown_eur", 0.0)),
        "max_drawdown_pct": float(rt.get("max_drawdown_pct", 0.0)),
        "fees_total": fees, "fees_pct_of_capital": fees / start * 100.0,
        "benchmark": bench,
        "price_start": first_price, "price_end": price,
        "price_change_pct": ((price / first_price - 1) * 100.0) if (first_price and price) else None,
        "analyses": int(rt.get("analyses", 0)), "signals": int(rt.get("signals", 0)),
        "data_errors": int(rt.get("data_errors", 0)), "restarts": int(rt.get("restarts", 0)),
        "downtime_s": float(rt.get("downtime_total_s", 0.0)),
        "halted": bool(rt.get("halted")),
        "exit_reasons": exit_reasons,
        "final_note": test.get("final_note"),
        "config": cfg.to_dict(),
        "disclaimer": DISCLAIMER,
    }
    report["evaluation"] = evaluate(report)
    return report


def evaluate(r: dict) -> dict:
    """Regelbasierte, ehrliche Einordnung des Ergebnisses in Worten."""
    paragraphs: List[str] = []
    closed = r["closed_trades"]
    bench = r.get("benchmark")
    ret = r["return_pct"]
    scope = "Der Test" if r["final"] else "Der bisherige Testverlauf"

    if abs(r["pnl_eur"]) < 0.005:
        outcome = "praktisch unverändert"
    else:
        outcome = "einem Gewinn" if r["pnl_eur"] > 0 else "einem Verlust"
    if outcome == "praktisch unverändert":
        paragraphs.append(f"{scope} endet {outcome}: Aus {eur(r['start_capital'])} wurden "
                          f"{eur(r['end_capital'])} ({pct(ret)}).")
    else:
        paragraphs.append(f"{scope} endet mit {outcome} von {signed_eur(r['pnl_eur'])} "
                          f"({pct(ret)}): Aus {eur(r['start_capital'])} wurden {eur(r['end_capital'])}.")

    if bench:
        diff = ret - bench["return_pct"]
        how = ("inklusive Kauf- und Verkaufsgebühr" if bench["liquidated"]
               else "inklusive Kaufgebühr, zum aktuellen Kurs bewertet")
        if abs(diff) < 0.05:
            cmp_text = "Die Strategie lag damit etwa gleichauf."
        elif diff > 0:
            cmp_text = f"Die Strategie war damit um {de_num(diff, 2)} Prozentpunkte besser."
        else:
            cmp_text = f"Die Strategie war damit um {de_num(-diff, 2)} Prozentpunkte schlechter."
        paragraphs.append(f"Vergleich: Wer zum Teststart einmalig für {eur(r['start_capital'])} Bitcoin "
                          f"gekauft und gehalten hätte ({how}), stünde bei {eur(bench['value'])} "
                          f"({pct(bench['return_pct'])}). {cmp_text}")

    if closed == 0:
        if r["open_position"]:
            paragraphs.append("Es wurde bisher kein Trade abgeschlossen; eine simulierte Position ist "
                              "noch offen. Trefferquote und Durchschnittswerte lassen sich erst nach "
                              "dem ersten Verkauf berechnen.")
        else:
            paragraphs.append(f"Es wurde kein einziger Trade simuliert. In {r['analyses']} Analysen "
                              "haben sich nie genügend Signale gleichzeitig bestätigt. Die Strategie hat "
                              "das Kapital damit geschützt, aber auch nichts verdient – eine Bewertung "
                              "der Handelsqualität ist nicht möglich.")
    else:
        text = (f"Von {closed} abgeschlossenen Trades waren {r['wins']} erfolgreich und "
                f"{r['losses']} erfolglos (Trefferquote {de_num(r['win_rate_pct'], 1)} %).")
        if r["avg_win_eur"] is not None and r["avg_loss_eur"] is not None:
            ratio = r["avg_win_eur"] / abs(r["avg_loss_eur"]) if r["avg_loss_eur"] else None
            text += (f" Ein Gewinntrade brachte im Schnitt {signed_eur(r['avg_win_eur'], 4)}, ein "
                     f"Verlusttrade {signed_eur(r['avg_loss_eur'], 4)}")
            text += (f" (Verhältnis {de_num(ratio, 2)} : 1)." if ratio else ".")
        if r["profit_factor"] is not None:
            text += (f" Profitfaktor (Summe Gewinne / Summe Verluste): {de_num(r['profit_factor'], 2)} – "
                     + ("über 1, die Gewinne überwiegen." if r["profit_factor"] > 1
                        else "unter 1, die Verluste überwiegen."))
        paragraphs.append(text)

    if r["orders_total"]:
        gross = r["pnl_eur"] + r["fees_total"]
        paragraphs.append(f"Die Handelsgebühren betrugen insgesamt {eur(r['fees_total'], 4)} "
                          f"({de_num(r['fees_pct_of_capital'], 2)} % des Startkapitals). Vor Gebühren "
                          f"läge das Ergebnis bei {signed_eur(gross, 4)}. Bei so kleinen Beträgen und "
                          "kurzen Haltedauern entscheiden die Gebühren oft über Gewinn oder Verlust.")

    paragraphs.append(f"Der größte zwischenzeitliche Rückgang des Kontostands (maximaler Drawdown) "
                      f"betrug {eur(r['max_drawdown_eur'], 4)} bzw. "
                      f"{de_num(r['max_drawdown_pct'], 2)} %."
                      + (" Das Verlustlimit wurde erreicht und der Handel gestoppt." if r["halted"] else ""))

    if r["data_errors"] or r["downtime_s"] > 0:
        paragraphs.append(f"Betrieb: {r['data_errors']} Datenabrufe schlugen fehl (in diesen Momenten "
                          f"wurde nicht gehandelt); das Programm war insgesamt "
                          f"{duration_text(r['downtime_s'])} nicht aktiv ({r['restarts']} Neustarts). "
                          "Solche Lücken können das Ergebnis beeinflussen.")

    paragraphs.append(f"Einordnung: {de_num(r['elapsed_s'] / 3600, 1)} Stunden und {closed} "
                      "abgeschlossene Trades sind eine sehr kleine Stichprobe. Das Ergebnis kann "
                      "überwiegend Zufall sein und sagt wenig darüber aus, wie die Strategie in anderen "
                      "Marktphasen abschneiden würde. Für eine belastbare Aussage wären deutlich längere "
                      "Tests über verschiedene Marktphasen nötig.")

    if closed == 0:
        code, verdict = "NOT_RATEABLE", "Nicht bewertbar – keine abgeschlossenen Trades"
    elif bench is None:
        code, verdict = ("POSITIVE", "Positiv – Gewinn erzielt") if r["pnl_eur"] > 0 else \
                        ("NEGATIVE", "Negativ – Verlust")
    elif r["pnl_eur"] > 0 and ret >= bench["return_pct"]:
        code, verdict = "POSITIVE", "Positiv – Gewinn erzielt und besser als Kaufen und Halten"
    elif r["pnl_eur"] > 0:
        code, verdict = "MIXED", "Gemischt – Gewinn erzielt, aber schlechter als Kaufen und Halten"
    elif ret >= bench["return_pct"]:
        code, verdict = "MIXED", "Gemischt – Verlust, aber geringer als bei Kaufen und Halten"
    else:
        code, verdict = "NEGATIVE", "Negativ – Verlust und schlechter als Kaufen und Halten"
    if not r["final"]:
        verdict += " (vorläufig)"
    return {"verdict_code": code, "verdict": verdict, "paragraphs": paragraphs}


# ---------------------------------------------------------------------------
# Tabellen fuer Anzeige und Export
# ---------------------------------------------------------------------------

def _opt_eur(value, digits=2, signed=False) -> str:
    if value is None:
        return "–"
    return signed_eur(value, digits) if signed else eur(value, digits)


def summary_rows(r: dict) -> List[tuple]:
    """(Abschnitt, Kennzahl, Wert) - gemeinsame Grundlage fuer CSV und PDF."""
    bench = r.get("benchmark")
    rows = [
        ("Ergebnis", "Startkapital", eur(r["start_capital"])),
        ("Ergebnis", "Endkapital" if r["final"] else "Aktueller Kontostand", eur(r["end_capital"])),
        ("Ergebnis", "Gesamtgewinn / Gesamtverlust", signed_eur(r["pnl_eur"], 4)),
        ("Ergebnis", "Rendite", pct(r["return_pct"])),
        ("Trades", "Simulierte Orders insgesamt (Käufe + Verkäufe)",
         f"{r['orders_total']} ({r['buys']} Käufe, {r['sells']} Verkäufe)"),
        ("Trades", "Abgeschlossene Trades (Kauf und Verkauf)", str(r["closed_trades"])),
        ("Trades", "Erfolgreiche Trades", str(r["wins"])),
        ("Trades", "Erfolglose Trades", str(r["losses"])),
        ("Trades", "Trefferquote",
         "–" if r["win_rate_pct"] is None else f"{de_num(r['win_rate_pct'], 1)} %"),
        ("Trades", "Durchschnittlicher Gewinn pro Gewinntrade", _opt_eur(r["avg_win_eur"], 4, True)),
        ("Trades", "Durchschnittlicher Verlust pro Verlusttrade", _opt_eur(r["avg_loss_eur"], 4, True)),
        ("Trades", "Größter Gewinn", _opt_eur(r["max_win_eur"], 4, True)),
        ("Trades", "Größter Verlust", _opt_eur(r["max_loss_eur"], 4, True)),
        ("Trades", "Durchschnittliches Ergebnis je Trade", _opt_eur(r["avg_trade_eur"], 4, True)),
        ("Trades", "Profitfaktor",
         "–" if r["profit_factor"] is None else de_num(r["profit_factor"], 2)),
        ("Trades", "Durchschnittliche Haltedauer",
         "–" if r["avg_hold_s"] is None else duration_text(r["avg_hold_s"])),
        ("Risiko und Kosten", "Maximaler Drawdown",
         f"{eur(r['max_drawdown_eur'], 4)} ({de_num(r['max_drawdown_pct'], 2)} %)"),
        ("Risiko und Kosten", "Handelsgebühren gesamt",
         f"{eur(r['fees_total'], 4)} ({de_num(r['fees_pct_of_capital'], 2)} % des Startkapitals)"),
        ("Risiko und Kosten", "Gebührensatz je Order", f"{de_num(r['config']['fee_rate'] * 100, 2)} %"),
        ("Markt", "BTC-Kurs zum Start", _opt_eur(r["price_start"])),
        ("Markt", "BTC-Kurs zum Ende" if r["final"] else "BTC-Kurs aktuell", _opt_eur(r["price_end"])),
        ("Markt", "Kursveränderung",
         "–" if r["price_change_pct"] is None else pct(r["price_change_pct"])),
        ("Markt", "Vergleich Kaufen und Halten",
         "–" if not bench else f"{eur(bench['value'])} ({pct(bench['return_pct'])})"),
        ("Betrieb", "Analysierte Marktsituationen", str(r["analyses"])),
        ("Betrieb", "Erkannte Handelssignale", str(r["signals"])),
        ("Betrieb", "Fehlgeschlagene Datenabrufe", str(r["data_errors"])),
        ("Betrieb", "Neustarts / Ausfallzeit",
         f"{r['restarts']} / {duration_text(r['downtime_s'])}"),
    ]
    return rows


def _csv_text(rows: List[List[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerows(rows)
    return "﻿" + buffer.getvalue()  # BOM, damit Excel UTF-8 erkennt


def _n(value, digits=2) -> str:
    return "" if value is None else de_num(value, digits)


def trade_table(trades: List[dict]) -> List[List[str]]:
    rows = [["Nr.", "Zeitpunkt", "Typ (simuliert)", "BTC-Kurs (EUR)", "Menge (BTC)",
             "Investierter Betrag (EUR)", "Erlös (EUR)", "Gebühren (EUR)",
             "Gewinn/Verlust (EUR)", "Gewinn/Verlust (%)", "Kontostand nach Trade (EUR)",
             "Grund", "Datenquelle"]]
    for t in trades:
        rows.append([str(t["id"]), local_dt(t["ts"]), "Kauf" if t["side"] == "BUY" else "Verkauf",
                     _n(t["price"], 2), _n(t["btc"], 8), _n(t["invested_eur"], 4),
                     _n(t["proceeds_eur"], 4), _n(t["fee_eur"], 4), _n(t["pnl_eur"], 4),
                     _n(t["pnl_pct"], 2), _n(t["equity_after"], 4), t["reason"], t["source"]])
    return rows


def report_csv(report: dict, trades: List[dict]) -> str:
    r = report
    rows: List[List[str]] = [
        [f"KI Crypto Trader – {r['title']}"],
        ["Modus", r["mode"]],
        ["Handelspaar", r["pair"]],
        ["Teststart", local_dt(r["start_ts"])],
        ["Testende (geplant)", local_dt(r["end_ts"])],
        ["Laufzeit", duration_text(r["elapsed_s"])],
        ["Bericht erstellt", local_dt(r["generated_ts"])],
        ["Zeitzone", local_tz_name()],
        [],
        ["Abschnitt", "Kennzahl", "Wert"],
    ]
    rows += [list(row) for row in summary_rows(r)]
    rows += [[], ["Bewertung der Strategie", r["evaluation"]["verdict"]]]
    rows += [["", p] for p in r["evaluation"]["paragraphs"]]
    if r.get("final_note"):
        rows += [["Hinweis", r["final_note"]]]
    rows += [[], ["Trade-Verlauf (alle Trades sind simuliert)"]]
    rows += trade_table(trades)
    rows += [[], ["Hinweis", r["disclaimer"]]]
    return _csv_text(rows)


def trades_csv(trades: List[dict]) -> str:
    return _csv_text(trade_table(trades))


def decisions_csv(decisions: List[dict]) -> str:
    rows = [["Nr.", "Zeitpunkt", "Art", "BTC-Kurs (EUR)", "Datenquelle", "Marktsituation",
             "Gesamtbewertung", "RSI", "MACD", "MACD-Signal", "MACD-Histogramm", "EMA 20", "EMA 50",
             "Volumen-Verhältnis", "Kursbewegung (%)", "Handelssignal erkannt", "Entscheidung",
             "Begründung", "Ergebnis", "Erreichte Stufe"]]
    kinds = {"ANALYSIS": "Analyse", "DATA_ERROR": "Datenfehler", "FINAL": "Testende"}
    stage_names = {0: "0 – keine Analyse (Datenfehler)", 3: "3 – Entscheidung getroffen",
                   4: "4 – Trade simuliert", 5: "5 – Trade abgeschlossen"}
    for d in decisions:
        i = (d.get("detail") or {}).get("indicators") or {}
        rows.append([
            str(d["id"]), local_dt(d["ts"]), kinds.get(d["kind"], d["kind"]), _n(d.get("price"), 2),
            d.get("source") or "", d.get("situation") or "",
            "" if d.get("score") is None else f"{d['score']:+d}",
            _n(i.get("rsi"), 1), _n(i.get("macd"), 2), _n(i.get("macd_signal"), 2),
            _n(i.get("macd_hist"), 2), _n(i.get("ema_fast"), 2), _n(i.get("ema_slow"), 2),
            _n(i.get("volume_ratio"), 2), _n(i.get("move_pct"), 3),
            "ja" if d.get("signal_detected") else "nein", d["decision"], d["reason"], d["result"],
            stage_names.get(d["stage"], str(d["stage"]))])
    return _csv_text(rows)


def equity_csv(points: List[dict]) -> str:
    rows = [["Zeitpunkt", "BTC-Kurs (EUR)", "Kontostand (EUR)", "Freies Guthaben (EUR)",
             "BTC-Bestand"]]
    for p in points:
        rows.append([local_dt(p["ts"]), _n(p["price"], 2), _n(p["equity"], 4), _n(p["cash"], 4),
                     _n(p["btc"], 8)])
    return _csv_text(rows)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def _short_reason(reason: str) -> str:
    """Kurzform des Handelsgrunds fuer die schmale PDF-Spalte."""
    reason = reason.split(" (mindestens")[0].split(" (mehrere")[0]
    return reason.replace("Gesamtbewertung", "Bewertung")


def report_pdf(report: dict, trades: List[dict]) -> bytes:
    r = report
    doc = PdfDoc(title=f"KI Crypto Trader – {r['title']}")
    doc.footer_left = f"KI Crypto Trader · {r['title']} · Paper-Trading-Simulation"

    doc.y -= 6
    doc.text(MARGIN_X, doc.y, "KI Crypto Trader", 22, bold=True)
    doc.y -= 22
    hours = r["duration_hours"]
    length = (f"{int(round(hours))}-Stunden-Test" if abs(hours - round(hours)) < 1e-9
              else f"Probelauf über {duration_text(hours * 3600)}")
    doc.text(MARGIN_X, doc.y, f"{r['title']} · BTC/EUR · {length}", 12, color=GRAY)
    doc.y -= 16
    doc.text(MARGIN_X, doc.y, "Paper-Trading-Simulation – kein echtes Geld, keine echten Orders",
             10, bold=True, color=GRAY)
    doc.y -= 14

    # Kernzahlen als vier Kacheln
    tiles = [
        ("Startkapital", eur(r["start_capital"])),
        ("Endkapital" if r["final"] else "Aktueller Kontostand", eur(r["end_capital"])),
        ("Gewinn / Verlust", signed_eur(r["pnl_eur"])),
        ("Rendite", pct(r["return_pct"])),
    ]
    gap = 8.0
    tile_w = (doc.content_width - 3 * gap) / 4
    tile_h = 50.0
    doc.y -= tile_h + 6
    for index, (label, value) in enumerate(tiles):
        x = MARGIN_X + index * (tile_w + gap)
        doc.rect(x, doc.y, tile_w, tile_h, (0.96, 0.96, 0.94))
        doc.text(x + 9, doc.y + tile_h - 16, label, 8, color=GRAY)
        doc.text(x + 9, doc.y + 12, value, 15, bold=True)
    doc.y -= 4

    doc.heading("Testzeitraum")
    doc.key_values([
        ("Teststart", local_dt(r["start_ts"])),
        ("Testende (geplant)", local_dt(r["end_ts"])),
        ("Tatsächliche Laufzeit", duration_text(r["elapsed_s"])),
        ("Bericht erstellt", f"{local_dt(r['generated_ts'])} ({local_tz_name()})"),
        ("Status", "Test abgeschlossen" if r["final"] else "Test läuft noch – Zwischenstand"),
    ])

    current = None
    block: List[tuple] = []
    for section, label, value in summary_rows(r) + [(None, "", "")]:
        if section != current:
            if block:
                doc.heading(current)
                doc.key_values(block)
            current, block = section, []
        if section is not None:
            block.append((label, value))

    doc.heading("Bewertung der Strategie")
    doc.paragraph(r["evaluation"]["verdict"], 11, bold=True)
    for paragraph in r["evaluation"]["paragraphs"]:
        doc.paragraph(paragraph, 10)
        doc.spacer(2)
    if r.get("final_note"):
        doc.paragraph("Hinweis zum Testende: " + r["final_note"], 9.5, color=GRAY)

    cfg = r["config"]
    doc.heading("Verwendete Strategie und Risikoregeln")
    doc.paragraph(
        "Regelbasierter Algorithmus (kein Sprachmodell). Fünf Signale werden gemeinsam bewertet, jedes "
        "liefert −1, 0 oder +1: Trend (EMA 20 gegen EMA 50), MACD (12, 26, 9), RSI (14), "
        "Handelsvolumen und kurzfristige Kursbewegung. Grundlage sind abgeschlossene "
        f"{cfg['candle_minutes']}-Minuten-Kerzen, geprüft wurde alle {cfg['poll_seconds']} Sekunden.", 10)
    doc.key_values([
        ("Kauf erst ab Gesamtbewertung", f"+{cfg['buy_score_min']} von 5 (und kein Abwärtstrend, RSI unter "
                                         f"{de_num(cfg['rsi_overbought'], 0)})"),
        ("Verkauf ab Gesamtbewertung", f"{cfg['sell_score_max']} von 5"),
        ("Stop-Loss / Gewinnziel", f"−{de_num(cfg['stop_loss_pct'], 1)} % / +{de_num(cfg['take_profit_pct'], 1)} %"),
        ("Nachgezogener Stopp", f"ab +{de_num(cfg['trailing_start_pct'], 1)} % Gewinn, Abstand "
                                f"{de_num(cfg['trailing_gap_pct'], 1)} %"),
        ("Maximaler Einsatz je Kauf", f"{de_num(cfg['max_stake_fraction'] * 100, 0)} % des freien Guthabens, "
                                      f"nie mehr als {eur(cfg['start_capital_eur'])}"),
        ("Verlustlimit (Handelsstopp)", f"−{de_num(cfg['max_total_loss_pct'], 0)} % vom Startkapital"),
        ("Höchstens Käufe in 24 Stunden", str(cfg["max_buys_per_24h"])),
        ("Hebel / Margin / Kredit", "nicht vorhanden"),
    ])

    doc.heading("Trade-Verlauf (alle Trades simuliert)")
    if trades:
        rows = []
        for t in trades:
            rows.append([
                str(t["id"]), local_dt(t["ts"], with_seconds=False),
                "Kauf" if t["side"] == "BUY" else "Verkauf", de_num(t["price"], 2),
                de_num(t["invested_eur"], 2), de_num(t["fee_eur"], 4),
                "" if t["pnl_eur"] is None else signed_eur(t["pnl_eur"], 4).replace(" €", ""),
                de_num(t["equity_after"], 2), _short_reason(t["reason"])])
        doc.table(["Nr.", "Zeitpunkt", "Typ", "BTC-Kurs €", "Betrag €", "Gebühr €", "G/V €",
                   "Kontostand €", "Grund"],
                  rows, widths=[4, 14, 7, 10, 8, 8, 9, 11, 29],
                  aligns=["r", "l", "l", "r", "r", "r", "r", "r", "l"])
        doc.paragraph("Betrag = investierter Betrag der Position. G/V = Ergebnis des abgeschlossenen "
                      "Trades nach Kauf- und Verkaufsgebühr. Kontostand = freies Guthaben plus "
                      "Marktwert des BTC-Bestands nach dem Trade.", 8.5, color=MUTED)
    else:
        doc.paragraph("Es wurden keine Trades simuliert.", 10, color=GRAY)

    doc.heading("Wichtiger Hinweis")
    doc.paragraph(r["disclaimer"], 9.5, color=GRAY)
    return doc.build()


# ---------------------------------------------------------------------------
# Dateien schreiben (automatisch am Testende)
# ---------------------------------------------------------------------------

def write_report_files(engine, directory: str) -> List[str]:
    os.makedirs(directory, exist_ok=True)
    report = engine.storage.get_meta("final_report") or build_report(engine)
    trades = engine.storage.get_trades()
    stamp = datetime.fromtimestamp(report["start_ts"]).strftime("%Y-%m-%d_%H%M")
    prefix = "abschlussbericht" if report["final"] else "zwischenbericht"
    files = {
        f"{prefix}_{stamp}.pdf": report_pdf(report, trades),
        f"{prefix}_{stamp}.csv": report_csv(report, trades).encode("utf-8"),
        f"{prefix}_{stamp}.json": json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"),
        f"trades_{stamp}.csv": trades_csv(trades).encode("utf-8"),
        f"entscheidungen_{stamp}.csv": decisions_csv(engine.storage.iter_decisions()).encode("utf-8"),
        f"kontostand_{stamp}.csv": equity_csv(engine.storage.get_equity()).encode("utf-8"),
    }
    paths = []
    for name, data in files.items():
        path = os.path.join(directory, name)
        tmp = path + ".tmp"
        with open(tmp, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
        paths.append(path)
    return paths


