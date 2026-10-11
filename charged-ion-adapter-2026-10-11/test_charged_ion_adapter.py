# SPDX-License-Identifier: MIT
import math
import unittest
from charged_ion_adapter import (
    AdapterHold, PROTON, ELECTRON, NA, H, precursor_metadata, fragment_ions,
    adapt_spectrum, clean_peaks, compatible_groups, potential_reuse_intervals,
)


def spectrum(adduct="[M+H]+",mode="positive",ev=(20.0,)):
    return {
        "adduct":adduct,"ionization_mode":mode,"precursor_mz":200.0,
        "ms2_mzs":[50.0,50.015,100.0],"ms2_normalized_intensities":[1.0,.5,.25],
        "instrument_type":"invented instrument","collision_energy_ev":list(ev),
        "collision_energy_orig_units":"eV",
    }


class AdapterContracts(unittest.TestCase):
    def test_proton_inverse(self):
        self.assertAlmostEqual(precursor_metadata("[M+H]+","positive",100+PROTON)["neutral_mass"],100)

    def test_deproton_inverse(self):
        self.assertAlmostEqual(precursor_metadata("[M-H]-","negative",100-PROTON)["neutral_mass"],100)

    def test_doubly_charged_precursor_inverse(self):
        self.assertAlmostEqual(precursor_metadata("[M+2H]2+","positive",(100+2*PROTON)/2)["neutral_mass"],100)

    def test_doubly_negative_precursor_inverse(self):
        self.assertAlmostEqual(precursor_metadata("[M-2H]2-","negative",(100-2*PROTON)/2)["neutral_mass"],100)

    def test_multimer_inverse(self):
        self.assertAlmostEqual(precursor_metadata("[2M+H]+","positive",200+PROTON)["neutral_mass"],100)

    def test_adduct_mode_disagreement(self):
        with self.assertRaises(AdapterHold):precursor_metadata("[M+H]+","negative",200)

    def test_ambiguous_charge_is_held(self):
        with self.assertRaises(AdapterHold):precursor_metadata("[M-2H]-","negative",200)

    def test_unknown_adduct_and_mode_held(self):
        for ad,mode in [("[M+Unknown]+","positive"),(None,"positive"),([], "positive"),("[M+H]+","unknown")]:
            with self.assertRaises(AdapterHold):precursor_metadata(ad,mode,200)

    def test_family_must_be_declared(self):
        meta=precursor_metadata("[M+H]+","positive",200)
        with self.assertRaises(AdapterHold):fragment_ions([100],meta,family=None)

    def test_sodium_retention_is_explicit(self):
        meta=precursor_metadata("[M+Na]+","positive",200)
        r=fragment_ions([100],meta,family="sodium_retained",h_shifts=(0,))
        self.assertAlmostEqual(r["ion_mz"][0],100+NA-ELECTRON)
        self.assertFalse(r["chemical_identity_verified"])

    def test_sodium_retention_from_proton_precursor_is_held(self):
        with self.assertRaises(AdapterHold):
            fragment_ions([100],precursor_metadata("[M+H]+","positive",200),family="sodium_retained")

    def test_precursor_charge_not_copied_to_fragment(self):
        meta=precursor_metadata("[M+2H]2+","positive",200)
        r=fragment_ions([100],meta,family="protonated",h_shifts=(0,))
        self.assertEqual(meta["precursor_abs_charge"],2)
        self.assertEqual(r["fragment_abs_charge"],1)
        self.assertAlmostEqual(r["ion_mz"][0],100+PROTON)

    def test_family_polarity_disagreement(self):
        with self.assertRaises(AdapterHold):
            fragment_ions([100],precursor_metadata("[M-H]-","negative",200),family="protonated")

    def test_h_shift_validation(self):
        meta=precursor_metadata("[M+H]+","positive",200)
        for shifts in [(0,0),(-3,), (True,), ()]:
            with self.assertRaises(AdapterHold):fragment_ions([100],meta,family="protonated",h_shifts=shifts)

    def test_neutral_kind_and_mass_validation(self):
        meta=precursor_metadata("[M+H]+","positive",200)
        with self.assertRaises(AdapterHold):fragment_ions([100],meta,family="protonated",mass_kind="ion")
        for masses in [[],[0],[math.nan],[True],[.001]]:
            with self.assertRaises(AdapterHold):fragment_ions(masses,meta,family="deprotonated" if meta["mode"]=="negative" else "protonated")

    def test_missing_window_is_assignment_only(self):
        r=adapt_spectrum(spectrum())
        self.assertEqual(r["status"],"READY_ASSIGNMENT_ONLY")
        self.assertIsNone(r["window"])
        self.assertEqual(r["window_status"],"HOLD_NO_ACQUISITION_WINDOW")

    def test_peak_extrema_are_never_window_bounds(self):
        r=adapt_spectrum(spectrum(),window_source="peak extrema are not acceptable metadata")
        self.assertIsNone(r["window"])

    def test_declared_window(self):
        s=spectrum();s.update(acquisition_mz_min=40,acquisition_mz_max=150)
        r=adapt_spectrum(s,window_source="invented acquisition metadata")
        self.assertEqual(r["window"],[40,150])

    def test_bad_declared_window_is_held(self):
        s=spectrum();s.update(acquisition_mz_min=60,acquisition_mz_max=150)
        with self.assertRaises(AdapterHold):adapt_spectrum(s,window_source="invented acquisition metadata")

    def test_different_energy_and_adduct_not_pooled(self):
        views=[adapt_spectrum(spectrum(),query_binding="invented same query"),
               adapt_spectrum(spectrum(ev=(30,)),query_binding="invented same query"),
               adapt_spectrum(spectrum("[M+Na]+"),query_binding="invented same query")]
        self.assertEqual(len(compatible_groups(views,same_query_binding="invented same query")),3)

    def test_unknown_energy_isolated(self):
        a=spectrum(ev=());views=[adapt_spectrum(a,query_binding="invented same query"),
                               adapt_spectrum(a,query_binding="invented same query")]
        self.assertEqual(len(compatible_groups(views,same_query_binding="invented same query")),2)

    def test_metadata_is_not_same_analyte_identity(self):
        views=[adapt_spectrum(spectrum()),adapt_spectrum(spectrum())]
        with self.assertRaises(AdapterHold):compatible_groups(views,same_query_binding="invented same query")
        views=[adapt_spectrum(spectrum(),query_binding="query A"),
               adapt_spectrum(spectrum(),query_binding="query B")]
        with self.assertRaises(AdapterHold):compatible_groups(views,same_query_binding="query A")

    def test_cleaning_declares_changed_native_tie_policy(self):
        r=clean_peaks([50,100],[1,.5])
        self.assertEqual(r["intensity"],[2/3,1/3])
        self.assertEqual(r["native_bitwise_parity"],"UNVERIFIED")
        raw=list(range(1,301))
        top=clean_peaks(raw,[1]*300)
        self.assertEqual(top["mz"],list(range(1,257)))

    def test_geometry_only_fixed_tolerance(self):
        r=potential_reuse_intervals(clean_peaks([50,50.015,100],[1,1,1]))
        self.assertEqual(r["overlapping_pairs"],1)
        self.assertEqual(r["actual_predicted_ion_reuse"],"UNMEASURED")

    def test_vectors_and_bad_numbers_are_held(self):
        for mz,it in [([],[]),([100],[0]),([100],[-1]),([math.nan],[1]),([100],[math.inf]),([100,110],[1])]:
            with self.assertRaises(AdapterHold):clean_peaks(mz,it)


if __name__=="__main__":
    unittest.main()

