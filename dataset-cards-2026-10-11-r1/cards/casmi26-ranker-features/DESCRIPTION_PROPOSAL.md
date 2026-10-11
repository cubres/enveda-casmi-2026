## What it is and intended use

A compact archive of candidate-level training features for the CASMI 2026 baseline's gradient-boosted candidate classifier. Each row is one candidate within a simulated molecular-identification query. It lets a user retrain that classifier without regenerating the spectral, analog, fragmentation and fingerprint-model features. It is a derived training resource, not a raw spectral library or a held-out competition test set.

## Contents

| File | Bytes | What it holds |
|---|---:|---|
| `rank_train.npz` | 9,553,020 | NumPy archive with four arrays: X, Y, M and G |

| Array | Shape | Dtype | Role |
|---|---|---|---|
| `X` | (142762, 31) | float32 | Ordered candidate-level feature matrix |
| `Y` | (142762,) | float64 | Classifier training target |
| `M` | (142762,) | float64 | Simulation-regime selector for weighting |
| `G` | (142762,) | int64 | Integer grouping array; the query mapping is not documented |

No column names, query manifest, checkpoint hashes or certified structure-level validation split are included. Feature groups (zero-based columns, as the card describes them):

| Columns | Channel |
|---|---|
| 0-4 | Library similarity, with rank, maximum, difference from maximum and positive-evidence indicator |
| 5-8 | Analog-propagation evidence, with rank, maximum and difference from maximum |
| 9-14 | Linear-weight analog evidence, Tanimoto statistics, top-analog spectral similarity, log candidate count |
| 15-20 | Fingerprint-logit dot-product z-score, rank, difference from maximum, bit-count-normalized score and rank, maximum indicator |
| 21-24 | Fragmentation explain-score: rank, difference from maximum, z-score |
| 25-30 | Agreement terms between library, analog and model channels; correlation with negated normalized model rank |

## How it was produced

The features come from the baseline's library, analog-propagation, fragmentation and fingerprint-model channels. Ranks, z-scores, maxima and correlations are computed within each candidate list, so adding candidates changes existing rows. The builder is not included; the card advises keeping a pinned copy of its source.

## How to load it

Inspect the numeric schema before using the archive for fitting. This example closes the archive and prints only shapes; it does not display labels, group values or query identifiers.

```python
from pathlib import Path
import numpy as np

path = Path("/kaggle/input/casmi26-ranker-features/rank_train.npz")
if path.stat().st_size != 9553020:
    raise ValueError("File size differs from the exact V6 live inventory")
with np.load(path, allow_pickle=False) as z:
    if set(z.files) != {"X", "Y", "M", "G"}:
        raise ValueError("Unexpected archive schema")
    X, y, regime, group = (z[k] for k in ("X", "Y", "M", "G"))
    contracts = ((X, (142762, 31), "float32"),
                 (y, (142762,), "float64"),
                 (regime, (142762,), "float64"),
                 (group, (142762,), "int64"))
    for array, shape, dtype in contracts:
        if array.shape != shape or array.dtype != np.dtype(dtype):
            raise ValueError("Array contract differs from the prior owner card")
        if not np.isfinite(array).all():
            raise ValueError("Nonfinite numeric array")
print("Shapes:", X.shape, y.shape, regime.shape, group.shape)
```

Shape/dtype expectations come from the prior owner card; this refresh did not download the NPZ. File size and a matching schema do not authenticate contents or validate a split. The recorded October 7 SHA256 below remains a historical file observation, not a new live-byte verification.

Keep complete candidate lists together when measuring ranking: ranks, maxima and z-scores depend on the list. `G` has an undocumented query mapping and must not be advertised as a certified molecule-disjoint split. An independent validation protocol needs the actual query-to-structure and initializer-exposure manifest, which this data version does not include. Do not call random candidate-row cross-validation an independent molecular-identification estimate.

The card gives the SHA-256 of the data-version-6 file as 41ccec87fba5f8ab255aaf5a723567f25bd766064265c5cc2b83ba2cf15f57f8, verified against a fresh download on October 7, 2026. The digest certifies the file, not its quality. The baseline fits a `HistGradientBoostingClassifier` on X and Y with regime weights from M. Keep complete candidate lists and molecular-identity groups together, and report coverage and full-query ranking metrics as well as classifier metrics.

## Licence and provenance

Licence: CC-BY-NC-SA-4.0. The archive is treated as derived from CASMI 2026 competition training data, which is distributed under CC BY-NC 4.0. Upstream resource terms still apply when regenerating or redistributing derived data.

## Attribution and citation

No citation supplied by the dataset owner. Reference notebook: kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline (version 32, checked October 7, 2026). Development records and reproduction notes: github.com/cubres/enveda-casmi-2026.

## Changelog

Current Kaggle data version 6. Release notes on the Kaggle version history:

- Version 1 (2026-09-15): initial release.
- Version 2 (2026-09-16): 25 features (adds fragmentation and model channels), trained on 819 molecules.
- Version 3 (2026-09-16): s2 model channel, tuned GBM, W1=0.50.
- Version 4 (2026-09-16): 31 features, combo model channel (merged and single).
- Version 5 (2026-09-17): 31 features with 50k-step merged-spectrum model channel.
- Version 6 (2026-09-17): release note reads "v5: 31 features, m1 merged-spectrum model channel". Labels and version numbers differ; do not mix archives with recipes by file name alone.

## Exact data version and verification scope

This card is bound to [Kaggle data version 6](https://www.kaggle.com/datasets/prvsiyan/casmi26-ranker-features/versions/6), numeric dataset id `12039490`, captured on 2026-10-11T19:35:15.842745+00:00. Dataset title, slug, licence metadata and public visibility are unchanged. The versioned API listed 1 files totalling 9,553,020 uncompressed bytes. No `MANIFEST.json` is listed; no current payload SHA256 was obtained. Existing October 7 header/hash statements above are historical observations, not this refresh's byte verification. A manifest-based flatpack verifier therefore does not apply to this release as-is.

[Existing campaign notebook](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) · [Public campaign experiments and reproduction notes](https://github.com/cubres/enveda-casmi-2026). The notebook's complete recipe and official result are separate from a standalone dataset's usefulness; this refresh supplies no new score or compatibility claim. Version-bound file inventories are available with the reviewed card package on GitHub after publication.
