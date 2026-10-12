"""A complete tiny retrieval demo with invented data, not a competition score."""
import json
from pathlib import Path

import numpy as np

from candidate_interop import load_fixture_bundle, mass_window, binary_tanimoto, stable_ranking


def main():
    package_root = Path(__file__).resolve().parent
    root = package_root / "fixtures" if (package_root / "fixtures").is_dir() else package_root
    # For a real third-party bundle, obtain its pin from the trusted publisher
    # separately. This pin is included here because both arrays and expected
    # results are entirely invented examples shipped together.
    pin = (root / "MANIFEST.sha256").read_text(encoding="ascii").strip()
    arrays, _ = load_fixture_bundle(root, manifest_sha256=pin)
    expected = json.loads((root / "EXPECTED.json").read_text(encoding="utf-8"))
    lo, hi = mass_window(arrays["masses.npy"], neutral_mass_da=100.0, ppm=10.0)
    if [lo, hi] != expected["expected_slice"]:
        raise RuntimeError("invented mass-window oracle mismatch")
    keys = arrays["keys.npy"][lo:hi]
    bits = arrays["morgan_sized.npy"][lo:hi]
    query = np.array(arrays["morgan_sized.npy"][4], copy=True)
    scores = binary_tanimoto(query, bits)
    order = stable_ranking(keys, scores)
    print(json.dumps({"kind": "INVENTED_RETRIEVAL_DEMO", "slice": [lo, hi],
                      "keys": keys[order].tolist(), "binary_tanimoto": scores[order].tolist(),
                      "chemical_model_evaluation": False}, indent=2))


if __name__ == "__main__":
    main()
