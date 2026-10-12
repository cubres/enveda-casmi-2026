# SPDX-License-Identifier: MIT
"""Invented adverse controls; no competition tasks, chemistry or models."""
import copy
import math
import tempfile
import unittest
from pathlib import Path
import hashlib
from fixed_panel_audit import AuditHold, digest, pair_audit, panel_audit, read_spec

SOURCE = "1" * 64


def fixture(branch="invented-query-0", mode="fallback"):
    labels = ["invented-candidate-a", "invented-candidate-b", "invented-candidate-c", "invented-tail"]
    base = [.4, .3, .2, .1]
    response = {"id": branch, "iceberg": [.1, .2, .9], "glacier": [None, None, None]}
    status = "ICE_FALLBACK"
    control = [0, 1, 2, 3]
    treatment = [2, 1, 0, 3]
    gl, ice = 0, 2
    if mode == "constant":
        response["iceberg"] = [.2, .3, .2]
        status, treatment = "ICE_CONSTANT_NOOP", control.copy()
    if mode == "finite-zero-gl":
        response["glacier"][0] = 0.0
        status, treatment, gl = "CONTROL_PRESERVED", control.copy(), 1
    if mode == "partial-ice":
        response["iceberg"][2] = None
        status, treatment, ice = "CONTROL_PRESERVED", control.copy(), 1
    signals = {k: [None if v is None else float(v) for v in response[k]] + [None]
               for k in ("iceberg", "glacier")}
    group = {"formula": "invented-formula-A", "slots": [0, 2], "members": [0, 2],
             "gl_finite": gl, "ice_finite": ice, "status": status,
             "changed": treatment != control}
    if status == "ICE_FALLBACK":
        group["revised_members"] = [2, 0]
    pair = {"schema": "PRIVATE_F1_COMPLETE_GROUP_ICE_FALLBACK_V1", "query_branch": branch,
            "source_sha256": SOURCE, "candidate_order_sha256": digest(labels),
            "candidate_head_sha256": digest(labels[:3]), "frozen_scores_sha256": digest(base),
            "signals_sha256": digest(signals), "top": 3, "control_order": control,
            "treatment_order": treatment, "groups": [group,
                {"formula": "invented-formula-B", "slots": [1], "members": [1], "gl_finite": 0,
                 "ice_finite": 1, "status": "CONTROL_PRESERVED", "changed": False}],
            "changed": treatment != control, "features31_changed": False,
            "ranker_refit": False, "candidate_pool_changed": False, "official_score": None}
    context = {"query_id": branch, "rank_capture": {
        "candidates": [{"ordinal": i, "smiles": label,
                        "formula": "invented-formula-A" if i in (0, 2) else "invented-formula-B"}
                       for i, label in enumerate(labels)], "fitted_control_probabilities": base}}
    return pair, context, response


def panel_fixture():
    ids = ["invented-query-%d" % i for i in range(16)]
    panel = {"schema": "ENVEDA_PRIVATE_NATIVE_PANEL_V1", "all_query_order": ids + ["invented-outside"],
             "selected_capture_order": ids,
             "all_query_roster": [{"query_id": identity, "spectrum_order": ["invented-spectrum-%d" % i],
                                   "spectrum_count": 1} for i, identity in enumerate(ids + ["invented-outside"])]}
    pair, context, response = fixture()
    contexts = []
    for i, identity in enumerate(ids):
        query = copy.deepcopy(context) if i == 0 else {"query_id": identity, "rank_capture": None}
        query.update(panel_sha256=digest(panel), capture_status="COMPLETE" if i == 0 else "NO_NATIVE_CANDIDATE_SCORES")
        query["spectra"] = [{"spectrum_id": "invented-spectrum-%d" % i, "view_ordinal": 0}]
        contexts.append(query)
    completion = {"schema": "ENVEDA_PRIVATE_NATIVE_CAPTURE_COMPLETE_V1", "panel_sha256": digest(panel),
        "query_truth_labels_loaded": False, "original_training_reference_labels_used": True,
        "candidate_generation_changed": False, "features_changed": False,
        "ranker_refitted_for_intervention": False, "official_score": None,
        "query_records": [{"query_id": identity, "path": "PRIVATE_QUERY_%03d.json" % i,
            "sha256": digest(contexts[i]), "status": contexts[i]["capture_status"]} for i, identity in enumerate(ids)]}
    return panel, completion, contexts, [pair], {pair["query_branch"]: response}


class PairControls(unittest.TestCase):
    def held(self, change, mode="fallback", response=True):
        pair, context, scalar = fixture(mode=mode)
        change(pair, context, scalar)
        with self.assertRaises(AuditHold):
            pair_audit(pair, SOURCE, context, scalar if response else None)

    def test_bound_effect_preserves_interleaved_protected_slot_and_tail(self):
        pair, context, response = fixture()
        result = pair_audit(pair, SOURCE, context, response)
        self.assertEqual((result["changed_slots"], result["changed_groups"], result["head_rank_l1_distance"]), (2, 1, 4))
        self.assertEqual(result["scalar_bound"], 1)

    def test_context_candidate_order_mismatch(self):
        self.held(lambda p, c, s: c["rank_capture"]["candidates"].reverse())

    def test_context_base_score_mismatch(self):
        self.held(lambda p, c, s: c["rank_capture"]["fitted_control_probabilities"].__setitem__(0, .5))

    def test_context_branch_mismatch(self):
        self.held(lambda p, c, s: c.update(query_id="invented-other"))

    def test_head_hash_mismatch(self):
        self.held(lambda p, c, s: p.update(candidate_head_sha256="0" * 64))

    def test_source_mismatch(self):
        self.held(lambda p, c, s: p.update(source_sha256="0" * 64))

    def test_gl_infinity_is_not_absence(self):
        self.held(lambda p, c, s: s["glacier"].__setitem__(0, math.inf))

    def test_gl_nan_is_not_valid_json_service_evidence(self):
        self.held(lambda p, c, s: s["glacier"].__setitem__(0, math.nan))

    def test_scalar_boolean_rejected(self):
        self.held(lambda p, c, s: s["iceberg"].__setitem__(0, True))

    def test_scalar_head_order_mismatch(self):
        self.held(lambda p, c, s: s["iceberg"].reverse())

    def test_finite_zero_gl_protects_group(self):
        pair, context, response = fixture(mode="finite-zero-gl")
        result = pair_audit(pair, SOURCE, context, response)
        self.assertEqual(result["changed_slots"], 0)
        self.assertEqual(result["declared_fallback_groups"], 0)

    def test_partial_ice_protects_group(self):
        pair, context, response = fixture(mode="partial-ice")
        self.assertEqual(pair_audit(pair, SOURCE, context, response)["changed_slots"], 0)

    def test_constant_ice_noop(self):
        pair, context, response = fixture(mode="constant")
        self.assertEqual(pair_audit(pair, SOURCE, context, response)["constant_noop_groups"], 1)

    def test_constant_ice_cannot_be_declared_fallback(self):
        def change(pair, context, response):
            response["iceberg"][2] = .1
            pair["signals_sha256"] = digest({k: response[k] + [None] for k in ("iceberg", "glacier")})
        self.held(change)

    def test_noop_cannot_change(self):
        def change(pair, context, response):
            pair["treatment_order"] = [2, 1, 0, 3]
            pair["changed"] = True
            pair["groups"][0]["changed"] = True
        self.held(change, mode="constant")

    def test_protected_slot_change(self):
        self.held(lambda p, c, s: p.update(treatment_order=[2, 0, 1, 3]))

    def test_tail_change(self):
        self.held(lambda p, c, s: p.update(treatment_order=[3, 1, 0, 2]))

    def test_universe_loss(self):
        self.held(lambda p, c, s: p.update(treatment_order=[2, 1, 2, 3]))

    def test_boolean_ordinal(self):
        self.held(lambda p, c, s: c["rank_capture"]["candidates"][0].update(ordinal=False))

    def test_group_slot_overlap(self):
        self.held(lambda p, c, s: p["groups"][1].update(slots=[0]))

    def test_group_flags_must_match_effect(self):
        self.held(lambda p, c, s: p["groups"][0].update(changed=False))

    def test_changed_flag_must_match_effect(self):
        self.held(lambda p, c, s: p.update(changed=False))

    def test_formula_identity_mismatch(self):
        self.held(lambda p, c, s: c["rank_capture"]["candidates"][2].update(formula="invented-different"))

    def test_no_response_means_unmeasured_not_independently_bound(self):
        pair, context, _ = fixture()
        self.assertEqual(pair_audit(pair, SOURCE, context)["scalar_bound"], 0)


class PanelControls(unittest.TestCase):
    def test_fixed16_no_outcome_exclusion_and_no_public_ids(self):
        p, c, q, pairs, responses = panel_fixture()
        out = panel_audit(p, c, q, pairs, SOURCE, scalar_responses=responses)
        self.assertEqual(out["counts"]["fixed_panel_size"], 16)
        self.assertEqual(out["counts"]["no_main_pair_queries"], 15)
        self.assertNotIn("invented-query", str(out))

    def test_cohort_reorder_rejected(self):
        p, c, q, pairs, _ = panel_fixture(); p["selected_capture_order"].reverse()
        with self.assertRaises(AuditHold): panel_audit(p, c, q, pairs, SOURCE)

    def test_incomplete_query_panel_rejected(self):
        p, c, q, pairs, _ = panel_fixture()
        with self.assertRaises(AuditHold): panel_audit(p, c, q[:-1], pairs, SOURCE)

    def test_wrong_query_digest_rejected(self):
        p, c, q, pairs, _ = panel_fixture();c["query_records"][0]["sha256"] = "0" * 64
        with self.assertRaises(AuditHold): panel_audit(p, c, q, pairs, SOURCE)

    def test_duplicate_pair_rejected(self):
        p, c, q, pairs, _ = panel_fixture()
        with self.assertRaises(AuditHold): panel_audit(p, c, q, pairs + pairs, SOURCE)

    def test_missing_pair_stays_explicit_zero_capture(self):
        p, c, q, _, _ = panel_fixture()
        out = panel_audit(p, c, q, [], SOURCE)
        self.assertEqual(out["counts"]["no_main_pair_queries"], 16)
        self.assertEqual(out["scalar_evidence"], "PARTIAL_OR_UNMEASURED")

    def test_auxiliary_does_not_inflate_primary_effect(self):
        p, c, q, pairs, _ = panel_fixture(); auxiliary, _, _ = fixture(branch="invented-query-0:tier")
        out = panel_audit(p, c, q, [auxiliary], SOURCE)
        self.assertEqual(out["counts"]["auxiliary_pairs"], 1)
        self.assertEqual(out["counts"]["changed_slots"], 0)

    def test_unknown_query_pair_rejected(self):
        p, c, q, _, _ = panel_fixture();unknown, _, _ = fixture(branch="invented-not-in-roster")
        with self.assertRaises(AuditHold): panel_audit(p, c, q, [unknown], SOURCE)

    def test_scalar_query_outside_fixed_cohort_rejected(self):
        p, c, q, pairs, responses = panel_fixture();responses["invented-outside"] = {}
        with self.assertRaises(AuditHold): panel_audit(p, c, q, pairs, SOURCE, scalar_responses=responses)

    def test_scalar_without_captured_pair_rejected(self):
        p, c, q, pairs, responses = panel_fixture();responses["invented-query-1"] = {}
        with self.assertRaises(AuditHold): panel_audit(p, c, q, pairs, SOURCE, scalar_responses=responses)

    def test_registered_spectrum_order_mismatch(self):
        p, c, q, pairs, _ = panel_fixture();q[0]["spectra"][0]["spectrum_id"] = "invented-wrong-spectrum"
        c["query_records"][0]["sha256"] = digest(q[0])
        with self.assertRaises(AuditHold): panel_audit(p, c, q, pairs, SOURCE)


class FileControls(unittest.TestCase):
    def make(self, raw):
        root = Path(tempfile.mkdtemp(prefix="fixed-panel-invented-"))
        name = "PRIVATE_INVENTED.json"
        with (root / name).open("xb") as stream: stream.write(raw)
        return root, {"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

    def test_valid_file_bound(self):
        root, spec = self.make(b'{"invented":true}')
        self.assertEqual(read_spec(root, spec, 128), {"invented": True})

    def test_byte_hash_mismatch(self):
        root, spec = self.make(b'{"invented":true}');spec["sha256"] = "0" * 64
        with self.assertRaises(AuditHold): read_spec(root, spec, 128)

    def test_duplicate_JSON_key(self):
        root, spec = self.make(b'{"invented":true,"invented":false}')
        with self.assertRaises(AuditHold): read_spec(root, spec, 128)

    def test_nonstandard_JSON_NaN(self):
        root, spec = self.make(b'{"invented":NaN}')
        with self.assertRaises(AuditHold): read_spec(root, spec, 128)

    def test_parent_path_escape(self):
        root, spec = self.make(b'{"invented":true}');spec["name"] = "../PRIVATE_INVENTED.json"
        with self.assertRaises(AuditHold): read_spec(root, spec, 128)


if __name__ == "__main__":
    unittest.main()
