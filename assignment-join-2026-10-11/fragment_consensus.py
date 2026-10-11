# SPDX-License-Identifier: MIT
"""Original, data-free candidate-ranking features; no model or chemistry parser.

The caller supplies *ion m/z hypotheses*, not neutral fragment masses, and
centroid spectra with declared acquisition windows. Hypotheses must already
reflect the correct adduct/polarity/charge. This module makes no such inference.
"""
from __future__ import annotations

import json
import math
from statistics import median
import sys

FEATURE_NAMES = (
    "assignment_max", "assignment_median", "assignment_q25",
    "uniform_excess_mean", "uniform_excess_q25", "reuse_gap_max",
    "coverage_mean", "hypothesis_count_log1p", "view_count",
)
MAX_PEAKS = 256
MAX_IONS = 2048
MAX_VIEWS = 16
MAX_TOTAL_CELLS = 8_388_608
MAX_JSON_BYTES = 2_097_152


def _number(value, name, *, positive=False):
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a real number, not a boolean")
    x = float(value)
    if not math.isfinite(x) or (positive and x <= 0):
        raise ValueError(f"{name} must be finite" + (" and positive" if positive else ""))
    return x


def _tolerances(abs_tol, ppm):
    a = _number(abs_tol, "abs_tol", positive=True)
    p = _number(ppm, "ppm")
    if a > 0.1 or not 0 <= p <= 1000:
        raise ValueError("prototype tolerances require abs_tol <= 0.1 and 0 <= ppm <= 1000")
    return a, p * 1e-6


def _ions(values):
    if not isinstance(values, (list, tuple)) or not 1 <= len(values) <= MAX_IONS:
        raise ValueError("supply 1..2048 explicit ion hypotheses; truncation is forbidden")
    return sorted(set(_number(v, "ion", positive=True) for v in values))


def _view(view):
    if not isinstance(view, dict) or set(view) != {"mz", "intensity", "window"}:
        raise ValueError("each spectrum needs exactly mz, intensity, window")
    mz, it, window = view["mz"], view["intensity"], view["window"]
    if not isinstance(mz, (list, tuple)) or not isinstance(it, (list, tuple)):
        raise ValueError("mz and intensity must be explicit vectors")
    if not 1 <= len(mz) <= MAX_PEAKS or len(it) != len(mz):
        raise ValueError("supply 1..256 aligned centroid peaks; truncation is forbidden")
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("window must be [lower, upper]")
    lo, hi = [_number(x, "window", positive=True) for x in window]
    if hi <= lo:
        raise ValueError("acquisition window must have positive width")
    pairs = []
    for m, w in zip(mz, it):
        m = _number(m, "mz", positive=True)
        w = _number(w, "intensity")
        if w < 0 or not lo <= m <= hi:
            raise ValueError("intensities must be nonnegative and peaks inside the window")
        pairs.append((m, math.sqrt(w)))
    if sum(w for _, w in pairs) <= 0:
        raise ValueError("a spectrum must contain positive intensity")
    return sorted(pairs), (lo, hi)


def _covered_fraction(ions, window, a, p):
    """Length of the admissible observation-mass union / declared window width.

    abs(ion - observed) <= max(a, p * observed). For p < 1, the
    admissible observation interval is the union of the absolute and ppm
    intervals. Both contain the ion, so their union is one interval.
    """
    lo, hi = window
    intervals = []
    for ion in ions:
        left = max(lo, min(ion-a, ion/(1+p)))
        right = min(hi, max(ion+a, ion/(1-p)))
        if right > left:
            intervals.append((left, right))
    if not intervals:
        return 0.0
    intervals.sort()
    total = 0.0
    left, right = intervals[0]
    for a0, b0 in intervals[1:]:
        if a0 > right:
            total += right-left
            left, right = a0, b0
        else:
            right = max(right, b0)
    total += right-left
    return min(1.0, max(0.0, total/(hi-lo)))


def _assignment(ions, peaks, a, p):
    """Exact max observed-weight matching; each ion and observed peak used once.

    Ordered matching suffices: the left/right admissibility bounds for
    successive observed masses are nondecreasing, so a crossing pair can be
    uncrossed without losing feasibility or changing the observed weights.
    DP uses O(ions * peaks) time and O(ions) memory. Mass-error rewards are
    deliberately absent; adding them invalidates this exactness argument.
    """
    previous = [0.0] * (len(ions)+1)
    independent = 0.0
    for mass, weight in peaks:
        tolerance = max(a, p*mass)
        row = [0.0] * (len(ions)+1)
        matched = False
        for j, ion in enumerate(ions, 1):
            best = max(previous[j], row[j-1])
            if abs(mass-ion) <= tolerance:
                matched = True
                best = max(best, previous[j-1]+weight)
            row[j] = best
        previous = row
        if matched:
            independent += weight
    total = sum(w for _, w in peaks)
    return previous[-1]/total, independent/total


def _quantile(values, q):
    ordered = sorted(values)
    x = (len(ordered)-1)*q
    i = int(x)
    j = min(i+1, len(ordered)-1)
    return ordered[i] + (ordered[j]-ordered[i])*(x-i)


def candidate_features(ion_mz, spectra, *, abs_tol=0.01, ppm=10.0):
    """Return stable-column features plus per-spectrum evidence.

    No score, rank change, supervised fitting, hidden test, or F1 adoption is
    performed here. Duplicate ion masses are collapsed exactly; distinct
    hydrogen-shift hypotheses remain distinct and require chemistry review.
    """
    a, p = _tolerances(abs_tol, ppm)
    ions = _ions(ion_mz)
    if not isinstance(spectra, (list, tuple)) or not 1 <= len(spectra) <= MAX_VIEWS:
        raise ValueError("supply 1..16 spectra; missing views must not become zero scores")
    views = [_view(v) for v in spectra]
    cells = len(ions) * sum(len(peaks) for peaks, _ in views)
    if cells > MAX_TOTAL_CELLS:
        raise ValueError("dynamic-program cell budget exceeded")
    rows = []
    for peaks, window in views:
        fraction, independent = _assignment(ions, peaks, a, p)
        coverage = _covered_fraction(ions, window, a, p)
        rows.append({
            "assignment": fraction,
            "independent_explain": independent,
            "reuse_gap": max(0.0, independent-fraction),
            "uniform_mass_coverage": coverage,
            "uniform_excess": fraction-coverage,
        })
    assigned = [r["assignment"] for r in rows]
    excess = [r["uniform_excess"] for r in rows]
    vector = [
        max(assigned), median(assigned), _quantile(assigned, .25),
        sum(excess)/len(rows), _quantile(excess, .25),
        max(r["reuse_gap"] for r in rows),
        sum(r["uniform_mass_coverage"] for r in rows)/len(rows),
        math.log1p(len(ions)), float(len(rows)),
    ]
    return {
        "status": "EXPERIMENTAL_FEATURES_ONLY",
        "feature_names": list(FEATURE_NAMES), "features": vector,
        "per_view": rows, "work_cells": cells,
        "uniform_null_is_physical_noise_model": False,
    }


def main():
    # Read one bounded JSON document; stdout only. No input file is modified.
    raw = sys.stdin.buffer.read(MAX_JSON_BYTES+1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("JSON input exceeds 2 MiB")
    document = json.loads(raw)
    if not isinstance(document, dict) or set(document) != {"ion_mz", "spectra"}:
        raise ValueError("JSON requires exactly ion_mz and spectra")
    print(json.dumps(candidate_features(**document), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
