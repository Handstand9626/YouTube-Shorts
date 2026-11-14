---
created: 2026-11-14
project: "[[Ei-Alarm!]]"
---

Keyframes für die wichtigsten Animationen. Alle Zeiten bei 30 Bildern pro Sekunde, Bildnummern in Klammern. Jede Animation soll ohne Text zeigen, was gerade passiert.

Wichtig für Roblox: Animationen speichern pro Knochen nur Position und Drehung, keine Skalierung. Stauchen und Strecken entsteht deshalb durch verschobene Knochen oder per Skript, nicht durch Scale-Keys.

Winkel sind Richtwerte. Die Achsen hängen von der Ausrichtung der Knochen im Rig ab, im Zweifel nach Augenmaß einstellen.

## Ei: Schlupf

Länge 1,2 s, keine Schleife, Priorität `Action`. Knochen: `Root`, `ShellBottom`, `ShellTop`. Der Server-Platzhalter in `Main` nutzt bereits dieselben Zeiten, die Kreatur erscheint bei 0,95 s.

| Zeit | Pose |
| --- | --- |
| 0,00 s (0) | Ruhe. `Root` gerade |
| 0,10 s (3) | Wackler 1: `Root` 14° nach rechts gekippt |
| 0,22 s (7) | `Root` 14° nach links |
| 0,30 s (9) | `Root` gerade |
| 0,40 s (12) | Wackler 2: `Root` 14° nach rechts |
| 0,52 s (16) | `Root` 14° nach links |
| 0,60 s (18) | `Root` gerade. Beginn der Pause |
| 0,88 s (26) | Ende der Pause, bis hier keine Bewegung. Die Stille macht den Knall |
| 0,92 s (28) | Ausholen: `ShellTop` 0,1 Studs nach unten gedrückt |
| 0,95 s (29) | Aufplatzen: `ShellTop` 1,2 Studs nach oben, 70° nach hinten gekippt. `ShellBottom` 0,15 nach unten. Marker `Crack` |
| 1,05 s (32) | `ShellTop` 1,6 Studs hoch und 0,8 nach hinten, 140° gekippt |
| 1,20 s (36) | `ShellTop` liegt hinter dem Ei am Boden, 180° gedreht |

Kurven: Wackler mit weichem Ein- und Ausklang (Sine), das Aufplatzen bei 0,95 s linear und hart. Der Marker `Crack` löst Knack-Sound und Partikel aus (`GetMarkerReachedSignal("Crack")`).

## Spieler: Ei tragen

Länge 0,8 s, Schleife, Priorität `Action`. R15-Charakter. Nur Oberkörper und Arme bekommen Keys, damit die normale Laufanimation für die Beine weiterläuft.

Grundpose, gilt in jedem Keyframe:

| Knochen | Pose |
| --- | --- |
| `UpperTorso` | 6° nach hinten gelehnt, Gegengewicht zum Ei |
| `Head` | 10° nach unten, Blick aufs Ei |
| `RightUpperArm`, `LeftUpperArm` | 75° nach vorn gehoben, 20° zur Körpermitte gedreht |
| `RightLowerArm`, `LeftLowerArm` | 70° gebeugt, Unterarme liegen quer vor der Brust |
| `RightHand`, `LeftHand` | 15° nach innen, Hände umfassen das Ei |

Das Zappeln kommt als kleine Störung auf die Grundpose:

| Zeit | Störung |
| --- | --- |
| 0,00 s (0) | Grundpose |
| 0,13 s (4) | Ei ruckt nach rechts: `UpperTorso` 3° nach rechts gedreht, rechter Oberarm 5° weiter außen, `Head` 4° nach rechts |
| 0,27 s (8) | Nachfassen: beide Unterarme 6° stärker gebeugt, `UpperTorso` zurück zur Mitte |
| 0,40 s (12) | Ei ruckt nach links: Spiegelbild von 0,13 s |
| 0,53 s (16) | Nachfassen wie bei 0,27 s |
| 0,67 s (20) | Ei ruckt nach oben: beide Oberarme 6° höher, `Head` 6° zurück |
| 0,80 s (24) | Grundpose, Schleife schließt |

Ein Ei aus der Mitte zappelt nicht. Dafür dieselbe Grundpose als zweite Animation ohne Störung anlegen, oder die Tragen-Animation mit halber Geschwindigkeit und geringem Gewicht abspielen.

Das Ei selbst bewegt der Client per Skript (`updateCarriedEggs`). Wenn die Animation steht, den Ausschlag dort an die Rucke anpassen.

## Waffelkrabbe: Seitwärtshüpfer

Länge 0,73 s, Schleife, Priorität `Movement`. Auf der Stelle animiert, die Seitwärtsbewegung macht das Skript. Knochen: `Body`, `ClawL`, `ClawR`, `LegsL`, `LegsR`.

| Zeit | Pose |
| --- | --- |
| 0,00 s (0) | Ruhe |
| 0,07 s (2) | Ducken: `Body` 0,15 Studs tiefer, Beine 15° gespreizt |
| 0,17 s (5) | Absprung: `Body` 0,6 hoch, Beine 20° angezogen, Scheren 30° hochgerissen |
| 0,27 s (8) | Scheitelpunkt: `Body` 0,9 hoch und 8° in Hüpfrichtung gerollt, Scheren offen |
| 0,37 s (11) | Sinken: `Body` 0,4 hoch, Rollen zurück auf 0° |
| 0,43 s (13) | Landung: `Body` 0,12 tiefer, Beine 20° gespreizt, Scheren schnappen zu. Marker `Clack` |
| 0,53 s (16) | Ausfedern auf Ruhe |
| 0,73 s (22) | Ruhe halten, dann Schleife |

Das Skript spiegelt die Rollrichtung, wenn die Krabbe die Richtung wechselt.

## Toaster-Gecko: Erschrecken

Länge 0,9 s, keine Schleife, Priorität `Action`. Knochen: `Body`, `Head`, `Tail1`, `Tail2`, `Toast`, vier Beine.

| Zeit | Pose |
| --- | --- |
| 0,00 s (0) | Ruhe |
| 0,07 s (2) | Zusammenzucken: `Body` 0,2 tiefer, `Head` 10° eingezogen, `Tail1` 25° eingerollt |
| 0,17 s (5) | Sprung: `Body` 1,2 hoch, alle Beine 40° abgespreizt, `Head` 20° nach oben, `Toast` 0,5 nach oben aus dem Schlitz. Marker `ToastOut` |
| 0,20 s (6) | `Toast` zurück im Schlitz (0,4 tiefer als in Ruhe, also unsichtbar). Den fliegenden Toast erzeugt das Skript als eigenes Part |
| 0,33 s (10) | Scheitelpunkt halten: `Body` 1,3 hoch, Schwanz gestreckt |
| 0,50 s (15) | Landung: `Body` 0,15 tiefer, Beine 20° gespreizt |
| 0,60 s (18) | `Body` auf Ruhe |
| 0,70 s (21) | Schwanzwedeln: `Tail1` 12° rechts, `Tail2` 18° rechts |
| 0,80 s (24) | `Tail1` 12° links, `Tail2` 18° links |
| 0,90 s (27) | Ruhe. `Toast` wieder in normaler Höhe |

Dazu eine Ruhe-Schleife, 2,0 s, Priorität `Idle`: `Body` atmet 0,04 Studs auf und ab, `Tail1` schwingt 6° hin und her, bei 1,5 s ein Lidschlag über ein kurzes Nicken des `Head` (4°).

## Pudding-Golem: Stapfen

Länge 1,8 s (zwei Schritte je 0,9 s), Schleife, Priorität `Movement`. Knochen: `Body`, `Top`, `Caramel`, `ArmL`, `ArmR`. Das Nachschwingen von `Top` und `Caramel` ist die eigentliche Animation.

Erster Schritt, links:

| Zeit | Pose |
| --- | --- |
| 0,00 s (0) | `Body` 6° nach rechts geneigt, Gewicht geht vom linken Rand |
| 0,10 s (3) | `Body` 0,25 Studs hoch, `ArmL` 20° nach vorn |
| 0,20 s (6) | Aufsetzen: `Body` 0,1 tiefer und gerade. Marker `Step` |
| 0,27 s (8) | `Top` 12° nach vorn geschwappt |
| 0,33 s (10) | `Caramel` 16° nach vorn, zwei Bilder nach `Top` |
| 0,40 s (12) | `Top` 9° nach hinten |
| 0,47 s (14) | `Caramel` 12° nach hinten |
| 0,53 s (16) | `Top` 6° nach vorn |
| 0,67 s (20) | `Top` 3° nach hinten, `Caramel` 4° nach vorn |
| 0,80 s (24) | `Top` und `Caramel` gerade, `Body` auf Ruhe |

Zweiter Schritt, rechts: dieselben Keys gespiegelt von 0,90 s (27) bis 1,80 s (54).

Regel für das Wackeln: jeder Ausschlag hat etwa drei Viertel der Stärke des vorigen, `Caramel` folgt `Top` mit zwei Bildern Verzögerung und einem Drittel mehr Ausschlag.

## Einbau

1. Animation in Blender als eigene Action anlegen, als FBX exportieren und im Animation Editor importieren (siehe [[Ei-Alarm Blender-Pipeline]]).
2. Im Animation Editor Schleife und Priorität setzen, Marker eintragen, veröffentlichen.
3. Asset-IDs in `Config` unter einem neuen Abschnitt `Animations` ablegen.
4. Abspielen: `Animator:LoadAnimation(animation):Play()`. Kreaturen auf dem Client, die Tragen-Animation ebenfalls auf dem Client des Trägers (Animationen des eigenen Charakters replizieren automatisch).
