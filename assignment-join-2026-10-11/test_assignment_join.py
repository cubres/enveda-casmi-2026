# SPDX-License-Identifier: MIT
import copy
import math
import unittest
import assignment_join as a
from invented_flow import fixture


class ExportJoinControls(unittest.TestCase):
    def setUp(self):
        self.export, self.protocol, self.join, self.labels, self.intervention = fixture(fitted=True)

    def score(self):
        return a.score_join(self.export, self.protocol)

    def repin_export(self):
        self.protocol["export_sha256"] = a.digest(self.export)

    def evaluate(self):
        return a.evaluate_paired(self.join, self.labels, self.protocol, self.intervention)

    def test_actual_matching_win_loss_and_pool_miss(self):
        r = self.evaluate()
        self.assertEqual(r["status"], "INVENTED_FLOW_ONLY")
        self.assertEqual(r["matching_feature_only_comparison"], {"mean_delta": 0.0, "wins": 1, "losses": 1, "ties": 1})
        self.assertEqual(r["truth_in_pool"], 2)
        self.assertEqual(r["pool_recall"], 2 / 3)

    def test_assignment_changes_only_column21(self):
        for old, new in zip(self.export["queries"], self.join["queries"]):
            for row0, row1 in zip(old["control"]["features"], new["joined_features"]):
                self.assertEqual(row0[:21] + row0[22:], row1[:21] + row1[22:])
                self.assertLessEqual(row1[21], row0[21])

    def test_native_baseline_is_independent_analytic_oracle(self):
        first = self.join["queries"][0]["candidate_evidence"][0]["per_view"][0]
        total = .8 + .5 + math.sqrt(.11)
        self.assertAlmostEqual(first["independent"], 1.3 / total)
        self.assertAlmostEqual(first["assignment"], .8 / total)
        self.assertAlmostEqual(first["reuse_gap"], .5 / total)

    def test_neutral_and_charged_routes_match(self):
        self.assertEqual(self.join["queries"][0]["joined_features"], self.join["queries"][1]["joined_features"])

    def test_equal_centroid_native_weight_order_preserved(self):
        spectrum = copy.deepcopy(self.export["queries"][0]["spectra"][0])
        spectrum["mz"] = [100.0, 100.0, 150.0]
        spectrum["cleaned_array_sha256"] = a.digest({"mz": spectrum["mz"], "intensity": spectrum["intensity"]})
        before = copy.deepcopy(spectrum)
        _, _, peaks = a._spectrum(spectrum, spectrum["query_id"])
        self.assertEqual(peaks, [(100.0, .8), (100.0, .5), (150.0, math.sqrt(.11))])
        self.assertEqual(spectrum, before)

    def test_control_only_does_not_pretend_refit(self):
        e, p, j, labels, _ = fixture(fitted=False)
        r = a.evaluate_paired(j, labels, p)
        self.assertEqual(r["fitted_ranker_comparison"], "HOLD_NO_REFITTED_PREDICTIONS")

    def test_export_drift_held(self):
        self.export["queries"][0]["control"]["probabilities"][0] = .7
        with self.assertRaises(a.JoinHold): self.score()

    def test_query_order_drift_held(self):
        self.export["queries"].reverse(); self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_candidate_order_drift_held(self):
        self.export["queries"][0]["candidate_order"].reverse(); self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_cross_query_spectrum_held(self):
        self.export["queries"][0]["spectra"][0]["query_id"] = "other"; self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_cross_candidate_prediction_held(self):
        self.export["queries"][0]["predictions"][0]["candidate_id"] = "invented-B"; self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_cleaned_array_drift_held(self):
        self.export["queries"][0]["spectra"][0]["intensity"][0] = .63; self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_no_recleaning_or_sorting(self):
        s = self.export["queries"][0]["spectra"][0]
        s["mz"].reverse(); s["cleaned_array_sha256"] = a.digest({"mz": s["mz"], "intensity": s["intensity"]}); self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_probability_order_held(self):
        c = self.export["queries"][0]["control"]; c["candidate_order"].reverse(); self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_probability_range_held(self):
        c = self.export["queries"][0]["control"]; c["probabilities"][0] = 2.0
        c["probability_sha256"] = a.digest(c["probabilities"]); self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_native_baseline_parity_failure_held(self):
        c = self.export["queries"][0]["control"]; c["native_independent_per_view"][0][0] = .1
        c["native_independent_sha256"] = a.digest(c["native_independent_per_view"]); self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_column21_parity_failure_held(self):
        c = self.export["queries"][0]["control"]; c["features"][0][21] = .1
        c["feature_sha256"] = a.digest(c["features"]); self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_no_31_to40_without_refit(self):
        c = self.export["queries"][0]["control"]; c["features"][0] += [0.0] * 9
        c["feature_sha256"] = a.digest(c["features"]); self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_native_float32_feature_contract(self):
        c = self.export["queries"][0]["control"]; c["features"][0][21] = .1
        c["feature_sha256"] = a.digest(c["features"]); self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_missing_prediction_not_zero(self):
        self.export["queries"][0]["predictions"].pop(); self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_empty_prediction_requires_explicit_status(self):
        p = self.export["queries"][0]["predictions"][2]; p["status"] = "MISSING"
        p["prediction_sha256"] = a.digest({k: v for k, v in p.items() if k != "prediction_sha256"}); self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_bad_empty_representation_held(self):
        p = self.export["queries"][0]["predictions"][2]; p["mass_kind"] = "unknown"
        p["prediction_sha256"] = a.digest({k: v for k, v in p.items() if k != "prediction_sha256"}); self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_polarity_or_carrier_mismatch_held(self):
        p = self.export["queries"][0]["predictions"][0]; p["family"] = "sodium_retained"
        p["prediction_sha256"] = a.digest({k: v for k, v in p.items() if k != "prediction_sha256"}); self.repin_export()
        with self.assertRaises(a.chem.AdapterHold): self.score()

    def test_abs_tolerance_frozen(self):
        self.protocol["ppm"] = 10
        with self.assertRaises(a.JoinHold): self.score()

    def test_scientific_source_pin_held(self):
        self.protocol["join_source_sha256"] = a.digest("another source")
        with self.assertRaises(a.JoinHold): self.score()

    def test_matching_budget_held_before_excess_work(self):
        original = a.MAX_WORK_CELLS
        try:
            a.MAX_WORK_CELLS = 1
            with self.assertRaises(a.JoinHold): self.score()
        finally:
            a.MAX_WORK_CELLS = original

    def test_aggregation_frozen(self):
        self.protocol["aggregation"] = "median"
        with self.assertRaises(a.JoinHold): self.score()

    def test_unreviewed_generator_held(self):
        p = self.export["queries"][0]["predictions"][0]; p["generator_source_sha256"] = a.digest("unreviewed")
        p["prediction_sha256"] = a.digest({k: v for k, v in p.items() if k != "prediction_sha256"}); self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_non_osi_code_component_held(self):
        self.export["provenance"]["component_pins"][0]["code_license_spdx"] = "CC-BY-NC-4.0"; self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_declared_window_kept_but_no_density_added(self):
        s = self.export["queries"][0]["spectra"][0]
        s["acquisition"] = {"bounds": [50.0, 200.0], "source_sha256": a.digest("invented acquisition")}; self.repin_export()
        r = self.score()
        self.assertEqual(r["queries"][0]["acquisition_declared_views"], 1)
        self.assertTrue(r["queries"][0]["no_density_features_computed"])

    def test_bad_window_held(self):
        s = self.export["queries"][0]["spectra"][0]
        s["acquisition"] = {"bounds": [110.0, 200.0], "source_sha256": a.digest("invented acquisition")}; self.repin_export()
        with self.assertRaises(a.JoinHold): self.score()

    def test_refit_fit_eval_overlap_held(self):
        self.intervention["fit_query_bindings"] = [self.protocol["query_order"][0]]
        with self.assertRaises(a.JoinHold): self.evaluate()

    def test_refit_feature_pin_held(self):
        self.intervention["joined_feature_pins"][self.protocol["query_order"][0]] = a.digest("wrong")
        with self.assertRaises(a.JoinHold): self.evaluate()

    def test_refit_probability_pin_held(self):
        self.intervention["probabilities"][self.protocol["query_order"][0]][0] = .4
        with self.assertRaises(a.JoinHold): self.evaluate()

    def test_labels_coverage_or_pin_held(self):
        self.labels["truth"][self.protocol["query_order"][0]] = "invented-A"
        with self.assertRaises(a.JoinHold): self.evaluate()

    def test_joined_evidence_mutation_held(self):
        self.join["queries"][0]["control_probabilities"][0] = .9
        with self.assertRaises(a.JoinHold): self.evaluate()

    def test_nonfinite_or_boolean_numeric_held(self):
        with self.assertRaises(a.JoinHold): a._real(True, "test")
        with self.assertRaises(a.JoinHold): a.canonical(float("nan"))

    def test_duplicate_object_keys_held(self):
        with self.assertRaises(a.JoinHold): a._unique_object([("x", 1), ("x", 2)])

    def test_uniform_tie_and_cutoff_oracles(self):
        self.assertAlmostEqual(a.expected_rr25([1, 1, 1], 0), (1 + 1/2 + 1/3) / 3)
        self.assertEqual(a.expected_rr25(list(range(30)), 0), 0)
        self.assertEqual(a.expected_rr25([1, 2], None), 0)


if __name__ == "__main__":
    unittest.main()
