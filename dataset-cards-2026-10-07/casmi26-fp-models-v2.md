## Two spectrum-to-fingerprint checkpoints, ready to inspect

This bundle supplies a single-spectrum checkpoint and a merged-spectrum checkpoint for the CASMI26 molecular-identification pipeline. The models turn MS/MS evidence into molecular-fingerprint logits; a candidate structure can then be scored against those logits. The bundle contains checkpoints, rather than a complete preprocessing package or standalone inference application.

```text
MS/MS spectra -> matching FPNet preprocessing -> 6,930 logits
candidate structures -> the same selected fingerprint bits -> candidate scores
```

### Files — Kaggle data version 1

| File | Bytes | Recorded training step | Output bits | Width / layers |
|---|---:|---:|---:|---|
| `fp_single_s2.pt` | 144,110,255 | 20,000 | 6,930 | 512 / 6 |
| `fp_merged_m1.pt` | 144,110,255 | 24,000 | 6,930 | 512 / 6 |

The steps and dimensions above come from the checkpoint metadata. A later recorded step is not evidence of better generalization. The similarly named [v4 bundle](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v4) contains different serialized checkpoints and four files; do not silently swap releases because a filename matches.

### Inspect a checkpoint on Kaggle

Attach this dataset with **Add Input**. This example only inspects the checkpoint contract; reconstruct FPNet and its preprocessing from the consuming notebook before running inference.

```python
from pathlib import Path
import torch

root = Path('/kaggle/input/casmi26-fp-models-v2')
ck = torch.load(root / 'fp_single_s2.pt', map_location='cpu', weights_only=True)
print({k: ck[k] for k in ('nbits', 'd', 'layers', 'step')})
print('state-dict entries:', len(ck['model']))
assert ck['nbits'] == 6930
```

Use a PyTorch release supporting `weights_only=True`. Keep that restricted loader; do not switch to unrestricted pickle loading to silence an incompatibility. On a local machine, set `root` to your extracted directory.

### Compatibility that matters

A 6,930-column fingerprint is compatible only if its descriptor definitions **and column order** match training. The [COCONUT companion dataset](https://www.kaggle.com/datasets/prvsiyan/coconut-casmi26-candidates) includes `fp_bits.npy`, the selection indices, plus a packed candidate matrix. The baseline fingerprint construction concatenates Morgan radius 2 (4,096 bits), Morgan radius 3 (4,096), RDKit path fingerprint (2,048; maxPath 6), and MACCS (167), then selects those indices. Preserve that order and pin RDKit when reconstructing descriptors.

Also retain the matching peak filtering, intensity transform, neutral-loss encoding, adduct vocabulary, instrument-family mapping, collision-energy treatment, and spectrum-merging rules. These checkpoints return logits; applying sigmoid produces bit probabilities, not a calibrated probability that a candidate molecule is correct. The dot product of a candidate's binary fingerprint and the logits is a ranking score under an independent-bit model.

### License and attribution

Kaggle's current metadata for [dataset version 1](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v2/versions/1) reports **CC BY-NC-SA 4.0** (checked October 20, 2026). This published label does not establish rights to upstream training data or alter competition restrictions. The reproduction source-code grant is separately scoped and excludes weights and data; see the [public provenance audit](../reproduction/legacy-v2/PUBLIC_REPRODUCIBILITY_AUDIT_2026-10-20.md).

### Reproducibility and scope

This card documents the existing files; it does not change or retrain them. Dataset version numbers below refer to Kaggle data versions, not the release suffix in the dataset title. The file inventory and binary headers were checked on October 7, 2026. Checkpoint metadata inspection does not establish a training split, upstream corpus snapshot, or held-out evaluation result. These assets have no standalone leaderboard score: evaluate the complete candidate-generation and ranking pipeline, and keep development measurements separate from official submissions.

### Project notebook and experiment history

[Analog Propagation — CASMI 2026 baseline](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) provides the public FPNet/preprocessing and rank-feature reference. Version 32 was checked on October 7, 2026; its `rank_features` definition matches the feature order described here. The baseline directly attaches the v2 model, COCONUT and ranker datasets; adapt and validate the model branch explicitly when using v4.

Public development records, experiment limitations and reproduction notes: [Enveda CASMI 2026 on GitHub](https://github.com/cubres/enveda-casmi-2026). Pin the relevant source commit and dataset version together when reproducing a run.
