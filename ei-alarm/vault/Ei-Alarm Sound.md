---
created: 2026-11-14
project: "[[Ei-Alarm!]]"
---

Sound soll beim Spielen helfen: Jeder Laut gehört zu genau einem Ereignis und ist auch ohne Bild erkennbar.

## Übersicht

| Sound | Charakter | Länge | Volume | Hörweite (Min / Max) | Auslöser |
| --- | --- | --- | --- | --- | --- |
| Alarm | zwei Töne im Wechsel, hoch-tief, klar und trocken | 0,7 s Schleife, 4 s lang | 0,9 | 16 / 75 Studs | 2,5 s nach einem Diebstahl, an der Lampe der bestohlenen Basis |
| Ei-Knacken | trockenes, kurzes Knacken ohne Hall | 0,3 s | 0,8 | 8 / 45 | Schlupf, beim Marker `Crack` |
| Ei-Zappeln | leises Rappeln, wie ein Kern in einer Dose | 0,4 s Schleife | 0,35 | 4 / 25 | solange ein geklautes Ei getragen wird |
| Waffelkrabbe | zwei hölzerne Klacker | 0,25 s | 0,6 | 6 / 35 | Landung nach dem Hüpfer, höchstens alle 3 s |
| Toaster-Gecko | Toaster-„Ka-tschick“ mit kurzem Quieken | 0,5 s | 0,6 | 6 / 35 | Erschrecken, beim Marker `ToastOut` |
| Pudding-Golem | tiefes, wabbelndes „Blubb“, Tonhöhe fällt ab | 0,6 s | 0,7 | 6 / 40 | jeder zweite Schritt |

Die Werte für Alarm, Knacken und die drei Kreaturen stehen schon in `Config.Sounds`. Dort fehlen nur die Asset-IDs. Das Zappeln ist im ersten Build noch nicht eingebaut.

## Hörweite des Alarms

Maße der Map: Eine Basis ist 30 × 26 Studs groß. Von der Alarmlampe bis zur Hallenmitte sind es etwa 60 Studs, bis zur Mitte der Nachbarbasis etwa 80, bis zur gegenüberliegenden etwa 105.

Einstellung: `RollOffMode = InverseTapered`, `RollOffMinDistance = 16`, `RollOffMaxDistance = 75`.

| Standort des Hörers | Eindruck |
| --- | --- |
| In der bestohlenen Basis (bis 16 Studs) | volle Lautstärke |
| Bis etwa 40 Studs, also vor der Basis und im nahen Teil der Halle | deutlich, die Richtung ist erkennbar |
| Hallenmitte (60 Studs) | leise |
| Nachbarbasis und gegenüberliegende Basis | still |

Das sind Richtwerte aus den Abständen. Wie laut es wirklich wirkt, zeigt erst der Test mit dem echten Sound.

So erkennt man den Alarm in der Nähe der Basis gut, und er verrät trotzdem nicht der ganzen Map, wo gerade geklaut wird. Der Besitzer bekommt zusätzlich das Banner „EI-ALARM!“, egal wo er steht. Für Phase 4 sinnvoll: ein kurzer, nicht räumlicher Ton nur für den Besitzer (Sound in `SoundService`, vom Client abgespielt), 0,3 s, Volume 0,5.

Der Alarmton läuft 4 Sekunden (`Config.AlarmSoundTime`), die Lampe blinkt bis zum Ende der Flucht. Ein Dauerton über 60 Sekunden würde nerven und die Kreaturenlaute überdecken.

## Sounds selbst erstellen

| Sound | Vorschlag |
| --- | --- |
| Alarm | Synthesizer oder jsfxr: Rechteckwelle, 880 Hz für 0,25 s, 660 Hz für 0,25 s, 0,2 s Pause. Keine Sirene mit gleitender Tonhöhe, die klingt nach Polizei und ist schlechter zu orten |
| Ei-Knacken | einen trockenen Zweig oder eine leere Eierschale nah am Mikrofon brechen. Anfang hart schneiden, Ausklang auf 0,2 s kürzen |
| Ei-Zappeln | ein Kirschkern in einer kleinen Blechdose, kurz schütteln |
| Waffelkrabbe | zwei Holzlöffel oder Kastagnetten |
| Toaster-Gecko | einen echten Toaster auslösen und aufnehmen, das Quieken mit einem Gummitier oder der eigenen Stimme, eine Oktave höher gestimmt |
| Pudding-Golem | einen Löffel in Wackelpudding oder Joghurt drücken, die Aufnahme eine halbe Oktave tiefer stimmen |

Aufbereitung in Audacity: Mono, 44,1 kHz, Stille am Anfang wegschneiden (der Laut muss sofort einsetzen), auf −1 dB normalisieren, als OGG oder MP3 exportieren.

## Lizenz

Nur diese Quellen verwenden:

1. Selbst aufgenommen oder selbst synthetisiert.
2. Audio aus dem Creator Store von Roblox, das für die Nutzung in Experiences freigegeben ist.
3. Fremde Aufnahmen mit Lizenz CC0. Bei CC BY ist eine Namensnennung nötig, dafür einen Abschnitt „Credits“ in der Spielbeschreibung anlegen. Keine Aufnahmen mit „NC“ (nicht kommerziell), sobald der Shop live ist.

Zu jeder Datei in dieser Notiz festhalten: Quelle, Lizenz, Datum, Asset-ID.

| Sound | Quelle | Lizenz | Asset-ID |
| --- | --- | --- | --- |
| Alarm | | | |
| Ei-Knacken | | | |
| Ei-Zappeln | | | |
| Waffelkrabbe | | | |
| Toaster-Gecko | | | |
| Pudding-Golem | | | |

## Einbau

1. In Studio über **Asset Manager → Audio** oder im Creator Hub hochladen. Der Upload wird moderiert, das kann einige Minuten dauern.
2. Asset-ID in `Config.Sounds` eintragen, Format `rbxassetid://123456`.
3. Im Zwei-Spieler-Test prüfen: Player1 stellt sich in die eigene Basis, in die Hallenmitte und in die gegenüberliegende Basis, während Player2 den Alarm auslöst. Die Tabelle oben muss stimmen, sonst `min` und `max` anpassen.
