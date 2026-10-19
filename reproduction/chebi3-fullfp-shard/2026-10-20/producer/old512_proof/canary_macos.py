"""Mac-only old512/new512 integrity and timing; no full continuation or model.

New uploader source, Apache-2.0. Frozen Linux implementation remains unchanged.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import json
import math
import multiprocessing
import os
from pathlib import Path
import pickle
import sys
import time
import traceback
import build_external_fp_shard as baseline

INNER_SECONDS = 240.0


def jobs_only_512(executor, jobs, consume, started):
    baseline.require(len(jobs) == 512 and len({i for i, _ in jobs}) == 512,
                     "EXACTLY_512_DISTINCT_CANARY_ROWS_REQUIRED")
    pending = {}; iterator = iter(baseline.chunks(jobs)); exhausted = False
    completed = 0; timings = []
    while pending or not exhausted:
        baseline.require(time.monotonic() - started < INNER_SECONDS, "MAC_CANARY_DEADLINE")
        while len(pending) < 4 and not exhausted:
            try:
                group = next(iterator)
            except StopIteration:
                exhausted = True; break
            pending[executor.submit(baseline.process_chunk, group)] = len(group)
        done, _ = concurrent.futures.wait(pending, timeout=0.1,
                         return_when=concurrent.futures.FIRST_COMPLETED)
        for future in done:
            count = pending.pop(future); rows, seconds = future.result()
            baseline.require(len(rows) == count, "CANARY_CHUNK_COUNT")
            for row in rows:
                consume(row)
            completed += count; timings.append(seconds)
    baseline.require(completed == 512, "CANARY_COMPLETION_COUNT")
    return timings


def verify_public_inputs(old_root, external_root):
    own_names = {"pool_fp.npy", "pool_mass.npy", "pool_meta.pkl", "fp_bits.npy"}
    result = {}
    for name, (size, expected) in baseline.EXPECTED_INPUTS.items():
        path = (old_root if name in own_names else external_root) / name
        baseline.require(path.is_file() and path.stat().st_size == size, "INPUT_SIZE:" + name)
        observed = baseline.sha256(path)
        baseline.require(observed == expected, "INPUT_SHA:" + name)
        result[name] = {"bytes": size, "sha256": observed}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-bank-root", required=True, type=Path)
    parser.add_argument("--external-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    baseline.require(sys.platform == "darwin", "MAC_ONLY_CANARY")
    baseline.require(os.environ.get("CASMI_MAC_CANARY_OWNED_WRAPPER") == "v1", "OWNED_WRAPPER_REQUIRED")
    old_root, external_root, output = (p.resolve() for p in (args.old_bank_root, args.external_root, args.output_root))
    baseline.require(all(root != output and root not in output.parents and output not in root.parents
                         for root in (old_root, external_root)), "SEPARATE_INPUT_OUTPUT_ROOTS")
    baseline.require(output.is_dir() and not list(output.iterdir()), "EXCLUSIVE_EMPTY_CANARY_OUTPUT")
    started = time.monotonic()
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    import rdkit
    pa.set_cpu_count(1); pa.set_io_thread_count(1)
    baseline.require(rdkit.__version__ == baseline.EXPECTED_RDKIT, "RDKIT_PIN")
    pins = verify_public_inputs(old_root, external_root)  # Before all input deserialization.
    bits = np.load(old_root / "fp_bits.npy", allow_pickle=False)
    baseline.require(bits.dtype == np.int64 and bits.shape == (10395,) and
                     np.array_equal(bits, np.unique(bits)) and int(bits[0]) >= 0 and int(bits[-1]) < 10407,
                     "FROZEN_MASK_SCHEMA")
    old_fp = np.load(old_root / "pool_fp.npy", mmap_mode="r", allow_pickle=False)
    old_mass = np.load(old_root / "pool_mass.npy", mmap_mode="r", allow_pickle=False)
    baseline.require(old_fp.dtype == np.uint8 and old_fp.shape == (711705, 1300), "OLD_FP_SCHEMA")
    baseline.require(old_mass.dtype == np.float64 and old_mass.shape == (711705,), "OLD_MASS_SCHEMA")
    with (old_root / "pool_meta.pkl").open("rb") as handle:
        old = pickle.load(handle)  # Only own exact SHA-bound public metadata, never publisher pickle.
    baseline.require(old["nbits"] == 10395 and len(old["keys"]) == len(old["smiles"]) == 711705, "OLD_META_SCHEMA")
    old_indices = baseline.sample_indices(711705)
    old_checks = []; new_results = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=2,
            mp_context=multiprocessing.get_context("spawn"), initializer=baseline.init_worker,
            initargs=(bits.tolist(),)) as executor:
        def consume_old(value):
            i, packed, mass, raw_key, group = value
            baseline.require(np.array_equal(packed, old_fp[i]), f"OLD_512_BIT_EXACT:{i}")
            baseline.require(abs(mass - float(old_mass[i])) <= 1e-6, f"OLD_512_MASS:{i}")
            old_checks.append({"source_row": i, "raw_key_matches": raw_key == str(old["keys"][i]), "canonical_group": group})
        old_start = time.monotonic()
        old_times = jobs_only_512(executor, [(i, str(old["smiles"][i])) for i in old_indices], consume_old, started)
        baseline.write_json(output / "OLD_512_CANARY.json", {
            "status": "PASS_EXACT_512_OLD_FINGERPRINTS", "rows": 512,
            "seconds": time.monotonic() - old_start, "indices": old_indices,
            "raw_key_mismatch_count": sum(not x["raw_key_matches"] for x in old_checks),
            "exact_mask_sha256": pins["fp_bits.npy"]["sha256"],
            "mass_absolute_tolerance": 1e-6, "chunk_seconds": old_times,
            "audit_rows": sorted(old_checks, key=lambda x: x["source_row"])})
        print(json.dumps({"stage": "OLD_512_PASS", "rows": 512}), flush=True)
        # This load is deliberately after the complete old512 bit-exact canary.
        table = pq.read_table(external_root / "bio_structures.parquet", use_threads=False)
        columns = {"inchikey14", "smiles", "source", "source_id", "chebi_star", "monoisotopic_mass"}
        baseline.require(columns.issubset(table.column_names) and table.num_rows == 98433, "EXTERNAL_SOURCE_SCHEMA")
        data = {name: table[name].to_pylist() for name in columns}
        categories = {}
        source_star_counts = {}
        for i, (source, star) in enumerate(zip(data["source"], data["chebi_star"])):
            category = (str(source), str(star)); categories.setdefault(category, i)
            label = str(source) + "|" + str(star)
            source_star_counts[label] = source_star_counts.get(label, 0) + 1
        new_indices = baseline.sample_indices(98433, category_rows=list(categories.values()))
        def consume_new(value):
            i, packed, mass, raw_key, group = value
            baseline.require(i not in new_results and i in new_indices, "NEW_CANARY_ROW_ID")
            baseline.require(raw_key == str(data["inchikey14"][i]), f"EXTERNAL_RAW_KEY:{i}")
            declared = float(data["monoisotopic_mass"][i])
            baseline.require(math.isfinite(declared) and abs(mass - declared) <= 1e-6, f"EXTERNAL_MASS:{i}")
            baseline.require(packed.shape == (1300,) and packed.dtype == np.uint8 and int(packed[-1]) & 31 == 0,
                             f"EXTERNAL_PACKING:{i}")
            new_results[i] = (packed, mass, raw_key, group)
        new_start = time.monotonic()
        new_times = jobs_only_512(executor, [(i, str(data["smiles"][i])) for i in new_indices], consume_new, started)
        baseline.require(len(new_results) == 512, "NEW_CANARY_INCOMPLETE")
        new_seconds = time.monotonic() - new_start
        print(json.dumps({"stage": "NEW_512_NUMERIC_PASS", "rows": 512, "full_continuation": False}), flush=True)
    ordered = sorted(new_results)
    fp = np.stack([new_results[i][0] for i in ordered])
    masses = np.asarray([new_results[i][1] for i in ordered], dtype=np.float64)
    indices = np.asarray(ordered, dtype=np.int64)
    for name, array in (("new_512_fp.npy", fp), ("new_512_mass.npy", masses), ("new_512_source_rows.npy", indices)):
        with (output / name).open("xb") as handle:
            np.save(handle, array, allow_pickle=False)
        disk = np.load(output / name, mmap_mode="r", allow_pickle=False)
        baseline.require(disk.dtype == array.dtype and disk.shape == array.shape and np.array_equal(disk, array),
                         "CANARY_EXACT_DISK_RELOAD:" + name)
    selected = table.take(pa.array(indices)).append_column("original_source_row", pa.array(indices))
    selected = selected.append_column("canonical_group", pa.array([new_results[i][3] for i in ordered]))
    with (output / "new_512_source.parquet").open("xb") as handle:
        pq.write_table(selected, handle, compression="zstd")
    baseline.require(pq.read_table(output / "new_512_source.parquet", use_threads=False).equals(selected), "CANARY_PARQUET_EXACT_RELOAD")
    with (output / "fp_bits.npy").open("xb") as handle:
        handle.write((old_root / "fp_bits.npy").read_bytes())
    baseline.require(baseline.sha256(output / "fp_bits.npy") == pins["fp_bits.npy"]["sha256"], "EXPORTED_MASK_IDENTITY")
    baseline.require(verify_public_inputs(old_root, external_root) == pins, "INPUT_IDENTITY_AFTER_CANARY")
    elapsed = time.monotonic() - started
    baseline.require(elapsed <= INNER_SECONDS, "INNER_CANARY_WALL_BUDGET")
    report = {"status": "MAC_512_OLD_512_NEW_COMPLETE_AWAITING_WRAPPER", "old_rows": 512, "new_rows": 512,
        "rdkit": rdkit.__version__, "python": sys.version.split()[0], "numpy": np.__version__,
        "old_bank_unchanged_before_after": pins,
        "new_structure_seconds": new_seconds, "new_chunk_seconds": new_times,
        "full_forecast_current_macos_runtime_only": baseline.numeric_forecast(new_times, 98433 - 512, elapsed),
        "full_continuation": False, "full_native_admission": False,
        "source_star_counts_full_metadata_only": source_star_counts,
        "source_star_card_statistics_discrepancy": "Original card describes 2/3-star; source stats lists 1/2/3. Actual counts reported without silent filtering.",
        "actual_full_new_keys_vs_old_bank": "NOT_MEASURED", "actual_full_metric_novelty": "NOT_MEASURED",
        "model_or_training_or_assay_or_hidden_test": False, "seconds": elapsed,
        "outputs": {path.name: {"bytes": path.stat().st_size, "sha256": baseline.sha256(path)}
                    for path in sorted(output.iterdir()) if path.is_file()}}
    baseline.write_json(output / "CANARY_COMPLETE_AWAITING_WRAPPER.json", report)
    print(json.dumps({"status": report["status"], "old_rows": 512, "new_rows": 512, "full_continuation": False}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
