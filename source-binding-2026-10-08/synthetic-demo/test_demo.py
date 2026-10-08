"""Portable tests using retained neutral synthetic files, with no model loading."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

import demo

HERE = Path(__file__).resolve().parent
TEST_RUN = HERE / ("test_runs_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
TEST_RUN.mkdir()
resolver, bridge = demo.verified_modules()


class SourceBindingTests(unittest.TestCase):
    def setUp(self):
        self.root = TEST_RUN / self._testMethodName / "input"
        self.root.mkdir(parents=True)
        self.namespaced = Path("datasets") / demo.OWNER / demo.SLUG

    def checked(self, **changes):
        contract = dict(input_root=self.root, owner=demo.OWNER, slug=demo.SLUG,
                        relative_filename=demo.FILENAME,
                        expected_size=len(demo.PAYLOAD), expected_sha256=demo.PAYLOAD_SHA)
        contract.update(changes)
        with mock.patch.object(Path, "glob", side_effect=AssertionError("no global search")), \
             mock.patch.object(Path, "rglob", side_effect=AssertionError("no global search")):
            return resolver.resolve_mapped_file(**contract)

    def rejected(self, reason, **changes):
        with self.assertRaises(resolver.MappedFileResolutionError) as caught:
            self.checked(**changes)
        self.assertEqual(caught.exception.receipt["reason"], reason)
        self.assertNotIn(str(TEST_RUN), str(caught.exception))
        return caught.exception.receipt

    def test_single_canonical_checks_size_and_full_sha(self):
        source = demo.put_file(self.root, self.namespaced)
        result = self.checked()
        self.assertEqual(result.path, source.resolve(strict=True))
        self.assertEqual(result.receipt["observed_sha256"], hashlib.sha256(demo.PAYLOAD).hexdigest())
        self.assertEqual(result.receipt["counts"]["unique_canonical_paths"], 1)

    def test_legacy_layout_is_explicitly_supported(self):
        source = demo.put_file(self.root, Path(demo.SLUG))
        result = self.checked()
        self.assertEqual(result.path, source.resolve(strict=True))
        self.assertEqual(result.receipt["resolved_source_classes"], ["legacy_slug"])

    def test_same_physical_alias_is_deduped(self):
        source = demo.put_file(self.root, self.namespaced)
        try:
            (self.root / demo.SLUG).symlink_to(
                (self.root / self.namespaced).resolve(strict=True), target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("OS does not permit symlink fixtures")
        result = self.checked()
        self.assertEqual(result.path, source.resolve(strict=True))
        self.assertEqual(result.receipt["counts"]["resolved_candidates"], 2)
        self.assertEqual(result.receipt["counts"]["unique_canonical_paths"], 1)
        self.assertEqual(result.receipt["counts"]["canonical_aliases"], 1)

    def test_distinct_files_with_identical_bytes_are_ambiguous(self):
        demo.put_file(self.root, self.namespaced)
        demo.put_file(self.root, Path(demo.SLUG))
        receipt = self.rejected("DISTINCT_CANONICAL_SOURCES")
        self.assertEqual(receipt["counts"]["unique_canonical_paths"], 2)

    def test_wrong_hash_same_size_is_rejected(self):
        demo.put_file(self.root, self.namespaced)
        self.rejected("SHA256_MISMATCH", expected_sha256="0" * 64)

    def test_wrong_size_is_rejected(self):
        demo.put_file(self.root, self.namespaced)
        self.rejected("SIZE_MISMATCH", expected_size=len(demo.PAYLOAD) + 1)

    def test_wrong_owner_does_not_fall_back_to_global_filename(self):
        demo.put_file(self.root, Path("datasets") / "another-lab" / demo.SLUG)
        self.rejected("MAPPED_FILE_MISSING")

    def test_traversal_and_absolute_paths_are_rejected(self):
        for name in ("../example.bin", "/example.bin", "folder/../example.bin",
                     "folder\\example.bin", "folder//example.bin"):
            with self.subTest(name=name):
                self.rejected("INPUT_CONTRACT_INVALID", relative_filename=name)

    def test_missing_file_is_a_structured_failure(self):
        receipt = self.rejected("MAPPED_FILE_MISSING")
        self.assertEqual(receipt["counts"]["explicit_candidates"], 2)
        self.assertEqual(receipt["counts"]["missing_candidates"], 2)

    def test_bridge_known_file_lookup_does_not_call_original(self):
        source = demo.put_file(self.root, self.namespaced)
        original = mock.Mock(return_value="neutral-original-selector")
        bound = bridge.bind_known_find(original, {demo.FILENAME: self.checked().path})
        self.assertEqual(bound(demo.FILENAME), str(source.resolve(strict=True)))
        original.assert_not_called()
        self.assertEqual(bound("unmapped.bin"), "neutral-original-selector")
        original.assert_called_once_with("unmapped.bin")

    def test_bridge_selector_changes_only_one_expression(self):
        for index, (old, replacement) in bridge.IO_SITES.items():
            source = "# Preserve this neutral surrounding text.\npaths = sorted(" + old + ")\n"
            transformed = bridge.transform_io_binding(index, source)
            self.assertEqual(transformed.replace(replacement, old), source)
            self.assertEqual(transformed, source.replace(old, replacement))

    def test_bridge_selector_count_drift_fails(self):
        for index, (old, _) in bridge.IO_SITES.items():
            for source in ("paths = []\n", old + "\n" + old):
                with self.subTest(index=index, count=source.count(old)):
                    with self.assertRaises(RuntimeError):
                        bridge.transform_io_binding(index, source)

    def test_demo_emits_relative_public_safe_receipts(self):
        receipt = demo.run_demo(TEST_RUN / "full_demo")
        encoded = json.dumps(receipt)
        for forbidden in (str(TEST_RUN), "/Users/", "prvsiyan", "cubres",
                          "zz-gpuchk", demo.PAYLOAD.decode().strip()):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(receipt["status"], "PASS_SYNTHETIC_SOURCE_BINDING_DEMO")
        self.assertEqual(receipt["scenarios"]["single_canonical"]["status"], "PASS")
        self.assertEqual(receipt["scenarios"]["distinct_physical_duplicates"]["reason"],
                         "DISTINCT_CANONICAL_SOURCES")
        self.assertEqual(receipt["scenarios"]["wrong_hash"]["reason"], "SHA256_MISMATCH")
        self.assertEqual(receipt["network_calls"], 0)
        self.assertEqual(receipt["model_loads"], 0)

    def test_cli_stdout_is_json_and_contains_no_private_paths(self):
        result = subprocess.run(
            [sys.executable, str(HERE / "demo.py"), "--output-root", str(TEST_RUN / "cli_demo")],
            check=True, capture_output=True, text=True, timeout=20)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["status"], "PASS_SYNTHETIC_SOURCE_BINDING_DEMO")
        self.assertNotIn(str(TEST_RUN), result.stdout)
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SourceBindingTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = {
        "status": "PASS_PORTABLE_SOURCE_BINDING_TESTS" if result.wasSuccessful() else "FAIL",
        "tests_run": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skipped": len(result.skipped),
        "artifact_directory": TEST_RUN.name, "fixtures_retained": True,
        "module_sha256": demo.MODULE_PINS,
        "test_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "network_calls": 0, "model_loads": 0, "bank_cell_executions": 0,
        "synthetic_files_only": True, "official_score": None,
    }
    with (TEST_RUN / "TEST_RESULT.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(receipt, sort_keys=True))
    raise SystemExit(0 if result.wasSuccessful() else 1)

