"""Original four-parameter intensity calibration; NumPy math only.

Inputs are already coalesced sparse physical bins, never candidate structures.
This module does not load GLACIER, spectra files, checkpoints, or notebooks.
The future external producer must bind the released model's actual bin settings.
"""
from dataclasses import dataclass
import hashlib
import math
import numpy as np


class Refusal(ValueError):
    pass


@dataclass(frozen=True)
class Spectrum:
    bins: np.ndarray
    intensities: np.ndarray


def checked(s):
    if not isinstance(s, Spectrum):
        raise Refusal("Spectrum required")
    b, v = np.asarray(s.bins), np.asarray(s.intensities)
    if b.ndim != 1 or v.ndim != 1 or len(b) != len(v) or len(b) == 0:
        raise Refusal("nonempty aligned one-dimensional arrays required")
    if b.dtype.kind not in "iu" or v.dtype.kind != "f":
        raise Refusal("integer bin IDs and floating intensities required")
    if not np.all(np.isfinite(v)) or np.any(v < 0) or not np.any(v > 0):
        raise Refusal("finite nonnegative nonzero intensities required")
    if int(np.max(b)) > np.iinfo(np.int64).max:
        raise Refusal("bin ID exceeds signed int64 before conversion")
    if np.any(b <= 0) or len(np.unique(b)) != len(b):
        raise Refusal("positive unique physical bins required; no double counting")
    order = np.argsort(b)
    return b[order].astype(np.int64, copy=True), v[order].astype(np.float64, copy=True)


def rounded_energy(ce):
    if isinstance(ce, (bool, np.bool_)) or not isinstance(ce, (int, float, np.floating)):
        raise Refusal("numeric singleton eV required")
    if not math.isfinite(float(ce)):
        raise Refusal("unknown or merged CE is outside this singleton prototype")
    bucket = float(np.round(float(ce) / 5.0) * 5.0)
    if not 20.0 <= bucket <= 60.0:
        raise Refusal("prototype range is rounded 20 through 60 eV")
    return bucket


def adjusted(s, theta, ce, theoretical_precursor, num_bins, upper_limit):
    b, p = checked(s)
    a = np.asarray(theta)
    if a.shape != (4,) or a.dtype.kind != "f" or not np.all(np.isfinite(a)):
        raise Refusal("four finite floating coefficients required")
    if (isinstance(num_bins, bool) or not isinstance(num_bins, int) or num_bins < 2
            or np.any(b >= num_bins)):
        raise Refusal("explicit valid model bin count required")
    if (isinstance(theoretical_precursor, bool) or not np.isscalar(theoretical_precursor)
            or not np.isfinite(theoretical_precursor) or theoretical_precursor <= 0
            or not np.isscalar(upper_limit) or not np.isfinite(upper_limit) or upper_limit <= 0):
        raise Refusal("positive finite theoretical mass and model upper limit required")
    e = (rounded_energy(ce) - 40.0) / 20.0
    # Use one feature for every member of a physical bin. Positive temperature
    # preserves the released duplicate-MAX winner even when raw peaks duplicate.
    mz = (b.astype(np.float64) - 1.0) * float(upper_limit) / (num_bins - 1.0)
    r = mz / (mz + float(theoretical_precursor)) - 0.5
    zt, zr = a[0] + a[1] * e, a[2] + a[3] * e
    ht, hr = np.tanh(zt), np.tanh(zr)
    temperature, tilt = 1.0 + 0.25 * ht, 0.5 * hr
    positive = p > 0
    logp = np.log(p[positive] / np.max(p))
    logits = temperature * logp + tilt * r[positive]
    logits -= np.max(logits)
    q = np.zeros_like(p)
    q[positive] = np.exp(logits)
    if not np.all(np.isfinite(q)) or np.any(q[positive] <= 0):
        raise Refusal("calibrated support must remain finite and positive")
    jac_log = np.zeros((len(p), 4), dtype=np.float64)
    jac_log[positive, 0] = 0.25 * (1.0 - ht * ht) * logp
    jac_log[positive, 1] = e * jac_log[positive, 0]
    jac_log[positive, 2] = 0.5 * (1.0 - hr * hr) * r[positive]
    jac_log[positive, 3] = e * jac_log[positive, 2]
    return Spectrum(b, q), jac_log


def cosine_loss_gradient(pred, target, jac_log):
    pb, p = checked(pred)
    tb, y = checked(target)
    j = np.asarray(jac_log)
    if j.shape != (len(p), 4) or not np.all(np.isfinite(j)):
        raise Refusal("aligned finite logarithmic Jacobian required")
    # checked() canonicalizes bin order, so carry the same row permutation
    # into the supplied logarithmic Jacobian.
    j = j[np.argsort(np.asarray(pred.bins))]
    # Cosine is invariant to independent positive scaling; prevent finite
    # large target intensities from overflowing the full-spectrum norms.
    p = p / np.max(p)
    y = y / np.max(y)
    # Full norms include unmatched peaks. The sparse dot counts a physical bin
    # at most once; target values never decide which predicted peaks survive.
    aligned = np.zeros_like(p)
    common, pi, ti = np.intersect1d(pb, tb, assume_unique=True, return_indices=True)
    aligned[pi] = y[ti]
    pn, yn = np.linalg.norm(p), np.linalg.norm(y)
    dot = float(p @ aligned)
    similarity = dot / (pn * yn)
    grad_p = -aligned / (pn * yn) + dot * p / (pn ** 3 * yn)
    grad = j.T @ (p * grad_p)
    if not np.isfinite(similarity) or not np.all(np.isfinite(grad)):
        raise Refusal("nonfinite objective")
    return float(1.0 - similarity), grad


@dataclass(frozen=True)
class Example:
    structure: str
    prediction: Spectrum
    target: Spectrum
    ce: float
    theoretical_precursor: float
    num_bins: int
    upper_limit: float


def objective(examples, theta, regularization=1e-3):
    if not examples or not np.isfinite(regularization) or regularization < 0:
        raise Refusal("nonempty fit set and nonnegative penalty required")
    # Equal structure weight prevents many acquisitions of one molecule from
    # dominating fitting. No task IDs or test labels enter the model features.
    groups = {}
    for x in examples:
        if not isinstance(x, Example) or not isinstance(x.structure, str) or not x.structure:
            raise Refusal("explicit structure group required")
        p, j = adjusted(x.prediction, theta, x.ce, x.theoretical_precursor, x.num_bins, x.upper_limit)
        loss, g = cosine_loss_gradient(p, x.target, j)
        groups.setdefault(x.structure, []).append((loss, g))
    loss = np.mean([np.mean([q[0] for q in v]) for v in groups.values()])
    grad = np.mean([np.mean([q[1] for q in v], axis=0) for v in groups.values()], axis=0)
    theta = np.asarray(theta, dtype=np.float64)
    return float(loss + regularization * (theta @ theta)), grad + 2.0 * regularization * theta


def fit(examples, iterations=200, regularization=1e-3):
    if isinstance(iterations, bool) or not isinstance(iterations, int) or not 1 <= iterations <= 200:
        raise Refusal("fixed one through 200 optimizer steps required")
    theta = np.zeros(4, dtype=np.float64)
    history = []
    for _ in range(iterations):
        loss, grad = objective(examples, theta, regularization)
        history.append(loss)
        if np.linalg.norm(grad) < 1e-10:
            break
        rate = 4.0
        for _ in range(20):
            proposal = theta - rate * grad
            candidate, _ = objective(examples, proposal, regularization)
            if candidate <= loss - 1e-4 * rate * float(grad @ grad):
                theta = proposal
                break
            rate *= 0.5
        else:
            break
    return theta.copy(), tuple(history)


def group_partition(structure_scaffold_pairs, salt="enveda-glacier-calibration-v1"):
    """Label-free connected-component split; chemical keys are external pins.

    All exact structures sharing a scaffold enter one component. A structure
    with conflicting scaffold assignments also joins those scaffolds, preventing
    a bad input map from silently splitting it. The producer must supply a
    declared acyclic sentinel, never an empty scaffold or unchecked raw SMILES.
    """
    if not structure_scaffold_pairs:
        raise Refusal("verified structure/scaffold keys required")
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            x = parent[x]
        return x
    def union(x, y):
        x, y = find(x), find(y)
        if x != y:
            parent[max(x, y)] = min(x, y)
    for structure, scaffold in structure_scaffold_pairs:
        if not isinstance(structure, str) or not structure or not isinstance(scaffold, str) or not scaffold:
            raise Refusal("nonempty external verified chemical keys required")
        union("structure:" + structure, "scaffold:" + scaffold)
    components = {}
    for structure, scaffold in structure_scaffold_pairs:
        components.setdefault(find("structure:" + structure), set()).add(structure)
    ordered = sorted(components.values(), key=lambda c: hashlib.sha256(
        (salt + "\0" + "\0".join(sorted(c))).encode("utf-8")).digest())
    if len(ordered) < 4:
        raise Refusal("at least four distinct components needed")
    nfit = len(ordered) // 2
    ndev = max(1, len(ordered) // 4)
    result = {}
    for i, component in enumerate(ordered):
        split = "fit" if i < nfit else "dev" if i < nfit + ndev else "test"
        for structure in component:
            result[structure] = split
    return result
