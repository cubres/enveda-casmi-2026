"""Original NumPy starters for public CASMI candidate resources.

No network, pickle loading, model execution, competition labels or submissions.
Copyright 2026 cubres. SPDX-License-Identifier: MIT.
"""
from pathlib import Path
import re
import numpy as np


def lookup_popularity(keys, sid, pmid, blocks):
    """Lookup exact S14 keys; unknown keys return matched=False and zero counts.

    `keys` must be a sorted unique S14 vector. This function does not scan its
    105-million-row order on every call; verify provenance and file hashes first.
    The counts are distinct integer counts, not precomputed logarithms.
    """
    if keys.ndim != 1 or keys.dtype != np.dtype('S14'):
        raise ValueError('keys must be a one-dimensional S14 array')
    if sid.shape != keys.shape or pmid.shape != keys.shape:
        raise ValueError('key and count arrays must have the same row count')
    if sid.dtype != np.dtype('uint32') or pmid.dtype != np.dtype('uint32'):
        raise ValueError('count arrays must use uint32')
    checked = []
    for block in blocks:
        if isinstance(block, bytes):
            block = block.decode('ascii')
        if not isinstance(block, str) or re.fullmatch(r'[A-Z]{14}', block) is None:
            raise ValueError('pass a 14-letter uppercase InChIKey first block')
        checked.append(block)
    q = np.asarray(checked, dtype='S14')
    index = np.searchsorted(keys, q, side='left')
    matched = index < len(keys)
    in_bounds = np.flatnonzero(matched)
    matched[in_bounds] = keys[index[in_bounds]] == q[in_bounds]
    positions = np.flatnonzero(matched)
    out_sid = np.zeros(len(q), dtype=np.uint32)
    out_pmid = np.zeros(len(q), dtype=np.uint32)
    out_sid[positions] = sid[index[positions]]
    out_pmid[positions] = pmid[index[positions]]
    pop = np.log1p(out_sid.astype(np.float64)) + np.log1p(out_pmid.astype(np.float64))
    return {'block': q, 'matched': matched, 'substances': out_sid,
            'pubmed': out_pmid, 'pop': pop}


def load_popularity(root):
    """Memory-map public v1 arrays; no copying the multi-GB key table."""
    root = Path(root)
    return tuple(np.load(root / name, mmap_mode='r', allow_pickle=False) for name in
                 ('ap2pop_ik14.npy', 'ap2pop_ik14_sid.npy', 'ap2pop_ik14_pmid.npy'))


def mass_window(mass, neutral_mass_da, ppm=10.0):
    """Return [lo, hi) in an ascending mass vector; interval ends are inclusive.

    Input is a neutral molecular mass, not measured precursor m/z. The caller
    must convert the adduct/charge with the same convention as its pipeline.
    """
    mass = np.asarray(mass)
    if mass.ndim != 1 or not np.issubdtype(mass.dtype, np.floating):
        raise ValueError('mass must be a one-dimensional floating-point vector')
    if not np.isfinite(mass).all() or np.any(mass[1:] < mass[:-1]):
        raise ValueError('mass must be finite and sorted ascending')
    center, ppm = float(neutral_mass_da), float(ppm)
    if not np.isfinite(center) or center <= 0 or not np.isfinite(ppm) or ppm < 0:
        raise ValueError('neutral mass must be positive and ppm nonnegative; both finite')
    width = center * (ppm / 1e6)
    lower, upper = center - width, center + width
    if not np.isfinite(lower) or not np.isfinite(upper):
        raise ValueError('mass interval overflowed')
    return (int(np.searchsorted(mass, lower, side='left')),
            int(np.searchsorted(mass, upper, side='right')))


def load_bio_numerical(root):
    """Memory-map only numerical files. Never deserialize bio_meta.pkl."""
    root = Path(root)
    mass = np.load(root / 'bio_mass.npy', mmap_mode='r', allow_pickle=False)
    packed = np.load(root / 'bio_fp.npy', mmap_mode='r', allow_pickle=False)
    if mass.shape != (62744,) or mass.dtype != np.dtype('float64'):
        raise ValueError('unexpected bio_mass v1 header')
    if packed.shape != (62744, 867) or packed.dtype != np.dtype('uint8'):
        raise ValueError('unexpected bio_fp v1 header')
    return mass, packed


def decode_selected_bits(packed_rows, selected_bit_count=6930):
    """Consumer convention only: big-endian bytes, discard padding.

    The selected-bit ordering must be pinned to the exact fingerprint generator;
    this shape check cannot prove chemical/model compatibility.
    """
    if packed_rows.ndim != 2 or packed_rows.dtype != np.dtype('uint8'):
        raise ValueError('packed rows must be a 2D uint8 matrix')
    if not 0 < selected_bit_count <= 8 * packed_rows.shape[1]:
        raise ValueError('selected bit count exceeds packed capacity')
    return np.unpackbits(packed_rows, axis=1, bitorder='big')[:, :selected_bit_count]
