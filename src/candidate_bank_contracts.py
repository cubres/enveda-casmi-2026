"""Check the numerical contract of a packed molecular fingerprint bank.

The CASMI COCONUT bank uses big-endian packed uint8 fingerprints, a sorted
neutral-mass index, and an ordered selection of fingerprint bit indices.
Run this check once before using searchsorted or unpacking candidate rows:

    python candidate_bank_contracts.py --mass coco_mass.npy \
        --fingerprints coco_fp.npy --bits fp_bits.npy

This checks array shapes, values, and padding. Molecular identities, chemistry,
licensing, and the correspondence between independently supplied rows require
their own provenance checks. NumPy is the only dependency. Inputs are read only.
"""

# MIT License
# Copyright (c) 2026 cubres
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

import argparse
import json
from numbers import Integral
from pathlib import Path

import numpy as np


def validate_candidate_bank(mass, fingerprints, bits, *, chunk_rows=65536):
    """Return a compact report, or raise ValueError on a numerical mismatch.

    Bit order is fixed to NumPy's default big-endian packing. Selected bits may
    appear in any order: that order defines the model's output coordinates.
    Repeated masses are valid, but repeated selected bits are rejected.
    """
    if isinstance(chunk_rows, bool) or not isinstance(chunk_rows, Integral) or chunk_rows < 1:
        raise ValueError("chunk_rows must be a positive integer")
    mass = np.asarray(mass)
    fingerprints = np.asarray(fingerprints)
    bits = np.asarray(bits)
    if mass.ndim != 1 or mass.dtype.kind != "f":
        raise ValueError("mass must be a one-dimensional floating-point array")
    if fingerprints.ndim != 2 or fingerprints.dtype != np.dtype("uint8"):
        raise ValueError("fingerprints must be a two-dimensional uint8 array")
    if bits.ndim != 1 or bits.dtype.kind not in "iu" or len(bits) == 0:
        raise ValueError("bits must be a nonempty one-dimensional integer array")
    if np.any(bits < 0) or np.unique(bits).size != bits.size:
        raise ValueError("selected bit indices must be nonnegative and distinct")
    if len(mass) == 0 or fingerprints.shape[0] != len(mass):
        raise ValueError("mass and fingerprint row counts must match and be nonempty")
    nbits = len(bits)
    expected_width = (nbits + 7) // 8
    if fingerprints.shape[1] != expected_width:
        raise ValueError(f"packed fingerprint width must be {expected_width} bytes for {nbits} bits")
    padding_bits = (-nbits) % 8
    padding_mask = (1 << padding_bits) - 1
    previous = None
    for start in range(0, len(mass), int(chunk_rows)):
        stop = min(start + int(chunk_rows), len(mass))
        values = mass[start:stop]
        if not np.all(np.isfinite(values)) or np.any(values <= 0):
            raise ValueError("neutral masses must be finite and strictly positive")
        if np.any(values[1:] < values[:-1]) or (previous is not None and values[0] < previous):
            raise ValueError("neutral masses must be sorted in ascending order")
        previous = values[-1]
        if padding_bits and np.any(fingerprints[start:stop, -1] & padding_mask):
            raise ValueError("unused fingerprint padding bits must be zero (big-endian packing)")
    return {
        "status": "PASS_ARRAY_CONTRACT",
        "rows": len(mass),
        "selected_bits": nbits,
        "packed_width_bytes": expected_width,
        "padding_bits": padding_bits,
        "bitorder": "big",
        "mass_min": float(mass[0]),
        "mass_max": float(mass[-1]),
        "mass_dtype": str(mass.dtype),
        "fingerprint_dtype": str(fingerprints.dtype),
        "selected_bit_dtype": str(bits.dtype),
        "identity_alignment_verified": False,
        "chemical_fingerprints_verified": False,
    }


def inspect_files(mass_path, fingerprint_path, bits_path, *, chunk_rows=65536):
    """Read .npy arrays through read-only memory maps; object arrays are rejected."""
    paths = [Path(p) for p in (mass_path, fingerprint_path, bits_path)]
    arrays = []
    for path in paths:
        if path.suffix.lower() != ".npy":
            raise ValueError("each input must be a .npy file")
        arrays.append(np.load(path, mmap_mode="r", allow_pickle=False))
    return validate_candidate_bank(*arrays, chunk_rows=chunk_rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mass", type=Path, required=True)
    parser.add_argument("--fingerprints", type=Path, required=True)
    parser.add_argument("--bits", type=Path, required=True)
    parser.add_argument("--chunk-rows", type=int, default=65536)
    args = parser.parse_args()
    try:
        report = inspect_files(args.mass, args.fingerprints, args.bits, chunk_rows=args.chunk_rows)
    except (ValueError, OSError) as error:
        parser.exit(1, json.dumps({"status": "FAIL_ARRAY_CONTRACT", "error": str(error)}) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
