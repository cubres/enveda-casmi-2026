"""4096 new-raw-key ChEBI3-star full-FP rows; no model or score assay.

Apache-2.0 new source. All fingerprint outputs use the unchanged old512-proven
baseline.process_chunk; instrumentation is checked against it for64 rows only.
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
import build_external_fp_shard as base
from selection_and_budget import select_shard, forecast_budget

CHUNK = 8
DRIVER_SECONDS = 1760.0
IO_RESERVE = 120.0
OUTPUT_BYTES = 512 << 20
BASE_SHA = "0d25816ad0de134d9c4a790530b15e3a89285332aef90f3252bc263ca48ed092"
PROOF_RESULT_SHA = "af4bd30904f66f57031d63f6548e9b2b710fbca7196c4bc79d68860aade7a700"
PROOF_CHILD_SHA = "48897a3fe1bc63fc4ef8b814e9c5e2629f14ea33204394bf3905ba9b768e12d6"
PROOF_OLD_SHA = "f089f64b3bb77550616b3ac5f5423315fdc12b3c1e49e39171642074e09699b5"
PROOF_MANIFEST_SHA = "5f9537852f0091ce3fb808fc4daa8af17b102793866a79c000f6f60c99432ce8"


def verify_inputs(old_root, external_root):
    own = {"pool_fp.npy", "pool_mass.npy", "pool_meta.pkl", "fp_bits.npy"}
    result = {}
    for name, (size, expected) in base.EXPECTED_INPUTS.items():
        path = (old_root if name in own else external_root) / name
        base.require(path.is_file() and path.stat().st_size == size, "INPUT_SIZE:" + name)
        observed = base.sha256(path)
        base.require(observed == expected, "INPUT_SHA:" + name)
        result[name] = {"bytes": size, "sha256": observed}
    return result


def verify_old512_proof(proof_run, current_inputs, runtime):
    proof_source = proof_run.parent
    files = {proof_run / "RESULT.json": PROOF_RESULT_SHA,
             proof_run / "data/CANARY_COMPLETE_AWAITING_WRAPPER.json": PROOF_CHILD_SHA,
             proof_run / "data/OLD_512_CANARY.json": PROOF_OLD_SHA,
             proof_source / "SOURCE_MANIFEST.json": PROOF_MANIFEST_SHA}
    for path, expected in files.items():
        base.require(path.is_file() and base.sha256(path) == expected, "OLD512_PROOF_PIN:" + path.name)
    manifest = json.loads((proof_source / "SOURCE_MANIFEST.json").read_text())
    for name, pin in manifest["files"].items():
        path = proof_source / name
        base.require(path.stat().st_size == pin["bytes"] and base.sha256(path) == pin["sha256"], "OLD512_EXECUTED_SOURCE:" + name)
    result = json.loads((proof_run / "RESULT.json").read_text())
    child = json.loads((proof_run / "data/CANARY_COMPLETE_AWAITING_WRAPPER.json").read_text())
    old = json.loads((proof_run / "data/OLD_512_CANARY.json").read_text())
    base.require(result["status"] == "COMPLETE_MAC_CANARY_ONLY" and result["child_returncode"] == 0
                 and not result["remaining_owned_group_pids"], "OLD512_PROOF_TERMINAL")
    base.require(old["status"] == "PASS_EXACT_512_OLD_FINGERPRINTS" and old["rows"] == 512
                 and old["raw_key_mismatch_count"] == 0, "OLD512_PROOF_PARITY")
    base.require(child["old_bank_unchanged_before_after"] == current_inputs, "OLD512_INPUT_IDENTITIES")
    base.require(runtime == {"python": child["python"], "numpy": child["numpy"], "rdkit": child["rdkit"]}, "OLD512_RUNTIME_IDENTITIES")
    here = Path(__file__).resolve().parent
    for name in ("build_external_fp_shard.py", "metric_distinct.py", "group_identity.py"):
        base.require(base.sha256(here / name) == manifest["files"][name]["sha256"], "IDENTICAL_FP_AND_GROUP_SOURCE:" + name)
    base.require(base.sha256(here / "build_external_fp_shard.py") == BASE_SHA, "BASE_FP_SOURCE")
    return {"status": "REUSED_EXACT_OLD512_INTEGRITY_PROOF", "rows": 512,
            "result_sha256": PROOF_RESULT_SHA, "child_receipt_sha256": PROOF_CHILD_SHA,
            "old_phase_sha256": PROOF_OLD_SHA, "executed_source_manifest_sha256": PROOF_MANIFEST_SHA,
            "current_input_hashes_identical": True, "runtime_identical": runtime,
            "fp_group_sources_identical": True, "old512_chemistry_repeated": False,
            "scope": "Deterministic FP/mass integrity only; no new-subset quality or score qualification."}


def timed_profile_chunk(jobs):
    """Diagnostic copy only, never the source of final fingerprint output."""
    np, Chem = base._WORKER["np"], base._WORKER["Chem"]
    answer = []
    for row, smiles in jobs:
        timings = {}; begin = time.monotonic()
        t = time.monotonic(); molecule = Chem.MolFromSmiles(smiles)
        base.require(molecule is not None, "PROFILE_PARSE")
        timings["parse"] = time.monotonic() - t
        parts = []
        for label, generator in zip(("Morgan_r2_4096", "Morgan_r3_4096", "RDKit_path6_2048"), base._WORKER["generators"]):
            t = time.monotonic(); parts.append(generator.GetFingerprintAsNumPy(molecule).astype(np.uint8))
            timings[label] = time.monotonic() - t
        t = time.monotonic(); parts.append(np.asarray(base._WORKER["MACCSkeys"].GenMACCSKeys(molecule), np.uint8))
        timings["MACCS_167"] = time.monotonic() - t
        t = time.monotonic(); raw = np.concatenate(parts)
        base.require(raw.shape == (10407,), "PROFILE_RAW_BITS")
        packed = np.packbits(raw[base._WORKER["bits"]], bitorder="big")
        timings["concatenate_mask_pack"] = time.monotonic() - t
        t = time.monotonic(); mass = float(base._WORKER["ExactMolWt"](molecule)); raw_key = Chem.MolToInchiKey(molecule)[:14]
        timings["exact_mass_and_raw_InChIKey"] = time.monotonic() - t
        before = base._WORKER["equivalence_key"].cache_info()
        t = time.monotonic(); metric_key = base._WORKER["equivalence_key"](smiles)
        timings["unchanged_metric_equivalence_key"] = time.monotonic() - t
        base.require(metric_key is not None, "PROFILE_METRIC_KEY")
        after = base._WORKER["equivalence_key"].cache_info()
        t = time.monotonic(); group, composition, ik14 = base._WORKER["group_identity"](metric_key)
        timings["unchanged_group_identity_hash"] = time.monotonic() - t
        base.require(all(math.isfinite(value) and value >= 0 for value in timings.values()), "PROFILE_TIMING")
        answer.append({"row": row, "fp": packed, "mass": mass, "raw_key": raw_key, "group": group,
                       "stage_seconds": timings, "total_seconds": time.monotonic() - begin,
                       "metric_cache_hits": after.hits - before.hits, "metric_cache_misses": after.misses - before.misses})
    return answer


def run_chunks(executor, function, jobs, consume, started, forecast_times=None, completed_before=0):
    groups = [jobs[i:i + CHUNK] for i in range(0, len(jobs), CHUNK)]
    iterator = iter(groups); pending = {}; exhausted = False; completed = 0
    while pending or not exhausted:
        base.require(time.monotonic() - started < DRIVER_SECONDS - IO_RESERVE, "COMPUTE_DEADLINE_WITH_IO_RESERVE")
        while len(pending) < 4 and not exhausted:
            try:
                group = next(iterator)
            except StopIteration:
                exhausted = True; break
            pending[executor.submit(function, group)] = [index for index, _ in group]
        done, _ = concurrent.futures.wait(pending, timeout=0.1, return_when=concurrent.futures.FIRST_COMPLETED)
        for future in done:
            expected = pending.pop(future); payload = future.result()
            if function is base.process_chunk:
                rows, seconds = payload
                base.require([row[0] for row in rows] == expected, "BASELINE_CHUNK_ROW_ORDER")
                for value in rows:
                    consume(value)
                if forecast_times is not None:
                    forecast_times.append(seconds)
            else:
                base.require([row["row"] for row in payload] == expected, "PROFILE_CHUNK_ROW_ORDER")
                for value in payload:
                    consume(value)
            completed += len(expected)
        if forecast_times is not None and completed_before >= 64 and forecast_times:
            forecast = forecast_budget(forecast_times[-128:], elapsed_seconds=time.monotonic() - started,
                                       completed_rows=completed_before + completed)
            base.require(forecast["passes"], "ROLLING_SELECTED_SHARD_FORECAST_REJECTED")
    base.require(completed == len(jobs), "EXACT_JOB_COMPLETION")


def exact_npy(path, value):
    import numpy as np
    with path.open("xb") as handle:
        np.save(handle, value, allow_pickle=False)
    disk = np.load(path, mmap_mode="r", allow_pickle=False)
    base.require(disk.dtype == value.dtype and disk.shape == value.shape and np.array_equal(disk, value), "EXACT_NPY_RELOAD:" + path.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-bank-root", type=Path, required=True)
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--old-proof-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    base.require(sys.platform == "darwin" and os.environ.get("CASMI_CHEBI3_OWNED_WRAPPER") == "v1", "OWNED_MAC_JOB_REQUIRED")
    output = args.output_root.resolve(); old_root = args.old_bank_root.resolve(); external = args.external_root.resolve()
    base.require(output.is_dir() and not list(output.iterdir()), "EXCLUSIVE_EMPTY_OWNED_OUTPUT")
    base.require(all(path != output and path not in output.parents and output not in path.parents
                     for path in (old_root, external, args.old_proof_root.resolve())), "INPUT_OUTPUT_SEPARATION")
    started = time.monotonic()
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    import rdkit
    pa.set_cpu_count(1); pa.set_io_thread_count(1)
    base.require(pa.__version__ == "25.0.0", "PYARROW_DEPENDENCY_PIN")
    runtime = {"python": sys.version.split()[0], "numpy": np.__version__, "rdkit": rdkit.__version__}
    base.require(runtime == {"python": "3.12.14", "numpy": "2.2.6", "rdkit": "2026.03.3"}, "EXACT_PROVEN_RUNTIME")
    phase_seconds = {}; phase_start = time.monotonic()
    input_pins = verify_inputs(old_root, external)
    phase_seconds["input_sha256_verification"] = time.monotonic() - phase_start
    phase_start = time.monotonic()
    proof = verify_old512_proof(args.old_proof_root.resolve(), input_pins, runtime)
    base.write_json(output / "OLD512_PROOF_REUSE.json", proof)
    phase_seconds["old512_proof_and_executed_source_verification"] = time.monotonic() - phase_start
    phase_start = time.monotonic()
    bits = np.load(old_root / "fp_bits.npy", allow_pickle=False)
    base.require(bits.dtype == np.int64 and bits.shape == (10395,) and np.array_equal(bits, np.unique(bits)), "MASK_SCHEMA")
    with (old_root / "pool_meta.pkl").open("rb") as handle:
        old = pickle.load(handle)  # Own exact SHA-bound public metadata only.
    base.require(old["nbits"] == 10395 and len(old["keys"]) == len(old["smiles"]) == 711705, "OLD_BANK_METADATA")
    old_keys = set(map(str, old["keys"])); old_smiles = set(map(str, old["smiles"]))
    base.require(len(old_keys) == 711705, "OLD_BANK_RAW_KEY_UNIQUENESS")
    source = pq.read_table(external / "bio_structures.parquet", use_threads=False)
    base.require(source.num_rows == 98433, "EXACT_PUBLIC_SOURCE_ROWS")
    records = source.to_pylist()
    selection = select_shard(records, old_keys)
    base.require(selection["eligible_count"] == 8895, "ELIGIBLE_METADATA_COUNT")
    chosen = selection["selected_indices"]
    base.require(len(chosen) == len(set(chosen)) == 4096 and selection["canary_indices"] == chosen[:64], "SELECTED_4096_CANARY64")
    base.require(all(str(records[row]["smiles"]) not in old_smiles for row in chosen), "SELECTED_EXACT_SMILES_ALREADY_IN_OLD")
    base.write_json(output / "SELECTION_MANIFEST.json", dict(selection, status="FROZEN_BEFORE_ANY_NEW_CHEMISTRY",
        source_parquet_sha256=input_pins["bio_structures.parquet"]["sha256"],
        old_pool_metadata_sha256=input_pins["pool_meta.pkl"]["sha256"],
        metric_novelty_vs_entire_old_bank="NOT_MEASURED", hidden_answer_coverage_or_score="NOT_MEASURED"))
    phase_seconds["metadata_load_and_deterministic_selection"] = time.monotonic() - phase_start
    matrix = np.empty((4096, 1300), np.uint8); masses = np.empty(4096, np.float64)
    raw_keys = [None] * 4096; groups = [None] * 4096; done = np.zeros(4096, bool)
    profiles = {}; reference_times = []
    canary_jobs = [(i, str(records[chosen[i]]["smiles"])) for i in range(64)]
    phase_start = time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("spawn"),
            initializer=base.init_worker, initargs=(bits.tolist(),)) as profile_pool:
        def consume_profile(value):
            base.require(value["row"] not in profiles, "PROFILE_ROW_DUPLICATE")
            profiles[value["row"]] = value
        run_chunks(profile_pool, timed_profile_chunk, canary_jobs, consume_profile, started)
    base.require(len(profiles) == 64, "PROFILE64_COMPLETION")
    phase_seconds["profile64_fresh_two_worker_pool_and_shutdown"] = time.monotonic() - phase_start
    phase_start = time.monotonic()
    # The measured baseline pool is fresh; profile calls cannot warm its metric LRU.
    with concurrent.futures.ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("spawn"),
            initializer=base.init_worker, initargs=(bits.tolist(),)) as pool:
        def consume_baseline(value):
            i, packed, mass, raw_key, group = value
            base.require(0 <= i < 4096 and not done[i], "BASELINE_COMPLETION_ID")
            row = records[chosen[i]]
            base.require(raw_key == str(row["inchikey14"]) and raw_key not in old_keys, "SELECTED_RAW_KEY_IDENTITY")
            declared = float(row["monoisotopic_mass"])
            base.require(math.isfinite(mass) and math.isfinite(declared) and abs(mass - declared) <= 1e-6
                         and 80 <= mass <= 1400, "SELECTED_MASS_IDENTITY")
            base.require(packed.dtype == np.uint8 and packed.shape == (1300,) and int(packed[-1]) & 31 == 0,
                         "SELECTED_FINGERPRINT_PACKING")
            if i < 64:
                observed = profiles[i]
                base.require(np.array_equal(packed, observed["fp"]) and mass == observed["mass"]
                             and raw_key == observed["raw_key"] and group == observed["group"], "PROFILE_REFERENCE_EXACT_PARITY")
            matrix[i] = packed; masses[i] = mass; raw_keys[i] = raw_key; groups[i] = group; done[i] = True
        run_chunks(pool, base.process_chunk, canary_jobs, consume_baseline, started, reference_times)
        base.require(done[:64].all() and not done[64:].any(), "EXACT_CANARY64_ONLY")
        phase_seconds["original64_fresh_two_worker_pool"] = time.monotonic() - phase_start
        phase_start = time.monotonic()
        exact_npy(output / "canary64_fp.npy", matrix[:64]); exact_npy(output / "canary64_mass.npy", masses[:64])
        exact_npy(output / "canary64_source_rows.npy", np.asarray(chosen[:64], np.int64))
        canary_table = source.take(pa.array(chosen[:64])).append_column("canonical_group", pa.array(groups[:64]))
        with (output / "canary64_source.parquet").open("xb") as handle:
            pq.write_table(canary_table, handle, compression="zstd")
        base.require(pq.read_table(output / "canary64_source.parquet", use_threads=False).equals(canary_table), "CANARY_PARQUET_EXACT_RELOAD")
        phase_seconds["canary64_numeric_and_parquet_disk_reload"] = time.monotonic() - phase_start
        timing_records = [{key: value for key, value in profiles[i].items() if key != "fp"} for i in range(64)]
        forecast = forecast_budget(reference_times, elapsed_seconds=time.monotonic() - started, completed_rows=64)
        base.write_json(output / "CANARY64_GATE.json", {"numeric_and_disk_parity": "PASS", "rows": 64,
            "baseline_original_chunk_seconds": reference_times, "instrumented_stage_records": timing_records,
            "reference_pool_fresh_after_profile_pool_closed": True, "forecast": forecast,
            "phase_seconds_before_gate": dict(phase_seconds),
            "full_continuation_admitted": forecast["passes"], "old512_reused_not_repeated": True})
        base.require(forecast["passes"], "SELECTED64_FORECAST_REJECTED_NO_CONTINUATION")
        print(json.dumps({"stage": "SELECTED64_NUMERIC_AND_FORECAST_PASS", "forecast": forecast}), flush=True)
        phase_start = time.monotonic()
        run_chunks(pool, base.process_chunk, [(i, str(records[chosen[i]]["smiles"])) for i in range(64, 4096)],
                   consume_baseline, started, reference_times, completed_before=64)
    phase_seconds["remaining4032_original_and_pool_shutdown"] = time.monotonic() - phase_start
    phase_start = time.monotonic()
    base.require(done.all() and len(set(raw_keys)) == 4096 and np.all((matrix[:, -1] & 31) == 0), "FULL_COMPLETION_PACKING_UNIQUENESS")
    enriched = source.take(pa.array(chosen)).append_column("original_source_row", pa.array(chosen, type=pa.int64()))
    enriched = enriched.append_column("canonical_group", pa.array(groups))
    enriched = enriched.append_column("computed_raw_key", pa.array(raw_keys))
    enriched = enriched.append_column("computed_mass", pa.array(masses))
    with (output / "external_chebi3_4096.parquet").open("xb") as handle:
        pq.write_table(enriched, handle, compression="zstd")
    base.require(pq.read_table(output / "external_chebi3_4096.parquet", use_threads=False).equals(enriched), "FULL_PARQUET_EXACT_RELOAD")
    for name, array in {"external_fp.npy": matrix, "external_mass.npy": masses,
                        "original_source_rows.npy": np.asarray(chosen, np.int64), "completion_bitmap.npy": done,
                        "mass_order.npy": np.argsort(masses, kind="stable").astype(np.int64)}.items():
        exact_npy(output / name, array)
    for name in ("fp_bits.npy",):
        with (output / name).open("xb") as handle:
            handle.write((old_root / name).read_bytes())
        base.require(base.sha256(output / name) == input_pins[name]["sha256"], "COPIED_MASK_BYTE_IDENTITY")
    for name in ("ATTRIBUTION.md", "stats.json"):
        with (output / ("SOURCE_" + name)).open("xb") as handle:
            handle.write((external / name).read_bytes())
    here = Path(__file__).resolve().parent
    source_manifest = json.loads((here / "SOURCE_MANIFEST.json").read_text())
    for name in list(source_manifest["files"]) + ["SOURCE_MANIFEST.json"]:
        with (output / name).open("xb") as handle:
            handle.write((here / name).read_bytes())
    # Retain the exact small old512 proof and its executed source, without old FP data.
    proof_root = output / "old512_proof"; proof_root.mkdir(); proof_run = proof_root / "run"; proof_run.mkdir()
    proof_data = proof_run / "data"; proof_data.mkdir()
    old_source = args.old_proof_root.resolve().parent
    old_manifest = json.loads((old_source / "SOURCE_MANIFEST.json").read_text())
    for name in list(old_manifest["files"]) + ["SOURCE_MANIFEST.json"]:
        with (proof_root / name).open("xb") as handle:
            handle.write((old_source / name).read_bytes())
    for source_file, destination in ((args.old_proof_root / "RESULT.json", proof_run / "RESULT.json"),
        (args.old_proof_root / "data/OLD_512_CANARY.json", proof_data / "OLD_512_CANARY.json"),
        (args.old_proof_root / "data/CANARY_COMPLETE_AWAITING_WRAPPER.json", proof_data / "CANARY_COMPLETE_AWAITING_WRAPPER.json")):
        with destination.open("xb") as handle:
            handle.write(source_file.read_bytes())
    base.require(verify_inputs(old_root, external) == input_pins, "INPUTS_UNCHANGED_AFTER_FULL")
    verify_old512_proof(args.old_proof_root.resolve(), input_pins, runtime)
    size = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
    base.require(size <= OUTPUT_BYTES and time.monotonic() - started < DRIVER_SECONDS, "FINAL_RESOURCE_BUDGET")
    output_manifest = {str(path.relative_to(output)): {"bytes": path.stat().st_size, "sha256": base.sha256(path)}
                       for path in sorted(output.rglob("*")) if path.is_file()}
    phase_seconds["full_output_reload_proof_input_reverification_and_output_hashes"] = time.monotonic() - phase_start
    base.require(time.monotonic() - started < DRIVER_SECONDS, "FINAL_HASHING_WITHIN_DEADLINE")
    base.write_json(output / "BUILD_COMPLETE_AWAITING_WRAPPER.json", {
        "status": "COMPLETE_4096_AWAITING_WRAPPER", "rows": 4096, "canary_rows": 64,
        "eligible_raw_key_new_chebi3_rows": 8895, "actual_selected_raw_key_new": 4096,
        "canonical_groups_selected": len(set(groups)), "metric_novelty_vs_old711705": "NOT_MEASURED",
        "fingerprints_from_unchanged_baseline_only": True, "old512_proof_reused": proof,
        "runtime": runtime, "input_hashes_before_and_after": input_pins,
        "pyarrow_version": pa.__version__,
        "phase_seconds": phase_seconds,
        "all_numeric_and_parquet_reloads_exact": True, "seconds": time.monotonic() - started,
        "output_bytes": size, "no_model_training_assay_hidden_test": True,
        "outputs": output_manifest})
    print(json.dumps({"status": "COMPLETE_4096_AWAITING_WRAPPER", "rows": 4096}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
