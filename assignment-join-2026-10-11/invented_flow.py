# SPDX-License-Identifier: MIT
"""Executable invented fixtures: one matching win, one loss and one pool miss.

No observed spectrum, model, fitted probability, label or score is real here.
Symbolic model/receipt pins exercise binding; they are not training receipts.
"""
import math
from assignment_join import digest, seal_native_export, freeze_protocol, score_join, evaluate_paired, chem, feature32


def fixture(fitted=False):
    h = digest
    pins = {role: h("INVENTED " + role) for role in
            ("native-cleaner", "fragment-generator", "control-model", "control-runtime")}
    total = .8 + .5 + math.sqrt(.11)
    legacy = [1.3 / total, (.8 + math.sqrt(.11)) / total, 0.0]
    queries = []
    for qi in (1, 2, 3):
        qid = "invented-query-" + str(qi); sid = "invented-view-1"
        candidates = ["invented-A", "invented-B", "invented-C"]
        spectrum = {"query_id": qid, "spectrum_id": sid, "adduct": "[M+H]+", "mode": "positive",
                    "precursor_mz": 301.00727645217, "mz": [100.0, 100.015, 150.0],
                    "intensity": [.64, .25, .11], "cleaning_source_sha256": pins["native-cleaner"],
                    "instrument": "invented-instrument", "collision_energy_ev": [20.0], "acquisition": None}
        ions = [[100.007], [100.0, 150.0], []]
        predictions = []
        for cid, masses in zip(candidates, ions):
            neutral = qi == 2
            predictions.append({"query_id": qid, "candidate_id": cid, "spectrum_id": sid,
                                "mass_kind": "neutral" if neutral else "ion_mz", "family": "protonated",
                                "charge": 1, "h_shifts": [0] if neutral else [],
                                "masses": [x - chem.PROTON for x in masses] if neutral else masses,
                                "generator_source_sha256": pins["fragment-generator"],
                                "status": "READY" if masses else "VALID_EMPTY"})
        features = []
        for value in legacy:
            row = [0.0] * 31; row[21] = feature32(value); features.append(row)
        control = {"candidate_order": candidates[:], "probabilities": [.6, .3, .1], "features": features,
                   "native_independent_per_view": [[x] for x in legacy], "model_sha256": pins["control-model"],
                   "runtime_source_sha256": pins["control-runtime"]}
        queries.append({"query_id": qid, "candidate_order": candidates, "spectra": [spectrum],
                        "predictions": predictions, "control": control})
    draft = {"schema": "ENVEDA_ASSIGNMENT_EXPORT_V1", "provenance": {
             "data_scope": "invented", "data_rights_review_sha256": h("invented-data-review"),
             "component_review_sha256": h("invented-component-review"), "exposure": "all inputs invented; no real experiment",
             "component_pins": [{"role": role, "source_sha256": pin, "code_license_spdx": "MIT",
                                 "reviewed_usage": "authorized-private-development"} for role, pin in pins.items()]},
             "queries": queries}
    export = seal_native_export(draft)
    labels = {"schema": "ENVEDA_PRIVATE_LABELS_V1", "label_source_sha256": h("invented-label-source"),
              "query_order": [q["query_id"] for q in queries],
              "truth": {"invented-query-1": "invented-B", "invented-query-2": "invented-A", "invented-query-3": "not-generated"}}
    probabilities = {q["query_id"]: [.2, .7, .1] for q in queries}
    protocol = freeze_protocol(export, labels_sha256=digest(labels),
                               intervention_model_sha256=h("INVENTED REFITTED MODEL") if fitted else None,
                               intervention_probability_sha256=digest(probabilities) if fitted else None)
    joined = score_join(export, protocol)
    intervention = None
    if fitted:
        intervention = {"schema": "ENVEDA_REFITTED_ASSIGNMENT_V1", "model_sha256": h("INVENTED REFITTED MODEL"),
                        "refit_receipt_sha256": h("INVENTED REFIT RECEIPT; NO REAL TRAINING"),
                        "fit_query_bindings": ["invented-fitting-query"], "exposure_review_sha256": h("INVENTED EXPOSURE REVIEW"),
                        "feature_count": 31, "join_sha256": joined["join_sha256"], "query_order": protocol["query_order"],
                        "candidate_orders": {q["query_id"]: q["candidate_order"] for q in joined["queries"]},
                        "joined_feature_pins": {q["query_id"]: q["joined_feature_sha256"] for q in joined["queries"]},
                        "probabilities": probabilities, "probability_sha256": digest(probabilities)}
    return export, protocol, joined, labels, intervention


def demonstration():
    export, protocol, joined, labels, intervention = fixture(fitted=True)
    result = evaluate_paired(joined, labels, protocol, intervention)
    return {"status": "INVENTED_CPU_FLOW_ONLY_NO_COMPETITION_METRICS_OR_FIT",
            "scoring": result, "work_cells": joined["work_cells"], "native_export_sha256": digest(export),
            "protocol_sha256": digest(protocol), "join_sha256": joined["join_sha256"],
            "feature_columns": 31, "changed_column": 21, "chemical_identity_verified": False,
            "actual_training_performed": False, "models_loaded": 0, "data_loaded": 0,
            "native_jobs": 0, "submissions": 0, "probabilities": "invented fixtures, not model outputs"}


if __name__ == "__main__":
    import json, os, resource
    os.nice(5); resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    print(json.dumps(demonstration(), indent=2, allow_nan=False))
