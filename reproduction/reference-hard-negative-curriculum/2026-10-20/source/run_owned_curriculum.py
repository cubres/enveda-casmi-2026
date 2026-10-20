"""One owned CPU-only curriculum attempt. SPDX-License-Identifier: Apache-2.0

Root must separately admit this unexecuted source. No network/native/model.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
from qualification import checked_headers, checked_output_tree, expected_identity, file_pin

SOURCE = Path(__file__).resolve().parent
CONTROL = SOURCE.parent
EXPERIMENT = "casmi-reference-curriculum-r3-160mib"
ONCE = CONTROL / "ROOT_CURRICULUM_R3_160MIB_ONCE_CONSUMED.json"
ADMISSION = CONTROL / "ROOT_REVISED_160MIB_ADMISSION.json"
WALL_SECONDS, RSS_BYTES = 120.0, 160 << 20


def dump(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def source_binding():
    path = SOURCE / "SOURCE_MANIFEST.json"
    value = json.loads(path.read_bytes())
    for name, expected in value["files"].items():
        current = SOURCE / name
        if not current.is_file() or current.is_symlink():
            raise ValueError("missing/symlink source " + name)
        raw = current.read_bytes()
        if {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()} != expected:
            raise ValueError("source pin mismatch " + name)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def revised_admission(binding):
    """No new once may be consumed without a distinct actual human/root admission."""
    revision = json.loads((SOURCE / "REVISION_CONTRACT.json").read_bytes())
    for relative, expected in revision["preserved_prior_files"].items():
        if file_pin(CONTROL.parent / relative) != expected:
            raise ValueError("preserved prior failure/marker drift: " + relative)
    if not ADMISSION.is_file() or ADMISSION.is_symlink():
        raise ValueError("distinct actual 160 MiB root/human admission required before attempt")
    admission = json.loads(ADMISSION.read_bytes())
    required = {"schema": "casmi-curriculum-revised-attempt-admission/1", "experiment": EXPERIMENT,
                "decision": "ADMIT_ONE_DISTINCT_REVISED_ATTEMPT", "source_manifest_sha256": binding,
                "input_contract_sha256": file_pin(SOURCE / "INPUT_CONTRACT.json")["sha256"],
                "limits": revision["prospective_limits"],
                "prior_failed_result_sha256": revision["preserved_prior_files"]["r2/ROOT_OWNED_CURRICULUM_RUN/RESULT.json"]["sha256"],
                "prior_consumed_marker_sha256": revision["preserved_prior_files"]["ROOT_CURRICULUM_ONCE_CONSUMED.json"]["sha256"]}
    for name, expected in required.items():
        if admission.get(name) != expected:
            raise ValueError("revised admission mismatch: " + name)
    review = admission.get("root_actual_review", {})
    human = admission.get("human_budget_exception", {})
    if not (review.get("decision") == "PASS_REVISED_SOURCE" and
            review.get("source_manifest_sha256") == binding and
            isinstance(review.get("review_reference"), str) and review["review_reference"].strip()):
        raise ValueError("actual root source review evidence required")
    if not (human.get("decision") == "AUTHORIZE_ONE_DISTINCT_160MIB_ATTEMPT" and
            isinstance(human.get("human_message_reference"), str) and human["human_message_reference"].strip()):
        raise ValueError("explicit human 160 MiB exception evidence required")
    return file_pin(ADMISSION)


def own_rss_peak():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def reaped_children_rss_peak():
    value = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def owned_cpu_seconds():
    own, children = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime


def child_rss(pid):
    # Child imports only audited stdlib and creates no threads/processes.
    result = subprocess.run(["ps", "-o", "pid=,pgid=,rss=", "-p", str(pid)],
                            capture_output=True, text=True, timeout=2, check=False)
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 3 and int(fields[0]) == pid and int(fields[1]) == pid:
            return int(fields[2]) * 1024
    return 0


def group_clean(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    return False


def stop_owned(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-dir", type=Path, required=True)
    parser.add_argument("--structure-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    if sys.version_info < (3, 10) or sys.platform not in ("darwin", "linux"):
        raise ValueError("Python3.10+ on macOS/Linux required")
    if not args.atlas_dir.is_dir() or not args.structure_dir.is_dir() or args.out.exists() or not args.out.parent.is_dir():
        raise ValueError("existing input roots and fresh output with existing parent required")
    binding = source_binding()
    admission_pin = revised_admission(binding)
    if own_rss_peak() >= 28 << 20:
        raise ValueError("wrapper baseline RSS leaves insufficient conservative reserve")
    marker = {"status": "CONSUMED_BEFORE_ONE_OWNED_CPU_CHILD_NO_RETRY", "source_manifest_sha256": binding,
              "experiment": EXPERIMENT, "distinct_actual_admission_pin": admission_pin,
              "wall_seconds": WALL_SECONDS, "whole_RSS_bytes": RSS_BYTES,
              "CPU_configured_active_tasks_max": 2, "numerical_workers": 1,
              "CPU_scope": "One single-thread scientific child plus wrapper/one serial ps observer; no hard affinity claim",
              "aggregate_CPU_seconds_limit": 240, "native_GPU_model_spectra_calls": 0,
              "atlas_directory": str(args.atlas_dir.resolve()), "structure_directory": str(args.structure_dir.resolve()),
              "output_directory": str(args.out.absolute()), "Python_version": sys.version}
    fd = os.open(ONCE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(marker, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    args.out.mkdir()
    env = os.environ.copy()
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS",
                 "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
        env[name] = "1"
    env.update({"CASMI_CURRICULUM_OWNED": "1", "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1", "CUDA_VISIBLE_DEVICES": ""})
    process, reason, peak, observer_peak = None, None, 0, 0
    result = {"schema": "casmi-reference-curriculum-owned-result/2",
              "status": "FAILED_CONSUMED_UNQUALIFIED", "attempt_remains_consumed": True,
              "experiment": EXPERIMENT, "distinct_actual_admission_pin": admission_pin,
              "wall_limit_seconds": WALL_SECONDS, "whole_RSS_limit_bytes": RSS_BYTES,
              "source_manifest_sha256": binding, "no_training_or_model_performed": True}
    try:
        with (args.out / "child.log").open("xb") as log:
            process = subprocess.Popen([sys.executable, "-B", "-u", str(SOURCE / "build_curriculum.py"),
                                        "--atlas-dir", str(args.atlas_dir.resolve()),
                                        "--structure-dir", str(args.structure_dir.resolve()),
                                        "--out", str(args.out / "data")], env=env, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            while process.poll() is None:
                peak = max(peak, child_rss(process.pid))
                observer_peak = max(observer_peak, reaped_children_rss_peak())
                if time.monotonic() - started > 110:
                    reason = "110s child ceiling leaves10s cleanup reserve"
                elif peak + own_rss_peak() + observer_peak > RSS_BYTES:
                    reason = "conservative whole owned RSS exceeded"
                elif owned_cpu_seconds() > 235:
                    reason = "aggregate CPU seconds preserves cleanup reserve"
                if reason:
                    stop_owned(process)
                    break
                time.sleep(.05)
            code = process.wait(timeout=3)
        receipt = args.out / "data/CURRICULUM_COMPLETE.json"
        child = json.loads(receipt.read_bytes()) if receipt.is_file() else None
        contract = json.loads((SOURCE / "INPUT_CONTRACT.json").read_bytes())
        identity = expected_identity(contract)
        input_hash = file_pin(SOURCE / "INPUT_CONTRACT.json")["sha256"]
        # After wait, RUSAGE_CHILDREN also covers the main child's true OS peak.
        # Reusing that maximum for the serial observer overcounts safely; it
        # prevents unaccounted ps RSS or a fast child escaping external samples.
        observer_peak = max(observer_peak, reaped_children_rss_peak())
        peak = max(peak, observer_peak, int(child["peak_RSS_bytes"]) if child else 0)
        clean, same = group_clean(process.pid), source_binding() == binding
        elapsed = time.monotonic() - started
        passed = (code == 0 and reason is None and clean and same and child is not None and
                  child["status"] == "COMPLETE_REFERENCE_CURRICULUM_PENDING_OWNED_RESOURCE_QUALIFICATION" and
                  child["schema"] == "casmi-reference-curriculum-completion/2" and
                  child["anchors"] == 4096 and child["identical_target_pairs_excluded"] == 96 and
                  child["reference_identity"] == identity and child["input_contract_sha256"] == input_hash and
                  peak + own_rss_peak() + observer_peak <= RSS_BYTES and elapsed <= WALL_SECONDS and
                  owned_cpu_seconds() <= 240)
        result.update({"status": "PASS_REFERENCE_CURRICULUM_MECHANICS_NO_MODEL_QUALITY_CLAIM" if passed else result["status"],
                       "reason": reason, "child_returncode": code, "owned_process_group_clean": clean,
                       "source_bytes_unchanged": same, "peak_child_RSS_bytes": peak,
                       "peak_wrapper_RSS_bytes": own_rss_peak(), "conservative_observer_RSS_peak_bytes": observer_peak,
                       "conservative_RSS_peaks_sum_bytes": peak + own_rss_peak() + observer_peak,
                       "aggregate_CPU_seconds": owned_cpu_seconds(),
                       "seconds": elapsed, "child_status": child["status"] if child else None,
                       "input_contract_sha256": input_hash, "reference_identity": identity})
        if passed:
            checked_output_tree(args.out / "data")
            result["output_manifest_pin"] = file_pin(args.out / "data/OUTPUT_MANIFEST.json")
            result["child_completion_pin"] = file_pin(receipt)
            result.update({"seconds": time.monotonic() - started,
                           "peak_wrapper_RSS_bytes": own_rss_peak(),
                           "conservative_RSS_peaks_sum_bytes": peak + own_rss_peak() + observer_peak,
                           "aggregate_CPU_seconds": owned_cpu_seconds()})
            checked_headers(result, child, contract, input_hash, binding)
    except BaseException as exc:
        if process is not None:
            stop_owned(process)
        result.update({"status": "FAILED_CONSUMED_UNQUALIFIED", "reason": type(exc).__name__ + ": " + str(exc),
                       "seconds": time.monotonic() - started})
    dump(args.out / "RESULT.json", result)
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "PASS_REFERENCE_CURRICULUM_MECHANICS_NO_MODEL_QUALITY_CLAIM":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
