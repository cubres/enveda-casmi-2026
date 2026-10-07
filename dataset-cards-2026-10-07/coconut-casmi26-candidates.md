## A compact natural-product candidate bank for mass-window search

This CASMI26 resource packages COCONUT-derived candidate structures, their neutral monoisotopic masses and selected molecular fingerprints. It supports candidate generation and fingerprint-based ranking; it contains neither query MS/MS spectra nor a ready-made competition submission.

```text
precursor m/z + adduct -> neutral mass -> candidate rows
                                         |-- aligned structures/identifiers
                                         |-- selected fingerprint bits -> ranking
```

### File contract — Kaggle data version 2

The bank contains **436,389 aligned candidate rows**. Row `i` must refer to the same molecule in every candidate array and in `coco_meta.pkl`; do not sort or filter one component independently.

| File | Shape / dtype | Contents |
|---|---|---|
| `coco_mass.npy` | `(436389,)`, float64 | Neutral monoisotopic mass in daltons, sorted ascending |
| `coco_fp.npy` | `(436389, 867)`, uint8 | Packed bits: 6,930 useful bits per row plus byte padding |
| `fp_bits.npy` | `(6930,)`, int64 | Selected column indices from the concatenated descriptor vector |
| `coco_meta.pkl` | Python pickle; 41,450,156 bytes | Aligned structure identifiers and SMILES metadata used by the baseline |

Version 2 added the fingerprint selection-index file. The complete mass array was checked as finite and ascending, with a range of **100.009519128–1299.7599298120003 Da**. The fingerprint matrix shape was verified from its binary header; this card does not certify every structure or fingerprint row.

### Load a narrow candidate window without unpacking the whole bank

```python
from pathlib import Path
import numpy as np

root = Path('/kaggle/input/coconut-casmi26-candidates')
mass = np.load(root / 'coco_mass.npy', mmap_mode='r', allow_pickle=False)
packed = np.load(root / 'coco_fp.npy', mmap_mode='r', allow_pickle=False)
selection = np.load(root / 'fp_bits.npy', allow_pickle=False)
assert mass.shape == (436389,)
assert packed.shape == (len(mass), 867) and len(selection) == 6930

neutral_mass_da, ppm = 300.0, 10.0  # illustrative neutral mass, not precursor m/z
width = neutral_mass_da * ppm / 1e6
lo = np.searchsorted(mass, neutral_mass_da - width, side='left')
hi = np.searchsorted(mass, neutral_mass_da + width, side='right')
fp = np.unpackbits(packed[lo:hi], axis=1, bitorder='big')[:, :len(selection)]
print('candidate window:', lo, hi, 'decoded shape:', fp.shape)
```

Memory mapping keeps the 378 MB packed matrix on disk. Unpacking all 436,389 rows at once creates about 3 GB of uint8 bits before additional copies, so decode only the rows you need. Change `root` for local experiments.

`selection` does **not** index the already selected packed matrix. It indexes the full descriptor vector used when fingerprinting new structures: Morgan radius 2 (4,096), Morgan radius 3 (4,096), RDKit path fingerprint (2,048; maxPath 6), then MACCS (167). Select those columns before comparison. Preserve RDKit version and normalization choices. The consumer's decoding uses NumPy's big-endian bit order and discards six padding bits.

The pickle metadata is optional for the numerical example. Deserialize it only from a trusted source in the matching NumPy environment; pickle is executable serialization. The file is not a CSV and Kaggle's table preview cannot describe its structure for you.

### Coverage and identity limits

COCONUT is a natural-products resource, not an exhaustive chemical universe. A correct structure may be absent, excluded by the snapshot's mass range, or missed because of adduct interpretation or normalization. Molecular fingerprints do not uniquely identify stereochemistry. Evaluate coverage separately from ranking and use the official competition identity normalization when scoring or deduplicating predictions. The exact original download date and historical generation runtime are not embedded in a complete release manifest.

### Source, license and integrity

Source: [COCONUT — COlleCtion of Open Natural prodUcTs](https://coconut.naturalproducts.net/). Preserve COCONUT attribution and cite the upstream release/publication used by your experiment. The existing Kaggle license is **CC BY 4.0**.

Two small companion files were downloaded from version 2 and hashed on October 7, 2026:

- `coco_mass.npy`: `2b2af92c3185fa8cd52a4a3e3e7fd7eda4d94e8b9402662a3a4c55ffb13c6e5c`
- `fp_bits.npy`: `a61e372fc41091bf5c7467e08134081266262665077cb9e2c56d73e4887f3013`

These hashes certify those two files, not the full candidate bank. Companion resources: [FPNet v2](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v2), [FPNet v4](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v4), and [ranker features](https://www.kaggle.com/datasets/prvsiyan/casmi26-ranker-features).

### Project notebook and experiment history

[Analog Propagation — CASMI 2026 baseline](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) provides the public FPNet/preprocessing and rank-feature reference. Version 32 was checked on October 7, 2026; its `rank_features` definition matches the feature order described here. The baseline directly attaches the v2 model, COCONUT and ranker datasets; adapt and validate the model branch explicitly when using v4.

Public development records, experiment limitations and reproduction notes: [Enveda CASMI 2026 on GitHub](https://github.com/cubres/enveda-casmi-2026). Pin the relevant source commit and dataset version together when reproducing a run.
