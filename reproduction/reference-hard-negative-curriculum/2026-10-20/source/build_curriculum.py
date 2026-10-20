"""Pinned reference-target curriculum; no spectra/model. SPDX-License-Identifier: Apache-2.0"""
import argparse
import ast
import csv
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import statistics
import struct
import sys
import time
from collections import Counter, defaultdict
from curriculum_core import STAGES, choose_canary, exact_pair, partition, require, select_anchor

SOURCE = Path(__file__).resolve().parent
ROWS, WIDTH, BITS = 4096, 1300, 10395


def dump(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")


def rss_peak():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def file_pin(path):
    checksum = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            block = stream.read(1 << 20)
            if not block:
                break
            checksum.update(block)
            size += len(block)
    return {"bytes": size, "sha256": checksum.hexdigest()}


def bound_file(root, name, expected):
    path = root / name
    require(path.is_file() and not path.is_symlink(), "missing/symlink input " + name)
    require(file_pin(path) == expected, "input pin mismatch " + name)
    return path


def packed_numpy(path):
    """Strict numeric .npy reader: no NumPy, pickle or chemistry imports."""
    with path.open("rb") as stream:
        require(stream.read(6) == b"\x93NUMPY", "not npy")
        version = stream.read(2)
        require(version in (b"\x01\x00", b"\x02\x00"), "unsupported npy version")
        field = stream.read(2 if version[0] == 1 else 4)
        require(len(field) == (2 if version[0] == 1 else 4), "truncated npy header length")
        length = int.from_bytes(field, "little")
        require(0 < length < 65536, "npy header bound")
        header = ast.literal_eval(stream.read(length).decode("latin1").strip())
        require(header == {"descr": "|u1", "fortran_order": False, "shape": (ROWS, WIDTH)}, "npy schema")
        raw = stream.read(ROWS * WIDTH + 1)
    require(len(raw) == ROWS * WIDTH, "npy payload length")
    fingerprints, hashes = [], []
    for index in range(ROWS):
        row = raw[index * WIDTH:(index + 1) * WIDTH]
        require(row[-1] & 31 == 0, "nonzero fingerprint padding")
        fingerprints.append(int.from_bytes(row, "big"))
        hashes.append(hashlib.sha256(row).hexdigest())
    return fingerprints, hashes


def csv_write(path, fields, rows):
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-dir", required=True, type=Path, help="Immutable8f2fd963 public atlas root")
    parser.add_argument("--structure-dir", required=True, type=Path, help="Immutable9cb4a4a6 public structure root")
    parser.add_argument("--out", required=True, type=Path, help="Fresh retained output directory")
    args = parser.parse_args()
    started = time.monotonic()
    require(os.environ.get("CASMI_CURRICULUM_OWNED") == "1", "owning wrapper required")
    require(not args.out.exists() and args.out.parent.is_dir(), "fresh output required")
    args.out.mkdir()
    contract = json.loads((SOURCE / "INPUT_CONTRACT.json").read_bytes())
    for name, expected in contract["atlas_files"].items():
        bound_file(args.atlas_dir, name, expected)
    for name, expected in contract["structure_files"].items():
        bound_file(args.structure_dir, name, expected)
    with (args.atlas_dir / "data/query_rows.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    require(len(rows) == ROWS and [int(r["query_row"]) for r in rows] == list(range(ROWS)), "all4096 row order")
    for row in rows:
        require(row["source"] == "ChEBI" and row["source_id"].startswith("CHEBI:"), "ChEBI identity")
        require(re.fullmatch(r"[A-Z]{14}", row["inchikey14"]) is not None, "provided InChIKey first block")
        require(re.fullmatch(r"[0-9a-f]{64}", row["canonical_group"]) is not None, "canonical digest")
        require(math.isfinite(float(row["reference_exact_mass_da"])) and float(row["reference_exact_mass_da"]) > 0,
                "reference mass")
    with gzip.open(args.atlas_dir / "data/pairs.csv.gz", "rt", newline="", encoding="utf-8") as stream:
        pairs = list(csv.DictReader(stream))
    require(len(pairs) == 3800, "frozen atlas pair count")
    pair_ids, by_anchor = set(), defaultdict(list)
    for pair in pairs:
        q, c = int(pair["query_row"]), int(pair["candidate_row"])
        require(0 <= q < ROWS and 0 <= c < ROWS and q != c and (q, c) not in pair_ids, "pair identity")
        require(rows[q]["canonical_group"] != rows[c]["canonical_group"], "atlas canonical exclusion")
        require(pair["selected_ppm"] == rows[q]["selected_ppm"], "unchanged atlas fallback")
        qmass, cmass = float(rows[q]["reference_exact_mass_da"]), float(rows[c]["reference_exact_mass_da"])
        delta = qmass * int(pair["selected_ppm"]) * 1e-6
        require(qmass - delta <= cmass <= qmass + delta, "reference closed interval")
        pair_ids.add((q, c))
        by_anchor[q].append(pair)
    for index, row in enumerate(rows):
        require(int(row["selected_rows"]) == len(by_anchor[index]), "all query pair counts")
    fingerprints, fp_hashes = packed_numpy(args.structure_dir / "external_fp.npy")
    for index, row in enumerate(rows):
        require(fingerprints[index].bit_count() == int(row["selected_on_bits"]), "query target on-bit join")
    aliases, components, folds, split_evidence = partition(rows, fp_hashes, pairs)
    kept, excluded, timings, processed = [], [], [], set()
    canary_rows, selection = choose_canary(rows, pairs)
    masses = [float(row["reference_exact_mass_da"]) for row in rows]
    observed = {"collision_anchor_rows": [], "nonempty_noncollision_anchor_rows": [], "empty_anchor_rows": [],
                "identical_target_source_pairs": []}

    def process_chunk(indices, validate_canary=False):
        before = time.monotonic()
        units = len(indices)
        for query in indices:
            require(query not in processed, "anchor processed more than once")
            selected, rejected = select_anchor(query, by_anchor[query], rows, fingerprints, aliases, folds)
            if validate_canary:
                # Reconstruct this actual reference-mass neighborhood, rather
                # than treating a stored zero-count cell as empty proof.
                choices = []
                for ppm in (10, 30):
                    delta = masses[query] * ppm * 1e-6
                    choices = [c for c in range(ROWS) if rows[c]["canonical_group"] != rows[query]["canonical_group"] and
                               masses[query] - delta <= masses[c] <= masses[query] + delta]
                    if choices:
                        break
                require(set(choices) == {int(p["candidate_row"]) for p in by_anchor[query]}, "canary numeric window parity")
                collisions = [(query, int(p["candidate_row"])) for p in by_anchor[query]
                              if fingerprints[query] == fingerprints[int(p["candidate_row"])]]
                if collisions:
                    observed["collision_anchor_rows"].append(query)
                    observed["identical_target_source_pairs"].extend(collisions)
                elif choices:
                    observed["nonempty_noncollision_anchor_rows"].append(query)
                else:
                    observed["empty_anchor_rows"].append(query)
            kept.extend(selected)
            excluded.extend(rejected)
            units += len(by_anchor[query])
            processed.add(query)
        duration = time.monotonic() - before
        timings.append((duration, units))
        require(time.monotonic() - started < 95, "producer processing ceiling preserves output reserve")
        require(rss_peak() < 100 << 20, "child RSS reserve for wrapper")

    for offset in range(0, len(canary_rows), 8):
        process_chunk(canary_rows[offset:offset + 8], validate_canary=True)
    require(len(processed) == 64 and processed == set(canary_rows), "64 exactly-once anchors")
    require(observed["collision_anchor_rows"] and observed["nonempty_noncollision_anchor_rows"] and
            observed["empty_anchor_rows"], "canary actual-bit and numeric-window coverage")
    require(any(p["reason"] == "identical_fingerprint_target" for p in excluded), "canary exercises collision exclusion")
    require((285, 3018) in observed["identical_target_source_pairs"], "frozen first collision actual-bit proof")
    remaining_rows = [query for query in range(ROWS) if query not in processed]
    # All setup/input validation and split construction count in elapsed time.
    # Canary pairs are retained and NOT recomputed when continuation is admitted.
    rates = sorted(duration / units for duration, units in timings)
    conservative_rate = 1.5 * max(rates[math.ceil(.9 * len(rates)) - 1], statistics.median(rates))
    remaining_units = len(remaining_rows) + sum(len(by_anchor[q]) for q in remaining_rows)
    forecast = time.monotonic() - started + conservative_rate * remaining_units + 15.0
    canary = {"status": "PASS64_NUMERIC_MECHANICS_ONLY" if forecast < 105 else "HOLD_FORECAST",
              "anchor_rows": canary_rows, "anchors": 64, "selection": selection,
              "observed_actual_bits_and_numeric_windows": observed,
              "source_pairs_processed": sum(len(by_anchor[q]) for q in canary_rows),
              "kept_pairs": len(kept), "excluded_pairs": len(excluded),
              "chunk_seconds_and_work_units": timings, "elapsed_including_setup_seconds": time.monotonic() - started,
              "conservative_seconds_per_work_unit": conservative_rate,
              "forecast_including_15_second_output_reserve": forecast,
              "full_continues_without_reset_or_canary_repeat": True,
              "source_author_arithmetic_vs_executed_qualification": "THIS_RECEIPT_EXISTS_ONLY_AFTER_REAL_EXECUTION"}
    dump(args.out / "CANARY64.json", canary)
    require(forecast < 105, "64-anchor forecast rejected")
    for offset in range(0, len(remaining_rows), 8):
        process_chunk(remaining_rows[offset:offset + 8])
    require(processed == set(range(ROWS)), "all4096 anchors exactly once")
    require(len(kept) + len(excluded) == len(pairs), "every source pair exactly one disposition")
    identical = sum(p["reason"] == "identical_fingerprint_target" for p in excluded)
    require(identical == 96, "expected exact-target collision arithmetic")
    require(all(p["target_hamming_bits"] > 0 for p in kept), "no identical target negative")
    by_selected = defaultdict(list)
    for pair in kept:
        by_selected[pair["query_row"]].append(pair)
    anchor_output = []
    for index, row in enumerate(rows):
        pools = [sum(p["minimum_stage"] <= stage for p in by_selected[index]) for stage in range(3)]
        anchor_output.append({"query_row": index, "source_id": row["source_id"],
                              "original_source_row": row["original_source_row"], "inchikey14": row["inchikey14"],
                              "canonical_group": row["canonical_group"], "fingerprint_sha256": fp_hashes[index],
                              "identity_alias": aliases[index], "component_id": components[index], "split": folds[index],
                              "reference_exact_mass_da": row["reference_exact_mass_da"],
                              "source_pair_count": len(by_anchor[index]), "eligible_target_aliases": len(by_selected[index]),
                              "separated_pool": pools[0], "intermediate_pool": pools[1], "confusable_pool": pools[2],
                              "empty_control": not bool(by_selected[index])})
    csv_write(args.out / "anchors.csv", list(anchor_output[0]), anchor_output)
    pair_fields = ["query_row", "candidate_row", "split", "hardness_bin", "minimum_stage", "intersection_on_bits",
                   "union_on_bits", "query_on_bits", "candidate_on_bits", "jaccard", "binary_cosine",
                   "target_hamming_bits", "signed_reference_ppm", "selected_reference_ppm", "candidate_identity_alias"]
    csv_write(args.out / "negative_pairs.csv", pair_fields, kept)
    csv_write(args.out / "excluded_source_pairs.csv", ["query_row", "candidate_row", "reason"], excluded)
    split_evidence.update({"claim_scope": "Source-provided qualified InChIKey-first-block connectivity IDs, canonical groups, exact selected FP targets and complete atlas pair graph; no new chemistry or spectra split proof.",
                           "fold_pair_counts": dict(Counter(p["split"] for p in kept)),
                           "exclusion_reason_counts": dict(Counter(p["reason"] for p in excluded)),
                           "hardness_bin_counts": dict(Counter(p["hardness_bin"] for p in kept)),
                           "all4096_anchors_retained": True,
                           "empty_eligible_negative_controls": sum(not by_selected[q] for q in range(ROWS)),
                           "original_empty_atlas_controls": sum(not by_anchor[q] for q in range(ROWS)),
                           "provided_unique_connectivity_ids": len({r["inchikey14"] for r in rows})})
    require(all(split_evidence["fold_pair_counts"].get(fold, 0) > 0 for fold in ("train", "validation", "test")),
            "all three folds need usable pairs; do not change seed as recovery")
    dump(args.out / "SPLIT_EVIDENCE.json", split_evidence)
    completion = {"schema": "casmi-reference-curriculum-completion/2",
                  "status": "COMPLETE_REFERENCE_CURRICULUM_PENDING_OWNED_RESOURCE_QUALIFICATION",
                  "anchors": ROWS, "source_pairs": len(pairs), "training_candidate_pairs": len(kept),
                  "excluded_pairs": len(excluded), "identical_target_pairs_excluded": identical,
                  "seconds": time.monotonic() - started, "peak_RSS_bytes": rss_peak(),
                  "input_contract_sha256": file_pin(SOURCE / "INPUT_CONTRACT.json")["sha256"],
                  "reference_identity": {"atlas_commit": contract["atlas_commit"], "structure_commit": contract["structure_commit"],
                                         "selected_bits": BITS, "packed_bytes_per_row": WIDTH},
                  "all4096_anchors_processed_exactly_once": True,
                  "canary64_real_collision_noncollision_empty_coverage": True,
                  "canary64_passed_and_continued": True, "all_source_pairs_validated_against_packed_targets": True,
                  "no_spectrum_model_accuracy_or_rights_inference": True}
    dump(args.out / "CURRICULUM_COMPLETE.json", completion)
    dump(args.out / "OUTPUT_MANIFEST.json", {"files": {p.name: file_pin(p) for p in sorted(args.out.iterdir()) if p.is_file()},
                                            "deterministic_scientific_outputs": ["anchors.csv", "negative_pairs.csv", "excluded_source_pairs.csv", "SPLIT_EVIDENCE.json"],
                                            "resource_timing_receipts_are_run_specific": True})
    print(json.dumps(completion, sort_keys=True))


if __name__ == "__main__":
    main()
