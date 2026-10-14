"""Original NumPy-only candidate-window mechanics. No molecular definitions.

Source qualification and declared contracts cannot certify producer honesty,
model compatibility, molecular identity, data rights, or competition eligibility.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import numpy as np

from block_balance_r2 import score_blocks

MAX_BANK_ROWS = 1_000_000
MAX_WINDOW_ROWS = 32_768
POSITION_COUNT = 2_216
PACKED_COLUMNS = 277


@dataclass(frozen=True)
class PackingContract:
    producer_status: str = "UNKNOWN"
    producer_id: str = "UNKNOWN"
    bitorder: str | None = None
    layout: str = "morgan2048-maccs167-pad1"

    def require_declared(self) -> None:
        if self.producer_status not in ("SYNTHETIC_ONLY", "EXTERNALLY_QUALIFIED"):
            raise ValueError("unknown producer: establish a qualified packing contract")
        if self.producer_id in ("", "UNKNOWN") or not isinstance(self.producer_id, str):
            raise ValueError("explicit producer identity required")
        if self.bitorder not in ("big", "little"):
            raise ValueError("unknown packing: never infer bit order")
        if self.layout != "morgan2048-maccs167-pad1":
            raise ValueError("unsupported layout; widths alone do not establish semantics")


def _positive_scalar(value: float, name: str, maximum: float | None = None) -> float:
    if isinstance(value, (bool, np.bool_)) or not np.isscalar(value):
        raise ValueError(f"{name} must be a positive finite scalar")
    try:
        out = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{name} must be a positive finite scalar") from None
    if not math.isfinite(out) or out <= 0.0 or (maximum is not None and out > maximum):
        raise ValueError(f"{name} is outside the declared envelope")
    return out


def validate_masses(masses: np.ndarray) -> None:
    if not isinstance(masses, np.ndarray) or masses.dtype != np.float64 or masses.ndim != 1:
        raise ValueError("mass axis must be a float64 NumPy vector")
    if len(masses) > MAX_BANK_ROWS:
        raise ValueError("mass bank cap exceeded")
    if not np.all(np.isfinite(masses)) or np.any(masses <= 0):
        raise ValueError("mass axis must contain finite positive neutral masses")
    if len(masses) > 1 and np.any(masses[1:] < masses[:-1]):
        raise ValueError("mass axis must already be sorted; preserve its shared row permutation")


def mass_window(masses: np.ndarray, neutral_mass_da: float, ppm: float = 10.0) -> tuple[int, int]:
    """Inclusive query-denominator ppm interval on a sorted neutral-mass axis.

    This validates the complete mass vector on every call. It converts no
    precursor m/z or adduct; the caller must supply a qualified neutral mass.
    Both endpoints and all duplicates at them belong to the returned slice.
    """
    validate_masses(masses)
    query = _positive_scalar(neutral_mass_da, "neutral mass")
    tolerance = _positive_scalar(ppm, "ppm", maximum=1000.0)
    delta = query * (tolerance / 1e6)
    lower, upper = query - delta, query + delta
    if not math.isfinite(lower) or not math.isfinite(upper) or lower <= 0:
        raise ValueError("nonfinite or invalid interval")
    return int(np.searchsorted(masses, lower, side="left")), int(np.searchsorted(masses, upper, side="right"))


def _tokens(tokens: tuple[str, ...] | list[str], row_count: int) -> tuple[str, ...]:
    if not isinstance(row_count, int) or not 0 <= row_count <= MAX_BANK_ROWS:
        raise ValueError("row token cap exceeded")
    if not isinstance(tokens, (tuple, list)) or len(tokens) != row_count:
        raise ValueError("same-row token sequence required")
    if any(not isinstance(token, str) or not token or len(token) > 128 for token in tokens):
        raise ValueError("tokens must be nonempty strings of at most128 characters")
    if len(set(tokens)) != len(tokens):
        raise ValueError("row tokens must be unique; native chemistry deduplication is external")
    return tuple(tokens)


def row_order_digest(tokens: tuple[str, ...] | list[str]) -> str:
    """Length-delimited UTF-8 row-token digest, not proof of chemical identity."""
    checked = _tokens(tokens, len(tokens))
    h = hashlib.sha256(b"packed-window-lab-row-order-v1\0")
    for token in checked:
        encoded = token.encode("utf-8")
        h.update(len(encoded).to_bytes(4, "big"))
        h.update(encoded)
    return h.hexdigest()


def validate_packed(packed: np.ndarray, contract: PackingContract, *, window: bool = False) -> None:
    contract.require_declared()
    if not isinstance(packed, np.ndarray) or packed.dtype != np.uint8 or packed.ndim != 2 or packed.shape[1] != PACKED_COLUMNS:
        raise ValueError("packed rows must be uint8 with exactly277 columns")
    cap = MAX_WINDOW_ROWS if window else MAX_BANK_ROWS
    if len(packed) > cap:
        raise ValueError("row cap exceeded; never truncate a candidate window")
    key0_mask = 0x80 if contract.bitorder == "big" else 0x01
    padding_mask = 0x01 if contract.bitorder == "big" else 0x80
    if np.any(packed[:, 256] & key0_mask) or np.any(packed[:, 276] & padding_mask):
        raise ValueError("nonzero MACCS key0 or final padding position")


def pack_declared_bits(bits: np.ndarray, contract: PackingContract) -> np.ndarray:
    """Pack caller-supplied binary positions; this does not compute chemistry."""
    contract.require_declared()
    if not isinstance(bits, np.ndarray) or bits.dtype != np.uint8 or bits.ndim != 2 or bits.shape[1] != POSITION_COUNT:
        raise ValueError("bits must be uint8 with exactly2216 positions")
    if len(bits) > MAX_WINDOW_ROWS or np.any((bits != 0) & (bits != 1)):
        raise ValueError("invalid binary values or window cap")
    if np.any(bits[:, 2048]) or np.any(bits[:, 2215]):
        raise ValueError("MACCS key0 and padding must be zero")
    return np.packbits(bits, axis=1, bitorder=contract.bitorder)


def unpack_declared_bits(packed: np.ndarray, contract: PackingContract) -> np.ndarray:
    validate_packed(packed, contract, window=True)
    return np.unpackbits(packed, axis=1, bitorder=contract.bitorder)


def aligned_window(
    masses: np.ndarray,
    tokens: tuple[str, ...] | list[str],
    packed: np.ndarray,
    contract: PackingContract,
    neutral_mass_da: float,
    *,
    expected_row_order_sha256: str,
    ppm: float = 10.0,
) -> tuple[tuple[int, int], tuple[str, ...], np.ndarray]:
    """Use the same half-open interval for all aligned candidate arrays.

    A trusted external manifest must bind the token digest AND physical mass,
    metadata and fingerprint hashes to one row order. This helper checks the
    declared token digest and dimensions; it cannot prove those manifest claims.
    Returned packed rows are a view. Keep input arrays unchanged during use.
    """
    lo, hi = mass_window(masses, neutral_mass_da, ppm)
    ids = _tokens(tokens, len(masses))
    validate_packed(packed, contract)
    if len(packed) != len(masses):
        raise ValueError("mass/token/fingerprint row counts disagree")
    if row_order_digest(ids) != expected_row_order_sha256:
        raise ValueError("declared row-order digest mismatch")
    if hi - lo > MAX_WINDOW_ROWS:
        raise ValueError("complete candidate window exceeds cap; HOLD rather than truncate")
    return (lo, hi), ids[lo:hi], packed[lo:hi]


def score_window(packed: np.ndarray, true_logits: np.ndarray, contract: PackingContract, *, mode: str = "likelihood_order") -> np.ndarray:
    """No model inference: consume caller-qualified true aggregated logits.

    likelihood_order returns bits dot true logits on valid positions, equal to
    Bernoulli log likelihood up to a query constant. balanced_prospective uses
    the reviewed original R2 block combination; it has no measured score gain.
    Shapes/ranges do not distinguish probabilities from true logits.
    """
    validate_packed(packed, contract, window=True)
    if mode not in ("likelihood_order", "balanced_prospective"):
        raise ValueError("unknown score mode")
    out = score_blocks(packed, true_logits, bitorder=contract.bitorder)
    return out["raw_combined"] if mode == "likelihood_order" else out["treatment"]


def topk_with_ties(scores: np.ndarray, tokens: tuple[str, ...] | list[str], k: int = 25) -> dict:
    """Stable descending scores with token-order ties and complete tie sizes.

    Tokens must already represent unique native identities for real inference.
    Invented demo tokens are not molecular keys. This does not deduplicate or
    normalize chemistry. A cut tie records its full size and selected members.
    """
    values = np.asarray(scores)
    if values.ndim != 1 or values.dtype != np.float64 or len(values) > MAX_WINDOW_ROWS:
        raise ValueError("bounded float64 score vector required")
    if not np.all(np.isfinite(values)) or isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 25:
        raise ValueError("finite scores and integer k from1 to25 required")
    ids = _tokens(tokens, len(values))
    order = np.lexsort((np.asarray(ids, dtype=np.str_), -values))
    groups = []
    start = 0
    while start < min(k, len(order)):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        groups.append({"start_rank": start + 1, "tie_size": end - start, "selected_indices": order[start:min(end, k)].tolist()})
        start = end
    selected = order[:k]
    return {"indices": selected.tolist(), "tokens": [ids[i] for i in selected], "tie_groups": groups}


def evaluation_only_expected_rr(scores: np.ndarray, truth_index: int | None, k: int = 25) -> float:
    """Invented/demo or independently eligible evaluation only; never inference.

    Expected reciprocal rank under uniform permutations inside exact-score ties.
    An absent truth is zero. The caller must keep truth outside prediction code.
    """
    values = np.asarray(scores)
    if values.ndim != 1 or values.dtype != np.float64 or len(values) > MAX_WINDOW_ROWS or not np.all(np.isfinite(values)):
        raise ValueError("bounded finite float64 scores required")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 25:
        raise ValueError("k must be from1 to25")
    if truth_index is None:
        return 0.0
    if isinstance(truth_index, bool) or not isinstance(truth_index, int) or not 0 <= truth_index < len(values):
        raise ValueError("invalid truth index")
    score = values[truth_index]
    start = 1 + int(np.count_nonzero(values > score))
    size = int(np.count_nonzero(values == score))
    if start > k:
        return 0.0
    return math.fsum(1.0 / rank for rank in range(start, min(start + size - 1, k) + 1)) / size
