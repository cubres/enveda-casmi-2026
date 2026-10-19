"""Read-only completed-shard audit. No RDKit calls, chemistry or score assay.

SPDX-License-Identifier: Apache-2.0
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pickle
import re
import sys
import time

SOURCE_SHA = "f14c9513f514743f785decddc6bbfc99306f547959331543252904f60a8a1c22"
BUILD_SHA = "01f0b7e8fd0d963975f6976c605180e40ea806d4bfa49cbfb87949295a5f823a"


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()


def require(value, code):
    if not value:
        raise RuntimeError(code)


def audit(packet, old_root, external):
    started = time.monotonic()
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    sys.path.insert(0, str(packet))
    import build_external_fp_shard as base
    import build_chebi3_shard as producer
    import run_owned_chebi3_shard as wrapper
    from selection_and_budget import select_shard, forecast_budget
    run = packet / "ROOT_CHEBI3_4096_SHARD_ONCE"
    data = run / "data"
    require(digest(packet / "SOURCE_MANIFEST.json") == SOURCE_SHA, "CURRENT_SOURCE_MANIFEST")
    manifest = json.loads((packet / "SOURCE_MANIFEST.json").read_text())
    require(wrapper.verify_sources(manifest, packet), "CURRENT13_SOURCE_PINS")
    result = json.loads((run / "RESULT.json").read_text())
    require(result["status"] == "COMPLETE_CHEBI3_4096_SHARD" and result["child_returncode"] == 0
            and result["remaining_owned_group_pids"] == [] and result["reason"] is None, "TERMINAL_OWNED_RESULT")
    require(digest(data / "BUILD_COMPLETE_AWAITING_WRAPPER.json") == BUILD_SHA == result["build_receipt_sha256"], "ACTUAL_BUILD_PIN")
    build = json.loads((data / "BUILD_COMPLETE_AWAITING_WRAPPER.json").read_text())
    require(wrapper.receipt_is_complete(build), "BUILD_CONTRACT")
    require(result["seconds"] < 1800 and result["aggregate_cpu_seconds"] < 3600
            and result["sum_observed_rss_peak_bytes"] < 4 << 30
            and result["output_bytes_before_final_receipt"] < (512 << 20) - 65536, "ACTUAL_RESOURCES")
    outputs = build["outputs"]
    actual = {str(path.relative_to(data)) for path in data.rglob("*") if path.is_file()}
    require(actual == set(outputs) | {"BUILD_COMPLETE_AWAITING_WRAPPER.json"}, "EXACT_OUTPUT_INVENTORY")
    for name, pin in outputs.items():
        path = data / name
        require(path.stat().st_size == pin["bytes"] and digest(path) == pin["sha256"], "OUTPUT_PIN:" + name)
    for name, pin in manifest["files"].items():
        require(digest(data / name) == pin["sha256"], "OUTPUT_PRODUCER_PIN:" + name)
    require(digest(data / "SOURCE_MANIFEST.json") == SOURCE_SHA, "OUTPUT_MANIFEST_BYTE_IDENTITY")

    input_pins = producer.verify_inputs(old_root, external)  # Hash all7 before any own-pickle load.
    require(input_pins == build["input_hashes_before_and_after"], "CURRENT7_INPUT_IDENTITIES")
    old512 = producer.verify_old512_proof(data / "old512_proof/run", input_pins, build["runtime"])
    require(old512 == build["old512_proof_reused"], "BUNDLED_OLD512_PROOF_IDENTITIES")
    with (old_root / "pool_meta.pkl").open("rb") as handle:
        old = pickle.load(handle)  # Own public SHA-bound pickle only; publisher pickle is never used.
    old_keys = set(old["keys"])
    old_smiles = set(old["smiles"])
    require(len(old_keys) == len(old["keys"]) == 711705 and old["nbits"] == 10395, "OLD_POOL_METADATA")
    source = pq.read_table(external / "bio_structures.parquet", use_threads=False)
    require(source.num_rows == 98433, "PUBLIC_SOURCE_COUNT")
    source_records = source.to_pylist()
    selection = select_shard(source_records, old_keys)
    observed_selection = json.loads((data / "SELECTION_MANIFEST.json").read_text())
    require(all(observed_selection[key] == value for key, value in selection.items()), "DETERMINISTIC_SELECTION_REPLAY")
    require(selection["eligible_count"] == 8895 and len(selection["selected_indices"]) == 4096, "SELECTION_COUNTS")

    def load(name, dtype, shape):
        array = np.load(data / name, mmap_mode="r", allow_pickle=False)
        require(array.dtype == np.dtype(dtype) and array.shape == shape, "NUMPY_SCHEMA:" + name)
        return array

    fp = load("external_fp.npy", "uint8", (4096, 1300))
    mass = load("external_mass.npy", "float64", (4096,))
    rows = load("original_source_rows.npy", "int64", (4096,))
    order = load("mass_order.npy", "int64", (4096,))
    bitmap = load("completion_bitmap.npy", "bool", (4096,))
    bits = load("fp_bits.npy", "int64", (10395,))
    require(np.array_equal(bits, np.unique(bits)) and bits.min() >= 0 and bits.max() < 10407, "FROZEN_BIT_POSITIONS")
    require(digest(data / "fp_bits.npy") == input_pins["fp_bits.npy"]["sha256"], "MASK_IDENTITY")
    require(np.all((fp[:, -1] & 31) == 0), "MSB_FIVE_ZERO_PADDING_BITS")
    require(np.all(np.isfinite(mass)) and np.all((80 <= mass) & (mass <= 1400)), "MASS_NUMERICS")
    require(bitmap.all() and len(np.unique(rows)) == 4096
            and np.array_equal(rows, np.asarray(selection["selected_indices"], np.int64)), "ALL4096_COMPLETION_AND_SOURCE_ROWS")
    require(np.array_equal(order, np.argsort(mass, kind="stable")), "MASS_ORDER_STABLE_PERMUTATION")
    table = pq.read_table(data / "external_chebi3_4096.parquet", use_threads=False)
    require(table.num_rows == 4096 and table.select(source.column_names).equals(source.take(pa.array(rows))), "ALL4096_EXACT_SOURCE_PARQUET_JOIN")
    records = table.to_pylist()
    groups = []
    for i, record in enumerate(records):
        require(record["source"] == "ChEBI" and record["chebi_star"] == "3", "ALL4096_SOURCE_QUALITY")
        require(record["original_source_row"] == int(rows[i]), "ALL4096_ORIGINAL_ROW_MAPPING")
        require(record["computed_raw_key"] == record["inchikey14"] and re.fullmatch("[A-Z]{14}", record["inchikey14"]), "ALL4096_RAW_KEY_FORMAT_AND_JOIN")
        require(record["inchikey14"] not in old_keys and record["smiles"] not in old_smiles, "ALL4096_RAW_KEY_AND_EXACT_SMILES_NEW")
        require(record["computed_mass"] == float(mass[i]) and abs(record["monoisotopic_mass"] - mass[i]) <= 1e-6, "ALL4096_EXACT_MASS_ARRAY_JOIN")
        require(re.fullmatch("[a-f0-9]{64}", record["canonical_group"]), "ALL4096_GROUP_DIGEST_SCHEMA")
        groups.append(record["canonical_group"])
    require(len({r["computed_raw_key"] for r in records}) == 4096, "ALL4096_UNIQUE_RAW_KEYS")
    counts = Counter(groups)
    require(len(counts) == build["canonical_groups_selected"] == 4092, "WITHIN_SHARD_CANONICAL_GROUP_COUNT")
    require(np.array_equal(load("canary64_fp.npy", "uint8", (64, 1300)), fp[:64]), "CANARY64_FP_PREFIX_BYTE_PARITY")
    require(np.array_equal(load("canary64_mass.npy", "float64", (64,)), mass[:64]), "CANARY64_MASS_PREFIX_EXACT_PARITY")
    require(np.array_equal(load("canary64_source_rows.npy", "int64", (64,)), rows[:64]), "CANARY64_SOURCE_PREFIX_PARITY")
    canary_table = pq.read_table(data / "canary64_source.parquet", use_threads=False)
    require(canary_table.equals(table.slice(0, 64).select(source.column_names + ["canonical_group"])), "CANARY64_PARQUET_EXACT_PREFIX")
    gate = json.loads((data / "CANARY64_GATE.json").read_text())
    require(gate["numeric_and_disk_parity"] == "PASS" and gate["full_continuation_admitted"] is True
            and gate["reference_pool_fresh_after_profile_pool_closed"] is True, "CANARY64_GATE")
    forecast = forecast_budget(gate["baseline_original_chunk_seconds"], completed_rows=64,
                               elapsed_seconds=gate["forecast"]["elapsed_seconds"])
    require(forecast == gate["forecast"] and forecast["passes"], "CANARY64_CURRENT_FORECAST_ARITHMETIC")
    for i, record in enumerate(gate["instrumented_stage_records"]):
        require(record["row"] == i and record["mass"] == float(mass[i])
                and record["raw_key"] == records[i]["computed_raw_key"] and record["group"] == groups[i], "CANARY64_PROFILE_MASS_KEY_GROUP_JOIN")
    # Independently reload bytes and joins only. Molecular semantics are not re-evaluated.
    return {"status": "PASS_READ_ONLY_ALL4096_HASH_NUMERIC_AND_SOURCE_JOIN_AUDIT",
        "observed_utc": datetime.now(timezone.utc).isoformat(), "audit_seconds": time.monotonic() - started,
        "source_manifest_sha256": SOURCE_SHA, "build_receipt_sha256": BUILD_SHA,
        "owned_result_sha256": digest(run / "RESULT.json"), "current_input_pins": input_pins,
        "source_files_verified": len(manifest["files"]), "declared_outputs_verified": len(outputs),
        "declared_output_bytes": sum(pin["bytes"] for pin in outputs.values()),
        "rows": 4096, "raw_keys_unique_and_absent_old711705": 4096, "exact_smiles_absent_old711705": 4096,
        "canonical_group_digest_count": len(counts), "canonical_group_size_histogram": dict(Counter(counts.values())),
        "old512_proof_reused_with_all_current_source_input_runtime_pins": True,
        "full4096_fp_array_schema_and_zero_padding": True, "all4096_source_metadata_mass_rawkey_group_format_joins": True,
        "canary64_fp_mass_source_exact_full_prefix": True, "mass_order_is_stable_exact_permutation": True,
        "selected64_forecast_seconds": forecast["forecast_total_seconds"],
        "actual_resources": {key:result[key] for key in ["seconds", "aggregate_cpu_seconds", "sum_observed_rss_peak_bytes", "output_bytes_before_final_receipt"]},
        "runtime": build["runtime"], "pyarrow_version": build["pyarrow_version"], "psutil_version": result["psutil_version"],
        "scientific_limits": ["No fingerprint or molecule chemistry was rerun by this audit; all4096 FP semantics bind to original frozen executed producer and passed64 exact-reference gate", "Canonical-group molecular semantics bind to the unchanged executed metric/group sources; this audit checks every exported digest and rowjoin but does not recompute chemistry", "Metric novelty versus entire old711705 bank is not measured", "No training, completed assay, hidden-test coverage or score improvement is established"],
        "chemistry_model_assay_upload_push_or_native_submission": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("packet-root", "old-bank-root", "external-root", "receipt"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.packet_root.resolve(), args.old_bank_root.resolve(), args.external_root.resolve())
    with args.receipt.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": report["status"], "rows": report["rows"], "audit_seconds": report["audit_seconds"], "receipt_sha256": digest(args.receipt)}, sort_keys=True))
