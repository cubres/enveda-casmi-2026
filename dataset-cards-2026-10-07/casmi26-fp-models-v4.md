## Four spectrum-to-fingerprint checkpoints for ensemble experiments

This release groups merged-spectrum and single-spectrum FPNet checkpoints for CASMI26. It is useful for testing which spectrum representation contributes complementary candidate-ranking evidence. The files alone do not include an inference script, input preprocessing, or a candidate database.

### Files — Kaggle data version 1

| File | Bytes | Role identified by the release filename |
|---|---:|---|
| `fp_merged_m1.pt` | 432,339,069 | First merged-spectrum checkpoint |
| `fp_merged_m2.pt` | 432,339,069 | Second merged-spectrum checkpoint |
| `fp_single_s2.pt` | 432,339,069 | Single-spectrum checkpoint |
| `fp_single_aug.pt` | 432,339,414 | Augmented single-spectrum checkpoint |

Every inspected checkpoint records **6,930 output bits, width 512, and 6 layers**. The filenames describe intended roles; they are not independent performance measurements or proof of non-overlapping training data. These files differ in size and serialized metadata from the [two-checkpoint v2 bundle](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v2), even when filenames match. Pin the dataset release as well as the filename.

### Inspect before composing an ensemble

```python
from pathlib import Path
import torch

root = Path('/kaggle/input/casmi26-fp-models-v4')
for path in sorted(root.glob('*.pt')):
    ck = torch.load(path, map_location='cpu', weights_only=True)
    print(path.name, {k: ck[k] for k in ('nbits', 'd', 'layers')})
    print('state-dict entries:', len(ck['model']))
    assert ck['nbits'] == 6930
    del ck
```

This is a checkpoint-inspection example, not an executable inference pipeline. Use a PyTorch release supporting the restricted `weights_only=True` loader. Loading one checkpoint at a time limits CPU memory pressure. For local use, change `root` to the extracted directory.

```text
single-spectrum branch ----                            -> aligned fingerprint evidence -> candidate ranker
merged-spectrum branches --/
```

Reconstruct FPNet and **the same preprocessing** before inference. Preserve the peak transform, merging policy, adduct and instrument encodings, and collision-energy conventions. Model output columns must match the selected descriptor order in the [COCONUT companion](https://www.kaggle.com/datasets/prvsiyan/coconut-casmi26-candidates), not merely its 6,930-bit width.

### Useful experiments

Compare a single branch with an ensemble on the same frozen candidate lists, query identities and preprocessing. Change one branch or weight at a time; recompute candidate-relative ranker features consistently after changing model evidence. Record checkpoint filenames, dataset versions, seeds, runtime and per-query results. Group by molecular identity when splitting development data. The release has no independently verified fold manifest, so use a separately audited split before making unseen-structure claims.

### License and attribution

The existing Kaggle license is **CC0-1.0**. Retain the terms and attribution of upstream training resources when creating new assets; a bundle license label is not a complete training-data provenance manifest.

### Reproducibility and scope

This card documents the existing files; it does not change or retrain them. Dataset version numbers below refer to Kaggle data versions, not the release suffix in the dataset title. The file inventory and binary headers were checked on October 7, 2026. Checkpoint metadata inspection does not establish a training split, upstream corpus snapshot, or held-out evaluation result. These assets have no standalone leaderboard score: evaluate the complete candidate-generation and ranking pipeline, and keep development measurements separate from official submissions.

### Project notebook and experiment history

[Analog Propagation — CASMI 2026 baseline](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) provides the public FPNet/preprocessing and rank-feature reference. Version 32 was checked on October 7, 2026; its `rank_features` definition matches the feature order described here. The baseline directly attaches the v2 model, COCONUT and ranker datasets; adapt and validate the model branch explicitly when using v4.

Public development records, experiment limitations and reproduction notes: [Enveda CASMI 2026 on GitHub](https://github.com/cubres/enveda-casmi-2026). Pin the relevant source commit and dataset version together when reproducing a run.
