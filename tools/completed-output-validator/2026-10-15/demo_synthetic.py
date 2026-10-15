#!/usr/bin/env python3
"""Demonstrate four validator cases using invented IDs and retained fake receipts.

Run: python3 -B demo_synthetic.py --destination NEW_DIRECTORY
The destination must not exist and its parent must exist. Nothing is deleted.
These fixtures are synthetic teaching material, never evidence of a native run.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

VALIDATOR_SHA = "2d214f73a14935f1fcaa9877d6e05d1f668bd4fc2e9d0975933d34edc59e4d5e"
BINDINGS_SHA = "4175116ccd23f865f1a4abfc797ed6a39a7fba5b62ad8a784adce9ae42d0af02"
CASES = (
    ("positive", None),
    ("tampered_csv_hash", "SUBMISSION_BYTE_HASH"),
    ("canary_finite_false", "EXACT_CANARY_RECEIPT"),
    ("swapped_ids_rebound_hash", "SUBMISSION_ID_ORDER"),
)
MARKER = {
    "synthetic_only": True,
    "native_evidence": False,
    "not_for_submission": True,
    "description": "Invented IDs, predictions and runtime receipts for a validator demonstration.",
}


def need(ok, code):
    if not ok:
        raise ValueError(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def create_destination(value):
    path = Path(value)
    need(".." not in path.parts, "DESTINATION_PATH_ESCAPE")
    path = path.absolute()
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise ValueError("DESTINATION_ALREADY_EXISTS")
    for parent in path.parents:
        mode = parent.lstat().st_mode
        need(stat.S_ISDIR(mode) and not stat.S_ISLNK(mode), "DESTINATION_PARENT_REQUIRED")
    path.mkdir(mode=0o700)
    write_new(path / "SYNTHETIC_ONLY.json", encode(MARKER))
    return path


def load_validator():
    here = Path(__file__).resolve().parent
    source = here / "validate_completed_output.py"
    bindings_path = here / "validation_bindings.json"
    source_raw = source.read_bytes()
    bindings_raw = bindings_path.read_bytes()
    need(digest(source_raw) == VALIDATOR_SHA, "REVIEWED_VALIDATOR_DRIFT")
    need(digest(bindings_raw) == BINDINGS_SHA, "REVIEWED_BINDINGS_DRIFT")
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("synthetic_artifact_validator", source)
    need(spec is not None and spec.loader is not None, "VALIDATOR_IMPORT_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, bindings_path, json.loads(bindings_raw)


def make_fixture(destination, name, binding):
    root = destination / name
    root.mkdir(mode=0o700)
    write_new(root / "SYNTHETIC_ONLY.json", encode(MARKER))
    work = root / "casmi_v6_native_once"
    work.mkdir(mode=0o700)
    policy = json.loads(binding["native_policy_text"])
    config = copy.deepcopy(policy["fixed_config"])
    for label, record in config["files"].items():
        route = policy["file_routes"][label]
        allowed = policy["mounts"][route["mount"]]["allowed_roots"][0]
        # These are policy strings. This demo never opens the native input paths.
        record["path"] = allowed + "/" + route["relative_path"]
    runtime = {key: "synthetic-" + key for key in
               ("python", "numpy", "torch", "pandas", "pyarrow", "pillow")}
    config.update(runtime=runtime,
                  competition_root=policy["mounts"]["competition"]["allowed_roots"][0],
                  canary_wall_seconds=299, wall_seconds=1799)
    config_raw = encode(config)
    config_sha = digest(config_raw)
    sources = binding["source_sha256"]
    policy_sha = binding["native_policy_sha256"]
    start = 1000.0
    sample = b"molecule_id,smiles\nINVENTED_ALPHA,\nINVENTED_BETA,\n"
    submission = b"molecule_id,smiles\nINVENTED_ALPHA,CC;CO\nINVENTED_BETA,CN\n"
    marker = {
        "status": "CONSUMED_BEFORE_PREFLIGHT", "policy_sha256": policy_sha,
        "source_sha256": sources, "global_start_monotonic": start,
        "canary_deadline_monotonic": start + 300, "total_deadline_monotonic": start + 1800,
        "retry_authorized": False, "competition_submission_authorized": False,
    }
    preflight = {
        "status": "PASS_PREFLIGHT_OBSERVATIONS_ONLY", "policy_sha256": policy_sha,
        "source_sha256": sources, "resolved_config_sha256": config_sha, "runtime": runtime,
        "declared_platform_image": policy["immutable_platform_image"],
        "image_attested_by_preflight": False, "native_compatibility_before_driver_canary": "UNKNOWN",
        "global_start_monotonic": start, "preflight_elapsed_seconds": 0.9,
        "driver_remaining_canary_seconds": 299, "driver_remaining_total_seconds": 1799,
        "same_pid_exec": True, "private_rows_or_arrays_published": False, "retry_authorized": False,
    }
    science = {
        "consumed_before_input_or_model_load": True,
        "source_sha256": sources["native_canary_and_infer.source.py"], "config_sha256": config_sha,
        "canary_dispatches": 1, "conditional_inference": True,
        "retry_authorized": False, "official_submission": False,
    }
    canary = copy.deepcopy(binding["exact_canary_receipt"])
    result = {
        "status": "COMPLETE_PURE_V6_NATIVE_INFERENCE_NO_SCORE",
        "source_sha256": sources["native_canary_and_infer.source.py"], "config_sha256": config_sha,
        "checkpoint_sha256": config["files"]["checkpoint"]["sha256"],
        "clean_coordinate_projection_performed": False,
        "input_sha256": {label: record["sha256"] for label, record in config["files"].items()},
        "competition_input_sha256": {
            "test.parquet": digest(b"SYNTHETIC PAYLOAD: NOT A PARQUET FILE"),
            "sample_submission.csv": digest(sample),
        },
        "diagnostics": {"molecules": 2, "empty_10ppm": 0, "spectrum_fallbacks": 0,
                        "candidate_rows_scored": 3},
        "submission_bytes": len(submission), "submission_sha256": digest(submission),
        "runtime": {"torch": runtime["torch"], "numpy": runtime["numpy"],
                    "rdkit": "2026.03.3", "python": runtime["python"], "device": "Synthetic T4"},
        "seconds": 10.0, "peak_rss_bytes": 1048576, "local_assay_gain_transferred": False,
        "official_submission": False, "official_score": None, "retry_authorized": False,
    }
    for key in ("candidate_bank_policy", "candidate_policy", "spectrum_policy", "fallback_policy"):
        result[key] = config[key]
    wrapper = {
        "status": "COMPLETE_ONE_CHILD_WITH_CONTINUOUS_PREFLIGHT_BUDGET",
        "source_sha256": sources, "policy_sha256": policy_sha,
        "peak_sampled_child_rss_bytes": 1048576, "rss_poll_seconds": 0.1,
        "global_start_monotonic": start, "prepublication_elapsed_seconds": 12.0,
        "canary_pass_observed_within_global_deadline": True, "same_pid_preflight_exec": True,
        "hard_memory_isolation_claimed": False, "retry_authorized": False,
        "competition_submission_authorized": False,
    }
    if name == "tampered_csv_hash":
        # Same length; only the hash gate should reject this case.
        submission = submission.replace(b"CC;CO", b"CN;CO")
    elif name == "canary_finite_false":
        canary["finite"] = False
    elif name == "swapped_ids_rebound_hash":
        # Rebind size and hash so rejection exercises order, not integrity.
        submission = b"molecule_id,smiles\nINVENTED_BETA,CN\nINVENTED_ALPHA,CC;CO\n"
        result["submission_bytes"] = len(submission)
        result["submission_sha256"] = digest(submission)
    for filename, value in {
        "V6_NATIVE_WRAPPER_ONE_ATTEMPT.json": marker, "PREFLIGHT_RESULT.json": preflight,
        "V6_NATIVE_SCIENCE_ONE_ATTEMPT.json": science, "CANARY.json": canary,
        "RESULT.json": result, "WRAPPER_RESULT.json": wrapper,
    }.items():
        write_new(work / filename, encode(value))
    write_new(work / "PREFLIGHT_POLICY.json", binding["native_policy_text"].encode("utf-8"))
    write_new(work / "NATIVE_CONFIG.json", config_raw)
    write_new(root / "sample.csv", sample)
    write_new(root / "submission.csv", submission)
    return root


def run(destination_text):
    validator, bindings_path, binding = load_validator()
    destination = create_destination(destination_text)
    outcomes = []
    for name, expected_rejection in CASES:
        root = make_fixture(destination, name, binding)
        try:
            result = validator.validate(root, root / "sample.csv", bindings_path)
        except ValueError as error:
            need(expected_rejection is not None and str(error) == expected_rejection,
                 "UNEXPECTED_VALIDATION_REJECTION")
            outcomes.append({"case": name, "status": "EXPECTED_REJECTION", "code": expected_rejection})
        else:
            need(expected_rejection is None and result["status"] ==
                 "PASS_COMPLETED_OUTPUT_ARTIFACTS_NO_OFFICIAL_SCORE" and result["rows"] == 2
                 and result["sample_hash_and_exact_id_order_verified"] is True,
                 "UNEXPECTED_VALIDATION_ACCEPTANCE")
            outcomes.append({"case": name, "status": "PASS"})
    aggregate = {"status": "PASS_SYNTHETIC_DEMO", "synthetic_only": True,
                 "native_evidence": False, "cases": outcomes, "fixtures_retained": True,
                 "official_score": None, "validator_sha256": VALIDATOR_SHA,
                 "bindings_sha256": BINDINGS_SHA}
    write_new(destination / "DEMO_RESULT.json", encode(aggregate))
    return aggregate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    try:
        result = run(args.destination)
    except BaseException:
        # No exception text or local paths are printed. Partial fixtures remain.
        print(json.dumps({"status": "HOLD_SYNTHETIC_DEMO", "synthetic_only": True,
                          "native_evidence": False, "partial_fixtures_preserved": True}), flush=True)
        return 2
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
