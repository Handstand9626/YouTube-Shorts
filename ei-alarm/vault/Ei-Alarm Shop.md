---
created: 2026-11-14
project: "[[Ei-Alarm!]]"
---

Entwurf für den Robux-Shop. Umsetzung erst nach dem ersten Multiplayer-Test (Phase 6 im Bauplan von [[Ei-Alarm!]]), wenn die Kernschleife Spaß macht.

## Grundsätze

- Nur Kosmetik. Kein Kauf verändert Tempo, Reichweite, Brutzeit, Schlupfchancen, Schutz oder Einkommen.
- Nur feste Käufe. Der Spieler sieht vorher genau, was er bekommt. Keine bezahlten Zufallsinhalte.
- Zufallseier sind ausschließlich erspielbar, nie käuflich und nie in einem Paket versteckt.
- Alle Spieler haben dieselben Chancen beim Klauen und Verteidigen.
- Kein Druck: keine Countdown-Angebote, keine Einblendungen während einer Flucht.

## Sortiment

**Brutmaschinen-Skins** (verändern das Aussehen aller eigenen Brutstationen)

| Skin | Aussehen | Preis |
| --- | --- | --- |
| Lavalampe | Glaskuppel mit langsam steigenden Farbblasen | 99 R$ |
| Kaugummiautomat | rote Kuppel, Drehgriff, Münzschlitz | 99 R$ |
| Eisfach | Reif auf dem Glas, kalter Nebel am Sockel | 149 R$ |

**Emotes**

| Emote | Bewegung | Preis |
| --- | --- | --- |
| Eiertanz | vorsichtiges Tippeln auf Zehenspitzen | 49 R$ |
| Rührei-Shuffle | Arme rühren im Kreis, Hüfte schwingt | 49 R$ |
| Alarm-Winken | beide Arme kreisen wie eine Warnleuchte | 79 R$ |

Emotes lassen sich nicht abspielen, solange man ein Ei trägt. Sonst würden sie die Trage-Animation verdecken.

**Schlupfeffekte** (ersetzen die Partikel beim Schlupf der eigenen Eier)

| Effekt | Aussehen | Preis |
| --- | --- | --- |
| Konfetti-Knall | bunte Papierschnipsel | 99 R$ |
| Toast-Regen | kleine Toastscheiben regnen herab | 149 R$ |
| Pudding-Platscher | gelbe Kleckse spritzen zur Seite | 149 R$ |

**Paket**

| Paket | Inhalt | Preis |
| --- | --- | --- |
| Laborstarter | Kaugummiautomat, Eiertanz, Konfetti-Knall | 199 R$ statt 247 R$ |

Die Preise sind Startwerte. Zusätzlich gibt es je Kategorie ein Teil für Münzen, damit auch Spieler ohne Robux ihre Basis gestalten können.

## Technik

- Jedes Teil ist ein **Game Pass**. Game Passes sind dauerhaft und passen damit zu Kosmetik. Developer Products wären für verbrauchbare Käufe, die es hier nicht gibt.
- Kauf: Der Client öffnet nur das Kauffenster (`MarketplaceService:PromptGamePassPurchase`). Der Server reagiert auf `PromptGamePassPurchaseFinished` und prüft den Besitz selbst mit `UserOwnsGamePassAsync`. Der Client behauptet nie, etwas zu besitzen.
- Besitz beim Beitritt prüfen und pro Sitzung merken. Fehlgeschlagene Abfragen in `pcall` fangen und später wiederholen.
- Ausgewählte Kosmetik im DataStore speichern (Phase 5 liefert das Speichersystem). Der Server setzt sie als Attribute an Basis und Spieler, die Clients zeichnen sie.
- Shop-Oberfläche: ein Knopf am Bildschirmrand öffnet ein Fenster mit drei Reitern. Jedes Teil zeigt Vorschau, Namen und Preis. Besessene Teile zeigen „Ausrüsten“.
- Schlupfeffekte und Skins sind reine Darstellung und belasten Smartphones wenig: höchstens 40 Partikel pro Effekt, keine zusätzlichen Lichter.

## Vor dem Start prüfen

- Die aktuellen Roblox-Richtlinien zu Käufen und zur Altersfreigabe lesen. Sie ändern sich, und dieser Entwurf ersetzt das nicht.
- Im Studio-Test sind Käufe kostenlos. Jeden Game Pass einmal kaufen und prüfen: Besitz wird erkannt, Kosmetik erscheint bei beiden Spielern, nach erneutem Beitritt ist sie noch da.
- Gegenprobe Fairness: Zwei Spieler, einer mit allen Käufen. Brutzeit, Tempo, Abfangreichweite und Schlupfchancen müssen identisch sein. Die Regeltests in `CoreSelfTest` dürfen den Shop gar nicht kennen.
