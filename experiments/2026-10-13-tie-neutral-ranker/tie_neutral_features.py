# SPDX-License-Identifier: MIT
"""Original numeric tie-neutral CASMI feature transformation; no fitting or I/O.

This changes only within-query rank features and their dependent agreement
features. It leaves the measured library, analog, fingerprint and fragment
scores unchanged. A query contains one simulation's complete candidate roster.
No truth label, structure identifier, source library or outcome enters this
function. The caller must preserve exact row/candidate joins and native identity.
"""
from __future__ import annotations

import numpy as np

FEATURES = (
    'lib_sim', 'lib_sim_rank', 'lib_sim_query_max', 'lib_sim_gap', 'lib_hit',
    'analog_prop', 'analog_prop_rank', 'analog_prop_query_max', 'analog_prop_gap',
    'analog_tanimoto_x_sim_max', 'analog_best_tanimoto', 'analog_top1_tanimoto',
    'analog_mean_tanimoto', 'analog_top1_sim', 'log_n_candidates', 'fp_model_z',
    'fp_model_rank', 'fp_model_gap', 'fp_model_norm_z', 'fp_model_norm_rank',
    'fp_model_is_max', 'frag_score', 'frag_rank', 'frag_gap', 'frag_z',
    'lib_x_model_disagree', 'analog_x_model_disagree', 'lib_top_model_agree',
    'analog_top_model_agree', 'lib_max_x_agree', 'lib_model_corr',
)
RANK_PAIRS = ((1, 0), (6, 5), (16, 17), (22, 21))
CHANGED_COLUMNS = (1, 6, 16, 22, 25, 26, 27, 28, 29, 30)


def descending_midrank(values):
    """0 is best, 1 worst; exact ties share their mean ordinal / (n - 1).

    Equality concerns the supplied float values, with no epsilon, quantization,
    threshold tuning or candidate cap. Signed zero is an exact tie. The ranks
    are invariant to a permutation of candidate order, after unpermuting rows.
    A singleton's normalized rank is zero. Empty vectors are explicitly allowed
    for diagnostics, and never create a fabricated candidate.
    """
    a = np.asarray(values)
    if a.ndim != 1 or a.dtype.kind not in 'fiu' or not np.isfinite(a).all():
        raise ValueError('finite one-dimensional real scores required')
    n = len(a)
    if n < 2:
        return np.zeros(n, dtype=np.float64)
    order = np.argsort(-a.astype(np.float64), kind='stable')
    sorted_values = a[order]
    starts = np.r_[0, np.flatnonzero(sorted_values[1:] != sorted_values[:-1]) + 1]
    ends = np.r_[starts[1:], n]
    out = np.empty(n, dtype=np.float64)
    for start, end in zip(starts, ends):
        out[order[start:end]] = (float(start) + float(end) - 1.0) / (2.0 * (n - 1))
    return out


def transform_query_features(features):
    """Return a new float32 matrix. Every input byte remains untouched.

    The retained raw-model gap is the explicitly registered FP score source.
    Length-normalized ranks remain unchanged: its pre-standardized scores were
    not retained, and a zero z-score can conceal a small nonzero variance.
    Missing FP/fragment channels preserve the producer's exact zero sentinels.
    This is a retained-feature treatment, not modern descriptor parity or a
    claim of reconstructing missing native logits.
    """
    x = np.asarray(features)
    if x.ndim != 2 or x.shape[1] != len(FEATURES) or x.dtype != np.float32:
        raise ValueError('exact float32 [candidate,31] matrix required')
    if not np.isfinite(x).all():
        raise ValueError('nonfinite feature')
    y = x.copy()
    if len(y) == 0:
        return y
    model_present = bool(np.any(x[:, 20] == 1))
    fragment_present = not bool(np.all(x[:, 21:25] == 0))
    for rank_column, score_column in RANK_PAIRS:
        if rank_column == 16 and not model_present:
            continue
        if rank_column == 22 and not fragment_present:
            continue
        y[:, rank_column] = descending_midrank(x[:, score_column])
    if model_present:
        old_rank = x[:, 16].astype(np.float64)
        new_rank = y[:, 16].astype(np.float64)
        lib = x[:, 0].astype(np.float64)
        analog = x[:, 5].astype(np.float64)
        difference = old_rank - new_rank
        # Add a correction to the retained value, keeping unaffected bytes exact.
        y[:, 25] = x[:, 25].astype(np.float64) + lib * difference
        y[:, 26] = x[:, 26].astype(np.float64) + analog * difference
        if lib.max() > 0:
            top = lib == lib.max()
            if top.sum() > 1 or np.any(difference[top] != 0):
                y[:, 27] = 1.0 - new_rank[top].mean()
                shift = float(y[0, 27]) - float(x[0, 27])
                y[:, 29] = x[:, 29].astype(np.float64) + lib.max() * shift
        if analog.max() > 0:
            top = analog == analog.max()
            if top.sum() > 1 or np.any(difference[top] != 0):
                y[:, 28] = 1.0 - new_rank[top].mean()
        if np.any(difference != 0):
            centered_lib = lib - lib.mean()
            centered_model = -new_rank + new_rank.mean()
            denominator = float(np.linalg.norm(centered_lib) * np.linalg.norm(centered_model))
            correlation = float(centered_lib @ centered_model / denominator) if denominator > 0 else 0.0
            y[:, 30] = correlation
    if not np.isfinite(y).all():
        raise ValueError('transformed nonfinite feature')
    return y


def group_query_simulation(query_ids, simulation_ids):
    """Complete group keys. Both simulations must share a future fit/eval fold."""
    q, m = np.asarray(query_ids), np.asarray(simulation_ids)
    if q.ndim != 1 or m.shape != q.shape or q.dtype.kind not in 'iu' or m.dtype.kind not in 'iu':
        raise ValueError('joined integer query/simulation vectors required')
    if np.any(q < 0) or not np.isin(m, [0, 1]).all():
        raise ValueError('nonnegative query, simulation0/1 required')
    return q.astype(np.int64) * 2 + m.astype(np.int64)
