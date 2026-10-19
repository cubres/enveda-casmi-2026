"""Restore 61 hash-pinned payload files from an independently verified flat set.

SPDX-License-Identifier: Apache-2.0

All sources are verified before the new output directory is created. Nothing
is overwritten, removed, downloaded or executed. Failures preserve any partial
output for audit; use a different, explicitly chosen output directory later.
The closure is returned/printed, never written inside the restored tree.
"""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import unicodedata


EXPECTED_FILES = 61
MAP_NAME = "TRANSPORT_MAP.json"
CHUNK_BYTES = 1024 * 1024
HEX_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _sha(value, field):
    if not isinstance(value, str) or not HEX_SHA256.fullmatch(value):
        raise ValueError(f"invalid SHA256: {field}")
    return value.lower()


def _relative_parts(value, *, top_level=False):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("invalid relative path")
    if value.startswith("/") or PureWindowsPath(value).drive:
        raise ValueError("absolute or drive-qualified path rejected")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("empty/traversal path component rejected")
    if top_level and len(parts) != 1:
        raise ValueError("flat_name must be one top-level filename")
    for part in parts:
        name = part.casefold()
        if ".ipynb" in name or "kernel-metadata.json" in name:
            raise ValueError("notebook identity artifacts are prohibited")
        if name.endswith((".pkl", ".pickle")):
            raise ValueError("pickle/bank artifacts are prohibited")
        binary = name.endswith((".npy", ".npz", ".parquet", ".bin"))
        if binary and (name.startswith(("pool_", "old_pool", "oldbank", "old_bank")) or name in {"pool.npy", "pool.npz", "fp.npy", "mass.npy", "keys.npy"}):
            raise ValueError("old pool/bank artifacts are prohibited")
    return tuple(parts)


def _portable_key(parts):
    return tuple(unicodedata.normalize("NFC", part).casefold() for part in parts)


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


@contextmanager
def _regular_source(path):
    """Open a regular source without following its final-component symlink."""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or path.is_symlink():
        raise ValueError("source must be a regular non-symlink file")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        current = path.lstat()
        if not stat.S_ISREG(opened.st_mode) or not stat.S_ISREG(current.st_mode):
            raise ValueError("source is no longer a regular file")
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino) or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError("source identity changed while opening")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            yield stream
    finally:
        os.close(descriptor)


def _read_mapping(path, expected_sha256):
    with _regular_source(path) as stream:
        raw = stream.read()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("mapping SHA256 mismatch; JSON was not parsed")
    mapping = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object)
    if not isinstance(mapping, dict) or set(mapping) != {"scope", "expected_files", "files"}:
        raise ValueError("invalid transport-map schema")
    if not isinstance(mapping["scope"], str) or not mapping["scope"].strip():
        raise ValueError("mapping scope must be a nonempty string")
    if type(mapping["expected_files"]) is not int or mapping["expected_files"] != EXPECTED_FILES:
        raise ValueError("mapping must declare exactly 61 files")
    if not isinstance(mapping["files"], dict) or len(mapping["files"]) != EXPECTED_FILES:
        raise ValueError("mapping must contain exactly 61 file entries")
    entries = []
    flat_keys, restored_keys = set(), set()
    portable_spellings = {}
    for original, item in mapping["files"].items():
        parts = _relative_parts(original)
        if not isinstance(item, dict) or set(item) != {"flat_name", "bytes", "sha256"}:
            raise ValueError("invalid mapped-file schema")
        flat_parts = _relative_parts(item["flat_name"], top_level=True)
        if flat_parts[0].casefold() == MAP_NAME.casefold():
            raise ValueError("transport mapping cannot map itself")
        if type(item["bytes"]) is not int or item["bytes"] <= 0:
            raise ValueError("mapped file size must be a positive integer")
        flat_key, restored_key = _portable_key(flat_parts), _portable_key(parts)
        if flat_key in flat_keys or restored_key in restored_keys:
            raise ValueError("portable flat/restored filename collision")
        for length in range(1, len(parts) + 1):
            prefix_key = restored_key[:length]
            if prefix_key in portable_spellings and portable_spellings[prefix_key] != parts[:length]:
                raise ValueError("portable directory-spelling collision")
            portable_spellings[prefix_key] = parts[:length]
        flat_keys.add(flat_key)
        restored_keys.add(restored_key)
        entries.append({"relative_path": original, "parts": parts, "flat_name": item["flat_name"], "bytes": item["bytes"], "sha256": _sha(item["sha256"], original)})
    for key in restored_keys:
        if any(key[:length] in restored_keys for length in range(1, len(key))):
            raise ValueError("restored file/directory prefix collision")
    return mapping["scope"], sorted(entries, key=lambda entry: entry["relative_path"])


def _verified_source(path, entry):
    digest, count = hashlib.sha256(), 0
    with _regular_source(path) as stream:
        for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
            digest.update(chunk)
            count += len(chunk)
    if count != entry["bytes"] or digest.hexdigest() != entry["sha256"]:
        raise ValueError(f"source size/SHA256 mismatch: {entry['flat_name']}")


def reassemble(flat_dir, output_dir, mapping_sha256):
    """Restore a pinned flat transport into a new, separate directory.

    Unmapped regular transport helper files are ignored. Any top-level source
    symlink is rejected. The output parent must already exist. All originals
    must be non-notebook, non-pickle payload files covered by the pinned map.
    """
    expected_mapping_sha = _sha(mapping_sha256, "mapping_sha256")
    raw_flat, raw_output = Path(flat_dir).absolute(), Path(output_dir).absolute()
    if raw_flat.is_symlink() or not raw_flat.is_dir():
        raise ValueError("flat_dir must be a non-symlink directory")
    if raw_output.exists() or raw_output.is_symlink():
        raise ValueError("output directory must not already exist")
    if raw_output.parent.is_symlink() or not raw_output.parent.is_dir():
        raise ValueError("output parent must be an existing non-symlink directory")
    flat, output = raw_flat.resolve(strict=True), raw_output.resolve(strict=False)
    if flat == output or flat in output.parents or output in flat.parents:
        raise ValueError("source/output ancestor or descendant overlap rejected")
    if any(entry.is_symlink() for entry in flat.iterdir()):
        raise ValueError("symlink in flat transport rejected")
    scope, entries = _read_mapping(flat / MAP_NAME, expected_mapping_sha)

    # Do not create output until every one of the 61 source files has passed.
    for entry in entries:
        _verified_source(flat / entry["flat_name"], entry)

    output.mkdir(exist_ok=False)
    closure = {}
    for entry in entries:
        parent = output
        for component in entry["parts"][:-1]:
            parent = parent / component
            if parent.exists() or parent.is_symlink():
                if parent.is_symlink() or not parent.is_dir():
                    raise ValueError("unsafe output parent appeared")
            else:
                parent.mkdir(exist_ok=False)
        destination = parent / entry["parts"][-1]
        digest, count = hashlib.sha256(), 0
        with _regular_source(flat / entry["flat_name"]) as source:
            with destination.open("xb") as target:
                for chunk in iter(lambda: source.read(CHUNK_BYTES), b""):
                    target.write(chunk)
                    digest.update(chunk)
                    count += len(chunk)
        if count != entry["bytes"] or digest.hexdigest() != entry["sha256"]:
            raise ValueError("source changed during exclusive copy; partial output preserved")
        _verified_source(destination, entry)
        closure[entry["relative_path"]] = {"bytes": count, "sha256": digest.hexdigest()}

    actual_files = set()
    for path in output.rglob("*"):
        if path.is_symlink():
            raise ValueError("unexpected output symlink")
        if path.is_file():
            actual_files.add(path.relative_to(output).as_posix())
        elif not path.is_dir():
            raise ValueError("unexpected nonregular output entry")
    if actual_files != set(closure) or len(actual_files) != EXPECTED_FILES:
        raise ValueError("output closure differs from the 61 mapped originals")
    return {"status": "PASS_EXACT_61_FILE_REASSEMBLY", "scope": scope, "mapping_sha256": expected_mapping_sha, "files": closure, "file_count": len(closure), "total_bytes": sum(item["bytes"] for item in closure.values()), "receipt_written_inside_output": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flat-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--mapping-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(reassemble(args.flat_dir, args.output_dir, args.mapping_sha256), indent=2))


if __name__ == "__main__":
    main()
