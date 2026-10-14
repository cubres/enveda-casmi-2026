"""Registered invented mechanics controls. Not a chemical/model benchmark."""
import unittest
import numpy as np

from packed_window_lab import PackingContract, aligned_window, evaluation_only_expected_rr, mass_window, pack_declared_bits, row_order_digest, score_window, topk_with_ties, unpack_declared_bits, validate_masses, validate_packed
from synthetic_demo import make_synthetic_demo


class WindowLabControls(unittest.TestCase):
    def setUp(self):
        self.m, self.ids, self.bits, self.p, self.l, self.c = make_synthetic_demo()

    def test_inclusive_ppm_boundaries_duplicates_and_adjacent_floats(self):
        self.assertEqual(mass_window(self.m, 100.0, 10.0), (2, 9))

    def test_complete_aligned_interval(self):
        interval, tokens, packed = aligned_window(self.m, self.ids, self.p, self.c, 100.0, expected_row_order_sha256=row_order_digest(self.ids))
        self.assertEqual(interval, (2, 9))
        self.assertEqual(tokens, self.ids[2:9])
        np.testing.assert_array_equal(packed, self.p[2:9])

    def test_row_count_digest_and_duplicate_tokens_fail(self):
        for tokens, packed, digest in ((self.ids[::-1], self.p, row_order_digest(self.ids)), (self.ids, self.p[:-1], row_order_digest(self.ids)), (self.ids, self.p, "0" * 64)):
            with self.assertRaises(ValueError):
                aligned_window(self.m, tokens, packed, self.c, 100.0, expected_row_order_sha256=digest)
        with self.assertRaises(ValueError):
            row_order_digest(("SYN_A", "SYN_A"))

    def test_unknown_producer_or_packing_strict_failure(self):
        for contract in (PackingContract(), PackingContract("UNKNOWN", "unverified", "big"), PackingContract("SYNTHETIC_ONLY", "invented", None), PackingContract("SYNTHETIC_ONLY", "invented", "little", "wrong-layout")):
            with self.assertRaises(ValueError):
                unpack_declared_bits(self.p, contract)

    def test_vector_packed_parity_big_and_little(self):
        expected = self.bits[:, :2048] @ self.l[:2048] + self.bits[:, 2049:2215] @ self.l[2049:2215]
        for order in ("big", "little"):
            contract = PackingContract("SYNTHETIC_ONLY", "invented-demo-v1", order)
            packed = pack_declared_bits(self.bits, contract)
            np.testing.assert_array_equal(unpack_declared_bits(packed, contract), self.bits)
            np.testing.assert_array_equal(score_window(packed, self.l, contract), expected)

    def test_dummy_positions_cannot_contribute(self):
        altered = self.l.copy()
        altered[[2048, 2215]] = [-333.0, 333.0]
        np.testing.assert_array_equal(score_window(self.p, self.l, self.c), score_window(self.p, altered, self.c))

    def test_nonzero_dummy_bits_rejected_for_both_packing_orders(self):
        for order in ("big", "little"):
            c = PackingContract("SYNTHETIC_ONLY", "invented", order)
            for position in (2048, 2215):
                bad = self.bits.copy()
                bad[0, position] = 1
                with self.assertRaises(ValueError):
                    pack_declared_bits(bad, c)
                raw = np.packbits(bad, axis=1, bitorder=order)
                with self.assertRaises(ValueError):
                    validate_packed(raw, c)

    def test_empty_window_and_topk(self):
        interval, ids, packed = aligned_window(self.m, self.ids, self.p, self.c, 175.0, expected_row_order_sha256=row_order_digest(self.ids))
        self.assertEqual(interval, (11, 11))
        scores = score_window(packed, self.l, self.c)
        self.assertEqual(topk_with_ties(scores, ids), {"indices": [], "tokens": [], "tie_groups": []})
        self.assertEqual(evaluation_only_expected_rr(scores, None), 0.0)

    def test_exact_ties_cut_at_k_and_stable_tokens(self):
        scores = np.array([2.0, 1.0, 1.0, 1.0, 0.0])
        out = topk_with_ties(scores, ["SYN_Z", "SYN_C", "SYN_A", "SYN_B", "SYN_X"], k=3)
        self.assertEqual(out["indices"], [0, 2, 3])
        self.assertEqual(out["tie_groups"][1], {"start_rank": 2, "tie_size": 3, "selected_indices": [2, 3]})
        self.assertAlmostEqual(evaluation_only_expected_rr(scores, 1, k=3), (1 / 2 + 1 / 3) / 3)
        self.assertEqual(evaluation_only_expected_rr(scores, 4, k=3), 0.0)

    def test_zero_variance_and_singleton_scores_are_finite(self):
        for n in (0, 1, 4):
            packed = np.zeros((n, 277), dtype=np.uint8)
            scores = score_window(packed, np.zeros(2216), self.c, mode="balanced_prospective")
            np.testing.assert_array_equal(scores, np.zeros(n))

    def test_finite_and_invalid_input_gates(self):
        for axis in (self.m[::-1], self.m.astype(np.float32), np.array([1.0, np.nan]), np.array([0.0]), np.array([1.0, np.inf])):
            with self.assertRaises(ValueError):
                validate_masses(axis)
        for mass, ppm in ((0, 10), (np.nan, 10), (100, 0), (100, 1001), (True, 10), (100, np.inf)):
            with self.assertRaises(ValueError):
                mass_window(self.m, mass, ppm)
        for logits in (np.full(2216, np.nan), np.full(2216, np.inf), np.zeros(2215)):
            with self.assertRaises(ValueError):
                score_window(self.p, logits, self.c)
        with self.assertRaises(ValueError):
            topk_with_ties(np.array([np.nan]), ["SYN_A"])

    def test_invalid_packed_dtype_shape_values_and_cap(self):
        for packed in (self.p.astype(np.float32), self.p[:, :-1], np.zeros((32769, 277), dtype=np.uint8)):
            with self.assertRaises(ValueError):
                validate_packed(packed, self.c, window=True)
        bad = self.bits.copy()
        bad[0, 0] = 2
        with self.assertRaises(ValueError):
            pack_declared_bits(bad, self.c)

    def test_tiny_scale_block_scores_preserve_order(self):
        a = score_window(self.p, self.l, self.c, mode="balanced_prospective")
        b = score_window(self.p, self.l * 1e-200, self.c, mode="balanced_prospective")
        np.testing.assert_allclose(a, b, rtol=1e-12, atol=1e-12)

    def test_no_input_mutation(self):
        saved = (self.m.copy(), self.p.copy(), self.l.copy())
        aligned_window(self.m, self.ids, self.p, self.c, 100.0, expected_row_order_sha256=row_order_digest(self.ids))
        score_window(self.p, self.l, self.c)
        for before, after in zip(saved, (self.m, self.p, self.l)):
            np.testing.assert_array_equal(before, after)


if __name__ == "__main__":
    unittest.main()
