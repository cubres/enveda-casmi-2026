"""Original explanatory diagrams. No measured quality or leaderboard claims.
Copyright 2026 cubres. SPDX-License-Identifier: MIT.
"""
from pathlib import Path
import os
OUT = Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR'] = str(OUT / 'matplotlib_config')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

INK, BLUE, GOLD = '#1a2942', '#245a8d', '#a76613'


def box(ax, x, y, w, h, heading, body, color=BLUE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.012,rounding_size=0.018',
                               facecolor='#f6f9fc', edgecolor=color, linewidth=1.6))
    ax.text(x + w / 2, y + h - 0.035, heading, ha='center', va='top',
            fontsize=11.5, fontweight='bold', color=color)
    ax.text(x + w / 2, y + h - 0.078, body, ha='center', va='top',
            fontsize=10.5, color=INK, linespacing=1.35)


def arrow(ax, a, b, color=BLUE):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=16,
                                linewidth=1.8, color=color, connectionstyle='arc3'))


def save(fig, name):
    for suffix in ('png', 'svg'):
        p = OUT / (name + '-v3.' + suffix)
        if p.exists():
            raise FileExistsError('Preserve previously generated diagram: ' + str(p))
        fig.savefig(p, dpi=160, facecolor='white', bbox_inches='tight', pad_inches=0.18)
    plt.close(fig)


def main():
    fig, ax = plt.subplots(figsize=(11, 5.8))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis('off')
    ax.text(.04, .96, 'One candidate row, three aligned views', fontsize=19,
            fontweight='bold', color=INK, va='top')
    ax.text(.04, .83, 'ChEBI + LIPID MAPS v1 · a data contract, not a quality result',
            fontsize=12, color='#53647b')
    box(ax, .04, .52, .23, .24, 'Neutral mass', 'adduct / charge conversion\nthen a ppm interval')
    box(ax, .36, .52, .25, .24, 'Mass-window rows', 'bio_mass.npy\nascending float64\n[lo, hi)')
    box(ax, .71, .59, .25, .20, 'Packed bits', 'bio_fp.npy\nuse exactly [lo:hi]')
    box(ax, .71, .29, .25, .20, 'Structure metadata', 'bio_meta.pkl\nsame row indices\ntrusted pickle only', color=GOLD)
    arrow(ax, (.285, .64), (.345, .64))
    arrow(ax, (.62, .68), (.695, .68))
    arrow(ax, (.62, .57), (.695, .41), color=GOLD)
    ax.text(.04, .23, 'Merging banks? Sort every companion with the same permutation.',
            fontsize=13, fontweight='bold', color=INK)
    ax.text(.04, .14, 'A matching shape cannot certify descriptor order, chemical identity or validation quality.',
            fontsize=11, color='#53647b')
    save(fig, 'bio-row-alignment')

    fig, ax = plt.subplots(figsize=(11, 5.8))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis('off')
    ax.text(.04, .96, 'Popularity lookup has two distinct paths', fontsize=19,
            fontweight='bold', color=INK, va='top')
    ax.text(.04, .83, 'PubChem counts v1 · raw integers, not float16 log values',
            fontsize=12, color='#53647b')
    box(ax, .04, .53, .23, .25, 'Arbitrary candidates', 'InChIKey first blocks\n14 uppercase letters')
    box(ax, .37, .53, .23, .25, 'Bounded lookup', 'sorted S14 table\nin-bounds equality check\nkeep matched flag')
    box(ax, .73, .53, .23, .25, 'Distinct counts', 'SID and PMID\nunknown block → 0\noptional log1p sum')
    arrow(ax, (.285, .66), (.355, .66))
    arrow(ax, (.615, .66), (.715, .66))
    box(ax, .04, .13, .38, .22, 'Companion mass-index rows', 'off.npy / len.npy row order\nbefore sorting masses', color=GOLD)
    box(ax, .57, .13, .39, .22, 'Aligned store count arrays', 'apply identical row indices\nor sorting permutation\nap2pop_store_sid / pmid', color=GOLD)
    arrow(ax, (.435, .24), (.55, .24), color=GOLD)
    ax.text(.04, .42, 'Documentation counts inform a prior; they do not establish the correct structure.',
            fontsize=12, color='#53647b')
    save(fig, 'pubchem-lookup-alignment')


if __name__ == '__main__':
    main()
