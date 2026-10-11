## What it is and intended use

This dataset groups four spectrum-to-fingerprint checkpoints for the CASMI 2026 pipeline: merged-spectrum and single-spectrum FPNet checkpoints. It is useful for testing which spectrum representation adds complementary candidate-ranking evidence. The files alone do not include an inference script, input preprocessing or a candidate database.

## Contents

| File | Bytes | Role identified by the file name only |
|---|---:|---|
| `fp_merged_m1.pt` | 432,339,069 | First merged-spectrum checkpoint |
| `fp_merged_m2.pt` | 432,339,069 | Second merged-spectrum checkpoint |
| `fp_single_s2.pt` | 432,339,069 | Single-spectrum checkpoint |
| `fp_single_aug.pt` | 432,339,414 | Augmented single-spectrum checkpoint |

Total size: 1,729,356,621 bytes. The card reports that every inspected checkpoint records 6,930 output bits, width 512 and 6 layers. The file names describe intended roles; they are not performance measurements or proof of non-overlapping training data. These files differ in size and serialized metadata from the two-checkpoint `prvsiyan/casmi26-fp-models-v2` bundle even where names match, so pin the dataset release as well as the file name.

## How it was produced

The card states that the file inventory and binary headers were checked on October 7, 2026. It does not establish a training split, an upstream corpus snapshot or a held-out evaluation, and it says the release has no independently verified fold manifest. No standalone leaderboard score is reported for these checkpoints.

## How to load it

Start with the exact data version linked below. The release suffix in the slug is not the Kaggle data-version number. The size check catches an accidental v2/v4 swap even when the file name matches; it is not a cryptographic integrity check.

```python
from pathlib import Path
import torch

root = Path("/kaggle/input/casmi26-fp-models-v4")  # change only for your local download
expected_bytes = {'fp_merged_m1.pt': 432339069, 'fp_merged_m2.pt': 432339069, 'fp_single_aug.pt': 432339414, 'fp_single_s2.pt': 432339069}
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

### Compatibility and use

- Reconstruct FPNet and the same preprocessing before inference: peak transform, merging policy, adduct and instrument encodings and collision-energy conventions.
- Model output columns must match the descriptor order in the companion COCONUT dataset's `fp_bits.npy`, not merely its 6,930-bit width.
- For an ensemble experiment, compare a single branch with the ensemble on the same frozen candidate lists, query identities and preprocessing. Change one branch or weight at a time, recompute candidate-relative ranker features after changing model evidence, and record file names, dataset versions, seeds and per-query results.
- Group by molecular identity when splitting development data.

## Licence and provenance

Published bundle licence metadata: CC-BY-NC-SA-4.0 (unchanged). The earlier owner card treats these checkpoints as trained on CASMI 2026 competition training data and states that training data is CC BY-NC 4.0; this refresh did not verify a training-data manifest. The bundle's published share-alike label is distinct from that stated upstream CC BY-NC licence and is not inferred from it. A bundle label does not establish every source's terms or grant additional rights. Check upstream terms and competition rules before retraining or redistributing derived artefacts. Public development records: https://github.com/cubres/enveda-casmi-2026.

## Attribution and citation

No citation supplied by the dataset owner. The Analog Propagation CASMI 2026 baseline notebook (kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) is the FPNet and rank-feature reference named in the card. The card says that notebook attaches the v2 model directly, so the v4 model branch needs explicit adaptation and validation.

## Changelog

Version 1, the only Kaggle data version recorded, initial release (2026-09-18). The card's checks of October 7, 2026 are described above. Kaggle data version numbers are separate from the release suffix in the title.

## Exact data version and verification scope

This card is bound to [Kaggle data version 1](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v4/versions/1), numeric dataset id `12078661`, captured on 2026-10-11T19:35:13.540433+00:00. Dataset title, slug, licence metadata and public visibility are unchanged. The versioned API listed 4 files totalling 1,729,356,621 uncompressed bytes. No `MANIFEST.json` is listed; no current payload SHA256 was obtained. Existing October 7 header/hash statements above are historical observations, not this refresh's byte verification. A manifest-based flatpack verifier therefore does not apply to this release as-is.

[Existing campaign notebook](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) · [Public campaign experiments and reproduction notes](https://github.com/cubres/enveda-casmi-2026). The notebook's complete recipe and official result are separate from a standalone dataset's usefulness; this refresh supplies no new score or compatibility claim. Version-bound file inventories are available with the reviewed card package on GitHub after publication.
