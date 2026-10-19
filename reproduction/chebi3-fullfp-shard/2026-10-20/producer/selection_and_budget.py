"""Deterministic metadata selection and measured CPU budget forecasting.

SPDX-License-Identifier: Apache-2.0

This module uses only the Python standard library. It neither reads files nor
performs molecular/fingerprint processing. Original input-list positions are
the source indices; callers must provide the complete source table in order.
"""

from collections.abc import Iterable, Mapping, Sequence
import math
from numbers import Integral, Real
import statistics


TARGET_ROWS = 4096
CANARY_ROWS = 64
MASS_MIN_DA = 80.0
MASS_MAX_DA = 1400.0
MASS_BIN_COUNT = 64
CHUNK_ROWS = 8
WORKERS = 2
SAFETY_FACTOR = 1.5
IO_RESERVE_SECONDS = 120.0
DRIVER_BUDGET_SECONDS = 1760.0
WRAPPER_BUDGET_SECONDS = 1800.0
MAX_RECENT_CHUNKS = 128
EXPECTED_ELIGIBLE_COUNT = 8895  # Independent metadata audit; driver verifies.


def _real(value, name):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a real number, excluding booleans")
    return float(value)


def _sequence(value, name):
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be an ordered sequence")


def mass_bin_index(mass):
    """Map an eligible finite mass to 64 equal-width bins, including 1400 Da.

    Bins are left-closed/right-open, except the last bin includes its endpoint.
    The width is exactly 20.625 Da. Out-of-range/nonfinite masses are rejected.
    """
    value = _real(mass, "mass")
    if not math.isfinite(value) or not MASS_MIN_DA <= value <= MASS_MAX_DA:
        raise ValueError("mass must be finite and within [80, 1400] Da")
    index = math.floor(
        (value - MASS_MIN_DA) * MASS_BIN_COUNT / (MASS_MAX_DA - MASS_MIN_DA)
    )
    return min(index, MASS_BIN_COUNT - 1)


def select_shard(rows, old_raw_keys):
    """Select exactly 4096 raw-new ChEBI three-star rows, without chemistry.

    Required mapping fields are ``source``, ``chebi_star``, ``inchikey14`` and
    ``monoisotopic_mass``. ``source == 'ChEBI'`` and ``str(chebi_star) == '3'``
    are literal eligibility rules. Masses must be numeric; nonfinite or
    out-of-range numeric masses are excluded. Malformed row schemas reject.

    After filtering, duplicate raw keys retain the earliest original source
    index. Each mass bin is sorted by (raw key, source index). Ascending-bin
    round-robin selection produces the shard; its first 64 entries are the
    deterministic, mass-balanced canary. Empty/exhausted bins are skipped.

    The driver separately asserts the frozen expected eligible count, 8895.
    This function reports the actual count rather than assuming that audit.
    """
    _sequence(rows, "rows")
    if isinstance(old_raw_keys, (str, bytes, bytearray, Mapping)) or not isinstance(
        old_raw_keys, Iterable
    ):
        raise ValueError("old_raw_keys must be an iterable of raw-key strings")
    old_keys = frozenset(old_raw_keys)
    if any(not isinstance(key, str) or not key for key in old_keys):
        raise ValueError("old_raw_keys contains a non-string or empty key")

    bins = [[] for _ in range(MASS_BIN_COUNT)]
    seen = set()
    excluded = dict.fromkeys(
        ("other_source", "other_star", "old_bank_key", "nonfinite_mass", "mass_range", "duplicate_raw_key"),
        0,
    )
    required = ("source", "chebi_star", "inchikey14", "monoisotopic_mass")
    for source_index, row in enumerate(rows):
        if not isinstance(row, Mapping) or any(field not in row for field in required):
            raise ValueError(f"row {source_index} has an invalid mapping schema")
        key = row["inchikey14"]
        if not isinstance(row["source"], str) or not isinstance(key, str) or not key:
            raise ValueError(f"row {source_index} has an invalid source or raw key")
        mass = _real(row["monoisotopic_mass"], f"row {source_index} mass")
        if row["source"] != "ChEBI":
            excluded["other_source"] += 1
        elif str(row["chebi_star"]) != "3":
            excluded["other_star"] += 1
        elif key in old_keys:
            excluded["old_bank_key"] += 1
        elif not math.isfinite(mass):
            excluded["nonfinite_mass"] += 1
        elif not MASS_MIN_DA <= mass <= MASS_MAX_DA:
            excluded["mass_range"] += 1
        elif key in seen:
            excluded["duplicate_raw_key"] += 1
        else:
            seen.add(key)
            bins[mass_bin_index(mass)].append((key, source_index))

    eligible_count = len(seen)
    if eligible_count < TARGET_ROWS:
        raise ValueError(f"only {eligible_count} eligible unique rows; need {TARGET_ROWS}")
    for bucket in bins:
        bucket.sort(key=lambda pair: (pair[0], pair[1]))

    selected = []
    selected_bin_counts = [0] * MASS_BIN_COUNT
    cursors = [0] * MASS_BIN_COUNT
    while len(selected) < TARGET_ROWS:
        progressed = False
        for bin_index, bucket in enumerate(bins):
            if cursors[bin_index] < len(bucket):
                selected.append(bucket[cursors[bin_index]][1])
                cursors[bin_index] += 1
                selected_bin_counts[bin_index] += 1
                progressed = True
                if len(selected) == TARGET_ROWS:
                    break
        if not progressed:  # Defensive; eligible_count already establishes size.
            raise RuntimeError("round-robin exhausted before target size")

    return {
        "selected_indices": selected,
        "canary_indices": selected[:CANARY_ROWS],
        "eligible_count": eligible_count,
        "eligible_bin_counts": [len(bucket) for bucket in bins],
        "selected_bin_counts": selected_bin_counts,
        "canary_bin_counts": [
            sum(mass_bin_index(rows[index]["monoisotopic_mass"]) == b for index in selected[:CANARY_ROWS])
            for b in range(MASS_BIN_COUNT)
        ],
        "excluded_counts": excluded,
        "source_row_count": len(rows),
        "target_rows": TARGET_ROWS,
        "mass_min_da": MASS_MIN_DA,
        "mass_max_da": MASS_MAX_DA,
        "mass_bin_count": MASS_BIN_COUNT,
        "duplicate_policy": "earliest eligible original source index per raw key",
        "order": "ascending-bin round-robin; lexicographic raw key then source index within bin",
    }


def forecast_budget(chunk_timings_seconds, *, completed_rows, elapsed_seconds):
    """Forecast remaining work from this selected shard's measured chunks only.

    Supply original 64-row canary timings, then the same accumulating timing
    history for rolling checks. At least eight positive finite eight-row chunk
    durations are required. The most recent 128 durations determine nearest-
    rank p90 and the median. This function cannot establish timing provenance;
    the driver must bind them to the current selected-shard run and include
    *all* input/proof/profile/canary time in ``elapsed_seconds``.

    Remaining work is ceil(ceil(remaining_rows / 8) / 2) parallel waves at
    1.5 * max(p90, median), plus 120 seconds for I/O. A forecast passes only
    when elapsed + remaining compute + reserve is strictly below 1760 seconds.
    The owning wrapper has a separate 1800-second hard bound.
    """
    _sequence(chunk_timings_seconds, "chunk_timings_seconds")
    if isinstance(completed_rows, bool) or not isinstance(completed_rows, Integral):
        raise ValueError("completed_rows must be an integer")
    completed_rows = int(completed_rows)
    if not CANARY_ROWS <= completed_rows <= TARGET_ROWS or completed_rows % CHUNK_ROWS:
        raise ValueError("completed_rows must be a multiple of 8 within [64, 4096]")
    if len(chunk_timings_seconds) < CANARY_ROWS // CHUNK_ROWS:
        raise ValueError("at least eight measured chunk timings are required")
    if len(chunk_timings_seconds) > completed_rows // CHUNK_ROWS:
        raise ValueError("more measured chunks than completed rows permit")
    elapsed = _real(elapsed_seconds, "elapsed_seconds")
    if not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError("elapsed_seconds must be finite and nonnegative")
    timings = [_real(value, "chunk timing") for value in chunk_timings_seconds]
    if any(not math.isfinite(value) or value <= 0 for value in timings):
        raise ValueError("chunk timings must be positive and finite")
    recent = timings[-MAX_RECENT_CHUNKS:]
    ordered = sorted(recent)
    p90 = ordered[math.ceil(0.9 * len(ordered)) - 1]
    median = float(statistics.median(ordered))
    seconds_per_wave = SAFETY_FACTOR * max(p90, median)
    remaining_rows = TARGET_ROWS - completed_rows
    remaining_chunks = math.ceil(remaining_rows / CHUNK_ROWS)
    remaining_waves = math.ceil(remaining_chunks / WORKERS)
    remaining_compute = remaining_waves * seconds_per_wave
    forecast_total = elapsed + remaining_compute + IO_RESERVE_SECONDS
    return {
        "passes": forecast_total < DRIVER_BUDGET_SECONDS,
        "elapsed_seconds": elapsed,
        "completed_rows": completed_rows,
        "remaining_rows": remaining_rows,
        "measured_chunk_count": len(timings),
        "recent_chunk_count": len(recent),
        "p90_chunk_seconds": p90,
        "median_chunk_seconds": median,
        "p90_method": "nearest rank, ceil(0.9*n)-1 in ascending order",
        "safety_factor": SAFETY_FACTOR,
        "seconds_per_parallel_wave": seconds_per_wave,
        "workers": WORKERS,
        "chunk_rows": CHUNK_ROWS,
        "remaining_chunks": remaining_chunks,
        "remaining_waves": remaining_waves,
        "remaining_compute_seconds": remaining_compute,
        "io_reserve_seconds": IO_RESERVE_SECONDS,
        "forecast_total_seconds": forecast_total,
        "driver_budget_seconds": DRIVER_BUDGET_SECONDS,
        "wrapper_budget_seconds": WRAPPER_BUDGET_SECONDS,
        "measurement_scope": "caller-bound current selected-shard canary and rolling chunks only",
    }
