"""Source-only ICE aggregation ablation over an immutable accepted runner.

The scientific core differs at one assignment: MAX becomes addition. Original
filtering, anchored grouping, representatives, stable top-k selection and FP64
normalization are retained. This module loads no models and executes no runner
entrypoint, installation, activation, CLI, notebook or trainer.

The SUM arm has an explicit extra eligibility guard: invalid normalized output
from finite-positive summation raises FiniteSumOverflowHold. That guard is a
domain restriction, not part of the unchanged original MAX control.
"""

import ast
import hashlib
import math

RUNNER_SHA256 = "622d576e47fb6405b73a1ef2d400f97fefab4017a2ba6fccef406e4334c057d4"
ARMS = ("max_control", "anchored_ice_sum")
MAX_ASSIGNMENT = "            it[-1] = max(it[-1], v)"
SUM_ASSIGNMENT = "            it[-1] += v"
OLD_SCORE_SITE = "            pm, pp = merge_predicted(sp, args.merge_tol, args.pred_top)"
NEW_SCORE_SITE = "            pm, pp = _codex_channel_reducer(name, sp, args.merge_tol, args.pred_top)"
PURE_FUNCTIONS = (
    "clean_spectrum", "merge_predicted", "_weighted", "entropy_similarity",
    "conditions", "score_item",
)


class FiniteSumOverflowHold(ValueError):
    """The SUM arm is ineligible; no zero scores or MAX fallback are produced."""


def extract_pinned_functions(runner_bytes):
    """Return source for an explicit allowlist, without executing the runner."""
    if hashlib.sha256(runner_bytes).hexdigest() != RUNNER_SHA256:
        raise ValueError("Accepted runner source hash mismatch")
    source = runner_bytes.decode("utf-8")
    tree = ast.parse(source, filename="<immutable-accepted-forward-runner>")
    selected = {}
    for name in PURE_FUNCTIONS:
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
        if len(nodes) != 1:
            raise ValueError("Expected exactly one pinned function: " + name)
        selected[name] = ast.get_source_segment(source, nodes[0])
    if selected["merge_predicted"].count(MAX_ASSIGNMENT) != 1:
        raise ValueError("Expected exactly one original MAX assignment")
    if selected["score_item"].count(OLD_SCORE_SITE) != 1:
        raise ValueError("Expected exactly one original reducer call site")
    return selected


def build_scoring_namespace(runner_bytes, arm, stats=None):
    """Compile only six pinned pure functions plus the channel dispatcher.

    ``score_item`` still requires a caller-supplied model object. This function
    defines no Models class, installs nothing and performs no prediction. The
    original entropy and condition functions are compiled without modification.
    """
    if arm not in ARMS:
        raise ValueError("Unrecognized frozen arm")
    sources = extract_pinned_functions(runner_bytes)
    namespace = {"__name__": "codex_pinned_pure_forward_functions", "math": math}
    for name in PURE_FUNCTIONS:
        exec(compile(sources[name], "<pinned-pure:" + name + ">", "exec"), namespace)
    original_merge = namespace["merge_predicted"]
    sum_source = sources["merge_predicted"].replace(MAX_ASSIGNMENT, SUM_ASSIGNMENT)
    sum_namespace = {}
    exec(compile(sum_source, "<pinned-merge:one-assignment-SUM>", "exec"), sum_namespace)
    sum_core = sum_namespace["merge_predicted"]
    counters = stats if stats is not None else {}
    counters.update(
        arm=arm, runner_sha256=RUNNER_SHA256,
        iceberg_reducer_calls=0, glacier_reducer_calls=0,
        finite_sum_overflow_holds=0,
    )

    def guarded_sum(spec, merge_tol=1e-3, top=100):
        import numpy as np
        mz, probability = sum_core(spec, merge_tol, top)
        # The original filter already excludes nonfinite/nonpositive raw rows.
        # A nonempty result must remain finite and L1-normalized. With finite
        # positive input, failed normalization identifies an overflow domain.
        # Do not alter group construction, drop peaks, rescale or fall back.
        if len(probability) and (
            not np.isfinite(probability).all()
            or not np.isclose(probability.sum(), 1.0, rtol=1e-12, atol=1e-12)
        ):
            counters["finite_sum_overflow_holds"] += 1
            raise FiniteSumOverflowHold("HOLD_FINITE_SUM_OVERFLOW: no experimental scores")
        return mz, probability

    def dispatch(name, spec, merge_tol=1e-3, top=100):
        if name not in ("iceberg", "glacier"):
            raise ValueError("Unexpected model channel")
        counters[name + "_reducer_calls"] += 1
        if name == "iceberg" and arm == "anchored_ice_sum":
            return guarded_sum(spec, merge_tol, top)
        return original_merge(spec, merge_tol, top)

    namespace["_codex_channel_reducer"] = dispatch
    namespace["_codex_original_merge"] = original_merge
    namespace["_codex_sum_core"] = sum_core
    namespace["_codex_guarded_sum"] = guarded_sum
    namespace["_codex_stats"] = counters
    changed_score = sources["score_item"].replace(OLD_SCORE_SITE, NEW_SCORE_SITE)
    exec(compile(changed_score, "<pinned-score:channel-dispatch-only>", "exec"), namespace)
    return namespace
