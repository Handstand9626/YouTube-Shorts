"""Winziger PDF-Erzeuger ohne Fremdbibliotheken (Text, Linien, Flaechen, Tabellen).

Nutzt die in jedem PDF-Betrachter vorhandenen Standardschriften Helvetica und
Helvetica-Bold mit WinAnsi-Kodierung (deckt Umlaute und das Euro-Zeichen ab).
"""
from __future__ import annotations

import zlib
from typing import List, Optional, Sequence, Tuple

PAGE_W, PAGE_H = 595.28, 841.89   # DIN A4 in Punkt
MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 48.0, 56.0, 56.0

# Zeichenbreiten (1/1000 der Schriftgroesse) fuer ASCII 32-126
_W_REGULAR = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
              556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
              1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
              667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
              333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
              556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]
_W_BOLD = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
           556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
           975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
           667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
           333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
           611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584]
_EXTRA_REGULAR = {"Ä": 667, "Ö": 778, "Ü": 722, "ä": 556, "ö": 556, "ü": 556, "ß": 611,
                  "€": 556, "–": 556, "·": 278, "Ø": 778, "°": 400, "§": 556, "„": 333, "“": 333}
_EXTRA_BOLD = {"Ä": 722, "Ö": 778, "Ü": 722, "ä": 556, "ö": 611, "ü": 611, "ß": 611,
               "€": 556, "–": 556, "·": 278, "Ø": 778, "°": 400, "§": 556, "„": 500, "“": 500}
_REPLACEMENTS = {"−": "-", "→": "->", "≥": ">=", "≤": "<=", "…": "...", " ": " ",
                 "’": "'", "‘": "'", "”": '"', "×": "x", "•": "·"}

Color = Tuple[float, float, float]
BLACK: Color = (0.04, 0.04, 0.04)
GRAY: Color = (0.32, 0.32, 0.31)
MUTED: Color = (0.54, 0.53, 0.51)
RULE: Color = (0.88, 0.88, 0.85)


def sanitize(text: str) -> str:
    for src, dst in _REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text.encode("cp1252", errors="replace").decode("cp1252")


def text_width(text: str, size: float, bold: bool = False) -> float:
    table, extra = (_W_BOLD, _EXTRA_BOLD) if bold else (_W_REGULAR, _EXTRA_REGULAR)
    total = 0
    for ch in sanitize(text):
        code = ord(ch)
        if 32 <= code <= 126:
            total += table[code - 32]
        else:
            total += extra.get(ch, 556)
    return total * size / 1000.0


def _escape(text: str) -> bytes:
    raw = sanitize(text).encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


class PdfDoc:
    def __init__(self, title: str = "", author: str = "KI Crypto Trader"):
        self.title = title
        self.author = author
        self.pages: List[List[bytes]] = []
        self.y = 0.0
        self.footer_left = ""
        self.new_page()

    # -- Grundoperationen --------------------------------------------------------
    @property
    def content_width(self) -> float:
        return PAGE_W - 2 * MARGIN_X

    def new_page(self) -> None:
        self.pages.append([])
        self.y = PAGE_H - MARGIN_TOP

    def ensure(self, height: float) -> None:
        if self.y - height < MARGIN_BOTTOM:
            self.new_page()

    def _op(self, data: str) -> None:
        self.pages[-1].append(data.encode("latin-1"))

    def text(self, x: float, y: float, text: str, size: float = 10, bold: bool = False,
             color: Color = BLACK, page: Optional[int] = None) -> None:
        font = "F2" if bold else "F1"
        r, g, b = color
        data = (f"BT /{font} {size:.2f} Tf {r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} Td (".encode()
                + _escape(text) + b") Tj ET")
        (self.pages[-1] if page is None else self.pages[page]).append(data)

    def text_right(self, x_right: float, y: float, text: str, size: float = 10,
                   bold: bool = False, color: Color = BLACK) -> None:
        self.text(x_right - text_width(text, size, bold), y, text, size, bold, color)

    def line(self, x1: float, y1: float, x2: float, y2: float, width: float = 0.6,
             color: Color = RULE) -> None:
        r, g, b = color
        self._op(f"{width:.2f} w {r:.3f} {g:.3f} {b:.3f} RG {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def rect(self, x: float, y: float, w: float, h: float, fill: Color) -> None:
        r, g, b = fill
        self._op(f"{r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")

    def wrap(self, text: str, size: float, max_width: float, bold: bool = False) -> List[str]:
        lines: List[str] = []
        for paragraph in text.split("\n"):
            words = paragraph.split()
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                if text_width(candidate, size, bold) <= max_width or not current:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return lines

    # -- Fliesstext-Bausteine ------------------------------------------------------
    def spacer(self, height: float) -> None:
        self.y -= height

    def heading(self, text: str, size: float = 13, space_before: float = 16) -> None:
        self.ensure(space_before + size + 40)
        self.y -= space_before + size
        self.text(MARGIN_X, self.y, text, size, bold=True)
        self.y -= 6
        self.line(MARGIN_X, self.y, PAGE_W - MARGIN_X, self.y)
        self.y -= 4

    def paragraph(self, text: str, size: float = 10, color: Color = BLACK, bold: bool = False,
                  leading: float = 1.42, indent: float = 0.0) -> None:
        for line in self.wrap(text, size, self.content_width - indent, bold):
            self.ensure(size * leading)
            self.y -= size * leading
            self.text(MARGIN_X + indent, self.y, line, size, bold, color)
        self.y -= 3

    def key_values(self, rows: Sequence[Tuple[str, str]], size: float = 10,
                   label_width: float = 250.0) -> None:
        row_height = size * 1.75
        for label, value in rows:
            value_lines = self.wrap(value, size, self.content_width - label_width, bold=True)
            needed = row_height + (len(value_lines) - 1) * size * 1.3
            self.ensure(needed)
            self.y -= row_height - 5
            self.text(MARGIN_X, self.y, label, size, color=GRAY)
            for i, line in enumerate(value_lines):
                self.text_right(PAGE_W - MARGIN_X, self.y - i * size * 1.3, line, size, bold=True)
            self.y -= 5 + (len(value_lines) - 1) * size * 1.3
            self.line(MARGIN_X, self.y, PAGE_W - MARGIN_X, self.y, 0.4)

    def table(self, headers: Sequence[str], rows: Sequence[Sequence[str]],
              widths: Sequence[float], aligns: Sequence[str], size: float = 8.0) -> None:
        """``widths`` als Anteile der Inhaltsbreite; ``aligns`` aus 'l' / 'r'."""
        total = float(sum(widths))
        cols = [w / total * self.content_width for w in widths]
        row_height = size * 1.9

        def draw_header() -> None:
            self.ensure(row_height * 2)
            self.y -= row_height
            self.rect(MARGIN_X, self.y - 3, self.content_width, row_height, (0.95, 0.95, 0.93))
            x = MARGIN_X
            for head, width, align in zip(headers, cols, aligns):
                if align == "r":
                    self.text_right(x + width - 4, self.y + 2, head, size, bold=True, color=GRAY)
                else:
                    self.text(x + 4, self.y + 2, head, size, bold=True, color=GRAY)
                x += width

        draw_header()
        for row in rows:
            if self.y - row_height < MARGIN_BOTTOM:
                self.new_page()
                draw_header()
            self.y -= row_height
            x = MARGIN_X
            for cell, width, align in zip(row, cols, aligns):
                cell = str(cell)
                if text_width(cell, size) > width - 8:
                    while len(cell) > 1 and text_width(cell + "...", size) > width - 8:
                        cell = cell[:-1]
                    cell += "..."
                if align == "r":
                    self.text_right(x + width - 4, self.y + 2, cell, size)
                else:
                    self.text(x + 4, self.y + 2, cell, size)
                x += width
            self.line(MARGIN_X, self.y - 3, PAGE_W - MARGIN_X, self.y - 3, 0.4)
        self.y -= 6

    # -- Ausgabe -------------------------------------------------------------------
    def build(self) -> bytes:
        total = len(self.pages)
        for index in range(total):
            label = f"Seite {index + 1} von {total}"
            self.text(PAGE_W - MARGIN_X - text_width(label, 8), 30, label, 8, color=MUTED, page=index)
            if self.footer_left:
                self.text(MARGIN_X, 30, self.footer_left, 8, color=MUTED, page=index)

        objects: List[bytes] = []

        def add(body: bytes) -> int:
            objects.append(body)
            return len(objects)

        catalog_id = add(b"")   # Platzhalter 1
        pages_id = add(b"")     # Platzhalter 2
        font_regular = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                           b"/Encoding /WinAnsiEncoding >>")
        font_bold = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
                        b"/Encoding /WinAnsiEncoding >>")
        page_ids = []
        for ops in self.pages:
            stream = zlib.compress(b"\n".join(ops))
            content_id = add(b"<< /Length " + str(len(stream)).encode() +
                             b" /Filter /FlateDecode >>\nstream\n" + stream + b"\nendstream")
            page_id = add(
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_W:.2f} {PAGE_H:.2f}] "
                f"/Resources << /Font << /F1 {font_regular} 0 R /F2 {font_bold} 0 R >> >> "
                f"/Contents {content_id} 0 R >>".encode())
            page_ids.append(page_id)
        kids = " ".join(f"{pid} 0 R" for pid in page_ids)
        objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()
        objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode()
        info_id = add(b"<< /Title (" + _escape(self.title) + b") /Author (" + _escape(self.author) +
                      b") /Producer (KI Crypto Trader) >>")

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for number, body in enumerate(objects, start=1):
            offsets.append(len(out))
            out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
        xref_at = len(out)
        out += f"xref\n0 {len(objects) + 1}\n".encode()
        out += b"0000000000 65535 f \n"
        for offset in offsets:
            out += f"{offset:010d} 00000 n \n".encode()
        out += (f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R /Info {info_id} 0 R >>\n"
                f"startxref\n{xref_at}\n%%EOF\n").encode()
        return bytes(out)
