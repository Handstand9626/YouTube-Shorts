---
categories:
  - "[[Projects]]"
  - "[[Games]]"
type:
  - "[[Roblox-Spiel]]"
org: []
start: 2026-11-14
year: 2026
url:
status: "Phase 1 geliefert, Studio-Test offen"
maker:
genre:
  - "[[Multiplayer]]"
  - "[[Sammeln und Klauen]]"
system: "[[Roblox]]"
---

Multiplayer-Spiel für Roblox. In einem verrückten Brutlabor sammeln Spieler Eier, brüten absurde Kreaturen aus und verdienen mit ihnen Münzen. Der besondere Moment ist die Flucht mit einem geklauten, zappelnden Ei.

Genre-Vorbilder sind Sammel-und-Klau-Spiele. Kreaturen, Namen, Modelle, Sounds und Map sind eigene Entwürfe.

## Kernschleife

1. Ei aus der zentralen Eierstation holen oder aus einer fremden Brutstation klauen.
2. Mit dem Ei zur eigenen Basis fliehen: kurz durch die offene Halle oder lang durch die Lüftung.
3. Ei in die eigene Brutstation setzen. Erst dann gehört es dir.
4. Ausbrüten. Geschlüpfte Kreaturen sind sicher und verdienen Münzen.

Regeln, die das Spiel fair halten:

- Jeder bekommt ein geschütztes Start-Ei.
- Alle haben dieselben Chancen beim Klauen und Verteidigen. Nichts davon ist käuflich.
- Der Server entscheidet über Besitz, Reichweite, Diebstahl, Schlupf und Münzen.

## Bauplan

| Phase | Inhalt | Stand |
| --- | --- | --- |
| 1 | Platzhalter-Build: Map, Eier, Klauen, Alarm, Abfangen, Schlupf, Münzen, automatische Tests | geliefert, siehe `README.md` im Projektordner |
| 2 | Test mit zwei Spielern in Roblox Studio, Fehler beheben, Werte in `Config` ausbalancieren | offen |
| 3 | Modelle aus Blender: Ei, Brutmaschine, drei Kreaturen. Siehe [[Ei-Alarm Blender-Pipeline]] | offen |
| 4 | Animationen und Sounds. Siehe [[Ei-Alarm Animationen]] und [[Ei-Alarm Sound]] | offen |
| 5 | Speichern (DataStore), Verwendung für Münzen, Tempo-Check gegen manipulierte Clients | offen |
| 6 | Robux-Shop für Kosmetik. Siehe [[Ei-Alarm Shop]] | nach dem Multiplayer-Test |

## Notizen

- [[Ei-Alarm Kreaturen]]
- [[Ei-Alarm Blender-Pipeline]]
- [[Ei-Alarm Animationen]]
- [[Ei-Alarm Sound]]
- [[Ei-Alarm Shop]]

## Map des ersten Builds

Quadratische Halle, 120 × 120 Studs, Eierstation mit vier Sockeln in der Mitte. Vier Basen stehen vor den Mitten der vier Wände, 46 Studs vom Zentrum. Hinter jeder Basis führt eine Tür in die Lüftung, einen 8 Studs breiten Ringkorridor um die Halle.

| Strecke | Halle | Lüftung |
| --- | --- | --- |
| Nachbarbasis | ca. 65 Studs | ca. 170 Studs |
| Gegenüberliegende Basis | ca. 92 Studs | ca. 300 Studs |
| Tempo mit Ei | 13 | 16 |
| Sichtbar für den Besitzer | ja | nein, hinter Wänden |

Der Besitzer läuft immer 16. In der Halle holt er den Dieb also ein, in der Lüftung nicht. Dafür ist der Weg dort zweieinhalb- bis dreimal so lang, und der Besitzer kann vor der Basis des Diebs warten. Ob das spannend genug ist, zeigt Phase 2.

## Offene Fragen für Phase 2

- Ist die Lüftung zu lang? Möglich wäre ein Querkanal unter der Halle.
- Soll der Fortschritt eines geklauten Eis erhalten bleiben? Aktuell ja, mit mindestens 8 Sekunden Restzeit.
- Wofür geben Spieler Münzen aus: zusätzliche Brutstationen, schnellere Brutmaschinen, Deko?
