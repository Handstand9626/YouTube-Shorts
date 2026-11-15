# KI Crypto Trader auf dem Steam Deck (SteamOS)

Schritt-für-Schritt-Anleitung für den 72-Stunden-Test auf dem Steam Deck.
Alles bleibt Simulation: kein echtes Geld, keine echten Orders.

> Hinweis: Diese Anleitung wurde nicht auf einem echten Steam Deck getestet.
> Menünamen können je nach SteamOS-Version leicht abweichen.

Tipp: Mit **Steam-Taste + X** öffnest du jederzeit die Bildschirmtastatur.
Eine USB- oder Bluetooth-Tastatur macht das Tippen deutlich einfacher.

---

## Teil 1: Vorbereitung (einmalig)

### Schritt 1: In den Desktop-Modus wechseln

1. **Steam-Taste** drücken.
2. **Ein/Aus** wählen.
3. **Zum Desktop wechseln** wählen.

### Schritt 2: Browser installieren (falls keiner da ist)

1. Unten links auf das **Anwendungsmenü** (SteamOS-Logo) tippen.
2. **Discover** öffnen.
3. Nach **Firefox** suchen und **Installieren** wählen.

### Schritt 3: Programm herunterladen

1. Firefox öffnen und das GitHub-Repository öffnen:
   `https://github.com/Handstand9626/YouTube-Shorts`
2. Bei Bedarf bei GitHub anmelden.
3. Oben links auf die Branch-Auswahl (zeigt `main`) tippen und
   **`ccr-fa89e440-l707bl`** wählen.
4. Grünen Knopf **Code** → **Download ZIP** wählen.
5. Die Datei landet im Ordner **Downloads**.

### Schritt 4: ZIP-Datei entpacken

1. Den Dateimanager **Dolphin** öffnen (Ordner-Symbol in der Taskleiste).
2. Links **Downloads** wählen.
3. Rechtsklick (linker Trigger **L2**) auf die ZIP-Datei → **Entpacken** → **Hier entpacken**.
4. Es entsteht der Ordner `YouTube-Shorts-ccr-fa89e440-l707bl`.

### Schritt 5: Ruhezustand ausschalten

Ohne diesen Schritt schläft das Steam Deck ein und der Test stoppt.

1. Anwendungsmenü → **Systemeinstellungen** öffnen.
2. **Energieverwaltung** (oder „Energiesparen“) wählen.
3. Im Bereich **Netzbetrieb**:
   - „Bildschirm-Energiesparen“ / „Bildschirm ausschalten“: darf an bleiben.
   - **„Standby“ / „Ruhezustand“ ausschalten.**
4. **Anwenden** wählen.
5. Steam Deck **ans Ladegerät** anschließen.

---

## Teil 2: Test starten

### Schritt 6: Konsole öffnen

Anwendungsmenü → **System** → **Konsole**.

### Schritt 7: In den Programmordner wechseln

In der Konsole eingeben und **Enter** drücken:

```
cd ~/Downloads/YouTube-Shorts-ccr-fa89e440-l707bl/ki-crypto-trader
```

### Schritt 8: Python prüfen

```
python3 --version
```

Es muss eine Zeile wie `Python 3.11.x` (oder höher) erscheinen.

### Schritt 9: Test starten

Nur auf dem Steam Deck ansehen:

```
./start.sh
```

Zusätzlich auf dem Handy ansehen:

```
./start.sh --handy
```

Erscheint `Permission denied`, stattdessen eingeben:

```
python3 start.py --handy
```

### Schritt 10: Dashboard öffnen

- Der Browser öffnet sich automatisch.
- Falls nicht: In Firefox `http://localhost:8000` eingeben.
- In der Konsole stehen **Teststart** und **Testende** (genau 72 Stunden später).

### Schritt 11: Aufs Handy holen (optional)

1. In der Konsole steht eine Zeile wie `Am Handy : http://192.168.178.23:8000`.
2. Handy ins **selbe WLAN** wie das Steam Deck bringen.
3. Diese Adresse im Handy-Browser öffnen.
4. Als App ablegen:
   - iPhone (Safari): Teilen → **Zum Home-Bildschirm**
   - Android (Chrome): Menü ⋮ → **App installieren**

---

## Teil 3: Während der 72 Stunden

**Wichtig:**

- **Im Desktop-Modus bleiben.** Wer in den Spielmodus wechselt, beendet das Programm.
- **Konsolenfenster nicht schließen.** Das Fenster darf minimiert sein.
- Steam Deck **am Ladegerät** und **mit WLAN verbunden** lassen.
- Das Browserfenster darfst du schließen und wieder öffnen; der Test läuft weiter.

### Wenn der Test unterbrochen wurde

Zum Beispiel durch Spielmodus, Neustart oder leeren Akku:

1. Wieder in den Desktop-Modus wechseln (Schritt 1).
2. Konsole öffnen (Schritt 6).
3. Diese zwei Befehle eingeben:

   ```
   cd ~/Downloads/YouTube-Shorts-ccr-fa89e440-l707bl/ki-crypto-trader
   ./start.sh --handy
   ```

Der Test läuft mit dem gespeicherten Stand weiter. Das Testende bleibt gleich.
Die Pause wird im Dashboard und im Bericht vermerkt.

---

## Teil 4: Nach 72 Stunden

1. Der Test endet automatisch. In der Konsole erscheint **„Test beendet“**.
2. Im Dashboard unter **Bericht**: **Bericht als PDF** oder **Bericht als CSV** wählen.
3. Alle Berichtsdateien liegen zusätzlich hier:
   `~/Downloads/YouTube-Shorts-ccr-fa89e440-l707bl/ki-crypto-trader/data/berichte/`
4. Programm beenden: In der Konsole **Strg + C** drücken.
5. Zurück zum Spielen: Desktop-Symbol **Zum Spielmodus zurückkehren**.

### Neuen Test beginnen

```
cd ~/Downloads/YouTube-Shorts-ccr-fa89e440-l707bl/ki-crypto-trader
./start.sh --neu
```

Der alte Test wird nicht gelöscht, sondern nach `data/archiv/` verschoben.

---

## Probleme lösen

| Problem | Lösung |
|---|---|
| `No such file or directory` bei `cd` | Ordnername in Dolphin prüfen und im Befehl anpassen. |
| `Permission denied` bei `./start.sh` | `python3 start.py` statt `./start.sh` verwenden. |
| `Es läuft bereits ein KI Crypto Trader …` | Es ist schon ein Konsolenfenster mit dem Test offen. Dieses benutzen. |
| `Port 8000 … konnte nicht starten` | `./start.sh --port 8001` und dann `http://localhost:8001` öffnen. |
| Handy findet die Adresse nicht | Gleiches WLAN prüfen. Mit `--handy` gestartet? |
| Dashboard zeigt „Pausiert aufgrund fehlender Daten“ | WLAN-Verbindung prüfen. Das Programm versucht es automatisch weiter. |
