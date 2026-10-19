"""Render the publication diagram from shared vector primitives.

SPDX-License-Identifier: Apache-2.0. Creates new SVG/PNG assets only.
Pillow is needed for PNG output; the data/demo do not depend on this renderer.
"""
import argparse
from html import escape
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1600, 820
BG, NAVY, TEAL, MUTED = "#f3f7f7", "#142c3b", "#087f83", "#536b76"
primitives = []


def rect(x, y, width, height, color, radius=0, outline=None):
    primitives.append(("rect", (x, y, width, height, color, radius, outline)))


def text(x, y, value, size, color=NAVY, bold=False):
    primitives.append(("text", (x, y, value, size, color, bold)))


def line(x1, y1, x2, y2, color=TEAL, width=3):
    primitives.append(("line", (x1, y1, x2, y2, color, width)))


def diagram():
    rect(0, 0, WIDTH, HEIGHT, BG)
    rect(68, 52, 176, 32, "#dcefee", 16)
    text(83, 59, "CASMI / OPEN DATA", 15, TEAL, True)
    text(68, 108, "4,096 structures. One exact fingerprint contract.", 49, bold=True)
    text(70, 175, "A compact ChEBI three-star bank with source identifiers, verified joins and a runnable retrieval demo.", 22, MUTED)

    cards = [(68, "01", "Public source"), (575, "02", "Exact fingerprint bits"), (1082, "03", "Use the aligned rows")]
    for x, number, title in cards:
        rect(x + 3, 245, 450, 357, "#e3ecec", 22)
        rect(x, 239, 450, 357, "#ffffff", 22, "#d6e3e4")
        text(x + 28, 267, number, 17, TEAL, True)
        text(x + 28, 301, title, 28, bold=True)
    for x in (535, 1042):
        line(x, 414, x + 25, 414, width=4)
        line(x + 16, 405, x + 25, 414, width=4)
        line(x + 16, 423, x + 25, 414, width=4)

    text(96, 356, "4,096", 59, TEAL, True)
    text(96, 427, "raw-key-new records", 24, bold=True)
    text(96, 477, "ChEBI release 255 / public mirror V1", 20, MUTED)
    text(96, 514, "64 mass bins; deterministic selection", 20, MUTED)
    text(96, 551, "Original attribution and IDs retained", 20, MUTED)

    text(603, 356, "10,395", 59, TEAL, True)
    text(603, 427, "selected bits / 1,300 bytes per row", 22, bold=True)
    text(603, 477, "Morgan r2 + r3 / path6 / MACCS", 20, MUTED)
    text(603, 514, "Frozen mask from 10,407 raw bits", 20, MUTED)
    text(603, 551, "MSB first; five zero padding bits", 20, MUTED)

    text(1110, 367, "80–1,400 Da", 43, TEAL, True)
    text(1110, 427, "neutral-mass candidate windows", 22, bold=True)
    text(1110, 477, "Stable mass-order index", 20, MUTED)
    text(1110, 514, "Packed FP / SMILES / source-row joins", 20, MUTED)
    text(1110, 551, "Read-only NumPy + PyArrow demo", 20, MUTED)

    rect(68, 637, 1464, 103, "#e0efec", 19)
    metrics = [(96, "PRODUCER OUTPUTS", "45 file hashes checked"),
               (456, "NUMERIC GATE", "64-row canary passed"),
               (816, "WITHIN THIS SHARD", "4,092 canonical groups"),
               (1176, "RECORDED CPU BUILD", "145.85 seconds")]
    for x, label, value in metrics:
        text(x, 659, label, 15, TEAL, True)
        text(x, 691, value, 23, bold=True)
    text(70, 771, "Canonical novelty versus the old bank, hidden-answer coverage and score improvement remain unmeasured.", 20, MUTED)


def font(size, bold):
    choices = (["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "DejaVuSans-Bold.ttf"] if bold
               else ["/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf"])
    for choice in choices:
        try:
            return ImageFont.truetype(choice, size)
        except OSError:
            continue
    raise RuntimeError("A supported TrueType font is required")


def render(output):
    output.mkdir(parents=True, exist_ok=True)
    diagram()
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(canvas)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
           '<title id="title">ChEBI 4,096-row fingerprint shard pipeline</title>',
           '<desc id="desc">Public ChEBI source rows become exact packed full fingerprints with verified retrieval joins. No score or whole-bank metric novelty is claimed.</desc>']
    for kind, values in primitives:
        if kind == "rect":
            x, y, w, h, color, radius, outline = values
            draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=color, outline=outline, width=1)
            stroke = f' stroke="{outline}"' if outline else ""
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{color}"{stroke}/>')
        elif kind == "line":
            x1, y1, x2, y2, color, width = values
            draw.line((x1, y1, x2, y2), fill=color, width=width)
            svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')
        else:
            x, y, value, size, color, bold = values
            draw.text((x, y), value, font=font(size, bold), fill=color, anchor="lt")
            weight = "700" if bold else "400"
            svg.append(f'<text x="{x}" y="{y + size * 0.88:g}" font-family="Arial,DejaVu Sans,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(value)}</text>')
    svg.append("</svg>")
    with (output / "pipeline.svg").open("x", encoding="utf-8") as handle:
        handle.write("\n".join(svg) + "\n")
    with (output / "pipeline.png").open("xb") as handle:
        canvas.save(handle, format="PNG", optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    render(parser.parse_args().output_dir)
