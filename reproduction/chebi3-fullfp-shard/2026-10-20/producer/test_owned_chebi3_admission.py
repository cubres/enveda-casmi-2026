"""Pure synthetic process/admission fixtures; no chemistry or real processes."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import time
import unittest
from unittest import mock
import build_chebi3_shard as driver
import run_owned_chebi3_shard as wrapper


class FakeExecutor:
    def __init__(self):
        self.calls = 0

    def submit(self, function, jobs):
        self.calls += 1
        result = concurrent.futures.Future()
        result.set_result(([(i, b"fixture", 1.0, "fixture", "fixture") for i, _ in jobs], 0.001))
        return result


class PureAdmissionTests(unittest.TestCase):
    def root_args(self, run):
        manifest = run.parent / "synthetic_manifest.json"
        manifest.write_text('{"files": {}, "scope": "synthetic lifecycle fixture"}')
        return ["fixture", "--old-bank-root", str(run.parent / "synthetic_old"),
            "--external-root", str(run.parent / "synthetic_external"),
            "--old-proof-root", str(run.parent / "synthetic_old_proof"),
            "--run-root", str(run), "--source-manifest", str(manifest),
            "--source-manifest-sha256", hashlib.sha256(manifest.read_bytes()).hexdigest()]

    @unittest.skipUnless(sys.platform == "darwin", "Mac-only lifecycle fixture")
    def test_popen_failure_is_consumed_terminal_without_child(self):
        with tempfile.TemporaryDirectory(prefix="casmi-chebi3-spawn-fixture-") as directory:
            run = Path(directory) / "owned"
            with mock.patch.object(sys, "argv", self.root_args(run)), mock.patch.object(wrapper, "verify_sources", return_value=True), mock.patch.object(wrapper.subprocess, "Popen", side_effect=OSError("synthetic launch failure")):
                self.assertEqual(wrapper.main(), 1)
            self.assertTrue((run / "ATTEMPT_CONSUMED.json").is_file())
            result = json.loads((run / "RESULT.json").read_text())
            self.assertEqual(result["status"], "STOPPED_UNPROMOTABLE")
            self.assertIsNone(result["child_returncode"])
            self.assertEqual(result["reason"], "WRAPPER_EXCEPTION:OSError")

    @unittest.skipUnless(sys.platform == "darwin", "Mac-only lifecycle fixture")
    def test_handle_write_failure_reaps_fake_owned_child(self):
        with tempfile.TemporaryDirectory(prefix="casmi-chebi3-handle-fixture-") as directory:
            run = Path(directory) / "owned"
            child = SimpleNamespace(pid=987654, wait=mock.Mock(return_value=0), poll=mock.Mock(return_value=0))
            original = wrapper.write_json
            def fail_handle(path, value):
                if Path(path).name == "CHILD_HANDLE.json":
                    raise OSError("synthetic handle write failure")
                return original(path, value)
            with mock.patch.object(sys, "argv", self.root_args(run)), mock.patch.object(wrapper, "verify_sources", return_value=True), mock.patch.object(wrapper.subprocess, "Popen", return_value=child), mock.patch.object(wrapper, "own_members", return_value=[]), mock.patch.object(wrapper, "write_json", side_effect=fail_handle):
                self.assertEqual(wrapper.main(), 1)
            child.wait.assert_called_once_with(timeout=10)
            self.assertEqual(json.loads((run / "RESULT.json").read_text())["status"], "STOPPED_UNPROMOTABLE")

    def test_each_resource_limit_stops_with_receipt_reserve(self):
        self.assertIsNone(wrapper.admission_reason(10, 10, 1, 1))
        self.assertEqual(wrapper.admission_reason(1780, 10, 1, 1), "WALL_LIMIT")
        self.assertEqual(wrapper.admission_reason(10, 3601, 1, 1), "CPU_TIME_LIMIT")
        self.assertEqual(wrapper.admission_reason(10, 10, wrapper.RSS_BYTES + 1, 1), "SUMMED_RSS_LIMIT")
        self.assertEqual(wrapper.admission_reason(10, 10, 1, wrapper.OUTPUT_BYTES - 65535), "OWNED_OUTPUT_LIMIT")

    def test_source_pin_drift_missing_extra(self):
        with tempfile.TemporaryDirectory(prefix="casmi-chebi3-source-fixture-") as directory:
            root = Path(directory)
            files = {}
            for name in wrapper.SOURCE_NAMES:
                payload = ("synthetic:" + name).encode()
                (root / name).write_bytes(payload)
                files[name] = {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
            manifest = {"files": files, "scope": "pure fixture"}
            self.assertTrue(wrapper.verify_sources(manifest, root))
            (root / "build_chebi3_shard.py").write_bytes(b"synthetic source drift")
            self.assertFalse(wrapper.verify_sources(manifest, root))
            self.assertFalse(wrapper.verify_sources({"files": {}, "scope": "fixture"}, root))

    def test_receipt_requires_numeric_and_scope_contract(self):
        good = {"status": "COMPLETE_4096_AWAITING_WRAPPER", "rows": 4096, "canary_rows": 64,
            "actual_selected_raw_key_new": 4096, "fingerprints_from_unchanged_baseline_only": True,
            "all_numeric_and_parquet_reloads_exact": True, "no_model_training_assay_hidden_test": True}
        self.assertTrue(wrapper.receipt_is_complete(good))
        for field in good:
            damaged = dict(good)
            damaged.pop(field)
            self.assertFalse(wrapper.receipt_is_complete(damaged))
        self.assertFalse(wrapper.receipt_is_complete(None))

    def test_baseline_chunk64_exact_row_order_and_counts(self):
        executor = FakeExecutor()
        rows = []; times = []
        driver.run_chunks(executor, driver.base.process_chunk, [(i, "fixture") for i in range(64)], rows.append, time.monotonic(), times)
        self.assertEqual(executor.calls, 8)
        self.assertEqual(sorted(x[0] for x in rows), list(range(64)))
        self.assertEqual(len(times), 8)

    def test_expired_driver_starts_no_chunk(self):
        executor = FakeExecutor()
        with self.assertRaisesRegex(RuntimeError, "COMPUTE_DEADLINE"):
            driver.run_chunks(executor, driver.base.process_chunk, [(0, "fixture")], lambda row: None, time.monotonic() - 1641)
        self.assertEqual(executor.calls, 0)

    def test_rolling_rejection_stops_before_next_batch(self):
        executor = FakeExecutor()
        with mock.patch.object(driver, "forecast_budget", return_value={"passes": False}):
            with self.assertRaisesRegex(RuntimeError, "ROLLING_SELECTED"):
                driver.run_chunks(executor, driver.base.process_chunk, [(i, "fixture") for i in range(64, 4096)], lambda row: None, time.monotonic(), [1.0] * 8, completed_before=64)
        self.assertEqual(executor.calls, 4)


if __name__ == "__main__":
    unittest.main()
