# CASMI26 full fingerprint inputs: 10,395 bits and explicit training roles

This V1 dataset provides a **711,705-candidate, 10,395-bit** bank plus training-structure metadata, the exact feature mask, saved optimizer bit counts and explicit four-role assignments. It supports the full-fingerprint training workflow. It contains neither raw spectra nor trained checkpoints; the prepared spectra are supplied separately by [CASMI26 spec-fp V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-spec-fp/versions/1).

[Exact dataset V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-full-fingerprint-inputs/versions/1) · [Original preparation source](https://github.com/cubres/enveda-casmi-2026/tree/main/reproduction/legacy-v2) · [Selected V6 training source](https://github.com/cubres/enveda-casmi-2026/tree/main/reproduction/selected-v6-training/2026-10-18) · [Competition notebook](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline)

## Exact files and schemas

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `pool_fp.npy` | 925,216,628 | `84afb2d17d567359963f1941c4c8b20523770aad4167ccc0bd715530360611e0` |
| `fp_bits.npy` | 83,288 | `f771cb6aa87a418b06d9abfbdac0c1759040afb955b9dfa59e8932105a65bdc6` |
| `fp_meta.pkl` | 17,095,875 | `88411e98cec6f862f7b121dbc27b807e5e18782416219fe2b11566deb3254132` |
| `pool_meta.pkl` | 64,843,052 | `53c276a6625f38c90d93e3a8c23c25a2d08712754358b1160f6683e42a922324` |
| `pool_mass.npy` | 5,693,768 | `0d28d5c288201e3598ba2fffea7f3d7284e397341ab0d72e5111b4cc67dabd1e` |
| `roles_by_structure.b64` | 55,913 | `fe654a3f5f655df3897a344ca222e01a9f555a7dfd22a786e6cb32b126c76049` |
| `optimizer_bit_counts.npy` | 83,384 | `4d874c910de699a0fa030a40d6bcded08d78c236f44aeefe0101f2ac20122193` |
| `FULL_FINGERPRINT_MANIFEST.json` | 3,347 | `5b08ca4b830de1558be4ce568a10f0997b5fa2fe875a872dcd6a216f901fd9ef` |
| `README.md` | 907 | `582dbf22a1223d3a2cecf7b0b2d7124c680fddbd13596b8958fe41c97ed97699` |

`pool_fp.npy` is `uint8[711705,1300]`: 10,395 effective packed bits and five padding bits per row. `pool_mass.npy` is aligned `float64[711705]`. `pool_meta.pkl` holds `keys`, `smiles`, `src`, `npl`, and `nbits=10395`; all candidate keys and SMILES match the separate legacy bank in exact order. `fp_meta.pkl` holds 275,810 ordered training keys/SMILES and `nbits=10395`; these are training-structure rows, not all candidate-pool rows.

`fp_bits.npy` is `int64[10395]`. `optimizer_bit_counts.npy` is `int64[10407]`; the saved mask exactly selects counts strictly between 0 and 219,470. The original preparation source specifies optimizer-only bit fitting. The bounded release check verified saved counts→mask equality, not an independent recount of optimizer rows.

`roles_by_structure.b64` stores base64-encoded, zlib-compressed, two-bit role codes packed most-significant bit first. The original training reader decodes one `uint8` role per training-structure row; base64 decoding alone is insufficient. Role values are: 0 optimizer (219,470), 1 checkpoint selection (27,204), 2 fusion selection (13,682), and 3 final evaluation (15,454). The file SHA in the table includes its trailing newline; the decoded byte SHA is `4d7b366293225a1ae67dfc0306480129b9ac1351a6d8581f0be40a269bdaff86`. These author-created assignments are distinct from the competition's own data partition and from legacy `spec.is_val`. Do not index the role array by candidate-pool position or optimize against reserved evaluation roles.

The role source groups training structures using canonical chemistry and public MassSpecGym reference structures, hashes groups into an 80/10/5/5 partition, and applies explicit historical-use overrides. The [original role-generation source](https://github.com/cubres/enveda-casmi-2026/tree/main/reproduction/full-fingerprint-preparation/2026-10-18/role-sources) records those overrides; this is not a claim that prior-used examples are untouched. No additional MassSpecGym spectra or novel MassSpecGym candidate rows are copied into these nine files. Supplying the exact role file makes the documented trainer input available without regenerating the historical partition.

## Small numerical contract check

Verify exact file hashes before use. The following reads only numeric arrays, does not load pickle or decode roles, and checks the saved feature-selection rule:

```python
from pathlib import Path
import numpy as np
root = Path("/path/to/casmi26-full-fingerprint-inputs-v1")
fp = np.load(root / "pool_fp.npy", mmap_mode="r", allow_pickle=False)
bits = np.load(root / "fp_bits.npy", allow_pickle=False)
counts = np.load(root / "optimizer_bit_counts.npy", allow_pickle=False)
assert fp.shape == (711705, 1300) and fp.dtype == np.uint8
assert bits.shape == (10395,) and counts.shape == (10407,)
assert np.array_equal(bits, np.flatnonzero((counts > 0) & (counts < 219470)))
print("Saved 10,395-bit contract matches")
```

This is an integrity/shape demonstration, not a scientific evaluation. A checkpoint must use the exact same fingerprint definition, column ordering, preprocessing and model source. Legacy 6,930-output S2/M1 checkpoints cannot consume this bank.

## Reproduction and limits

The public original full-fingerprint preparation builder binds the raw 10,407-bit training matrix, training structures, prepared spectra, existing pool order and supplied role assignment. The selected V6 source release separately provides its actual trainer, structure-uniform sampler, wrapper, model and commands; it must not be conflated with older legacy S2/M1 training. Preserve the supplied prepared spectrum SHA `99dbf966d2607e2da8085a6550206a71fc912d2c90b9555a725a2569e4af4500` and the complete source/input contracts.

The release audit verified every candidate key/SMILES origin and the exact full/legacy order, matched the full training metadata to the provided-train metadata, and checked saved count/mask equality. It did not rerun models, training, ranking assays, full chemical generation, role decoding or official evaluation. Native run completion, historical checkpoint reproducibility and official competition scores are separate evidence; this dataset claims no score.

The contributor-created role metadata and counts are derived selection artifacts. Their public availability does not make evaluation roles eligible for fitting, nor assert that the original training outcome is byte-deterministic.

## Origins, attribution and component terms — Other (specified in description)

The candidate rows are a union of competition-provided training structures and the COCONUT September 2026 snapshot. The exact retained cleaned snapshot has 462,028 rows; 25,639 keys overlap the training structure table, and 436,389 additional COCONUT keys enter the pool. The original builder gives training SMILES precedence for overlapping keys. Of 275,810 training structures, 275,316 survive the pool's original mass/validity filtering. The bounded release audit accounted for every retained pool key/SMILES pair and checked all legacy/full pool rows in exact order. It did not rerun chemical normalization, every fingerprint, omission filters or mass-tie sorting.

The competition hosts' [provided-training-data clarification](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/745072) permits qualifying artifacts from the open training compilation; the competition noncommercial provision was intended for test data. This release relies on that permission for the provided-train-derived components. Original library contributors retain their applicable rights and terms; consult the [competition training-data sources](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/data), retain source notices and do not treat this as a blanket waiver.

COCONUT's curated dataset is [CC0 according to its original publisher](https://coconut.naturalproducts.net/about). Credit its authors and retain the snapshot provenance: `coconut_csv-09-2026.csv` SHA256 `1360a7f38a134328c8759aa8a6762a24cccdc974d6fce51db710dd1283d9da75`; the derived cleaned parquet SHA256 is `7bbc682c4e99f2df837be66de3ad1effb5e5c3c452c467c7c5fc07481c28b7b5`. The original cleaning source keeps the largest fragment, removes hydrogens, sanitizes, filters heavy-atom/mass/charge ranges and keeps one key after descending NP-likeness sorting. The release identifies the retained historical source bytes; it does not claim an unverified current COCONUT download has identical content.

The uploader contributes preparation, array organization, fingerprints, masks and selection metadata. Those contributions are supplied for reproducing the CASMI workflow within the host-permitted training-artifact scope and do not relicense underlying molecular records or spectra. The metadata label **Other** points to these component terms; neither blanket CC0 nor a blanket noncommercial restriction is asserted over every source. Software licenses apply to code, not automatically to underlying data. This dataset contains no competition test data and grants no rights over proprietary sources. See [component attribution](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/ATTRIBUTION.md) and [source scope](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/LICENSE-SCOPE.md).
