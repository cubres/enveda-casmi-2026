# SPDX-License-Identifier: MIT
"""Original invented example; no network, model, candidate edit or submission."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types

EXPECTED_TOOL_SHA256 = 'd9a91b2163a9532c26fbe281e4d33537343391c9b0bb92a08153fb5a22767b8c'

def load_tool(path):
    # Obtain this original helper from the separately recorded pinned commit.
    # A digest checks consistency; it does not authenticate an untrusted pin.
    with Path(path).open("rb") as f:
        raw = f.read(1_048_577)
    if len(raw) > 1_048_576 or hashlib.sha256(raw).hexdigest() != EXPECTED_TOOL_SHA256:
        raise ValueError("PINNED_TOOL_MISMATCH")
    module = types.ModuleType("companion_pinned_tool")
    module.__file__ = str(Path(path))
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    return module

def run(tool):
    result = tool.candidate_features(
        ion_mz=[100.0],
        spectra=[
            {"mz": [100.0, 100.006], "intensity": [9.0, 4.0], "window": [90.0, 120.0]},
            {"mz": [100.0], "intensity": [9.0], "window": [90.0, 120.0]},
            {"mz": [110.0], "intensity": [9.0], "window": [90.0, 120.0]},
        ],
        abs_tol=0.01, ppm=0.0,
    )
    features = dict(zip(result["feature_names"], result["features"]))
    expected = {"assignment_max": 1.0, "assignment_median": 0.6,
                "assignment_q25": 0.3, "reuse_gap_max": 0.4, "view_count": 3.0}
    if any(abs(features[k] - v) > 1e-12 for k, v in expected.items()):
        raise ValueError("INVENTED_EXPECTATION_MISMATCH")
    return {"status": "INVENTED_ION_AND_CENTROIDS_ONLY", "features": features,
            "per_view": result["per_view"], "work_cells": result["work_cells"],
            "chemistry_adaptor_provided": False,
            "candidate_ranking_or_native_ablation": False, "official_score": None}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True, help="Path to the pinned original helper")
    args = parser.parse_args()
    try:
        result = run(load_tool(args.tool))
    except (OSError, ValueError) as exc:
        # No input path, content, credentials or traceback is printed on HOLD.
        print(json.dumps({"status": "HOLD", "reason": "SOURCE_OR_EXAMPLE_CHECK_FAILED"}))
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
