"""61-file synthetic filesystem fixtures; no real dataset or network access.

SPDX-License-Identifier: Apache-2.0

Fixture directories are intentionally preserved. No test deletes files or
overwrites an existing path, including during symlink and mismatch cases.
"""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from reassemble_payload import MAP_NAME, reassemble


def fixture(transform=None, *, symlink=False):
    root = Path(tempfile.mkdtemp(prefix="casmi_flat_transport_synthetic_"))
    flat = root / "flat"
    flat.mkdir()
    mapping = {"scope": "Invented 61-file unit-test payload", "expected_files": 61, "files": {}}
    contents = {}
    for index in range(61):
        original = f"top{index:02d}.txt" if index < 10 else f"source/group{index % 3}/file{index:02d}.txt"
        flat_name = original.replace("/", "__")
        data = f"Invented payload number {index:02d}\n".encode()
        if symlink and index == 0:
            target = root / "synthetic_link_target.txt"
            with target.open("xb") as stream:
                stream.write(data)
            (flat / flat_name).symlink_to(target)
        else:
            with (flat / flat_name).open("xb") as stream:
                stream.write(data)
        mapping["files"][original] = {"flat_name": flat_name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        contents[original] = data
    if transform:
        transform(mapping)
    raw = (json.dumps(mapping, indent=2) + "\n").encode()
    with (flat / MAP_NAME).open("xb") as stream:
        stream.write(raw)
    return root, flat, root / "restored", hashlib.sha256(raw).hexdigest(), contents


class ReassemblyTests(unittest.TestCase):
    def test_exact_nested_restore_and_no_extra_receipt(self):
        _, flat, output, mapping_sha, contents = fixture()
        result = reassemble(flat, output, mapping_sha)
        self.assertEqual(result["file_count"], 61)
        self.assertFalse(result["receipt_written_inside_output"])
        self.assertEqual(result["total_bytes"], sum(map(len, contents.values())))
        actual = {path.relative_to(output).as_posix(): path.read_bytes() for path in output.rglob("*") if path.is_file()}
        self.assertEqual(actual, contents)
        self.assertTrue((flat / MAP_NAME).is_file())

    def test_mapping_digest_mismatch_before_json_parse_or_output(self):
        _, flat, output, _, _ = fixture()
        with self.assertRaisesRegex(ValueError, "mapping SHA256 mismatch"):
            reassemble(flat, output, "0" * 64)
        self.assertFalse(output.exists())

    def test_late_source_digest_mismatch_prevents_all_output_creation(self):
        def change(mapping):
            last = list(mapping["files"])[-1]
            mapping["files"][last]["sha256"] = "0" * 64
        _, flat, output, mapping_sha, _ = fixture(change)
        with self.assertRaisesRegex(ValueError, "source size/SHA256 mismatch"):
            reassemble(flat, output, mapping_sha)
        self.assertFalse(output.exists())

    def test_bad_paths_and_forbidden_artifacts_reject(self):
        for bad in ["../outside.txt", "/absolute.txt", "C:/drive.txt", "dir\\backslash.txt", "a//b.txt", "a/./b.txt", "notebook.ipynb", "x/kernel-metadata.json", "x/pool_meta.pkl", "pool_fp.npy"]:
            def change(mapping, bad=bad):
                first = next(iter(mapping["files"]))
                item = mapping["files"].pop(first)
                mapping["files"][bad] = item
            _, flat, output, mapping_sha, _ = fixture(change)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                reassemble(flat, output, mapping_sha)
            self.assertFalse(output.exists())

    def test_flat_collision_and_restored_prefix_collision_reject(self):
        def flat_collision(mapping):
            keys = list(mapping["files"])
            mapping["files"][keys[1]]["flat_name"] = mapping["files"][keys[0]]["flat_name"]
        def prefix_collision(mapping):
            keys = list(mapping["files"])
            first = mapping["files"].pop(keys[0])
            second = mapping["files"].pop(keys[1])
            mapping["files"]["same"] = first
            mapping["files"]["same/child.txt"] = second
        def directory_case_collision(mapping):
            keys = list(mapping["files"])
            first = mapping["files"].pop(keys[0])
            second = mapping["files"].pop(keys[1])
            mapping["files"]["Case/one.txt"] = first
            mapping["files"]["case/two.txt"] = second
        for change in [flat_collision, prefix_collision, directory_case_collision]:
            _, flat, output, mapping_sha, _ = fixture(change)
            with self.subTest(change=change.__name__), self.assertRaisesRegex(ValueError, "collision"):
                reassemble(flat, output, mapping_sha)
            self.assertFalse(output.exists())

    def test_symlink_source_rejected_and_preserved(self):
        _, flat, output, mapping_sha, _ = fixture(symlink=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            reassemble(flat, output, mapping_sha)
        self.assertTrue((flat / "top00.txt").is_symlink())
        self.assertFalse(output.exists())

    def test_existing_output_is_never_overwritten(self):
        _, flat, output, mapping_sha, _ = fixture()
        output.mkdir()
        sentinel = output / "preserve.txt"
        with sentinel.open("xb") as stream:
            stream.write(b"preserve this exact synthetic file")
        with self.assertRaisesRegex(ValueError, "must not already exist"):
            reassemble(flat, output, mapping_sha)
        self.assertEqual(sentinel.read_bytes(), b"preserve this exact synthetic file")

    def test_source_descendant_output_rejected(self):
        _, flat, _, mapping_sha, _ = fixture()
        output = flat / "new_child"
        with self.assertRaisesRegex(ValueError, "overlap"):
            reassemble(flat, output, mapping_sha)
        self.assertFalse(output.exists())

    def test_nonpositive_sizes_and_wrong_counts_reject(self):
        def zero_size(mapping):
            mapping["files"][next(iter(mapping["files"]))]["bytes"] = 0
        def wrong_declared(mapping):
            mapping["expected_files"] = 60
        def wrong_entries(mapping):
            mapping["files"].pop(next(iter(mapping["files"])))
        for change in [zero_size, wrong_declared, wrong_entries]:
            _, flat, output, mapping_sha, _ = fixture(change)
            with self.subTest(change=change.__name__), self.assertRaises(ValueError):
                reassemble(flat, output, mapping_sha)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
