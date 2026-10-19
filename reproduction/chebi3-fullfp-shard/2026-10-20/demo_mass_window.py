"""Inspect a deterministic neutral-mass candidate window without a model.

SPDX-License-Identifier: Apache-2.0

Only user-supplied dataset files are read; results go to stdout. No RDKit,
labels, model weights, pickle deserialization, network or file mutation.
"""

import argparse
import json
import math
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pyarrow.parquet as pq


ROWS = 4096
SELECTED_BITS = 10395
PACKED_BYTES = 1300


class Bank(NamedTuple):
    fingerprints: np.ndarray
    masses: np.ndarray
    mass_order: np.ndarray
    source: object
    source_rows: np.ndarray
    selected_bits: np.ndarray


def validate_bank(bank):
    """Validate consumer shapes and exact joins; this performs no chemistry."""
    if bank.fingerprints.shape != (ROWS, PACKED_BYTES) or bank.fingerprints.dtype != np.uint8:
        raise ValueError("expected 4096x1300 uint8 packed fingerprints")
    if bank.masses.shape != (ROWS,) or bank.masses.dtype != np.float64:
        raise ValueError("expected 4096 float64 neutral masses")
    if not np.all(np.isfinite(bank.masses)) or not np.all((bank.masses >= 80) & (bank.masses <= 1400)):
        raise ValueError("neutral masses must be finite within [80, 1400] Da")
    if bank.mass_order.shape != (ROWS,) or bank.mass_order.dtype.kind not in "iu":
        raise ValueError("expected 4096 integer mass-order indices")
    if not np.array_equal(bank.mass_order, np.argsort(bank.masses, kind="stable")):
        raise ValueError("mass_order must be the exact stable argsort")
    if bank.source_rows.shape != (ROWS,) or bank.source_rows.dtype.kind not in "iu":
        raise ValueError("expected 4096 integer original source indices")
    if np.any(bank.source_rows < 0) or np.unique(bank.source_rows).size != ROWS:
        raise ValueError("original source indices must be unique and nonnegative")
    if bank.selected_bits.shape != (SELECTED_BITS,) or bank.selected_bits.dtype.kind not in "iu":
        raise ValueError("expected 10395 integer selected-bit indices")
    if np.any(bank.selected_bits < 0) or np.any(bank.selected_bits >= 10407) or np.unique(bank.selected_bits).size != SELECTED_BITS:
        raise ValueError("selected-bit indices must be distinct within the 10407-bit definition")
    if np.any(bank.fingerprints[:, -1] & np.uint8(0x1F)):
        raise ValueError("the five trailing padding bits must be zero")
    required = {"inchikey14", "smiles", "source", "source_id", "chebi_star", "original_source_row", "computed_raw_key", "computed_mass"}
    if bank.source.num_rows != ROWS or not required.issubset(bank.source.column_names):
        raise ValueError("source Parquet row count or required fields differ")
    if set(bank.source["source"].to_pylist()) != {"ChEBI"} or set(bank.source["chebi_star"].to_pylist()) != {"3"}:
        raise ValueError("expected ChEBI three-star records only")
    keys = bank.source["inchikey14"].to_pylist()
    if any(not isinstance(key, str) or not key for key in keys) or len(set(keys)) != ROWS:
        raise ValueError("raw keys must be nonempty and unique")
    if bank.source["computed_raw_key"].to_pylist() != keys:
        raise ValueError("computed/source raw-key joins differ")
    if not np.array_equal(bank.source["original_source_row"].to_numpy(), bank.source_rows):
        raise ValueError("original source-row joins differ")
    if not np.array_equal(bank.source["computed_mass"].to_numpy(), bank.masses):
        raise ValueError("source computed masses do not align with mass array")


def load_bank(data_dir):
    """Load the six explicit files, using read-only mmap and no NumPy pickle."""
    directory = Path(data_dir)
    bank = Bank(
        fingerprints=np.load(directory / "external_fp.npy", mmap_mode="r", allow_pickle=False),
        masses=np.load(directory / "external_mass.npy", mmap_mode="r", allow_pickle=False),
        mass_order=np.load(directory / "mass_order.npy", mmap_mode="r", allow_pickle=False),
        source=pq.read_table(directory / "external_chebi3_4096.parquet"),
        source_rows=np.load(directory / "original_source_rows.npy", mmap_mode="r", allow_pickle=False),
        selected_bits=np.load(directory / "fp_bits.npy", mmap_mode="r", allow_pickle=False),
    )
    validate_bank(bank)
    return bank


def mass_window_indices(masses, mass_order, low_da, high_da):
    """Return row indices in a closed neutral-mass window, preserving tie order."""
    low, high = float(low_da), float(high_da)
    if not math.isfinite(low) or not math.isfinite(high) or low > high:
        raise ValueError("mass-window endpoints must be finite and ordered")
    ordered_masses = masses[mass_order]
    left = int(np.searchsorted(ordered_masses, low, side="left"))
    right = int(np.searchsorted(ordered_masses, high, side="right"))
    return mass_order[left:right]


def demo_result(bank, query_mass=None, ppm=10.0, limit=10):
    """Show source metadata and packed-bit counts, without structure ranking."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    mass = float(bank.masses[0]) if query_mass is None else float(query_mass)
    tolerance = float(ppm)
    if not math.isfinite(mass) or mass <= 0 or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("query mass and ppm must be positive and finite")
    delta = mass * tolerance * 1e-6
    indices = mass_window_indices(bank.masses, bank.mass_order, mass - delta, mass + delta)
    records = []
    for index in indices[:limit]:
        row_index = int(index)
        row = bank.source.slice(row_index, 1).to_pylist()[0]
        records.append({
            "row": row_index,
            "original_source_row": int(bank.source_rows[row_index]),
            "neutral_mass_da": float(bank.masses[row_index]),
            "inchikey14": row["inchikey14"],
            "source": row["source"],
            "source_id": row["source_id"],
            "smiles": row["smiles"],
            "selected_on_bits": int(np.unpackbits(bank.fingerprints[row_index], bitorder="big")[:SELECTED_BITS].sum()),
        })
    return {
        "query_origin": "illustrative first dataset row" if query_mass is None else "user-supplied neutral mass",
        "query_neutral_mass_da": mass,
        "tolerance_ppm": tolerance,
        "window_da": [mass - delta, mass + delta],
        "matching_rows": int(indices.size),
        "shown_rows": len(records),
        "order": "neutral mass ascending; original shard row order for ties",
        "records": records,
        "scope": "Candidate enumeration only; no model ranking, labels or score claim.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, help="Directory containing the six dataset files")
    parser.add_argument("--mass", type=float, default=None, help="Neutral monoisotopic mass in Da; default is an illustrative dataset row")
    parser.add_argument("--ppm", type=float, default=10.0)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(demo_result(load_bank(args.data_dir), args.mass, args.ppm, args.limit), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
