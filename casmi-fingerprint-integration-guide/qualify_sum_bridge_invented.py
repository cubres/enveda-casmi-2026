"""Separate original SUM-bridge proof; no model or scientific data inputs.

Source-only until a root-owned, bounded CPU invocation. The earlier 25-check
receipt does not cover this module. No import-time I/O or fixture execution.
"""

import json
import math
import resource
import sys
import time

from packed_bernoulli_reference import ContractError
from packed_v2_sum_bridge import sum_bernoulli_scores
from qualify_invented_fixtures import inputs, expect_hold


def direct_sum(rows, z):
    # Independent all-output Bernoulli formula, including excluded zeros.
    result = []
    for row in rows:
        terms = []
        for spectrum in z:
            for i, value in enumerate(spectrum):
                bit = (row[i // 8] >> (7 - i % 8)) & 1
                x = -value if bit else value
                terms.append(-(max(x, 0.0) + math.log1p(math.exp(-abs(x)))))
        result.append(math.fsum(terms))
    return tuple(result)


def qualify():
    c, rows, z, _ = inputs("keys0_166_zero_key", "big")
    bindings = dict(candidate_schema_sha256=c.schema_binding_sha256,
                    logit_schema_sha256=c.schema_binding_sha256)
    checks = []
    def check(name, fn):
        fn(); checks.append(dict(name=name, status="PASS"))
    def compare(logits):
        a = sum_bernoulli_scores(rows, logits, c, **bindings)
        b = direct_sum(rows, logits)
        if not all(math.isclose(x, y, rel_tol=1e-12, abs_tol=1e-8) for x, y in zip(a, b)):
            raise AssertionError("ALL_OUTPUT_SUM_MISMATCH")
        for i in range(len(a)):
            for j in range(i + 1, len(a)):
                if abs(b[i]-b[j]) > 1e-7 and (a[i] > a[j]) != (b[i] > b[j]):
                    raise AssertionError("RANK_MISMATCH_ABOVE_MARGIN")
    check("one_spectrum_sum_equals_direct", lambda: compare(z[:1]))
    check("four_spectra_sum_equals_direct", lambda: compare(z))
    changed = [list(r) for r in z]
    for i, r in enumerate(changed):
        r[2048], r[2215] = 1000.0 if i % 2 else -1000.0, -1000.0 if i % 2 else 1000.0
    check("zero_coordinate_constants_restored", lambda: compare(tuple(tuple(r) for r in changed)))
    check("oversized_spectrum_count_before_allocation", lambda: expect_hold(lambda: sum_bernoulli_scores(rows, (z[0],)*9, c, **bindings)))
    check("nonsequence_spectrum_input", lambda: expect_hold(lambda: sum_bernoulli_scores(rows, None, c, **bindings)))
    other, _, _, _ = inputs("keys1_166", "big")
    check("wrong_maccs_layout_rejected", lambda: expect_hold(lambda: sum_bernoulli_scores(rows, z, other, **bindings)))
    little, _, _, _ = inputs("keys0_166_zero_key", "little")
    check("wrong_bitorder_rejected", lambda: expect_hold(lambda: sum_bernoulli_scores(rows, z, little, **bindings)))
    return checks


def main():
    if sys.argv[1:] != ["--invented-fixtures-only"]:
        raise SystemExit("ROOT_OWNED_INVENTED_FIXTURE_FLAG_REQUIRED")
    wall = time.perf_counter(); cpu = time.process_time()
    checks = qualify()
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps(dict(status="PASS_INVENTED_SUM_BRIDGE_ARITHMETIC_ONLY", checks=checks,
                          elapsed_wall_s=time.perf_counter()-wall, process_cpu_s=time.process_time()-cpu,
                          peak_rss_bytes=rss if sys.platform == "darwin" else rss*1024,
                          native_model_execution=False, model_quality_measured=False,
                          scientific_input_reads=0, network_calls=0), sort_keys=True))


if __name__ == "__main__":
    main()
