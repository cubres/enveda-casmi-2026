"""Build a reference exact-mass ambiguity atlas; root-owned execution only.

SPDX-License-Identifier: Apache-2.0
Only six SHA-bound public structure files are inputs. No model or spectra.
"""
import argparse
import csv
import gzip
import hashlib
import importlib.metadata
import io
import json
import math
from pathlib import Path
import re
import resource
import shutil
import sys
import time

BOOT = time.monotonic()
import numpy as np
from atlas_core import (BITS, BYTES, closed_window, exact_integer_pair,
                        packed_counts, query_policy, require, similarity_batches)

ROOT = Path(__file__).resolve().parent
MAX_SECONDS = 100.0
RSS_LIMIT = 448 << 20  # wrapper and its supervision retain the other 64 MiB
MAX_PAIRS = 1_000_000  # fail closed, never truncate a supposedly complete atlas
PAIR_FIELDS = ["query_row", "candidate_row", "signed_ppm", "selected_ppm",
               "intersection_on_bits", "union_on_bits", "query_on_bits",
               "candidate_on_bits", "jaccard", "binary_cosine"]
QUERY_FIELDS = ["query_row", "original_source_row", "source", "source_id", "inchikey14",
                "canonical_group", "reference_exact_mass_da", "selected_on_bits",
                "rows_10ppm", "groups_10ppm", "rows_30ppm", "groups_30ppm",
                "selected_ppm", "selected_rows", "selected_groups", "fallback_used"]


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def file_pin(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def rss_bytes():
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(raw if sys.platform == "darwin" else raw * 1024)


def budget():
    require(time.monotonic() - BOOT <= MAX_SECONDS, "producer 100-second budget exceeded")
    require(rss_bytes() <= RSS_LIMIT, "producer 448-MiB RSS budget exceeded")


def load_reference(directory, contract):
    # PyArrow is optional for synthetic core tests, required only here.
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    directory = directory.resolve(strict=True)
    before = {}
    for name, expected in contract["files"].items():
        path = directory / name
        require(path.is_file() and not path.is_symlink(), "missing input or symbolic-link input")
        before[name] = file_pin(path)
        require(before[name] == expected, "public input hash/size mismatch: " + name)
        budget()
    arrays = {name: np.load(directory / name, mmap_mode="r", allow_pickle=False)
              for name in contract["files"] if name.endswith(".npy")}
    fp, masses, order = (arrays[n] for n in ("external_fp.npy", "external_mass.npy", "mass_order.npy"))
    rows, bits = arrays["original_source_rows.npy"], arrays["fp_bits.npy"]
    require(fp.shape == (4096, BYTES) and fp.dtype == np.uint8, "fingerprint schema")
    require(not np.any(fp[:, -1] & np.uint8(0x1F)), "nonzero low padding bits")
    require(masses.shape == (4096,) and masses.dtype == np.float64, "mass schema")
    require(np.all(np.isfinite(masses)) and np.all((masses >= 80) & (masses <= 1400)), "reference mass range")
    require(order.shape == (4096,) and order.dtype == np.int64 and
            np.array_equal(order, np.argsort(masses, kind="stable")), "stable mass order")
    require(rows.shape == (4096,) and rows.dtype == np.int64 and
            len(np.unique(rows)) == 4096 and np.all(rows >= 0), "source-row schema")
    require(bits.shape == (BITS,) and bits.dtype == np.int64 and len(np.unique(bits)) == BITS and
            np.all((bits >= 0) & (bits < 10407)), "frozen selected-bit schema")
    columns = ["original_source_row", "source", "source_id", "inchikey14", "computed_raw_key",
               "chebi_star", "computed_mass", "canonical_group"]
    table = pq.read_table(directory / "external_chebi3_4096.parquet", columns=columns, use_threads=False)
    require(table.num_rows == 4096, "public Parquet row count")
    records = table.to_pylist()
    groups = np.asarray([r["canonical_group"] for r in records], dtype=object)
    require(len(set(groups)) == 4092 and all(isinstance(g, str) and re.fullmatch(r"[a-f0-9]{64}", g) for g in groups),
            "public canonical-group schema/count")
    keys = []
    for i, row in enumerate(records):
        require(row["source"] == "ChEBI" and row["chebi_star"] == "3", "ChEBI three-star source")
        require(row["original_source_row"] == int(rows[i]) and row["computed_mass"] == float(masses[i]), "source joins")
        require(row["computed_raw_key"] == row["inchikey14"] and
                isinstance(row["inchikey14"], str) and re.fullmatch(r"[A-Z]{14}", row["inchikey14"]), "raw key")
        require(row["source_id"] is not None and bool(str(row["source_id"])), "source identifier")
        keys.append(row["inchikey14"])
    require(len(set(keys)) == 4096, "unique reference raw keys")
    budget()
    return fp, masses, order, groups, records, packed_counts(fp), before


def mechanics_canary(fp, masses, order, groups, on_bits):
    started = time.monotonic()
    summaries = []
    selected_pair_rows = 0
    for q in range(64):
        summary, selected = query_policy(masses, order, groups, q)
        brute = {}
        for ppm in (10, 30):
            delta = float(masses[q]) * ppm * 1e-6
            brute[ppm] = order[(masses[order] >= masses[q] - delta) &
                               (masses[order] <= masses[q] + delta) & (groups[order] != groups[q])]
        expected = brute[10] if len(brute[10]) else brute[30]
        require(np.array_equal(selected, expected), "canary closed-window/fallback parity")
        require(summary["rows_10ppm"] == len(brute[10]) and summary["rows_30ppm"] == len(brute[30]),
                "canary candidate count parity")
        # One deterministic, label-free fingerprint pair per reference query,
        # even when the mass window is empty. This is numerical QA only.
        partner = np.asarray([(q + 1) % len(masses)], dtype=np.int64)
        batch = next(similarity_batches(fp, on_bits, q, partner))
        i, u, qa, cb = exact_integer_pair(fp[q], fp[partner[0]])
        require((int(batch[1][0]), int(batch[2][0]), int(on_bits[q]), int(batch[3][0])) == (i, u, qa, cb),
                "canary independent Python-integer popcount parity")
        expected_jac = i / u if u else math.nan
        expected_cos = i / math.sqrt(qa * cb) if qa * cb else math.nan
        for actual, expected in ((float(batch[4][0]), expected_jac), (float(batch[5][0]), expected_cos)):
            require((math.isnan(actual) and math.isnan(expected)) or math.isclose(actual, expected, rel_tol=1e-14, abs_tol=1e-15),
                    "canary independent Jaccard/cosine ratio parity")
        # Time every selected candidate batch and the actual CSV formatting,
        # not just a single pair. The sink is bounded to one query at a time.
        scratch = io.StringIO()
        writer = csv.writer(scratch, lineterminator="\n")
        for candidate_rows, inter, union, c_counts, jac, cos in similarity_batches(fp, on_bits, q, selected):
            for j, c in enumerate(candidate_rows):
                c = int(c)
                writer.writerow(pair_values(q, c, masses, summary["selected_ppm"], inter[j], union[j],
                                            on_bits[q], c_counts[j], jac[j], cos[j]))
            budget()
        selected_pair_rows += len(selected)
        scratch.close()
        summaries.append(summary)
        budget()
    elapsed = time.monotonic() - started
    forecast = (time.monotonic() - BOOT) + elapsed * 64 * 1.5 + 8.0
    require(forecast <= 85.0, "canary full-run forecast exceeds 85-second admission")
    return summaries, {"status": "PASS_MECHANICS_ONLY", "blind_reference_query_rows": 64,
                       "query_selection": "first 64 fixed public shard rows; no labels or score-based selection",
                       "independent_integer_fingerprint_pairs": 64, "seconds": elapsed,
                       "selected_candidate_pairs_computed_and_CSV_formatted": selected_pair_rows,
                       "projected_total_seconds_with_reserve": forecast,
                       "forecast_scope": "64 fixed reference queries extrapolated with 1.5 factor and 8-second reserve; remainder density/compression cost may differ, so hard full-run caps remain binding",
                       "forecast_limit_seconds": 85.0, "peak_RSS_bytes": rss_bytes(),
                       "accuracy_or_scoring_evidence": False}


def ratio_text(value):
    return "" if math.isnan(float(value)) else format(float(value), ".17g")


def pair_values(q, c, masses, selected_ppm, intersection, union, q_count, c_count, jac, cos):
    signed_ppm = (float(masses[c]) - float(masses[q])) / float(masses[q]) * 1e6
    return [q, c, format(signed_ppm, ".17g"), selected_ppm, int(intersection), int(union),
            int(q_count), int(c_count), ratio_text(jac), ratio_text(cos)]


def build(directory, output):
    contract = json.loads((ROOT / "REFERENCE_INPUTS.json").read_bytes())
    fp, masses, order, groups, records, on_bits, before = load_reference(directory, contract)
    canary_summaries, canary = mechanics_canary(fp, masses, order, groups, on_bits)
    dump(output / "CANARY64_MECHANICS.json", canary)
    # Full enumeration starts only after the actual 64-query canary passed.
    query_count, pair_count, ten_queries, fallback_queries, empty_queries = 0, 0, 0, 0, 0
    ambiguous_queries, max_rows, undefined_jaccard, undefined_cosine = 0, 0, 0, 0
    full_first64 = []
    with (output / "query_rows.csv").open("w", newline="", encoding="utf-8") as query_stream, \
         (output / "pairs.csv.gz").open("wb") as raw:
        query_writer = csv.writer(query_stream, lineterminator="\n")
        query_writer.writerow(QUERY_FIELDS)
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=1, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text:
                pair_writer = csv.writer(text, lineterminator="\n")
                pair_writer.writerow(PAIR_FIELDS)
                for q in range(4096):
                    info, candidates = query_policy(masses, order, groups, q)
                    require(pair_count + len(candidates) <= MAX_PAIRS, "full atlas exceeds 1,000,000-pair resource admission; no truncation")
                    if q < 64:
                        full_first64.append(info)
                    row = records[q]
                    query_writer.writerow([q, row["original_source_row"], row["source"], row["source_id"],
                                           row["inchikey14"], row["canonical_group"], format(float(masses[q]), ".17g"),
                                           int(on_bits[q])] + [info[k] for k in QUERY_FIELDS[8:]])
                    for candidates_batch, intersection, union, c_count, jac, cos in similarity_batches(fp, on_bits, q, candidates):
                        for j, c in enumerate(candidates_batch):
                            c = int(c)
                            require(groups[q] != groups[c], "same-group pair escaped filtering")
                            pair_writer.writerow(pair_values(q, c, masses, info["selected_ppm"], intersection[j], union[j],
                                                           on_bits[q], c_count[j], jac[j], cos[j]))
                            undefined_jaccard += int(math.isnan(float(jac[j])))
                            undefined_cosine += int(math.isnan(float(cos[j])))
                        budget()
                    query_count += 1
                    pair_count += len(candidates)
                    ten_queries += int(info["selected_ppm"] == 10)
                    fallback_queries += int(info["fallback_used"])
                    empty_queries += int(info["selected_rows"] == 0)
                    ambiguous_queries += int(info["selected_groups"] >= 2)
                    max_rows = max(max_rows, info["selected_rows"])
                    budget()
    require(query_count == 4096 and full_first64 == canary_summaries, "all-row retention or canary/full parity")
    after = {name: file_pin(directory / name) for name in contract["files"]}
    require(after == before, "public input files changed during production")
    for name in ("REFERENCE_INPUTS.json", "DATA-LICENSE.md", "SOURCE_COMPONENT_LICENSE.md", "SOURCE_ATTRIBUTION.md",
                 "LICENSE-SOURCE", "demo_atlas.py"):
        shutil.copyfile(ROOT / name, output / name)
    result = {"schema": "reference-exact-mass-ambiguity-atlas/1", "status": "COMPLETE_REFERENCE_ATLAS_ONLY",
              "rows": query_count, "canonical_groups": 4092, "directional_pair_rows": pair_count,
              "queries_with_10ppm_confusers": ten_queries, "queries_using_30ppm_fallback": fallback_queries,
              "queries_with_no_different_group_confuser_at_30ppm": empty_queries,
              "queries_with_at_least_two_selected_confuser_groups": ambiguous_queries,
              "maximum_selected_candidate_rows": max_rows,
              "undefined_jaccard_rows": undefined_jaccard, "undefined_binary_cosine_rows": undefined_cosine,
              "fallback_policy": "all different-group rows in closed 10ppm window; only if none, all in closed 30ppm window",
              "ppm_denominator": "query reference exact mass; directed and not necessarily symmetric",
              "mass_scope": "Molecular reference exact masses, not observed MS2 precursor measurements",
              "fingerprint_scope": "10395 selected MSB-first bits; five low padding bits zero; binary-set similarity",
              "undefined_similarity_policy": "empty union or zero cosine norm is an empty CSV field, not a fabricated zero/one",
              "all_input_hashes_unchanged": True, "input_files": before,
              "seconds": time.monotonic() - BOOT, "peak_RSS_bytes": rss_bytes(),
              "resource_limits": {"producer_seconds": 100, "wrapper_seconds": 120, "producer_RSS_bytes": RSS_LIMIT,
                                  "whole_RSS_bytes": 512 << 20, "CPU_thread_limit": 2, "pair_row_cap_fail_closed": MAX_PAIRS},
              "numpy": np.__version__, "pyarrow": importlib.metadata.version("pyarrow"), "python": sys.version,
              "no_spectra_models_labels_or_competition_targets": True,
              "accuracy_score_recall_or_validation_claim": None, "chemistry_recomputed": False}
    budget()
    card = ("# Reference exact-mass ambiguity atlas\n\n"
            f"All {query_count:,} public ChEBI reference rows are retained, with 4,092 canonical groups and "
            f"{pair_count:,} directed different-group confuser pairs. "
            f"There are {ten_queries:,} queries using the 10 ppm window, {fallback_queries:,} using the "
            f"30 ppm fallback and {empty_queries:,} with no different-group peer at 30 ppm.\n\n"
            "These are molecular reference exact masses, not observed MS2 precursor measurements. "
            "For reference q, use the closed window mass[q] +/- mass[q]*ppm*1e-6; exclude all equal public "
            "canonical groups before choosing all 10 ppm rows or, only if none, all 30 ppm rows. "
            "The q-mass denominator and fallback make pairs directional.\n\n"
            "`query_rows.csv` preserves every reference row and 10/30 ppm row/group counts. "
            "`pairs.csv.gz` contains all selected directed row pairs, exact intersection/union and on-bit "
            "counts, Jaccard and binary cosine on 10,395 MSB-first bits. Undefined ratios are blank. "
            "Display limits do not truncate stored data.\n\n"
            "```bash\npython demo_atlas.py --atlas-dir . --query-row 0 --limit 5\n"
            "python demo_atlas.py --atlas-dir . --mass 400 --ppm 10 --limit 5\n```\n\n"
            "The numeric-mass example is a user-supplied illustration; without a query structure it "
            "cannot exclude a canonical group and performs no fingerprint ranking. "
            "See `REFERENCE_INPUTS.json` for the immutable source and file hashes, `ATLAS_COMPLETE.json` "
            "for measured counts/runtime, and `OUTPUT_MANIFEST.json` for output hashes.\n\n"
            "Preserve `DATA-LICENSE.md`, `SOURCE_COMPONENT_LICENSE.md` and `SOURCE_ATTRIBUTION.md`: "
            "ChEBI CC BY 4.0 and separate frozen-mask component terms remain. "
            "This reference atlas establishes no validation recall, hidden-answer coverage, model quality "
            "or official score. Release admission also requires a successful outer owned wrapper and "
            "independent completed-output review.\n")
    (output / "README.md").write_text(card)
    dump(output / "ATLAS_COMPLETE.json", result)
    manifest = {p.name: file_pin(p) for p in sorted(output.iterdir()) if p.is_file()}
    dump(output / "OUTPUT_MANIFEST.json", {"files": manifest, "completion": result["status"]})
    budget()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=False, exist_ok=False)
    try:
        result = build(args.source_dir, args.out)
    except BaseException as exc:
        dump(args.out / "FAILED_NOT_PROMOTABLE.json", {"status": "FAILED_NOT_PROMOTABLE", "type": type(exc).__name__,
                                                     "reason": str(exc), "seconds": time.monotonic() - BOOT,
                                                     "peak_RSS_bytes": rss_bytes(), "never_retry_consumed_attempt": True})
        raise
    print(json.dumps({"status": result["status"], "rows": result["rows"], "pairs": result["directional_pair_rows"]}))


if __name__ == "__main__":
    main()
