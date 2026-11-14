---
created: 2026-11-14
project: "[[Ei-Alarm!]]"
---

Schritte für eigene Modelle in Blender und den Import in Roblox Studio. Ziel: stilisiert, gut erkennbar, leicht genug für Smartphones.

In der Sitzung, in der diese Notiz entstand, war weder Blender verfügbar noch die Roblox-Dokumentation erreichbar. Die Schritte unten sind der übliche Weg. Zahlen zu Limits und die genauen Namen der Importer-Optionen bitte beim ersten Import gegen Studio prüfen. Der Testwürfel in Schritt 1 fängt Maßstabsfehler ab.

## Budget pro Modell

| Modell | Dreiecke | Knochen | Textur |
| --- | --- | --- | --- |
| Ei | 300 bis 500 | 3 | 256 × 256 |
| Brutmaschine | bis 2.500 | 2 (Deckel, Lampe) | 512 × 512 |
| Waffelkrabbe | bis 1.500 | 6 | 512 × 512 |
| Toaster-Gecko | bis 2.000 | 10 | 512 × 512 |
| Pudding-Golem | bis 1.500 | 6 | 512 × 512 |

Das liegt weit unter dem, was Roblox pro Mesh erlaubt. Auf einem Server stehen bis zu 32 Kreaturen und 16 Eier gleichzeitig, deshalb das niedrige Budget. Ein Material und eine Textur pro Modell.

## 1. Szene einrichten und Maßstab festlegen

1. Neue Datei. **Scene Properties → Units**: Unit System `Metric`, Unit Scale `1.0`.
2. Festlegung: 1 Blender-Einheit entspricht 1 Stud. Ein Roblox-Charakter ist etwa 5 bis 6 Studs hoch. Zielgrößen: Ei 2,2 × 2,8 × 2,2, Waffelkrabbe 5 breit und 2 hoch, Toaster-Gecko 6 lang und 2,5 hoch, Pudding-Golem 4,5 hoch.
3. Achsen: Blender-Vorderseite ist −Y. Das Modell blickt in Richtung −Y und steht mit den Füßen auf Z = 0. Der Objekt-Ursprung liegt am Boden in der Mitte.
4. Testwürfel: einen Würfel mit Kantenlänge 4 exportieren (Abschnitt 5) und importieren (Abschnitt 6). In Studio neben ein Part mit Size 4, 4, 4 stellen. Stimmt die Größe nicht, die Option für die Einheit im Importer ändern, bis beide gleich groß sind. Diese Einstellung für alle weiteren Importe beibehalten.

## 2. Modellieren

Allgemein: mit Grundformen beginnen, wenige große Formen, klare Silhouette. Nach dem Modellieren **Shade Smooth**, harte Kanten per **Mark Sharp** und Auto Smooth. Keine Subdivision-Modifier im Export, höchstens Stufe 1 und angewendet.

**Ei**
1. UV Sphere, 16 Segmente, 10 Ringe. In Z auf 1,27 skalieren, obere Hälfte mit Proportional Editing leicht verjüngen.
2. Mit **Bisect** eine Zickzacklinie etwa auf zwei Dritteln der Höhe schneiden: Loop Cut, dann jeden zweiten Vertex 0,1 nach oben schieben. Entlang dieser Kante mit **Split** in zwei Teile trennen: `ShellTop` und `ShellBottom`.
3. Beide Teile bleiben ein Objekt, die Trennung dient dem Aufplatzen in der Animation.

**Brutmaschine**
1. Sockel: Zylinder, 12 Segmente, Durchmesser 4, Höhe 1.
2. Glaskuppel: halbe UV Sphere, Durchmesser 3,6, eigenes Objekt mit durchsichtigem Material. In Roblox später als eigenes MeshPart mit Transparency 0,6.
3. Details: zwei Rohre (Zylinder mit 6 Segmenten), eine Statuslampe (Icosphere, Stufe 1), ein Bedienfeld (flacher Quader).
4. Skins für den Shop sind später nur andere Texturen und ein anderer Sockel.

**Waffelkrabbe**
1. Körper: Zylinder, 16 Segmente, Durchmesser 3,2, Höhe 0,8. Oberseite: **Inset**, dann mit Loop Cuts ein 4 × 4-Gitter und jede zweite Fläche 0,1 nach innen extrudieren.
2. Scheren: zwei Icospheres (Stufe 2), Durchmesser 1,2. Vorn einen Keil herausschneiden für die Öffnung.
3. Beine: pro Seite drei Zylinder mit 6 Segmenten, zu einem Objektteil pro Seite verbunden.
4. Augen: zwei kleine Icospheres auf kurzen Stielen.

**Toaster-Gecko**
1. Toaster: Quader 2,2 × 3 × 1,8, alle Kanten mit **Bevel** (2 Segmente). Oben zwei Schlitze per Inset und Extrude nach innen.
2. Toast: Quader 1,2 × 0,3 × 1,2 mit gerundeten Ecken, eigenes Objektteil für den eigenen Knochen.
3. Kopf: Quader mit Subdivision Stufe 1, angewendet, breit und flach. Augen als Icospheres seitlich oben.
4. Schwanz: Zylinder mit 8 Segmenten, 4 Loop Cuts, zur Spitze verjüngt.
5. Beine: vier kurze Zylinder mit flachem Fuß.

**Pudding-Golem**
1. Untere Stufe: Zylinder, 16 Segmente, Durchmesser 3,4 unten und 3,0 oben, Höhe 2,4. Senkrechte Rillen: jede zweite Seitenkante leicht nach innen skalieren.
2. Obere Stufe: gleiche Form, 70 % so groß.
3. Karamell: flacher Zylinder obenauf, am Rand vier bis fünf Tropfen nach unten extrudieren.
4. Arme: zwei Zylinder mit 8 Segmenten und gerundetem Ende.
5. Für das Wackeln zwei waagerechte Loop Cuts pro Stufe, damit sich das Mesh biegen kann.

## 3. Material und Textur

1. **UV Editing → Smart UV Project**, Island Margin 0,02. Bei den Kreaturen reicht eine Farbpalette: alle Flächen einer Farbe auf dasselbe kleine Feld der Textur legen.
2. Ein Material mit Principled BSDF, nur Base Color mit der Textur. Roughness und Metallic stellst du später in Roblox am MeshPart oder per SurfaceAppearance ein.
3. Textur als PNG speichern, Seitenlänge laut Budgettabelle.

## 4. Rigging

1. **Add → Armature**. Erster Knochen `Root` am Ursprung, zeigt nach oben. Er bekommt selbst keine Gewichte.
2. Weitere Knochen als Kinder von `Root`:
   - Ei: `ShellBottom`, `ShellTop`
   - Waffelkrabbe: `Body`, `ClawL`, `ClawR`, `LegsL`, `LegsR`
   - Toaster-Gecko: `Body`, `Head`, `Tail1`, `Tail2` (Kind von `Tail1`), `Toast`, `LegFL`, `LegFR`, `LegBL`, `LegBR`
   - Pudding-Golem: `Body`, `Top` (Kind von `Body`), `Caramel` (Kind von `Top`), `ArmL`, `ArmR`
3. Mesh auswählen, dann Armature, **Ctrl+P → With Empty Groups**. Gewichte von Hand zuweisen: starre Teile (Scheren, Toast, Toaster) bekommen Gewicht 1,0 auf genau einem Knochen. Nur Schwanz und Pudding bekommen weiche Übergänge.
4. Höchstens vier Knochen pro Vertex: im Weight-Paint-Modus **Weights → Limit Total**, Limit 4, danach **Normalize All**.
5. Knochennamen ohne Leerzeichen und Umlaute. Sie müssen in jeder Animationsdatei gleich bleiben.

## 5. FBX-Export

Vorher im Object Mode Mesh und Armature auswählen und **Ctrl+A → All Transforms** anwenden. Location, Rotation und Scale müssen danach 0, 0 und 1 zeigen.

**File → Export → FBX**:

| Option | Wert |
| --- | --- |
| Include → Limit to | Selected Objects |
| Include → Object Types | Armature, Mesh |
| Transform → Scale | 1.0 |
| Transform → Apply Scalings | FBX All |
| Transform → Forward / Up | −Z Forward, Y Up |
| Geometry → Apply Modifiers | an |
| Geometry → Triangulate Faces | an |
| Armature → Add Leaf Bones | aus |
| Armature → Only Deform Bones | an |
| Bake Animation | aus für das Modell, an für Animationsdateien |

Animationen: eine FBX-Datei pro Animation, mit demselben Rig. Bildrate der Szene vorher auf 30 fps stellen. Beim Export zusätzlich **Bake Animation → NLA Strips** und **All Actions** ausschalten, damit nur die aktive Action in der Datei landet.

## 6. Import in Roblox Studio

1. **Home → Import 3D** (oder **File → Import 3D**) und die FBX-Datei wählen.
2. Im Vorschaufenster prüfen und einstellen:
   - Maßstab: die Einheit so wählen, wie beim Testwürfel ermittelt.
   - Rig-Typ: `Custom` (kein R15), damit die Knochen als Bones erhalten bleiben.
   - Als ein Modell importieren, Meshes nicht zusammenführen, wenn die Glaskuppel getrennt bleiben soll.
   - Anchored: an für Ei und Brutmaschine.
   - Vorschau: Größe, Ausrichtung (Blick nach −Z) und Dreieckszahl kontrollieren. Steht das Modell verkehrt herum, im Importer die Vorwärtsachse umstellen oder in Blender um 180° um Z drehen, Transforms anwenden und neu exportieren.
3. Importieren. Im Explorer liegt ein Model mit MeshPart(s) und Bones.
4. Nacharbeit am Model:
   - **Pivot**: mit dem Pivot-Werkzeug an den Boden in die Mitte setzen. Die Skripte stellen Kreaturen mit `PivotTo` auf den Stellplatz.
   - Im Model einen **AnimationController** mit **Animator** anlegen. Kreaturen brauchen keinen Humanoid.
   - Am MeshPart: `CanCollide` aus, `CollisionFidelity` auf `Box`, `RenderFidelity` auf `Automatic`, `CastShadow` bei kleinen Teilen aus.
5. Animationen: Model auswählen, **Avatar → Animation Editor**, dort **Import → From FBX Animation**. Schleifen und Priorität setzen (siehe [[Ei-Alarm Animationen]]), dann **Publish to Roblox**. Die Asset-ID notieren.
6. Fertige Modelle nach `ReplicatedStorage/EiAlarm/Models` legen, benannt wie die Kreaturen-IDs in `Config.Creatures`. Dann in `MapBuilder.buildCreature` und `MapBuilder.buildEgg` die Platzhalter durch `Models[name]:Clone()` ersetzen.

## Prüfliste vor jedem Export

- Transforms angewendet, Ursprung am Boden
- Blick in Richtung −Y, Füße auf Z = 0
- Normalen zeigen nach außen (**Mesh → Normals → Recalculate Outside**)
- Dreieckszahl im Budget (Overlay **Statistics**)
- Höchstens vier Gewichte pro Vertex
- Ein Material, eine Textur
