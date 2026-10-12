"""Write a tiny, deterministic invented bundle; refuses to overwrite any file."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def build(directory):
    root = Path(directory)
    if root.exists() and any(root.iterdir()):
        raise ValueError("choose a new empty fixture directory")
    root.mkdir(parents=True, exist_ok=True)
    q, width = 100.0, 100.0 * (10.0 / 1e6)
    masses = np.array([50.0, 99.997, q-width, q-width, q, q, 100.0005,
                       q+width, q+width, 100.003, 150.0, 300.0], dtype=np.float64)
    keys = np.array([f"SYN{i:03d}" for i in range(len(masses))], dtype="<U6")
    morgan = np.zeros((len(masses), 2048), dtype=np.uint8)
    maccs = np.zeros((len(masses), 166), dtype=np.uint8)
    for i in range(len(masses)):
        morgan[i, [0, (17*i+7) % 2048, 2047]] = 1
        maccs[i, [i % 166, 165]] = 1
    arrays = {"masses.npy": masses, "keys.npy": keys,
              "morgan_sized.npy": morgan, "maccs_sized.npy": maccs}
    entries = {}
    for filename, array in arrays.items():
        path = root / filename
        with path.open("xb") as handle:
            np.save(handle, array, allow_pickle=False)
        entries[filename] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                             "bytes": path.stat().st_size, "dtype": array.dtype.str,
                             "shape": list(array.shape)}
    manifest = {"schema": "casmi-interop-invented-fixtures-v1", "rows": len(masses),
                "chemical_data": False, "fingerprints_are_invented": True,
                "mass_semantics": "invented positive neutral mass in Da; sorted ascending",
                "row_semantics": "SYN000..SYN011 are invented keys, not chemical identifiers",
                "feature_semantics": "Morgan-sized and MACCS-sized invented bits; no molecules, no RDKit",
                "files": entries}
    with (root / "MANIFEST.json").open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    pin = hashlib.sha256((root / "MANIFEST.json").read_bytes()).hexdigest()
    with (root / "MANIFEST.sha256").open("x", encoding="ascii") as handle:
        handle.write(pin + "\n")
    expected = {"schema": "casmi-interop-invented-oracles-v1",
                "query_neutral_mass_da": 100.0, "ppm_query_denominator": 10.0,
                "expected_slice": [2, 9], "expected_keys": keys[2:9].tolist(),
                "purpose": "Boundary duplicates included; toy rows only. No chemistry or model evaluation."}
    with (root / "EXPECTED.json").open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(expected, indent=2, sort_keys=True) + "\n")
    return pin


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python build_fixtures.py NEW_EMPTY_DIRECTORY")
    print(build(sys.argv[1]))
