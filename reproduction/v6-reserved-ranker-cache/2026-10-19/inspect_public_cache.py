"""Inspect published numeric V6 cache without a GPU/model/score; Apache-2.0."""
from pathlib import Path
import argparse
import hashlib
import json


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    release = json.loads((args.root / "PUBLIC_RELEASE_MANIFEST.json").read_text())
    assert release["status"] == "ACTUAL_NATIVE_NUMERIC_OUTPUTS_VERIFIED"
    for name, entry in release["files"].items():
        path = args.root / name
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert path.stat().st_size == entry["bytes"] and digest(path) == entry["sha256"], name
    import numpy as np
    logits = np.load(args.root / "query_logits.npy", mmap_mode="r", allow_pickle=False)
    structures = np.load(args.root / "structure_indices.npy", allow_pickle=False)
    bitmap = np.load(args.root / "completion_bitmap.npy", allow_pickle=False)
    bits = np.load(args.root / "fp_bit_indices.npy", allow_pickle=False)
    truth = np.load(args.root / "truth_fp_packed.npy", mmap_mode="r", allow_pickle=False)
    keys = np.load(args.root / "structure_keys.npy", allow_pickle=False)
    assert logits.shape == (13579, 10395) and logits.dtype == np.float32
    assert len(structures) == len(keys) == len(bitmap) == 13579
    assert bitmap.dtype == np.bool_ and bitmap.all()
    assert np.all(np.diff(structures) > 0) and np.all(structures % 2 == 1)
    assert bits.shape == (10395,) and np.all(np.diff(bits) > 0)
    assert truth.shape == (13579, 1300) and truth.dtype == np.uint8
    assert np.all((truth[:, -1] & 31) == 0)
    for start in range(0, len(structures), 256):
        assert np.isfinite(logits[start:start + 256]).all()
    print(json.dumps({"status": "PASS_PUBLIC_NUMERIC_CACHE", "queries": len(structures), "bits": len(bits),
                      "model_loaded": False, "gpu_used": False, "score_computed": False,
                      "first_public_keys": keys[:3].tolist(),
                      "qualification": "optimizer-held-out raw structures; canonical checkpoint-selection overlap unaudited"}, indent=2))


if __name__ == "__main__":
    main()
