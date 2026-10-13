# SPDX-License-Identifier: MIT
"""Reusable original CASMI weighting and tie-aware metric utilities.

These functions require only NumPy; they perform no fitting, filesystem I/O or
network operation. Use your own explicit train/evaluation identity splits.
They do not qualify a native competition score or guarantee an improvement.
"""
from __future__ import annotations
import numpy as np

def query_balanced_weights(query_ids, simulation_ids):
    """Equal group mass, then one scalar preserving baseline total weight.

    Counts come from this fit's actual rows. No held labels or feature values
    enter the weighting rule. It intentionally changes weighted positive prior
    and relative leaf regularization; this is not a new class-balancing arm.
    """
    q, m = np.asarray(query_ids), np.asarray(simulation_ids)
    if q.ndim != 1 or q.shape != m.shape or not len(q):
        raise ValueError('nonempty joined training vectors required')
    if q.dtype.kind not in 'iu' or m.dtype.kind not in 'iu' or np.any(q < 0) or not np.isin(m, [0, 1]).all():
        raise ValueError('nonnegative queries and simulation0/1 required')
    group = q.astype(np.int64) * 2 + m.astype(np.int64)
    unique, inverse, counts = np.unique(group, return_inverse=True, return_counts=True)
    if not np.array_equal(unique[::2] + 1, unique[1::2]) or not np.all(unique[::2] % 2 == 0):
        raise ValueError('both simulations of every training query required')
    if not np.array_equal(counts[::2], counts[1::2]):
        raise ValueError('paired simulations must retain identical pool sizes')
    baseline = np.where(m == 0, 0.30, 0.70).astype(np.float64)
    treatment = baseline / counts[inverse]
    treatment *= baseline.sum(dtype=np.float64) / treatment.sum(dtype=np.float64)
    if not np.isfinite(treatment).all() or not np.all(treatment > 0):
        raise ValueError('invalid treatment weights')
    if not np.isclose(treatment.sum(), baseline.sum(), rtol=1e-13, atol=1e-10):
        raise ValueError('global weighted loss scale changed')
    return baseline, treatment, group

def expected_rank_metrics(scores, labels):
    """Expected RR@25/top1/top25 under uniform order of exact score ties.

    Ties extending past rank25 include zero contributions beyond rank25. The
    positive position is never selected by source order or an identity hash.
    """
    score, y = np.asarray(scores), np.asarray(labels)
    if score.ndim != 1 or y.shape != score.shape or not np.isfinite(score).all():
        raise ValueError('finite complete candidate group required')
    if not np.isin(y, [0, 1]).all() or int(y.sum()) != 1:
        raise ValueError('exactly one positive required')
    truth_score = score[np.flatnonzero(y)[0]]
    above, tied = int((score > truth_score).sum()), int((score == truth_score).sum())
    assert tied >= 1
    positions = np.arange(above + 1, min(above + tied, 25) + 1, dtype=np.float64)
    reciprocal = float((1.0 / positions).sum() / tied)
    top1 = 1.0 / tied if above == 0 else 0.0
    top25 = float(max(0, min(tied, 25 - above)) / tied)
    return reciprocal, top1, top25, tied
