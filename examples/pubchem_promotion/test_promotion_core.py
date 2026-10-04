"""Synthetic chemistry contracts only; no spectrum labels or model execution."""
import dataclasses
import math
import unittest

from promotion_core import (ADDUCTS, Observation, RankedCandidate, TierEvidence,
                            matching_observations, neutral_observation, promote_leading)


def candidate(index):
    # Synthetic declared identities, not asserted chemical identities.
    return RankedCandidate(f"synthetic-{index}", ((("C", index + 1),), "A" * 13 + chr(65 + index)))


def evidence(c=None):
    return TierEvidence(c or candidate(0), 300.0, 14.0, 2.0, 3.0, 2.75, 10, 10.0, 2.0, 12)


def observed(mass=300.0, adduct="[M+H]+"):
    n, z, shift = ADDUCTS[adduct]
    return Observation((mass * n + shift) / z, adduct, "positive" if adduct.endswith("+") else "negative")


class MassContracts(unittest.TestCase):
    def test_all_supported_adducts_round_trip(self):
        for adduct in ADDUCTS:
            with self.subTest(adduct=adduct):
                self.assertAlmostEqual(neutral_observation(observed(adduct=adduct)), 300.0, places=10)

    def test_doubly_charged_requires_charge(self):
        self.assertEqual(matching_observations(300.0, [observed(adduct="[M+2H]2+")]), (0,))

    def test_dimer_requires_multiplicity(self):
        self.assertEqual(matching_observations(300.0, [observed(adduct="[2M+Na]+")]), (0,))

    def test_unknown_adduct_abstains(self):
        self.assertIsNone(neutral_observation(Observation(301.0, "[M+unknown]+", "positive")))

    def test_missing_and_nonfinite_mass(self):
        for value in (None, math.nan, math.inf, -1.0, True):
            self.assertIsNone(neutral_observation(Observation(value, "[M+H]+", "positive")))

    def test_polarity_conflict(self):
        self.assertIsNone(neutral_observation(dataclasses.replace(observed(), mode="negative")))

    def test_mass_inside_and_outside_fixed_tolerance(self):
        self.assertEqual(matching_observations(300.0, [observed(300.0029), observed(300.0031)]), (0,))

    def test_one_supported_observation_is_enough(self):
        self.assertEqual(matching_observations(300.0, [Observation(None, None, None), observed()]), (1,))


class PromotionContracts(unittest.TestCase):
    def setUp(self):
        self.baseline = [candidate(i) for i in range(1, 26)]
        self.kw = dict(policy_approved=True, full_pipeline_available=True, ap2_invoked=True, library_max=0.1)

    def run_promotion(self, e=None, **overrides):
        return promote_leading(self.baseline, e or evidence(), [observed()], **(self.kw | overrides))

    def assert_abstention(self, result, reason):
        self.assertFalse(result.promoted)
        self.assertIs(result.ranked, self.baseline)
        self.assertEqual(result.reason, reason)

    def test_default_policy_does_not_promote(self):
        self.assert_abstention(self.run_promotion(policy_approved=False), "policy_unapproved")

    def test_full_pipeline_missing(self):
        self.assert_abstention(self.run_promotion(full_pipeline_available=False), "full_pipeline_unavailable")

    def test_ap2_uninvoked(self):
        self.assert_abstention(self.run_promotion(ap2_invoked=False), "ap2_uninvoked")

    def test_strong_library_unchanged(self):
        for value in (0.9, 1.0, 1.0000001192092896):
            self.assert_abstention(self.run_promotion(library_max=value), "strong_library_match")

    def test_literal_float32_below_point_nine_remains_open(self):
        # float32(0.9) converted to Python float; do not round the threshold down.
        self.assertTrue(self.run_promotion(library_max=0.8999999761581421).promoted)

    def test_missing_library_max(self):
        self.assert_abstention(self.run_promotion(library_max=None), "library_evidence_missing")

    def test_new_identity_displaces_only_tail(self):
        result = self.run_promotion()
        self.assertEqual(result.ranked, [candidate(0)] + self.baseline[:24])
        self.assertEqual(len(self.baseline), 25)

    def test_existing_alias_is_removed_by_scoring_identity(self):
        c = RankedCandidate("different-spelling", self.baseline[11].identity)
        result = self.run_promotion(evidence(c))
        self.assertEqual(result.ranked[0], c)
        self.assertEqual(result.ranked[1:], self.baseline[:11] + self.baseline[12:])

    def test_duplicate_baseline_is_rejected(self):
        self.baseline[5] = self.baseline[0]
        self.assert_abstention(self.run_promotion(), "final_list_not_deduplicated")

    def test_empty_baseline_is_rejected(self):
        self.baseline = []
        self.assert_abstention(self.run_promotion(), "final_list_invalid")

    def test_tautomer_key_contract_is_required(self):
        c = RankedCandidate("valid-looking-smiles", ((("C", 1),), "bad"))
        self.assert_abstention(self.run_promotion(evidence(c)), "tier_metadata_invalid")

    def test_nonfinite_or_degenerate_statistics_abstain(self):
        for field, value in (("raw_fz", math.nan), ("survivor_std", 0.0),
                             ("popularity", -1.0), ("exact_mass", math.inf),
                             ("survivor_count", 1), ("store_row", -1)):
            with self.subTest(field=field):
                self.assert_abstention(self.run_promotion(dataclasses.replace(evidence(), **{field: value})), "tier_metadata_invalid")

    def test_reordered_popularity_cannot_silently_rebind(self):
        self.assert_abstention(self.run_promotion(dataclasses.replace(evidence(), popularity=4.0)), "tier_metadata_invalid")

    def test_candidate_specific_mass_failure(self):
        self.assert_abstention(self.run_promotion(dataclasses.replace(evidence(), exact_mass=301.0)), "candidate_mass_ineligible")


if __name__ == "__main__":
    unittest.main()
