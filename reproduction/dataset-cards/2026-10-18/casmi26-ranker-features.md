# CASMI26 candidate-ranker features: exact V6 and recovered builder

[Kaggle dataset V6](https://www.kaggle.com/datasets/prvsiyan/casmi26-ranker-features/versions/6), id **12039490**. Anonymous public access and the existing **CC BY-NC-SA 4.0** label were verified on 18 October 2026.

`rank_train.npz` contains **142,762 candidate rows and 31 features**. Recorded arrays are `X` float32 `(142762,31)`, `Y` float64 `(142762,)`, `M` float64 `(142762,)`, and `G` int64 `(142762,)`. The 9,553,020-byte archive's retained digest is `41ccec87fba5f8ab255aaf5a723567f25bd766064265c5cc2b83ba2cf15f57f8`. Freshly hashed retained copies agree; this card refresh did not redownload the public payload.

These are candidate-level training features, not a held-out query set. Within-query ranks, maxima, z-scores and correlations depend on the whole candidate list. A training row cannot be shuffled independently for a valid ranking evaluation. `G` is a grouping array, not by itself proof of structure-disjoint validation or absence of initializer exposure.

## Recovered feature-builder contract

The recovered source release contains [make_ranker3.py](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/ranker_lineage/original_sources/make_ranker3.py), [rankfeat.py](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/ranker_lineage/original_sources/rankfeat.py) and [casmi_core.py](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/ranker_lineage/original_sources/casmi_core.py). Stage these sources in a new working directory with the historical data layout described in the [ranker recipe](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/ranker_lineage/README.txt), then use:

```bash
python make_ranker3.py --model
```

The source writes `up_rank3/rank_train.npz` and `data/w1_v3.pkl`, not a fitted classifier. The twelve fingerprint-derived columns (15–20 and 25–30, zero-based) depend on `data/val_model_logits_combo.npy` and `data/hard_model_logits.npy`. `--model` enables their optional loading; it does not identify either historical producer. If the flag is absent, or if the corresponding cache is missing, those twelve columns are silently zero for that query set. It fits cross-validation classifiers to choose the simulation-regime weight. Its data preparation and cache expectations are documented in the [source release](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/README.md).

**Current reproduction boundary:** this invocation requires precomputed spectral/analog features, pool arrays and fingerprint logits. The original A-cache producer (`val_model_logits_combo.npy`, 250 × 6930) is not yet bound. The B-cache (`hard_model_logits.npy`, 569 × 6930) has several historical writers, so a matching filename does not identify its model channel. Their generator source, checkpoint hashes, query ordering and cache hashes must be resolved before claiming complete regeneration of the published archive. The command documents the recovered feature-builder contract, not a proven byte-exact historical invocation or regeneration. Do not substitute an unrelated later cache.

A local folder named `up_rank6` contains a different 39-column artifact. Its name does not identify this public **dataset version 6**, and it must not replace this 31-column contract. Existing release notes also use internal labels such as “v5”; bind the actual Kaggle version and bytes.

### Retained serving fit recipe

The separately recovered local serving generator fits eight classifiers in memory: regime weights `0.30` and `0.60`, each with seeds `0,1,2,3`. It uses `HistGradientBoostingClassifier(max_depth=6, max_iter=500, learning_rate=0.03, min_samples_leaf=80, l2_regularization=1.0, random_state=seed)` and `sample_weight=np.where(M == 0, weight, 1-weight)`. Scores are the mean of the eight `predict_proba(... )[:,1]` outputs. This is a retained local-source recipe, not a freshly version-bound native fit or an original standalone fit-and-save CLI. The generator itself contains publishing actions and must not be run as a training demo. A separately extracted executable would need to preserve these parameters and be labelled as a new extraction.

For a no-pickle numeric check:

```python
import numpy as np
with np.load("rank_train.npz", allow_pickle=False) as z:
    assert set(z.files) == {"X", "Y", "M", "G"}
    assert z["X"].shape == (142762, 31)
    assert all(np.isfinite(z[name]).all() for name in z.files)
```

This checks numeric structure, not training provenance, semantic column identity or generalization. No new ranking score is reported.

## License and attribution

The existing NC-SA bundle label is retained for the publisher's contributions. Third-party spectra, structures, features and checkpoints retain their applicable terms. The hosts' [training-data clarification](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/745072) permits qualifying open training-derived artifacts; it is not a blanket CC0 grant. The [weight-sharing requirement](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/748882) still requires original code and permitted data access for reused participant weights.

See [license scope](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/LICENSE-SCOPE.md), [attribution](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/ATTRIBUTION.md), the [Analog notebook](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) and [source repository](https://github.com/cubres/enveda-casmi-2026). Publishing a more detailed card alone does not complete the unresolved cache lineage.
