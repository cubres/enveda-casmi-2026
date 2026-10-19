"""macOS canary only: two chemistry workers, 300s wall, 600 CPU-s, 4GiB RSS.

No full continuation, launch, model, assay or publication. Apache-2.0 source.
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

WALL_SECONDS = 300.0
CPU_SECONDS = 600.0
RSS_BYTES = 4 << 30
OUTPUT_BYTES = 64 << 20
SOURCE_NAMES = {"canary_macos.py", "run_owned_macos_canary.py", "build_external_fp_shard.py",
    "metric_distinct.py", "group_identity.py", "DATA-LICENSE.md", "LICENSE-SOURCE",
    "PUBLIC_SOURCE_BINDINGS.json", "README.md", "test_macos_admission.py", "DOWNLOAD_PLAN.json"}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False); f.write("\n")


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
    if size > OUTPUT_BYTES:
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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--old-bank-root", type=Path, required=True)
    p.add_argument("--external-root", type=Path, required=True)
    p.add_argument("--run-root", type=Path, required=True)
    p.add_argument("--source-manifest", type=Path, required=True)
    p.add_argument("--source-manifest-sha256", required=True)
    args = p.parse_args()
    if sys.platform != "darwin" or (os.cpu_count() or 0) < 2:
        raise RuntimeError("MAC_ONLY_TWO_CPU_WORKER_ADMISSION")
    root = Path(__file__).resolve().parent
    if digest(args.source_manifest) != args.source_manifest_sha256:
        raise RuntimeError("SOURCE_MANIFEST_SHA256")
    if not verify_sources(json.loads(args.source_manifest.read_text()), root):
        raise RuntimeError("SOURCE_IDENTITY")
    run = args.run_root.resolve()
    for source in (args.old_bank_root.resolve(), args.external_root.resolve()):
        if source == run or source in run.parents or run in source.parents:
            raise RuntimeError("INPUT_OUTPUT_ROOTS_MUST_BE_SEPARATE")
    run.mkdir(exist_ok=False); data = run / "data"; data.mkdir(exist_ok=False)
    import psutil
    env = dict(os.environ)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
        env[name] = "1"
    env["CASMI_MAC_CANARY_OWNED_WRAPPER"] = "v1"
    command = [sys.executable, "-B", str(root / "canary_macos.py"),
        "--old-bank-root", str(args.old_bank_root.resolve()),
        "--external-root", str(args.external_root.resolve()), "--output-root", str(data)]
    write_json(run / "ADMISSION.json", {"source_manifest_sha256": args.source_manifest_sha256,
        "chemistry_worker_processes": 2, "numerical_threads_per_process": 1,
        "wall_seconds": WALL_SECONDS, "aggregate_cpu_seconds": CPU_SECONDS,
        "sum_observed_rss_bytes": RSS_BYTES, "owned_output_bytes": OUTPUT_BYTES,
        "macos_cpu_affinity": "Unavailable; two chemistry workers and aggregate CPU-time monitoring, not a hard two-core affinity claim.",
        "full_continuation": False, "root_must_confirm_other_two_cpu_job_terminal": True})
    write_json(run / "ATTEMPT_CONSUMED.json", {"coordinator": "/root",
        "attempt": "CASMI_EXTERNAL_MAC_OLD512_NEW512_20261019",
        "source_manifest_sha256": args.source_manifest_sha256,
        "retry_authorized": False, "full_continuation": False,
        "native_notebook_push_or_competition_submission": False})
    start = time.monotonic(); peak = 0; cpu_max = {}; reason = None; remaining = []
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
                    returncode = None; reason = reason or "LEADER_NOT_REAPED"
                remaining = [process.pid for process in own_members(psutil, group)]
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    self_cpu = self_proc.cpu_times()
    final_cpu = max(sum(cpu_max.values()),
        usage.ru_utime + usage.ru_stime - prior_child_usage.ru_utime - prior_child_usage.ru_stime
        + self_cpu.user + self_cpu.system)
    elapsed = time.monotonic() - start; size = total_bytes(run)
    marker = data / "CANARY_COMPLETE_AWAITING_WRAPPER.json"
    receipt_contract = False
    if marker.is_file():
        try:
            receipt = json.loads(marker.read_text())
            receipt_contract = receipt.get("status") == "MAC_512_OLD_512_NEW_COMPLETE_AWAITING_WRAPPER" and receipt.get("old_rows") == receipt.get("new_rows") == 512 and receipt.get("full_continuation") is False and receipt.get("model_or_training_or_assay_or_hidden_test") is False
        except (ValueError, TypeError, AttributeError):
            reason = reason or "CANARY_RECEIPT_PARSE"
    if reason is None and returncode != 0:
        reason = "CHILD_EXIT_NONZERO"
    if reason is None and not receipt_contract:
        reason = "CANARY_RECEIPT_CONTRACT"
    passed = reason is None and returncode == 0 and not remaining and receipt_contract and elapsed <= WALL_SECONDS and final_cpu <= CPU_SECONDS and peak <= RSS_BYTES and size <= OUTPUT_BYTES - 65536
    result = {"status": "COMPLETE_MAC_CANARY_ONLY" if passed else "STOPPED_UNPROMOTABLE",
        "child_returncode": returncode, "reason": reason, "seconds": elapsed,
        "aggregate_cpu_seconds": final_cpu, "sum_observed_rss_peak_bytes": peak,
        "rss_sampling_seconds": 0.1, "output_bytes_before_final_receipt": size,
        "remaining_owned_group_pids": remaining, "source_manifest_sha256": args.source_manifest_sha256,
        "canary_receipt_sha256": digest(marker) if marker.is_file() else None,
        "root_input_identity_after_verified_by_child": passed,
        "full_continuation": False, "model_or_training_or_assay": False,
        "cpu_affinity_not_supported_on_macos": True}
    write_json(run / "RESULT.json", result)
    write_json(run / ("COMPLETE.json" if passed else "STOPPED_UNPROMOTABLE.json"), result)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
