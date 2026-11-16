---
created: 2026-11-14
project: "[[Ei-Alarm!]]"
---

Die vier Kreaturen des Builds. Jede soll schon als Silhouette erkennbar sein und eine Bewegung haben, die es bei keiner anderen gibt.

| Kreatur | Seltenheit | Münzen pro Sekunde | Bewegung | Laut |
| --- | --- | --- | --- | --- |
| Waffelkrabbe | Gewöhnlich | 2 | hüpft seitwärts | zwei hölzerne Klacker |
| Toaster-Gecko | Selten | 6 | spuckt beim Erschrecken Toast aus | Toaster-„Ka-tschick“ mit kurzem Quieken |
| Pudding-Golem | Episch | 15 | stapft, die obere Stufe schwappt nach | tiefes, wabbelndes „Blubb“ |
| Donut-Drache | Legendär | 50 | schwebt, schlägt mit Zuckerguss-Flügeln | helles Fauchen mit Glöckchen |

Die Werte stehen in `Config.Creatures`. Welche Kreatur schlüpft, hängt vom Ei-Typ ab (`Config.EggTypes`). Gewürfelt wird auf dem Server.

## Ei-Typen

| Ei | Seltenheit | Chance in der Mitte | Brutzeit | Aussehen |
| --- | --- | --- | --- | --- |
| Labor-Ei | Gewöhnlich | 70 % | 30 s | cremeweiß, braune Flecken, jedes Muster anders |
| Kühlfach-Ei | Selten | 22 % | 40 s | eisblau, Schneehaube, Eiskristalle |
| Tresor-Ei | Episch | 7 % | 55 s | dunkles Metall, Goldbänder, Zahlenschloss, Lichtsäule |
| Kometen-Ei | Legendär | 1 % | 75 s | violett, Sterne, schräger Goldring, Funkeln, Lichtsäule |

## Waffelkrabbe

- Körper: eine runde Waffel mit Gittermuster, flach, leicht gewölbt. Obenauf ein Klecks Sirup als Farbakzent.
- Scheren: zwei rote, kugelige Scheren, übergroß. Sie machen die Silhouette.
- Beine: je drei kurze Waffelröllchen pro Seite, als ein Block pro Seite geriggt.
- Augen: zwei schwarze Kugeln auf kurzen Stielen an der Vorderkante.
- Farben: Waffel `#DEAA5A`, Sirup `#96501E`, Scheren `#EB5A46`.
- Charakter: nervös, immer in Bewegung, läuft nie geradeaus.

## Toaster-Gecko

- Körper: ein Zweischlitz-Toaster aus gebürstetem Metall mit abgerundeten Kanten. Aus einem Schlitz ragt eine Toastscheibe.
- Kopf, Schwanz, Beine: grüner Gecko. Breiter Kopf mit großen Augen vorn am Toaster, langer Schwanz hinten, vier kurze Beine mit Haftzehen.
- Detail: der Hebel an der Seite. Er springt hoch, wenn der Toast fliegt.
- Farben: Metall `#CDD2DC`, Gecko `#6EBE78`, Toast `#C88C46`.
- Charakter: steht still und döst. Kommt ein fremder Spieler nah heran oder geht der Alarm seiner Basis los, erschrickt er, springt hoch und spuckt Toast aus. Er ist damit auch eine kleine Alarmanlage für die Basis.

## Pudding-Golem

- Körper: ein großer Wackelpudding in Sturzform, zwei Stufen, oben Karamellsoße, die an den Seiten herunterläuft.
- Arme: zwei dicke Puddingstummel ohne Hände. Keine sichtbaren Beine, der Körper rutscht und stampft.
- Augen: zwei kleine schwarze Kugeln, weit oben und eng beieinander. Das wirkt gutmütig und etwas langsam.
- Farben: Pudding `#FAD678`, Karamell `#8C4B1E`.
- Charakter: schwer und gemütlich. Jeder Schritt lässt die oberen Stufen nachschwingen.

## Donut-Drache

- Körper: Hefeteig-Ellipsoid mit cremefarbenem Bauch, rosa Glasur auf dem Rücken, bunte Streusel.
- Kopf: auf schrägem Hals, kurze Schnauze, zwei cremefarbene Hörner.
- Flügel: halbtransparente Zuckerguss-Membranen mit Teig-Knochen.
- Schwanz: endet in einem Mini-Donut.
- Farben: Teig `#D69650`, Glasur `#FF88BA`, Creme `#FADEA6`.
- Charakter: stolz und verspielt. Schwebt immer etwas über dem Boden.

## Platzhalter im ersten Build

`MapBuilder.buildCreature` baut jede Kreatur aus fünf bis zwölf Parts in diesen Farben. Die Bewegungen laufen im Client-Skript (`animateCreature`). Beides wird in Phase 3 und 4 durch die Modelle und Animationen aus [[Ei-Alarm Blender-Pipeline]] und [[Ei-Alarm Animationen]] ersetzt.

## Ideen für später

- Eier in Stufen (Labor-Ei, Kühlfach-Ei, Tresor-Ei) mit eigenen Kreaturenlisten. Alle erspielbar, keines käuflich.
- Seltene Farbvarianten derselben Kreatur statt immer neuer Modelle. Das spart Dreiecke und Arbeit.
