"""Inspect a completed reference atlas, or enumerate a user-supplied neutral mass.

SPDX-License-Identifier: Apache-2.0
Standard library only; no models, source-bank arrays or chemistry.
"""
import argparse
import csv
import gzip
import json
import math
from pathlib import Path


def result(directory, query_row=None, mass=None, ppm=10.0, limit=10):
    completion = json.loads((directory / "ATLAS_COMPLETE.json").read_bytes())
    if completion["status"] != "COMPLETE_REFERENCE_ATLAS_ONLY":
        raise ValueError("completed reference atlas required")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("positive display limit required")
    with (directory / "query_rows.csv").open(newline="", encoding="utf-8") as stream:
        references = list(csv.DictReader(stream))
    if len(references) != 4096:
        raise ValueError("all 4096 reference rows required")
    if query_row is not None:
        if isinstance(query_row, bool) or not isinstance(query_row, int) or not 0 <= query_row < 4096:
            raise ValueError("reference row must be in 0..4095")
        query = references[query_row]
        shown, total = [], 0
        with gzip.open(directory / "pairs.csv.gz", "rt", newline="", encoding="utf-8") as stream:
            for pair in csv.DictReader(stream):
                index = int(pair["query_row"])
                if index == query_row:
                    total += 1
                    if len(shown) < limit:
                        shown.append(pair)
                elif index > query_row:
                    break
        if total != int(query["selected_rows"]):
            raise ValueError("pair/query count mismatch")
        return {"query_origin": "public reference structure", "query": query,
                "total_directional_confusers": total, "displayed_pairs": shown,
                "display_limit_only": limit, "scope": "reference ambiguity, not MS2 retrieval or validation"}
    value, tolerance = float(mass), float(ppm)
    if not math.isfinite(value) or value <= 0 or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("positive finite user mass and ppm required")
    delta = value * tolerance * 1e-6
    matches = [r for r in references if value - delta <= float(r["reference_exact_mass_da"]) <= value + delta]
    matches.sort(key=lambda r: (float(r["reference_exact_mass_da"]), int(r["query_row"])))
    return {"query_origin": "user-provided numeric neutral mass; not an observed competition target",
            "neutral_mass_da": value, "ppm_denominator": "user-provided numeric mass", "ppm": tolerance,
            "closed_window_da": [value - delta, value + delta], "matching_reference_rows": len(matches),
            "displayed_rows": matches[:limit], "same_group_exclusion": "not available for an unidentified numeric mass",
            "scope": "reference enumeration only; no fingerprint query, MS2, recall, model or score"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-dir", required=True, type=Path)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--query-row", type=int)
    selection.add_argument("--mass", type=float)
    parser.add_argument("--ppm", type=float, default=10.0)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(result(args.atlas_dir, args.query_row, args.mass, args.ppm, args.limit), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
