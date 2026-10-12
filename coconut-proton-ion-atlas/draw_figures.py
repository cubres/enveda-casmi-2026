"""Original MIT diagram and measured source-mass chart, rendered with Pillow.

Draws new images only; no existing image is edited. The chart reads the
generator's aggregate public mass_distribution.csv, never competition queries.
"""
from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BG, INK, MUTED = "#fbf6ed", "#342d25", "#71624f"


def font(size: int, serif: bool = False):
    choices = (("/System/Library/Fonts/Supplemental/Georgia.ttf", "DejaVuSerif.ttf")
               if serif else ("/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf"))
    for name in choices:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def save_new(image, path: Path):
    with path.open("xb") as f:
        image.save(f, format="PNG", optimize=True)


def diagram(output: Path):
    image = Image.new("RGB", (1400, 630), BG)
    d = ImageDraw.Draw(image)
    d.text((62, 37), "One row. Several ion hypotheses.", fill=INK, font=font(38, True))
    d.text((65, 88), "COCONUT ion mass atlas · theoretical masses, explicit conventions", fill=MUTED, font=font(20))
    cards = [
        (62, 418, "#f1e7d4", "#d0b68d", "#9d6339", "PIN THE SOURCE", "436,389 positions",
         ["Neutral mass M in daltons", "Same version · same SHA-256", "i means source row position", "No invented molecular keys"]),
        (507, 862, "#e6ede5", "#a6b9a3", "#557550", "NAME THE ION", "Charge & proton count",
         ["m/z = (n × M + h × p) / |z|", "±1, ±2, ±3 proton monomers", "Positive / negative homodimers", "Eight sorted channels · same i"]),
        (948, 1337, "#ede5ec", "#bba6b7", "#8b6080", "QUERY THE WINDOW", "Both endpoints included",
         ["Observed m/z ± instrument ppm", "left lower · right upper edge", "Original positions [lo:hi]", "Duplicates kept · no ranking"]),
    ]
    for left, right, fill, outline, accent, kicker, title, lines in cards:
        d.rounded_rectangle((left, 164, right, 444), radius=18, fill=fill, outline=outline, width=2)
        d.text((left + 25, 185), kicker, fill=accent, font=font(17))
        d.text((left + 25, 229), title, fill=INK, font=font(27, True))
        for y, text in zip((278, 314, 367, 403), lines):
            d.text((left + 25, y), text, fill=INK if y < 400 else MUTED, font=font(17))
        d.line((left + 25, 347, right - 25, 347), fill=outline, width=2)
    for left, right in ((432, 495), (875, 937)):
        d.line((left, 298, right, 298), fill="#a86836", width=3)
        d.line((right - 13, 290, right, 298, right - 13, 306), fill="#a86836", width=3)
    d.text((65, 482), "Precise mass matching still leaves ambiguity.", fill=INK, font=font(25, True))
    d.text((65, 523), "Mass bins describe this pool; they do not measure coverage of a query set.", fill=MUTED, font=font(20))
    d.text((65, 579), "Original diagram: prvsiyan · source: COCONUT / prvsiyan · data CC BY-NC-SA 4.0 · code MIT", fill=MUTED, font=font(17))
    save_new(image, output / "ion-atlas.png")


def density(output: Path):
    with (output / "mass_distribution.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 24:
        raise ValueError("expected the full 24-bin generated mass distribution")
    bins = [int(row["lower_da_inclusive"]) for row in rows]
    upper = [int(row["upper_da_exclusive"]) for row in rows]
    counts = [int(row["source_rows"]) for row in rows]
    unique = [int(row["distinct_exact_float64_mass_values"]) for row in rows]
    if (bins != list(range(100, 1300, 50)) or upper != list(range(150, 1350, 50))
            or sum(counts) != 436389 or sum(unique) != 111106
            or any(c < u or u < 0 for c, u in zip(counts, unique))):
        raise ValueError("generated source-bin count contract changed")
    image = Image.new("RGB", (1400, 850), BG)
    d = ImageDraw.Draw(image)
    d.text((62, 38), "How crowded is the source mass index?", fill=INK, font=font(38, True))
    d.text((65, 92), "Measured from the exact 436,389-row public COCONUT V2 mass file", fill=MUTED, font=font(21))
    left, right = 135, 1330
    width = (right - left) / len(bins)
    panels = ((170, 390, counts, "Source rows per 50-Da bin", "#b77942"),
              (485, 705, unique, "Distinct exact float64 mass values per bin", "#64825f"))
    for top, bottom, values, title, color in panels:
        d.text((left, top - 37), title, fill=INK, font=font(22))
        max_value = max(values)
        scale = max(1, max_value) * 1.1
        for fraction in (0.0, 0.5, 1.0):
            y = bottom - fraction * (bottom - top)
            d.line((left, y, right, y), fill="#dfd5c6", width=1)
            tick = int(scale * fraction)
            label = f"{tick:,}"
            d.text((left - 18, y), label, anchor="rm", fill=MUTED, font=font(17))
        for i, value in enumerate(values):
            x0, x1 = left + i * width + 3, left + (i + 1) * width - 3
            y = bottom - value / scale * (bottom - top)
            d.rectangle((x0, y, x1, bottom), fill=color)
        d.line((left, bottom, right, bottom), fill=MUTED, width=2)
        for mass in (100, 300, 500, 700, 900, 1100, 1300):
            x = left + ((mass - 100) / 1200) * (right - left)
            d.text((x, bottom + 18), str(mass), anchor="mt", fill=MUTED, font=font(18))
    d.text((735, 755), "Source neutral mass (Da) · half-open 50-Da bins", anchor="mm", fill=INK, font=font(20))
    d.text((65, 798), "Numerical mass multiplicity is not molecular diversity, isomer count or competition-query coverage.", fill=MUTED, font=font(18))
    save_new(image, output / "mass-density.png")


def render_figures(output: Path):
    diagram(output)
    density(output)
