#!/usr/bin/env python3
"""KI Crypto Trader - Startskript.

    python start.py            startet den 72-Stunden-Test bzw. setzt ihn fort
    python start.py --neu      archiviert den alten Test und beginnt einen neuen

Ausschliesslich Paper-Trading: Es wird kein echtes Geld eingesetzt und es
werden keine echten Orders ausgefuehrt.
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import sys
import threading
import time
import webbrowser
from datetime import datetime

if sys.version_info < (3, 8):
    sys.exit("Bitte Python 3.8 oder neuer verwenden (gefunden: %s)." % sys.version.split()[0])

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kitrader.config import ALLOWED_CANDLE_MINUTES, Config  # noqa: E402
from kitrader.engine import Engine  # noqa: E402
from kitrader.storage import Storage  # noqa: E402
from kitrader.textfmt import duration_text, eur, local_dt  # noqa: E402
from kitrader.webserver import DashboardServer  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="KI Crypto Trader – 72-Stunden-Paper-Trading-Test für BTC/EUR mit Live-Dashboard.")
    parser.add_argument("--port", type=int, default=8000, help="Port des Dashboards (Standard: 8000)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Adresse des Dashboards. 0.0.0.0 macht es im eigenen WLAN erreichbar "
                             "(z. B. fürs Smartphone). Standard: 127.0.0.1")
    parser.add_argument("--neu", action="store_true",
                        help="Bisherigen Test archivieren und einen neuen Test starten")
    parser.add_argument("--intervall", type=int, default=60, metavar="SEKUNDEN",
                        help="Abstand der Marktprüfungen, 60 bis 300 Sekunden (Standard: 60)")
    parser.add_argument("--kerze", type=int, default=60, choices=ALLOWED_CANDLE_MINUTES,
                        metavar="MINUTEN", help="Kerzenlänge für die Indikatoren: 5, 15 oder 60 "
                                                "(Standard: 60). Kürzere Kerzen bedeuten mehr "
                                                "Trades und damit mehr Gebühren")
    parser.add_argument("--dauer-stunden", type=float, default=72.0, metavar="STUNDEN",
                        help="Testdauer. Standard und Projektvorgabe: 72. Kleinere Werte nur für "
                             "einen kurzen Probelauf (z. B. 0.1 = 6 Minuten)")
    parser.add_argument("--daten", default=os.path.join(HERE, "data"), metavar="ORDNER",
                        help="Ordner für Datenbank und Berichte (Standard: ./data)")
    parser.add_argument("--kein-browser", action="store_true",
                        help="Dashboard nicht automatisch im Browser öffnen")
    return parser.parse_args(argv)


def archive_existing(data_dir: str) -> str:
    """Verschiebt den alten Test in data/archiv/ - geloescht wird nichts."""
    db_path = os.path.join(data_dir, "trader.db")
    if not os.path.exists(db_path):
        return ""
    target = os.path.join(data_dir, "archiv", datetime.now().strftime("test_%Y-%m-%d_%H%M%S"))
    os.makedirs(target, exist_ok=True)
    for name in ("trader.db", "trader.db-wal", "trader.db-shm"):
        source = os.path.join(data_dir, name)
        if os.path.exists(source):
            shutil.move(source, os.path.join(target, name))
    reports = os.path.join(data_dir, "berichte")
    if os.path.isdir(reports):
        shutil.move(reports, os.path.join(target, "berichte"))
    return target


def another_instance_running(storage: Storage) -> bool:
    """Erkennt eine zweite laufende Instanz am fortlaufenden Lebenszeichen."""
    first = storage.get_meta("heartbeat")
    if first is None or time.time() - float(first) > 12:
        return False
    time.sleep(7)
    return storage.get_meta("heartbeat") != first


def main(argv=None) -> int:
    args = parse_args(argv)
    os.makedirs(args.daten, exist_ok=True)

    if args.neu:
        archived = archive_existing(args.daten)
        if archived:
            print(f"Bisheriger Test archiviert nach: {archived}")

    try:
        cfg = Config(poll_seconds=args.intervall, candle_minutes=args.kerze,
                     duration_hours=args.dauer_stunden).validate()
    except ValueError as exc:
        print(f"Ungültige Einstellung: {exc}")
        return 2

    storage = Storage(os.path.join(args.daten, "trader.db"))
    if another_instance_running(storage):
        print("Es läuft bereits ein KI Crypto Trader mit diesem Datenordner. Bitte zuerst das andere "
              "Fenster beenden (Strg+C) – zwei Instanzen würden den Test verfälschen.")
        return 1

    engine = Engine(storage, cfg, report_dir=os.path.join(args.daten, "berichte"))
    try:
        server = DashboardServer(engine, args.host, args.port)
    except OSError as exc:
        print(f"Das Dashboard konnte auf Port {args.port} nicht starten ({exc}).\n"
              f"Tipp: anderen Port wählen, z. B.  python start.py --port {args.port + 1}")
        return 1

    url = f"http://{'localhost' if args.host in ('127.0.0.1', '0.0.0.0') else args.host}:{server.port}"
    test = engine.test
    print("=" * 68)
    print(" KI Crypto Trader – PAPER-TRADING (Simulation, kein echtes Geld)")
    print("=" * 68)
    if engine.resumed and test["status"] == "running":
        print(" Gespeicherter Test wird fortgesetzt.")
    elif engine.resumed:
        print(" Dieser Test ist bereits beendet – der Abschlussbericht wird angezeigt.")
        print(" Neuer Test:  python start.py --neu")
    else:
        print(" Neuer Test gestartet.")
    print(f" Startkapital : {eur(engine.cfg.start_capital_eur)} (virtuell)")
    print(f" Teststart    : {local_dt(test['start_ts'])}")
    print(f" Testende     : {local_dt(test['end_ts'])}  "
          f"(Dauer {duration_text(engine.cfg.duration_seconds)})")
    print(f" Marktprüfung : alle {engine.cfg.poll_seconds} Sekunden, "
          f"{engine.cfg.candle_minutes}-Minuten-Kerzen")
    print(f" Dashboard    : {url}")
    if args.host == "0.0.0.0":
        print("                (im WLAN: http://<IP-Adresse-dieses-Rechners>:%d)" % server.port)
    if engine.resumed and test["status"] == "running" and (
            cfg.poll_seconds != engine.cfg.poll_seconds or cfg.candle_minutes != engine.cfg.candle_minutes
            or abs(cfg.duration_hours - engine.cfg.duration_hours) > 1e-9):
        print(" Hinweis: Der laufende Test behält seine ursprünglichen Einstellungen.")
    if abs(engine.cfg.duration_hours - 72.0) > 1e-9:
        print(" Hinweis: Testdauer weicht von den vorgesehenen 72 Stunden ab (Probelauf).")
    print(" Beenden mit Strg+C – der Zustand bleibt gespeichert und wird beim")
    print(" nächsten Start wiederhergestellt.")
    print("=" * 68, flush=True)

    stop_event = threading.Event()

    def handle_signal(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    try:
        signal.signal(signal.SIGTERM, handle_signal)
    except (AttributeError, ValueError):
        pass

    server.start()
    engine.start()
    if not args.kein_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    finished_announced = test["status"] == "finished"
    try:
        while not stop_event.is_set():
            stop_event.wait(1.0)
            if not finished_announced and engine.test["status"] == "finished":
                finished_announced = True
                print(f"\n[{local_dt(time.time())}] Test beendet. Abschlussbericht im Dashboard und im "
                      f"Ordner {os.path.join(args.daten, 'berichte')}.", flush=True)
                print("Das Dashboard bleibt erreichbar, bis du mit Strg+C beendest.", flush=True)
    finally:
        print("\nBeende … Zustand wird gespeichert.", flush=True)
        engine.stop()
        server.stop()
        storage.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
