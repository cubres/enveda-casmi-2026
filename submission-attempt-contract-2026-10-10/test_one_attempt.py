"""Invented controls only. No network or Kaggle operations."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
from threading import Barrier, Thread
import unittest
from unittest.mock import patch
import one_attempt as module
from one_attempt import Binding, Hold, IntentStore, request_once


class IntentTests(unittest.TestCase):
    def setUp(self):
        # Permanently retained invented-fixture directories: no cleanup flow.
        self.directory = Path(tempfile.mkdtemp(prefix="owned-intent-controls-"))
        self.store = IntentStore(self.directory)
        self.binding = Binding("invented-competition", "invented/solver", 7,
                               "submission.csv", "a" * 64)

    def test_accepted_then_repeat_is_blocked(self):
        calls = []
        result = request_once(self.store, self.binding, lambda: calls.append(1) or "123")
        self.assertEqual(result["state"], "ACCEPTED_UNSCORED")
        with self.assertRaises(Hold):
            request_once(self.store, self.binding, lambda: calls.append(2) or "124")
        self.assertEqual(calls, [1])

    def test_unknown_after_acceptance_like_exception_is_not_retried(self):
        calls = []
        def accepted_then_transport_error():
            calls.append(1)
            raise OSError("private exception payload")
        with self.assertRaises(Hold):
            request_once(self.store, self.binding, accepted_then_transport_error)
        with self.assertRaises(Hold):
            request_once(self.store, self.binding, lambda: calls.append(2) or "125")
        self.assertEqual(calls, [1])
        outcome = json.loads(next(self.directory.glob("*.outcome.json")).read_text())
        self.assertEqual(outcome["state"], "UNKNOWN")
        self.assertNotIn("private", json.dumps(outcome))

    def test_missing_or_invalid_response_holds(self):
        for value in (None, "", "0", "secret payload", 123, True):
            store = IntentStore(self.directory / ("case-" + str(len(list(self.directory.iterdir())))))
            with self.assertRaises(Hold):
                request_once(store, self.binding, lambda: value)
            with self.assertRaises(Hold):
                store.admit(self.binding)

    def test_changed_hash_cannot_escape_same_version_latch(self):
        self.store.admit(self.binding)
        changed = replace(self.binding, artifact_sha256="b" * 64)
        self.assertEqual(changed.key(), self.binding.key())
        with self.assertRaises(Hold): self.store.admit(changed)
        with self.assertRaises(Hold): self.store.record_outcome(changed, "126")

    def test_case_alias_cannot_escape_latch(self):
        changed = replace(self.binding, competition="INVENTED-COMPETITION", ref="INVENTED/SOLVER")
        self.assertEqual(changed.key(), self.binding.key())
        self.store.admit(self.binding)
        with self.assertRaises(Hold): self.store.admit(changed)

    def test_changed_file_cannot_escape_same_version_latch(self):
        self.store.admit(self.binding)
        for name in ("SUBMISSION.csv", "other.csv"):
            changed = replace(self.binding, file_name=name)
            self.assertEqual(changed.key(), self.binding.key())
            with self.assertRaises(Hold): self.store.admit(changed)
            with self.assertRaises(Hold): self.store.record_outcome(changed, "126")

    def test_new_version_is_separate(self):
        self.store.admit(self.binding)
        self.store.admit(replace(self.binding, version=8))
        self.assertEqual(len(list(self.directory.glob("*.intent.json"))), 2)

    def test_two_racing_threads_admit_one_request(self):
        barrier = Barrier(2); calls = []; results = []
        def worker():
            barrier.wait()
            try: results.append(request_once(self.store, self.binding, lambda: calls.append(1) or "127")["state"])
            except Hold: results.append("HOLD")
        a = Thread(target=worker); b = Thread(target=worker)
        a.start(); b.start(); a.join(5); b.join(5)
        self.assertFalse(a.is_alive()); self.assertFalse(b.is_alive())
        self.assertEqual(calls, [1]); self.assertCountEqual(results, ["HOLD", "ACCEPTED_UNSCORED"])

    def test_partial_intent_after_process_death_holds(self):
        path = self.directory / (self.binding.key() + ".intent.json")
        with path.open("x") as f: f.write("{")
        with self.assertRaises(Hold): self.store.admit(self.binding)
        with self.assertRaises(Hold): self.store.record_outcome(self.binding, "128")

    def test_fsync_failure_prevents_request_and_retains_latch(self):
        calls = []
        with patch.object(module.os, "fsync", side_effect=OSError("sync failed")):
            with self.assertRaises(OSError):
                request_once(self.store, self.binding, lambda: calls.append(1) or "129")
        self.assertEqual(calls, [])
        with self.assertRaises(Hold): self.store.admit(self.binding)

    def test_outcome_write_failure_prevents_repeat(self):
        calls = []; original = module._durable_exclusive_json
        def fail_outcome(path, value):
            if path.name.endswith(".outcome.json"): raise OSError("disk failed")
            return original(path, value)
        with patch.object(module, "_durable_exclusive_json", side_effect=fail_outcome):
            with self.assertRaises(Hold):
                request_once(self.store, self.binding, lambda: calls.append(1) or "130")
        with self.assertRaises(Hold): self.store.admit(self.binding)
        self.assertEqual(calls, [1])

    def test_keyboard_interrupt_is_unknown_not_retry(self):
        def interrupted(): raise KeyboardInterrupt
        with self.assertRaises(Hold): request_once(self.store, self.binding, interrupted)
        with self.assertRaises(Hold): self.store.admit(self.binding)

    def test_invalid_bindings_do_not_create_intents(self):
        changes = [dict(version=True), dict(version=0), dict(ref="../bad"),
                   dict(competition="bad/path"), dict(file_name="../submission.csv"),
                   dict(artifact_sha256="x" * 64)]
        for values in changes:
            with self.assertRaises(ValueError): self.store.admit(replace(self.binding, **values))
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_outcome_requires_matching_durable_intent(self):
        with self.assertRaises(Hold): self.store.record_outcome(self.binding, "131")
        self.store.admit(self.binding)
        result = self.store.record_outcome(self.binding, "131")
        self.assertEqual(result["artifact_sha256"], self.binding.artifact_sha256)
        with self.assertRaises(FileExistsError): self.store.record_outcome(self.binding, "132")


if __name__ == "__main__": unittest.main()

