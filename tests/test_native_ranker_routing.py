# MIT License
#
# Copyright (c) 2026 cubres
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Synthetic mechanics only; no saved model, molecule, labels or quality metric."""

from dataclasses import replace
import hashlib
import math
import struct
import unittest

from native_ranker_routing import BundleContract, route_query, verify_native_bundle


NAMES = tuple(f"Column_{i}" for i in range(31))
PIPELINE = hashlib.sha256(b"synthetic feature producer only").hexdigest()


def fake_native(*, objective="lambdarank", version="v4", names=NAMES, trees=(0, 1)):
    return ("tree\n" + f"version={version}\nnum_class=1\nnum_tree_per_iteration=1\n"
            + f"max_feature_idx={len(names)-1}\nobjective={objective}\n"
            + "feature_names=" + " ".join(names) + "\n"
            + "".join(f"\nTree={i}\nnum_leaves=1\nleaf_value=0\n" for i in trees)).encode()


def fixture(blob0=None, blob1=None):
    blobs = (blob0 or fake_native(), blob1 or fake_native())
    contract = BundleContract(NAMES, PIPELINE,
                              tuple(hashlib.sha256(b).hexdigest() for b in blobs),
                              "synthetic-4.6.0", 2, 2, 0.90)
    return blobs, contract


class NativeIdentityTests(unittest.TestCase):
    def test_exact_two_synthetic_files_are_accepted(self):
        blobs, contract = fixture()
        self.assertIs(verify_native_bundle(blobs, contract, runtime_version=contract.runtime_version).contract,
                      contract)

    def test_byte_append_is_rejected(self):
        blobs, contract = fixture()
        with self.assertRaisesRegex(ValueError, "hash drift"):
            verify_native_bundle((blobs[0] + b"\n", blobs[1]), contract,
                                 runtime_version=contract.runtime_version)

    def test_swapped_distinct_heads_are_rejected(self):
        blobs, contract = fixture(blob1=fake_native() + b"\nsynthetic second head\n")
        with self.assertRaisesRegex(ValueError, "hash drift"):
            verify_native_bundle(blobs[::-1], contract, runtime_version=contract.runtime_version)

    def test_even_compatible_runtime_version_change_is_rejected(self):
        blobs, contract = fixture()
        with self.assertRaisesRegex(ValueError, "runtime"):
            verify_native_bundle(blobs, contract, runtime_version="synthetic-4.6.1")

    def test_objective_format_and_feature_order_are_checked_after_hash(self):
        for blob in [fake_native(objective="binary"), fake_native(version="v3"),
                     fake_native(names=NAMES[::-1]), fake_native(names=NAMES[:-1])]:
            with self.subTest(blob=blob[:40]):
                blobs, contract = fixture(blob0=blob)
                with self.assertRaisesRegex(ValueError, "schema drift"):
                    verify_native_bundle(blobs, contract, runtime_version=contract.runtime_version)

    def test_missing_duplicated_or_reordered_trees_are_rejected(self):
        for trees in [(0,), (0, 0), (1, 0), (0, 1, 2)]:
            with self.subTest(trees=trees):
                blobs, contract = fixture(blob0=fake_native(trees=trees))
                with self.assertRaisesRegex(ValueError, "tree"):
                    verify_native_bundle(blobs, contract, runtime_version=contract.runtime_version)

    def test_duplicate_header_is_rejected(self):
        blob = fake_native().replace(b"version=v4\n", b"version=v4\nversion=v4\n")
        blobs, contract = fixture(blob0=blob)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify_native_bundle(blobs, contract, runtime_version=contract.runtime_version)

    def test_wrong_head_count_is_rejected(self):
        blobs, contract = fixture()
        with self.assertRaisesRegex(ValueError, "two"):
            verify_native_bundle(blobs[:1], contract, runtime_version=contract.runtime_version)

    def test_malformed_pins_fail_before_prediction(self):
        _, contract = fixture()
        for changes in [dict(feature_names=()), dict(feature_names=("a", "a")),
                        dict(feature_names=("has space",)), dict(feature_pipeline_sha256=""),
                        dict(head_sha256=("bad", "bad")), dict(runtime_version=""),
                        dict(trees_per_head=True), dict(trees_per_head=0),
                        dict(library_max_column=True), dict(library_max_column=31),
                        dict(gate=True), dict(gate=math.nan), dict(gate=1)]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(contract, **changes)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        blobs, contract = fixture()
        self.bundle = verify_native_bundle(blobs, contract, runtime_version=contract.runtime_version)
        self.calls = []
        self.baseline = [0.8, 0.8, 0.1]

    def features(self, maximum=0.2):
        rows = [[0.0] * 31 for _ in range(3)]
        for row in rows:
            row[2] = maximum
        return rows

    def baseline_predict(self, rows):
        self.calls.append(("baseline", rows))
        return self.baseline

    def head(self, index, scores):
        def predict(rows, *, raw_score):
            self.calls.append((index, rows, raw_score))
            self.assertIs(raw_score, True)
            return scores
        return predict

    def run_route(self, rows=None, heads=None, **kwargs):
        arguments = dict(bundle=self.bundle, feature_names=NAMES,
                         feature_pipeline_sha256=PIPELINE,
                         runtime_version=self.bundle.contract.runtime_version,
                         library_max_column=2, gate=0.90)
        arguments.update(kwargs)
        return route_query(self.features() if rows is None else rows, self.baseline_predict,
                           (self.head(0, [-5.0, 9.0, 3.0]), self.head(1, [1.0, 3.0, 1.0]))
                           if heads is None else heads, **arguments)

    def test_open_gate_uses_arithmetic_raw_mean_without_probability_conversion(self):
        result = self.run_route()
        self.assertEqual(result.scores, (-2.0, 6.0, 2.0))
        self.assertEqual([c[0] for c in self.calls], [0, 1])
        self.assertTrue(result.gate_open)
        self.assertEqual(result.source, "native_raw_mean")

    def test_strong_gate_returns_exact_baseline_object_and_inputs_unchanged(self):
        rows = self.features(0.99)
        before = [r[:] for r in rows]
        result = self.run_route(rows)
        self.assertIs(result.scores, self.baseline)
        self.assertIs(self.calls[0][1], rows)
        self.assertEqual([c[0] for c in self.calls], ["baseline"])
        self.assertFalse(result.gate_open)
        self.assertEqual(rows, before)

    def test_literal_gate_equality_is_closed(self):
        self.assertFalse(self.run_route(self.features(0.90)).gate_open)

    def test_float32_point_nine_is_below_literal_gate_and_stays_open(self):
        observed = struct.unpack("f", struct.pack("f", 0.90))[0]
        self.assertLess(observed, 0.90)
        self.assertTrue(self.run_route(self.features(observed)).gate_open)
        self.assertEqual([c[0] for c in self.calls], [0, 1])

    def test_adjacent_float32_above_gate_is_closed(self):
        bits = struct.unpack("I", struct.pack("f", 0.90))[0] + 1
        observed = struct.unpack("f", struct.pack("I", bits))[0]
        self.assertGreater(observed, 0.90)
        self.assertFalse(self.run_route(self.features(observed)).gate_open)

    def test_small_cosine_overshoot_is_preserved_as_strong(self):
        result = self.run_route(self.features(1.0000001192092896))
        self.assertIs(result.scores, self.baseline)
        self.assertEqual(result.library_max, 1.0000001192092896)
        self.assertFalse(result.gate_open)

    def test_ties_keep_input_score_positions_without_sorting(self):
        heads = (self.head(0, [6.0, 2.0, 4.0]), self.head(1, [-2.0, 2.0, 0.0]))
        result = self.run_route(heads=heads)
        self.assertEqual(result.scores, (2.0, 2.0, 2.0))

    def test_short_long_and_ragged_features_fail_before_any_callback(self):
        for width in [30, 32]:
            with self.subTest(width=width), self.assertRaisesRegex(ValueError, "width"):
                self.run_route([[0.0] * width for _ in range(3)])
        rows = self.features(); rows[1].append(0.0)
        with self.assertRaisesRegex(ValueError, "width"):
            self.run_route(rows)
        self.assertEqual(self.calls, [])

    def test_empty_query_fails_before_any_callback(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            self.run_route([])
        self.assertEqual(self.calls, [])

    def test_different_maxima_must_not_be_tolerated_or_averaged(self):
        rows = self.features(); rows[1][2] = math.nextafter(rows[0][2], math.inf)
        with self.assertRaisesRegex(ValueError, "exact query"):
            self.run_route(rows)
        self.assertEqual(self.calls, [])

    def test_nonfinite_or_nonnumeric_features_fail_before_any_callback(self):
        for bad in [math.nan, math.inf, -math.inf, True, "0.1"]:
            rows = self.features(); rows[1][7] = bad
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "finite scalar"):
                self.run_route(rows)
        self.assertEqual(self.calls, [])

    def test_feature_identity_drift_fails_even_for_strong_query(self):
        for overrides in [dict(feature_names=NAMES[::-1]),
                          dict(feature_pipeline_sha256="0" * 64),
                          dict(runtime_version="synthetic-4.6.1")]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.run_route(self.features(0.99), **overrides)
        self.assertEqual(self.calls, [])

    def test_invalid_gate_or_column_fails_before_callbacks(self):
        for overrides in [dict(gate=math.nan), dict(gate=True), dict(gate=-0.1),
                          dict(gate=1.1), dict(library_max_column=31),
                          dict(library_max_column=True)]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.run_route(**overrides)
        self.assertEqual(self.calls, [])

    def test_valid_but_unpinned_gate_or_column_are_rejected(self):
        for overrides in [dict(gate=0.91), dict(library_max_column=0),
                          dict(gate=struct.unpack("f", struct.pack("f", 0.90))[0])]:
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, "policy drift"):
                self.run_route(**overrides)
        self.assertEqual(self.calls, [])

    def test_huge_integer_feature_is_a_validation_failure(self):
        rows = self.features(); rows[0][0] = 10 ** 1000
        with self.assertRaisesRegex(ValueError, "finite scalar"):
            self.run_route(rows)
        self.assertEqual(self.calls, [])

    def test_candidates_over_existing_cap_are_not_silently_removed(self):
        rows = self.features() * 174  # 522 synthetic candidates, no implicit cap.
        values = list(range(len(rows)))
        result = self.run_route(rows, heads=(self.head(0, values), self.head(1, values)))
        self.assertEqual(result.scores, tuple(float(i) for i in values))
        self.assertEqual(len(result.scores), 522)

    def test_invalid_native_score_shapes_and_values_are_rejected(self):
        for bad in [[1.0, 2.0], [[1.0], [2.0], [3.0]], [1.0, math.nan, 3.0],
                    [1.0, math.inf, 3.0], [1.0, True, 3.0], [1.0, "2.0", 3.0]]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.run_route(heads=(self.head(0, bad), self.head(1, [0.0] * 3)))
        self.assertNotIn("baseline", [c[0] for c in self.calls])

    def test_two_finite_heads_with_overflowing_sum_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            self.run_route(heads=(self.head(0, [1.7e308] * 3), self.head(1, [1.7e308] * 3)))

    def test_baseline_shape_and_probability_contracts_are_checked(self):
        for bad in [[0.8], [0.2, math.nan, 0.1], [0.2, 1.01, 0.1], [-0.01, 0.2, 0.1]]:
            self.baseline = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.run_route(self.features(0.99))
        self.assertEqual([c[0] for c in self.calls], ["baseline"] * 4)

    def test_missing_or_extra_heads_are_rejected_before_baseline(self):
        for heads in [(), (self.head(0, [0.0] * 3),), (None, None),
                      (self.head(0, [0.0] * 3),) * 3]:
            with self.subTest(heads=heads), self.assertRaisesRegex(ValueError, "two"):
                self.run_route(self.features(0.99), heads=heads)
        self.assertEqual(self.calls, [])

    def test_native_callback_failure_is_not_silently_promoted_or_fallback_scored(self):
        def broken(rows, *, raw_score):
            raise RuntimeError("synthetic runtime failure")
        with self.assertRaisesRegex(RuntimeError, "synthetic"):
            self.run_route(heads=(broken, self.head(1, [0.0] * 3)))
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
