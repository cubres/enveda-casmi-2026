"""Original invented-fixture qualification harness; source-only until root runs.

No arrays, checkpoints, spectra, chemistry, credentials or network services are
read. Only per-check status, elapsed time and process peak RSS are printed.
Run in a fresh root-owned CPU process with an external 60s wall cap.
"""

import json
import math
import random
import resource
import sys
import time

from packed_bernoulli_reference import Contract, ContractError, packed_scores, dense_reference_scores


def pack(bits, order):
    out = bytearray(277)
    for i, bit in enumerate(bits):
        if bit:
            out[i // 8] |= 1 << (7 - i % 8 if order == "big" else i % 8)
    return bytes(out)


def inputs(layout, order, seed=71):
    # This schema identifier is deliberately invented and not an actual model
    # or generator binding. Runtime science admission cannot use it.
    h = "a" * 64 if layout == "keys0_166_zero_key" else "b" * 64
    c = Contract(layout, order, h)
    rng = random.Random(seed)
    bits = [[rng.randrange(2) for _ in range(2216)] for _ in range(12)]
    for row in bits:
        for i in c.excluded:
            row[i] = 0
    rows = tuple(pack(row, order) for row in bits)
    z = tuple(tuple(rng.uniform(-30, 30) for _ in range(2216)) for _ in range(4))
    return c, rows, z, (0.5, 2.0, 0.0, 1.0)


def score(c, rows, z, w):
    args = dict(candidate_schema_sha256=c.schema_binding_sha256,
                logit_schema_sha256=c.schema_binding_sha256)
    a = packed_scores(rows, z, w, c, **args)
    b = dense_reference_scores(rows, z, w, c, **args)
    if not all(math.isclose(x, y, rel_tol=1e-12, abs_tol=1e-8) for x, y in zip(a.full_loglik, b)):
        raise AssertionError("DIRECT_LOG_LIKELIHOOD_MISMATCH")
    # Exact duplicate rows have stable input-index ties. Near-tie ordering is
    # not asserted; floating subtraction may cancel at the full-score scale.
    for i in range(len(b)):
        for j in range(i + 1, len(b)):
            if abs(b[i] - b[j]) > 1e-7 and (a.rank_only[i] > a.rank_only[j]) != (b[i] > b[j]):
                raise AssertionError("RANK_ORDER_MISMATCH_ABOVE_MARGIN")
    return a


def expect_hold(fn):
    try:
        fn()
    except ContractError:
        return
    raise AssertionError("EXPECTED_CONTRACT_HOLD")


def qualify():
    checks = []
    def check(name, fn):
        fn()
        checks.append(dict(name=name, status="PASS"))
    for layout in ("keys0_166_zero_key", "keys1_166"):
        for order in ("big", "little"):
            c, rows, z, w = inputs(layout, order)
            check(layout + "_" + order + "_weighted_direct_identity", lambda: score(c, rows, z, w))
    c, rows, z, w = inputs("keys0_166_zero_key", "big")
    bindings = dict(candidate_schema_sha256=c.schema_binding_sha256, logit_schema_sha256=c.schema_binding_sha256)
    changed = [list(r) for r in z]
    for r in changed:
        r[2048], r[2215] = 1000.0, -1000.0
    def excluded_logits():
        if score(c, rows, z, w) != score(c, rows, tuple(tuple(r) for r in changed), w):
            raise AssertionError("EXCLUDED_LOGITS_CHANGED_SCORE")
    check("excluded_dummy_and_padding_logits_invariant", excluded_logits)
    for i in (2048, 2215):
        bitrow = [0] * 2216; bitrow[i] = 1
        check("nonzero_excluded_coordinate_" + str(i),
              lambda row=pack(bitrow, "big"): expect_hold(lambda: packed_scores((row,), z, w, c, **bindings)))
    c166, _, _, _ = inputs("keys1_166", "big")
    b166 = dict(candidate_schema_sha256=c166.schema_binding_sha256, logit_schema_sha256=c166.schema_binding_sha256)
    def first_maccs_real_key():
        bits = [0] * 2216; bits[2048] = 1
        zz = [0.0] * 2216; zz[2048] = 3.0
        result = packed_scores((pack([0]*2216, "big"), pack(bits, "big")), (tuple(zz),), (1.0,), c166, **b166)
        if result.rank_only != (0.0, 3.0): raise AssertionError("MACCS166_FIRST_KEY_MASKED")
    check("maccs166_first_key_is_real", first_maccs_real_key)
    for i in (2214, 2215):
        bits = [0] * 2216; bits[i] = 1
        check("maccs166_nonzero_padding_" + str(i),
              lambda row=pack(bits, "big"): expect_hold(lambda: packed_scores((row,), z, w, c166, **b166)))
    check("candidate_binding_mismatch", lambda: expect_hold(lambda: packed_scores(rows, z, w, c, candidate_schema_sha256="b"*64, logit_schema_sha256="a"*64)))
    check("logit_binding_mismatch", lambda: expect_hold(lambda: packed_scores(rows, z, w, c, candidate_schema_sha256="a"*64, logit_schema_sha256="b"*64)))
    check("missing_maccs_declaration", lambda: expect_hold(lambda: Contract("", "big", "a"*64)))
    check("short_packed_row", lambda: expect_hold(lambda: packed_scores((rows[0][:-1],), z, w, c, **bindings)))
    check("wrong_output_dimension", lambda: expect_hold(lambda: packed_scores(rows, tuple(r[:-1] for r in z), w, c, **bindings)))
    for name, weights in (("negative_weight", (-1, 2, 0, 1)), ("nan_weight", (math.nan, 2, 0, 1)), ("zero_total", (0, 0, 0, 0))):
        check(name, lambda weights=weights: expect_hold(lambda: packed_scores(rows, z, weights, c, **bindings)))
    oversized = [list(r) for r in z]; oversized[0][0] = 10**1000
    check("oversized_integer_logit", lambda: expect_hold(lambda: packed_scores(rows, tuple(tuple(r) for r in oversized), w, c, **bindings)))
    check("oversized_integer_weight", lambda: expect_hold(lambda: packed_scores(rows, z, (10**1000, 2, 0, 1), c, **bindings)))
    check("candidate_bound", lambda: expect_hold(lambda: packed_scores((rows[0],)*65, z, w, c, **bindings)))
    check("spectrum_bound", lambda: expect_hold(lambda: packed_scores(rows, (z[0],)*9, (1,)*9, c, **bindings)))
    extreme = tuple(tuple(1000.0 if i % 2 else -1000.0 for i in range(2216)) for _ in range(2))
    check("extreme_finite_logits_stable", lambda: score(c, rows, extreme, (1e308, 1e308)))
    def ties():
        result = score(c, (rows[0], rows[0]), z, w)
        if result.ranking_indices != (0, 1): raise AssertionError("TIE_ORDER_CHANGED")
    check("exact_duplicate_stable_tie", ties)
    def probability_pooling_is_distinct():
        sigmoid = lambda x: 1 / (1 + math.exp(-x))
        a = (sigmoid(10) + sigmoid(-8)) / 2
        pooled_a = math.log(a / (1 - a))
        if not ((10-8)/2 > .4 and pooled_a < .4): raise AssertionError("POOLING_COUNTEREXAMPLE")
    check("probability_pooling_not_logit_pooling", probability_pooling_is_distinct)
    return checks


def main():
    if sys.argv[1:] != ["--invented-fixtures-only"]:
        raise SystemExit("ROOT_OWNED_INVENTED_FIXTURE_FLAG_REQUIRED")
    start = time.perf_counter(); cpu = time.process_time()
    result = qualify()
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps(dict(status="PASS_INVENTED_ARITHMETIC_ONLY", checks=result,
                          elapsed_wall_s=time.perf_counter()-start, process_cpu_s=time.process_time()-cpu,
                          peak_rss_bytes=rss if sys.platform == "darwin" else rss*1024,
                          native_model_execution=False, model_quality_measured=False,
                          scientific_input_reads=0, network_calls=0), sort_keys=True))


if __name__ == "__main__":
    main()
