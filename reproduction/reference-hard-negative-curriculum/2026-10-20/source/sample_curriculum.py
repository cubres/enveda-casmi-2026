"""Read completed curriculum; no spectra/model. SPDX-License-Identifier: Apache-2.0"""
import argparse
import csv
import json
from pathlib import Path
from curriculum_core import require, sample_negative
from qualification import load_qualified_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True,
                        help="Portable completed tree: RESULT.json beside data/OUTPUT_MANIFEST.json")
    parser.add_argument("--anchor", type=int, required=True)
    parser.add_argument("--stage", type=int, choices=range(3), required=True)
    parser.add_argument("--epoch", type=int, required=True)
    args = parser.parse_args()
    data = load_qualified_run(args.run_root, Path(__file__).resolve().parent)
    with (data / "anchors.csv").open(newline="", encoding="utf-8") as stream:
        anchors = list(csv.DictReader(stream))
    require(0 <= args.anchor < len(anchors), "anchor outside manifest")
    require(anchors[args.anchor]["split"] == "train", "optimizer consumer is train-only")
    with (data / "negative_pairs.csv").open(newline="", encoding="utf-8") as stream:
        negatives = list(csv.DictReader(stream))
    value = sample_negative(negatives, args.anchor, args.stage, args.epoch)
    print(json.dumps({"anchor": anchors[args.anchor], "reference_negative": value,
                      "spectrum_or_model_used": False,
                      "requires_before_training": "Independently licensed positive spectrum, qualified exact connectivity join and matching selected FP target; preserve folds across all spectra of each connectivity. This example does not qualify that join."},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
