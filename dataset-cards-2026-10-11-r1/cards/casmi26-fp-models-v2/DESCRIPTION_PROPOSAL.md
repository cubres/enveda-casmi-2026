## What it is and intended use

This dataset holds two spectrum-to-fingerprint checkpoints for the CASMI 2026 molecular-identification pipeline. The models turn MS/MS evidence into logits over a 6,930-bit molecular fingerprint, and a candidate structure can then be scored against those logits. The bundle contains checkpoints only: it has no complete preprocessing package and no standalone inference application.

## Contents

| File | Bytes | Recorded training step | Output bits | Width / layers | What it holds |
|---|---:|---:|---:|---|---|
| `fp_single_s2.pt` | 144,110,255 | 20,000 | 6,930 | 512 / 6 | Single-spectrum checkpoint |
| `fp_merged_m1.pt` | 144,110,255 | 24,000 | 6,930 | 512 / 6 | Merged-spectrum checkpoint |

Total size: 288,220,510 bytes. Step, output bits, width and layers come from checkpoint metadata, as recorded in the existing card. A later recorded step is not evidence of better generalization. The similarly named `prvsiyan/casmi26-fp-models-v4` bundle contains different serialized checkpoints in four files, so a matching file name is not enough to swap releases.

## How it was produced

The card states that the file inventory and binary headers were checked on October 7, 2026. It does not document a training split, an upstream corpus snapshot or a held-out evaluation, and the checkpoint metadata does not establish one. No standalone leaderboard score is reported; the assets are meant to be evaluated within the full candidate-generation and ranking pipeline.

## How to load it

Start with the exact data version linked below. The release suffix in the slug is not the Kaggle data-version number. The size check catches an accidental v2/v4 swap even when the file name matches; it is not a cryptographic integrity check.

```python
from pathlib import Path
import torch

root = Path("/kaggle/input/casmi26-fp-models-v2")  # change only for your local download
expected_bytes = {'fp_merged_m1.pt': 144110255, 'fp_single_s2.pt': 144110255}
for name, size in expected_bytes.items():
    path = root / name
    if not path.is_file() or path.stat().st_size != size:
        raise ValueError("Dataset version or file inventory does not match this card")

# Inspect one checkpoint at a time; do not load the whole bundle simultaneously.
ck = torch.load(root / "fp_single_s2.pt", map_location="cpu", weights_only=True)
if not isinstance(ck, dict) or not {"model", "nbits", "d", "layers"}.issubset(ck):
    raise ValueError("Checkpoint metadata schema differs from the prior card")
if (ck["nbits"], ck["d"], ck["layers"]) != (6930, 512, 6):
    raise ValueError("Checkpoint architecture differs from the prior card")
print("Metadata contract checked; inference and performance remain unevaluated")
```

Use a PyTorch release that supports `weights_only=True`. A failed restricted load is a stop signal: do not retry with unrestricted deserialization. This is a proposed local inspection recipe, not a new execution on the live checkpoint bytes. Architecture values above come from the prior owner card; verify them on your own pinned download. Reconstruct the matching FPNet, preprocessing and fingerprint-column order from the consuming notebook before inference. A matching shape alone cannot establish descriptor compatibility.

### Compatibility

- A 6,930-column fingerprint matches training only if its descriptor definitions and column order match. The baseline builds Morgan radius 2 (4,096 bits), Morgan radius 3 (4,096 bits), an RDKit path fingerprint (2,048 bits, maxPath 6) and MACCS (167 bits), then selects the indices in `fp_bits.npy` from the companion COCONUT dataset. Pin RDKit when rebuilding descriptors.
- Keep the matching peak filtering, intensity transform, neutral-loss encoding, adduct vocabulary, instrument-family mapping, collision-energy treatment and spectrum-merging rules.
- The checkpoints return logits. A sigmoid gives bit probabilities, not a calibrated probability that a candidate is correct. The dot product of a candidate's binary fingerprint and the logits is a ranking score under an independent-bit model.

## Licence and provenance

Published bundle licence metadata: CC-BY-NC-SA-4.0 (unchanged). The earlier owner card treats these checkpoints as trained on CASMI 2026 competition training data and states that training data is CC BY-NC 4.0; this refresh did not verify a training-data manifest. The bundle's published share-alike label is distinct from that stated upstream CC BY-NC licence and is not inferred from it. A bundle label does not establish every source's terms or grant additional rights. Check upstream terms and competition rules before retraining or redistributing derived artefacts. Public development records: https://github.com/cubres/enveda-casmi-2026.

## Attribution and citation

No citation supplied by the dataset owner. The public reference notebook is the Analog Propagation CASMI 2026 baseline (kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline), which the card names as the FPNet and preprocessing reference (version 32, checked October 7, 2026). The card states that this notebook attaches the v2 model, COCONUT and ranker datasets directly.

## Changelog

Version 1, the only Kaggle data version recorded, initial release (2026-09-16). Kaggle data version numbers are separate from the release suffix in the title.

## Exact data version and verification scope

This card is bound to [Kaggle data version 1](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v2/versions/1), numeric dataset id `12054715`, captured on 2026-10-11T19:35:12.585367+00:00. Dataset title, slug, licence metadata and public visibility are unchanged. The versioned API listed 2 files totalling 288,220,510 uncompressed bytes. No `MANIFEST.json` is listed; no current payload SHA256 was obtained. Existing October 7 header/hash statements above are historical observations, not this refresh's byte verification. A manifest-based flatpack verifier therefore does not apply to this release as-is.

[Existing campaign notebook](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) · [Public campaign experiments and reproduction notes](https://github.com/cubres/enveda-casmi-2026). The notebook's complete recipe and official result are separate from a standalone dataset's usefulness; this refresh supplies no new score or compatibility claim. Version-bound file inventories are available with the reviewed card package on GitHub after publication.
