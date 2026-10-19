"""Owned Mac-only 64-row gate and conditional 4096-row CPU shard.

Apache-2.0 source. This program performs no model training or score assay.
"""
from __future__ import annotations
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

WALL_SECONDS = 1800.0
CPU_SECONDS = 3600.0
RSS_BYTES = 4 << 30
OUTPUT_BYTES = 512 << 20
SOURCE_NAMES = {"build_chebi3_shard.py", "run_owned_chebi3_shard.py", "selection_and_budget.py",
    "build_external_fp_shard.py", "metric_distinct.py", "group_identity.py", "DATA-LICENSE.md",
    "LICENSE-SOURCE", "PUBLIC_SOURCE_BINDINGS.json", "README.md", "test_selection_and_budget.py",
    "test_owned_chebi3_admission.py", "requirements.txt"}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def verify_sources(manifest, root):
    if set(manifest) != {"files", "scope"} or set(manifest["files"]) != SOURCE_NAMES:
        return False
    for name, pin in manifest["files"].items():
        path = root / name
        if set(pin) != {"bytes", "sha256"} or not path.is_file():
            return False
        if path.stat().st_size != pin["bytes"] or digest(path) != pin["sha256"]:
            return False
    return True


def admission_reason(wall, cpu, rss, size):
    if wall >= WALL_SECONDS - 20:
        return "WALL_LIMIT"
    if cpu > CPU_SECONDS:
        return "CPU_TIME_LIMIT"
    if rss > RSS_BYTES:
        return "SUMMED_RSS_LIMIT"
    if size > OUTPUT_BYTES - 65536:
        return "OWNED_OUTPUT_LIMIT"
    return None


def own_members(psutil, group):
    result = []
    for process in psutil.process_iter(["pid", "status"]):
        try:
            if os.getpgid(process.pid) == group and process.info["status"] != psutil.STATUS_ZOMBIE:
                result.append(process)
        except (ProcessLookupError, PermissionError, psutil.NoSuchProcess):
            continue
    return result


def total_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def receipt_is_complete(receipt):
    return (isinstance(receipt, dict)
        and receipt.get("status") == "COMPLETE_4096_AWAITING_WRAPPER"
        and receipt.get("rows") == 4096 and receipt.get("canary_rows") == 64
        and receipt.get("actual_selected_raw_key_new") == 4096
        and receipt.get("fingerprints_from_unchanged_baseline_only") is True
        and receipt.get("all_numeric_and_parquet_reloads_exact") is True
        and receipt.get("no_model_training_assay_hidden_test") is True)


def main():
    start = time.monotonic()
    parser = argparse.ArgumentParser()
    for name in ("old-bank-root", "external-root", "old-proof-root", "run-root", "source-manifest"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    args = parser.parse_args()
    if sys.platform != "darwin" or (os.cpu_count() or 0) < 2:
        raise RuntimeError("MAC_ONLY_TWO_CPU_WORKER_ADMISSION")
    root = Path(__file__).resolve().parent
    if digest(args.source_manifest) != args.source_manifest_sha256:
        raise RuntimeError("SOURCE_MANIFEST_SHA256")
    manifest = json.loads(args.source_manifest.read_text())
    if not verify_sources(manifest, root):
        raise RuntimeError("SOURCE_IDENTITY")
    import psutil
    if psutil.__version__ != "7.2.2":
        raise RuntimeError("PSUTIL_DEPENDENCY_PIN")
    run = args.run_root.resolve()
    for source in (root, args.old_bank_root.resolve(), args.external_root.resolve(), args.old_proof_root.resolve()):
        # A run inside this source packet is allowed, but never overlapping an input.
        if source == run or source != root and (source in run.parents or run in source.parents):
            raise RuntimeError("INPUT_OUTPUT_ROOTS_MUST_BE_SEPARATE")
    run.mkdir(exist_ok=False)
    data = run / "data"
    data.mkdir(exist_ok=False)
    env = dict(os.environ)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
        env[name] = "1"
    env["CASMI_CHEBI3_OWNED_WRAPPER"] = "v1"
    command = [sys.executable, "-B", str(root / "build_chebi3_shard.py"),
        "--old-bank-root", str(args.old_bank_root.resolve()), "--external-root", str(args.external_root.resolve()),
        "--old-proof-root", str(args.old_proof_root.resolve()), "--output-root", str(data)]
    write_json(run / "ADMISSION.json", {"source_manifest_sha256": args.source_manifest_sha256,
        "chemistry_worker_processes": 2, "numerical_threads_per_process": 1,
        "wall_seconds": WALL_SECONDS, "aggregate_cpu_seconds": CPU_SECONDS,
        "sum_observed_rss_bytes": RSS_BYTES, "owned_output_bytes": OUTPUT_BYTES,
        "driver_seconds": 1760, "driver_io_reserve_seconds": 120,
        "macos_cpu_affinity": "Unavailable; two chemistry workers and aggregate CPU monitoring, not hard two-core affinity.",
        "full_continuation": "Only selected64 exact numeric/reload/forecast PASS admits remaining4032 in same owned job",
        "root_must_confirm_other_two_cpu_job_terminal": True})
    write_json(run / "ATTEMPT_CONSUMED.json", {"coordinator": "/root",
        "attempt": "CASMI_CHEBI3_RAW_NEW_4096_SELECTED64_GATE_20261019",
        "source_manifest_sha256": args.source_manifest_sha256, "retry_authorized": False,
        "native_notebook_push_or_competition_submission": False})
    peak = 0; cpu_max = {}; reason = None; remaining = []
    self_proc = psutil.Process(os.getpid())
    prior_child_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    child = None; group = None; returncode = None
    with (run / "child.stdout.txt").open("x") as stdout, (run / "child.stderr.txt").open("x") as stderr:
        try:
            child = subprocess.Popen(command, cwd=root, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            group = child.pid
            write_json(run / "CHILD_HANDLE.json", {"pid": child.pid, "owned_process_group": group,
                "root_observes_same_handle_until_terminal": True,
                "source_manifest_sha256": args.source_manifest_sha256})
            while True:
                members = own_members(psutil, group)
                rss = 0
                for process in [self_proc] + members:
                    try:
                        rss += process.memory_info().rss
                        cpu = process.cpu_times()
                        key = (process.pid, process.create_time())
                        cpu_max[key] = max(cpu_max.get(key, 0.0), cpu.user + cpu.system)
                    except psutil.NoSuchProcess:
                        continue
                peak = max(peak, rss)
                reason = admission_reason(time.monotonic() - start, sum(cpu_max.values()), rss, total_bytes(run))
                if reason is not None or child.poll() is not None:
                    break
                time.sleep(0.1)
        except BaseException as exc:
            reason = "WRAPPER_EXCEPTION:" + type(exc).__name__
        finally:
            if child is not None:
                try:
                    if own_members(psutil, group):
                        os.killpg(group, signal.SIGTERM)
                        until = time.monotonic() + 5
                        while time.monotonic() < until and own_members(psutil, group):
                            time.sleep(0.1)
                        if own_members(psutil, group):
                            os.killpg(group, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    returncode = child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    returncode = None
                    reason = reason or "LEADER_NOT_REAPED"
                remaining = [process.pid for process in own_members(psutil, group)]
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    self_cpu = self_proc.cpu_times()
    final_cpu = max(sum(cpu_max.values()), usage.ru_utime + usage.ru_stime
        - prior_child_usage.ru_utime - prior_child_usage.ru_stime + self_cpu.user + self_cpu.system)
    elapsed = time.monotonic() - start
    size = total_bytes(run)
    marker = data / "BUILD_COMPLETE_AWAITING_WRAPPER.json"
    receipt_contract = False
    if marker.is_file():
        try:
            receipt_contract = receipt_is_complete(json.loads(marker.read_text()))
        except (ValueError, TypeError, AttributeError):
            reason = reason or "BUILD_RECEIPT_PARSE"
    if reason is None and returncode != 0:
        reason = "CHILD_EXIT_NONZERO"
    if reason is None and not receipt_contract:
        reason = "BUILD_RECEIPT_CONTRACT"
    if reason is None and not verify_sources(manifest, root):
        reason = "SOURCE_DRIFT_DURING_RUN"
    if reason is None:
        reason = admission_reason(elapsed, final_cpu, peak, size)
    if reason is None and remaining:
        reason = "OWNED_PROCESS_GROUP_NOT_EMPTY"
    passed = (reason is None and returncode == 0 and not remaining and receipt_contract
        and elapsed <= WALL_SECONDS and final_cpu <= CPU_SECONDS and peak <= RSS_BYTES
        and size <= OUTPUT_BYTES - 65536)
    result = {"status": "COMPLETE_CHEBI3_4096_SHARD" if passed else "STOPPED_UNPROMOTABLE",
        "child_returncode": returncode, "reason": reason, "seconds": elapsed,
        "aggregate_cpu_seconds": final_cpu, "sum_observed_rss_peak_bytes": peak,
        "rss_sampling_seconds": 0.1, "output_bytes_before_final_receipt": size,
        "remaining_owned_group_pids": remaining, "source_manifest_sha256": args.source_manifest_sha256,
        "build_receipt_sha256": digest(marker) if marker.is_file() else None,
        "root_input_identity_after_verified_by_child": passed,
        "selected64_canary_then_conditional4096_same_job": True,
        "model_or_training_or_assay": False, "cpu_affinity_not_supported_on_macos": True}
    result["psutil_version"] = psutil.__version__
    write_json(run / "RESULT.json", result)
    write_json(run / ("COMPLETE.json" if passed else "STOPPED_UNPROMOTABLE.json"), result)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
