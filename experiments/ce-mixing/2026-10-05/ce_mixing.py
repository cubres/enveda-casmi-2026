"""Original, NumPy-only collision-energy mixing experiment.

Mass representation/final processing follows Ahmed Berat Ozer's GLACIER V1
gl_runner.py::post, SHA256 5c4f74313ac54263d05d987c39d012d81ec57c5f35e1095ecd49a5bcb6440fca.
The equal-energy mixture is an explicit experimental hypothesis. No acquisition
weights, chemical candidates, ranking, or missing observations are inferred.
"""
from __future__ import annotations
import math
import numbers
import numpy as np

ENERGIES = (20.0, 40.0, 60.0)
TOPK = 100


class Refusal(ValueError):
    """An input fails this fixed pilot's contract."""


def ce_bucket(ce):
    """Released 5-eV round-to-even convention, minimum 5 eV."""
    if isinstance(ce, bool) or not isinstance(ce, numbers.Real):
        raise Refusal("CE must be a finite numeric scalar in eV")
    value = float(ce)
    if not math.isfinite(value):
        raise Refusal("CE must be finite")
    return max(5.0, float(np.round(value / 5.0) * 5.0))


def validate_energies(values):
    """Only the frozen [20,40,60] acquisition or its [40] control."""
    if not isinstance(values, (list, tuple)) or not values:
        raise Refusal("CE protocol must be a nonempty list/tuple")
    if any(isinstance(x, bool) or not isinstance(x, numbers.Real) for x in values):
        raise Refusal("CE protocol has a nonnumeric value")
    vals = tuple(float(x) for x in values)
    if not all(math.isfinite(x) for x in vals):
        raise Refusal("CE protocol has a nonfinite value")
    if len(set(vals)) != len(vals):
        raise Refusal("CE protocol must not duplicate an acquisition")
    ordered = tuple(sorted(vals))
    if ordered not in (ENERGIES, (40.0,)):
        raise Refusal("outside frozen pilot CE protocol")
    return ordered


def raw_array(raw):
    """Validate a real, finite, nonempty sparse raw forward spectrum."""
    if not isinstance(raw, np.ndarray) or raw.dtype not in (np.dtype('float32'), np.dtype('float64')):
        raise Refusal("raw spectrum must be a float32/float64 NumPy array")
    if raw.ndim != 2 or raw.shape[1] != 2 or raw.shape[0] == 0:
        raise Refusal("raw spectrum must have nonempty shape (N,2)")
    if not np.isfinite(raw).all():
        raise Refusal("raw spectrum contains nonfinite values")
    valid = raw[(raw[:, 0] > 0) & (raw[:, 1] > 0)]
    if valid.shape[0] == 0:
        raise Refusal("no positive forward peaks")
    return valid


def mass_basis(raw):
    """Released 4-decimal sparse mass basis, duplicate intensity MAX.

    Keep every positive raw peak here; apply the shared top-100 budget only at
    the final stage. This deliberately avoids Predictor._run's early top-100.
    """
    valid = raw_array(raw)
    key = np.round(valid[:, 0].astype(np.float64), 4)
    if not np.isfinite(key).all() or np.any(key <= 0) or np.any(key > np.finfo(np.float32).max):
        raise Refusal("mass is invalid on released float32/4-decimal basis")
    mz, inverse = np.unique(key, return_inverse=True)
    intensity = np.zeros(len(mz), dtype=np.float64)
    np.maximum.at(intensity, inverse, valid[:, 1].astype(np.float64))
    return mz, intensity


def finalize(raw):
    """Same final top-100, ascending mass order, max-normalized float32."""
    mz, intensity = mass_basis(raw)
    if len(mz) > TOPK:
        keep = np.argsort(-intensity, kind='stable')[:TOPK]
        mz, intensity = mz[keep], intensity[keep]
    order = np.argsort(mz)
    mz, intensity = mz[order], intensity[order]
    return np.column_stack((mz.astype(np.float32), (intensity / intensity.max()).astype(np.float32)))


def mixture(raw_by_ce, energies):
    """Equal-weight, individually base-peak-normalized raw CE mixture.

    raw_by_ce values are the actual raw model outputs; no query peaks enter.
    The equal scale cancels during final max normalization, but is retained
    explicitly. Sorting the frozen energy list makes order immaterial.
    """
    values = validate_energies(energies)
    if not isinstance(raw_by_ce, dict) or set(raw_by_ce) != set(values):
        raise Refusal("model outputs must match every requested CE exactly")
    if values == (40.0,):
        return finalize(raw_by_ce[40.0])
    masses, intensities = [], []
    for value in values:
        mz, intensity = mass_basis(raw_by_ce[value])
        masses.append(mz)
        intensities.append(intensity / intensity.max() / len(values))
    joined = np.concatenate(masses)
    mz, inverse = np.unique(joined, return_inverse=True)
    intensity = np.bincount(inverse, weights=np.concatenate(intensities))
    return finalize(np.column_stack((mz, intensity)))


def paired_outputs(raw_by_ce, energies):
    """Reuse the exact raw mean-energy prediction as the baseline."""
    if not isinstance(raw_by_ce, dict):
        raise Refusal("model outputs must be a dict")
    values = validate_energies(energies)
    mean_bucket = ce_bucket(float(np.mean(values)))
    if mean_bucket not in raw_by_ce:
        raise Refusal("mean-energy baseline output is missing")
    return finalize(raw_by_ce[mean_bucket]), mixture(raw_by_ce, values)


def entropy_similarity(a, b):
    """Unweighted entropy similarity on already normalized finite spectra.

    This CPU component is a test oracle, not the native measurement scorer.
    Native evaluation uses the exact pinned released prep_query/entropy_sim
    after the same query/prediction processing for both arms.
    """
    aa, bb = raw_array(a), raw_array(b)
    ma, ia = mass_basis(aa); mb, ib = mass_basis(bb)
    ia, ib = ia / ia.sum(), ib / ib.sum()
    all_mz = np.union1d(ma, mb)
    pa, pb = np.zeros(len(all_mz)), np.zeros(len(all_mz))
    pa[np.searchsorted(all_mz, ma)] = ia
    pb[np.searchsorted(all_mz, mb)] = ib
    def entropy(p):
        positive = p[p > 0]
        return float(-np.sum(positive * np.log(positive)))
    return 1.0 - (2 * entropy((pa + pb) / 2) - entropy(pa) - entropy(pb)) / math.log(4)
