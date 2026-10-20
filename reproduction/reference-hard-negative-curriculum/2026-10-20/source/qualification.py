"""Portable completed-tree checks. SPDX-License-Identifier: Apache-2.0

Reading a retained partial tree is never permission to sample it.
"""
import hashlib
import json
from pathlib import Path

PASS = "PASS_REFERENCE_CURRICULUM_MECHANICS_NO_MODEL_QUALITY_CLAIM"
COMPLETE = "COMPLETE_REFERENCE_CURRICULUM_PENDING_OWNED_RESOURCE_QUALIFICATION"
OUTPUTS = {"CANARY64.json", "anchors.csv", "negative_pairs.csv", "excluded_source_pairs.csv",
           "SPLIT_EVIDENCE.json", "CURRICULUM_COMPLETE.json"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "missing/symlink qualified artifact " + path.name)
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def source_pin(source):
    manifest_path = source / "SOURCE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_bytes())
    for name, expected in manifest["files"].items():
        require(file_pin(source / name) == expected, "consumer source mismatch " + name)
    return file_pin(manifest_path)["sha256"]


def expected_identity(contract):
    return {"atlas_commit": contract["atlas_commit"], "structure_commit": contract["structure_commit"],
            "selected_bits": 10395, "packed_bytes_per_row": 1300}


def checked_output_tree(data):
    """Exact portable data/ layout; no original absolute paths are consulted."""
    manifest = json.loads((data / "OUTPUT_MANIFEST.json").read_bytes())
    require(set(manifest["files"]) == OUTPUTS, "qualified output manifest exact file set")
    for name, expected in manifest["files"].items():
        require(file_pin(data / name) == expected, "qualified output hash mismatch " + name)
    completion = json.loads((data / "CURRICULUM_COMPLETE.json").read_bytes())
    canary = json.loads((data / "CANARY64.json").read_bytes())
    require(canary["status"] == "PASS64_NUMERIC_MECHANICS_ONLY" and canary["anchors"] == 64,
            "qualified64 canary required")
    observed = canary["observed_actual_bits_and_numeric_windows"]
    require(observed["collision_anchor_rows"] and observed["nonempty_noncollision_anchor_rows"] and
            observed["empty_anchor_rows"], "qualified real canary treatment coverage required")
    require(len(canary["anchor_rows"]) == len(set(canary["anchor_rows"])) == 64, "64 distinct qualified anchors")
    return completion


def checked_headers(result, completion, contract, input_hash, source_hash):
    """Pure receipt/identity checks, also usable by invented mechanics controls."""
    require(result.get("schema") == "casmi-reference-curriculum-owned-result/2" and
            result.get("status") == PASS, "owning wrapper PASS required; partial/failed tree is unusable")
    require(result.get("child_returncode") == 0 and result.get("owned_process_group_clean") is True and
            result.get("source_bytes_unchanged") is True, "owning wrapper clean completion required")
    require(result.get("seconds", float("inf")) <= 120 and
            result.get("conservative_RSS_peaks_sum_bytes", 161 << 20) <= 160 << 20 and
            result.get("aggregate_CPU_seconds", float("inf")) <= 240, "owning resource qualification required")
    require(result.get("source_manifest_sha256") == source_hash and
            result.get("input_contract_sha256") == input_hash, "owning source/input identity")
    identity = expected_identity(contract)
    require(result.get("reference_identity") == identity and completion.get("reference_identity") == identity,
            "required immutable reference identity")
    require(completion.get("schema") == "casmi-reference-curriculum-completion/2" and
            completion.get("status") == COMPLETE and completion.get("input_contract_sha256") == input_hash,
            "actual R2 child completion required")
    require(completion.get("anchors") == 4096 and completion.get("source_pairs") == 3800 and
            completion.get("identical_target_pairs_excluded") == 96 and
            completion.get("all4096_anchors_processed_exactly_once") is True and
            completion.get("canary64_real_collision_noncollision_empty_coverage") is True and
            completion.get("canary64_passed_and_continued") is True and
            completion.get("all_source_pairs_validated_against_packed_targets") is True,
            "completed full-run numeric and coverage identity")


def load_qualified_run(run_root, source):
    """Fail closed before opening a sampling pool; accepts a relocated completed tree."""
    run_root, source = Path(run_root), Path(source)
    result = json.loads((run_root / "RESULT.json").read_bytes())
    require(result.get("status") == PASS, "owning wrapper PASS required before sampling")
    data = run_root / "data"
    require(file_pin(data / "OUTPUT_MANIFEST.json") == result.get("output_manifest_pin"),
            "owning receipt must bind actual output manifest")
    completion = checked_output_tree(data)
    require(file_pin(data / "CURRICULUM_COMPLETE.json") == result.get("child_completion_pin"),
            "owning receipt must bind actual child completion")
    contract = json.loads((source / "INPUT_CONTRACT.json").read_bytes())
    checked_headers(result, completion, contract, file_pin(source / "INPUT_CONTRACT.json")["sha256"], source_pin(source))
    return data
