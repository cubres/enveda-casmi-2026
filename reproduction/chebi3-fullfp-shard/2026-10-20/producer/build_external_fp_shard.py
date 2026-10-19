"""New external-only structure fingerprints. No spectra, labels, models or scoring.

Copyright 2026 cubres. Apache-2.0 for this new source; data terms are separate.
Fingerprint definition follows the publisher's already-public CASMI V6 builders.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
import pickle
import statistics
import sys
import time
import traceback

THREAD_ENV = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")
for _name in THREAD_ENV:
    os.environ[_name] = "1"

EXPECTED_RDKIT = "2026.03.3"
OLD_ROWS = 711705
NEW_ROWS = 98433
RAW_BITS = 10407
NBITS = 10395
PACKED_BYTES = 1300
CANARY_ROWS = 512
CHUNK = 32
BUILD_SECONDS = 1680.0
IO_RESERVE_SECONDS = 120.0
MAX_OUTPUT_BYTES = 512 << 20
EXPECTED_INPUTS = {
    "pool_fp.npy": (925216628, "84afb2d17d567359963f1941c4c8b20523770aad4167ccc0bd715530360611e0"),
    "pool_meta.pkl": (64843052, "53c276a6625f38c90d93e3a8c23c25a2d08712754358b1160f6683e42a922324"),
    "pool_mass.npy": (5693768, "0d28d5c288201e3598ba2fffea7f3d7284e397341ab0d72e5111b4cc67dabd1e"),
    "fp_bits.npy": (83288, "f771cb6aa87a418b06d9abfbdac0c1759040afb955b9dfa59e8932105a65bdc6"),
    "bio_structures.parquet": (5407545, "6bef7106d640ed370046e79d67b86932ba26da3a3632e6901e3b040fad56aa88"),
    "stats.json": (608, "dd0d5686dd54824a40857b75338ed03dc922a2580031d246bf1995b43af57a5e"),
    "ATTRIBUTION.md": (2428, "fb49f6a959f562b7edb50a9103eccbbdf55a2c38327f09b989a369311fd280d7"),
}
_WORKER = {}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def numeric_forecast(chunk_seconds, remaining_rows, elapsed_seconds):
    require(bool(chunk_seconds), "NO_MEASURED_CANARY_TIMES")
    require(all(math.isfinite(x) and x > 0 for x in chunk_seconds), "INVALID_CANARY_TIME")
    ordered = sorted(chunk_seconds)
    p90 = ordered[min(len(ordered) - 1, math.ceil(0.9 * len(ordered)) - 1)]
    per_chunk = max(p90, statistics.median(ordered)) * 1.5
    compute = math.ceil(math.ceil(max(0, remaining_rows) / CHUNK) / 2) * per_chunk
    forecast = elapsed_seconds + compute + IO_RESERVE_SECONDS
    return {"chunk_p90_seconds": p90, "safety_factor": 1.5,
            "remaining_compute_seconds": compute, "io_reserve_seconds": IO_RESERVE_SECONDS,
            "forecast_total_seconds": forecast, "budget_seconds": BUILD_SECONDS,
            "passes": forecast < BUILD_SECONDS}


def sample_indices(total, count=CANARY_ROWS, category_rows=()):
    require(total >= count > 0, "CANARY_REQUIRES_SUFFICIENT_ROWS")
    selected = []
    seen = set()
    values = list(category_rows) + [int(i * (total - 1) / (count - 1)) for i in range(count)] + list(range(count))
    for value in values:
        require(0 <= int(value) < total, "SAMPLE_INDEX_OUT_OF_RANGE")
        if int(value) not in seen:
            selected.append(int(value)); seen.add(int(value))
            if len(selected) == count:
                break
    require(len(selected) == count, "INSUFFICIENT_DISTINCT_CANARY_ROWS")
    return selected


def verify_inputs(root):
    receipts = {}
    for name, (size, expected) in EXPECTED_INPUTS.items():
        path = root / name
        require(path.is_file() and path.stat().st_size == size, f"INPUT_SIZE:{name}")
        observed = sha256(path)
        require(observed == expected, f"INPUT_SHA256:{name}")
        receipts[name] = {"bytes": size, "sha256": observed}
    return receipts


def init_worker(bits):
    import numpy as np
    import rdkit
    from rdkit import Chem, RDLogger
    from rdkit.Chem import MACCSkeys, rdFingerprintGenerator
    from rdkit.Chem.Descriptors import ExactMolWt
    require(rdkit.__version__ == EXPECTED_RDKIT, "WORKER_RDKIT_PIN")
    RDLogger.DisableLog("rdApp.*")
    source_root = Path(__file__).resolve().parent
    require(sha256(source_root / "metric_distinct.py") == "b4c0bbbafca0d821d872733d28f39518f41be53004970a9eeb725aef94a47b4f", "METRIC_HELPER_SOURCE_PIN")
    require(sha256(source_root / "group_identity.py") == "dd4c1750cf4816cdc3d880df837bdffec6a2beb62f3b676cc5ca663107ee042d", "GROUP_HELPER_SOURCE_PIN")
    from metric_distinct import equivalence_key
    from group_identity import group_identity
    _WORKER.update(np=np, Chem=Chem, MACCSkeys=MACCSkeys, ExactMolWt=ExactMolWt,
                   bits=np.asarray(bits, dtype=np.int64),
                   generators=(rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=4096),
                               rdFingerprintGenerator.GetMorganGenerator(radius=3, fpSize=4096),
                               rdFingerprintGenerator.GetRDKitFPGenerator(fpSize=2048, maxPath=6)),
                   equivalence_key=equivalence_key, group_identity=group_identity)


def process_chunk(jobs):
    started = time.monotonic()
    np, Chem = _WORKER["np"], _WORKER["Chem"]
    results = []
    for row, smiles in jobs:
        require(isinstance(smiles, str) and bool(smiles.strip()), f"EMPTY_SMILES:{row}")
        molecule = Chem.MolFromSmiles(smiles)
        require(molecule is not None, f"INVALID_SMILES:{row}")
        raw = np.concatenate([g.GetFingerprintAsNumPy(molecule).astype(np.uint8)
                              for g in _WORKER["generators"]]
                             + [np.asarray(_WORKER["MACCSkeys"].GenMACCSKeys(molecule), np.uint8)])
        require(raw.shape == (RAW_BITS,), f"RAW_BIT_COUNT:{row}")
        packed = np.packbits(raw[_WORKER["bits"]], bitorder="big")
        require(packed.shape == (PACKED_BYTES,) and int(packed[-1]) & 31 == 0, f"PADDING:{row}")
        mass = float(_WORKER["ExactMolWt"](molecule))
        raw_key = Chem.MolToInchiKey(molecule)[:14]
        require(math.isfinite(mass) and mass > 0 and len(raw_key) == 14, f"MASS_OR_KEY:{row}")
        metric_key = _WORKER["equivalence_key"](smiles)
        require(metric_key is not None, f"METRIC_KEY:{row}")
        group_digest, composition, canonical_ik14 = _WORKER["group_identity"](metric_key)
        results.append((int(row), packed, mass, raw_key, group_digest))
    return results, max(time.monotonic() - started, 1e-9)


def chunks(jobs):
    for offset in range(0, len(jobs), CHUNK):
        yield jobs[offset:offset + CHUNK]


def run_jobs(executor, jobs, stage, consume, started, measured_times):
    pending = {}
    iterator = iter(chunks(jobs))
    submitted = completed = 0
    exhausted = False
    while pending or not exhausted:
        require(time.monotonic() - started < BUILD_SECONDS - IO_RESERVE_SECONDS, f"DEADLINE:{stage}")
        while len(pending) < 4 and not exhausted:
            try:
                group = next(iterator)
            except StopIteration:
                exhausted = True
                break
            future = executor.submit(process_chunk, group)
            pending[future] = len(group); submitted += len(group)
        done, _ = concurrent.futures.wait(pending, timeout=0.2,
                                          return_when=concurrent.futures.FIRST_COMPLETED)
        for future in done:
            count = pending.pop(future)
            rows, seconds = future.result()
            require(len(rows) == count, f"CHUNK_ROW_COUNT:{stage}")
            for row in rows:
                consume(row)
            measured_times.append(seconds)
            completed += count
        if stage == "full" and measured_times:
            forecast = numeric_forecast(measured_times[-128:], len(jobs) - completed,
                                        time.monotonic() - started)
            require(forecast["passes"], "ROLLING_FULL_BUDGET_STOP")
    require(completed == submitted == len(jobs), f"COMPLETION_COUNT:{stage}")


def output_size(root):
    return sum(p.stat().st_size for p in root.iterdir() if p.is_file())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.inputs_root.resolve()
    output = args.output_root.resolve()
    require(root != output and root not in output.parents and output not in root.parents, "INPUT_OUTPUT_MUST_BE_SEPARATE")
    require(output.is_dir() and not list(output.iterdir()), "EXCLUSIVE_EMPTY_OWNED_OUTPUT_REQUIRED")
    started = time.monotonic()
    require(os.environ.get("CASMI_EXTERNAL_OWNED_WRAPPER") == "v1", "OWNED_WRAPPER_REQUIRED")
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    import rdkit
    require(rdkit.__version__ == EXPECTED_RDKIT, "RDKIT_PIN")
    input_receipts = verify_inputs(root)  # Every file is pinned before any data deserialization.
    bits = np.load(root / "fp_bits.npy", allow_pickle=False)
    require(bits.dtype == np.dtype("int64") and bits.shape == (NBITS,), "FROZEN_MASK_SCHEMA")
    require(np.array_equal(bits, np.unique(bits)) and int(bits[0]) >= 0 and int(bits[-1]) < RAW_BITS, "FROZEN_MASK_ORDER")
    old_fp = np.load(root / "pool_fp.npy", mmap_mode="r", allow_pickle=False)
    old_mass = np.load(root / "pool_mass.npy", mmap_mode="r", allow_pickle=False)
    require(old_fp.dtype == np.uint8 and old_fp.shape == (OLD_ROWS, PACKED_BYTES), "OLD_FP_SCHEMA")
    require(old_mass.dtype == np.float64 and old_mass.shape == (OLD_ROWS,), "OLD_MASS_SCHEMA")
    # This is our exact, hash-bound public artifact. No unverified publisher pickle is loaded.
    with (root / "pool_meta.pkl").open("rb") as handle:
        old = pickle.load(handle)
    require(int(old["nbits"]) == NBITS and len(old["keys"]) == len(old["smiles"]) == OLD_ROWS, "OLD_META_SCHEMA")
    old_keys = {str(key) for key in old["keys"]}
    require(len(old_keys) == OLD_ROWS, "OLD_KEYS_NOT_UNIQUE")
    old_indices = sample_indices(OLD_ROWS)
    old_jobs = [(i, str(old["smiles"][i])) for i in old_indices]
    old_result = []
    old_times = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=2,
            mp_context=multiprocessing.get_context("spawn"), initializer=init_worker,
            initargs=(bits.tolist(),)) as executor:
        def consume_old(value):
            row, packed, mass, key, audit_key = value
            require(np.array_equal(packed, old_fp[row]), f"OLD_512_BIT_PARITY:{row}")
            require(abs(mass - float(old_mass[row])) <= 1e-6, f"OLD_512_MASS_PARITY:{row}")
            old_result.append({"row": row, "raw_key_matches": key == str(old["keys"][row]),
                               "audit_key": audit_key})
        run_jobs(executor, old_jobs, "old_512", consume_old, started, old_times)
        require(len(old_result) == CANARY_ROWS, "OLD_CANARY_INCOMPLETE")
        write_json(output / "OLD_BANK_512_CANARY.json", {
            "status": "PASS_BIT_EXACT_512", "rows": CANARY_ROWS,
            "source_fp_sha256": EXPECTED_INPUTS["pool_fp.npy"][1],
            "source_mass_sha256": EXPECTED_INPUTS["pool_mass.npy"][1],
            "raw_key_mismatches": sum(not x["raw_key_matches"] for x in old_result),
            "indices": old_indices, "mass_absolute_tolerance": 1e-6,
            "audited_results": sorted(old_result, key=lambda x: x["row"]),
            "seconds_since_start": time.monotonic() - started})
        # No external table is loaded or new-structure timing performed before the old-bank parity pass.
        table = pq.read_table(root / "bio_structures.parquet")
        required = {"inchikey14", "smiles", "source", "source_id", "chebi_star", "monoisotopic_mass"}
        require(required.issubset(set(table.column_names)) and table.num_rows == NEW_ROWS, "EXTERNAL_TABLE_SCHEMA")
        data = {name: table[name].to_pylist() for name in required}
        category_first = {}
        for i, (source, star) in enumerate(zip(data["source"], data["chebi_star"])):
            category_first.setdefault((str(source), str(star)), i)
        new_indices = sample_indices(NEW_ROWS, category_rows=list(category_first.values()))
        matrix = np.empty((NEW_ROWS, PACKED_BYTES), dtype=np.uint8)
        masses = np.empty(NEW_ROWS, dtype=np.float64)
        raw_keys = [None] * NEW_ROWS
        audit_keys = [None] * NEW_ROWS
        completed = np.zeros(NEW_ROWS, dtype=bool)
        new_times = []
        def consume_new(value):
            row, packed, mass, key, audit_key = value
            require(not completed[row], f"DUPLICATE_COMPLETION:{row}")
            require(key == str(data["inchikey14"][row]), f"SOURCE_RAW_KEY_MISMATCH:{row}")
            declared_mass = float(data["monoisotopic_mass"][row])
            require(math.isfinite(declared_mass) and abs(mass - declared_mass) <= 1e-6,
                    f"SOURCE_MASS_MISMATCH:{row}")
            matrix[row] = packed; masses[row] = mass
            raw_keys[row] = key; audit_keys[row] = audit_key; completed[row] = True
        canary_start = time.monotonic()
        run_jobs(executor, [(i, str(data["smiles"][i])) for i in new_indices],
                 "new_512", consume_new, started, new_times)
        with (output / "new_512_fp.npy").open("xb") as handle:
            np.save(handle, matrix[new_indices], allow_pickle=False)
        disk_canary = np.load(output / "new_512_fp.npy", allow_pickle=False)
        require(np.array_equal(disk_canary, matrix[new_indices]), "NEW_CANARY_EXACT_DISK_RELOAD")
        forecast = numeric_forecast(new_times, NEW_ROWS - CANARY_ROWS, time.monotonic() - started)
        require(forecast["passes"], "NEW_CANARY_FORECAST_REJECTED")
        write_json(output / "NEW_STRUCTURE_512_CANARY.json", {
            "status": "PASS_WITH_FULL_BUDGET_ADMITTED", "rows": CANARY_ROWS,
            "indices": new_indices, "seconds": time.monotonic() - canary_start,
            "fingerprint_seconds_per_chunk": new_times, "forecast": forecast,
            "disk_reload_exact": True, "disk_canary_sha256": sha256(output / "new_512_fp.npy"),
            "category_first_rows": [{"source": k[0], "star": k[1], "row": v}
                                    for k, v in sorted(category_first.items())],
            "claim": "Numeric/resource admission only; no model, accuracy, assay or hidden-answer coverage."})
        remaining = [(i, str(data["smiles"][i])) for i in range(NEW_ROWS) if not completed[i]]
        full_times = list(new_times)
        run_jobs(executor, remaining, "full", consume_new, started, full_times)
    require(bool(completed.all()) and completed.sum() == NEW_ROWS, "FULL_BITMAP_INCOMPLETE")
    require(bool(((matrix[:, -1] & 31) == 0).all()), "FULL_PADDING")
    raw_first, audit_first = {}, {}
    duplicates_raw, duplicates_audit, exists_old, eligible, reasons = [], [], [], [], []
    source_counts, star_counts = {}, {}
    for i, (key, audit_key, mass) in enumerate(zip(raw_keys, audit_keys, masses)):
        previous_raw = raw_first.setdefault(key, i)
        previous_audit = audit_first.setdefault(audit_key, i)
        prior = key in old_keys
        in_mass_range = 80 <= float(mass) <= 1400
        duplicates_raw.append(previous_raw if previous_raw != i else -1)
        duplicates_audit.append(previous_audit if previous_audit != i else -1)
        exists_old.append(prior)
        eligible.append(not prior and previous_raw == i and in_mass_range)
        reasons.append("already_in_old_raw_bank" if prior else "duplicate_raw_key" if previous_raw != i
                       else "outside_old_mass_range" if not in_mass_range else "eligible_raw_extension")
        source = str(data["source"][i]); star = str(data["chebi_star"][i])
        source_counts[source] = source_counts.get(source, 0) + 1
        star_counts[source + "|" + star] = star_counts.get(source + "|" + star, 0) + 1
    enriched = table.append_column("source_row", pa.array(range(NEW_ROWS), type=pa.int64()))
    for name, values in {"computed_raw_key": raw_keys, "metric_audit_key": audit_keys,
                         "computed_neutral_mass": masses, "already_in_old_raw_bank": exists_old,
                         "duplicate_raw_source_row": duplicates_raw, "duplicate_metric_audit_source_row": duplicates_audit,
                         "eligible_raw_extension": eligible, "extension_reason": reasons}.items():
        enriched = enriched.append_column(name, pa.array(values))
    with (output / "external_structures.parquet").open("xb") as handle:
        pq.write_table(enriched, handle, compression="zstd")
    arrays = {"external_fp.npy": matrix, "external_mass.npy": masses,
              "mass_order.npy": np.argsort(masses, kind="stable").astype(np.int64),
              "completion_bitmap.npy": completed}
    for name, value in arrays.items():
        with (output / name).open("xb") as handle:
            np.save(handle, value, allow_pickle=False)
        disk = np.load(output / name, mmap_mode="r", allow_pickle=False)
        require(disk.dtype == value.dtype and disk.shape == value.shape
                and np.array_equal(disk, value), f"FULL_EXACT_DISK_RELOAD:{name}")
        require(output_size(output) <= MAX_OUTPUT_BYTES, "OUTPUT_BUDGET")
    with (output / "fp_bits.npy").open("xb") as handle:
        handle.write((root / "fp_bits.npy").read_bytes())
    require(sha256(output / "fp_bits.npy") == EXPECTED_INPUTS["fp_bits.npy"][1], "EXPORTED_MASK_IDENTITY")
    parquet_reload = pq.read_table(output / "external_structures.parquet")
    require(parquet_reload.equals(enriched), "FULL_PARQUET_EXACT_DISK_RELOAD")
    # Copy attribution unchanged, without copying a checkpoint, spectra or legacy bank.
    for name in ("ATTRIBUTION.md", "stats.json"):
        with (output / ("SOURCE_" + name)).open("xb") as handle:
            handle.write((root / name).read_bytes())
    source_root = Path(__file__).resolve().parent
    for name in ("build_external_fp_shard.py", "run_owned_builder.py", "stage_inputs.py",
                 "metric_distinct.py", "group_identity.py", "SOURCE_MANIFEST.json",
                 "test_pure_admission.py", "DATA-LICENSE.md", "LICENSE-SOURCE", "README.md", "PUBLIC_SOURCE_BINDINGS.json"):
        with (output / name).open("xb") as handle:
            handle.write((source_root / name).read_bytes())
    unchanged_inputs = verify_inputs(root)
    require(unchanged_inputs == input_receipts, "INPUT_IDENTITY_CHANGED")
    observed_stats = json.loads((root / "stats.json").read_text())
    report = {"status": "BUILD_COMPLETE_AWAITING_WRAPPER", "rows": NEW_ROWS,
        "rdkit": rdkit.__version__, "python": sys.version.split()[0], "numpy": np.__version__,
        "raw_bits": RAW_BITS, "selected_bits": NBITS, "packed_bytes": PACKED_BYTES,
        "bitorder": "big", "trailing_padding_bits": 5, "completed_rows": int(completed.sum()),
        "all_output_numeric_and_parquet_disk_reloads_exact": True,
        "old_bank_identity_before_and_after": input_receipts,
        "source_counts_actual": source_counts, "source_star_counts_actual": star_counts,
        "source_stats_chebi_stars": observed_stats.get("chebi_stars"),
        "source_card_claims_two_or_three_star": True,
        "quality_note": "Report observed star values; stats mentions 1/2/3 while the source card describes 2/3.",
        "raw_keys_in_old_bank": sum(exists_old), "duplicate_raw_rows_within_external": sum(x >= 0 for x in duplicates_raw),
        "duplicate_metric_audit_rows_within_external": sum(x >= 0 for x in duplicates_audit),
        "eligible_raw_extension_rows": sum(eligible),
        "metric_audit_definition": "Exact existing public metric_distinct.equivalence_key b4c0bbba… and group_identity dd4c1750…; default tautomer canonicalization, InChIKey14 plus heavy-atom composition. No extra stereo-removal transform.",
        "metric_novelty_vs_entire_old_bank": "NOT_MEASURED; old-bank metric keys were calculated only for the 512-row integrity canary.",
        "hidden_answer_coverage_or_score": "NOT_MEASURED", "model_training_or_inference": False,
        "completed_old_assay_repeated": False, "seconds": time.monotonic() - started,
        "outputs": {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p)}
                    for p in sorted(output.iterdir()) if p.is_file()}}
    require(report["seconds"] < BUILD_SECONDS and output_size(output) <= MAX_OUTPUT_BYTES, "FINAL_BUDGET")
    write_json(output / "BUILD_COMPLETE_AWAITING_WRAPPER.json", report)
    print(json.dumps({k: report[k] for k in ("status", "rows", "eligible_raw_extension_rows", "seconds")}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
