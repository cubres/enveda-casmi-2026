"""Exclusive root-owned CPU execution: one 64-query canary and gated atlas.

SPDX-License-Identifier: Apache-2.0
No native/GPU/network actions. A consumed attempt is never retried here.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

SOURCE = Path(__file__).resolve().parent
CONTROL = SOURCE.parent
ONCE = CONTROL / "ROOT_REFERENCE_ATLAS_ONCE_CONSUMED.json"
WALL_SECONDS = 120.0
WHOLE_RSS_BYTES = 512 << 20


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def source_binding():
    contract = json.loads((SOURCE / "SOURCE_MANIFEST.json").read_bytes())
    for name, expected in contract["files"].items():
        path = SOURCE / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("source file missing/symlink: " + name)
        raw = path.read_bytes()
        if len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
            raise ValueError("source binding mismatch: " + name)
    return hashlib.sha256((SOURCE / "SOURCE_MANIFEST.json").read_bytes()).hexdigest()


def own_rss_peak():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def child_rss(pid):
    result = subprocess.run(["ps", "-o", "pid=,pgid=,rss=", "-p", str(pid)], capture_output=True,
                            text=True, timeout=2, check=False)
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 3 and int(fields[0]) == pid and int(fields[1]) == pid:
            return int(fields[2]) * 1024
    return None


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
        process.wait(timeout=4)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=4)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path, help="Exact pinned public ChEBI4096 release directory")
    parser.add_argument("--out", required=True, type=Path, help="New owned execution directory; parent must exist")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        raise ValueError("Python >=3.10 required before attempt admission (integer bit_count oracle)")
    if sys.platform not in ("darwin", "linux"):
        raise ValueError("owned RSS and process-group implementation requires macOS/Linux")
    if args.out.exists() or not args.out.parent.is_dir() or not args.source_dir.is_dir():
        raise ValueError("fresh output path and existing source directory/parent required")
    for dependency in ("numpy", "pyarrow"):
        if importlib.util.find_spec(dependency) is None:
            raise ValueError("missing dependency before attempt admission: " + dependency)
    binding = source_binding()
    started = time.monotonic()
    marker = {"status": "CONSUMED_BEFORE_PRODUCER_NO_RETRY", "source_manifest_sha256": binding,
              "source_directory": str(args.source_dir.resolve()), "output_directory": str(args.out.absolute()),
              "wrapper_seconds": WALL_SECONDS, "whole_RSS_bytes": WHOLE_RSS_BYTES,
              "CPU_thread_limit": 2, "scientific_run": "reference structures only; no assay or model"}
    fd = os.open(ONCE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(json.dumps(marker, indent=2, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    args.out.mkdir(exist_ok=False)
    environment = os.environ.copy()
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS",
                 "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
        environment[name] = "2"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONUNBUFFERED"] = "1"
    environment["CUDA_VISIBLE_DEVICES"] = ""
    process, reason, peak_child = None, None, 0
    result = {"status": "FAILED_CONSUMED_NOT_PROMOTABLE", "source_manifest_sha256": binding,
              "whole_RSS_bytes": WHOLE_RSS_BYTES, "wrapper_seconds": WALL_SECONDS,
              "no_GPU_model_spectra_or_labels": True, "attempt_remains_consumed": True}
    try:
        with (args.out / "child.log").open("wb") as log:
            process = subprocess.Popen([sys.executable, "-B", "-u", str(SOURCE / "build_atlas.py"),
                                        "--source-dir", str(args.source_dir.resolve()), "--out", str(args.out / "data")],
                                       env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            while process.poll() is None:
                measured = child_rss(process.pid)
                peak_child = max(peak_child, measured or 0)
                if time.monotonic() - started > WALL_SECONDS - 10:
                    reason = "110-second execution ceiling leaves cleanup reserve"
                elif peak_child + own_rss_peak() > WHOLE_RSS_BYTES:
                    reason = "whole owned RSS budget exceeded"
                if reason:
                    stop_owned(process)
                    break
                time.sleep(0.1)
            returncode = process.wait(timeout=4)
        child_receipt = args.out / "data/ATLAS_COMPLETE.json"
        child = json.loads(child_receipt.read_bytes()) if child_receipt.is_file() else None
        # The producer has no child processes. Its OS high-water mark remains
        # valid evidence when the process exits between two external samples.
        peak_child = max(peak_child, int(child["peak_RSS_bytes"]) if child else 0)
        clean = group_clean(process.pid)
        same = source_binding() == binding
        elapsed = time.monotonic() - started
        success = (returncode == 0 and reason is None and clean and same and child is not None and
                   child["status"] == "COMPLETE_REFERENCE_ATLAS_ONLY" and child["rows"] == 4096 and
                   peak_child + own_rss_peak() <= WHOLE_RSS_BYTES and elapsed <= WALL_SECONDS)
        result.update({"status": "PASS_COMPLETE_REFERENCE_ATLAS_NO_QUALITY_CLAIM" if success else result["status"],
                       "reason": reason, "child_returncode": returncode, "owned_process_group_clean": clean,
                       "source_hashes_unchanged": same, "peak_child_RSS_bytes": peak_child,
                       "peak_wrapper_RSS_bytes": own_rss_peak(), "conservative_sum_of_RSS_peaks_bytes": peak_child + own_rss_peak(),
                       "seconds": elapsed, "child_completion": child["status"] if child else None})
    except BaseException as exc:
        if process is not None:
            stop_owned(process)
        result.update({"reason": type(exc).__name__ + ": " + str(exc), "seconds": time.monotonic() - started})
    dump(args.out / "RESULT.json", result)
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "PASS_COMPLETE_REFERENCE_ATLAS_NO_QUALITY_CLAIM":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
