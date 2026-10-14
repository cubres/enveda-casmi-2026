"""Original, in-memory Morgan/MACCS score comparator; no chemistry or model IO.

This is prospective experiment source, not qualified producer compatibility.
The externally qualified producer must establish the exact 2216-position order.
MIT terms apply only to this original file, not to caller-supplied artifacts.
"""
from __future__ import annotations

import numpy as np

WIDTH = 2216
PACKED_WIDTH = 277
MAX_CANDIDATES = 32768
MACCS_WEIGHT = 0.30


def _population_z(values: np.ndarray) -> np.ndarray:
    if len(values) < 2 or np.all(values == values[0]):
        return np.zeros_like(values)
    centered = values - values.mean(dtype=np.float64)
    largest = np.max(np.abs(centered))
    if largest == 0.0 or not np.isfinite(largest):
        raise ValueError("unresolved nonconstant score scale")
    scaled = centered / largest
    scale = np.sqrt(np.mean(scaled * scaled, dtype=np.float64))
    if scale == 0.0 or not np.isfinite(scale):
        raise ValueError("unresolved normalized score scale")
    return scaled / scale


def score_blocks(
    candidate_packed: np.ndarray,
    aggregated_logits: np.ndarray,
    *,
    bitorder: str,
) -> dict[str, np.ndarray]:
    """Compare raw-block control with one fixed block-balanced treatment.

    candidate_packed is uint8 (n,277); aggregated_logits is the SAME frozen
    finite (2216,) model-logit vector for both arms. The caller, not this
    function, establishes molecular row alignment and view aggregation.

    Positions: Morgan[0:2048], MACCS[2048:2215], final padding[2215].
    MACCS local key 0 at 2048 and padding 2215 must be zero in every candidate.
    They contribute to neither arm, regardless of their model outputs.
    The caller must prove these are true logits; that semantic fact cannot
    be detected from shape or range. Sigmoid probabilities must not be
    dotted against candidate bits and described as log-likelihood.

    Whole-window standardization occurs AFTER chunk scores are assembled.
    Window rows are never truncated to satisfy the cap.
    """
    packed = np.asarray(candidate_packed)
    logits = np.asarray(aggregated_logits)
    if packed.dtype != np.uint8 or packed.ndim != 2 or packed.shape[1] != PACKED_WIDTH:
        raise ValueError("expected uint8 packed rows with 277 columns")
    if len(packed) > MAX_CANDIDATES:
        raise ValueError("candidate cap exceeded; do not truncate")
    if logits.shape != (WIDTH,) or logits.dtype.kind not in "fiu":
        raise ValueError("expected 2216 numeric true logits")
    logits = logits.astype(np.float64, copy=False)
    if not np.all(np.isfinite(logits)) or np.max(np.abs(logits)) > 1e6:
        raise ValueError("nonfinite or out-of-envelope logits")
    if bitorder not in ("big", "little"):
        raise ValueError("explicit qualified bitorder required")

    raw_morgan = np.empty(len(packed), dtype=np.float64)
    raw_maccs = np.empty(len(packed), dtype=np.float64)
    for start in range(0, len(packed), 1024):
        end = min(start + 1024, len(packed))
        bits = np.unpackbits(packed[start:end], axis=1, bitorder=bitorder)
        if np.any(bits[:, 2048]) or np.any(bits[:, 2215]):
            raise ValueError("nonzero MACCS key0 or padding")
        raw_morgan[start:end] = bits[:, :2048].astype(np.float64) @ logits[:2048]
        raw_maccs[start:end] = bits[:, 2049:2215].astype(np.float64) @ logits[2049:2215]

    z_morgan = _population_z(raw_morgan)
    z_maccs = _population_z(raw_maccs)
    raw_combined = raw_morgan + raw_maccs
    return {
        "raw_morgan": raw_morgan,
        "raw_maccs": raw_maccs,
        "raw_combined": raw_combined,
        "control": _population_z(raw_combined),
        "treatment": z_morgan + MACCS_WEIGHT * z_maccs,
    }


def deterministic_order(scores: np.ndarray, native_identity_tokens: list[str]) -> np.ndarray:
    """Descending scores, then caller-qualified unique native identity token.

    Tokens may be invented for mechanics fixtures. This function does not
    prove that a real token is the competition's normalized identity.
    """
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError("finite 1D scores required")
    if len(values) != len(native_identity_tokens):
        raise ValueError("identity row count mismatch")
    if any(not isinstance(x, str) or not x for x in native_identity_tokens):
        raise ValueError("nonempty string tokens required")
    if len(set(native_identity_tokens)) != len(native_identity_tokens):
        raise ValueError("deduplicate by the native metric BEFORE both arms")
    return np.lexsort((np.asarray(native_identity_tokens, dtype=np.str_), -values))
