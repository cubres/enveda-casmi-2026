## What it is and intended use

A candidate bank of 436,389 natural-product structures from COCONUT 2.0, with neutral monoisotopic masses, selected molecular fingerprints and aligned identifiers. It supports candidate generation and fingerprint-based ranking. It contains neither query MS/MS spectra nor a ready-made competition submission.

## Contents

| File | Shape, dtype and size | What it holds |
|---|---|---|
| `coco_mass.npy` | (436389,), float64, 3,491,240 bytes | Neutral monoisotopic mass in daltons, sorted ascending |
| `coco_fp.npy` | (436389, 867), uint8, 378,349,391 bytes | Packed bits: 6,930 useful bits per row plus byte padding |
| `fp_bits.npy` | (6930,), int64, 55,568 bytes | Selected column indices into the concatenated descriptor vector |
| `coco_meta.pkl` | Python pickle, 41,450,156 bytes | Aligned structure identifiers and SMILES metadata used by the baseline |

Total size: 423,346,355 bytes. Row i must refer to the same molecule in every candidate array and in `coco_meta.pkl`; do not sort or filter one component independently. The card gives a mass range of 100.009519128 to 1299.7599298120003 Da.

## How it was produced

The source is COCONUT, COlleCtion of Open Natural prodUcTs (coconut.naturalproducts.net). Version 2 added the `fp_bits.npy` selection index. The card states that the complete mass array was checked as finite and ascending, and that the fingerprint matrix shape was verified from its binary header; it does not certify every structure or fingerprint row. The download date and generation runtime are not recorded in a release manifest.

The packed fingerprints are selected from a 10,407-column descriptor vector: Morgan radius 2 (4,096), Morgan radius 3 (4,096), RDKit path fingerprint (2,048, maxPath 6) and MACCS (167). The card states that `fp_bits.npy` indexes this full vector, not the packed matrix. Card-stated SHA-256 values for the two small companion files (version 2, hashed October 7, 2026): `coco_mass.npy` 2b2af92c3185fa8cd52a4a3e3e7fd7eda4d94e8b9402662a3a4c55ffb13c6e5c and `fp_bits.npy` a61e372fc41091bf5c7467e08134081266262665077cb9e2c56d73e4887f3013. These certify those two files only.

## How to load it

The following recipe uses numeric arrays only; it does not open `coco_meta.pkl`. Keep the four files from the same data version together. The expected shapes and dtypes are the prior owner card's contract, not a newly downloaded-payload attestation.

```python
from pathlib import Path
import numpy as np

root = Path("/kaggle/input/coconut-casmi26-candidates")  # or your local V2 folder
mass = np.load(root / "coco_mass.npy", mmap_mode="r", allow_pickle=False)
packed = np.load(root / "coco_fp.npy", mmap_mode="r", allow_pickle=False)
bits = np.load(root / "fp_bits.npy", allow_pickle=False)
if mass.shape != (436389,) or mass.dtype != np.dtype("float64"):
    raise ValueError("Unexpected mass-array contract")
if packed.shape != (436389, 867) or packed.dtype != np.dtype("uint8"):
    raise ValueError("Unexpected packed-fingerprint contract")
if bits.shape != (6930,) or bits.dtype != np.dtype("int64"):
    raise ValueError("Unexpected descriptor-index contract")
if not np.isfinite(mass).all() or np.any(mass[1:] < mass[:-1]):
    raise ValueError("searchsorted requires finite ascending masses")
if np.any(bits < 0) or np.any(bits >= 10407) or len(np.unique(bits)) != 6930:
    raise ValueError("Unexpected descriptor-column mapping")

neutral_mass = 300.0  # invented illustrative value, not a query
window = neutral_mass * 10e-6
lo = np.searchsorted(mass, neutral_mass - window, side="left")
hi = np.searchsorted(mass, neutral_mass + window, side="right")
# Both exact endpoints belong to the inclusive +/-10 ppm window.
selected_fp = np.unpackbits(packed[lo:hi], axis=1, bitorder="big")[:, :6930]
print("Selected numeric rows:", len(selected_fp), "columns:", selected_fp.shape[1])
```

Decode only the rows you need: the full unpacked matrix occupies about 3 GB as uint8. `fp_bits.npy` indexes the original 10,407-column descriptor vector, while the decoded packed rows already contain the selected 6,930 columns. Applying that selection again to the packed rows is incorrect. Never sort or filter the mass, fingerprint or metadata arrays independently. A neutral-mass window needs the query's correct adduct/polarity conversion; it is not a window over raw precursor m/z.

The inclusive endpoint behavior was checked separately on four invented masses, without downloading this dataset. The complete reproducible toy is linked in the campaign repository after reviewed publication; it is not a spectrum, hidden-query or coverage evaluation. `coco_meta.pkl` remains a trusted-source-only serialized object; this numerical recipe does not deserialize it.

Coverage limits: COCONUT is not exhaustive; a correct structure may be absent, outside the mass range or missed through adduct or normalization differences. Fingerprints do not identify stereochemistry; use the official competition identity normalization when scoring.

## Licence and provenance

Published dataset licence metadata: CC-BY-NC-SA-4.0 (unchanged). The earlier owner card states that structures, masses and metadata are COCONUT-derived (upstream CC BY 4.0), while `fp_bits.npy` and the packed fingerprint selection use the baseline FPNet's selected bits and treats those checkpoints as competition-training-derived (stated upstream CC BY-NC 4.0). This refresh did not verify that derivation or a source manifest. The published dataset's share-alike label is separate from those stated upstream labels; it is not implied by CC BY-NC. Check COCONUT and competition terms before reuse or redistribution; this card grants no additional rights.

## Attribution and citation

Preserve COCONUT attribution and cite the upstream COCONUT release or publication used; the dataset owner supplied no paper citation. Companion resources: the FPNet v2 and v4 bundles and the ranker features dataset.

## Changelog

Version 2 (2026-09-15): added the fingerprint bit-selection index `fp_bits.npy`. Version 1 (2026-09-15): initial release. The card reports no other revisions.

## Exact data version and verification scope

This card is bound to [Kaggle data version 2](https://www.kaggle.com/datasets/prvsiyan/coconut-casmi26-candidates/versions/2), numeric dataset id `12039473`, captured on 2026-10-11T19:35:14.518136+00:00. Dataset title, slug, licence metadata and public visibility are unchanged. The versioned API listed 4 files totalling 423,346,355 uncompressed bytes. No `MANIFEST.json` is listed; no current payload SHA256 was obtained. Existing October 7 header/hash statements above are historical observations, not this refresh's byte verification. A manifest-based flatpack verifier therefore does not apply to this release as-is.

[Existing campaign notebook](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) · [Public campaign experiments and reproduction notes](https://github.com/cubres/enveda-casmi-2026). The notebook's complete recipe and official result are separate from a standalone dataset's usefulness; this refresh supplies no new score or compatibility claim. Version-bound file inventories are available with the reviewed card package on GitHub after publication.
