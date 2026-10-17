# CASMI26 candidate pool: training structures + COCONUT, 6,930 selected bits

This V1 dataset supplies the aligned candidate structures, exact molecular masses and packed fingerprints consumed by the original single-spectrum S2 and merged-spectrum M1 FPNet trainers. It has **711,705 candidates and 6,930 effective fingerprint bits**. These three files form one ordered bank; do not combine one version's fingerprint rows with another version's metadata.

[Dataset V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-pool/versions/1) · [Prepared spectra V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-spec-fp/versions/1) · [Original source and commands](https://github.com/cubres/enveda-casmi-2026/tree/main/reproduction/legacy-v2) · [Competition notebook](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline)

## Exact files and layout

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `pool_fp.npy` | 617,048,363 | `7e41ed56d1e74d7eeb1411135d78e43dcf9fc6d4c61ce9cef3e49fb97c6f6768` |
| `pool_mass.npy` | 5,693,768 | `0d28d5c288201e3598ba2fffea7f3d7284e397341ab0d72e5111b4cc67dabd1e` |
| `pool_meta.pkl` | 64,843,052 | `069c01f0d42affd7b46c5d5b7c56b7eb20e4ca0a8806a0b2e0772c4b1de049f5` |

`pool_fp.npy` is `uint8[711705,867]`, with packed big-endian bits and six padding bits at the end of each row. `pool_mass.npy` is `float64[711705]` in the same order. `pool_meta.pkl` contains aligned `keys`, `smiles`, `src`, `npl` and integer `nbits=6930`. The original builder sorts by exact mass; metadata includes training/COCONUT source flags and NP-likeness values. Treat pickle as executable serialization: verify the exact file hash before using trusted original code, and do not load an arbitrary replacement pickle.

The selected bit definitions are the exact ordered `fp_bits.npy` from the companion prepared-spectra dataset: Morgan radius2/4096, Morgan radius3/4096, RDKit path/2048 with maxPath6 and MACCS/167, followed by the original 0.005–0.995 frequency selection. That selection uses all retained training structures. This 6,930-bit bank matches the original S2/M1 architecture; the separate 10,395-bit full bank is incompatible with those output columns.

## Small mass-window example

After verifying the three file hashes against the table, inspect a small mass window without loading the full bank or pickle metadata:

```python
from pathlib import Path
import numpy as np
root = Path("/path/to/casmi26-pool-v1")
fp = np.load(root / "pool_fp.npy", mmap_mode="r", allow_pickle=False)
mass = np.load(root / "pool_mass.npy", mmap_mode="r", allow_pickle=False)
assert fp.shape == (711705, 867) and fp.dtype == np.uint8
assert mass.shape == (711705,) and mass.dtype == np.float64
lo, hi = np.searchsorted(mass, [299.99, 300.01])  # illustrative neutral-mass window
assert 0 <= hi - lo <= 10000
candidate_bits = np.unpackbits(fp[lo:hi], axis=1)[:, :6930]
print(candidate_bits.shape)
```

This demonstrates aligned data access, not candidate accuracy or a leaderboard score. Precursor/adduct conversion and calibrated mass tolerance belong to the consuming scientific pipeline.

## Preparation and original training

The public original `build_pool.py` combines training fingerprints/metadata with additional cleaned COCONUT structures, computes their fingerprints and masses, filters invalid/out-of-range mass rows and sorts the aligned arrays. See the [preparation recipe](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/public_source/README.txt). The separate flat-cache/selected-export bridge is explicitly reconstructed; original builder source remains unchanged.

Using these exact files at the working-directory root and the [supplied prepared spectra](https://www.kaggle.com/datasets/prvsiyan/casmi26-spec-fp/versions/1) at the documented `ds/` and `up_train/` paths removes the need to regenerate the historical pool or split before running the published [S2/M1 commands](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/casmi26-fp-models-v2.md). The original trainers seed Torch after model initialization, so accessible source and exact inputs do not promise byte-identical historical checkpoint weights. Historical ranker-feature producer provenance remains a separate question.

## Origins, attribution and component terms — Other (specified in description)

The candidate rows are a union of competition-provided training structures and the COCONUT September 2026 snapshot. The exact retained cleaned snapshot has 462,028 rows; 25,639 keys overlap the training structure table, and 436,389 additional COCONUT keys enter the pool. The original builder gives training SMILES precedence for overlapping keys. Of 275,810 training structures, 275,316 survive the pool's original mass/validity filtering. The bounded release audit accounted for every retained pool key/SMILES pair and checked all legacy/full pool rows in exact order. It did not rerun chemical normalization, every fingerprint, omission filters or mass-tie sorting.

The competition hosts' [provided-training-data clarification](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/745072) permits qualifying artifacts from the open training compilation; the competition noncommercial provision was intended for test data. This release relies on that permission for the provided-train-derived components. Original library contributors retain their applicable rights and terms; consult the [competition training-data sources](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/data), retain source notices and do not treat this as a blanket waiver.

COCONUT's curated dataset is [CC0 according to its original publisher](https://coconut.naturalproducts.net/about). Credit its authors and retain the snapshot provenance: `coconut_csv-09-2026.csv` SHA256 `1360a7f38a134328c8759aa8a6762a24cccdc974d6fce51db710dd1283d9da75`; the derived cleaned parquet SHA256 is `7bbc682c4e99f2df837be66de3ad1effb5e5c3c452c467c7c5fc07481c28b7b5`. The original cleaning source keeps the largest fragment, removes hydrogens, sanitizes, filters heavy-atom/mass/charge ranges and keeps one key after descending NP-likeness sorting. The release identifies the retained historical source bytes; it does not claim an unverified current COCONUT download has identical content.

The uploader contributes preparation, array organization, fingerprints, masks and selection metadata. Those contributions are supplied for reproducing the CASMI workflow within the host-permitted training-artifact scope and do not relicense underlying molecular records or spectra. The metadata label **Other** points to these component terms; neither blanket CC0 nor a blanket noncommercial restriction is asserted over every source. Software licenses apply to code, not automatically to underlying data. This dataset contains no competition test data and grants no rights over proprietary sources. See [component attribution](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/ATTRIBUTION.md) and [source scope](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/LICENSE-SCOPE.md).
