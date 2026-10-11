# SPDX-License-Identifier: MIT
import math
import random
import unittest
from fragment_consensus import candidate_features, _assignment, _covered_fraction


def view(mz, it=None):
    return {"mz": mz, "intensity": it or [1.0]*len(mz), "window": [40.0, 300.0]}


def brute(ions, peaks, a, p):
    # Independent exhaustive unordered matching oracle; at most 5 x 5.
    best = 0.0
    def visit(k, used, weight):
        nonlocal best
        if k == len(peaks):
            best = max(best, weight)
            return
        visit(k+1, used, weight)
        m, w = peaks[k]
        for j, ion in enumerate(ions):
            if j not in used and abs(m-ion) <= max(a, p*m):
                visit(k+1, used | {j}, weight+w)
    visit(0, set(), 0.0)
    return best/sum(w for _, w in peaks)


class Contracts(unittest.TestCase):
    def test_one_ion_cannot_explain_two_peaks(self):
        result = candidate_features([100.0], [view([99.999, 100.001], [100, 81])])
        self.assertAlmostEqual(result["per_view"][0]["assignment"], 10/19)
        self.assertEqual(result["per_view"][0]["independent_explain"], 1)

    def test_choose_weight_instead_of_first_peak(self):
        result = candidate_features([100.0], [view([99.999, 100.001], [1, 100])])
        self.assertAlmostEqual(result["per_view"][0]["assignment"], 10/11)

    def test_assignment_reassigns_an_ion_when_greedy_would_fail(self):
        result = candidate_features([100.0, 100.009], [view([100.008, 100.015])])
        self.assertAlmostEqual(result["per_view"][0]["assignment"], 1)

    def test_distinct_ions_explain_distinct_peaks(self):
        result = candidate_features([100, 150, 200], [view([100, 150, 200])])
        self.assertAlmostEqual(result["per_view"][0]["assignment"], 1)

    def test_exact_duplicate_hypotheses_do_not_add_capacity(self):
        first = candidate_features([100, 100], [view([99.999, 100.001])])
        second = candidate_features([100], [view([99.999, 100.001])])
        self.assertEqual(first, second)

    def test_permutation_invariance(self):
        first = candidate_features([150, 100], [view([150, 100, 180], [9, 16, 1])])
        second = candidate_features([100, 150], [view([180, 150, 100], [1, 9, 16])])
        self.assertEqual(first, second)

    def test_no_match(self):
        result = candidate_features([220], [view([100, 150])])
        self.assertEqual(result["per_view"][0]["assignment"], 0)
        self.assertLess(result["per_view"][0]["uniform_excess"], 0)

    def test_cross_spectrum_consensus_resists_one_accidental_view(self):
        spectra = [view([100, 150]), view([110, 160]), view([120, 170])]
        result = candidate_features([100, 150], spectra)
        names = dict(zip(result["feature_names"], result["features"]))
        self.assertEqual(names["assignment_max"], 1)
        self.assertEqual(names["assignment_median"], 0)
        self.assertEqual(names["assignment_q25"], 0)

    def test_union_not_sum_of_overlapping_intervals(self):
        self.assertAlmostEqual(_covered_fraction([100, 100.01], (99, 101), .01, 0), .03/2)

    def test_ppm_null_interval_uses_observation_mass(self):
        lo, hi = 900, 1100
        p = .001
        expected = (1000/(1-p)-1000/(1+p))/(hi-lo)
        self.assertAlmostEqual(_covered_fraction([1000], (lo, hi), .01, p), expected)

    def test_density_baseline_is_near_one_for_dense_hypotheses(self):
        dense = [40+i*.02 for i in range(1001)]
        spectra = [{"mz":[42,47,53,58],"intensity":[1,1,1,1],"window":[40,60]}]
        result = candidate_features(dense, spectra, abs_tol=.011, ppm=0)
        self.assertEqual(result["per_view"][0]["assignment"], 1)
        self.assertAlmostEqual(result["per_view"][0]["uniform_excess"], 0)

    def test_view_budget_fails_closed(self):
        ions = [50+i*.001 for i in range(2048)]
        spectra = [view([50+i*.001 for i in range(256)]) for _ in range(16)]
        self.assertEqual(len(ions)*sum(len(v["mz"]) for v in spectra), 8388608)
        with self.assertRaises(ValueError):
            candidate_features(ions, spectra+[spectra[0]])

    def test_invalid_inputs_fail_closed(self):
        bad = [
            ([], [view([100])]),
            ([math.nan], [view([100])]),
            ([True], [view([100])]),
            ([100], []),
            ([100], [{"mz":[100],"intensity":[0],"window":[40,300]}]),
            ([100], [{"mz":[100],"intensity":[-1],"window":[40,300]}]),
            ([100], [{"mz":[100],"intensity":[1],"window":[100,100]}]),
            ([100], [{"mz":[301],"intensity":[1],"window":[40,300]}]),
            ([100], [{"mz":[100],"intensity":[1,2],"window":[40,300]}]),
            ([100]*2049, [view([100])]),
            ([100], [view([100]*257)]),
        ]
        for ions, spectra in bad:
            with self.subTest(ions=ions[:2], spectra_count=len(spectra)):
                with self.assertRaises(ValueError):
                    candidate_features(ions, spectra)
        for kwargs in [{"abs_tol":0}, {"abs_tol":.2}, {"ppm":-1}, {"ppm":1001}, {"ppm":True}]:
            with self.assertRaises(ValueError):
                candidate_features([100], [view([100])], **kwargs)

    def test_exhaustive_unordered_oracle_200_cases(self):
        rng = random.Random(11)
        for _ in range(200):
            n, m = rng.randint(1,5), rng.randint(1,5)
            ions = sorted(set(100+rng.randint(0,12)*.002 for _ in range(n)))
            peaks = sorted((100+rng.randint(0,12)*.002, float(rng.randint(1,9))) for _ in range(m))
            a, p = .004, rng.choice([0.0, .00004])
            exact, independent = _assignment(ions, peaks, a, p)
            self.assertAlmostEqual(exact, brute(ions, peaks, a, p), places=12)
            self.assertLessEqual(exact, independent+1e-12)
            self.assertGreaterEqual(exact, 0)
            self.assertLessEqual(exact, 1+1e-12)


if __name__ == "__main__":
    unittest.main()

