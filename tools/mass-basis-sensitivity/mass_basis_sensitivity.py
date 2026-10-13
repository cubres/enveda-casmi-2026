"""Original numerical sensitivity tool: a mass basis is never inferred.

Three conditional interpretations share one supplied scalar and one explicit
proton channel. This is row-window arithmetic, not chemical identification.
No third-party code, structures, reference records or model files are used.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import MappingProxyType
from io import StringIO

PROTON_MASS_DA = 1.0072764665789  # Declared NIST CODATA 2022 convention.
MAX_ROWS = 1_000_000
MAX_CSV_BYTES = 64 * 1024 * 1024
BASIS_NAMES = ("neutral_monomer_mass", "ion_total_mass", "precursor_mz")
CHANNELS = MappingProxyType({
    "[M+H]+": (1, 1, 1), "[M-H]-": (1, -1, -1),
    "[M+2H]2+": (1, 2, 2), "[M-2H]2-": (1, -2, -2),
    "[M+3H]3+": (1, 3, 3), "[M-3H]3-": (1, -3, -3),
    "[2M+H]+": (2, 1, 1), "[2M-H]-": (2, -1, -1),
})


def number(value, name, *, positive=False):
    if type(value) not in (int, float):
        raise ValueError(name + " must be a finite built-in number; bool is refused")
    try:
        result = float(value)
    except (OverflowError, ValueError):
        raise ValueError(name + " is outside finite binary64") from None
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(name + " must be finite" + (" and positive" if positive else ""))
    return result


@dataclass(frozen=True)
class MassIndex:
    """Owned immutable sorted positive numerical masses; preserve row positions."""
    masses: tuple

    def __post_init__(self):
        if type(self.masses) not in (list, tuple):
            raise ValueError("masses must be a bounded list/tuple, not a lazy iterable")
        if len(self.masses) > MAX_ROWS:
            raise ValueError("mass row cap exceeded before numerical consumption")
        owned = tuple(number(value, "candidate mass", positive=True) for value in self.masses)
        if any(a > b for a, b in zip(owned, owned[1:])):
            raise ValueError("mass rows must already be nondecreasing; rows are never sorted")
        object.__setattr__(self, "masses", owned)


def _channel(label, polarity):
    if type(label) is not str or label not in CHANNELS:
        raise ValueError("unknown channel; only the eight declared proton channels are supported")
    n, h, z = CHANNELS[label]
    if polarity is not None and (type(polarity) is not str or polarity not in ("positive", "negative")):
        raise ValueError("polarity must be positive, negative, or None")
    sign = "positive" if z > 0 else "negative"
    if polarity is not None and polarity != sign:
        raise ValueError("declared channel and explicit polarity disagree")
    return {"label": label, "molecule_multiplier": n, "signed_protons": h,
            "signed_charge": z, "polarity": sign}


def interpretation_window(supplied_value, channel, ppm, basis, *, polarity=None):
    """Return the closed binary64 interval under one conditional interpretation.

PPM is referenced to the supplied scalar S in each assumed unit. Neutral means
neutral MONOMER mass M, including for dimer channels. No ion-feasibility filter
is applied to the neutral numerical hypothesis.
"""
    value = number(supplied_value, "supplied value", positive=True)
    tolerance = number(ppm, "ppm")
    if not 0 <= tolerance < 1_000_000:
        raise ValueError("ppm must be in [0, 1000000)")
    if type(basis) is not str or basis not in BASIS_NAMES:
        raise ValueError("unknown mass-basis hypothesis")
    spec = _channel(channel, polarity)
    n, h, z = spec["molecule_multiplier"], spec["signed_protons"], spec["signed_charge"]
    # Fixed operation order defines the reported finite binary64 endpoints.
    half = value * (tolerance / 1_000_000.0)
    raw_lower, raw_upper = value - half, value + half
    if basis == "neutral_monomer_mass":
        center, lower, upper = value, raw_lower, raw_upper
        formula = "M = S"
    else:
        factor = 1 if basis == "ion_total_mass" else abs(z)
        shift = h * PROTON_MASS_DA
        center = (factor * value - shift) / n
        lower = (factor * raw_lower - shift) / n
        upper = (factor * raw_upper - shift) / n
        formula = "M = (S - h*p)/n" if basis == "ion_total_mass" else "M = (abs(z)*S - h*p)/n"
    if not all(math.isfinite(x) for x in (half, center, lower, upper)):
        raise ValueError("nonfinite converted center or window")
    if center <= 0 or lower > center or center > upper:
        return {"basis": basis, "status": "HOLD_NONPOSITIVE_OR_INVALID_CENTER",
                "center_da": center, "lower_da": lower, "upper_da": upper,
                "formula": formula, "mass_basis_qualification": "UNQUALIFIED"}
    return {"basis": basis, "status": "CONDITIONAL_NUMERICAL_WINDOW",
            "center_da": center, "lower_da": lower, "upper_da": upper,
            "lower_closed": True, "upper_closed": True, "formula": formula,
            "implemented_interval_half_span_da": (upper - lower) / 2.0,
            "positive_ppm_collapsed_at_binary64_resolution": tolerance > 0 and lower == upper,
            "mass_basis_qualification": "UNQUALIFIED"}


def _difference(lhs, rhs):
    start, stop = lhs
    common_start, common_stop = max(start, rhs[0]), min(stop, rhs[1])
    if start == stop:
        return []
    if common_start >= common_stop:
        return [[start, stop]]
    return [[a, b] for a, b in ((start, common_start), (common_stop, stop)) if a < b]


def audit_basis(index, supplied_value, channel, ppm, *, polarity=None):
    """Compare three assumptions without choosing or qualifying a true basis."""
    if type(index) is not MassIndex:
        raise ValueError("use a validated owned MassIndex")
    spec = _channel(channel, polarity)
    windows = []
    for basis in BASIS_NAMES:
        row = interpretation_window(supplied_value, channel, ppm, basis, polarity=polarity)
        if row["status"] == "CONDITIONAL_NUMERICAL_WINDOW":
            lo = bisect_left(index.masses, row["lower_da"])
            hi = bisect_right(index.masses, row["upper_da"])
            row.update({"source_row_start": lo, "source_row_stop_exclusive": hi,
                        "source_row_count": hi - lo})
        windows.append(row)
    pairs = []
    for i in range(3):
        for j in range(i + 1, 3):
            a, b = windows[i], windows[j]
            pair = {"lhs": a["basis"], "rhs": b["basis"]}
            if "source_row_start" not in a or "source_row_start" not in b:
                pair.update({"status": "UNAVAILABLE_HELD_HYPOTHESIS", "row_jaccard": None})
            else:
                ra = (a["source_row_start"], a["source_row_stop_exclusive"])
                rb = (b["source_row_start"], b["source_row_stop_exclusive"])
                common = max(0, min(ra[1], rb[1]) - max(ra[0], rb[0]))
                union = a["source_row_count"] + b["source_row_count"] - common
                removed, added = _difference(ra, rb), _difference(rb, ra)
                pair.update({"status": "CONDITIONAL_SOURCE_POSITION_COMPARISON", "intersection_row_count": common,
                             "union_row_count": union, "row_jaccard": common / union if union else None,
                             "empty_union_jaccard": "UNAVAILABLE", "lhs_only_ranges": removed,
                             "rhs_only_ranges": added, "lhs_only_row_count": a["source_row_count"] - common,
                             "rhs_only_row_count": b["source_row_count"] - common})
            pairs.append(pair)
    return {"schema": "original-mass-basis-sensitivity-v1", "mass_basis_qualification": "UNQUALIFIED",
            "supplied_value": number(supplied_value, "supplied value", positive=True),
            "ppm": number(ppm, "ppm"), "ppm_denominator": "supplied scalar S under each assumed unit",
            "channel": spec, "explicit_polarity_constraint": polarity, "proton_mass_da": PROTON_MASS_DA,
            "candidate_source_rows": len(index.masses), "bounds": "closed implemented binary64 endpoints",
            "row_semantics": "positions in the exact supplied sorted mass sequence; duplicates retained",
            "neutral_hypothesis_ion_feasibility_screening": False,
            "hypotheses": windows, "pairwise_sensitivity": pairs,
            "chemical_identity_or_basis_inferred": False, "model_or_official_score": None}


def load_mass_csv(path):
    path = Path(path)
    if path.suffix.lower() != ".csv":
        raise ValueError("require a mass-only CSV below the 64-MiB byte cap")
    with path.open("rb") as stream:
        payload = stream.read(MAX_CSV_BYTES + 1)
    if len(payload) > MAX_CSV_BYTES:
        raise ValueError("CSV exceeds the 64-MiB byte cap")
    values = []
    with StringIO(payload.decode("utf-8"), newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["source_row_id", "neutral_mass_da"]:
            raise ValueError("CSV header must be source_row_id,neutral_mass_da only")
        for row in reader:
            if len(values) >= MAX_ROWS:
                raise ValueError("CSV row cap exceeded")
            if set(row) != {"source_row_id", "neutral_mass_da"} or row["source_row_id"] != str(len(values)):
                raise ValueError("CSV must preserve consecutive zero-based numerical row positions")
            values.append(float(row["neutral_mass_da"]))
    return MassIndex(values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--masses-csv", required=True)
    parser.add_argument("--value", required=True, type=float)
    parser.add_argument("--channel", required=True, choices=tuple(CHANNELS))
    parser.add_argument("--ppm", required=True, type=float)
    parser.add_argument("--polarity", choices=("positive", "negative"))
    parser.add_argument("--report", required=True, help="Fresh .json output; existing files are preserved")
    parser.add_argument("--windows-csv", help="Optional fresh .csv output for local experiment tables")
    args = parser.parse_args()
    report_path = Path(args.report)
    csv_path = Path(args.windows_csv) if args.windows_csv else None
    if report_path.suffix.lower() != ".json" or report_path.name == "kernel-metadata.json" or (csv_path and csv_path.suffix.lower() != ".csv"):
        raise ValueError("require ordinary fresh JSON/CSV outputs")
    report = audit_basis(load_mass_csv(args.masses_csv), args.value, args.channel, args.ppm, polarity=args.polarity)
    with report_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    if csv_path:
        names = ["basis", "status", "center_da", "lower_da", "upper_da", "source_row_start", "source_row_stop_exclusive", "source_row_count", "mass_basis_qualification"]
        with csv_path.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=names, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(report["hypotheses"])


if __name__ == "__main__":
    main()
