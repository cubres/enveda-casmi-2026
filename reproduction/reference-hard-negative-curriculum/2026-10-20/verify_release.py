"""Read-only verification of the current code-only package. SPDX-License-Identifier: Apache-2.0

Checks file hashes and confirms that withdrawn derived outputs are absent.
Does not run the producer, consumer, network, training, or model inference.
"""
import hashlib
import json
from pathlib import Path


def pin(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("missing/symlink release file: " + str(path))
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    root = Path(__file__).resolve().parent
    release = json.loads((root / "RELEASE_FILES.json").read_bytes())
    if release.get("schema") != "casmi-reference-negative-curriculum-public-release-files/2":
        raise ValueError("unexpected current release manifest schema")
    for relative, expected in release["files"].items():
        rel = Path(relative)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("invalid public release path")
        if pin(root / rel) != expected:
            raise ValueError("release byte mismatch: " + relative)
    for relative in release["withdrawn_paths"]:
        rel = Path(relative)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("invalid withdrawn path")
        if (root / rel).exists():
            raise ValueError("withdrawn data output is present: " + relative)
    print(json.dumps({
        "status": "PASS_CURRENT_CODE_ONLY_PACKAGE",
        "release_files": len(release["files"]),
        "withdrawn_paths_absent": len(release["withdrawn_paths"]),
        "producer_or_sampler_executed": False
    }, sort_keys=True))


if __name__ == "__main__":
    main()
