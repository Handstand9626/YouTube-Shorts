"""Erklärvideo "Energiegewinnung im Mitochondrium" (1920x1080, zwei Sprecher).

Thema: Energieübertragung auf Transportmoleküle, Redoxreaktionen, NADH und ATP.

Aufruf:  python3 mitochondrien/make_video.py [ausgabe-ordner]
Erzeugt: mitochondrien-energie.mp4            (mit zwei KI-Sprecherstimmen)
         mitochondrien-energie-ohne-ton.mp4   (nur Musik + Untertitel, zum Selbst-Einsprechen)
         SKRIPT.md                            (Sprechertext mit Zeitmarken)
"""
import io, math, os, random, subprocess, sys, wave
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
W, H, FPS, SR, SS = 1920, 1080, 25, 44100, 2
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
VOICES = {"A": os.path.join(ROOT, "voices", "de-thorsten-low.onnx"),
          "B": os.path.join(ROOT, "voices", "de-kerstin-low.onnx")}
SPK = {"A": ("Sprecher 1", (77, 208, 225)), "B": ("Sprecher 2", (255, 138, 201))}
SAY = [("NADH", "N A D H"), ("NAD⁺", "NAD plus"), ("H⁺-Ionen", "H plus Ionen"), ("H⁺", "H plus"),
       ("O₂", "O 2"), ("e⁻", "Elektronen")]

# colours
WHITE, GREY = (240, 244, 250), (150, 165, 185)
EL, NADH_C, NAD_C = (255, 216, 74), (255, 138, 61), (110, 130, 160)
ATP_C, ADP_C, HP = (61, 220, 132), (110, 130, 160), (255, 93, 115)
OX, RED, O2C = (255, 120, 100), (100, 170, 255), (120, 200, 255)
PANEL = (28, 44, 70)

# ---------------------------------------------------------------- script
SCENES = [
 ("title", "", [
  ("A", "Hallo zusammen! In diesem Video erklären wir, wie Mitochondrien Energie gewinnen."),
  ("B", "Dabei schauen wir uns drei Dinge an: Redoxreaktionen, das Molekül NADH und das Molekül ATP."),
 ]),
 ("kraftwerk", "Das Mitochondrium – Kraftwerk der Zelle", [
  ("A", "Mitochondrien nennt man auch die Kraftwerke der Zelle. Fast jede unserer Zellen besitzt viele davon."),
  ("B", "Sie haben zwei Membranen: eine glatte äußere und eine stark gefaltete innere Membran. Ganz innen liegt die Matrix."),
  ("A", "An der inneren Membran passiert das Entscheidende: Hier wird die Energie aus unserer Nahrung auf ATP übertragen."),
 ]),
 ("transport", "Transportmoleküle für Energie", [
  ("B", "Aber wie kommt die Energie aus der Nahrung dorthin, wo die Zelle sie braucht?"),
  ("A", "Die Zelle nutzt dafür Transportmoleküle. Man kann sie sich wie wiederaufladbare Akkus vorstellen."),
  ("B", "Die zwei wichtigsten sind NADH und ATP. NADH transportiert energiereiche Elektronen."),
  ("A", "Und ATP ist die Energiewährung, mit der die Zelle fast alle Arbeiten bezahlt."),
 ]),
 ("redox", "Die Redoxreaktion", [
  ("B", "Um das zu verstehen, brauchen wir die Redoxreaktion."),
  ("A", "Bei einer Oxidation gibt ein Stoff Elektronen ab."),
  ("B", "Bei einer Reduktion nimmt ein Stoff Elektronen auf."),
  ("A", "Beides passiert immer gleichzeitig, denn die Elektronen wandern von einem Partner zum anderen. Deshalb heißt es Redoxreaktion."),
  ("B", "Wichtig ist: Mit den Elektronen wird auch Energie übertragen."),
 ]),
 ("nadh", "NADH – der Elektronentransporter", [
  ("A", "Schauen wir uns NADH genauer an. Die leere Form heißt NAD⁺."),
  ("B", "Beim Abbau von Nährstoffen werden Elektronen frei. NAD⁺ nimmt zwei Elektronen und ein Proton auf und wird so zu NADH."),
  ("A", "NAD⁺ wird also reduziert. NADH ist die beladene, energiereiche Form."),
  ("B", "Gibt NADH die Elektronen später wieder ab, wird es oxidiert und ist wieder NAD⁺. Es funktioniert wie ein Taxi für Elektronen."),
 ]),
 ("atp", "ATP – die Energiewährung", [
  ("A", "Jetzt zu ATP, dem Adenosintriphosphat. Es besteht aus Adenosin und drei Phosphatgruppen."),
  ("B", "Die entladene Form ist ADP, das Adenosindiphosphat, mit nur zwei Phosphatgruppen."),
  ("A", "Wird mit Energie eine dritte Phosphatgruppe angehängt, entsteht ATP. Der Akku ist geladen."),
  ("B", "Spaltet die Zelle die Phosphatgruppe wieder ab, wird die Energie frei, zum Beispiel für Muskelbewegung oder den Transport von Stoffen."),
 ]),
 ("kette", "An der inneren Mitochondrienmembran", [
  ("A", "Jetzt verbinden wir alles. Wir sind an der inneren Membran des Mitochondriums."),
  ("B", "NADH kommt an und gibt seine zwei Elektronen an einen Proteinkomplex in der Membran ab. NADH wird dabei zu NAD⁺ oxidiert."),
  ("A", "Die Elektronen wandern nun von Komplex zu Komplex. Das ist eine Kette von Redoxreaktionen: Jeder Komplex wird erst reduziert und dann wieder oxidiert."),
  ("B", "Bei jedem Schritt wird etwas Energie frei. Damit pumpen die Komplexe Protonen, also H⁺-Ionen, durch die Membran in den Raum zwischen den beiden Membranen."),
  ("A", "Am Ende nimmt Sauerstoff die Elektronen auf. Er wird reduziert, und zusammen mit Protonen entsteht Wasser. Dafür atmen wir Sauerstoff ein."),
  ("B", "Jetzt sind auf der einen Seite viele Protonen und auf der anderen wenige. In diesem Unterschied steckt Energie, wie bei Wasser hinter einem Staudamm."),
  ("A", "Die Protonen können nur durch ein Enzym zurückfließen: die ATP-Synthase. Sie dreht sich dabei wie eine Turbine."),
  ("B", "Mit dieser Drehung wird ADP mit einer Phosphatgruppe zu ATP verbunden. Die Energie steckt jetzt im ATP."),
 ]),
 ("fluss", "Der Weg der Energie", [
  ("A", "Fassen wir den Weg der Energie zusammen."),
  ("B", "Erstens: Die Energie aus Nährstoffen wird mit Elektronen auf NAD⁺ übertragen. Es entsteht NADH."),
  ("A", "Zweitens: NADH gibt die Elektronen ab. Über Redoxreaktionen wird die Energie genutzt, um Protonen zu pumpen."),
  ("B", "Drittens: Der Rückfluss der Protonen treibt die ATP-Synthase an, und es entsteht ATP."),
  ("A", "Viertens: ATP liefert die Energie für die Arbeit der Zelle."),
 ]),
 ("kreislauf", "Ein Kreislauf – nichts wird verbraucht", [
  ("B", "Und das Beste: Die Transportmoleküle werden nicht verbraucht. NAD⁺ und ADP werden immer wieder neu beladen."),
  ("A", "Dein Körper bildet so jeden Tag ungefähr so viel ATP, wie du selbst wiegst."),
 ]),
 ("merke", "Das Wichtigste auf einen Blick", [
  ("B", "Merke dir: Oxidation bedeutet Elektronenabgabe, Reduktion bedeutet Elektronenaufnahme."),
  ("A", "NADH transportiert Elektronen, und ATP liefert die Energie für die Zelle."),
  ("B", "Danke fürs Zuschauen!"),
 ]),
]

# ---------------------------------------------------------------- helpers
_fonts = {}


def font(size, bold=True):
    k = (int(size * SS), bold)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(BOLD if bold else REG, max(6, k[0]))
    return _fonts[k]


def cl(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = cl(x); return 1 - (1 - x) ** 3


def back(x):
    x = cl(x); c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def lerp(a, b, p):
    return a + (b - a) * p


def mix(c1, c2, p):
    return tuple(int(lerp(a, b, cl(p))) for a, b in zip(c1, c2))


class Cv:
    def __init__(self, bg):
        self.img = bg.copy(); self.d = ImageDraw.Draw(self.img, "RGBA")

    @staticmethod
    def c(col, a):
        return None if col is None else (col[0], col[1], col[2], int(255 * cl(a)))

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=3, r=0, a=1.0):
        if a <= 0.01 or x1 - x0 < 1 or y1 - y0 < 1: return
        r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
        self.d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], r * SS, fill=self.c(fill, a),
                                 outline=self.c(outline, a), width=int(width * SS))

    def circ(self, x, y, r, fill=None, outline=None, width=3, a=1.0):
        if a <= 0.01 or r < 0.5: return
        self.d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=self.c(fill, a),
                       outline=self.c(outline, a), width=int(width * SS))

    def line(self, pts, fill=WHITE, width=4, a=1.0):
        if a <= 0.01: return
        self.d.line([(x * SS, y * SS) for x, y in pts], fill=self.c(fill, a), width=int(width * SS), joint="curve")

    def poly(self, pts, fill, a=1.0):
        if a <= 0.01: return
        self.d.polygon([(x * SS, y * SS) for x, y in pts], fill=self.c(fill, a))

    def arrow(self, x0, y0, x1, y1, fill=WHITE, width=6, a=1.0, p=1.0, head=20):
        """Arrow that grows with p (0..1)."""
        if a <= 0.01 or p <= 0.02: return
        x1, y1 = lerp(x0, x1, p), lerp(y0, y1, p)
        ang = math.atan2(y1 - y0, x1 - x0)
        bx, by = x1 - head * math.cos(ang), y1 - head * math.sin(ang)
        self.line([(x0, y0), (bx, by)], fill, width, a)
        self.poly([(x1, y1), (bx + head * 0.6 * math.sin(ang), by - head * 0.6 * math.cos(ang)),
                   (bx - head * 0.6 * math.sin(ang), by + head * 0.6 * math.cos(ang))], fill, a)

    def arc_arrow(self, cx, cy, r, a0, a1, fill=WHITE, width=6, a=1.0, head=20):
        """Arc from angle a0 to a1 (degrees, clockwise on screen), arrow head at a1."""
        if a <= 0.01: return
        n = max(8, int(abs(a1 - a0) / 4))
        pts = [(cx + r * math.cos(math.radians(lerp(a0, a1, i / n))),
                cy + r * math.sin(math.radians(lerp(a0, a1, i / n)))) for i in range(n + 1)]
        self.line(pts[:-1], fill, width, a)
        (px, py), (qx, qy) = pts[-3], pts[-1]
        ang = math.atan2(qy - py, qx - px)
        bx, by = qx - head * math.cos(ang), qy - head * math.sin(ang)
        self.poly([(qx, qy), (bx + head * 0.6 * math.sin(ang), by - head * 0.6 * math.cos(ang)),
                   (bx - head * 0.6 * math.sin(ang), by + head * 0.6 * math.cos(ang))], fill, a)

    def text(self, x, y, s, size=40, fill=WHITE, anchor="mm", a=1.0, bold=True):
        if a <= 0.01 or not s: return
        self.d.text((x * SS, y * SS), s, font=font(size, bold), fill=self.c(fill, a), anchor=anchor)

    def tw(self, s, size, bold=True):
        return self.d.textlength(s, font=font(size, bold)) / SS

    def chip(self, x, y, s, size=34, fill=PANEL, tcol=WHITE, a=1.0, pad=22, outline=None, sc=1.0):
        """Rounded label centred at x,y."""
        if a <= 0.01 or sc <= 0.05: return
        size *= sc
        w, h = self.tw(s, size) + 2 * pad * sc, size * 1.75
        self.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, fill, outline, 3, h / 2, a)
        self.text(x, y, s, size, tcol, "mm", a)

    def token(self, x, y, kind, a=1.0, sc=1.0):
        """Small molecule tokens used in several scenes."""
        if kind == "e":
            self.circ(x, y, 17 * sc, EL, (120, 90, 0), 2, a); self.text(x, y, "e⁻", 19 * sc, (60, 40, 0), "mm", a)
        elif kind == "H":
            self.circ(x, y, 19 * sc, HP, (120, 20, 40), 2, a); self.text(x, y, "H⁺", 19 * sc, (255, 255, 255), "mm", a)
        else:
            col = {"NADH": NADH_C, "NAD⁺": NAD_C, "ATP": ATP_C, "ADP + P": ADP_C, "O₂": O2C, "H₂O": (70, 140, 230)}[kind]
            dark = kind in ("NADH", "ATP", "O₂")
            self.chip(x, y, kind, 30, col, (20, 25, 35) if dark else WHITE, a, 18, (255, 255, 255), sc)

    def battery(self, x, y, level, a=1.0, w=150, h=70):
        self.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, None, WHITE, 5, 12, a)
        self.rect(x + w / 2, y - h / 5, x + w / 2 + 12, y + h / 5, WHITE, None, 0, 4, a)
        col = mix((230, 80, 70), ATP_C, level)
        inner = (w - 22) * cl(level)
        self.rect(x - w / 2 + 11, y - h / 2 + 11, x - w / 2 + 11 + inner, y + h / 2 - 11, col, None, 0, 5, a)

    def bolt(self, x, y, s=1.0, a=1.0, col=EL):
        p = [(8, -40), (-22, 6), (-2, 6), (-10, 40), (24, -10), (4, -10)]
        self.poly([(x + px * s, y + py * s) for px, py in p], col, a)

    def mito(self, cx, cy, w, h, a=1.0, hl=0.0):
        """Schematic mitochondrion; hl highlights the inner membrane."""
        om, im, mat, dk = (246, 178, 107), (255, 220, 160), (150, 62, 50), (92, 35, 26)
        self.rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, om, (180, 95, 6), 7, h / 2, a)
        g = h * 0.085
        inner_col = mix(dk, EL, hl)
        iw = 6 + 5 * hl
        self.rect(cx - w / 2 + g, cy - h / 2 + g, cx + w / 2 - g, cy + h / 2 - g, mat, inner_col, iw, h / 2, a)
        n = 7; x0 = cx - w / 2 + h * 0.42; x1 = cx + w / 2 - h * 0.42; fw = h * 0.085
        for i in range(n):
            x = lerp(x0, x1, i / (n - 1)); top = i % 2 == 0
            ln = h * (0.52 if 0 < i < n - 1 else 0.40)
            if top:
                ya, yb = cy - h / 2 + g - 3, cy - h / 2 + g + ln
            else:
                ya, yb = cy + h / 2 - g - ln, cy + h / 2 - g + 3
            self.rect(x - fw, ya, x + fw, yb, im if hl < 0.5 else mix(im, (255, 245, 200), hl), inner_col, iw, fw, a)
            # open the finger towards the intermembrane space
            if top: self.rect(x - fw + iw, ya - 4, x + fw - iw, ya + fw, om, None, 0, 0, a)
            else: self.rect(x - fw + iw, yb - fw, x + fw - iw, yb + 4, om, None, 0, 0, a)


class T:
    """Timing of one scene: t = local time, L = start time of every spoken line."""
    def __init__(self, t, L, dur, gt):
        self.t, self.L, self.dur, self.gt = t, L, dur, gt

    def s(self, k, delay=0.0):
        return self.t - self.L[k] - delay if k < len(self.L) else -1.0

    def f(self, k, delay=0.0, d=0.5):
        return ease(self.s(k, delay) / d)

    def b(self, k, delay=0.0, d=0.5):
        return back(self.s(k, delay) / d) if self.s(k, delay) > 0 else 0.0


def path_pos(pts, s):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d = math.hypot(x1 - x0, y1 - y0)
        if s <= d:
            return lerp(x0, x1, s / d), lerp(y0, y1, s / d)
        s -= d
    return pts[-1]


def path_len(pts):
    return sum(math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(pts, pts[1:]))


def stream(c, pts, since, kind="e", speed=170, gap=95, n=None, sc=1.0):
    """Dots continuously flowing along a polyline once since > 0."""
    if since <= 0: return
    L = path_len(pts); n = n or int(L / gap) + 1
    for i in range(n):
        s = since * speed - i * gap
        if s < 0: continue
        s %= n * gap
        if s > L: continue
        a = min(1, s / 30, (L - s) / 30)
        c.token(*path_pos(pts, s), kind, a, sc)


# ---------------------------------------------------------------- scenes
def sc_title(c, T):
    c.mito(960, 330, 760 * back(T.t / 0.8), 300 * back(T.t / 0.8), 1.0)
    a = ease((T.t - 0.5) / 0.6)
    c.text(960, 590 + 30 * (1 - a), "Energiegewinnung im Mitochondrium", 78, WHITE, "mm", a)
    c.rect(960 - 330 * a, 648, 960 + 330 * a, 656, EL, None, 0, 4, a)
    for i, (s, col) in enumerate([("Redoxreaktion", OX), ("NADH", NADH_C), ("ATP", ATP_C)]):
        c.chip(560 + i * 400, 760, s, 46, col, (20, 25, 35), 1, 34, None, T.b(1, 1.2 + i * 1.3))
    c.text(960, 860, "Wie wird Energie auf Transportmoleküle übertragen?", 36, GREY, "mm", T.f(1, 0.3), False)


def sc_kraftwerk(c, T):
    hl = T.f(2, 0.3, 0.8) * (0.75 + 0.25 * math.sin(T.t * 4))
    c.mito(760, 500, 1000 * back(T.t / 0.7), 400 * back(T.t / 0.7), 1.0, hl if T.s(2) > 0 else 0)
    def lab(x, y, tx, ty, s, k, dl, col=WHITE):
        a = T.f(k, dl)
        c.line([(x, y), (tx - 14, ty)], col, 3, a); c.circ(x, y, 8, col, None, 0, a)
        c.text(tx, ty, s, 38, col, "lm", a)
    lab(1180, 345, 1400, 250, "äußere Membran", 1, 1.2)
    lab(1085, 520, 1400, 420, "innere Membran", 1, 3.0, mix(WHITE, EL, hl))
    c.text(1400, 466, "(stark gefaltet)", 30, GREY, "lm", T.f(1, 3.0), False)
    lab(1243, 520, 1400, 610, "Intermembranraum", 1, 7.0, GREY)
    lab(1000, 640, 1400, 760, "Matrix", 1, 6.0)
    for i in range(5):
        s = T.s(2, 2.0 + i * 0.5)
        if s > 0:
            ph = (s % 3.0) / 3.0
            x = 420 + i * 170
            c.token(x, 500 - 260 * ph - 40, "ATP", min(1, ph * 5, (1 - ph) * 3))
    for i in range(3):
        c.bolt(250 + i * 70, 220 + (i % 2) * 30, 1.0, T.f(0, 0.8 + i * 0.3) * (0.7 + 0.3 * math.sin(T.t * 5 + i)) * (1 - T.f(2, 0)))


def sc_transport(c, T):
    a0 = T.f(0, 0.2)
    c.rect(110, 240, 470, 400, PANEL, (246, 178, 107), 4, 28, a0)
    c.text(290, 295, "Nährstoffe", 44, (246, 178, 107), "mm", a0)
    c.text(290, 352, "z. B. Glucose", 30, GREY, "mm", a0, False)
    c.rect(1450, 240, 1810, 400, PANEL, ATP_C, 4, 28, T.f(0, 2.0))
    c.text(1630, 295, "Zellarbeit", 44, ATP_C, "mm", T.f(0, 2.0))
    c.text(1630, 352, "Bewegung, Transport", 30, GREY, "mm", T.f(0, 2.0), False)
    c.arrow(500, 320, 1420, 320, GREY, 7, T.f(0, 1.0), T.f(0, 1.0, 1.2))
    q = T.f(0, 1.5) * (1 - T.f(1, 0.3))
    c.text(960, 300 + 8 * math.sin(T.t * 3), "?", 150, EL, "mm", q)
    a1 = T.f(1, 0.4)
    c.chip(960, 320, "Transportmoleküle", 44, (40, 62, 100), EL, a1, 30, EL)
    for i in range(3):
        lv = (T.t * 0.35 + i * 0.33) % 1.0
        c.battery(790 + i * 170, 470, lv, a1 * (1 - T.f(2, 0.0)))
    # cards
    for k, (x, name, sub1, sub2, col) in enumerate([(610, "NADH", "transportiert", "energiereiche Elektronen", NADH_C),
                                                    (1310, "ATP", "universelle", "Energiewährung der Zelle", ATP_C)]):
        s = T.b(2 + k, 0.2 if k else 1.6)
        if s <= 0.02: continue
        w, h = 560 * s, 400 * s; y = 680
        c.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, PANEL, col, 5, 34)
        c.text(x, y - 120 * s, name, 84 * s, col)
        c.text(x, y + 100 * s, sub1, 34 * s, WHITE, "mm", 1, False)
        c.text(x, y + 148 * s, sub2, 34 * s, WHITE)
        if k == 0:
            for j in range(2):
                c.token(x - 40 + j * 80 + 6 * math.sin(T.t * 4 + j), y - 15 * s, "e", 1, 1.5 * s)
        else:
            c.battery(x, y - 15 * s, 0.5 + 0.5 * math.sin(T.t * 1.5) ** 2, 1, 170 * s, 76 * s)


def sc_redox(c, T):
    ax, bx, y, r = 520, 1400, 500, 150
    a = T.f(0, 0.2)
    c.circ(ax, y, r, (60, 44, 60), OX, 6, a); c.text(ax, y, "Stoff A", 54, WHITE, "mm", a)
    c.circ(bx, y, r, (40, 52, 80), RED, 6, a); c.text(bx, y, "Stoff B", 54, WHITE, "mm", a)
    s = T.s(1, 0.6)
    if s > 0:
        c.arrow(ax + r + 30, y, bx - r - 30, y, (90, 105, 130), 5, 1, ease(s / 0.8))
        for i in range(2):
            ph = ((s * 0.33 + i * 0.12) % 1.0)
            x = lerp(ax + r - 30, bx - r - 28, ease(ph * 1.15) if ph < 0.87 else 1)
            c.token(x, y - 34 + i * 68 - 50 * math.sin(math.pi * cl(ph * 1.15)), "e", min(1, ph * 8, (1 - ph) * 8), 1.7)
    a1, a2 = T.f(1, 0.3), T.f(2, 0.3)
    c.text(ax, y + r + 60, "Oxidation", 56, OX, "mm", a1)
    c.text(ax, y + r + 120, "gibt Elektronen ab", 36, WHITE, "mm", a1, False)
    c.text(bx, y + r + 60, "Reduktion", 56, RED, "mm", a2)
    c.text(bx, y + r + 120, "nimmt Elektronen auf", 36, WHITE, "mm", a2, False)
    a3 = T.f(3, 5.0)
    c.line([(ax, 270), (ax, 235), (bx, 235), (bx, 270)], EL, 5, a3)
    c.chip(960, 235, "Redoxreaktion  =  Reduktion + Oxidation", 44, (40, 62, 100), EL, a3, 30, EL)
    a4 = T.f(4, 0.8)
    c.bolt(960, 590, 1.2, a4 * (0.7 + 0.3 * math.sin(T.t * 6)))
    c.text(960, 345, "Elektronen übertragen Energie", 40, EL, "mm", a4)


def cycle_boxes(c, T, y, left, right, lcol, rcol, lsub, rsub, a_l, a_r):
    lx, rx, w, h = 470, 1450, 400, 190
    c.rect(lx - w / 2, y - h / 2, lx + w / 2, y + h / 2, PANEL, lcol, 6, 36, a_l)
    c.text(lx, y - 18, left, 80, lcol, "mm", a_l); c.text(lx, y + 58, lsub, 30, GREY, "mm", a_l, False)
    c.rect(rx - w / 2, y - h / 2, rx + w / 2, y + h / 2, PANEL, rcol, 6, 36, a_r)
    c.text(rx, y - 18, right, 80, rcol, "mm", a_r); c.text(rx, y + 58, rsub, 30, GREY, "mm", a_r, False)
    return lx, rx, w, h


def sc_nadh(c, T):
    y = 520
    lx, rx, w, h = cycle_boxes(c, T, y, "NAD⁺", "NADH", NAD_C, NADH_C, "leer · energiearm", "beladen · energiereich",
                               T.f(0, 3.0), T.f(1, 4.5))
    # top arrow: reduction
    s = T.s(1, 3.5)
    if s > 0:
        p = ease(s / 1.0)
        c.arrow(lx + w / 2 + 20, y - 50, rx - w / 2 - 20, y - 50, RED, 7, 1, p)
        c.text(960, y - 150, "nimmt 2 e⁻ + H⁺ auf", 40, WHITE, "mm", p)
        c.chip(960, y - 215, "Reduktion", 40, (30, 50, 90), RED, T.f(2, 0.3), 26, RED)
        for i, kind in enumerate(["e", "e", "H"]):
            ph = (s * 0.4 + i * 0.1) % 1.0
            c.token(*path_pos([(520, 255), (700, y - 50), (1240, y - 50)], ph * 790), kind,
                    min(1, ph * 8, (1 - ph) * 8), 1.3)
        c.text(520, 205, "aus Nährstoffen", 30, GREY, "mm", p, False)
    s = T.s(3, 0.5)
    if s > 0:
        p = ease(s / 1.0)
        c.arrow(rx - w / 2 - 20, y + 50, lx + w / 2 + 20, y + 50, OX, 7, 1, p)
        c.text(960, y + 105, "gibt 2 e⁻ + H⁺ ab", 40, WHITE, "mm", p)
        c.chip(960, y + 172, "Oxidation", 40, (70, 40, 40), OX, p, 26, OX)
    a = T.f(1, 6.5)
    c.rect(400, 765, 1520, 865, PANEL, None, 0, 24, a)
    c.text(960, 815, "NAD⁺  +  2 e⁻  +  H⁺    ⇄    NADH", 50, WHITE, "mm", a)


def molecule(c, x, y, n, a=1.0, third=1.0, shake=0.0):
    """Adenosine block + n phosphate groups; 'third' animates the last P."""
    c.rect(x - 150, y - 45, x + 20, y + 45, (150, 110, 220), WHITE, 3, 16, a)
    c.text(x - 65, y, "Adenosin", 28, WHITE, "mm", a)
    for i in range(n):
        px = x + 62 + i * 78
        aa, off = a, 0
        if i == 2:
            aa = a * cl(third * 2); off = (1 - ease(third)) * 120
        c.line([(px - 42, y), (px - 30 + off, y)], EL if i == 2 else WHITE, 6 if i == 2 else 4, aa)
        c.circ(px + off + shake * math.sin(i * 2.1), y, 30, (240, 170, 50) if i < 2 else EL, WHITE, 3, aa)
        c.text(px + off, y, "P", 30, (40, 30, 0), "mm", aa)


def sc_atp(c, T):
    y = 520
    lx, rx, w, h = cycle_boxes(c, T, y + 30, "ADP", "ATP", ADP_C, ATP_C, "entladen", "geladen", T.f(1, 0.3), T.f(0, 0.5))
    third = 1.0
    if T.s(2) > 0:
        third = ease((T.s(2, 0.3) % 4.0) / 1.5) if T.s(3) < 0 else 1.0
    molecule(c, rx - 60, y - 150, 3, T.f(0, 1.5), third)
    molecule(c, lx - 30, y - 150, 2, T.f(1, 1.0))
    c.battery(lx, y + 190, 0.12, T.f(1, 2.5)); c.battery(rx, y + 190, 1.0, T.f(2, 3.5))
    s = T.s(2, 0.5)
    if s > 0:
        p = ease(s / 1.0)
        c.arrow(lx + w / 2 + 20, y - 20, rx - w / 2 - 20, y - 20, ATP_C, 7, 1, p)
        c.text(960, y - 70, "+ P  + Energie", 40, WHITE, "mm", p)
        c.bolt(790, y - 150, 0.9, p * (0.6 + 0.4 * math.sin(T.t * 6)))
    s = T.s(3, 0.5)
    if s > 0:
        p = ease(s / 1.0)
        c.arrow(rx - w / 2 - 20, y + 80, lx + w / 2 + 20, y + 80, EL, 7, 1, p)
        c.text(960, y + 130, "Energie wird frei", 40, EL, "mm", p)
        c.text(960, y + 180, "(ca. 30 kJ pro mol)", 28, GREY, "mm", p, False)
        c.chip(790, y + 245, "Muskelbewegung", 30, PANEL, WHITE, T.f(3, 4.0), 20, EL)
        c.chip(1140, y + 245, "Stofftransport", 30, PANEL, WHITE, T.f(3, 5.5), 20, EL)
    a = T.f(2, 5.0)
    c.rect(480, 812, 1440, 888, PANEL, None, 0, 24, a)
    c.text(960, 850, "ADP  +  P  +  Energie    ⇄    ATP", 44, WHITE, "mm", a)


CX = [330, 660, 990]; SX = 1500; MY0, MY1 = 440, 560
_rng = random.Random(7)
POOL = [(_rng.uniform(120, 1800), _rng.uniform(215, 395), _rng.uniform(0, 6.3)) for _ in range(34)]
POOL_LOW = [(_rng.uniform(150, 1750), _rng.uniform(600, 640), _rng.uniform(0, 6.3)) for _ in range(3)]


def sc_kette(c, T):
    t = T.t; a = ease(t / 0.8)
    c.text(70, 150, "Intermembranraum (zwischen den Membranen)", 32, GREY, "lm", a, False)
    c.text(1850, 610, "Matrix (innen)", 32, GREY, "rm", a, False)
    # membrane
    c.rect(-20, MY0, W + 20, MY1, (120, 92, 60), None, 0, 0, a)
    for i in range(0, 90):
        c.circ(12 + i * 22, MY0 + 4, 10, (232, 201, 138), (120, 92, 60), 2, a)
        c.circ(12 + i * 22, MY1 - 4, 10, (232, 201, 138), (120, 92, 60), 2, a)
    for k, (x, name) in enumerate(zip(CX, ["I", "III", "IV"])):
        s = back((t - 0.6 - k * 0.3) / 0.5) if t > 0.6 + k * 0.3 else 0
        c.rect(x - 75 * s, 500 - 95 * s, x + 75 * s, 500 + 95 * s, (70, 105, 200), (190, 210, 255), 5, 40)
        c.text(x - 22, 462, name, 40 * s, WHITE)
    s = back((t - 1.6) / 0.5) if t > 1.6 else 0
    spin = T.s(6, 1.0)
    if s > 0:
        c.rect(SX - 48 * s, 500 - 95 * s, SX + 48 * s, 500 + 95 * s, (40, 150, 110), (170, 240, 210), 5, 24)
        c.rect(SX - 14, 590, SX + 14, 620, (40, 150, 110), None, 0, 0, s)
        c.circ(SX, 680, 78 * s, (40, 150, 110), (170, 240, 210), 5)
        ang = max(0, spin) * 3.0
        for j in range(3):
            aa = ang + j * 2.094
            c.line([(SX, 680), (SX + 62 * s * math.cos(aa), 680 + 62 * s * math.sin(aa))], (170, 240, 210), 6)
        c.circ(SX, 680, 14 * s, (170, 240, 210))
        c.text(SX, 368, "ATP-Synthase", 30, (170, 240, 210), "mm", cl(s))
    c.text(660, 660, "Proteinkomplexe", 30, (190, 210, 255), "mm", ease((t - 1.5) / 0.5), False)

    # --- NADH delivers electrons (line 1)
    s = T.s(1, 0.3)
    if s > 0:
        ph = s % 6.0
        if ph < 1.6:
            p = ease(ph / 1.6); c.token(lerp(90, 215, p), lerp(800, 690, p), "NADH", min(1, ph * 4), 1.15)
        elif ph < 2.4:
            c.token(215, 690, "NADH" if ph < 2.0 else "NAD⁺", 1, 1.15)
        else:
            p = ease((ph - 2.4) / 2.5); c.token(lerp(215, 110, p), lerp(690, 830, p), "NAD⁺", 1 - p, 1.15)
        c.chip(330, 866, "NADH wird oxidiert", 30, (70, 40, 40), OX, ease((s - 2) / 0.5), 20, OX)
        stream(c, [(250, 670), (330, 610), (330, 545)], s - 2.0, "e", 150, 60, 2)
    # --- electrons along the chain (line 2)
    epath = [(330, 545), (660, 545), (990, 545), (990, 610)]
    stream(c, epath, T.s(2, 0.3), "e", 150, 110)
    # --- proton pumping (line 3)
    sp = T.s(3, 1.5)
    if sp > 0:
        for k, x in enumerate(CX):
            stream(c, [(x + 45, 640), (x + 45, 330)], sp - k * 0.4, "H", 140, 110, None, 0.85)
        c.chip(660, 285, "H⁺ werden gepumpt", 30, (70, 30, 45), HP, ease(sp / 0.5) * (1 - T.f(5, 0)), 20, HP)
    npool = int(cl(sp / 14) * len(POOL)) if sp > 0 else 0
    for i, (x, y, ph) in enumerate(POOL[:npool]):
        if abs(x - 660) < 330 and 240 < y < 330: continue
        if abs(x - SX) < 140 and y > 325: continue
        c.token(x + 6 * math.sin(t * 1.3 + ph), y + 5 * math.cos(t * 1.1 + ph), "H", 0.95, 0.9)
    for x, y, ph in POOL_LOW:
        if 200 < x < 1130 or abs(x - SX) < 150: x = 1250 + (x % 100)
        c.token(x + 6 * math.sin(t + ph), y + 30, "H", 0.9 * a, 0.9)
    # --- oxygen is reduced (line 4)
    s = T.s(4, 0.5)
    if s > 0:
        ph = s % 6.0
        if ph < 2.2:
            p = ease(ph / 1.6); c.token(lerp(1180, 1090, p), lerp(820, 680, p), "O₂", min(1, ph * 4), 1.15)
        else:
            p = ease((ph - 2.2) / 3.0); c.token(lerp(1070, 880, p), lerp(690, 790, p), "H₂O", min(1, (1 - p) * 3), 1.15)
        c.chip(990, 866, "O₂ wird reduziert  →  H₂O", 30, (30, 50, 90), RED, ease((s - 1.5) / 0.5), 20, RED)
    # --- gradient (line 5)
    a5 = T.f(5, 0.5)
    c.chip(660, 285, "viele H⁺  =  gespeicherte Energie", 32, (70, 30, 45), WHITE, a5, 22, HP)
    c.text(1250, 600, "wenige H⁺", 28, HP, "mm", a5, False)
    # --- ATP synthase (lines 6, 7)
    if spin > 0:
        stream(c, [(SX, 330), (SX, 600)], spin, "H", 170, 90)
    s = T.s(7, 0.5)
    if s > 0:
        ph = s % 4.0
        if ph < 1.8:
            p = ease(ph / 1.4); c.token(lerp(1250, 1360, p), lerp(800, 700, p), "ADP + P", min(1, ph * 4), 1.0)
        else:
            p = ease((ph - 1.8) / 2.0); c.token(lerp(1640, 1790, p), lerp(700, 790, p), "ATP", min(1, (1 - p) * 3), 1.3)
        c.chip(SX, 866, "ADP + P  →  ATP", 30, (25, 70, 50), ATP_C, ease(s / 0.5), 20, ATP_C)


def sc_fluss(c, T):
    boxes = [("Nährstoffe", (246, 178, 107)), ("NADH", NADH_C), ("H⁺-Gefälle", HP), ("ATP", ATP_C), ("Zellarbeit", WHITE)]
    bw, gap, y = 290, 78, 300
    xs = [90 + bw / 2 + i * (bw + gap) for i in range(5)]
    app = [T.f(0, 0.3), T.f(1, 2.5), T.f(2, 3.0), T.f(3, 2.5), T.f(4, 1.0)]
    for i, ((s, col), x) in enumerate(zip(boxes, xs)):
        c.rect(x - bw / 2, y - 70, x + bw / 2, y + 70, PANEL, col, 5, 28, app[i])
        c.text(x, y, s, 40, col, "mm", app[i])
        if i:
            c.arrow(xs[i - 1] + bw / 2 + 8, y, x - bw / 2 - 8, y, GREY, 6, app[i], app[i], 18)
    # travelling energy pulse
    last = max([i for i in range(5) if app[i] > 0.9] or [0])
    if last > 0:
        ph = (T.t * 0.35) % 1.0
        c.bolt(lerp(xs[0], xs[last], ph), y - 110, 0.6, min(1, ph * 6, (1 - ph) * 6))
    rows = [("1", "Elektronen aus Nährstoffen reduzieren NAD⁺ zu NADH", NADH_C),
            ("2", "NADH wird oxidiert – die Redoxkette pumpt H⁺ durch die Membran", HP),
            ("3", "H⁺ fließen durch die ATP-Synthase zurück: ADP + P → ATP", ATP_C),
            ("4", "ATP wird gespalten und liefert Energie für die Zelle", WHITE)]
    for i, (n, s, col) in enumerate(rows):
        a = T.f(i + 1, 0.4); yy = 480 + i * 105
        c.rect(150, yy - 42, 1770, yy + 42, PANEL, None, 0, 22, a)
        c.circ(205, yy, 30, col, None, 0, a); c.text(205, yy, n, 36, (20, 25, 35), "mm", a)
        c.text(260, yy, s, 36, WHITE, "lm", a, i == sum(1 for k in range(1, 5) if T.s(k) > 0) - 1)


def sc_kreislauf(c, T):
    for k, (cx, top, bot, tc, bc, mid) in enumerate([(520, "NADH", "NAD⁺", NADH_C, NAD_C, "e⁻"),
                                                     (1400, "ATP", "ADP + P", ATP_C, ADP_C, "Energie")]):
        a = T.f(0, 0.3 + k * 1.5); cy, r = 500, 190
        rot = T.t * 25
        c.arc_arrow(cx, cy, r, -60 + rot % 1 * 0, 60, tc, 8, a)
        c.arc_arrow(cx, cy, r, 120, 240, bc if k else GREY, 8, a)
        ph = (T.t * 0.25) % 1.0
        ang = math.radians(-90 + 360 * ph)
        c.circ(cx + r * math.cos(ang), cy + r * math.sin(ang), 14, EL, None, 0, a)
        c.chip(cx, cy - r, top, 46, tc, (20, 25, 35), a, 28)
        c.chip(cx, cy + r, bot, 46, bc, WHITE, a, 28)
        c.text(cx + r + 30, cy, "entladen", 30, GREY, "lm", a, False)
        c.text(cx - r - 30, cy, "beladen", 30, GREY, "rm", a, False)
        c.text(cx, cy, mid, 40, EL, "mm", a)
    a = T.f(1, 0.5)
    c.rect(380, 765, 1540, 895, PANEL, ATP_C, 4, 30, a)
    c.text(960, 808, "pro Tag etwa das eigene Körpergewicht an ATP", 38, WHITE, "mm", a)
    c.text(960, 858, "möglich, weil ADP ständig neu beladen wird", 30, GREY, "mm", a, False)


def sc_merke(c, T):
    rows = [("Oxidation", "= Abgabe von Elektronen", OX, 0, 0.3), ("Reduktion", "= Aufnahme von Elektronen", RED, 0, 3.0),
            ("NADH", "transportiert Elektronen:   NAD⁺ + 2 e⁻ + H⁺  ⇄  NADH", NADH_C, 1, 0.2),
            ("ATP", "liefert Energie:   ADP + P + Energie  ⇄  ATP", ATP_C, 1, 2.2)]
    for i, (h, s, col, k, dl) in enumerate(rows):
        a = T.f(k, dl); y = 240 + i * 135; x = 140 - 60 * (1 - a)
        c.rect(x, y - 52, x + 1640, y + 52, PANEL, None, 0, 24, a)
        c.rect(x, y - 52, x + 14, y + 52, col, None, 0, 6, a)
        c.text(x + 50, y, h, 46, col, "lm", a)
        c.text(x + 370, y, s, 36, WHITE, "lm", a, False)
    a = T.b(2, 0.1)
    if a > 0.02:
        c.text(960, 800, "Danke fürs Zuschauen!", 70 * a, EL)


DRAW = dict(title=sc_title, kraftwerk=sc_kraftwerk, transport=sc_transport, redox=sc_redox, nadh=sc_nadh,
            atp=sc_atp, kette=sc_kette, fluss=sc_fluss, kreislauf=sc_kreislauf, merke=sc_merke)


# ---------------------------------------------------------------- frame
def make_bg():
    yy, xx = np.mgrid[0:H * SS, 0:W * SS].astype(np.float32)
    r = np.sqrt(((xx / (W * SS)) - 0.5) ** 2 + ((yy / (H * SS)) - 0.42) ** 2)
    v = np.clip(1 - r * 1.25, 0, 1)[..., None]
    img = np.array([10, 18, 32], np.float32) + v * np.array([18, 30, 52], np.float32)
    out = np.dstack([img, np.full((H * SS, W * SS, 1), 255, np.float32)]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def wrap(c, s, size, maxw, bold=False):
    lines, cur = [], ""
    for w in s.split():
        if cur and c.tw(cur + " " + w, size, bold) > maxw:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + [cur]


G = {}


def render_frame(fi):
    t = fi / FPS
    scenes, total, bg = G["scenes"], G["total"], G["bg"]
    sc = next((s for s in scenes if s["start"] <= t < s["end"]), scenes[-1])
    lt = t - sc["start"]
    c = Cv(bg)
    DRAW[sc["kind"]](c, T(lt, [l["start"] - sc["start"] for l in sc["lines"]], sc["end"] - sc["start"], t))
    if sc["head"]:
        a = ease(lt / 0.5)
        c.text(70, 78, sc["head"], 50, WHITE, "lm", a)
        c.rect(70, 116, 70 + 150 * a, 122, EL, None, 0, 3, a)
    # caption
    ln = None
    for l in sc["lines"]:
        if l["start"] - 0.15 <= t < l["end"] + 0.25: ln = l
    if ln:
        name, col = SPK[ln["sp"]]
        a = min(1, (t - ln["start"] + 0.15) / 0.2, (ln["end"] + 0.25 - t) / 0.2)
        lines = wrap(c, ln["text"], 36, 1620)
        hh = 28 + len(lines) * 46
        y0 = 1056 - hh
        c.rect(100, y0, 1820, 1056, (0, 0, 0), None, 0, 20, 0.62 * a)
        c.rect(100, y0, 112, 1056, col, None, 0, 6, a)
        c.text(124, y0 - 22, name, 26, col, "lm", a)
        for i, s in enumerate(lines):
            c.text(960, y0 + 14 + 23 + i * 46, s, 36, WHITE, "mm", a, False)
    c.rect(0, 0, W * t / total, 6, EL, None, 0, 0, 0.9)
    img = c.img.reduce(SS).convert("RGB")
    fade = min(lt / 0.35, (sc["end"] - t) / 0.35, 1.0)
    if t < 0.35 or total - t < 0.5 or (fade < 1 and True):
        fade = max(0.0, min(fade, (total - t) / 0.5))
        img = Image.blend(G["bg_small"], img, fade)
    return img.tobytes()


def render_segment(args):
    k, f0, f1, path = args
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                           "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        ff.stdin.write(render_frame(fi))
    ff.stdin.close(); ff.wait()
    return path


# ---------------------------------------------------------------- audio
def say_text(s):
    for a, b in SAY:
        s = s.replace(a, b)
    return s


def tts(scenes):
    from piper import PiperVoice
    voices = {k: PiperVoice.load(p) for k, p in VOICES.items()}
    for v in voices.values():      # piper splits "ç" (ich-Laut) into c + cedilla; the old voices need it whole
        def fixed(text, _ph=v.phonemize):
            out = []
            for sent in _ph(text):
                r = []
                for ph in sent:
                    if ph == "\u0327" and r and r[-1] == "c": r[-1] = "ç"
                    else: r.append(ph)
                out.append(r)
            return out
        v.phonemize = fixed
    for sc in scenes:
        for l in sc["lines"]:
            b = io.BytesIO()
            with wave.open(b, "wb") as wf:
                voices[l["sp"]].synthesize_wav(say_text(l["text"]), wf)
            b.seek(0)
            with wave.open(b) as wf:
                sr = wf.getframerate()
                a = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
            n = int(len(a) * SR / sr)
            a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a)
            l["audio"] = a / max(0.05, np.abs(a).max()) * 0.85


def music(total):
    n = int(total * SR); t = np.arange(n) / SR
    prog = [(130.8, 196.0, 261.6, 329.6), (110.0, 164.8, 220.0, 261.6), (87.3, 174.6, 220.0, 261.6), (98.0, 196.0, 246.9, 293.7)]
    bar = 4.0; out = np.zeros(n, np.float32)
    for k in range(int(total / bar) + 1):
        s, e = int(k * bar * SR), min(n, int((k + 1) * bar * SR + 0.6 * SR))
        if s >= n: break
        tt = t[s:e] - k * bar
        env = np.minimum(1, tt / 0.8) * np.clip((bar + 0.6 - tt) / 0.8, 0, 1)
        for f in prog[k % 4]:
            out[s:e] += (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 2.005 * tt)) * env * 0.1
        for j in range(8):                       # soft plucked arpeggio
            f = prog[k % 4][(j * 3) % 4] * 2; i = int((k * bar + j * 0.5) * SR)
            if i >= n: break
            m = min(n - i, int(0.45 * SR)); pt = np.arange(m) / SR
            out[i:i + m] += np.sin(2 * np.pi * f * pt) * np.exp(-pt * 7) * 0.07
    return out * np.minimum(1, np.minimum(t / 1.5, (total - t) / 2.5))


def write_wav(path, x):
    x = x / max(1.0, np.abs(x).max() / 0.97)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((x * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- main
def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    work = os.path.join(out_dir, "mito_work"); os.makedirs(work, exist_ok=True)
    scenes = [dict(kind=k, head=h, lines=[dict(sp=s, text=x) for s, x in ls]) for k, h, ls in SCENES]
    tts(scenes)
    t = 0.0
    for sc in scenes:
        sc["start"] = t; t += 0.9
        for l in sc["lines"]:
            l["start"] = t; l["end"] = t + len(l["audio"]) / SR; t = l["end"] + 0.45
        t += 0.8; sc["end"] = t
    total = t
    voice = np.zeros(int(total * SR) + SR, np.float32)
    for sc in scenes:
        for l in sc["lines"]:
            i = int(l["start"] * SR); voice[i:i + len(l["audio"])] += l["audio"]
    voice = voice[: int(total * SR)]
    mus = music(total)[: len(voice)]
    write_wav(f"{work}/voice.wav", voice + mus * 0.16)
    write_wav(f"{work}/music.wav", mus * 0.5)

    with open(os.path.join(HERE, "SKRIPT.md"), "w") as f:
        f.write("# Skript: Energiegewinnung im Mitochondrium\n\n"
                f"Gesamtlänge: {int(total // 60)}:{int(total % 60):02d} min · zwei Sprecher im Wechsel. "
                "Die Zeitmarken passen zum Video – so könnt ihr die Version ohne Stimmen selbst einsprechen.\n")
        for sc in scenes:
            f.write(f"\n## {sc['head'] or 'Einstieg'}\n\n")
            for l in sc["lines"]:
                f.write(f"- `{int(l['start'] // 60)}:{int(l['start'] % 60):02d}` **{SPK[l['sp']][0]}:** {l['text']}\n")

    G.update(scenes=[dict(sc, lines=[{k: v for k, v in l.items() if k != "audio"} for l in sc["lines"]]) for sc in scenes],
             total=total, bg=make_bg())
    G["bg_small"] = G["bg"].reduce(SS).convert("RGB")
    if os.environ.get("FRAMES"):          # debug: dump single frames (seconds, comma separated)
        for s in os.environ["FRAMES"].split(","):
            Image.frombytes("RGB", (W, H), render_frame(int(float(s) * FPS))).save(f"{work}/f_{float(s):06.1f}.png")
        print("total", total, [(sc["kind"], round(sc["start"], 1), [round(l["start"], 1) for l in sc["lines"]]) for sc in scenes])
        return
    nf = int(total * FPS); nproc = os.cpu_count() or 2; step = math.ceil(nf / (nproc * 4))
    jobs = [(k, f0, min(nf, f0 + step), f"{work}/seg{k:03d}.mp4") for k, f0 in enumerate(range(0, nf, step))]
    with Pool(nproc) as pool:
        segs = pool.map(render_segment, jobs, chunksize=1)
    with open(f"{work}/list.txt", "w") as f:
        f.writelines(f"file '{os.path.abspath(s)}'\n" for s in segs)
    for name, wav in [("mitochondrien-energie.mp4", "voice.wav"), ("mitochondrien-energie-ohne-ton.mp4", "music.wav")]:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{work}/list.txt",
                        "-i", f"{work}/{wav}", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                        "-movflags", "+faststart", os.path.join(out_dir, name)], check=True)
        print(os.path.join(out_dir, name), f"{total:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "videos"))
