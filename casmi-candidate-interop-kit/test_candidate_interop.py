"""Adverse, entirely invented controls. Outputs are preserved in a new directory."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest

import numpy as np

from candidate_interop import (ContractError, IonSpec, PROTON_MASS_DA,
    binary_tanimoto, expected_overlap_score, load_fixture_bundle, load_numeric_npy,
    mass_window, maccs_keys_1_to_166, mz_from_neutral, neutral_from_mz,
    precursor_window, protonated_ion, require_matching_feature_contracts,
    sha256_file, stable_ranking, unpack_fingerprints, validate_binary, validate_masses)


class InteropTests(unittest.TestCase):
    def setUp(self):
        self.work = WORK / self._testMethodName
        self.work.mkdir(exist_ok=False)

    def test_inclusive_edges_duplicates_and_nextafter(self):
        q, width = 100., .001
        lower, upper = q-width, q+width
        masses = np.array([np.nextafter(lower, -np.inf), lower, lower, q,
                           upper, upper, np.nextafter(upper, np.inf)], dtype=np.float64)
        self.assertEqual(mass_window(masses, q, 10.), (1, 6))

    def test_zero_ppm_keeps_all_exact_duplicates(self):
        masses = np.array([99., 100., 100., 101.], dtype=np.float64)
        self.assertEqual(mass_window(masses, 100., 0.), (1, 3))

    def test_empty_bank(self):
        self.assertEqual(mass_window(np.empty(0, dtype=np.float64), 100., 10.), (0, 0))

    def test_mass_rejections(self):
        for bad in (np.array([2., 1.]), np.array([np.nan]), np.array([np.inf]),
                    np.array([0.]), np.array([-1.]), np.array([1], dtype=np.int64),
                    np.array([[1.]])):
            with self.assertRaises(ContractError): validate_masses(bad)

    def test_query_and_tolerance_rejections(self):
        masses = np.array([100.], dtype=np.float64)
        for bad in (np.nan, np.inf, 0., -1., True, "100"):
            with self.assertRaises(ContractError): mass_window(masses, bad, 10.)
        for bad in (np.nan, np.inf, -1., 1e6, True, "10"):
            with self.assertRaises(ContractError): mass_window(masses, 100., bad)

    def test_explicit_query_denominator(self):
        # This mass fits the candidate-denominator test but lies above the
        # query-denominator upper bound. The kit uses the latter deliberately.
        masses = np.array([100.001000005], dtype=np.float64)
        self.assertEqual(mass_window(masses, 100., 10.), (0, 0))
        self.assertLess(abs(masses[0]-100.) / masses[0] * 1e6, 10.)

    def test_positive_negative_and_double_charge_roundtrip(self):
        for charge in (-2, -1, 1, 2, 3):
            ion = protonated_ion(charge)
            self.assertAlmostEqual(neutral_from_mz(mz_from_neutral(300., ion), ion), 300., places=12)
        self.assertAlmostEqual(mz_from_neutral(100., protonated_ion(1)), 101.0072764665789, places=12)

    def test_dimer_explicit_equation(self):
        ion = IonSpec(1, PROTON_MASS_DA, molecule_count=2)
        self.assertAlmostEqual(neutral_from_mz(mz_from_neutral(100., ion), ion), 100., places=12)

    def test_invalid_ion_rejections(self):
        for bad in (0, True, "1", 1.5):
            with self.assertRaises(ContractError): protonated_ion(bad)
        for bad in (IonSpec, "[M+Na]+", None):
            with self.assertRaises(ContractError): neutral_from_mz(100., bad)
        with self.assertRaises(ContractError): IonSpec(1, np.nan)
        with self.assertRaises(ContractError): IonSpec(1, 1., molecule_count=0)
        with self.assertRaises(ContractError): neutral_from_mz(1., IonSpec(1, 2.))

    def test_precursor_ppm_is_not_neutral_ppm(self):
        ion = protonated_ion(1)
        mz = mz_from_neutral(100., ion)
        masses = np.array([100.001005], dtype=np.float64)
        self.assertEqual(mass_window(masses, 100., 10.), (0, 0))
        self.assertEqual(precursor_window(masses, mz, 10., ion), (0, 1))

    def test_precursor_charge_error_propagation(self):
        ion = protonated_ion(2)
        mz = mz_from_neutral(300., ion)
        width = mz * 1e-5 * 2
        masses = np.array([300.-width, 300.+width], dtype=np.float64)
        self.assertEqual(precursor_window(masses, mz, 10., ion), (0, 2))

    def test_both_bit_orders_with_asymmetric_sentinels(self):
        bits = np.zeros((1, 2048), dtype=np.uint8)
        bits[0, [0, 7, 8, 166, 2047]] = 1
        for order in ("big", "little"):
            packed = np.packbits(bits, axis=1, bitorder=order)
            self.assertTrue(np.array_equal(unpack_fingerprints(packed, bit_count=2048, bitorder=order), bits))
            wrong = unpack_fingerprints(packed, bit_count=2048, bitorder="little" if order == "big" else "big")
            self.assertFalse(np.array_equal(wrong, bits))

    def test_padding_and_wrong_width_rejections(self):
        bits = np.zeros((1, 166), dtype=np.uint8)
        for order in ("big", "little"):
            packed = np.packbits(bits, axis=1, bitorder=order)
            packed[0, -1] = 1 if order == "big" else 128
            with self.assertRaises(ContractError): unpack_fingerprints(packed, bit_count=166, bitorder=order)
        with self.assertRaises(ContractError): unpack_fingerprints(np.zeros((1, 20), dtype=np.uint8), bit_count=166, bitorder="big")
        with self.assertRaises(ContractError): unpack_fingerprints(np.zeros((1, 21), dtype=np.uint8), bit_count=166, bitorder=None)

    def test_maccs_last_key_and_unused_zero(self):
        full = np.zeros((1, 167), dtype=np.uint8); full[0, 166] = 1
        reduced = maccs_keys_1_to_166(full)
        self.assertEqual(reduced.shape, (1, 166)); self.assertEqual(reduced[0, 165], 1)
        full[0, 0] = 1
        with self.assertRaises(ContractError): maccs_keys_1_to_166(full)
        with self.assertRaises(ContractError): maccs_keys_1_to_166(reduced)

    def test_binary_dtype_and_value_rejections(self):
        for bad in (np.array([[0., 1.]]), np.array([[0, 2]], dtype=np.uint8),
                    np.array([[0, 1]], dtype=np.int64), np.array([0, 1], dtype=np.uint8)):
            with self.assertRaises(ContractError): validate_binary(bad, 2)

    def test_binary_tanimoto_nontrivial_oracle(self):
        q = np.array([1, 1, 0, 0], dtype=np.uint8)
        c = np.array([[1, 0, 1, 1], [1, 1, 0, 0], [0, 0, 1, 1]], dtype=np.uint8)
        self.assertTrue(np.allclose(binary_tanimoto(q, c), [.25, 1., 0.]))

    def test_binary_popcount_does_not_overflow_uint8(self):
        q = np.ones(2048, dtype=np.uint8)
        self.assertEqual(binary_tanimoto(q, q.reshape(1, -1))[0], 1.)

    def test_empty_fingerprints_score_zero(self):
        q = np.zeros(2048, dtype=np.uint8)
        self.assertEqual(binary_tanimoto(q, q.reshape(1, -1))[0], 0.)
        self.assertEqual(expected_overlap_score(q.astype(float), q.reshape(1, -1))[0], 0.)

    def test_expected_overlap_fractional_oracle_not_algebraic(self):
        p = np.array([.5, .5]); c = np.array([[1, 0]], dtype=np.uint8)
        self.assertAlmostEqual(expected_overlap_score(p, c)[0], 1./3., places=14)
        self.assertNotAlmostEqual(expected_overlap_score(p, c)[0], .5)

    def test_expected_overlap_reduces_to_binary(self):
        q = np.array([1, 1, 0, 0], dtype=np.uint8)
        c = np.array([[1, 0, 1, 1], [1, 1, 0, 0]], dtype=np.uint8)
        self.assertTrue(np.array_equal(expected_overlap_score(q.astype(float), c), binary_tanimoto(q, c)))

    def test_probability_rejections(self):
        c = np.zeros((1, 2), dtype=np.uint8)
        for bad in (np.array([np.nan, 0.]), np.array([1.1, 0.]), np.array([-.1, 0.]), np.array([0, 1])):
            with self.assertRaises(ContractError): expected_overlap_score(bad, c)

    def test_deterministic_tie_ranking_and_duplicate_rejection(self):
        keys = np.array(["SYN002", "SYN001", "SYN003"])
        self.assertEqual(stable_ranking(keys, np.array([.5, .5, .7])).tolist(), [2, 1, 0])
        with self.assertRaises(ContractError): stable_ranking(np.array(["A", "A"]), np.array([.1, .2]))

    def test_full_morgan_contract_mismatch(self):
        parameters = {"radius": 2, "use_chirality": False, "use_bond_types": True,
            "invariant_kind": "connectivity", "count_simulation": False,
            "include_ring_membership": True, "include_redundant_environments": False,
            "only_nonzero_invariants": False}
        contract = {"family": "Morgan", "bit_count": 2048, "generator": "RDKit",
            "generator_version": "EXAMPLE-version-not-real-data", "parameters": parameters,
            "preprocessing": "EXAMPLE-explicit-rule-not-real-data", "bit_names": "hash-bin-index"}
        self.assertTrue(require_matching_feature_contracts(contract, copy.deepcopy(contract)))
        mismatch = copy.deepcopy(contract); mismatch["parameters"]["radius"] = 3
        with self.assertRaises(ContractError): require_matching_feature_contracts(contract, mismatch)
        unknown = copy.deepcopy(contract); unknown["generator_version"] = "unknown"
        with self.assertRaises(ContractError): require_matching_feature_contracts(unknown, unknown)
        incomplete = copy.deepcopy(contract); incomplete["parameters"].pop("use_chirality")
        with self.assertRaises(ContractError): require_matching_feature_contracts(incomplete, incomplete)
        counts = copy.deepcopy(contract); counts["parameters"]["count_simulation"] = True
        with self.assertRaises(ContractError): require_matching_feature_contracts(counts, counts)

    def test_object_and_structured_npy_rejected(self):
        obj_path = self.work / "object.npy"
        with obj_path.open("xb") as f: np.save(f, np.array([{"invented": True}], dtype=object), allow_pickle=True)
        with self.assertRaises(ValueError): load_numeric_npy(obj_path)
        struct_path = self.work / "structured.npy"
        with struct_path.open("xb") as f: np.save(f, np.array([(1,)], dtype=[("x", "i4")]), allow_pickle=False)
        with self.assertRaises(ContractError): load_numeric_npy(struct_path)

    def test_fixture_manifest_pin_and_full_row_drift(self):
        package_root = Path(__file__).resolve().parent
        fixture = package_root / "fixtures" if (package_root / "fixtures").is_dir() else package_root
        pin = (fixture / "MANIFEST.sha256").read_text().strip()
        arrays, manifest = load_fixture_bundle(fixture, manifest_sha256=pin)
        self.assertEqual(len(arrays["masses.npy"]), 12)
        self.assertFalse(manifest["chemical_data"])
        with self.assertRaises(ContractError): load_fixture_bundle(fixture, manifest_sha256="0" * 64)
        # Keep all shapes, binary values and row counts valid, but shuffle just
        # the fingerprint rows. A trusted byte hash detects this real mistake.
        for name in ("masses.npy", "keys.npy", "maccs_sized.npy"):
            with (self.work / name).open("xb") as f: f.write((fixture / name).read_bytes())
        with (self.work / "MANIFEST.json").open("xb") as f: f.write((fixture / "MANIFEST.json").read_bytes())
        with (self.work / "morgan_sized.npy").open("xb") as f:
            np.save(f, arrays["morgan_sized.npy"][::-1], allow_pickle=False)
        with self.assertRaises(ContractError): load_fixture_bundle(self.work, manifest_sha256=pin)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--work-dir":
        raise SystemExit("usage: python test_candidate_interop.py --work-dir NEW_DIRECTORY")
    WORK = Path(sys.argv[2]); WORK.mkdir(parents=True, exist_ok=False)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(InteropTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = {"schema": "casmi-interop-invented-unit-results-v1", "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "numpy_version": np.__version__,
        "status": "PASS" if result.wasSuccessful() else "FAIL", "invented_fixtures_only": True,
        "network_calls": 0, "chemical_model_evaluations": 0, "official_score": None}
    with (WORK / "RESULT.json").open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
