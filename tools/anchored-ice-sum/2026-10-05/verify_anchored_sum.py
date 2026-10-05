"""Deterministic pure-array verification; no models, notebooks or remote I/O.

The default reference is the adjacent inert accepted_fwd_runner.py. The optional
CCO NPZ must be the exact retained synthetic canary. Reports go to stdout; the
verifier itself writes no files and imports no reference runner or model class.
"""

import argparse
import ast
import hashlib
import json
import platform
import warnings
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from anchored_ice_sum import (
    FiniteSumOverflowHold, MAX_ASSIGNMENT, SUM_ASSIGNMENT,
    build_scoring_namespace, extract_pinned_functions,
)

CANARY_SHA256 = "614dc1f2be54390dfa1ad30ff64e41759010bd2442e453b473bacaba92086e8b"


def verify_fake_two_channel(control, experimental):
    """Exercise unchanged job construction with constructed arrays, not models."""
    item = {
        "id": "constructed-two-channel-only",
        "candidates": ["CCO", "COC", "CCC"],
        "spectra": [
            {"mz": [31., 45.], "it": [.7, .3], "precursor_mz": 47.04914,
             "adduct": "[M+H]+", "ce": energy, "instrument": "QTOF", "mode": "positive"}
            for energy in (40., 60.)
        ],
    }
    args = SimpleNamespace(ce_bucket=5., merge_tol=.001, pred_top=100, tol=.01)
    allowed = {"[M+H]+", "[M+Na]+"}
    instr_map = {"QTOF": "QTOF", "*": "Unknown"}
    calls = []

    def fake_interface():
        call_records = []
        calls.append(call_records)

        def predict(channel, smiles, energies, adducts, instruments, precursors):
            call_records.append({
                "channel": channel, "smiles": list(smiles), "energies": list(energies),
                "adducts": list(adducts), "instruments": list(instruments),
                "precursors": list(precursors),
            })
            output = []
            for smiles_value in smiles:
                if channel == "iceberg" and smiles_value == "CCO":
                    peaks = [[31., 1.], [31., 1.], [45., 1.]]
                elif channel == "iceberg" and smiles_value == "COC":
                    peaks = [[31., 1.], [45., 2.]]
                elif channel == "iceberg":
                    peaks = [[31., 3.], [45., 1.]]
                else:
                    peaks = [[31., 2.], [45., 1.]]
                output.append(np.asarray(peaks, np.float64))
            return output

        # A constructed interface stub; no accepted Models class is defined,
        # instantiated or imported, and there are no learned parameters.
        return SimpleNamespace(m={"iceberg": None, "glacier": None}, predict=predict)

    before = json.dumps(item, sort_keys=True)
    old, old_raw, old_jobs = control["score_item"](fake_interface(), item, args, allowed, instr_map, keep_raw=True)
    new, new_raw, new_jobs = experimental["score_item"](fake_interface(), item, args, allowed, instr_map, keep_raw=True)
    assert json.dumps(item, sort_keys=True) == before
    assert calls[0] == calls[1]
    assert old_jobs == new_jobs == 12
    assert len(calls[0]) == len(calls[1]) == 2
    assert list(old_raw) == list(new_raw)
    assert all(np.array_equal(old_raw[k], new_raw[k]) for k in old_raw)
    assert np.array_equal(old["glacier"], new["glacier"])
    assert old["iceberg"][0] != new["iceberg"][0]
    assert old["iceberg"][1:] == new["iceberg"][1:]
    assert all(np.isfinite(values).all() for values in (old["iceberg"], new["iceberg"], old["glacier"], new["glacier"]))
    return {
        "status": "PASS_CONSTRUCTED_INTERFACE_ONLY", "job_count_per_arm": 12,
        "predict_calls_per_arm": 2, "candidate_count": 3, "conditions_per_channel": 2,
        "identical_prediction_call_arguments": True, "input_unchanged": True,
        "raw_predicted_arrays_identical": True, "GL_scores_exact_equal": True,
        "ICE_changed_candidate_indices": [0], "unchanged_ICE_candidate_indices": [1, 2],
        "old_ICE_scores": old["iceberg"], "new_ICE_scores": new["iceberg"],
        "native_models_or_serving_or_labels": False,
    }


def main():
    if not __debug__:
        raise RuntimeError("Verification requires assertions enabled; do not use Python -O")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", type=Path, default=Path(__file__).with_name("accepted_fwd_runner.py"))
    parser.add_argument("--synthetic-canary", type=Path, default=None)
    args = parser.parse_args()
    runner_bytes = args.runner.read_bytes()
    canary_bytes = None
    if args.synthetic_canary is not None:
        canary_bytes = args.synthetic_canary.read_bytes()
        if hashlib.sha256(canary_bytes).hexdigest() != CANARY_SHA256:
            raise ValueError("Retained synthetic CCO canary hash mismatch")
    sources = extract_pinned_functions(runner_bytes)
    # Independently AST-extract the exact original function as the oracle.
    original_tree = ast.parse(runner_bytes.decode("utf-8"))
    node = next(n for n in original_tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "merge_predicted")
    oracle_namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "<independent-AST-oracle>", "exec"), oracle_namespace)
    oracle = oracle_namespace["merge_predicted"]
    control = build_scoring_namespace(runner_bytes, "max_control")
    experimental = build_scoring_namespace(runner_bytes, "anchored_ice_sum")
    original_source = ast.get_source_segment(runner_bytes.decode("utf-8"), node)
    assert sources["merge_predicted"] == original_source
    transformed = original_source.replace(MAX_ASSIGNMENT, SUM_ASSIGNMENT)
    original_ast = ast.parse(original_source)
    sum_ast = ast.parse(transformed)
    changed = [n for n in ast.walk(sum_ast) if isinstance(n, ast.AugAssign)]
    assert len(changed) == 1 and isinstance(changed[0].op, ast.Add)
    assert len([n for n in ast.walk(original_ast) if isinstance(n, ast.AugAssign)]) == 0

    checks = []

    def compare(label, spec, merge_tol=.001, top=100, expected=None, collision_free=False):
        old = oracle(spec, merge_tol, top)
        for name in ("iceberg", "glacier"):
            actual = control["_codex_channel_reducer"](name, spec, merge_tol, top)
            assert all(np.array_equal(a, b) for a, b in zip(old, actual)), label + ": MAX control drift"
        gl = experimental["_codex_channel_reducer"]("glacier", spec, merge_tol, top)
        assert all(np.array_equal(a, b) for a, b in zip(old, gl)), label + ": GL delegation drift"
        new = experimental["_codex_channel_reducer"]("iceberg", spec, merge_tol, top)
        if expected is not None:
            assert np.array_equal(new[0], np.asarray(expected[0], np.float64)), label + ": representative/group drift"
            assert np.allclose(new[1], np.asarray(expected[1], np.float64), rtol=1e-15, atol=1e-15), label + ": SUM drift"
        if collision_free:
            assert all(np.array_equal(a, b) for a, b in zip(old, new)), label + ": no-collision parity drift"
        checks.append(label)
        return old, new

    compare("anchored-chain-not-transitive", [[0., 1.], [.00075, 2.], [.0015, 4.]],
            expected=([0., .0015], [3/7, 4/7]))
    compare("exact-boundary-inside", [[0., 1.], [.001, 2.]], expected=([0.], [1.]))
    compare("nextafter-boundary-outside", [[0., 1.], [np.nextafter(.001, np.inf), 2.]],
            expected=([0., np.nextafter(.001, np.inf)], [1/3, 2/3]), collision_free=True)
    compare("stable-mass-sort-first-representative", [[.0008, 3.], [0., 1.], [.0004, 2.], [2., 6.]],
            expected=([0., 2.], [.5, .5]))
    compare("known-duplicate-sum", [[1., 1.], [1., 3.], [2., 2.]],
            expected=([1., 2.], [2/3, 1/3]))
    compare("sum-changes-topk-by-strength-only", [[1., 2.], [1., 2.], [2., 3.]], top=1,
            expected=([1.], [1.]))
    compare("equal-summed-topk-stable-order", [[3., 2.], [1., 1.], [2., 2.], [1., 1.]], top=2,
            expected=([1., 2.], [.5, .5]))
    compare("top100-tied-101-groups", [[float(k), 1.] for k in reversed(range(101))],
            expected=(list(range(100)), [.01]*100), collision_free=True)
    compare("empty", [], expected=([], []), collision_free=True)
    compare("all-filtered", [[np.nan, 1.], [1., np.inf], [2., 0.], [3., -1.]],
            expected=([], []), collision_free=True)
    compare("mixed-filtering-retained", [[np.nan, 1.], [np.inf, 1.], [1., np.nan], [1., np.inf],
            [1., -np.inf], [1., 0.], [1., -1.], [1., 1.], [1., 2.], [2., 3.]],
            expected=([1., 2.], [.5, .5]))
    compare("flat-reshape-contract-preserved", [1., 1., 1., 2., 2., 3.],
            expected=([1., 2.], [.5, .5]))
    compare("negative-masses-preserved-original-contract", [[-2., 1.], [-2., 2.], [1., 3.]],
            expected=([-2., 1.], [.5, .5]))

    rng = np.random.default_rng(20261005)
    random_collision_free_cases = 0
    random_duplicate_cases = 0
    for i in range(250):
        n = int(rng.integers(1, 180))
        m = np.arange(n, dtype=np.float64) * 2
        it = rng.uniform(.001, 10., n)
        spec = np.column_stack((m, it))[rng.permutation(n)]
        compare("random-no-collision-" + str(i), spec, top=int(rng.choice([1, 2, 100])), collision_free=True)
        random_collision_free_cases += 1
    for i in range(250):
        n = int(rng.integers(1, 80))
        multiplicities = rng.integers(1, 5, n)
        m = np.repeat(np.arange(n, dtype=np.float64) * 2, multiplicities)
        it = rng.uniform(.001, 10., len(m))
        spec = np.column_stack((m, it))[rng.permutation(len(m))]
        expected_it = np.array([it[m == k*2].sum() for k in range(n)])
        expected = (np.arange(n)*2, expected_it/expected_it.sum())
        compare("random-exact-duplicates-" + str(i), spec, expected=expected)
        random_duplicate_cases += 1

    overflow_checks = []
    for label, spec in (
        ("within-group-finite-addition-overflow", [[1., 1e308], [1., 1e308]]),
        ("finite-normalization-denominator-overflow", [[1., 1e308], [2., 1e308]]),
    ):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", RuntimeWarning)
            try:
                experimental["_codex_channel_reducer"]("iceberg", spec, .001, 100)
            except FiniteSumOverflowHold as error:
                assert "HOLD_FINITE_SUM_OVERFLOW" in str(error)
            else:
                raise AssertionError(label + ": no explicit HOLD")
        overflow_checks.append({"case": label, "status": "HOLD", "runtime_warning_count": len(caught)})

    invalid_shape_checks = 0
    for spec in ([1.], [1., 2., 3.], [[1., 2., 3.]]):
        for fn in (oracle, experimental["_codex_guarded_sum"]):
            try:
                fn(spec)
            except ValueError:
                pass
            else:
                raise AssertionError("original reshape rejection drift")
        invalid_shape_checks += 1
    try:
        experimental["_codex_channel_reducer"]("unknown", [[1., 1.]])
    except ValueError:
        pass
    else:
        raise AssertionError("unknown channel not rejected")

    canary_report = []
    if args.synthetic_canary is not None:
        with np.load(args.synthetic_canary, allow_pickle=False) as arrays:
            assert len(arrays.files) == 2
            for key in arrays.files:
                assert key.startswith("iceberg|codex-ethanol-mechanical|")
                raw = arrays[key]
                old, new = compare("retained-synthetic-CCO-" + key.split("|")[-1], raw)
                assert np.array_equal(old[0], new[0])
                assert len(old[0]) == len(new[0]) == 10
                canary_report.append({
                    "collision_energy_ev": float(key.split("|")[-1]),
                    "raw_rows": len(raw), "positive_rows": int((raw[:, 1] > 0).sum()),
                    "max_peak_count": len(old[0]), "sum_peak_count": len(new[0]),
                    "representative_masses_exact_equal": True,
                    "top100_truncation": False,
                    "probability_L1_difference": float(np.abs(old[1]-new[1]).sum()),
                    "old_vs_new_entropy_similarity": control["entropy_similarity"](*old, *new),
                })

    fake_report = verify_fake_two_channel(control, experimental)
    assert "Models" not in experimental and "main" not in experimental
    assert "activate" not in experimental and "install_site" not in experimental
    print(json.dumps({
        "status": "PASS_SOURCE_ONLY_SYNTHETIC_REDUCER_VERIFICATION",
        "runner_sha256": hashlib.sha256(runner_bytes).hexdigest(),
        "canary_sha256": hashlib.sha256(canary_bytes).hexdigest() if canary_bytes is not None else None,
        "canary_status": "PASS_RETAINED_SYNTHETIC_ONLY" if canary_bytes is not None else "UNAVAILABLE_NOT_SUPPLIED",
        "python": platform.python_version(), "numpy": np.__version__,
        "ordinary_case_count": len(checks), "named_boundary_and_filter_cases": checks[:13],
        "random_collision_free_exact_parity_cases": random_collision_free_cases,
        "random_duplicate_known_sum_cases": random_duplicate_cases,
        "overflow_cases": overflow_checks, "invalid_shape_cases": invalid_shape_checks,
        "canary": canary_report,
        "native_models_executed": False, "native_model_objects_instantiated": False,
        "fake_prediction_interfaces_instantiated": True, "fake_two_channel": fake_report,
        "actual_queries_or_labels_read": False, "native_serve_integration_proven": False,
        "hidden_ranking_effect_verified": False, "official_score_gain_claim": False,
        "domain": "Original float64 reshape/finite-positive filter; tested tolerance .001, top1/2/100; synthetic finite ordinary values, explicit overflow/malformed-shape cases and fake two-channel score_item; optional hash-checked retained synthetic CCO only",
        "sum_guard_is_additional_eligibility_restriction": True,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
