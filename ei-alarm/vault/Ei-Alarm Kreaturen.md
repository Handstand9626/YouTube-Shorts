---
created: 2026-11-14
project: "[[Ei-Alarm!]]"
---

Die drei Kreaturen des ersten Builds. Jede soll schon als Silhouette erkennbar sein und eine Bewegung haben, die es bei keiner anderen gibt.

| Kreatur | Chance | Münzen pro Sekunde | Bewegung | Laut |
| --- | --- | --- | --- | --- |
| Waffelkrabbe | 60 % | 2 | hüpft seitwärts | zwei hölzerne Klacker |
| Toaster-Gecko | 30 % | 5 | spuckt beim Erschrecken Toast aus | Toaster-„Ka-tschick“ mit kurzem Quieken |
| Pudding-Golem | 10 % | 12 | wackelt bei jedem Schritt | tiefes, wabbelndes „Blubb“ |

Die Werte stehen in `Config.Creatures`. Gewürfelt wird auf dem Server.

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

## Platzhalter im ersten Build

`MapBuilder.buildCreature` baut jede Kreatur aus fünf bis zwölf Parts in diesen Farben. Die Bewegungen laufen im Client-Skript (`animateCreature`). Beides wird in Phase 3 und 4 durch die Modelle und Animationen aus [[Ei-Alarm Blender-Pipeline]] und [[Ei-Alarm Animationen]] ersetzt.

## Ideen für später

- Eier in Stufen (Labor-Ei, Kühlfach-Ei, Tresor-Ei) mit eigenen Kreaturenlisten. Alle erspielbar, keines käuflich.
- Seltene Farbvarianten derselben Kreatur statt immer neuer Modelle. Das spart Dreiecke und Arbeit.
