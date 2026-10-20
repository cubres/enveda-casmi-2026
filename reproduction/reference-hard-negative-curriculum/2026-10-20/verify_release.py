"""Read-only public package/actual-output verification. SPDX-License-Identifier: Apache-2.0

No producer, consumer sampling, network, model or source mutation is invoked.
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
    for relative, expected in release["files"].items():
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError("invalid public release path")
        if pin(root / relative) != expected:
            raise ValueError("release byte mismatch: " + relative)
    actual = json.loads((root / "completed/data/OUTPUT_MANIFEST.json").read_bytes())
    if len(actual["files"]) != 6:
        raise ValueError("six actual scientific/resource files required")
    for relative, expected in actual["files"].items():
        if pin(root / "completed/data" / relative) != expected:
            raise ValueError("actual output byte mismatch: " + relative)
    print(json.dumps({"status": "PASS_PUBLIC_FILE_BYTES_ONLY", "release_files": len(release["files"]),
                      "actual_output_files": 6, "producer_or_sampler_executed": False,
                      "fresh_run_dynamic_receipt_parity_claim": False}, sort_keys=True))


if __name__ == "__main__":
    main()
