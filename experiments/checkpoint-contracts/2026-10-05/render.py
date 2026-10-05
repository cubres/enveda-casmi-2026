"""Render actual checkpoint file sizes from the unchanged native receipt."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
RECEIPT_SHA = "9b61a02d3284e167bf4b2b9f216dde1cda077279042daed0f6130e3ac7181e21"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    raw = (HERE / "measured-data.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != RECEIPT_SHA:
        raise ValueError("Native measurement receipt changed")
    data = json.loads(raw)
    if data["status"] != "PASS_CHECKPOINT_MEASUREMENT_ONLY" or len(data["files"]) != 6:
        raise ValueError("Unexpected measurement scope")
    rows = data["files"]
    logical = [sum(math.prod(s) for s in r["state_tensor_shapes"].values()) * 4 for r in rows]
    if len(set(logical)) != 1 or any(r["state_tensor_dtypes"] != ["torch.float32"] for r in rows):
        raise ValueError("The FP32 logical-size annotation needs revision")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(10.5, 5.8), layout="constrained")
    labels = ["FP" + r["dataset_ref"].rsplit("-v", 1)[-1] + " / " + r["file"] for r in rows]
    sizes = [r["bytes"] / 1_000_000 for r in rows]
    bars = ax.barh(labels, sizes, color=["#247c84"] * 2 + ["#7066ab"] * 4, height=.65)
    ax.invert_yaxis()
    ax.bar_label(bars, labels=[f"{v:.3f} MB" for v in sizes], padding=7)
    ax.axvline(logical[0] / 1_000_000, color="#35424b", ls="--", lw=1.5, label="Listed FP32 model tensors: 144.081 MB")
    ax.set_xlim(0, 490)
    ax.set_xlabel("Observed whole-file bytes / 1,000,000")
    ax.set_title("Six checkpoints; identical listed model tensor shapes", loc="left", fontweight="bold", pad=18)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", alpha=.14)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.16), frameon=False, fontsize=9)
    fig.suptitle("CPU measurement • Kaggle V9 • no inference or score", x=.01, ha="left", fontsize=10, color="#52616b")
    fig.savefig(args.output_dir / "checkpoint-sizes.svg", metadata={"Date": None})
    fig.savefig(args.output_dir / "checkpoint-sizes.png", dpi=160)
    print(json.dumps({"files": 6, "model_logical_bytes": logical[0], "receipt_sha256": RECEIPT_SHA, "output_dir": str(args.output_dir)}))

if __name__ == "__main__":
    main()
