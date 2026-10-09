# ChEBI + LIPID MAPS candidates for CASMI26

A compact numerical candidate bank for experiments that need biochemical and lipid structures alongside a natural-product pool. Data version 1 supplies **62,744 candidate rows**, with neutral monoisotopic masses and packed molecular fingerprints. The files can support a narrow mass-window search on a CPU; they contain neither query spectra nor a ready-to-submit prediction file.

```text
measured precursor m/z + charge/adduct convention
                     |
               neutral mass
                     |
             ppm window in bio_mass
                     |
          same row indices in bio_fp / bio_meta
                     |
        chemical / spectral ranking and identity deduplication
```

## File dictionary — data version 1

| File | Shape / dtype / bytes | Role |
|---|---|---|
| `bio_mass.npy` | `(62744,)`, `float64`; 502,080 bytes | Ascending neutral monoisotopic masses in daltons |
| `bio_fp.npy` | `(62744, 867)`, `uint8`; 54,399,176 bytes | Packed fingerprint bytes, one candidate per row |
| `bio_meta.pkl` | Python pickle; 5,545,993 bytes | Companion structure metadata; the public consumer expects aligned `keys` and `smiles` entries |

The public baseline consumes all three in the same row order. Preserve that alignment when filtering, merging, deduplicating or sorting. This audit did not deserialize the pickle or independently prove every metadata/fingerprint row correspondence.

The entire mass vector was freshly read on October 9, 2026: all values were finite and ascending, spanning **100.013599376 to 1299.29974316 Da**. Its full SHA256 is:

`7b67b125f7bed307c2ac08bf41ad92044bfc2177519c5d4bb36c2c51789a2921`

The fingerprint shape and dtype were established from its binary header. That is a shape check, rather than a complete fingerprint payload or chemical-correctness certification.

## Quick start: inspect a neutral-mass window without pickle

```python
from pathlib import Path
import numpy as np

root = Path('/kaggle/input/chebi-lipidmaps-casmi26')  # use a local folder if needed
mass = np.load(root / 'bio_mass.npy', mmap_mode='r', allow_pickle=False)
packed = np.load(root / 'bio_fp.npy', mmap_mode='r', allow_pickle=False)
assert mass.shape == (62744,) and mass.dtype == np.dtype('float64')
assert packed.shape == (62744, 867) and packed.dtype == np.dtype('uint8')
assert np.isfinite(mass).all() and np.all(mass[1:] >= mass[:-1])

neutral_mass_da, ppm = 300.0, 10.0  # illustrative neutral mass, not precursor m/z
if not np.isfinite(neutral_mass_da) or neutral_mass_da <= 0:
    raise ValueError('neutral mass must be positive and finite')
if not np.isfinite(ppm) or ppm < 0:
    raise ValueError('ppm must be finite and nonnegative')
width = neutral_mass_da * (ppm / 1e6)
lo = int(np.searchsorted(mass, neutral_mass_da - width, side='left'))
hi = int(np.searchsorted(mass, neutral_mass_da + width, side='right'))
rows = np.arange(lo, hi)  # preserve these row indices for every companion lookup
print('candidate rows:', len(rows), 'range:', (lo, hi))

# The baseline's consumer convention is 6,930 selected bits, big-endian bytes.
# Confirm the matching generator/selection indices before using another model.
bits = np.unpackbits(packed[lo:hi], axis=1, bitorder='big')[:, :6930]
print('decoded window shape:', bits.shape)
```

The example memory-maps the packed matrix and decodes only the selected window. Six trailing padding bits are discarded under the baseline convention. Loading the complete 62,744 × 6,930 unpacked matrix would allocate approximately 435 MB of uint8 values before other copies; there is usually no reason to do that for one mass window.

The actual mass loading/sort/range checks ran during the audit. The general window and bit-decoding logic passed invented boundary fixtures, including an empty window. Full real fingerprint decoding and model inference were not executed in that audit.

## Before merging with another bank

- Match the exact fingerprint construction and selected-bit ordering, rather than relying on the shared 867-byte shape. The companion [COCONUT resource](https://www.kaggle.com/datasets/prvsiyan/coconut-casmi26-candidates) publishes `fp_bits.npy`; do not assume a newly generated bank has that ordering without its build record.
- If you concatenate two ascending mass vectors, the result is usually **not** ascending. Compute one stable sorting permutation for the combined masses and apply it to fingerprints, identifiers, SMILES and any provenance labels together before using `searchsorted`.
- Keep source membership and original row numbers during merging. Deduplicate using the competition's scored structure-identity convention, rather than fingerprint equality alone.
- Evaluate candidate coverage and ranking separately. More candidates can recover absent answers and can also dilute an existing shortlist; this card makes no score-improvement claim.

## Sources, license and known provenance gaps

Please credit [ChEBI](https://www.ebi.ac.uk/chebi/) and [LIPID MAPS](https://www.lipidmaps.org/) when using their candidate structures. The current Kaggle dataset label is **CC BY-NC-SA 4.0**, which is preserved here. ChEBI's [current licensing page](https://www.ebi.ac.uk/chebi/about/) and LIPID MAPS' [current terms](https://www.lipidmaps.org/terms-of-use) state CC BY 4.0 for their databases; those present-day pages do not identify the exact historical releases used for this packaged snapshot or automatically change its existing license label.

Version 1 currently contains the three binary files above, without an included release/build manifest. The precise source download dates, source URLs/checksums, generator runtime, per-source row counts and deduplication procedure still need a documented historical build record. Do not invent those facts or infer them from filenames.

ChEBI recommends its 2025 resource paper, *ChEBI: re-engineered for a sustainable future*; LIPID MAPS recommends Conroy et al., *LIPID MAPS: update to databases and tools for the lipidomics community* (2023), DOI [10.1093/nar/gkad896](https://doi.org/10.1093/nar/gkad896). Follow the upstream [LIPID MAPS citation guidance](https://www.lipidmaps.org/how-to-link) for particular resources.

For experiments, consult the [public CASMI notebook](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) and [Enveda project history](https://github.com/cubres/enveda-casmi-2026). Check the notebook's actual configuration: attaching this dataset does not establish that a particular version enabled this branch.
