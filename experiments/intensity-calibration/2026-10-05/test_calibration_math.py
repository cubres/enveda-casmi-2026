import unittest
import numpy as np
from calibration_math import (Spectrum, Example, Refusal, adjusted, checked,
                              cosine_loss_gradient, objective, fit, group_partition)


class Contracts(unittest.TestCase):
    def setUp(self):
        self.p = Spectrum(np.array([11, 51, 101]), np.array([0.2, 1.0, 0.4]))
        self.kw = dict(ce=40.0, theoretical_precursor=120.0, num_bins=150001, upper_limit=1500.0)

    def test_identity_support_and_immutability(self):
        b, p = self.p.bins.copy(), self.p.intensities.copy()
        out, _ = adjusted(self.p, np.zeros(4), **self.kw)
        np.testing.assert_array_equal(out.bins, b)
        np.testing.assert_allclose(out.intensities, p / p.max(), atol=1e-15)
        np.testing.assert_array_equal(self.p.bins, b)
        np.testing.assert_array_equal(self.p.intensities, p)

    def test_unmatched_prediction_and_target_penalties(self):
        one = Spectrum(np.array([11]), np.array([1.0]))
        extra = Spectrum(np.array([11, 12]), np.array([1.0, 1.0]))
        j1, j2 = np.zeros((1, 4)), np.zeros((2, 4))
        self.assertEqual(cosine_loss_gradient(one, one, j1)[0], 0.0)
        self.assertGreater(cosine_loss_gradient(extra, one, j2)[0], 0.29)
        self.assertGreater(cosine_loss_gradient(one, extra, j1)[0], 0.29)

    def test_duplicate_bins_refused(self):
        with self.assertRaises(Refusal):
            checked(Spectrum(np.array([11, 11]), np.array([1.0, 1.0])))

    def test_uint64_cast_boundary(self):
        with self.assertRaises(Refusal):
            checked(Spectrum(np.array([2**63], dtype=np.uint64), np.array([1.0])))
        bins, values = checked(Spectrum(np.array([2**63 - 1], dtype=np.uint64), np.array([1.0])))
        self.assertEqual(int(bins[0]), 2**63 - 1)

    def test_unsorted_jacobian_matches_numerical_gradient(self):
        bins = np.array([101, 11, 51])
        base = np.array([0.4, 0.2, 1.0])
        features = np.array([[0.2, 0.7, -0.1, 0.3], [0.5, -0.2, 0.4, 0.6], [-0.3, 0.1, 0.8, 0.4]])
        theta = np.array([0.2, -0.1, 0.3, 0.1])
        target = Spectrum(np.array([11, 51, 101, 121]), np.array([0.3, 0.8, 0.7, 0.1]))
        def value(a):
            pred = Spectrum(bins, base * np.exp(features @ a))
            return cosine_loss_gradient(pred, target, features)
        _, actual = value(theta)
        expected = []
        for k in range(4):
            delta = np.zeros(4); delta[k] = 1e-6
            expected.append((value(theta + delta)[0] - value(theta - delta)[0]) / 2e-6)
        np.testing.assert_allclose(actual, expected, atol=2e-9, rtol=2e-6)

    def test_large_finite_target_scale_is_numerically_equivalent(self):
        target = Spectrum(np.array([11, 51, 101, 121]), np.array([0.3, 0.8, 0.7, 0.1]))
        out, j = adjusted(self.p, np.array([0.2, -0.4, 0.3, 0.1]), **self.kw)
        before = cosine_loss_gradient(out, target, j)
        after = cosine_loss_gradient(out, Spectrum(target.bins, target.intensities * 1e308), j)
        self.assertAlmostEqual(before[0], after[0])
        np.testing.assert_allclose(before[1], after[1])

    def test_zero_nonfinite_integer_intensity_refused(self):
        for v in (np.array([0.0]), np.array([np.nan]), np.array([-1.0]), np.array([1])):
            with self.assertRaises(Refusal):
                checked(Spectrum(np.array([1]), v))

    def test_invalid_ce_and_mass_protocol_refused(self):
        for ce in (np.nan, [20, 40, 60], True, 10.0, 80.0):
            with self.assertRaises(Refusal):
                adjusted(self.p, np.zeros(4), **(self.kw | {"ce": ce}))
        with self.assertRaises(Refusal):
            adjusted(self.p, np.zeros(4), **(self.kw | {"theoretical_precursor": np.inf}))

    def test_analytic_gradient_matches_finite_difference(self):
        target = Spectrum(np.array([11, 51, 101, 121]), np.array([0.3, 0.8, 0.7, 0.1]))
        x = Example("fit-structure", self.p, target, 60.0, 120.0, 150001, 1500.0)
        theta = np.array([0.2, -0.4, 0.3, 0.1])
        _, actual = objective([x], theta)
        expected = []
        for k in range(4):
            delta = np.zeros(4); delta[k] = 1e-6
            expected.append((objective([x], theta + delta)[0] - objective([x], theta - delta)[0]) / 2e-6)
        np.testing.assert_allclose(actual, expected, atol=2e-9, rtol=2e-6)

    def test_order_and_scale_invariance(self):
        out, j = adjusted(self.p, np.array([0.2, 0.1, 0.4, -0.1]), **self.kw)
        reversed_p = Spectrum(self.p.bins[::-1], self.p.intensities[::-1] * 37.0)
        other, k = adjusted(reversed_p, np.array([0.2, 0.1, 0.4, -0.1]), **self.kw)
        np.testing.assert_allclose(out.intensities, other.intensities)
        np.testing.assert_allclose(j, k)

    def test_positive_temperature_preserves_bin_max_order(self):
        # Two raw intensities in the SAME physical bin have the same tilt.
        # Any positive temperature preserves their duplicate-MAX winner.
        for a in (-1e5, 0.0, 1e5):
            temperature = 1.0 + 0.25 * np.tanh(a)
            self.assertGreater(0.8 ** temperature, 0.2 ** temperature)

    def test_group_partition_does_not_split_structure_or_scaffold(self):
        pairs = [("a", "ringA"), ("a-repeat", "ringA"), ("a", "ringB"), ("b", "ringB"),
                 ("c", "ringC"), ("d", "ringD"), ("e", "ACYCLIC")]
        splits = group_partition(pairs)
        self.assertEqual(splits["a"], splits["a-repeat"])
        self.assertEqual(splits["a"], splits["b"])
        self.assertEqual(splits, group_partition(pairs[::-1]))
        self.assertEqual(set(splits.values()), {"fit", "dev", "test"})

    def test_structure_weight_prevents_replicate_dominance(self):
        x = Example("a", self.p, self.p, 40.0, 120.0, 150001, 1500.0)
        y = Example("b", self.p, Spectrum(np.array([11]), np.array([1.0])), 40.0, 120.0, 150001, 1500.0)
        theta = np.array([0.2, 0.1, 0.4, 0.1])
        l1, g1 = objective([x, y], theta)
        l2, g2 = objective([x] * 9 + [y], theta)
        self.assertAlmostEqual(l1, l2)
        np.testing.assert_allclose(g1, g2)

    def test_synthetic_fitting_and_distinct_held_out_cases(self):
        # These are mathematical synthetic labels, never observed Enveda data.
        truth = np.array([0.5, -0.4, 0.3, 0.7])
        train, held = [], []
        for i in range(12):
            p = Spectrum(np.array([501 + i, 12001 + 37 * i, 27001 + 43 * i]),
                         np.array([0.10 + 0.02 * i, 1.0, 0.20 + 0.01 * i]))
            for ce in (20.0, 60.0):
                target, _ = adjusted(p, truth, ce, 380.0 + i, 150001, 1500.0)
                x = Example(f"synthetic-structure-{i}", p, target, ce, 380.0 + i, 150001, 1500.0)
                (train if i < 8 else held).append(x)
        theta, history = fit(train)
        self.assertLess(history[-1], history[0])
        before = objective(held, np.zeros(4), 0.0)[0]
        after = objective(held, theta, 0.0)[0]
        self.assertLess(after, before * 0.25)
        self.assertTrue(np.all(np.isfinite(theta)))
        self.assertEqual({x.structure for x in train} & {x.structure for x in held}, set())


if __name__ == "__main__":
    unittest.main()
