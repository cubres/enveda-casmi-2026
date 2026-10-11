# SPDX-License-Identifier: MIT
"""One-attempt private CPU consumer; inputs must be already reviewed exports.

Writes new private result/receipt files only. No native model or remote action.
The coordinator owns attempt-ledger choice and duplicate protection across runs.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    for name in ("export", "protocol", "labels", "out", "attempt-ledger"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--intervention")
    args = parser.parse_args()
    actual_nice = os.nice(5)
    soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
    finite_limits = [x for x in (soft, hard) if x != resource.RLIM_INFINITY]
    cpu_limit = min([90] + finite_limits)
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
    import assignment_join as a
    started = datetime.now(timezone.utc).isoformat(); cpu = time.process_time()
    protocol = a.read_json(args.protocol)
    ledger = Path(args.attempt_ledger)
    if not ledger.is_dir() or Path(args.out).exists():
        raise a.JoinHold("existing attempt ledger and new output path required")
    a._sha(protocol["export_sha256"], "export")
    marker = ledger / (protocol["export_sha256"] + ".assignment-attempt.json")
    receipt = {"status": "ATTEMPT_STARTED_BEFORE_LABEL_READ", "utc": started,
               "protocol_sha256": a.digest(protocol), "export_sha256": protocol["export_sha256"],
               "runner_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "no_models_or_remote_mutations": True}
    with marker.open("x", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2); f.write("\n")
    try:
        export = a.read_json(args.export)
        joined = a.score_join(export, protocol)
        # Only after the label-blind join/parity/source/order checks succeed.
        labels = a.read_json(args.labels)
        intervention = a.read_json(args.intervention) if args.intervention else None
        evaluated = a.evaluate_paired(joined, labels, protocol, intervention)
        result = {"status": "PRIVATE_JOIN_COMPLETED", "start_utc": started,
                  "end_utc": datetime.now(timezone.utc).isoformat(), "join": joined, "evaluation": evaluated,
                  "cpu_seconds": time.process_time() - cpu, "nice_adjustment": 5,
                  "actual_nice": actual_nice, "cpu_limit_seconds": cpu_limit,
                  "publication": "PRIVATE_UNLESS_ALL_INPUT_AND_DERIVED_RESULT_RIGHTS_REVIEWED",
                  "runner_source_sha256": receipt["runner_source_sha256"]}
        with Path(args.out).open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2, allow_nan=False); f.write("\n")
        print(json.dumps({"status": result["status"], "scope": evaluated["status"],
                          "queries": evaluated["queries"], "official_score": None}))
    except Exception as error:
        failure = {"status": "PRIVATE_JOIN_FAILED_ATTEMPT_REMAINS_PRESERVED", "utc": datetime.now(timezone.utc).isoformat(),
                   "error_type": type(error).__name__, "reason": str(error), "protocol_sha256": receipt["protocol_sha256"],
                   "runner_source_sha256": receipt["runner_source_sha256"]}
        with Path(str(args.out) + ".failure.json").open("x", encoding="utf-8") as f:
            json.dump(failure, f, indent=2, allow_nan=False); f.write("\n")
        print(json.dumps({"status": failure["status"], "error_type": failure["error_type"]}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
