# SPDX-License-Identifier: MIT
"""Original, label-blind native export/join and paired ranking evaluator.

No model, dataset code, pickle, candidate generation, fitting or remote action.
Hashes bind bytes and declared provenance; they do not authenticate declarations.
"""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import struct

HELPER_PINS = {
    "charged_ion_adapter.py": "0ff785544ea07d741cf888202d20cb3a823608f3f7f78a09f3cee353e137c7ad",
    "fragment_consensus.py": "d9a91b2163a9532c26fbe281e4d33537343391c9b0bb92a08153fb5a22767b8c",
}
MAX_JSON_BYTES = 2_097_152
MAX_QUERIES = 64
MAX_CANDIDATES = 128
MAX_VIEWS = 8
MAX_WORK_CELLS = 16_777_216
FEATURE_COUNT = 31
FRAGMENT_COLUMN = 21
BASELINE_EPSILON = 1e-8


class JoinHold(ValueError):
    """No partially joined or ranked result is returned on a contract failure."""


def _load_owned(filename):
    p = Path(__file__).with_name(filename)
    if hashlib.sha256(p.read_bytes()).hexdigest() != HELPER_PINS[filename]:
        raise JoinHold("owned helper source pin drift: " + filename)
    spec = importlib.util.spec_from_file_location("_owned_assignment_" + p.stem, p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


chem = _load_owned("charged_ion_adapter.py")
matching = _load_owned("fragment_consensus.py")


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, OverflowError) as error:
        raise JoinHold("finite JSON-native values required") from error


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise JoinHold("duplicate JSON object key")
        out[key] = value
    return out


def read_json(path):
    with Path(path).open("rb") as f:
        b = f.read(MAX_JSON_BYTES + 1)
    if len(b) > MAX_JSON_BYTES:
        raise JoinHold("JSON byte budget exceeded")
    def reject_constant(value):
        raise JoinHold("nonfinite JSON constant")
    return json.loads(b, object_pairs_hook=_unique_object,
                      parse_constant=reject_constant)


def _object(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise JoinHold(name + " object fields mismatch")


def _token(value, name):
    if not isinstance(value, str) or not 1 <= len(value) <= 128 or not value.strip():
        raise JoinHold(name + " nonempty bounded token required")
    return value


def _sha(value, name):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise JoinHold(name + " SHA256 required")
    return value


def _real(value, name, lo=None, hi=None):
    if type(value) not in (int, float):
        raise JoinHold(name + " finite real required")
    try:
        value = float(value)
    except OverflowError as error:
        raise JoinHold(name + " outside float range") from error
    if not math.isfinite(value) or (lo is not None and value < lo) or (hi is not None and value > hi):
        raise JoinHold(name + " outside finite bounds")
    return value


def _list(value, lo, hi, name):
    if not isinstance(value, list) or not lo <= len(value) <= hi:
        raise JoinHold(name + " list size outside bounds")
    return value


def feature32(value):
    """Native feature contract is float32; do not silently change its precision."""
    value = _real(value, "feature32 input")
    try:
        out = struct.unpack("<f", struct.pack("<f", value))[0]
    except (OverflowError, struct.error) as error:
        raise JoinHold("feature32 value outside finite range") from error
    if not math.isfinite(out):
        raise JoinHold("finite feature32 required")
    return out


def _review(provenance):
    _object(provenance, ("data_scope", "data_rights_review_sha256", "component_review_sha256",
                         "exposure", "component_pins"), "provenance")
    if provenance["data_scope"] not in ("invented", "exposed-development"):
        raise JoinHold("private development or invented input required; no hidden-score mode")
    _sha(provenance["data_rights_review_sha256"], "data rights review")
    _sha(provenance["component_review_sha256"], "component review")
    _token(provenance["exposure"], "explicit exposure")
    for pin in _list(provenance["component_pins"], 1, 32, "components"):
        _object(pin, ("role", "source_sha256", "code_license_spdx", "reviewed_usage"), "component")
        _token(pin["role"], "component role")
        _sha(pin["source_sha256"], "component source")
        # Small explicitly supported OSI license subset, not a general license oracle.
        if pin["code_license_spdx"] not in ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"):
            raise JoinHold("component code license outside reviewed supported subset")
        if pin["reviewed_usage"] != "authorized-private-development":
            raise JoinHold("component usage review missing")
    return {p["source_sha256"] for p in provenance["component_pins"]}


def seal_native_export(draft):
    """Normalize live native JSON-native values; compute hashes without labels.

    Native caller supplies the already cleaned arrays, original features,
    actual fitted-control probabilities and fragment predictions. No arrays are
    cleaned again, inferred from logs, reordered, truncated or synthesized here.
    """
    out = copy.deepcopy(draft)
    _object(out, ("schema", "provenance", "queries"), "export")
    if out["schema"] != "ENVEDA_ASSIGNMENT_EXPORT_V1":
        raise JoinHold("export schema mismatch")
    _review(out["provenance"])
    queries = _list(out["queries"], 1, MAX_QUERIES, "queries")
    seen = set()
    for query in queries:
        _object(query, ("query_id", "candidate_order", "spectra", "predictions", "control"), "native query")
        qid = _token(query["query_id"], "query identity")
        if qid in seen:
            raise JoinHold("duplicate query identity")
        seen.add(qid)
        order = _list(query["candidate_order"], 1, MAX_CANDIDATES, "candidate order")
        if len(set(_token(c, "candidate") for c in order)) != len(order):
            raise JoinHold("duplicate candidate identity")
        query["candidate_order_sha256"] = digest(order)
        for spectrum in _list(query["spectra"], 1, MAX_VIEWS, "spectra"):
            _object(spectrum, ("query_id", "spectrum_id", "adduct", "mode", "precursor_mz",
                               "mz", "intensity", "cleaning_source_sha256", "instrument",
                               "collision_energy_ev", "acquisition"), "native spectrum")
            spectrum["cleaned_array_sha256"] = digest({"mz": spectrum["mz"], "intensity": spectrum["intensity"]})
        for prediction in _list(query["predictions"], 1, MAX_CANDIDATES * MAX_VIEWS, "predictions"):
            _object(prediction, ("query_id", "candidate_id", "spectrum_id", "mass_kind", "family",
                                 "charge", "h_shifts", "masses", "generator_source_sha256", "status"), "native prediction")
            prediction["prediction_sha256"] = digest(prediction)
        control = query["control"]
        _object(control, ("candidate_order", "probabilities", "features", "native_independent_per_view",
                          "model_sha256", "runtime_source_sha256"), "native control")
        control["candidate_order_sha256"] = digest(control["candidate_order"])
        control["probability_sha256"] = digest(control["probabilities"])
        control["feature_sha256"] = digest(control["features"])
        control["native_independent_sha256"] = digest(control["native_independent_per_view"])
    if len(canonical(out)) > MAX_JSON_BYTES:
        raise JoinHold("sealed export byte budget exceeded")
    return out


def freeze_protocol(export, *, labels_sha256, intervention_model_sha256=None,
                    intervention_probability_sha256=None):
    """Construct a label-blind byte-binding protocol from a sealed export.

    labels_sha256 is supplied from a sealed label file, before interpreting its
    values. Independent review/timestamping and exposure audit remain external.
    """
    _sha(labels_sha256, "label payload")
    if intervention_model_sha256 is not None:
        _sha(intervention_model_sha256, "refitted intervention model")
        _sha(intervention_probability_sha256, "refitted probability payload")
    elif intervention_probability_sha256 is not None:
        raise JoinHold("refitted probabilities need a refitted model")
    return {"schema": "ENVEDA_ASSIGNMENT_PROTOCOL_V1", "status": "FROZEN_BEFORE_LABEL_VALUES",
            "join_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "owned_helper_pins": HELPER_PINS.copy(),
            "export_sha256": digest(export), "labels_sha256": labels_sha256,
            "query_order": [q["query_id"] for q in export["queries"]],
            "candidate_order_pins": {q["query_id"]: q["candidate_order_sha256"] for q in export["queries"]},
            "abs_da": .01, "ppm": 0, "aggregation": "frozen_max_across_same_query_views",
            "baseline_epsilon": BASELINE_EPSILON, "replacement_column": FRAGMENT_COLUMN,
            "feature_count": FEATURE_COUNT, "intervention_model_sha256": intervention_model_sha256,
            "intervention_probability_sha256": intervention_probability_sha256}


def _spectrum(spectrum, qid):
    _object(spectrum, ("query_id", "spectrum_id", "adduct", "mode", "precursor_mz", "mz", "intensity",
                       "cleaning_source_sha256", "instrument", "collision_energy_ev", "acquisition",
                       "cleaned_array_sha256"), "sealed spectrum")
    if spectrum["query_id"] != qid:
        raise JoinHold("spectrum query binding mismatch")
    sid = _token(spectrum["spectrum_id"], "spectrum identity")
    _sha(spectrum["cleaning_source_sha256"], "native cleaning source")
    pair = {"mz": spectrum["mz"], "intensity": spectrum["intensity"]}
    if digest(pair) != spectrum["cleaned_array_sha256"]:
        raise JoinHold("cleaned array hash mismatch")
    mz = _list(spectrum["mz"], 1, 256, "native cleaned peaks")
    intensity = _list(spectrum["intensity"], len(mz), len(mz), "native cleaned intensity")
    mz = [_real(x, "native m/z", 1e-300) for x in mz]
    if mz != sorted(mz):
        raise JoinHold("native cleaned m/z order must already be sorted")
    intensity = [_real(x, "native intensity", 0) for x in intensity]
    if not math.isfinite(sum(intensity)) or sum(intensity) <= 0:
        raise JoinHold("positive finite native intensity total required")
    meta = chem.precursor_metadata(spectrum["adduct"], spectrum["mode"], spectrum["precursor_mz"])
    if spectrum["instrument"] is not None:
        _token(spectrum["instrument"], "instrument")
    energy = spectrum["collision_energy_ev"]
    if energy is not None:
        energy = sorted(_real(x, "declared eV", 0) for x in _list(energy, 1, 16, "declared eV"))
    acquisition = spectrum["acquisition"]
    if acquisition is not None:
        _object(acquisition, ("bounds", "source_sha256"), "acquisition")
        _sha(acquisition["source_sha256"], "acquisition source")
        bounds = _list(acquisition["bounds"], 2, 2, "acquisition bounds")
        lo, hi = [_real(x, "acquisition bound", 1e-300) for x in bounds]
        if hi <= lo or any(not lo <= x <= hi for x in mz):
            raise JoinHold("declared acquisition bounds invalid")
    return sid, meta, list(zip(mz, (math.sqrt(x) for x in intensity)))


def _ions(prediction, qid, cid, sid, metadata):
    _object(prediction, ("query_id", "candidate_id", "spectrum_id", "mass_kind", "family", "charge",
                        "h_shifts", "masses", "generator_source_sha256", "status", "prediction_sha256"), "prediction")
    if (prediction["query_id"], prediction["candidate_id"], prediction["spectrum_id"]) != (qid, cid, sid):
        raise JoinHold("candidate/query/view prediction order binding mismatch")
    _sha(prediction["generator_source_sha256"], "fragment generator source")
    if digest({k: v for k, v in prediction.items() if k != "prediction_sha256"}) != prediction["prediction_sha256"]:
        raise JoinHold("prediction hash mismatch")
    if type(prediction["charge"]) is not int or prediction["charge"] != 1:
        raise JoinHold("explicit singly charged fragment hypothesis required")
    # Reuse pinned carrier/polarity gates even for already charged m/z inputs.
    chem.fragment_ions([100.0], metadata, family=prediction["family"], h_shifts=(0,))
    if prediction["mass_kind"] not in ("neutral", "ion_mz"):
        raise JoinHold("explicit neutral or ion_mz representation required")
    if prediction["mass_kind"] == "neutral":
        chem.fragment_ions([100.0], metadata, family=prediction["family"], h_shifts=prediction["h_shifts"])
    elif prediction["h_shifts"] != []:
        raise JoinHold("already charged m/z must not be shifted again")
    masses = _list(prediction["masses"], 0, 2048, "fragment masses")
    if not masses:
        if prediction["status"] != "VALID_EMPTY":
            raise JoinHold("missing prediction cannot silently become zero")
        return []
    if prediction["status"] != "READY":
        raise JoinHold("nonempty prediction must be READY")
    if prediction["mass_kind"] == "neutral":
        return chem.fragment_ions(masses, metadata, family=prediction["family"],
                                  h_shifts=prediction["h_shifts"], mass_kind="neutral")["ion_mz"]
    if prediction["mass_kind"] == "ion_mz":
        if prediction["h_shifts"] != []:
            raise JoinHold("already charged m/z must not be shifted again")
        return sorted(set(_real(x, "charged-ion m/z", 1e-300) for x in masses))
    raise JoinHold("explicit neutral or ion_mz representation required")


def score_join(export, protocol):
    """Raw-column21 ablation: hold arrays/pool/ions/max and old columns22..24.

    This mixed-feature31-column intervention needs refit. It is not a fully
    recomputed assignment rank/z feature family or compatible-view consensus.
    """
    _object(protocol, ("schema", "status", "join_source_sha256", "owned_helper_pins", "export_sha256", "labels_sha256", "query_order",
                       "candidate_order_pins", "abs_da", "ppm", "aggregation", "baseline_epsilon",
                       "replacement_column", "feature_count", "intervention_model_sha256",
                       "intervention_probability_sha256"), "protocol")
    if protocol["schema"] != "ENVEDA_ASSIGNMENT_PROTOCOL_V1" or protocol["status"] != "FROZEN_BEFORE_LABEL_VALUES":
        raise JoinHold("frozen protocol required")
    if protocol["join_source_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest() or protocol["owned_helper_pins"] != HELPER_PINS:
        raise JoinHold("frozen scientific source pin drift")
    fixed = {"abs_da": .01, "ppm": 0, "aggregation": "frozen_max_across_same_query_views",
             "baseline_epsilon": BASELINE_EPSILON, "replacement_column": FRAGMENT_COLUMN,
             "feature_count": FEATURE_COUNT}
    if any(type(protocol[k]) is not type(v) or protocol[k] != v for k, v in fixed.items()):
        raise JoinHold("assignment-only protocol drift")
    if digest(export) != protocol["export_sha256"]:
        raise JoinHold("sealed native export drift")
    _object(export, ("schema", "provenance", "queries"), "sealed export")
    reviewed_pins = _review(export["provenance"])
    if export["schema"] != "ENVEDA_ASSIGNMENT_EXPORT_V1":
        raise JoinHold("export schema mismatch")
    queries = _list(export["queries"], 1, MAX_QUERIES, "queries")
    if [q["query_id"] for q in queries] != protocol["query_order"] or len(set(protocol["query_order"])) != len(queries):
        raise JoinHold("query order or uniqueness mismatch")
    if set(protocol["candidate_order_pins"]) != set(protocol["query_order"]):
        raise JoinHold("expected pool binding incomplete")
    joined = []; work = 0
    for query in queries:
        _object(query, ("query_id", "candidate_order", "spectra", "predictions", "control", "candidate_order_sha256"), "sealed query")
        qid = _token(query["query_id"], "query identity")
        order = _list(query["candidate_order"], 1, MAX_CANDIDATES, "candidate order")
        if len(set(_token(c, "candidate") for c in order)) != len(order):
            raise JoinHold("duplicate candidate")
        pool = digest(order)
        if pool != query["candidate_order_sha256"] or pool != protocol["candidate_order_pins"][qid]:
            raise JoinHold("candidate pool/order drift")
        spectra = _list(query["spectra"], 1, MAX_VIEWS, "views")
        parsed = [_spectrum(s, qid) for s in spectra]
        if any(s["cleaning_source_sha256"] not in reviewed_pins for s in spectra):
            raise JoinHold("native cleaning source absent from component review")
        if len(set(sid for sid, _, _ in parsed)) != len(parsed):
            raise JoinHold("duplicate spectrum identity")
        control = query["control"]
        _object(control, ("candidate_order", "probabilities", "features", "native_independent_per_view", "model_sha256",
                          "runtime_source_sha256", "candidate_order_sha256", "probability_sha256",
                          "feature_sha256", "native_independent_sha256"), "control")
        _sha(control["model_sha256"], "fitted control model")
        _sha(control["runtime_source_sha256"], "control runtime source")
        if control["model_sha256"] not in reviewed_pins or control["runtime_source_sha256"] not in reviewed_pins:
            raise JoinHold("control model/runtime absent from component review")
        if control["candidate_order"] != order or control["candidate_order_sha256"] != pool:
            raise JoinHold("fitted probability candidate order mismatch")
        for value, pin in (("probabilities", "probability_sha256"), ("features", "feature_sha256"),
                           ("native_independent_per_view", "native_independent_sha256")):
            if digest(control[value]) != control[pin]:
                raise JoinHold("native control hash mismatch: " + value)
        probabilities = [_real(p, "fitted control probability", 0, 1) for p in
                         _list(control["probabilities"], len(order), len(order), "control probabilities")]
        features = _list(control["features"], len(order), len(order), "native features")
        features = [[_real(x, "native feature") for x in _list(row, FEATURE_COUNT, FEATURE_COUNT, "31-column row")]
                    for row in features]
        if any(x != feature32(x) for row in features for x in row):
            raise JoinHold("native 31-column features must retain float32 values")
        baseline = _list(control["native_independent_per_view"], len(order), len(order), "native explanation")
        baseline = [[_real(x, "native explanation", 0, 1) for x in _list(row, len(parsed), len(parsed), "native views")]
                    for row in baseline]
        predictions = _list(query["predictions"], len(order) * len(parsed), len(order) * len(parsed), "complete prediction join")
        if any(p["generator_source_sha256"] not in reviewed_pins for p in predictions):
            raise JoinHold("fragment generator absent from component review")
        evidence = []; new_features = copy.deepcopy(features)
        for i, cid in enumerate(order):
            views = []
            for j, (sid, metadata, peaks) in enumerate(parsed):
                ions = _ions(predictions[i * len(parsed) + j], qid, cid, sid, metadata)
                work += len(ions) * len(peaks)
                if work > MAX_WORK_CELLS:
                    raise JoinHold("total matching cell budget exceeded")
                assigned, independent = matching._assignment(ions, peaks, .01, 0)
                if abs(independent - baseline[i][j]) > BASELINE_EPSILON:
                    raise JoinHold("native independent-score parity failed; no rank result")
                views.append({"spectrum_id": sid, "assignment": assigned, "independent": independent,
                              "reuse_gap": independent - assigned, "ion_count": len(ions), "peak_count": len(peaks)})
            old_max = max(row["independent"] for row in views)
            new_max = max(row["assignment"] for row in views)
            if features[i][FRAGMENT_COLUMN] != feature32(old_max):
                raise JoinHold("native column21/max-view contract mismatch")
            new_features[i][FRAGMENT_COLUMN] = feature32(new_max)
            evidence.append({"candidate_id": cid, "independent_max": old_max,
                             "assignment_max": new_max, "independent_feature32": feature32(old_max),
                             "assignment_feature32": feature32(new_max), "per_view": views})
        joined.append({"query_id": qid, "candidate_order": order, "candidate_order_sha256": pool,
                       "control_model_sha256": control["model_sha256"], "control_probabilities": probabilities,
                       "original_feature_sha256": control["feature_sha256"], "joined_features": new_features,
                       "joined_feature_sha256": digest(new_features), "candidate_evidence": evidence,
                       "acquisition_declared_views": sum(s["acquisition"] is not None for s in spectra),
                       "aggregation_scope": "same-query frozen max, not compatible-view consensus",
                       "no_density_features_computed": True})
    result = {"schema": "ENVEDA_ASSIGNMENT_JOIN_V1", "data_scope": export["provenance"]["data_scope"],
              "export_sha256": digest(export), "protocol_sha256": digest(protocol), "queries": joined,
              "work_cells": work, "feature_count": FEATURE_COUNT, "replacement_column": FRAGMENT_COLUMN,
              "derived_fragment_columns22_24": "FROZEN_OLD_INDEPENDENT_FEATURES_RAW_COLUMN21_ABLATION",
              "refit_required_before_fitted_intervention": True, "official_score": None}
    result["join_sha256"] = digest(result)
    return result


def expected_rr25(scores, truth_index):
    if truth_index is None:
        return 0.0
    score = scores[truth_index]
    higher = sum(x > score for x in scores); tied = sum(x == score for x in scores)
    return sum(1.0 / rank for rank in range(higher + 1, min(25, higher + tied) + 1)) / tied


def evaluate_paired(join, labels, protocol, intervention=None):
    """Actual same-pool feature comparison; fitted comparison only after refit."""
    if digest({k: v for k, v in join.items() if k != "join_sha256"}) != join.get("join_sha256"):
        raise JoinHold("joined evidence drift")
    if join["protocol_sha256"] != digest(protocol) or join["export_sha256"] != protocol["export_sha256"]:
        raise JoinHold("join/protocol mismatch")
    _object(labels, ("schema", "label_source_sha256", "query_order", "truth"), "labels")
    _sha(labels["label_source_sha256"], "label source")
    if labels["schema"] != "ENVEDA_PRIVATE_LABELS_V1" or digest(labels) != protocol["labels_sha256"]:
        raise JoinHold("frozen label payload mismatch")
    if labels["query_order"] != protocol["query_order"] or set(labels["truth"]) != set(protocol["query_order"]):
        raise JoinHold("label query coverage/order mismatch")
    fitted = None
    if intervention is not None:
        _object(intervention, ("schema", "model_sha256", "refit_receipt_sha256", "fit_query_bindings",
                               "exposure_review_sha256", "feature_count", "join_sha256", "query_order",
                               "candidate_orders", "joined_feature_pins", "probabilities",
                               "probability_sha256"), "fitted intervention")
        if intervention["schema"] != "ENVEDA_REFITTED_ASSIGNMENT_V1" or intervention["feature_count"] != FEATURE_COUNT:
            raise JoinHold("separately refitted 31-column intervention required")
        _sha(intervention["refit_receipt_sha256"], "refit receipt")
        _sha(intervention["exposure_review_sha256"], "fit exposure review")
        if intervention["model_sha256"] != protocol["intervention_model_sha256"] or intervention["model_sha256"] is None:
            raise JoinHold("frozen refitted model pin mismatch")
        _sha(intervention["model_sha256"], "refitted model")
        fits = _list(intervention["fit_query_bindings"], 1, 10_000, "fit query bindings")
        for token in fits: _token(token, "fit query")
        if set(fits) & set(protocol["query_order"]):
            raise JoinHold("evaluation query present in declared fit cohort")
        if intervention["join_sha256"] != join["join_sha256"] or intervention["query_order"] != protocol["query_order"]:
            raise JoinHold("refitted prediction join binding mismatch")
        for key in ("candidate_orders", "joined_feature_pins", "probabilities"):
            if set(intervention[key]) != set(protocol["query_order"]):
                raise JoinHold("refitted prediction coverage mismatch")
        if digest(intervention["probabilities"]) != intervention["probability_sha256"] or intervention["probability_sha256"] != protocol["intervention_probability_sha256"]:
            raise JoinHold("frozen refitted probability payload mismatch")
        fitted = intervention["probabilities"]
    rows = []
    for query in join["queries"]:
        qid = query["query_id"]; order = query["candidate_order"]
        truth = _token(labels["truth"][qid], "truth identity")
        ti = order.index(truth) if truth in order else None
        old = [x["independent_feature32"] for x in query["candidate_evidence"]]
        new = [x["assignment_feature32"] for x in query["candidate_evidence"]]
        row = {"truth_in_pool": ti is not None, "independent_feature_rr25": expected_rr25(old, ti),
               "assignment_feature_rr25": expected_rr25(new, ti),
               "control_fitted_rr25": expected_rr25(query["control_probabilities"], ti)}
        row["feature_delta"] = row["assignment_feature_rr25"] - row["independent_feature_rr25"]
        if fitted is not None:
            if intervention["model_sha256"] == query["control_model_sha256"]:
                raise JoinHold("unchanged control model is not a refitted intervention")
            if intervention["candidate_orders"][qid] != order or intervention["joined_feature_pins"][qid] != query["joined_feature_sha256"]:
                raise JoinHold("refitted features or candidate order mismatch")
            probs = [_real(x, "refitted probability", 0, 1) for x in _list(fitted[qid], len(order), len(order), "refitted probabilities")]
            row["intervention_fitted_rr25"] = expected_rr25(probs, ti)
            row["fitted_delta"] = row["intervention_fitted_rr25"] - row["control_fitted_rr25"]
        rows.append(row)
    def summary(delta_key):
        deltas = [r[delta_key] for r in rows]
        return {"mean_delta": sum(deltas) / len(deltas), "wins": sum(x > 1e-12 for x in deltas),
                "losses": sum(x < -1e-12 for x in deltas), "ties": sum(abs(x) <= 1e-12 for x in deltas)}
    return {"status": "INVENTED_FLOW_ONLY" if join["data_scope"] == "invented" else "EXPOSED_PRIVATE_DEVELOPMENT_ONLY",
            "queries": len(rows), "truth_in_pool": sum(r["truth_in_pool"] for r in rows),
            "pool_recall": sum(r["truth_in_pool"] for r in rows) / len(rows),
            "mean_independent_feature_rr25": sum(r["independent_feature_rr25"] for r in rows) / len(rows),
            "mean_assignment_feature_rr25": sum(r["assignment_feature_rr25"] for r in rows) / len(rows),
            "matching_feature_only_comparison": summary("feature_delta"),
            "fitted_ranker_comparison": summary("fitted_delta") if fitted is not None else "HOLD_NO_REFITTED_PREDICTIONS",
            "per_query_metrics_no_identifiers": rows, "official_score": None,
            "scientific_limits": "Declared provenance is not authenticated; no unseen-transfer/adoption claim; candidate-pool misses score zero."}
