# SPDX-License-Identifier: MIT
"""Create a fresh, wholly invented file-backed audit example. No cleanup."""
import argparse
import hashlib
import json
from pathlib import Path
from fixed_panel_audit import canonical, manifest_audit
from test_fixed_panel_audit import SOURCE, panel_fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=False)
    panel, completion, queries, pairs, responses = panel_fixture()

    def write(name, value):
        raw = canonical(value)
        with (args.destination / name).open("xb") as stream:
            stream.write(raw)
        return {"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

    manifest = {"schema": "FIXED_PANEL_CAPTURE_FILE_MANIFEST_V1", "expected_count": 16,
                "expected_pair_source_sha256": SOURCE,
                "panel": write("PRIVATE_PANEL_REGISTRATION.json", panel),
                "completion": write("PRIVATE_PANEL_COMPLETION.json", completion),
                "queries": [write("PRIVATE_QUERY_%03d.json" % i, value) for i, value in enumerate(queries)],
                "pairs": [write("PRIVATE_PAIR_%05d.json" % i, value) for i, value in enumerate(pairs)],
                "scalar_responses": write("PRIVATE_SCALAR_RESPONSES.json", responses)}
    write("PRIVATE_INPUT_MANIFEST.json", manifest)
    result = manifest_audit(manifest, args.destination)
    result["evidence_kind"] = "WHOLLY_INVENTED_SOFTWARE_EXAMPLE_NOT_A_COMPETITION_RESULT"
    write("DEMO_RESULT.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
