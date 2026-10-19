"""Reference-only directed mass windows and exact packed-bit counts.

SPDX-License-Identifier: Apache-2.0
No chemistry, spectra, models, labels, network or file mutations.
"""
import math
import numpy as np

BITS = 10395
BYTES = 1300
COUNT = np.asarray([i.bit_count() for i in range(256)], dtype=np.uint8)


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def packed_counts(fingerprints):
    require(fingerprints.dtype == np.uint8 and fingerprints.ndim == 2 and fingerprints.shape[1] == BYTES,
            "packed uint8 matrix with 1300 bytes per row required")
    require(not np.any(fingerprints[:, -1] & np.uint8(0x1F)), "nonzero padding bits")
    return COUNT[fingerprints].sum(axis=1, dtype=np.int32)


def closed_window(masses, order, query_mass, ppm):
    """Closed [q-q*ppm/1e6, q+q*ppm/1e6]; denominator is query mass."""
    q, tolerance = float(query_mass), float(ppm)
    require(math.isfinite(q) and q > 0 and math.isfinite(tolerance) and tolerance > 0,
            "positive finite reference mass and ppm required")
    delta = q * tolerance * 1e-6
    sorted_masses = masses[order]
    lo = int(np.searchsorted(sorted_masses, q - delta, side="left"))
    hi = int(np.searchsorted(sorted_masses, q + delta, side="right"))
    return order[lo:hi]


def different_group_candidates(masses, order, groups, query_row, ppm):
    require(isinstance(query_row, (int, np.integer)) and not isinstance(query_row, (bool, np.bool_)) and
            0 <= query_row < len(masses), "query row outside reference bank")
    rows = closed_window(masses, order, masses[query_row], ppm)
    return rows[groups[rows] != groups[query_row]]


def query_policy(masses, order, groups, query_row):
    ten = different_group_candidates(masses, order, groups, query_row, 10.0)
    thirty = different_group_candidates(masses, order, groups, query_row, 30.0)
    chosen = ten if len(ten) else thirty
    tolerance = 10 if len(ten) else (30 if len(thirty) else None)
    return {
        "rows_10ppm": int(len(ten)), "groups_10ppm": int(len(set(groups[ten]))),
        "rows_30ppm": int(len(thirty)), "groups_30ppm": int(len(set(groups[thirty]))),
        "selected_ppm": tolerance, "selected_rows": int(len(chosen)),
        "selected_groups": int(len(set(groups[chosen]))),
        "fallback_used": bool(not len(ten) and len(thirty)),
    }, chosen


def similarity_batches(fingerprints, on_bits, query_row, candidates, batch_size=256):
    """Exact integer intersections/unions; float64 ratios, undefined -> NaN.

    Padding must already have been validated. Cosine uses binary vectors, not
    signed/centered model logits. Never unpack a full candidate-by-bit bank.
    """
    require(isinstance(batch_size, int) and not isinstance(batch_size, bool) and 0 < batch_size <= 256,
            "batch size must be within 1..256")
    require(isinstance(query_row, (int, np.integer)) and not isinstance(query_row, (bool, np.bool_)) and
            0 <= query_row < len(fingerprints), "query row outside reference bank")
    candidates = np.asarray(candidates)
    require(candidates.ndim == 1 and candidates.dtype.kind in "iu" and
            np.all((candidates >= 0) & (candidates < len(fingerprints))), "candidate row outside reference bank")
    require(on_bits.shape == (len(fingerprints),) and on_bits.dtype.kind in "iu" and
            np.all((on_bits >= 0) & (on_bits <= BITS)), "on-bit counts invalid")
    q_count = int(on_bits[query_row])
    for offset in range(0, len(candidates), batch_size):
        rows = candidates[offset:offset + batch_size]
        intersection = COUNT[np.bitwise_and(fingerprints[rows], fingerprints[query_row])].sum(axis=1, dtype=np.int32)
        c_count = on_bits[rows].astype(np.int32, copy=False)
        union = q_count + c_count - intersection
        product = q_count * c_count.astype(np.int64)
        jaccard = np.full(len(rows), np.nan, dtype=np.float64)
        cosine = np.full(len(rows), np.nan, dtype=np.float64)
        np.divide(intersection, union, out=jaccard, where=union != 0)
        np.divide(intersection, np.sqrt(product.astype(np.float64)), out=cosine, where=product != 0)
        yield rows, intersection, union, c_count, jaccard, cosine


def exact_integer_pair(left, right):
    """Independent Python-bigint oracle, used only by mechanics canary/tests."""
    a, b = int.from_bytes(left.tobytes(), "big"), int.from_bytes(right.tobytes(), "big")
    intersection, union = (a & b).bit_count(), (a | b).bit_count()
    a_count, b_count = a.bit_count(), b.bit_count()
    return intersection, union, a_count, b_count
