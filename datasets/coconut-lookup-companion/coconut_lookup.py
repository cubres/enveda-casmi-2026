"""Original numerical lookup for the retained COCONUT CASMI26 V2 layout.

Copyright 2026 cubres contributors. SPDX-License-Identifier: MIT
No RDKit, pickle, network, spectra, model weights, or structure deserialization.
Numeric/header checks do not certify molecular identity or regenerate chemistry.
"""
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path

import numpy as np

ROWS = 436389
SELECTED_BITS = 6930
FULL_BITS = 10407
PACKED_BYTES = 867
BITORDER = "big"
DESCRIPTOR_ORDER = ("Morgan-r2-4096", "Morgan-r3-4096", "RDKit-path-maxPath6-2048", "MACCS-167")
SMALL_PINS = {
    "coco_mass.npy": "2b2af92c3185fa8cd52a4a3e3e7fd7eda4d94e8b9402662a3a4c55ffb13c6e5c",
    "fp_bits.npy": "a61e372fc41091bf5c7467e08134081266262665077cb9e2c56d73e4887f3013",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite_number(value, name):
    require(not isinstance(value, (bool, np.bool_)), name + " must be a number, not bool")
    number = float(value)
    require(math.isfinite(number), name + " must be finite")
    return number


def mass_window_rows(masses, neutral_mass_da, ppm=10.0, *, max_rows=4096):
    """Inclusive neutral-mass window; original row indices remain in bank order.

    The caller converts a measured precursor/adduct to neutral mass beforehand.
    This function intentionally does not infer an adduct or widen an empty window.
    """
    require(isinstance(masses, np.ndarray) and masses.ndim == 1
            and masses.dtype.kind == "f", "one-dimensional floating masses required")
    require(np.isfinite(masses).all() and (masses > 0).all()
            and (np.diff(masses) >= 0).all(), "finite positive ascending mass array required")
    mass, tolerance = finite_number(neutral_mass_da, "neutral mass"), finite_number(ppm, "ppm")
    require(mass > 0 and tolerance >= 0, "positive neutral mass and nonnegative ppm required")
    require(type(max_rows) is int and 0 < max_rows <= 4096, "max_rows must be 1..4096")
    width = mass * tolerance / 1e6
    require(math.isfinite(width) and math.isfinite(mass + width), "mass window overflow")
    lo = int(np.searchsorted(masses, mass - width, side="left"))
    hi = int(np.searchsorted(masses, mass + width, side="right"))
    require(hi - lo <= max_rows, "window exceeds row cap; narrow it explicitly")
    return np.arange(lo, hi, dtype=np.int64)


def assert_row_join(candidate_row_ids, fingerprint_row_ids):
    """Reject a missing, duplicate, or reordered identity join without chemistry.

    Supply independently justified row IDs from the two producers. Equal IDs
    assert their supplied join; they do not establish those producers' truth.
    """
    left, right = np.asarray(candidate_row_ids), np.asarray(fingerprint_row_ids)
    require(left.ndim == right.ndim == 1 and left.dtype.kind == right.dtype.kind == "U",
            "one-dimensional Unicode text row IDs required")
    require(left.shape == right.shape and left.size > 0, "nonempty equal row counts required")
    require(np.all(left != "") and np.all(right != ""), "empty row ID")
    require(np.unique(left).size == left.size and np.unique(right).size == right.size,
            "duplicate row ID")
    require(np.array_equal(left, right), "candidate/fingerprint row order differs")


def assert_model_columns(bank_bits, model_bits, model_descriptor_order):
    """Require the declared full descriptor families and exact selected bit order.

    Shape alone cannot admit a Morgan2048+MACCS model into this selected space.
    Producer RDKit version/normalization and model provenance need separate pins.
    """
    left, right = np.asarray(bank_bits), np.asarray(model_bits)
    require(tuple(model_descriptor_order) == DESCRIPTOR_ORDER, "descriptor family/order differs")
    require(left.shape == right.shape == (SELECTED_BITS,) and left.dtype.kind in "iu"
            and right.dtype.kind in "iu", "6930 ordered integer bit indices required")
    require(np.unique(left).size == np.unique(right).size == SELECTED_BITS
            and np.all((left >= 0) & (left < FULL_BITS))
            and np.all((right >= 0) & (right < FULL_BITS)), "invalid/duplicate selected bit index")
    require(np.array_equal(left, right), "model/candidate selected bit order differs")


@dataclass(frozen=True)
class Bank:
    masses: np.ndarray
    packed: np.ndarray
    bits: np.ndarray

    def window(self, neutral_mass_da, ppm=10.0, *, max_rows=4096):
        return mass_window_rows(self.masses, neutral_mass_da, ppm, max_rows=max_rows)

    def decode(self, row_indices):
        """Decode at most4096 ordered rows; six byte-padding bits must be zero."""
        rows = np.asarray(row_indices)
        require(rows.ndim == 1 and rows.dtype.kind in "iu" and rows.size <= 4096,
                "at most4096 integer row indices required")
        require(np.all(rows < len(self.masses)) and np.all(rows >= 0)
                and (rows.size < 2 or np.all(rows[1:] > rows[:-1])), "invalid/reordered row indices")
        require(self.packed.dtype == np.uint8 and self.packed.shape == (len(self.masses), PACKED_BYTES),
                "packed matrix header differs")
        selected = self.packed[rows]
        require(np.all((selected[:, -1] & 63) == 0), "nonzero discarded padding bits")
        return np.unpackbits(selected, axis=1, bitorder=BITORDER)[:, :SELECTED_BITS]


def load_v2(root):
    """Read only three numerical files. Never load coco_meta.pkl.

    Small-file hashes pin mass and selection; the large packed file is checked
    by header, not fully hashed or verified against molecular structures here.
    """
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), "ordinary bank directory required")
    paths = {name: root / name for name in ("coco_mass.npy", "fp_bits.npy", "coco_fp.npy")}
    for path in paths.values():
        require(path.is_file() and not path.is_symlink(), "ordinary numeric file required")
    for name, expected in SMALL_PINS.items():
        require(paths[name].stat().st_size <= 4 * 1024 ** 2, "small-file size bound")
        require(hashlib.sha256(paths[name].read_bytes()).hexdigest() == expected, "retained V2 small-file pin differs")
    masses = np.load(paths["coco_mass.npy"], mmap_mode="r", allow_pickle=False)
    packed = np.load(paths["coco_fp.npy"], mmap_mode="r", allow_pickle=False)
    bits = np.load(paths["fp_bits.npy"], allow_pickle=False)
    require(masses.shape == (ROWS,) and masses.dtype == np.float64, "mass header differs")
    require(packed.shape == (ROWS, PACKED_BYTES) and packed.dtype == np.uint8, "packed header differs")
    require(bits.shape == (SELECTED_BITS,) and bits.dtype == np.int64
            and np.unique(bits).size == SELECTED_BITS
            and np.all((bits >= 0) & (bits < FULL_BITS)), "selection header/index contract differs")
    mass_window_rows(masses, 300.0, 0.0)  # numeric ordering validation, no decoded matrix
    return Bank(masses, packed, bits)
