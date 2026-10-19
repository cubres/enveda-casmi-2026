"""Independent mechanics fixtures using invented arrays only.

This does not read public reference arrays, run the producer, import Arrow,
train/evaluate a model, or qualify any real atlas output.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parent
CORE_PATH = ROOT / "source/atlas_core.py"
CORE_BYTES_BEFORE = CORE_PATH.read_bytes()
CORE_SHA_BEFORE = hashlib.sha256(CORE_BYTES_BEFORE).hexdigest()
spec = importlib.util.spec_from_file_location("reviewed_atlas_core", CORE_PATH)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def packed(bit_sets):
    result = np.zeros((len(bit_sets), 1300), dtype=np.uint8)
    for row, bits in enumerate(bit_sets):
        for bit in bits:
            if not 0 <= bit < 10395:
                raise ValueError("fixture bit outside valid range")
            result[row, bit // 8] |= np.uint8(1 << (7 - bit % 8))
    return result


def bank(masses, groups):
    masses = np.asarray(masses, dtype=np.float64)
    return masses, np.argsort(masses, kind="stable"), np.asarray(groups, dtype=object)


def result_arrays(fp, query, candidates, size=256):
    count = core.packed_counts(fp)
    parts = list(core.similarity_batches(fp, count, query, np.asarray(candidates, dtype=np.int64), size))
    return tuple(np.concatenate([part[i] for part in parts]) for i in range(6))


class InventedCoreTests(unittest.TestCase):
    def test_closed_endpoints_and_adjacent_float_exclusions(self):
        q, ppm = 100.0, 10.0
        delta = q * ppm * 1e-6
        low, high = q - delta, q + delta
        masses, order, _ = bank([q, high, low, np.nextafter(low, -np.inf),
                                 np.nextafter(high, np.inf), low], list("ABCDEF"))
        actual = core.closed_window(masses, order, q, ppm)
        np.testing.assert_array_equal(actual, [2, 5, 0, 1])
        expected = order[(masses[order] >= low) & (masses[order] <= high)]
        np.testing.assert_array_equal(actual, expected)

    def test_query_denominator_gives_directional_asymmetry(self):
        masses, order, groups = bank([100.0, 100.001000005], ["A", "B"])
        forward, rows_forward = core.query_policy(masses, order, groups, 0)
        reverse, rows_reverse = core.query_policy(masses, order, groups, 1)
        self.assertEqual(forward["selected_ppm"], 30)
        self.assertTrue(forward["fallback_used"])
        self.assertEqual(reverse["selected_ppm"], 10)
        self.assertFalse(reverse["fallback_used"])
        np.testing.assert_array_equal(rows_forward, [1])
        np.testing.assert_array_equal(rows_reverse, [0])

    def test_same_group_ten_only_does_not_block_fallback(self):
        masses, order, groups = bank([100.0, 100.0005, 100.002], ["A", "A", "B"])
        info, rows = core.query_policy(masses, order, groups, 0)
        self.assertEqual(info["rows_10ppm"], 0)
        self.assertEqual(info["selected_ppm"], 30)
        self.assertTrue(info["fallback_used"])
        np.testing.assert_array_equal(rows, [2])

    def test_all_ten_preferred_over_thirty_superset(self):
        masses, order, groups = bank([100.0, 100.0002, 100.0007, 100.002], ["A", "B", "C", "D"])
        info, rows = core.query_policy(masses, order, groups, 0)
        self.assertEqual(info["rows_10ppm"], 2)
        self.assertEqual(info["rows_30ppm"], 3)
        self.assertEqual(info["selected_ppm"], 10)
        np.testing.assert_array_equal(rows, [1, 2])

    def test_duplicate_peer_groups_count_rows_and_groups_separately(self):
        masses, order, groups = bank([100.0, 100.0002, 100.0003], ["A", "B", "B"])
        info, rows = core.query_policy(masses, order, groups, 0)
        self.assertEqual(info["selected_rows"], 2)
        self.assertEqual(info["selected_groups"], 1)
        np.testing.assert_array_equal(rows, [1, 2])

    def test_every_empty_query_is_retained_by_policy_iteration(self):
        masses, order, groups = bank([80.0, 100.0, 1400.0], ["A", "B", "C"])
        summaries = [core.query_policy(masses, order, groups, q) for q in range(len(masses))]
        self.assertEqual(len(summaries), 3)
        for info, rows in summaries:
            self.assertIsNone(info["selected_ppm"])
            self.assertEqual(info["selected_rows"], 0)
            self.assertEqual(info["selected_groups"], 0)
            self.assertFalse(info["fallback_used"])
            self.assertEqual(len(rows), 0)

    def test_msb_first_final_valid_bit_and_exact_set_oracle(self):
        fp = packed([{0, 1, 10394}, {1, 8, 10394}])
        self.assertEqual(int(fp[0, 0]), 0xC0)
        self.assertEqual(int(fp[0, -1]), 0x20)
        self.assertEqual(int(fp[1, 1]), 0x80)
        rows, intersection, union, candidate_count, jac, cos = result_arrays(fp, 0, [1])
        np.testing.assert_array_equal(rows, [1])
        self.assertEqual((int(intersection[0]), int(union[0]), int(candidate_count[0])), (2, 4, 3))
        self.assertEqual(float(jac[0]), 0.5)
        self.assertAlmostEqual(float(cos[0]), 2 / 3, places=15)
        self.assertEqual(core.exact_integer_pair(fp[0], fp[1]), (2, 4, 3, 3))

    def test_zero_vectors_have_explicit_undefined_ratios(self):
        fp = packed([set(), set(), {2}])
        _, _, _, _, jac, cos = result_arrays(fp, 0, [1, 2])
        self.assertTrue(math.isnan(float(jac[0])))
        self.assertTrue(math.isnan(float(cos[0])))
        self.assertEqual(float(jac[1]), 0.0)
        self.assertTrue(math.isnan(float(cos[1])))
        _, _, _, _, jac_reverse, cos_reverse = result_arrays(fp, 2, [0])
        self.assertEqual(float(jac_reverse[0]), 0.0)
        self.assertTrue(math.isnan(float(cos_reverse[0])))

    def test_full_bit_counts_do_not_overflow_count_or_norm_product(self):
        fp = packed([set(range(10395)), set(range(10395))])
        np.testing.assert_array_equal(core.packed_counts(fp), [10395, 10395])
        _, inter, union, count, jac, cos = result_arrays(fp, 0, [1])
        self.assertEqual(10395 * 10395, 108056025)
        self.assertEqual((int(inter[0]), int(union[0]), int(count[0])), (10395, 10395, 10395))
        self.assertEqual((float(jac[0]), float(cos[0])), (1.0, 1.0))

    def test_batch_sizes_are_identical_across_299_candidates(self):
        fp = packed([{i, (i * 31 + 1) % 10395} for i in range(300)])
        expected = result_arrays(fp, 0, np.arange(1, 300), 1)
        for size in (7, 64, 256):
            actual = result_arrays(fp, 0, np.arange(1, 300), size)
            for want, got in zip(expected, actual):
                np.testing.assert_array_equal(want, got)

    def test_invalid_packing_rejected(self):
        invalid = [np.zeros((1, 1299), dtype=np.uint8), np.zeros((1, 1300), dtype=np.float64),
                   np.zeros(1300, dtype=np.uint8)]
        padding = np.zeros((1, 1300), dtype=np.uint8)
        padding[0, -1] = 1
        invalid.append(padding)
        for value in invalid:
            with self.subTest(shape=value.shape, dtype=str(value.dtype)):
                with self.assertRaises(ValueError):
                    core.packed_counts(value)

    def test_invalid_window_scalars_rejected(self):
        masses, order, _ = bank([100.0], ["A"])
        for q, ppm in [(0, 10), (-1, 10), (math.nan, 10), (math.inf, 10),
                       (100, 0), (100, -1), (100, math.nan), (100, math.inf)]:
            with self.subTest(q=q, ppm=ppm):
                with self.assertRaises(ValueError):
                    core.closed_window(masses, order, q, ppm)

    def test_invalid_policy_query_indices_rejected(self):
        masses, order, groups = bank([100.0, 101.0], ["A", "B"])
        for q in (-1, 2, True, np.bool_(False), 0.5):
            with self.subTest(query=q):
                with self.assertRaises(ValueError):
                    core.query_policy(masses, order, groups, q)

    def test_invalid_similarity_batch_and_indices_rejected(self):
        fp = packed([{0}, {1}])
        counts = core.packed_counts(fp)
        for size in (True, 0, -1, 257, 1.5):
            with self.subTest(batch_size=size):
                with self.assertRaises(ValueError):
                    list(core.similarity_batches(fp, counts, 0, np.asarray([1]), size))
        for q in (-1, 2, True, np.bool_(False), 0.5):
            with self.subTest(query=q):
                with self.assertRaises(ValueError):
                    list(core.similarity_batches(fp, counts, q, np.asarray([1])))
        for candidates in (np.asarray([-1]), np.asarray([2]), np.asarray([0.5]),
                           np.asarray([[1]]), np.asarray([True])):
            with self.subTest(candidates=candidates.tolist()):
                with self.assertRaises(ValueError):
                    list(core.similarity_batches(fp, counts, 0, candidates))

    def test_invalid_count_vectors_rejected(self):
        fp = packed([{0}, {1}])
        for counts in (np.asarray([1]), np.asarray([1.0, 1.0]), np.asarray([-1, 1]),
                       np.asarray([10396, 1])):
            with self.subTest(counts=counts.tolist()):
                with self.assertRaises(ValueError):
                    list(core.similarity_batches(fp, counts, 0, np.asarray([1])))

    def test_empty_valid_candidate_list_yields_no_batches(self):
        fp = packed([{0}])
        self.assertEqual(list(core.similarity_batches(fp, core.packed_counts(fp), 0,
                                                     np.asarray([], dtype=np.int64))), [])


def main():
    started = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(InventedCoreTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = hashlib.sha256(CORE_PATH.read_bytes()).hexdigest()
    status = "PASS_INVENTED_CORE_MECHANICS_ONLY" if result.wasSuccessful() and after == CORE_SHA_BEFORE else "FAIL"
    receipt = {"status": status, "tests": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "seconds": time.monotonic() - started,
               "python": sys.version.split()[0], "numpy": np.__version__,
               "core_sha256_before": CORE_SHA_BEFORE, "core_sha256_after": after,
               "fixture_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "data_scope": "Tiny invented in-memory arrays only; largest fixture is 300x1300 uint8",
               "not_performed": ["real-array read/hash", "producer/wrapper execution", "PyArrow import",
                                 "model loading", "inference/training/assay", "network/native action"],
               "limitations": "Core mechanics only; does not measure real coverage, resource use, producer output completeness or score"}
    path = ROOT / "INDEPENDENT_INVENTED_CORE_FIXTURE_RECEIPT.json"
    with path.open("x") as stream:
        stream.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    if status == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
