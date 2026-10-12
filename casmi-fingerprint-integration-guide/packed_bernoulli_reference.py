"""Original bounded, model-free score reference. No import-time I/O.

This is a qualification reference, not a fast array backend or admitted model
adapter. The supplied schema binding must already be established from exact
generator and checkpoint source/tensors. Width alone never establishes it.
All fixtures used with this module must be invented; no chemistry is bundled.
"""

from dataclasses import dataclass
import math


MAX_CANDIDATES = 64
MAX_SPECTRA = 8
OUTPUT_BITS = 2216
ROW_BYTES = 277
ABS_LOGIT_LIMIT = 1_000_000.0


class ContractError(ValueError):
    """An explicit contract violation; never a fallback scoring route."""


@dataclass(frozen=True)
class Contract:
    maccs_layout: str
    bitorder: str
    schema_binding_sha256: str

    def __post_init__(self):
        if self.maccs_layout not in ("keys0_166_zero_key", "keys1_166"):
            raise ContractError("EXPLICIT_MACCS_LAYOUT_REQUIRED")
        if self.bitorder not in ("big", "little"):
            raise ContractError("EXPLICIT_BIT_ORDER_REQUIRED")
        h = self.schema_binding_sha256
        if not isinstance(h, str) or len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
            raise ContractError("EXTERNALLY_VERIFIED_SCHEMA_BINDING_REQUIRED")

    @property
    def logical_bits(self):
        return 2215 if self.maccs_layout == "keys0_166_zero_key" else 2214

    @property
    def excluded(self):
        # In the 167-coordinate layout key0 must have been established as a
        # constant zero by source/fixture qualification; it is checked below.
        return (2048, 2215) if self.maccs_layout == "keys0_166_zero_key" else (2214, 2215)

    @property
    def valid_indices(self):
        return tuple(i for i in range(OUTPUT_BITS) if i not in self.excluded)


def _bit(row, i, order):
    shift = 7 - i % 8 if order == "big" else i % 8
    return (row[i // 8] >> shift) & 1


def _binding(contract, supplied):
    if supplied != contract.schema_binding_sha256:
        raise ContractError("SCHEMA_BINDING_MISMATCH")


def _rows(rows, contract, binding):
    _binding(contract, binding)
    if not isinstance(rows, (tuple, list)) or not 1 <= len(rows) <= MAX_CANDIDATES:
        raise ContractError("CANDIDATE_COUNT_OUTSIDE_BOUND")
    for row in rows:
        if not isinstance(row, bytes) or len(row) != ROW_BYTES:
            raise ContractError("PACKED_BYTES_WIDTH_REQUIRED")
        if any(_bit(row, i, contract.bitorder) for i in contract.excluded):
            raise ContractError("NONZERO_PADDING_OR_DECLARED_ZERO_KEY")
    return tuple(rows)


def _inputs(logits, weights, contract, binding):
    _binding(contract, binding)
    if not isinstance(logits, (tuple, list)) or not 1 <= len(logits) <= MAX_SPECTRA:
        raise ContractError("SPECTRUM_COUNT_OUTSIDE_BOUND")
    if not isinstance(weights, (tuple, list)) or len(weights) != len(logits):
        raise ContractError("WEIGHT_COUNT_MISMATCH")
    z = []
    for row in logits:
        if not isinstance(row, (tuple, list)) or len(row) != OUTPUT_BITS:
            raise ContractError("MODEL_OUTPUT_COORDINATES_REQUIRED")
        if any(type(x) not in (int, float) for x in row):
            raise ContractError("NUMERIC_LOGITS_REQUIRED")
        try:
            r = tuple(float(x) for x in row)
        except OverflowError:
            raise ContractError("LOGITS_OUTSIDE_FINITE_REFERENCE_BOUND") from None
        if any(not math.isfinite(x) or abs(x) > ABS_LOGIT_LIMIT for x in r):
            raise ContractError("LOGITS_OUTSIDE_FINITE_REFERENCE_BOUND")
        z.append(r)
    if any(type(x) not in (int, float) for x in weights):
        raise ContractError("NUMERIC_WEIGHTS_REQUIRED")
    try:
        w = tuple(float(x) for x in weights)
    except OverflowError:
        raise ContractError("FINITE_NONNEGATIVE_POSITIVE_TOTAL_WEIGHTS_REQUIRED") from None
    if any(not math.isfinite(x) or x < 0 for x in w) or max(w) <= 0:
        raise ContractError("FINITE_NONNEGATIVE_POSITIVE_TOTAL_WEIGHTS_REQUIRED")
    # Scaling by the maximum prevents overflow when summing finite weights.
    scaled = tuple(x / max(w) for x in w)
    total = math.fsum(scaled)
    normalized = tuple(x / total for x in scaled)
    return tuple(z), normalized


def _softplus(x):
    return max(x, 0.0) + math.log1p(math.exp(-abs(x)))


@dataclass(frozen=True)
class Scores:
    rank_only: tuple
    full_loglik: tuple
    candidate_independent_constant: float
    ranking_indices: tuple
    valid_bits: int


def packed_scores(rows, logits, weights, contract, *, candidate_schema_sha256, logit_schema_sha256):
    """Weighted mean Bernoulli loglik without a dense candidate matrix.

    For fixed, candidate-independent valid bits V:
      L(c) = c dot mean_logits - sum_s normalized_w_s sum_b_in_V softplus(z_sb).
    Dropping the latter term preserves rankings in exact arithmetic only for
    the same query, masks, weights and coordinate contract. This is distinct
    from averaging sigmoid probabilities and then taking their logit.
    """
    rows = _rows(rows, contract, candidate_schema_sha256)
    z, w = _inputs(logits, weights, contract, logit_schema_sha256)
    valid = contract.valid_indices
    mean = tuple(math.fsum(w_s * z_s[i] for w_s, z_s in zip(w, z)) for i in range(OUTPUT_BITS))
    constant = math.fsum(w_s * math.fsum(_softplus(z_s[i]) for i in valid)
                         for w_s, z_s in zip(w, z))
    rank = tuple(math.fsum(mean[i] for i in valid if _bit(row, i, contract.bitorder)) for row in rows)
    full = tuple(x - constant for x in rank)
    ranking = tuple(sorted(range(len(rank)), key=lambda i: (-rank[i], i)))
    return Scores(rank, full, constant, ranking, len(valid))


def dense_reference_scores(rows, logits, weights, contract, *, candidate_schema_sha256, logit_schema_sha256):
    """Independent stable direct Bernoulli formula for invented proof fixtures.

    Uses log(sigmoid(z))=-softplus(-z), avoiding probability clipping. A
    finite-precision implementation with clipped probabilities is a separate
    scorer and requires separate equivalence qualification.
    """
    rows = _rows(rows, contract, candidate_schema_sha256)
    z, w = _inputs(logits, weights, contract, logit_schema_sha256)
    valid = contract.valid_indices
    dense = tuple(tuple(_bit(row, i, contract.bitorder) for i in valid) for row in rows)
    return tuple(math.fsum(w_s * math.fsum(-_softplus(-z_s[i]) if bit else -_softplus(z_s[i])
                                         for i, bit in zip(valid, bits))
                           for w_s, z_s in zip(w, z)) for bits in dense)
