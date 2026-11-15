# Ei-Alarm! – erster spielbarer Build

Multiplayer-Spiel für Roblox Studio (Luau). Spieler holen Eier aus der zentralen Eierstation, brüten sie in ihrer Basis aus und klauen sich brütende Eier gegenseitig. Dieser Abschnitt enthält die komplette Spielmechanik mit Platzhaltern aus Parts. Blender-Modelle, Animationen, Sounds und Shop folgen danach (siehe `vault/Ei-Alarm!.md`).

## Was der Build kann

- Kompakte Map, die das Skript selbst baut: Halle mit vier Basen, zentrale Eierstation, Lüftungsring als zweiter Fluchtweg.
- Jeder Spieler bekommt eine Basis und ein geschütztes Start-Ei.
- Ei nehmen, in die eigene Brutstation setzen, ausbrüten, Münzen verdienen.
- Klauen: Das Ei zappelt, nach 2,5 Sekunden geht der Alarm der bestohlenen Basis los.
- Abfangen: Kommt der Besitzer auf 6 Studs heran, fällt das Ei zu Boden. Er kann es zurückholen.
- Sichern: Wer das Ei in die eigene Brutstation setzt, dem gehört es.
- Drei Kreaturen mit Platzhalter-Bewegung: Waffelkrabbe, Toaster-Gecko, Pudding-Golem. Geschlüpfte Kreaturen sind sicher.

Der Server entscheidet alles: Besitz, Reichweite, Diebstahl, Schlupf und Münzen. Der Client sendet keine eigenen Befehle, er löst nur ProximityPrompts aus, die der Server prüft.

## Explorer-Struktur

```
ReplicatedStorage
└─ EiAlarm                     (Folder)
   └─ Config                   (ModuleScript)
ServerScriptService
└─ EiAlarm                     (Folder)
   ├─ Main                     (Script)
   ├─ EggCore                  (ModuleScript)
   ├─ MapBuilder               (ModuleScript)
   └─ CoreSelfTest             (ModuleScript)
StarterPlayer
└─ StarterPlayerScripts
   └─ EiAlarmClient            (LocalScript)
```

Zur Laufzeit legt der Server zusätzlich an: `ReplicatedStorage/EiAlarm/Remotes/Notify` (RemoteEvent) und `Workspace/EiAlarm` mit `Map`, `Eggs`, `Creatures`, `Base1` bis `Base4` und `EggStation`.

| Skript | Datei in `src/` | Aufgabe |
| --- | --- | --- |
| Config | `ReplicatedStorage/EiAlarm/Config.luau` | Alle Stellschrauben: Zeiten, Tempo, Reichweiten, Kreaturen, Sounds, Map-Maße |
| EggCore | `ServerScriptService/EiAlarm/EggCore.luau` | Spielregeln als reine Logik, ohne Roblox-Instanzen |
| MapBuilder | `ServerScriptService/EiAlarm/MapBuilder.luau` | Baut Map, Eier und Kreaturen aus Parts |
| CoreSelfTest | `ServerScriptService/EiAlarm/CoreSelfTest.luau` | 16 Regeltests, laufen beim Serverstart |
| Main | `ServerScriptService/EiAlarm/Main.server.luau` | Verbindet Regeln und Welt: Prompts, Abfangen, Alarm, Schlupf, Münzen |
| EiAlarmClient | `StarterPlayerScripts/EiAlarmClient.client.luau` | Anzeige: Banner, passende Prompts, Zappeln, Kreaturen-Bewegung |

## Einbau in Roblox Studio

Schnellster Weg: die fertige Place-Datei `Ei-Alarm.rbxlx` in Roblox Studio öffnen (**File → Open from File** oder die Datei auf das Studio-Fenster ziehen). Sie enthält alle Skripte am richtigen Platz und hat StreamingEnabled ausgeschaltet. Nach Änderungen an den Skripten erzeugt `python tools/build_place.py` die Datei neu. Die Place-Datei wurde noch nicht in Studio geöffnet.

Von Hand geht es so:


1. Neues Projekt mit der Vorlage **Baseplate** anlegen.
2. Im Explorer auf **ReplicatedStorage** rechtsklicken, **Insert Object → Folder**, umbenennen in `EiAlarm`. Darin ein **ModuleScript** anlegen, `Config` nennen, den Inhalt löschen und den Inhalt von `Config.luau` einfügen.
3. In **ServerScriptService** einen Folder `EiAlarm` anlegen. Darin drei **ModuleScripts** (`EggCore`, `MapBuilder`, `CoreSelfTest`) und ein **Script** (`Main`) anlegen und jeweils den Inhalt der passenden Datei einfügen. Die Namen müssen exakt stimmen, `Main` lädt die Module über diese Namen.
4. Unter **StarterPlayer → StarterPlayerScripts** ein **LocalScript** `EiAlarmClient` anlegen und den Inhalt von `EiAlarmClient.client.luau` einfügen.
5. **Workspace** anklicken und in den Properties **StreamingEnabled** für den ersten Test ausschalten. Die Map ist klein, so sehen beide Clients sofort alles.
6. Speichern. `Baseplate` und `SpawnLocation` der Vorlage müssen nicht gelöscht werden, das Skript entfernt sie beim Start der Spielsitzung.

Mit Rojo geht es schneller: `rojo serve` in diesem Ordner starten und in Studio mit dem Rojo-Plugin verbinden. `default.project.json` bildet die Struktur oben ab. Diese Projektdatei wurde noch nicht mit Rojo ausprobiert.

Später vor der Veröffentlichung: in den Experience-Einstellungen die maximale Spielerzahl auf 4 stellen. Ein fünfter Spieler wird sonst vom Skript mit einer Meldung abgewiesen.

## Spielablauf

1. Du spawnst in deiner Basis. In Brutstation 1 liegt dein geschütztes Start-Ei, es schlüpft nach 10 Sekunden.
2. In der Hallenmitte liegen bis zu vier Labor-Eier. Prompt **Ei nehmen**, dann zur eigenen Basis und an einer freien Brutstation **Ei einsetzen**. Nach 30 Sekunden schlüpft eine Kreatur.
3. Brütende Eier anderer Spieler zeigen **Ei klauen** (0,6 Sekunden halten). Danach zappelt das Ei, nach 2,5 Sekunden blinkt die Alarmlampe der bestohlenen Basis und der Besitzer bekommt eine Warnung.
4. Fluchtwege: quer durch die Halle (kurz, aber das Ei bremst dich auf 13 statt 16) oder durch die Tür hinter der Basis in die Lüftung (langer Ring, volles Tempo, hinter Wänden).
5. Fängt dich der Besitzer ab, liegt das Ei am Boden. Er hebt es auf und es sitzt wieder in seiner Station. Du bist 1,5 Sekunden gesperrt, danach darfst du wieder zugreifen. Nach 15 Sekunden am Boden kehrt das Ei von selbst zurück.
6. Setzt du das Ei in deine eigene Brutstation, gehört es dir.

## Test in Roblox Studio mit zwei Spielern

Start: Tab **Test**, im Bereich **Clients and Servers** die Einstellungen **Local Server** und **2 Players** wählen, dann **Start**. In der neuen Studio-Oberfläche heißt der Eintrag im Test-Menü **Server & Clients**. Es öffnen sich ein Serverfenster und zwei Clientfenster (Player1, Player2).

Im Output des Serverfensters müssen zuerst diese Zeilen stehen:

```
[Ei-Alarm][Selbsttest] 16 bestanden, 0 fehlgeschlagen
[Ei-Alarm] Server bereit.
```

| # | Aktion | Erwartetes Ergebnis |
| --- | --- | --- |
| 1 | Beide Fenster ansehen | Jeder Spieler steht in einer eigenen farbigen Basis, das Schild über der Lüftungstür zeigt seinen Namen, in Brutstation 1 liegt ein Ei mit der Anzeige „Geschützt“ |
| 2 | 10 Sekunden warten | Das Ei wackelt zweimal, hält kurz inne und platzt auf. Eine Kreatur steht in der Basis, oben rechts steigen die Münzen |
| 3 | Player2 geht zum Start-Ei von Player1, falls es noch brütet | Kein Klau-Prompt sichtbar |
| 4 | Player1 nimmt ein Ei aus der Mitte und setzt es in eine freie Brutstation | Tempo sinkt beim Tragen. Der Prompt **Ei einsetzen** erscheint nur an eigenen freien Stationen. Danach läuft ein 30-Sekunden-Zähler |
| 5 | **Gleichzeitig greifen:** beide Spieler stellen sich an dasselbe Ei in der Mitte und lösen den Prompt möglichst gleichzeitig aus | Genau ein Spieler trägt das Ei. Der andere sieht „Jemand anderes war schneller.“ und trägt nichts |
| 6 | Player2 klaut das brütende Ei von Player1 und läuft los | Das Ei zappelt und ist rot markiert. Nach 2,5 Sekunden blinkt die Lampe in der Basis von Player1, Player1 sieht „EI-ALARM!“ |
| 7 | Player1 läuft Player2 hinterher und holt ihn ein | Das Ei fällt zu Boden. Player2 ist kurz langsam und kann es nicht sofort aufheben |
| 8 | Player1 hebt das Ei auf | Das Ei sitzt wieder in derselben Brutstation, der Alarm ist aus |
| 9 | Player2 klaut erneut, diesmal durch die Lüftung, und setzt das Ei in seine eigene Brutstation | Das Ei gehört Player2. Player1 sieht die Meldung dazu, seine Station ist wieder frei |
| 10 | **Verbindungsabbruch:** Player1 klaut das Ei zurück. Während er es trägt, das Clientfenster von Player1 schließen | Das Ei sitzt sofort wieder in der Station von Player2. Die Basis von Player1 ist leer, das Schild zeigt „Frei“ |
| 11 | Im Serverfenster den Output prüfen | Keine roten Fehlermeldungen |

Für Schritt 5 hilft es, zwei Eingabegeräte zu nutzen oder beide Fenster nebeneinanderzulegen. Trifft man den Moment nicht genau, ist das kein Problem: die Regel wird zusätzlich bei jedem Serverstart automatisch geprüft (Selbsttest „Zwei Spieler, ein Ei“).

## Automatische Tests ohne Studio

```
pip install lupa
python tests/run_tests.py
```

Das Skript prüft drei Dinge mit einem Lua-5.1-Interpreter:

1. Alle sechs Skripte kompilieren.
2. Die 16 Regeltests aus `CoreSelfTest`.
3. Ein kompletter Durchlauf mit zwei Spielern (`tests/scenario.lua`, 87 Prüfungen). Dabei laufen die echten Server- und Client-Skripte gegen einen kleinen Roblox-Nachbau (`tests/roblox_mock.lua`).

Die Skripte nutzen dafür nur den Teil von Luau, der auch gültiges Lua 5.1 ist (kein `+=`, kein `continue`, keine Typannotationen).

Stand der Prüfung: Diese Tests laufen durch. In Roblox Studio selbst liefen die Skripte noch nicht. Der Nachbau simuliert weder Physik noch Replikation noch Darstellung. Was nur der Studio-Test zeigt: ob das getragene Ei sauber am Charakter sitzt, ob Spawnpunkte, Prompts, Banner und Kreaturen-Bewegung richtig aussehen und ob eine Eigenschaft anders heißt als im Nachbau angenommen.

## Stellschrauben

Alle Werte stehen in `Config`. Für das Balancing nach dem ersten Test sind diese am wichtigsten:

| Wert | Standard | Wirkung |
| --- | --- | --- |
| `CarrySpeedHall` / `CarrySpeedVent` | 13 / 16 | Wie stark sich Halle und Lüftung unterscheiden |
| `AlarmDelay` | 2,5 s | Vorsprung des Diebs |
| `TagRange` | 6 Studs | Wie nah der Besitzer herankommen muss |
| `StunTime` | 1,5 s | Sperre nach dem Abfangen |
| `Incubation` / `StarterIncubation` | 30 s / 10 s | Brutzeit, für Tests kurz gehalten |
| `MinIncubationAfterSteal` | 8 s | Fenster, in dem das Opfer zurückklauen kann |
| `RunSelfTests` | true | Selbsttest beim Serverstart |

## Grenzen dieses Builds

- Kein Speichern: Münzen und Kreaturen gelten nur für die Sitzung.
- Münzen haben noch keine Verwendung.
- Sounds sind stumm, bis in `Config.Sounds` Asset-IDs eingetragen sind. Der Alarm ist bis dahin an Lampe und Banner zu erkennen.
- Keine Trage-Animation, das Ei hängt vor der Brust.
- Kein Tempo-Check gegen manipulierte Clients. Ein Cheater kann schneller laufen, aber kein Ei beanspruchen, das ihm die Regeln nicht geben.
