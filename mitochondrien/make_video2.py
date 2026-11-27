"""Erklärvideo 2 "Energiegewinnung in Mitochondrien" (1920x1080, zwei Sprecher).

Nach dem Arbeitsauftrag (NUR Energieübertragung an den Transportmolekülen, Redoxreaktionen, ATP und
NADH – kein Citratzyklus, kein Calvinzyklus) und den Lehrbuchseiten 26–28: exergonisch/endergonisch,
energetische Kopplung, Lastwagen-Modell und seine Grenzen, Oxidations-/Reduktionsmittel,
NAD⁺/NADH + H⁺ als Reduktionsäquivalent, ATP (Phosphorylierung, 32 kJ/mol, 70 kg pro Tag) und die
Energieübertragung im Mitochondrium – am Ende vier Aufgaben zum Mitdenken.

Aufruf:  python3 mitochondrien/make_video2.py [ausgabe-ordner]
Erzeugt: mitochondrien-video2.mp4           (mit zwei KI-Sprecherstimmen)
         mitochondrien-video2-ohne-ton.mp4  (nur Musik + Untertitel, zum Selbst-Einsprechen)
         SKRIPT_video2.md                   (Sprechertext mit Zeitmarken)
Namen im Abspann: NAMEN="Name 1 & Name 2" python3 mitochondrien/make_video2.py
"""
import math, os, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_video as mv  # noqa: E402
from make_video import (W, H, SS, WHITE, GREY, EL, NADH_C, NAD_C, ATP_C, OX, RED, PANEL,  # noqa: E402
                        cl, ease, back, lerp, mix)

DARK = (20, 25, 35)
GREEN = (95, 200, 120)      # Elektronendonator / Nährstoff (wie im Buch grün)
REDB = (230, 95, 95)        # Elektronenakzeptor (rot)
BLUE = (100, 160, 255)
WARM = (255, 150, 90)
MEMB = (232, 201, 138)
CARGO = (255, 160, 60)

# ---------------------------------------------------------------- Sprechertext
CHAPTERS = ["Einstieg", "Transportmoleküle", "Redoxreaktionen", "NADH + H⁺", "ATP", "Mitochondrium",
            "Zusammenfassung", "Aufgaben"]

SCENES2 = [
 ("v2_title", "", [
  ("A", "Hallo! In unserem Erklärvideo geht es um die Energiegewinnung in Mitochondrien."),
  ("B", "Mitochondrien nennt man auch die Kraftwerke der Zelle. Hier wird ein Großteil der Energie aus der Nahrung "
        "für die Zelle nutzbar gemacht."),
  ("A", "Wir zeigen, wie diese Energie mit Transportmolekülen übertragen wird. Dabei geht es um Redoxreaktionen, "
        "NADH + H⁺ und ATP."),
 ], 0),
 ("v2_kopplung", "1 · Energieübertragung mit Transportmolekülen", [
  ("B", "Beim Abbau von Nährstoffen wie Glucose wird Energie frei. Solche Reaktionen laufen freiwillig ab und heißen "
        "exergonisch."),
  ("A", "Der Aufbau von Eiweißen aus Aminosäuren läuft dagegen nicht freiwillig ab. Er benötigt Energie und heißt "
        "endergonisch."),
  ("B", "Transportmoleküle verbinden beide Reaktionen. Das nennt man energetische Kopplung. Man kann sie sich wie "
        "Lastwagen vorstellen."),
  ("A", "Bei der exergonischen Reaktion wird der Lastwagen mit Energie beladen. Er ist jetzt ein energiereiches "
        "Transportmolekül."),
  ("B", "Bei der endergonischen Reaktion lädt er die Energie ab und fährt als energiearmes Transportmolekül zurück."),
  ("A", "Aber das Modell hat Grenzen: Energie ist keine Ladung, sondern in chemischen Bindungen gespeichert. Und das "
        "Transportmolekül verändert sich dabei selbst."),
  ("B", "Außerdem bewegen sich Moleküle nicht gezielt, sondern zufällig. Und bei jeder Übertragung geht Energie als "
        "Wärme verloren."),
 ], 1),
 ("v2_redox", "2 · Redoxreaktionen", [
  ("B", "Wie wird Energie chemisch übertragen? Meist über Elektronen, und zwar in Redoxreaktionen."),
  ("A", "Gibt ein Stoff Elektronen ab, ist das eine Oxidation. Nimmt ein Stoff Elektronen auf, ist das eine Reduktion."),
  ("B", "Beide Teilreaktionen laufen immer gleichzeitig ab und bilden zusammen die Redoxreaktion. Mit den Elektronen "
        "wird dabei auch Energie übertragen."),
  ("A", "Der Stoff, der Elektronen abgibt, heißt Elektronendonator oder Reduktionsmittel. Er reduziert seinen Partner "
        "und wird selbst oxidiert."),
  ("B", "Der Stoff, der die Elektronen aufnimmt, heißt Elektronenakzeptor oder Oxidationsmittel. Er oxidiert seinen "
        "Partner und wird selbst reduziert."),
 ], 2),
 ("v2_nad", "3 · NAD⁺ und NADH + H⁺", [
  ("A", "In der Zelle übernimmt das ein besonderes Transportmolekül: NAD⁺, das Nikotinamid-Adenin-Dinucleotid."),
  ("B", "Beim Abbau von Nährstoffen gibt ein energiereicher Stoff zwei Elektronen und zwei H⁺-Ionen an NAD⁺ ab. "
        "Dieser Stoff wird dabei oxidiert."),
  ("A", "NAD⁺ wird reduziert, und es entsteht NADH + H⁺. Die Energie steckt jetzt in diesem Transportmolekül."),
  ("B", "NADH + H⁺ überträgt die Elektronen dann auf einen passenden Akzeptor. Dabei wird es oxidiert und ist wieder "
        "NAD⁺. Der Akzeptor wird reduziert."),
  ("A", "Im Lastwagen-Modell ist NAD⁺ also der leere und NADH + H⁺ der beladene Lastwagen. Man nennt NADH + H⁺ auch "
        "ein Reduktionsäquivalent."),
  ("B", "Weil die Zelle nur wenig NAD⁺ besitzt, muss dieser Kreislauf ständig laufen. Sonst könnte bald keine "
        "Energie mehr aus den Nährstoffen übertragen werden."),
 ], 3),
 ("v2_atp", "4 · ATP – Adenosintriphosphat", [
  ("B", "Das wichtigste Transportmolekül für Energie ist ATP, das Adenosintriphosphat. Es besteht aus der Base Adenin, "
        "dem Zucker Ribose und drei Phosphatgruppen."),
  ("A", "Wird an ADP, das Adenosindiphosphat, eine Phosphatgruppe gebunden, nennt man das Phosphorylierung. Diese "
        "Reaktion ist endergonisch."),
  ("B", "Die Energie ist jetzt in der neuen Bindung chemisch gespeichert. ATP ist also energiereicher als ADP."),
  ("A", "Wird diese Bindung mit Wasser gespalten, entstehen wieder ADP und Phosphat. Das ist exergonisch: Pro Mol "
        "werden etwa 32 Kilojoule nutzbar."),
  ("B", "Damit stellt die Zelle zum Beispiel Proteine her, transportiert Stoffe oder bewegt sich."),
  ("A", "Und der Bedarf ist riesig: Ein Mensch verbraucht in Ruhe etwa 70 Kilogramm ATP am Tag, besitzt aber nur "
        "etwa 100 Gramm. Jedes ATP wird also rund 700 Mal am Tag neu gebildet."),
 ], 4),
 ("v2_mito", "5 · Energieübertragung im Mitochondrium", [
  ("A", "Jetzt setzen wir alles zusammen. Bei der Zellatmung wird Glucose mithilfe von Sauerstoff schrittweise zu "
        "Kohlenstoffdioxid und Wasser oxidiert."),
  ("B", "Die energiereichen Elektronen aus der Glucose werden dabei auf NAD⁺ übertragen. Es entsteht NADH + H⁺."),
  ("A", "An der inneren Mitochondrienmembran gibt NADH + H⁺ die Elektronen wieder ab und wird oxidiert."),
  ("B", "Die Elektronen wandern über eine Kette von Einzelreaktionen, lauter kleine Redoxreaktionen. Bei jedem Schritt "
        "wird etwas Energie frei."),
  ("A", "Am Ende nimmt Sauerstoff die Elektronen auf und wird mit H⁺-Ionen zu Wasser reduziert. Dafür brauchen wir den "
        "eingeatmeten Sauerstoff."),
  ("B", "Mit der frei werdenden Energie wird an der inneren Membran ADP zu ATP phosphoryliert. Der Rest der Energie "
        "geht als Wärme an die Umgebung."),
 ], 5),
 ("v2_fazit", "Zusammenfassung", [
  ("B", "Fassen wir zusammen. Erstens: Beim Abbau von Nährstoffen werden Elektronen auf NAD⁺ übertragen, es entsteht "
        "NADH + H⁺."),
  ("A", "Zweitens: An der inneren Mitochondrienmembran gibt NADH + H⁺ die Elektronen über Redoxreaktionen an "
        "Sauerstoff weiter."),
  ("B", "Drittens: Mit der frei werdenden Energie wird ADP zu ATP phosphoryliert."),
  ("A", "Viertens: ATP gibt die Energie an endergonische Vorgänge ab, zum Beispiel an Muskelarbeit oder aktiven "
        "Transport."),
  ("B", "Kurz gesagt: Beim Abbau von Nährstoffen wird Energie auf das ATP/ADP-System übertragen und so für zelluläre "
        "Vorgänge nutzbar gemacht."),
 ], 6),
 ("v2_quiz", "Aufgaben zum Mitdenken", [
  ("A", "Jetzt seid ihr dran: vier Aufgaben zum Mitdenken. Pausiert das Video, wenn ihr mehr Zeit braucht."),
  ("B", "Aufgabe eins: Nennt die Definitionen von Oxidation und Reduktion."),
  ("?", 4),
  ("A", "Oxidation ist die Abgabe von Elektronen, Reduktion die Aufnahme von Elektronen. Beides läuft immer "
        "gleichzeitig ab."),
  ("B", "Aufgabe zwei: Welche Funktion haben NAD⁺ und NADH + H⁺ im Lastwagen-Modell?"),
  ("?", 4),
  ("A", "NAD⁺ ist der leere, energiearme Lastwagen. NADH + H⁺ ist der beladene, energiereiche Lastwagen, der "
        "Elektronen und damit Energie transportiert."),
  ("B", "Aufgabe drei: Erklärt, warum der NAD⁺/NADH + H⁺-Zyklus ständig laufen muss."),
  ("?", 4),
  ("A", "Die Zelle hat nur wenig NAD⁺. Nur wenn NADH + H⁺ immer wieder zu NAD⁺ oxidiert wird, kann weiter Energie aus "
        "den Nährstoffen übertragen werden."),
  ("B", "Aufgabe vier: Erläutert die Synthese von ATP aus energetischer Sicht."),
  ("?", 4),
  ("A", "Die Phosphorylierung von ADP zu ATP ist endergonisch. Die Energie dafür liefert der exergonische Abbau der "
        "Nährstoffe. Beide Reaktionen sind gekoppelt."),
 ], 7),
 ("v2_ende", "", [
  ("B", "Das war unser Erklärvideo zur Energiegewinnung in Mitochondrien. Danke fürs Zuschauen!"),
  ("-", 3),
 ], 7),
]

QUIZ = [("Nennt die Definitionen von Oxidation und Reduktion.", "nach Buch S. 26, Aufgabe 2"),
        ("Welche Funktion haben NAD⁺ und NADH + H⁺ im Lastwagen-Modell?", "nach Buch S. 26, Aufgabe 3"),
        ("Erklärt, warum der NAD⁺/NADH + H⁺-Zyklus ständig laufen muss.", "nach Buch S. 26, Aufgabe 4"),
        ("Erläutert die Synthese von ATP aus energetischer Sicht.", "nach Buch S. 28, Aufgabe 3")]


# ---------------------------------------------------------------- Hilfsfunktionen
def qb(p0, p1, p2, s):
    u = 1 - s
    return (u * u * p0[0] + 2 * u * s * p1[0] + s * s * p2[0], u * u * p0[1] + 2 * u * s * p1[1] + s * s * p2[1])


def cb(p0, p1, p2, p3, s):
    u = 1 - s
    return (u ** 3 * p0[0] + 3 * u * u * s * p1[0] + 3 * u * s * s * p2[0] + s ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * s * p1[1] + 3 * u * s * s * p2[1] + s ** 3 * p3[1])


def smooth(x):
    x = cl(x)
    return x * x * (3 - 2 * x)


def anim(t, v0, events):
    """Wert, der bei v0 startet und nacheinander zu jedem (Zeit, Ziel, Dauer) gleitet."""
    v = v0
    for te, tgt, d in events:
        if t < te: break
        v = lerp(v, tgt, ease((t - te) / d))
    return v


def nb(s):
    """Keep "NADH + H⁺" together when wrapping."""
    return s.replace(" + H⁺", " + H⁺")


def curve(c, arc, col, width=5, a=1.0, p=1.0, head=18):
    """Gebogener Pfeil (quadratische Bézierkurve p0, Kontrollpunkt, p2), gezeichnet bis zum Anteil p."""
    if a <= 0.01 or p <= 0.03: return
    n = 36
    pts = [qb(*arc, p * i / n) for i in range(n + 1)]
    (px, py), (qx, qy) = pts[-3], pts[-1]
    ang = math.atan2(qy - py, qx - px)
    bx, by = qx - head * math.cos(ang), qy - head * math.sin(ang)
    c.line(pts[:-2] + [(bx, by)], col, width, a)
    c.poly([(qx, qy), (bx + head * 0.6 * math.sin(ang), by - head * 0.6 * math.cos(ang)),
            (bx - head * 0.6 * math.sin(ang), by + head * 0.6 * math.cos(ang))], col, a)


def fit(c, x, y, s, size, fill, a, maxw, anchor="lm", bold=False):
    while size > 14 and c.tw(s, size, bold) > maxw: size -= 1
    c.text(x, y, s, size, fill, anchor, a, bold)


def vtext(c, x, y, s, size, fill, a=1.0, bold=False):
    """Um 90° gedrehter Text (von unten nach oben lesbar)."""
    if a <= 0.01: return
    f = mv.font(size, bold)
    w, h = int(c.d.textlength(s, font=f)) + 8, int(size * SS * 1.5)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((w / 2, h / 2), s, font=f, fill=mv.Cv.c(fill, a), anchor="mm")
    im = im.rotate(90, expand=True)
    c.img.paste(im, (int(x * SS - im.width / 2), int(y * SS - im.height / 2)), im)


def energy_axis(c, x, y0, y1, a):
    c.arrow(x, y0, x, y1, WARM, 5, a, 1.0, 18)
    vtext(c, x - 30, (y0 + y1) / 2, "chemische Energie", 24, GREY, a)


def ball(c, x, y, r, col, a=1.0):
    """Molekül als Kugel wie im Buchmodell."""
    if a <= 0.01: return
    c.circ(x, y, r, col, mix(col, (0, 0, 0), 0.35), 3, a)
    c.circ(x - r * 0.3, y - r * 0.32, r * 0.3, mix(col, WHITE, 0.5), None, 0, a * 0.7)


def ball_slots(x, y, r, side=1):
    out = []
    for k, ang in [("e", -62), ("e", -22), ("H", 18), ("H", 58)]:
        a = math.radians(ang if side > 0 else 180 - ang)
        out.append((k, (x + 1.02 * r * math.cos(a), y + 1.02 * r * math.sin(a))))
    return out


def tray_slots(x, y, sc=1.0):
    h, w = 56 * sc, 236 * sc
    return [("e", (x - 62 * sc, y - h / 2 - 6 * sc)), ("e", (x - 22 * sc, y - h / 2 - 6 * sc)),
            ("H", (x + 22 * sc, y - h / 2 - 8 * sc)), ("H", (x + w / 2 + 24 * sc, y + 4 * sc))]


def draw_slots(c, slots, a, sc=0.95):
    for k, (x, y) in slots:
        c.token(x, y, k, a, sc)


def fly(c, src, dst, p, lift=-90, a=1.0, sc=0.95, stagger=0.1):
    """Teilchen (Art, Position) fliegen von src- zu dst-Plätzen; p = Gesamtfortschritt 0..1."""
    n = len(src)
    for i, ((k, s0), (_, s1)) in enumerate(zip(src, dst)):
        q = smooth((p - i * stagger) / (1 - stagger * (n - 1)))
        ctrl = ((s0[0] + s1[0]) / 2, (s0[1] + s1[1]) / 2 + lift)
        x, y = qb(s0, ctrl, s1, q)
        c.token(x, y, k, a, sc)


def nad_tray(c, x, y, load=0.0, a=1.0, tokens=0.0, sc=1.0):
    """NAD⁺ (grau, leer) bzw. NADH + H⁺ (orange, beladen); tokens = Sichtbarkeit von 2 e⁻ + 2 H⁺."""
    if a <= 0.01: return
    col = mix(NAD_C, NADH_C, load)
    w, h = 236 * sc, 56 * sc
    c.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, col, WHITE, 3, 16 * sc, a)
    loaded = load > 0.5
    c.text(x + 22 * sc, y + 2 * sc, "NADH + H⁺" if loaded else "NAD⁺", 28 * sc, DARK if loaded else WHITE, "mm", a)
    if tokens > 0.01:
        draw_slots(c, tray_slots(x, y, sc), a * tokens, 0.95 * sc)


def truck(c, x, y, facing=1, load=0.0, a=1.0, sc=1.0, roll=0.0):
    """Lastwagen wie im Buchmodell: Fahrerhaus, Ladefläche, orange Ladung "Energie"."""
    if a <= 0.01: return
    f = facing

    def R(x0, y0, x1, y1, fill, outline=None, width=3, r=0, al=1.0):
        xa, xb = sorted((x + f * x0 * sc, x + f * x1 * sc))
        c.rect(xa, y + y0 * sc, xb, y + y1 * sc, fill, outline, width * sc, r * sc, a * al)

    R(-140, -24, 72, 0, (125, 135, 150), None, 0, 4)
    R(-140, -44, -128, -24, (160, 170, 185), None, 0, 2)
    R(72, -88, 152, 0, (215, 60, 60), None, 0, 12)
    R(100, -78, 144, -46, (190, 225, 255), None, 0, 6)
    R(150, -18, 162, -4, (90, 95, 105), None, 0, 3)
    if load > 0.01:
        R(-130, -82, 62, -26, CARGO, (170, 85, 15), 3, 8, load)
        c.text(x + f * -34 * sc, y - 54 * sc, "Energie", 26 * sc, DARK, "mm", a * load)
    for dx in (-112, -64, 116):
        cx, cy = x + f * dx * sc, y + 6 * sc
        c.circ(cx, cy, 21 * sc, (40, 44, 52), (15, 15, 20), 2, a)
        c.circ(cx, cy, 8 * sc, (175, 180, 190), None, 0, a)
        ang = roll * f
        c.line([(cx, cy), (cx + 15 * sc * math.cos(ang), cy + 15 * sc * math.sin(ang))], (175, 180, 190), 3 * sc, a)


def cargo(c, x, y, a=1.0):
    c.chip(x, y, "Energie", 24, CARGO, DARK, a, 16)


# ---------------------------------------------------------------- Szenen
def s_title(c, T):
    t = T.t
    s = back(t / 0.8)
    ka = T.w(1, "Kraftwerke", -0.2)
    c.mito(960, 290, 640 * s, 250 * s, 1.0, 0.55 * T.w(1, "Energie", -0.3) * (0.75 + 0.25 * math.sin(t * 4)))
    c.line([(1285, 290), (1345, 290)], EL, 3, ka)
    c.chip(1545, 290, "„Kraftwerke“ der Zelle", 32, PANEL, EL, ka, 24, EL)
    for i, (bx, by) in enumerate([(600, 175), (1320, 180), (585, 405)]):
        c.bolt(bx, by, 0.8, ka * (0.6 + 0.4 * math.sin(t * 5 + i * 2)))
    a = ease((t - 0.5) / 0.6)
    c.text(960, 525 + 25 * (1 - a), "Energiegewinnung in Mitochondrien", 76, WHITE, "mm", a)
    c.rect(960 - 340 * a, 580, 960 + 340 * a, 588, EL, None, 0, 4, a)
    c.text(960, 640, "Energieübertragung mit Transportmolekülen", 40, GREY, "mm", T.w(2, "Transportmolekülen", -0.4), False)
    items = [("Transportmoleküle", EL, "Transportmolekülen"), ("Redoxreaktionen", OX, "Redoxreaktionen"),
             ("NADH + H⁺", NADH_C, "NADH"), ("ATP", ATP_C, "ATP")]
    ws = [c.tw(lab, 38) + 56 for lab, _, _ in items]
    x = 960 - (sum(ws) + 36 * (len(ws) - 1)) / 2
    for (lab, col, word), w in zip(items, ws):
        c.chip(x + w / 2, 760, lab, 38, col, DARK, 1, 28, None, T.wb(2, word, -0.1, 0.45))
        x += w + 36


LX, RX, TOPY, BOTY, R1, R2 = 255, 1665, 265, 640, 318, 598


def info_box(c, x, y, l1, l2, col, a, tag=0.0):
    if a <= 0.01: return
    w, h = 340, 150
    c.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, mix(col, (16, 26, 42), 0.78), col, 4, 22, a)
    c.text(x, y - 40, l1, 31, WHITE, "mm", a)
    c.text(x, y - 3, l2, 26, GREY, "mm", a, False)
    if tag > 0.01:
        c.chip(x, y + 42, "Energie", 24, CARGO, DARK, a, 16, None, back(tag) if tag < 1 else 1.0)


def road(c, y, a):
    if a <= 0.01: return
    c.rect(470, y - 14, 1450, y + 14, (52, 62, 82), None, 0, 8, a)
    for i in range(16):
        xx = 490 + i * 60
        c.rect(xx, y - 2, xx + 28, y + 2, (200, 205, 215), None, 0, 1, a * 0.5)


def s_kopplung(c, T):
    t = T.t
    mid = (TOPY + BOTY) / 2
    # links: exergonische Reaktion (Abbau von Nährstoffen)
    a0 = T.w(0, "Nährstoffen", -0.3)
    info_box(c, LX, TOPY, "Nahrungsmoleküle", "z. B. Glucose", GREEN, a0, 1.0)
    c.arrow(LX, TOPY + 82, LX, BOTY - 82, GREEN, 6, a0, T.w(0, "frei", -0.5, 0.9), 20)
    info_box(c, LX, BOTY, "Wasser und", "Kohlenstoffdioxid", GREEN, T.w(0, "frei", 0.1))
    c.chip(LX, mid, "exergonisch", 26, (70, 40, 30), WARM, T.w(0, "exergonisch", -0.2), 16, WARM)
    # rechts: endergonische Reaktion (Aufbau von Eiweißen)
    t_un = T.tw(4, "lädt") - 0.2
    ar = T.w(1, "Aminosäuren", -0.3)
    info_box(c, RX, BOTY, "einzelne", "Aminosäuren", BLUE, ar)
    info_box(c, RX, TOPY, "Baustoffmoleküle", "z. B. Eiweiß", BLUE, T.w(1, "Eiweißen", -0.3),
             ease((t - t_un - 0.8) / 0.4) if t > t_un + 0.8 else 0.0)
    c.arrow(RX, BOTY - 82, RX, TOPY + 82, BLUE, 6, ar, T.w(1, "benötigt", -0.4, 0.9), 20)
    c.chip(RX, mid, "endergonisch", 26, (30, 40, 70), BLUE, T.w(1, "endergonisch", -0.2), 16, BLUE)
    # frei werdende Energie wartet neben dem Pfeil
    t_load = T.tw(3, "beladen") - 0.5
    if t < t_load:
        c.bolt(LX + 150, mid, 0.7, T.w(0, "frei", 0.2) * (0.7 + 0.3 * math.sin(t * 6)))
    # Straßen = Weg der Transportmoleküle
    ra = T.w(2, "Transportmoleküle", -0.4)
    road(c, R1, ra); road(c, R2, ra)
    c.chip(960, mid, "energetische Kopplung", 30, PANEL, EL, T.w(2, "energetische", -0.2), 22, EL)
    c.text(960, 182, "energiereiches Transportmolekül", 28, (255, 170, 80), "mm", T.w(3, "energiereiches", -0.2))
    c.text(960, 668, "energiearmes Transportmolekül", 28, GREY, "mm", T.w(4, "energiearmes", -0.2))
    # Lastwagen
    t_show = T.tw(2, "Lastwagen") - 0.4
    t_go = T.tw(3, "energiereiches") - 0.2
    t_sw = t_un + 0.9
    y1, y2 = R1 - 20, R2 - 20
    if t > t_show:
        a_t = ease((t - t_show) / 0.4)
        if t < t_sw:
            x = anim(t, 600, [(t_go, 1290, 2.4)])
            load = 1.0 if t_load + 0.8 <= t < t_un else 0.0
            truck(c, x, y1, 1, load, a_t * (1 - ease((t - t_un - 0.55) / 0.3)), 1.0, (x - 600) / 21)
        else:
            x = anim(t, 1290, [(t_sw + 0.5, 620, 2.4)])
            truck(c, x, y2, -1, 0.0, ease((t - t_sw) / 0.3), 1.0, (1290 - x) / 21)
        for t0, src, dst in [(t_load, (LX + 150, mid), (600 - 34, y1 - 54)),
                             (t_un, (1290 - 34, y1 - 54), (RX, TOPY + 42))]:
            if t0 <= t < t0 + 0.8:
                pos = qb(src, ((src[0] + dst[0]) / 2, min(src[1], dst[1]) - 110), dst, smooth((t - t0) / 0.8))
                cargo(c, *pos)
    # Grenzen des Modells
    ov = T.w(5, "Grenzen", -0.4, 0.6)
    if ov > 0.01:
        c.rect(0, 0, W, H, (8, 14, 26), None, 0, 0, 0.88 * ov)
        c.text(960, 215, "Grenzen des Modells", 52, OX, "mm", ov)
        items = [(5, "Ladung", "Energie ist keine Ladung – sie ist in chemischen Bindungen gespeichert."),
                 (5, "verändert", "Das Transportmolekül verändert sich dabei selbst (z. B. ADP → ATP)."),
                 (6, "gezielt", "Moleküle fahren nicht gezielt – sie bewegen sich zufällig."),
                 (6, "Wärme", "Bei jeder Übertragung geht ein Teil der Energie als Wärme verloren.")]
        for i, (k, word, s) in enumerate(items):
            p = T.w(k, word, -0.5)
            y = 335 + i * 115; x = 250 + 40 * (1 - p)
            c.rect(x - 30, y - 44, 1690, y + 44, PANEL, None, 0, 20, p)
            c.circ(x + 20, y, 24, OX, None, 0, p); c.text(x + 20, y, "!", 32, DARK, "mm", p)
            fit(c, x + 64, y, s, 34, WHITE, p, 1690 - x - 90)


def s_redox(c, T):
    t = T.t; r = 58
    AX, BX, Y1, Y2 = 660, 1260, 270, 640
    a0 = T.f(0, 0.1, 0.6)
    arcA = ((AX + 46, Y1 + 34), (1300, (Y1 + Y2) / 2), (AX + 46, Y2 - 34))
    arcB = ((BX - 46, Y1 + 34), (620, (Y1 + Y2) / 2), (BX - 46, Y2 - 34))
    curve(c, arcA, GREEN, 5, a0 * 0.9, T.f(0, 0.4, 1.0))
    curve(c, arcB, REDB, 5, a0 * 0.9, T.f(0, 0.6, 1.0))
    for (x, y, col) in [(AX, Y1, GREEN), (AX, Y2, mix(GREEN, (40, 60, 50), 0.25)),
                        (BX, Y1, REDB), (BX, Y2, mix(REDB, (60, 40, 40), 0.15))]:
        ball(c, x, y, r, col, a0)
    for (x, y, s, anc) in [(AX - r - 22, Y1, "Ausgangsstoff A", "rm"), (AX - r - 22, Y2, "Endprodukt C", "rm"),
                           (BX + r + 22, Y1, "Ausgangsstoff B", "lm"), (BX + r + 22, Y2, "Endprodukt D", "lm")]:
        c.text(x, y, s, 24, GREY, anc, a0, False)
    # Elektronen wandern von A nach D (Schleife)
    t0 = T.tw(1, "Elektronen ab") - 0.3
    aA, aD, mov = 1.0, 0.0, None
    if t > t0:
        ph = ((t - t0) % 3.6) / 3.6
        if ph < 0.12: aA, aD = 1.0, 0.0
        elif ph < 0.7: aA, aD, mov = 0.0, 0.0, smooth((ph - 0.12) / 0.58)
        elif ph < 0.93: aA, aD = 0.0, ease((ph - 0.7) / 0.05)
        else: aA, aD = ease((ph - 0.93) / 0.07), 1 - ease((ph - 0.93) / 0.07)
    for (k, pa), (_, pd) in zip(ball_slots(AX, Y1, r, 1)[:2], ball_slots(BX, Y2, r, -1)[:2]):
        c.token(*pa, k, a0 * aA, 1.0)
        c.token(*pd, k, a0 * aD, 1.0)
    en = T.w(2, "Energie", -0.2)
    if mov is not None:
        path = ((AX + 30, Y1 + 20), (930, 300), (1000, 610), (BX - 30, Y2 - 20))
        for i in range(2):
            x, y = cb(*path, cl(mov * 1.08 - i * 0.08))
            c.token(x + (i - 0.5) * 30, y, "e", a0, 1.0)
        x, y = cb(*path, mov)
        c.bolt(x, y - 44, 0.5, en)
    c.text(880, 455, "Oxidation", 30, OX, "rm", T.w(1, "Oxidation", -0.2))
    c.text(1040, 455, "Reduktion", 30, RED, "lm", T.w(1, "Reduktion", -0.2))
    pa, pb = T.w(1, "Oxidation", -0.2), T.w(1, "Reduktion", -0.2)
    c.text(230, 440, "Oxidation", 44, OX, "mm", pa)
    c.text(230, 487, "= Elektronenabgabe", 28, WHITE, "mm", pa, False)
    c.text(1690, 440, "Reduktion", 44, RED, "mm", pb)
    c.text(1690, 487, "= Elektronenaufnahme", 28, WHITE, "mm", pb, False)
    c.chip(960, 790, "Redoxreaktion  =  Oxidation + Reduktion", 32, PANEL, EL, T.w(2, "Redoxreaktion", -0.3), 24, EL)
    c.text(960, 165, "Elektronen übertragen Energie", 32, EL, "mm", en)
    p3, p4 = T.w(3, "Elektronendonator", -0.3), T.w(4, "Elektronenakzeptor", -0.3)
    c.text(230, 585, "Elektronendonator", 30, GREEN, "mm", p3)
    c.text(230, 625, "= Reduktionsmittel", 26, WHITE, "mm", p3, False)
    c.text(1690, 585, "Elektronenakzeptor", 30, REDB, "mm", p4)
    c.text(1690, 625, "= Oxidationsmittel", 26, WHITE, "mm", p4, False)
    if T.s(4) < 0:
        c.circ(AX, Y1, r + 12 + 4 * math.sin(t * 6), None, GREEN, 4, p3 * 0.8)
    c.circ(BX, Y1, r + 12 + 4 * math.sin(t * 6), None, REDB, 4, p4 * 0.8)


def s_nad(c, T):
    t = T.t; r = 50
    a0 = T.f(0, 0.1, 0.6)
    energy_axis(c, 120, 830, 175, a0)
    A0, C0, B0, D0 = (380, 260), (380, 700), (1540, 600), (1540, 300)
    TOP, BOT = (960, 300), (960, 700)
    arcA = ((420, 300), (970, 480), (420, 660))
    arcL = ((880, 680), (410, 500), (880, 320))
    arcR = ((1040, 320), (1510, 500), (1040, 680))
    arcB = ((1500, 575), (990, 450), (1500, 325))
    tA = T.tw(1, "energiereicher") - 0.4
    tin = T.tw(1, "NAD⁺ ab") - 0.9
    tox = T.tw(1, "oxidiert") - 0.3
    tup = T.tw(2, "reduziert") - 0.3
    tB = T.tw(3, "Akzeptor") - 0.5
    tout = T.tw(3, "Akzeptor") + 0.1
    tdown = T.tw(3, "oxidiert") - 0.2
    tred = T.tw(3, "reduziert") - 0.2
    tloop = T.L[5] if len(T.L) > 5 else 1e9
    # gekreuzte Pfeile wie im Buch (Bild 2)
    curve(c, arcA, OX, 4, 0.85, ease((t - tox) / 0.8))
    curve(c, arcL, RED, 4, 0.85, ease((t - tup) / 0.8))
    curve(c, arcR, OX, 4, 0.85, ease((t - tdown) / 0.8))
    curve(c, arcB, RED, 4, 0.85, ease((t - tred) / 0.8))
    c.text(600, 392, "wird oxidiert", 26, OX, "rm", ease((t - tox) / 0.5))
    c.text(735, 410, "wird reduziert", 26, RED, "lm", ease((t - tup) / 0.5))
    c.text(1190, 410, "wird oxidiert", 26, OX, "rm", ease((t - tdown) / 0.5))
    c.text(1335, 400, "wird reduziert", 26, RED, "lm", ease((t - tred) / 0.5))
    # Elektronendonator A -> C
    aA = ease((t - tA) / 0.5)
    ball(c, *C0, r, GREEN, aA * 0.22)
    ax, ay = qb(A0, (900, 480), C0, smooth((t - tox) / 1.0))
    ball(c, ax, ay, r, GREEN, aA)
    c.text(380, 188, "Elektronendonator A", 24, GREEN, "mm", aA)
    c.text(380, 768, "Produkt C", 24, GREEN, "mm", ease((t - tox - 0.8) / 0.4))
    if t < tin:
        draw_slots(c, ball_slots(*A0, r, 1), aA)
    elif t < tin + 1.0:
        fly(c, ball_slots(*A0, r, 1), tray_slots(*BOT), (t - tin) / 1.0, 60)
    # Elektronenakzeptor B -> D
    aB = ease((t - tB) / 0.5)
    ball(c, *D0, r, REDB, aB * 0.22)
    bx, by = qb(B0, (1020, 450), D0, smooth((t - tred) / 1.0))
    ball(c, bx, by, r, REDB, aB)
    c.text(1540, 672, "Elektronenakzeptor B", 24, REDB, "mm", aB)
    c.text(1540, 228, "Produkt D", 24, REDB, "mm", ease((t - tred - 0.8) / 0.4))
    if tout <= t < tout + 1.0:
        fly(c, tray_slots(*TOP), ball_slots(*B0, r, -1), (t - tout) / 1.0, -80)
    elif t >= tout + 1.0:
        draw_slots(c, ball_slots(bx, by, r, -1), 1.0)
    # NAD⁺ / NADH + H⁺
    if t < tloop:
        if t < tup: tp = BOT
        elif t < tup + 1.2: tp = qb(BOT, (560, 500), TOP, smooth((t - tup) / 1.2))
        elif t < tdown: tp = TOP
        elif t < tdown + 1.2: tp = qb(TOP, (1360, 500), BOT, smooth((t - tdown) / 1.2))
        else: tp = BOT
        load = ease((t - tup - 0.9) / 0.3) * (1 - ease((t - tout) / 0.3))
        tok = 1.0 if tin + 1.0 <= t < tout else 0.0
    else:                                   # der Kreislauf läuft ständig
        cyc = ((t - tloop) % 4.0) / 4.0
        if cyc < 0.12: tp, load, tok = BOT, 0.0, ease(cyc / 0.12)
        elif cyc < 0.45: tp, load, tok = qb(BOT, (560, 500), TOP, smooth((cyc - 0.12) / 0.33)), ease((cyc - 0.3) / 0.15), 1.0
        elif cyc < 0.57: tp, load, tok = TOP, 1.0, 1 - ease((cyc - 0.45) / 0.12)
        elif cyc < 0.9: tp, load, tok = qb(TOP, (1360, 500), BOT, smooth((cyc - 0.57) / 0.33)), 1 - ease((cyc - 0.57) / 0.1), 0.0
        else: tp, load, tok = BOT, 0.0, 0.0
    nad_tray(c, tp[0], tp[1], load, a0, tok)
    c.text(960, 760, "oxidierte Form · Elektronenakzeptor", 22, GREY, "mm", a0, False)
    c.text(960, 228, "reduzierte Form · Elektronendonator", 22, GREY, "mm", ease((t - tup - 1.0) / 0.5), False)
    eq = "NAD⁺ + 2 e⁻ + 2 H⁺  " + ("⇄" if t > tdown else "→") + "  NADH + H⁺"
    c.chip(1500, 160, eq, 30, PANEL, WHITE, T.w(2, "entsteht", -0.3), 22, GREY)
    # Modell: leerer / beladener Lastwagen
    pm = T.w(4, "Lastwagen-Modell", -0.3)
    truck(c, 1175, 318, 1, 1.0, pm, 0.42)
    c.text(1262, 300, "beladen", 22, (255, 170, 80), "lm", pm, False)
    truck(c, 1175, 718, 1, 0.0, pm, 0.42)
    c.text(1262, 705, "leer", 22, GREY, "lm", pm, False)
    c.chip(960, 165, "Reduktionsäquivalent", 26, PANEL, NADH_C, T.w(4, "Reduktionsäquivalent", -0.3), 18, NADH_C)
    pl = T.w(5, "Kreislauf", -0.5)
    c.chip(960, 470, "NAD⁺/NADH + H⁺-Zyklus", 30, PANEL, EL, pl, 22, EL)
    c.text(960, 518, "muss ständig laufen", 24, EL, "mm", pl, False)
    pw = T.w(5, "Sonst", -0.3)
    c.text(960, 830, "Nikotinamid-Adenin-Dinucleotid", 28, GREY, "mm", T.w(0, "Nikotinamid", -0.3) * (1 - pw), False)
    c.chip(960, 830, "Ohne freies NAD⁺ keine Energieübertragung", 28, (70, 40, 30), OX, pw, 20, OX)


def hexagon(c, x, y, r, fill, a):
    pts = [(x + r * math.cos(math.radians(60 * i + 30)), y + r * math.sin(math.radians(60 * i + 30))) for i in range(6)]
    c.poly(pts, fill, a); c.line(pts + [pts[0]], WHITE, 3, a)


def pentagon(c, x, y, r, fill, a):
    pts = [(x + r * math.cos(math.radians(72 * i - 90)), y + r * math.sin(math.radians(72 * i - 90))) for i in range(5)]
    c.poly(pts, fill, a); c.line(pts + [pts[0]], WHITE, 3, a)


def bracket(c, x0, x1, y, label, a):
    c.line([(x0, y + 10), (x0, y), (x1, y), (x1, y + 10)], GREY, 3, a)
    c.text((x0 + x1) / 2, y - 22, label, 24, GREY, "mm", a, False)


def s_atp(c, T):
    t = T.t
    am = T.f(0, 0.1, 0.6)
    det1, att1 = T.tw(1, "ADP") - 0.1, T.tw(1, "gebunden") - 0.6
    det2, loop = T.tw(3, "gespalten") - 0.4, (T.L[5] if len(T.L) > 5 else 1e9)
    if t < loop:
        off = anim(t, 0.0, [(det1, 1.0, 0.5), (att1, 0.0, 0.8), (det2, 1.0, 0.6)])
    else:                                       # ständiges Auf- und Entladen
        cyc = ((t - loop) % 2.0) / 2.0
        off = 1 - smooth(cyc / 0.4) if cyc < 0.5 else smooth((cyc - 0.5) / 0.4)
    glow = T.w(2, "Bindung", -0.3) * (1 - T.w(3, "gespalten", -0.6)) * (0.7 + 0.3 * math.sin(t * 6))
    # Molekül: Adenin + Ribose + drei Phosphatgruppen
    hexagon(c, 300, 300, 58, (120, 140, 235), am)
    c.text(300, 300, "A", 34, WHITE, "mm", am)
    c.line([(352, 312), (425, 322)], WHITE, 4, am)
    pentagon(c, 470, 325, 50, (235, 150, 90), am)
    c.text(470, 330, "R", 30, WHITE, "mm", am)
    c.line([(518, 325), (560, 325)], WHITE, 4, am)
    for px in (600, 705):
        c.circ(px, 325, 40, (250, 200, 70), WHITE, 3, am); c.text(px, 325, "P", 30, (60, 40, 0), "mm", am)
    c.line([(640, 325), (665, 325)], WHITE, 4, am)
    x3, y3 = 810 + 150 * off, 325 - 50 * off
    c.line([(745, 325), (770, 325)], mix(WHITE, EL, glow), 4 + 6 * glow, am * (1 - cl(off * 4)))
    c.circ(x3, y3, 40, (250, 200, 70), WHITE, 3, am); c.text(x3, y3, "P", 30, (60, 40, 0), "mm", am)
    c.text(300, 385, "Adenin", 24, GREY, "mm", T.w(0, "Adenin", -0.3), False)
    c.text(470, 395, "Ribose", 24, GREY, "mm", T.w(0, "Ribose", -0.3), False)
    bracket(c, 240, 522, 228, "Adenosin", T.w(0, "Adenosintriphosphat", -0.3))
    bracket(c, 560, 850, 262, "drei Phosphatgruppen", T.w(0, "Phosphatgruppen", -0.3))
    if glow > 0.05:
        c.text(757, 395, "Energie in der Bindung", 24, EL, "mm", glow, False)
    name = "ATP – Adenosintriphosphat" if off < 0.5 else "ADP – Adenosindiphosphat  +  P"
    c.text(560, 470, name, 36, ATP_C if off < 0.5 else GREY, "mm", T.w(0, "ATP", -0.3))
    c.battery(560, 560, 1 - 0.85 * off, T.w(0, "Phosphatgruppen", 0.3), 220, 90)
    # Energie hinein (Phosphorylierung) / Wasser hinaus
    if att1 - 0.2 <= t < att1 + 0.6:
        p = smooth((t - att1 + 0.2) / 0.8)
        c.bolt(lerp(830, 757, p), lerp(160, 300, p), 0.7, 1 - ease((p - 0.85) / 0.15))
    if att1 + 0.8 <= t < att1 + 2.0:
        p = smooth((t - att1 - 0.8) / 1.2)
        c.token(lerp(757, 900, p), lerp(330, 190, p), "H₂O", 1 - ease((p - 0.6) / 0.4), 0.9)
    # Wasser hinein / Energie hinaus (Spaltung)
    if det2 - 0.7 <= t < det2:
        p = smooth((t - det2 + 0.7) / 0.7)
        c.token(lerp(930, 757, p), lerp(190, 330, p), "H₂O", 1.0, 0.9)
    if det2 <= t < det2 + 0.8:
        p = smooth((t - det2) / 0.8)
        c.bolt(lerp(790, 1000, p), lerp(300, 395, p), 0.7, 1 - ease((p - 0.8) / 0.2))

    # Gleichungen (wie im Buch: energetische Kopplung)
    def eq_row(y, eq, tag, col, a):
        c.rect(1000, y - 62, 1840, y + 62, PANEL, col, 3, 22, a)
        c.text(1420, y - 20, eq, 36, WHITE, "mm", a)
        c.text(1420, y + 28, tag, 24, col, "mm", a, False)
    eq_row(250, "ADP + P  →  ATP + H₂O", "endergonisch · Energie wird in der Bindung gespeichert", RED,
           T.w(1, "endergonisch", -0.4))
    eq_row(395, "ATP + H₂O  →  ADP + P", "exergonisch · pro Mol werden ca. 32 kJ nutzbar", WARM,
           T.w(3, "exergonisch", -0.4))
    # Wofür?
    uses = [("Proteinherstellung", "Proteine"), ("Stofftransport", "transportiert"), ("Bewegung", "bewegt")]
    ws = [c.tw(u, 26) + 36 for u, _ in uses]
    x = 1420 - (sum(ws) + 20 * (len(ws) - 1)) / 2
    for (u, word), w in zip(uses, ws):
        tu = T.tw(4, word) - 0.5
        if tu <= t < tu + 0.6:
            p = smooth((t - tu) / 0.6)
            c.bolt(lerp(1420, x + w / 2, p), lerp(440, 500, p), 0.45, 1.0)
        c.chip(x + w / 2, 520, u, 26, PANEL, WHITE, 1.0, 18, EL, T.wb(4, word, -0.1, 0.45))
        x += w + 20
    # ATP-Bedarf: 70 kg pro Tag, nur 100 g vorhanden
    ps = T.w(5, "Bedarf", -0.3)
    if ps > 0.01:
        c.rect(1000, 575, 1840, 862, PANEL, None, 0, 22, ps)
        c.text(1420, 605, "ATP-Bedarf eines Menschen in Ruhe", 26, WHITE, "mm", ps)
        b1, b2 = T.w(5, "70", 0, 1.0), T.w(5, "100", 0, 0.5)
        c.text(1030, 650, "Verbrauch pro Tag", 24, GREY, "lm", ps, False)
        c.text(1810, 650, "≈ 70 kg", 28, EL, "rm", b1)
        c.rect(1030, 670, 1030 + 780 * b1, 700, EL, None, 0, 8, ps)
        c.text(1030, 737, "im Körper vorhanden", 24, GREY, "lm", ps, False)
        c.text(1810, 737, "≈ 100 g", 28, ATP_C, "rm", b2)
        c.rect(1030, 757, 1034 + 780 / 700 * b2, 787, ATP_C, None, 0, 2, b2)
        c.text(1420, 828, "→ jedes ATP wird ≈ 700-mal am Tag neu gebildet", 28, WHITE, "mm", T.w(5, "700", -0.3))
    pmi = T.w(5, "700", 0.2)
    if pmi > 0.01:
        c.mito(560, 730, 330 * pmi, 130 * pmi, 1.0, 0.8 * (0.75 + 0.25 * math.sin(t * 4)))
        c.text(560, 828, "Bildung an der inneren Mitochondrienmembran", 24, MEMB, "mm", pmi)


ST = [(600, 480), (820, 570), (1040, 660)]
O2P = (1250, 752)


def station(c, x, y, a, hl=0.0):
    c.rect(x - 85, y + 24, x + 85, y + 36, MEMB, None, 0, 4, a)
    c.rect(x - 58, y - 22, x + 58, y + 22, mix((70, 105, 200), (150, 185, 255), hl), (190, 210, 255), 3, 14, a)


def hop(p, q, s, lift=60):
    return lerp(p[0], q[0], s), lerp(p[1], q[1], s) - lift * math.sin(math.pi * s)


def s_mito(c, T):
    t = T.t
    a0 = T.f(0, 0.1, 0.6)
    energy_axis(c, 110, 840, 190, a0)
    c.chip(1480, 160, "C₆H₁₂O₆ + 6 O₂  →  6 CO₂ + 6 H₂O", 30, PANEL, WHITE, T.w(0, "Zellatmung", -0.3), 24, GREY)
    c.text(1480, 205, "Glucose wird oxidiert · Sauerstoff wird reduziert", 22, GREY, "mm", T.w(0, "oxidiert", -0.3), False)
    pg = T.w(0, "Glucose", -0.3)
    c.rect(185, 225, 415, 295, mix(GREEN, (16, 26, 42), 0.7), GREEN, 4, 18, pg)
    c.text(300, 250, "Glucose", 32, WHITE, "mm", pg)
    c.text(300, 280, "C₆H₁₂O₆", 20, GREY, "mm", pg, False)
    # innere Mitochondrienmembran mit der Kette von Einzelreaktionen
    pb = T.w(2, "Mitochondrienmembran", -0.6)
    c.rect(470, 380, 1370, 815, (120, 92, 60), None, 0, 26, 0.22 * pb)
    c.rect(470, 380, 1370, 815, None, MEMB, 3, 26, 0.6 * pb)
    c.text(900, 792, "an der inneren Mitochondrienmembran", 24, MEMB, "mm", pb)
    po = T.w(0, "Sauerstoff", -0.3)
    c.rect(O2P[0] - 85, O2P[1] + 24, O2P[0] + 85, O2P[1] + 36, MEMB, None, 0, 4, pb)
    # Zeiten der Elektronensprünge
    t_h0 = T.tw(1, "übertragen") - 0.7
    times = [T.tw(2, "Elektronen") - 0.2, T.tw(3, "Kette") - 0.2, T.tw(3, "Redoxreaktionen") - 0.2,
             T.tw(4, "Sauerstoff") - 0.2]
    t_w = T.tw(4, "Wasser") - 0.6
    pts = [(310 - 34, 425 - 34)] + [(x, y - 40) for x, y in ST] + [(O2P[0], O2P[1] - 34)]
    k = sum(1 for tt in times if t >= tt) - 1
    s = cl((t - times[k]) / 0.9) if k >= 0 else 0.0
    for j, (x, y) in enumerate(ST):
        station(c, x, y, pb, 1.0 if (k == j and s >= 0.9) or (k == j + 1 and s < 0.15) else 0.0)
    c.token(*O2P, "H₂O" if t > t_w + 0.8 else "O₂", po, 1.2)
    # NAD⁺ / NADH + H⁺
    tray_a = T.w(1, "NAD⁺", -0.4)
    load = ease((t - t_h0 - 0.9) / 0.3) * (1 - ease((t - times[0]) / 0.3))
    tok = 1.0 if t_h0 + 0.9 <= t < times[0] else 0.0
    nad_tray(c, 310, 425, load, tray_a, tok, 0.8)
    if t_h0 <= t < t_h0 + 0.9:
        src = [(kk, (300 + dx, 262)) for kk, dx in [("e", -40), ("e", -10), ("H", 20), ("H", 50)]]
        fly(c, src, tray_slots(310, 425, 0.8), (t - t_h0) / 0.9, -40, 1.0, 0.7)
    if times[0] <= t < times[0] + 0.8:      # die H⁺-Ionen bleiben in der Umgebung zurück
        p = (t - times[0]) / 0.8
        for kk, (x, y) in tray_slots(310, 425, 0.8)[2:]:
            c.token(x + 30 * p, y + 40 * p, kk, 1 - p, 0.66)
    c.chip(310, 492, "wird oxidiert", 24, (70, 40, 30), OX, T.w(2, "oxidiert", -0.3), 16, OX)
    # Elektronen springen die Stufen hinunter
    if k >= 0 and t < times[3] + 1.2:
        pos = hop(pts[k], pts[k + 1], smooth(s))
        al = 1 - ease((t - times[3] - 0.9) / 0.3) if k == 3 else 1.0
        for j in (-1, 1):
            c.token(pos[0] + 19 * j, pos[1] - 4 * j, "e", al, 1.0)
    # bei jedem Schritt wird Energie frei
    tb = T.tw(5, "Energie") + 0.3
    for i in range(1, 4):
        if t < times[i] + 0.4: continue
        m = hop(pts[i], pts[i + 1], 0.5)
        home = (m[0] + 30, m[1] - 52)
        tf = tb + 0.6 * (i - 1)
        if t < tf:
            c.bolt(*home, 0.6, ease((t - times[i] - 0.4) / 0.3) * (0.7 + 0.3 * math.sin(t * 6 + i)))
        elif t < tf + 0.9:
            p = smooth((t - tf) / 0.9)
            c.bolt(lerp(home[0], 1460, p), lerp(home[1], 520, p) - 80 * math.sin(math.pi * p), 0.6, 1.0)
    c.text(600, 650, "Energie wird frei", 26, EL, "mm", T.w(3, "Energie", -0.3))
    # Sauerstoff wird reduziert
    if t_w <= t < t_w + 0.8:
        p = smooth((t - t_w) / 0.8)
        for j, (sx, sy) in enumerate([(1420, 850), (1470, 800)]):
            c.token(lerp(sx, O2P[0] + 30 * (j - 0.5), p), lerp(sy, O2P[1], p), "H", 1.0, 0.8)
    c.chip(1060, 848, "O₂ + 4 e⁻ + 4 H⁺  →  2 H₂O", 26, (30, 50, 90), RED, T.w(4, "reduziert", -0.3), 18, RED)
    # Phosphorylierung von ADP zu ATP
    pbx = T.w(5, "Energie", -0.6)
    c.rect(1460, 400, 1840, 640, mix(ATP_C, (16, 26, 42), 0.8), ATP_C, 4, 24, pbx)
    c.text(1650, 435, "Phosphorylierung", 28, ATP_C, "mm", pbx)
    c.text(1650, 485, "ADP + P  →  ATP", 30, WHITE, "mm", pbx)
    for i in range(3):
        pa = ease((t - tb - 0.6 * i - 0.9) / 0.3)
        c.token(1542 + i * 108, 578, "ATP", pa, back(pa) if pa < 1 else 1.0)
    # der Rest geht als Wärme verloren
    ph = T.w(5, "Wärme", -0.8, 0.8)
    if ph > 0.01:
        for x, y in ST + [O2P]:
            for j in range(2):
                xs = x - 20 + 40 * j
                wave = [(xs + 7 * math.sin(t * 6 + q * 0.7 + j), y - 50 - q * 7 - (t * 40 + 15 * j) % 25) for q in range(9)]
                c.line(wave, WARM, 3, ph * 0.75)
        c.text(1180, 560, "Wärme", 30, WARM, "mm", ph)


def s_fazit(c, T):
    t = T.t
    boxes = [("Glucose", GREEN), ("NADH + H⁺", NADH_C), ("Redoxkette", BLUE), ("ATP", ATP_C), ("Zellarbeit", WHITE)]
    arrows = ["Reduktion", "Oxidation", "Phosphorylierung", "Spaltung"]
    bw, gap, y = 290, 75, 290
    xs = [85 + bw / 2 + i * (bw + gap) for i in range(5)]
    keys = [(0, "NADH"), (1, "Redoxreaktionen"), (2, "ATP"), (3, "endergonische")]
    app = [T.f(0, 0.2)] + [T.w(k, w_, -0.4) for k, w_ in keys]
    pm = T.w(4, "Kurz", -0.3)
    for i, ((s, col), x) in enumerate(zip(boxes, xs)):
        c.rect(x - bw / 2, y - 70, x + bw / 2, y + 70, PANEL, col, 5, 28, app[i])
        c.text(x, y, s, 40, col, "mm", app[i])
        if i:
            c.arrow(xs[i - 1] + bw / 2 + 8, y, x - bw / 2 - 8, y, GREY, 6, app[i], app[i], 18)
            c.text((xs[i - 1] + x) / 2, y - 105, arrows[i - 1], 22, GREY, "mm", app[i], False)
    # Staffelstab: die Energie wird weitergegeben
    bx = anim(t, xs[0], [(T.tw(k, w_) - 0.4, xs[i + 1], 0.8) for i, (k, w_) in enumerate(keys)])
    c.bolt(bx, y - 118 + 6 * math.sin(t * 4), 0.6, app[0])
    rows = [("1", "Elektronen aus Nährstoffen reduzieren NAD⁺ zu NADH + H⁺", NADH_C, 0, "Erstens"),
            ("2", "NADH + H⁺ gibt sie über Redoxreaktionen an Sauerstoff weiter", BLUE, 1, "Zweitens"),
            ("3", "Mit der frei werdenden Energie wird ADP zu ATP phosphoryliert", ATP_C, 2, "Drittens"),
            ("4", "ATP liefert Energie für endergonische Vorgänge, z. B. Muskelarbeit", WHITE, 3, "Viertens")]
    for i, (n, s, col, k, word) in enumerate(rows):
        a = T.w(k, word, -0.3) * (1 - pm); yy = 450 + i * 88
        c.rect(150, yy - 37, 1770, yy + 37, PANEL, None, 0, 20, a)
        c.circ(200, yy, 26, col, None, 0, a); c.text(200, yy, n, 32, DARK, "mm", a)
        cur = T.s(k) >= 0 and (k == 3 or T.s(k + 1) < 0)
        c.text(250, yy, s, 33, WHITE, "lm", a, cur)
    if pm > 0.01:
        c.rect(160, 430, 1760, 760, mix(ATP_C, (16, 26, 42), 0.82), ATP_C, 4, 28, pm)
        c.text(960, 485, "Merksatz", 32, ATP_C, "mm", pm)
        msg = ("Beim Abbau von Nährstoffen wird Energie auf das ATP/ADP-System übertragen und so für zelluläre "
               "Vorgänge nutzbar gemacht.")
        for i, s in enumerate(mv.wrap(c, msg, 42, 1440, True)):
            c.text(960, 565 + i * 62, s, 42, WHITE, "mm", pm)


def s_quiz(c, T):
    t = T.t
    pi = T.f(0, 0.1, 0.5) * (1 - ease((t - T.L[1] + 0.4) / 0.4)) if len(T.L) > 1 else 0.0
    if pi > 0.01:
        c.text(960, 330, "Aufgaben zum Mitdenken", 72, EL, "mm", pi)
        for i in range(4):
            c.circ(660 + i * 200, 480, 48, PANEL, EL, 4, pi * T.b(0, 0.4 + 0.25 * i))
            c.text(660 + i * 200, 480, str(i + 1), 44, WHITE, "mm", pi * T.f(0, 0.4 + 0.25 * i))
        pp = T.w(0, "Pausiert", -0.2) * pi
        hint = "Pausiert das Video, wenn ihr mehr Zeit braucht."
        x0 = 960 - (60 + 30 + c.tw(hint, 30, False)) / 2
        c.rect(x0, 600, x0 + 22, 660, WHITE, None, 0, 4, pp); c.rect(x0 + 38, 600, x0 + 60, 660, WHITE, None, 0, 4, pp)
        c.text(x0 + 90, 630, hint, 30, GREY, "lm", pp, False)
    for q, (task, ref) in enumerate(QUIZ):
        kq, kp, ka = 1 + 3 * q, 2 + 3 * q, 3 + 3 * q
        if ka >= len(T.L): break
        t_in = T.L[kq] - 0.3
        t_out = T.L[kq + 3] - 0.5 if kq + 3 < len(T.L) else 1e9
        a = ease((t - t_in) / 0.4) * (1 - ease((t - t_out) / 0.4))
        if a <= 0.01: continue
        sl = 60 * (1 - ease((t - t_in) / 0.4))
        c.rect(240 + sl, 170, 1680 + sl, 520, PANEL, EL, 4, 30, a)
        c.chip(380 + sl, 215, f"Aufgabe {q + 1}/4", 26, EL, DARK, a, 18)
        c.text(1650 + sl, 215, ref, 22, GREY, "rm", a, False)
        lines = mv.wrap(c, nb(task), 48, 1320, True)
        y0 = 360 - (len(lines) - 1) * 32
        for i, s in enumerate(lines):
            c.text(960 + sl, y0 + i * 64, s, 48, WHITE, "mm", a)
        ps, pe = T.L[kp], T.E[kp]
        if ps - 0.2 <= t < pe + 0.2:            # Countdown
            ca = a * ease((t - ps + 0.2) / 0.3) * (1 - ease((t - pe) / 0.2))
            rem = max(0.0, pe - t); frac = rem / max(0.1, pe - ps)
            c.circ(960, 650, 70, (16, 26, 42), (60, 75, 100), 8, ca)
            if frac > 0.01:
                arc = [(960 + 70 * math.cos(math.radians(-90 + 360 * frac * i / 48)),
                        650 + 70 * math.sin(math.radians(-90 + 360 * frac * i / 48))) for i in range(49)]
                c.line(arc, EL, 8, ca)
            c.text(960, 650, str(math.ceil(rem)), 56, WHITE, "mm", ca)
            c.text(960, 755, "Zeit zum Überlegen …", 28, GREY, "mm", ca, False)
        pa = a * ease((t - T.L[ka] + 0.2) / 0.4)
        if pa > 0.01:                           # Lösung
            lines = mv.wrap(c, nb(T.X[ka]), 34, 1290)
            hh = 70 + len(lines) * 46
            c.rect(240, 555, 1680, 555 + hh, mix(ATP_C, (16, 26, 42), 0.8), ATP_C, 4, 26, pa)
            c.circ(300, 555 + hh / 2, 30, ATP_C, None, 0, pa); c.text(300, 555 + hh / 2, "✓", 34, DARK, "mm", pa)
            for i, s in enumerate(lines):
                c.text(360, 555 + 58 + i * 46, s, 34, WHITE, "lm", pa, False)


def s_ende(c, T):
    t = T.t
    rows = [("Redox", "Oxidation = Elektronenabgabe · Reduktion = Elektronenaufnahme", OX),
            ("NADH + H⁺", "transportiert Elektronen und damit Energie (Reduktionsäquivalent)", NADH_C),
            ("ATP", "ADP + P → ATP + H₂O speichert Energie – die Spaltung setzt sie frei", ATP_C),
            ("Kopplung", "exergonischer Nährstoffabbau treibt die endergonische ATP-Bildung an", EL)]
    c.text(960, 175, "Das Wichtigste", 54, WHITE, "mm", T.f(0, 0.0, 0.5))
    for i, (h, s, col) in enumerate(rows):
        a = ease((t - 0.3 - 0.35 * i) / 0.5); y = 280 + i * 112; x = 150 - 50 * (1 - a)
        c.rect(x, y - 46, x + 1620, y + 46, PANEL, None, 0, 22, a)
        c.rect(x, y - 46, x + 12, y + 46, col, None, 0, 6, a)
        c.text(x + 40, y, h, 36, col, "lm", a)
        fit(c, x + 300, y, s, 30, WHITE, a, 1290)
    pd = T.wb(0, "Danke", -0.2, 0.5)
    if pd > 0.02:
        c.text(960, 755, "Danke fürs Zuschauen!", 64 * pd, EL, "mm", 1.0)
    names = os.environ.get("NAMEN", "").strip()
    if names:
        c.text(960, 830, f"Ein Erklärvideo von {names}", 30, GREY, "mm", T.w(0, "Danke", 0.3), False)


mv.DRAW.update(v2_title=s_title, v2_kopplung=s_kopplung, v2_redox=s_redox, v2_nad=s_nad, v2_atp=s_atp,
               v2_mito=s_mito, v2_fazit=s_fazit, v2_quiz=s_quiz, v2_ende=s_ende)

INTRO = ("\nInhalt nach Arbeitsauftrag (nur Energieübertragung an den Transportmolekülen, Redoxreaktionen, ATP und "
         "NADH – kein Citratzyklus, kein Calvinzyklus) und Lehrbuch S. 26–28. Die vier Aufgaben am Ende sind an "
         "die Buchaufgaben S. 26 Nr. 2–4 und S. 28 Nr. 3 angelehnt.\n")


def main(out_dir):
    mv.LENGTH.update(A=0.92, B=0.84)                 # etwas flotter sprechen
    mv.GAPS.update(pre=0.7, line=0.35, post=0.6)
    mv.render(SCENES2, out_dir, "mitochondrien-video2", os.path.join(HERE, "SKRIPT_video2.md"),
              "Skript: Energiegewinnung in Mitochondrien (Video 2)", CHAPTERS, INTRO)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(mv.ROOT, "videos"))
