"""Original source-only bridge to the visible V2 sum-over-spectra contract.

No publisher implementation is included. Exact producer/checkpoint/pipeline
byte bindings remain external prerequisites. No model is loaded or called.
"""

import math

from packed_bernoulli_reference import ContractError, MAX_SPECTRA, packed_scores


def sum_bernoulli_scores(rows, logits, contract, *, candidate_schema_sha256, logit_schema_sha256):
    """Restore sum scaling and constant-zero-coordinate terms after masking.

    The visible V2 recipe scores all 2216 outputs, including constant-zero
    dummy/padding bits, then sums spectra. If all candidate rows have zeros at
    these excluded coordinates, their missing likelihood is candidate-
    independent: minus sum softplus(z) on those coordinates.

    Full-score equality is algebraic, subject to floating-point tolerance.
    Neither this bridge nor matching width establishes checkpoint semantics.
    """
    if contract.maccs_layout != "keys0_166_zero_key" or contract.bitorder != "big":
        raise ContractError("VISIBLE_V2_BIG_167_CONTRACT_REQUIRED")
    if not isinstance(logits, (tuple, list)) or not 1 <= len(logits) <= MAX_SPECTRA:
        raise ContractError("SPECTRUM_COUNT_OUTSIDE_BOUND")
    # packed_scores performs all schema/count/finite-value/zero-tail checks.
    result = packed_scores(rows, logits, (1.0,) * len(logits), contract,
                           candidate_schema_sha256=candidate_schema_sha256,
                           logit_schema_sha256=logit_schema_sha256)
    omitted = math.fsum(max(float(row[i]), 0.0) + math.log1p(math.exp(-abs(float(row[i]))))
                        for row in logits for i in contract.excluded)
    return tuple(len(logits) * score - omitted for score in result.full_loglik)
