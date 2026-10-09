"""Original input-slice and paired-outcome audit. SPDX-License-Identifier: MIT.

Only scalar aggregates are returned; no explicit unit records, IDs or paths.
Small cohorts or rare strata can reveal individual outcomes through aggregates;
release still requires privacy review. A bootstrap interval describes the supplied
cohort, not a new validation sample.
"""
from __future__ import annotations

import math
import numpy as np


def _vector(value, name, *, boolean=False):
    array = np.asarray(value)
    if array.ndim != 1 or not len(array):
        raise ValueError(name + ': nonempty one-dimensional input required')
    if boolean:
        if array.dtype.kind != 'b':
            raise ValueError(name + ': actual boolean values required')
    else:
        if array.dtype.kind not in 'iuf' or not np.isfinite(array).all():
            raise ValueError(name + ': finite real numeric values required')
        with np.errstate(over="ignore", invalid="ignore"):
            array = array.astype(np.float64, copy=False)
        if not np.isfinite(array).all():
            raise ValueError(name + ": values must remain finite as float64")
    return array


def input_slices(gate_open, confidence, analog_similarity, top1_coconut_only):
    """Fixed rules: S1 <=confidence tercile & analog median; S2 NP flag;
    S3 <=confidence20% & analog tercile. Quantiles use gate-open inputs only.

    Outcomes are deliberately absent from this API. Masks remain private caller
    state; exporting them would disclose per-unit membership. These rules do not
    certify independence or transport to another domain.
    """
    gate = _vector(gate_open, 'gate_open', boolean=True)
    prob = _vector(confidence, 'confidence')
    analog = _vector(analog_similarity, 'analog_similarity')
    coconut = _vector(top1_coconut_only, 'top1_coconut_only', boolean=True)
    if not (len(gate) == len(prob) == len(analog) == len(coconut)):
        raise ValueError('Input vectors must describe the same ordered units')
    if not ((prob >= 0).all() and (prob <= 1).all()) or not gate.any():
        raise ValueError('Confidence must be in [0,1]; gate-open coverage required')
    q = dict(confidence_tercile=float(np.quantile(prob[gate], 1 / 3, method='linear')),
             confidence_q20=float(np.quantile(prob[gate], .2, method='linear')),
             analog_median=float(np.quantile(analog[gate], .5, method='linear')),
             analog_tercile=float(np.quantile(analog[gate], 1 / 3, method='linear')))
    masks = {'S1_primary': gate & (prob <= q['confidence_tercile']) & (analog <= q['analog_median']),
             'S2_np_proxy': gate & coconut,
             'S3_tight': gate & (prob <= q['confidence_q20']) & (analog <= q['analog_tercile'])}
    return masks, q


def exact_sign_p(wins, losses):
    """Two-sided binomial sign-test p for equiprobable nonzero directions.

    This tests the direction balance, a different null from mean paired gain.
    It does not replace a preregistered mean-effect decision rule.
    """
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in (wins, losses)):
        raise ValueError('Nonnegative integer win/loss counts required')
    n = wins + losses
    if n > 10000:
        raise ValueError('This exact audit is bounded to 10000 non-tied units')
    if not n:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / (1 << n))


def paired_summary(reference, candidate, *, bootstrap=5000, seed=20261012, confidence=.9):
    """Paired percentile bootstrap; fixed ordered-unit pairing is caller's duty.

    Outcomes must be finite in [0,1]. Chunks retain the deterministic NumPy RNG
    draw order while limiting temporary memory. No refitting, selection or tuning
    occurs. Distribution diagnostics explain a mean gain with tied win counts.
    """
    a, b = _vector(reference, 'reference'), _vector(candidate, 'candidate')
    if len(a) != len(b) or len(a) > 10000:
        raise ValueError('Equal paired lengths, at most 10000 units, required')
    if any((x < 0).any() or (x > 1).any() for x in (a, b)):
        raise ValueError('Bounded [0,1] outcomes required')
    if not isinstance(bootstrap, int) or isinstance(bootstrap, bool) or not 100 <= bootstrap <= 100000:
        raise ValueError('Bootstrap count must be an integer in [100,100000]')
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError('Nonnegative integer seed required')
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 < confidence < 1:
        raise ValueError('Confidence must lie strictly between zero and one')
    d, n = b - a, len(a)
    rng = np.random.default_rng(seed)
    means = np.empty(bootstrap)
    for start in range(0, bootstrap, 256):
        size = min(256, bootstrap - start)
        means[start:start + size] = d[rng.integers(0, n, size=(size, n))].mean(axis=1)
    tail = (1 - confidence) / 2
    interval = [float(np.quantile(means, tail, method='linear')),
                float(np.quantile(means, 1 - tail, method='linear'))]
    positive, negative = d[d > 0], -d[d < 0]
    gain_mass, loss_mass = float(positive.sum()), float(negative.sum())
    summary = dict(n=n, reference_mean=float(a.mean()), candidate_mean=float(b.mean()),
                   mean_delta=float(d.mean()), percentile_interval=interval,
                   confidence=float(confidence), bootstrap=bootstrap, seed=seed,
                   wins=len(positive), losses=len(negative), ties=int((d == 0).sum()),
                   gain_mass=gain_mass, loss_mass=loss_mass,
                   mean_gain_when_improved=float(positive.mean()) if len(positive) else 0.0,
                   mean_loss_when_worse=float(negative.mean()) if len(negative) else 0.0,
                   exact_direction_sign_p=exact_sign_p(len(positive), len(negative)),
                   largest_three_gain_fraction=float(np.sort(positive)[-3:].sum() / gain_mass) if gain_mass else 0.0,
                   leave_one_unit_mean_range=[float((d.sum() - d.max()) / (n - 1)),
                                              float((d.sum() - d.min()) / (n - 1))] if n > 1 else None,
                   outcome_equals_one_reference=int((a == 1).sum()),
                   outcome_equals_one_candidate=int((b == 1).sum()),
                   pairing_independently_verified=False, independent_holdout_certified=False,
                   domain_transport_certified=False, promotion_authorized=False,
                   explicit_unit_records_exported=False, aggregate_privacy_certified=False)
    return summary
