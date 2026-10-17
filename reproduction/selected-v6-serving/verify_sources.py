"""Check the six archived source files without importing or executing them."""
import hashlib
import json
from pathlib import Path


def verify(root):
    root = Path(root)
    binding = json.loads((root / "SERVING_BINDING.json").read_text())
    entries = binding["sources"]
    if len(entries) != 6:
        raise ValueError("EXPECTED_SIX_SOURCES")
    for name, expected in entries.items():
        if Path(name).name != name:
            raise ValueError("SOURCE_BASENAME_REQUIRED")
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("REGULAR_SOURCE_REQUIRED")
        raw = path.read_bytes()
        if len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
            raise ValueError("SOURCE_BYTES_DIFFER")
        compile(raw.decode("utf-8"), name, "exec")
    return {"status": "PASS_SOURCE_BYTES_AND_SYNTAX", "source_files": len(entries),
            "scientific_execution": False, "native_compatibility_claimed": False,
            "complete_reproduction_claimed": False}


if __name__ == "__main__":
    print(json.dumps(verify(Path(__file__).resolve().parent), sort_keys=True))
