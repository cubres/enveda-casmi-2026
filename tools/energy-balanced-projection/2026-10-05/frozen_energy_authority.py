"""Original molecule-balanced multi-energy learning loss on labelled formulas.

This module consumes precomputed *training* logits. It does not load foundation
models, construct a competition candidate bank, or perform identification.
Every row belongs to one labelled molecule and measured collision-energy stratum.
Columns must be distinct audited connectivity/tautomer identities. Formula keys
must come from independently standardized training structures.
"""
from __future__ import annotations

import numpy as np


def _cross_entropy(vector: np.ndarray, positive: int):
    shifted = vector - np.max(vector)
    exponent = np.exp(shifted)
    denominator = exponent.sum()
    probabilities = exponent / denominator
    value = float(np.log(denominator) - shifted[positive])
    derivative = probabilities.copy()
    derivative[positive] -= 1.0
    return value, derivative


def energy_balanced_loss(
    logits, row_targets, row_energies, column_keys, column_formulas, *, eta=0.5
):
    """Return scalar loss and analytic derivative with respect to all logits.

    The learning unit is a molecule, then an energy, then a replicate. Negatives
    are other labelled training molecules with the exact same formula. Each
    molecule receives equal weight, independent of its spectrum count.

    For molecule i, p_i is cross-entropy of energy-averaged logits and q_i is
    energy-average cross-entropy. L_i = eta*p_i + (1-eta)*q_i. The q term guards
    against a strong energy concealing failure at another observed energy.
    Columns from a different formula have exactly zero derivative.
    """
    x = np.asarray(logits, dtype=np.float64)
    targets = np.asarray(row_targets)
    energies = np.asarray(row_energies, dtype=np.float64)
    if x.ndim != 2 or min(x.shape) < 2:
        raise ValueError("at least two spectral rows and molecule columns required")
    n_rows, n_columns = x.shape
    if not np.isfinite(x).all() or np.max(np.abs(x)) > 1e6:
        raise ValueError("finite bounded logits required")
    if targets.shape != (n_rows,) or targets.dtype.kind not in "iu":
        raise ValueError("one integer molecule index per spectral row required")
    if np.any(targets < 0) or np.any(targets >= n_columns):
        raise ValueError("molecule index outside training matrix")
    if energies.shape != (n_rows,) or not np.isfinite(energies).all():
        raise ValueError("observed finite collision energies required")
    if np.any(energies < 0) or np.any(energies > 1000):
        raise ValueError("explicit eV collision energies in [0,1000] required")
    keys, formulas = tuple(column_keys), tuple(column_formulas)
    if len(keys) != n_columns or len(set(keys)) != n_columns:
        raise ValueError("one distinct standardized training identity per column required")
    if len(formulas) != n_columns:
        raise ValueError("one standardized formula per column required")
    if any(not isinstance(k, str) or not k for k in keys + formulas):
        raise ValueError("nonempty explicit identity and formula keys required")
    if not np.isfinite(eta) or not 0 <= eta <= 1:
        raise ValueError("eta must be finite and in [0,1]")
    represented = np.unique(targets)
    if set(map(int, represented)) != set(range(n_columns)):
        raise ValueError("every training molecule needs at least one observed spectrum")

    total = 0.0
    gradient = np.zeros_like(x)
    for molecule in represented:
        molecule = int(molecule)
        columns = np.array([j for j, f in enumerate(formulas) if f == formulas[molecule]])
        if len(columns) < 2:
            raise ValueError("each participating formula needs two distinct training molecules")
        positive = int(np.flatnonzero(columns == molecule)[0])
        rows = np.flatnonzero(targets == molecule)
        levels = np.unique(energies[rows])
        energy_rows = [rows[energies[rows] == e] for e in levels]
        means = np.stack([x[np.ix_(indices, columns)].mean(axis=0) for indices in energy_rows])
        pooled_loss, pooled_gradient = _cross_entropy(means.mean(axis=0), positive)
        individual = [_cross_entropy(vector, positive) for vector in means]
        energy_loss = float(np.mean([v[0] for v in individual]))
        total += eta * pooled_loss + (1.0 - eta) * energy_loss
        for indices, (_, energy_gradient) in zip(energy_rows, individual):
            derivative = eta * pooled_gradient + (1.0 - eta) * energy_gradient
            weight = 1.0 / (len(represented) * len(levels) * len(indices))
            gradient[np.ix_(indices, columns)] += derivative[None, :] * weight
    return total / len(represented), gradient
