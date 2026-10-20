#!/usr/bin/env python3
"""Verify the public CASMI source files cited by the reproducibility audit.

This standard-library-only checker reads and hashes source files. It never
imports or executes them, accesses network resources, or reads model/data
payloads. A mismatch is reported as a failure; the pinned values are not
silently refreshed.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 cubres
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


SOURCE_REFERENCE_COMMIT = "7c885861724ba280db9cfee9d96fe8fa56813e80"

PINS = (
    {
        "path": "reproduction/legacy-v2/ranker_lineage/original_sources/make_ranker3.py",
        "bytes": 4859,
        "sha256": "e94e41a384ee78c027d8c9f3918708aa2d4a94b1eae8fee00c9a7bc5fa427532",
    },
    {
        "path": "reproduction/legacy-v2/ranker_lineage/original_sources/rankfeat.py",
        "bytes": 3557,
        "sha256": "716e01b30f55ad89780d433dd81c683037bf60e759e710756a0b40f28c830c86",
    },
    {
        "path": "reproduction/legacy-v2/ranker_lineage/original_sources/casmi_core.py",
        "bytes": 2977,
        "sha256": "bc8011a1d5a3a0024c739e812b644a8649087e0e92acfbce289e5048a63259f2",
    },
    {
        "path": "reproduction/legacy-v2/ranker_lineage/original_sources/score_model.py",
        "bytes": 2033,
        "sha256": "8970ca52b11fe2490b861f6c29d54e316d96d2118349d1ea40afd1b501b8d2ea",
    },
    {
        "path": "reproduction/legacy-v2/checkpoint_lineage/original_sources/fpmodel.py",
        "bytes": 5158,
        "sha256": "69f2656778a08233e22235bf4853f0b3d2420b431390a32d6c8ed453cde85c76",
    },
    {
        "path": "reproduction/legacy-v2/checkpoint_lineage/original_sources/train_fp3.py",
        "bytes": 9631,
        "sha256": "43bb618dd512def4ccb1119f813aabce2b9f9bcbfa681c9d2db5adfa05e66840",
    },
    {
        "path": "reproduction/legacy-v2/checkpoint_lineage/original_sources/train_fp4.py",
        "bytes": 11704,
        "sha256": "e2eaef630c5f09f157eea3652095b8b9780cbe7fdffa6f0652ae5845d7b18c8a",
    },
    {
        "path": "reproduction/legacy-v2/public_source/build_fps.py",
        "bytes": 2182,
        "sha256": "6cd11e3910dc935ecda4a02f2f406c2bafb4c66e356f15dd88f635d5b993078c",
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(repo_root: Path) -> dict:
    root = repo_root.resolve(strict=True)
    results = []
    for pin in PINS:
        relative = Path(pin["path"])
        candidate = root / relative
        item = {
            "path": pin["path"],
            "expected_bytes": pin["bytes"],
            "expected_sha256": pin["sha256"],
            "actual_bytes": None,
            "actual_sha256": None,
            "status": "FAIL",
        }

        if relative.is_absolute() or ".." in relative.parts:
            item["reason"] = "UNSAFE_PIN_PATH"
        elif candidate.is_symlink():
            item["reason"] = "SYMLINK_SOURCE_REFUSED"
        elif not candidate.is_file():
            item["reason"] = "SOURCE_FILE_MISSING"
        else:
            resolved = candidate.resolve(strict=True)
            if root not in resolved.parents:
                item["reason"] = "SOURCE_PATH_ESCAPES_ROOT"
            else:
                item["actual_bytes"] = resolved.stat().st_size
                item["actual_sha256"] = sha256_file(resolved)
                if (item["actual_bytes"] == pin["bytes"]
                        and item["actual_sha256"] == pin["sha256"]):
                    item["status"] = "PASS"
                else:
                    item["reason"] = "SOURCE_PIN_MISMATCH"
        results.append(item)

    passed = sum(item["status"] == "PASS" for item in results)
    return {
        "status": "PASS_SOURCE_PINS" if passed == len(results) else "FAIL_SOURCE_PINS",
        "source_reference": {
            "repository": "https://github.com/cubres/enveda-casmi-2026",
            "commit": SOURCE_REFERENCE_COMMIT,
        },
        "checked_files": len(results),
        "passed_files": passed,
        "scope": "source-file bytes only; no imports, execution, network, model or dataset payload reads",
        "limitations": [
            "Passing hashes bind source bytes only; they do not reproduce historical checkpoints or ranker arrays.",
            "This script does not audit dataset rights, input versions, training runtime or scientific quality.",
            "Competition-derived datasets, weights and caches retain their separate terms.",
        ],
        "files": results,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[4],
        help="checkout root (defaults to the repository containing this script)",
    )
    args = parser.parse_args(argv)
    try:
        report = audit(args.repo_root)
    except (OSError, RuntimeError) as exc:
        report = {
            "status": "FAIL_SOURCE_PINS",
            "checked_files": len(PINS),
            "passed_files": 0,
            "error": str(exc),
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS_SOURCE_PINS" else 1


if __name__ == "__main__":
    sys.exit(main())
