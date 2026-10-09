"""Raster preview of our own simple SVG, using optional matplotlib only."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent
tree = ET.parse(ROOT / 'contract-diagram-v2.svg')
fig, ax = plt.subplots(figsize=(13.2, 7.8), dpi=100)
fig.subplots_adjust(0, 0, 1, 1)
ax.set_xlim(0, 1320)
ax.set_ylim(780, 0)
ax.axis('off')
group = tree.find('.//{http://www.w3.org/2000/svg}g')
elements = [e for e in tree.getroot() if e.tag.endswith('rect')] + list(group)
for item in elements:
    kind = item.tag.split('}')[-1]
    a = item.attrib
    if kind == 'rect':
        x, y, w, h = (float(a[k]) for k in ('x', 'y', 'width', 'height')) if 'x' in a else (0, 0, 1320, 780)
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={a.get('rx', '0')}",
                                   facecolor=a.get('fill', 'none'), edgecolor=a.get('stroke', 'none'), linewidth=1))
    elif kind == 'text':
        ax.text(float(a['x']), float(a['y']), item.text, fontsize=float(a.get('font-size', 18)) * 0.72,
                fontfamily='DejaVu Sans', color=a.get('fill', '#16324b'),
                fontweight='bold' if a.get('font-weight') == '700' else 'normal', va='baseline')
    elif kind == 'path':
        tokens = re.findall(r'[MHVL]|[0-9.]+', a['d'])
        points, i, x, y = [], 0, 0, 0
        while i < len(tokens):
            action = tokens[i]
            i += 1
            if action in ('M', 'L'):
                x, y = float(tokens[i]), float(tokens[i + 1])
                i += 2
            elif action == 'H':
                x = float(tokens[i]); i += 1
            elif action == 'V':
                y = float(tokens[i]); i += 1
            points.append((x, y))
        if len(points) >= 2:
            ax.plot([p[0] for p in points[:-1]], [p[1] for p in points[:-1]], color='#55708b', linewidth=2)
            ax.add_patch(FancyArrowPatch(points[-2], points[-1], arrowstyle='-|>', mutation_scale=14,
                                        color='#55708b', linewidth=2))
with (ROOT / 'contract-diagram-v2.png').open('xb') as f:
    fig.savefig(f, format='png', dpi=100, facecolor='#f4f7fb')
plt.close(fig)
print(ROOT / 'contract-diagram-v2.png')
