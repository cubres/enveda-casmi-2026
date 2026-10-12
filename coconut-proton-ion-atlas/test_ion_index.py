"""MIT-licensed adverse mechanics tests. All masses here are invented fixtures."""
import unittest
import numpy as np

from ion_index import (BY_LABEL, CHANNELS, PROTON_MASS_U, finite_positive,
                       inclusive_window, ppm_width, query)


class IonMechanics(unittest.TestCase):
    def test_all_eight_channels_round_trip(self):
        for c in CHANNELS:
            for mass in (100.0, 300.0, 1299.0):
                with self.subTest(adduct=c.label, mass=mass):
                    self.assertAlmostEqual(float(c.neutral_mass(c.precursor_mz(mass))),
                                           mass, places=12)

    def test_monotonic_source_positions(self):
        mass = np.array([100.0, 100.0, 101.0, 1000.0], dtype="<f8")
        for c in CHANNELS:
            ions = c.precursor_mz(mass)
            self.assertTrue(np.all(ions[1:] >= ions[:-1]))
            self.assertEqual(ions[0], ions[1])

    def test_proton_is_not_hydrogen_atom(self):
        self.assertAlmostEqual(PROTON_MASS_U, 1.0072764665789, places=13)
        self.assertLess(PROTON_MASS_U, 1.007825)

    def test_negative_double_charge_uses_absolute_charge(self):
        c = BY_LABEL["[M-2H]2-"]
        self.assertAlmostEqual(c.precursor_mz(300.0), 150.0 - PROTON_MASS_U)

    def test_dimer_inverts_molecule_multiplier(self):
        c = BY_LABEL["[2M+H]+"]
        self.assertAlmostEqual(c.neutral_mass(601.0072764665789), 300.0)

    def test_both_endpoints_and_duplicates(self):
        center, ppm = 300.0, 10.0
        width = ppm_width(center, ppm)
        low, high = center - width, center + width
        mass = np.array([np.nextafter(low, -np.inf), low, low, center,
                         high, high, np.nextafter(high, np.inf)])
        self.assertEqual(inclusive_window(mass, center, ppm), (1, 6))

    def test_zero_ppm_keeps_all_equal_masses(self):
        mass = np.array([299.0, 300.0, 300.0, 300.0, 301.0])
        self.assertEqual(inclusive_window(mass, 300.0, 0.0), (1, 4))

    def test_empty_window(self):
        self.assertEqual(inclusive_window(np.array([200.0, 400.0]), 300.0, 10.0), (1, 1))

    def test_finite_inputs_cannot_overflow_interval_endpoints(self):
        with self.assertRaises(ValueError):
            inclusive_window(np.array([200.0, 400.0]), 1.5e308, 1e6)

    def test_numerical_bad_centers(self):
        for x in (False, 0.0, -1.0, np.nan, np.inf, -np.inf):
            with self.subTest(value=x):
                with self.assertRaises(ValueError):
                    finite_positive(x, "mass")

    def test_bad_ppm(self):
        for ppm in (True, -1.0, np.nan, np.inf):
            with self.subTest(value=ppm):
                with self.assertRaises(ValueError):
                    ppm_width(300.0, ppm)

    def fake_maps(self):
        neutral = np.array([100.0, 299.997, 300.0, 300.003, 400.0])
        ions = {c.label: c.precursor_mz(neutral) for c in CHANNELS}
        return {}, neutral, ions

    def test_all_adducts_retain_center_row(self):
        maps = self.fake_maps()
        for c in CHANNELS:
            answer = query(maps, float(c.precursor_mz(300.0)), c.label, 10.0,
                           polarity=c.polarity)
            self.assertLessEqual(answer["source_row_start"], 2)
            self.assertGreater(answer["source_row_stop_exclusive"], 2)

    def test_polarity_rejected(self):
        with self.assertRaises(ValueError):
            query(self.fake_maps(), 300.0, "[M+H]+", polarity="negative")

    def test_unknown_adduct_rejected(self):
        with self.assertRaises(ValueError):
            query(self.fake_maps(), 300.0, "[M+Na]+")

    def test_unknown_ppm_basis_rejected(self):
        with self.assertRaises(ValueError):
            query(self.fake_maps(), 300.0, "[M+H]+", tolerance_basis="implicit")

    def test_precursor_and_neutral_widths_are_distinct(self):
        maps = self.fake_maps()
        c = BY_LABEL["[2M+H]+"]
        mz = float(c.precursor_mz(300.0))
        a = query(maps, mz, c.label, 10.0, tolerance_basis="precursor_mz")
        b = query(maps, mz, c.label, 10.0, tolerance_basis="neutral_mass")
        self.assertAlmostEqual(a["neutral_mass_half_width_da"], mz * 10e-6 / 2)
        self.assertAlmostEqual(b["neutral_mass_half_width_da"], 300.0 * 10e-6)
        self.assertGreater(a["neutral_mass_half_width_da"], b["neutral_mass_half_width_da"])

    def test_no_candidate_cap(self):
        neutral = np.full(100, 300.0)
        ions = {c.label: c.precursor_mz(neutral) for c in CHANNELS}
        answer = query(({}, neutral, ions), float(BY_LABEL["[M+H]+"].precursor_mz(300.0)),
                       "[M+H]+", 0.0)
        self.assertEqual(answer["candidate_count"], 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
