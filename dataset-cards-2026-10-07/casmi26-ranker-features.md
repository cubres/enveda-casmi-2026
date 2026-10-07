## Candidate-level training features for the CASMI26 ranker

This compact archive lets you retrain the baseline's gradient-boosted candidate classifier without regenerating all spectral, analog, fragmentation and fingerprint-model features. Each row is a candidate within a simulated molecular-identification query. It is a derived training resource, not a raw spectral library or a held-out competition test set.

### Current file — Kaggle data version 6

| Archive key | Shape | Dtype | Role in the baseline |
|---|---|---|---|
| `X` | `(142762, 31)` | float32 | Ordered candidate-level feature matrix |
| `Y` | `(142762,)` | float64 | Classifier training target |
| `M` | `(142762,)` | float64 | Simulation-regime selector used for mixture/sample weighting |
| `G` | `(142762,)` | int64 | Integer grouping array; query/structure mapping is not documented in the archive |

The archive does not include column names, a complete query manifest, checkpoint hashes, or a certified structure-level validation split. Keep a pinned copy of the feature-builder source with the archive; changing a model channel while retaining the same column count can silently change the feature distribution.

### Inspect the archive

```python
from pathlib import Path
import hashlib
import numpy as np

path = Path('/kaggle/input/casmi26-ranker-features/rank_train.npz')
expected = '41ccec87fba5f8ab255aaf5a723567f25bd766064265c5cc2b83ba2cf15f57f8'
assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
with np.load(path, allow_pickle=False) as z:
    print({name: (z[name].shape, str(z[name].dtype)) for name in z.files})
    assert set(z.files) == {'X', 'Y', 'M', 'G'}
    assert z['X'].shape == (142762, 31)
    X, y, regime, group = (z[name] for name in ('X', 'Y', 'M', 'G'))
```

That SHA256 was verified against a fresh download of data version 6 on October 7, 2026. Use a local extracted path outside Kaggle. The same digest is not a quality score.

### Feature order used by the baseline consumer

| Zero-based columns | Channel and ordering |
|---|---|
| 0–4 | Library similarity; normalized rank; candidate-list maximum; difference from maximum; positive-evidence indicator |
| 5–8 | Analog-propagation evidence; normalized rank; maximum; difference from maximum |
| 9–14 | Linear-weight analog evidence; best Tanimoto; Tanimoto to top analog; similarity-weighted mean Tanimoto; top analog's spectral similarity; log candidate count |
| 15–20 | Fingerprint logit dot-product z-score; rank; difference from maximum; bit-count-normalized score z-score; its rank; maximum-score indicator |
| 21–24 | Fragmentation explain-score; rank; difference from maximum; z-score |
| 25–30 | Library/model and analog/model agreement terms; best-library and best-analog agreement; best-library agreement times library maximum; correlation of library similarity with **negated** normalized model rank |

Ranks, z-scores, maxima, agreement and correlations are computed **within each candidate list**. Adding candidates changes existing rows' features; do not append raw candidates to a precomputed matrix and expect consistent rankings. Preserve the builder's rank/tie conventions and normalization.

### Train and evaluate honestly

The baseline fits `HistGradientBoostingClassifier` on `X` and `Y`, with regime-dependent weights from `M`, and averages multiple explicitly seeded fits. For a new experiment, first recover the mapping from `G` to query and structure identities from the matching generator, then keep complete candidate lists and molecular-identity groups together. The headers alone do not establish that mapping. Independently audit structure aliases and overlap with fingerprint-model training and spectral references before calling a split unseen-structure validation. The archive lacks enough provenance to certify those checks by itself.

Report retrieval coverage and full-query ranking metrics as well as classifier metrics. A held-out query with no correct candidate is still part of the ranking denominator. Retuning against this archive or the same development panel is training/development evidence, not an independent official score.

### Version history and license

Kaggle version 2 introduced a 25-feature layout. Later releases introduced the 31-feature layout and changed the fingerprint-model channel. Current version 6 is described in the original release notes as **“v5: 31 features, m1 merged-spectrum model channel”**: the internal recipe label and Kaggle version number are different. Avoid mixing an old feature archive with a newer inference recipe based only on a shared filename.

The existing Kaggle license is **CC0-1.0**. Companion assets: [fingerprint v2](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v2), [fingerprint v4](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v4), and [COCONUT candidates](https://www.kaggle.com/datasets/prvsiyan/coconut-casmi26-candidates). Upstream resource terms still matter when regenerating or redistributing derived data.

### Project notebook and experiment history

[Analog Propagation — CASMI 2026 baseline](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) provides the public FPNet/preprocessing and rank-feature reference. Version 32 was checked on October 7, 2026; its `rank_features` definition matches the feature order described here. The baseline directly attaches the v2 model, COCONUT and ranker datasets; adapt and validate the model branch explicitly when using v4.

Public development records, experiment limitations and reproduction notes: [Enveda CASMI 2026 on GitHub](https://github.com/cubres/enveda-casmi-2026). Pin the relevant source commit and dataset version together when reproducing a run.
