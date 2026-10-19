"""Pure source/admission fixtures; no RDKit, datasets, processes or canaries."""
import concurrent.futures
import hashlib
import tempfile
import time
import sys
import json
from types import SimpleNamespace
from pathlib import Path
import unittest
from unittest import mock
import canary_macos as canary
import run_owned_macos_canary as wrapper


class FakeExecutor:
    def submit(self, function, group):
        future = concurrent.futures.Future()
        future.set_result(([(i, b"fixture", 1.0, "fixture", "fixture") for i, _ in group], 0.001))
        return future


class PureMacAdmissionTests(unittest.TestCase):
    def root_args(self, run_root):
        source = Path(wrapper.__file__).resolve().parent
        manifest = source / "SOURCE_MANIFEST.json"
        return ["fixture", "--old-bank-root", str(run_root.parent / "synthetic_old"),
                "--external-root", str(run_root.parent / "synthetic_external"),
                "--run-root", str(run_root), "--source-manifest", str(manifest),
                "--source-manifest-sha256", hashlib.sha256(manifest.read_bytes()).hexdigest()]

    @unittest.skipUnless(sys.platform == "darwin", "Mac-only wrapper lifecycle")
    def test_popen_failure_is_consumed_terminal_without_child(self):
        with tempfile.TemporaryDirectory(prefix="casmi-mac-spawn-fixture-") as directory:
            run = Path(directory) / "owned"
            with mock.patch.object(sys, "argv", self.root_args(run)), mock.patch.object(wrapper.subprocess, "Popen", side_effect=OSError("synthetic launch failure")):
                self.assertEqual(wrapper.main(), 1)
            self.assertTrue((run / "ATTEMPT_CONSUMED.json").is_file())
            result = json.loads((run / "RESULT.json").read_text())
            self.assertEqual(result["status"], "STOPPED_UNPROMOTABLE")
            self.assertIsNone(result["child_returncode"])

    @unittest.skipUnless(sys.platform == "darwin", "Mac-only wrapper lifecycle")
    def test_handle_write_failure_reaps_owned_fake_child(self):
        with tempfile.TemporaryDirectory(prefix="casmi-mac-handle-fixture-") as directory:
            run = Path(directory) / "owned"
            child = SimpleNamespace(pid=987654, wait=mock.Mock(return_value=0), poll=mock.Mock(return_value=0))
            original = wrapper.write_json
            def fail_handle(path, value):
                if Path(path).name == "CHILD_HANDLE.json":
                    raise OSError("synthetic handle write failure")
                return original(path, value)
            with mock.patch.object(sys, "argv", self.root_args(run)), mock.patch.object(wrapper.subprocess, "Popen", return_value=child), mock.patch.object(wrapper, "own_members", return_value=[]), mock.patch.object(wrapper, "write_json", side_effect=fail_handle):
                self.assertEqual(wrapper.main(), 1)
            child.wait.assert_called_once_with(timeout=10)
            self.assertEqual(json.loads((run / "RESULT.json").read_text())["status"], "STOPPED_UNPROMOTABLE")

    def test_exactly_512_completion_without_chemistry(self):
        received = []
        timings = canary.jobs_only_512(FakeExecutor(), [(i, "fixture") for i in range(512)], received.append, time.monotonic())
        self.assertEqual(len(received), 512)
        self.assertEqual(len(timings), 16)
        self.assertEqual({x[0] for x in received}, set(range(512)))

    def test_more_than_canary_rows_cannot_continue(self):
        with self.assertRaises(RuntimeError):
            canary.jobs_only_512(FakeExecutor(), [(i, "fixture") for i in range(513)], lambda row: None, time.monotonic())

    def test_duplicate_source_rows_reject(self):
        with self.assertRaises(RuntimeError):
            canary.jobs_only_512(FakeExecutor(), [(0, "fixture")] * 512, lambda row: None, time.monotonic())

    def test_expired_inner_canary_does_no_work(self):
        with self.assertRaises(RuntimeError):
            canary.jobs_only_512(FakeExecutor(), [(i, "fixture") for i in range(512)], lambda row: None, time.monotonic() - 241)

    def test_each_resource_limit_stops(self):
        self.assertIsNone(wrapper.admission_reason(10, 10, 1, 1))
        self.assertEqual(wrapper.admission_reason(280, 10, 1, 1), "WALL_LIMIT")
        self.assertEqual(wrapper.admission_reason(10, 601, 1, 1), "CPU_TIME_LIMIT")
        self.assertEqual(wrapper.admission_reason(10, 10, wrapper.RSS_BYTES + 1, 1), "SUMMED_RSS_LIMIT")
        self.assertEqual(wrapper.admission_reason(10, 10, 1, wrapper.OUTPUT_BYTES + 1), "OWNED_OUTPUT_LIMIT")

    def test_exact_source_pins_drift_and_extra_resources(self):
        with tempfile.TemporaryDirectory(prefix="casmi-mac-source-fixture-") as directory:
            root = Path(directory); files = {}
            for name in wrapper.SOURCE_NAMES:
                payload = ("fixture:" + name).encode(); (root / name).write_bytes(payload)
                files[name] = {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
            manifest = {"files": files, "scope": "pure fixture"}
            self.assertTrue(wrapper.verify_sources(manifest, root))
            (root / "canary_macos.py").write_bytes(b"fixture source drift")
            self.assertFalse(wrapper.verify_sources(manifest, root))
            self.assertFalse(wrapper.verify_sources({"files": {}, "scope": "fixture"}, root))


if __name__ == "__main__":
    unittest.main()
