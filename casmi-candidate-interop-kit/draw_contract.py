"""Regenerate the original conceptual diagram into a new output directory."""
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def draw(directory):
    root = Path(directory); root.mkdir(parents=True, exist_ok=True)
    targets = [root / "retrieval-contract-v2.svg", root / "retrieval-contract-v2.png"]
    if any(p.exists() for p in targets):
        raise ValueError("choose a directory with no existing diagram files")
    fig, ax = plt.subplots(figsize=(13, 7), dpi=160)
    fig.patch.set_facecolor("#f4f1e9"); ax.set_facecolor("#f4f1e9")
    ax.set_xlim(0, 13); ax.set_ylim(0, 7); ax.axis("off")
    ax.text(.45, 6.65, "Before the model: make candidate retrieval trustworthy", fontsize=20, fontweight="bold", color="#143a3c")
    ax.text(.45, 6.17, "CASMI Candidate Interop Kit · conceptual contract diagram · invented fixtures only", fontsize=11, color="#53706e")
    boxes = [(.45, 3.55, 3.7, 1.65, "1  Establish the mass", "Neutral mass or precursor m/z?\nExplicit charge + signed adduct shift\nKeep ppm denominator visible"),
             (4.65, 3.55, 3.7, 1.65, "2  Select aligned rows", "Sorted float64 masses\nInclusive lower + upper endpoints\nSame slice for keys and bits"),
             (8.85, 3.55, 3.7, 1.65, "3  Confirm feature meaning", "Morgan parameters + generator\nMACCS 167 versus 166\nExplicit packed-bit order + padding")]
    for x,y,w,h,title,body in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.04,rounding_size=0.12", facecolor="#ffffff", edgecolor="#c9d8d1", linewidth=1.3))
        ax.text(x+.2,y+h-.20,title,fontsize=14,fontweight="bold",color="#143a3c",va="top")
        ax.text(x+.2,y+h-.65,body,fontsize=11.2,color="#385856",linespacing=1.6,va="top")
    for x in (4.2,8.4):
        ax.annotate("",xy=(x+.4,4.37),xytext=(x,4.37),arrowprops=dict(arrowstyle="->",color="#307d79",lw=2))
    ax.add_patch(FancyBboxPatch((.45,.85),12.1,2.08,boxstyle="round,pad=0.04,rounding_size=0.12",facecolor="#e1ece6",edgecolor="#b4cdc1",linewidth=1.3))
    ax.text(.7,2.51,"Then rank with a named formula — and check the tiny expected answers",fontsize=16,fontweight="bold",color="#143a3c")
    ax.text(.7,2.02,"Binary overlap / union   ≠   expected-overlap heuristic   ≠   calibrated likelihood",fontsize=12,color="#315653")
    ax.text(.7,1.52,"25 adverse tests  •  Boundary duplicates  •  Bit-order sentinels  •  MACCS last key  •  Trusted file hashes",fontsize=11,color="#315653")
    ax.text(.7,1.07,"No RDKit needed to use this kit. No chemical database, spectra, weights or competition score are bundled.",fontsize=10.5,color="#315653")
    ax.text(.45,.32,"A trusted manifest detects changed bytes; equal shapes alone cannot prove chemical row alignment.",fontsize=10.5,color="#53706e")
    fig.tight_layout(pad=.35)
    for target in targets:
        fig.savefig(target,facecolor=fig.get_facecolor(),metadata={"Creator":"Original prvsiyan / cubres CASMI companion diagram"})
    plt.close(fig)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python draw_contract.py NEW_DIAGRAM_OUTPUT_DIRECTORY")
    draw(sys.argv[1])
