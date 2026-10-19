# CASMI V6: 13,579 reserved ranker-training predictions

This dataset saves a completed GPU extraction: **13,579 molecular structures ×
10,395 raw fingerprint logits**, aligned public training joins and packed targets.
The exact producer is the selected step-28,000 V6 checkpoint; the original
architecture/data sources, builder, hashes, licenses and numeric-only demo are
included. No model fit or new score is claimed for this cache.

The [existing trainer notebook, public V7](https://www.kaggle.com/code/prvsiyan/casmi-fp-trainer-merged-spectra?scriptVersionId=359867655)
completed this extraction with a 64-query canary, then every reserved query.
Native run **359867655**, V7; exact raw server source SHA256
`de68bd81c5d5c702c874035072ae0fec53fc648bdfed83ed98991792c641db36`.
The typed notebook matched the reviewed source. The full cache builder took
44.8741 seconds; the process wrapper exited 0 with clean process-group cleanup
in 48.3238 seconds. These are resource observations, not accuracy measures.

## Use and qualification

The actual V6 optimizer source trained on role 0 only. These query structures
are **role 1 and odd original trainer structure index**, explicitly reserved for
ranker-row generation. Each uses its lowest original prepared spectrum index.
Canonical-group overlap with role-1-even checkpoint selection is unaudited:
these are optimizer-held-out raw structures, **not claimed clean group OOF**.
A later ranker needs a documented group-disjoint split or an honestly qualified
development design before validation claims. No ranker is trained here.

Role 2 and role 3 are never model queries or exported target rows. No hidden
competition test data is included. No retrieval library, self/sibling spectrum
matches, candidate-label inputs or known-answer insertion is used. The candidate
pool already contains eligible true molecular structures as part of its frozen
public molecular-identification contract. The historical twelve-column ranker
producer ambiguity remains unresolved; this is a **new explicit producer**.
The completed earlier local assay was not repeated.

## Inspect with NumPy, no GPU

```sh
python -B inspect_public_cache.py /path/to/this/dataset
```

The demo streams every release-file hash, memory-maps the dense matrix and
checks numeric shape, finite values, bit order, padding and completion. It never
loads model weights, predicts spectra or computes a score. Example data access:

```python
from pathlib import Path
import numpy as np
root = Path('/path/to/this/dataset')
logits = np.load(root/'query_logits.npy', mmap_mode='r', allow_pickle=False)
keys = np.load(root/'structure_keys.npy', allow_pickle=False)
bit_ids = np.load(root/'fp_bit_indices.npy', allow_pickle=False)
print(logits.shape, keys.shape, bit_ids.shape)
# (13579, 10395), (13579,), (10395,)
```

## Arrays and joins

| File | Schema |
| --- | --- |
| `query_logits.npy` | float32[13579,10395], raw V6 logits, not sigmoid probabilities |
| `truth_fp_packed.npy` | uint8[13579,1300], MSB-first true fingerprints, five zero padding bits |
| `fp_bit_indices.npy` | int64[10395], ordered indices into the original 10,407-bit definition |
| `structure_indices.npy` | int64[13579], increasing odd original trainer metadata rows |
| `structure_keys.npy` | fixed Unicode[13579], exact public molecular keys |
| `spectrum_indices.npy` | int64[13579], representative original prepared-spectrum rows |
| `source_rows.npy` | int64[13579], public provided-training-compilation source rows |
| `positive_pool_indices.npy` | int64[13579], aligned joins into the frozen 711,705-row candidate pool |
| `completion_bitmap.npy` | bool[13579], every value true |

`PUBLIC_RELEASE_MANIFEST.json` binds the actual files distributed here. The
original native `CACHE_MANIFEST.json`, canary and wrapper receipts are retained.
The native run also produced a byte-bound NPZ duplicate and verified its numeric
reload parity. **That duplicate is not distributed here and was not downloaded
or independently rehashed for this release.** The nine independently acquired,
rehashed and numerically verified NPY arrays carry the complete cache contents.
Its native-only NPZ SHA is preserved separately as a native producer certificate,
not represented as an independently checked local file. No signed URLs, private
paths or credentials are distributed.

## Exact producer, precision and resources

Builder SHA256
`984c4f13126f5eb9a13f28f43902299ee16161b3c17f76b09baefb8167a3cd88`.
Checkpoint: 197,739,081 bytes, SHA256
`9c46ca4fcf19002fecbcded0d0808e8a81e3a25a143e684e259f265c44a5be31`;
seed 20261003, step 28000, 8 layers, width 512, 10,395 outputs.
Cache selection/canary seed: **20261019**. Evaluation mode, inference mode,
`aug=False`, `merge_p=0`, `K=0`; canary and full batches both 64.

The observed environment was Python 3.12.13, NumPy 2.0.2, PyTorch 2.10.0+cu128,
CUDA 12.8, Tesla T4, two CPU threads. FP32 weights/inputs use FP16 CUDA autocast;
raw outputs are promoted to FP32 storage. The same 64-query canary repeated with
maximum absolute difference **0.0** and exact disk reload parity. Native process
peak RSS was **4,321,251,328 bytes**; Torch allocated peak was **1,369,720,832 bytes**.
Only device 0 was used; quota accounting must include the whole actual provider
allocation, including both T4s if allocated. The original image digest is
`37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461`.

The builder and all four original imported sources are included. Original source
scope/credits are in `ORIGINAL_SOURCE_NOTICE.md`; the original training recipe
and limitations are retained in `TRAINING_CONTRACT.json`/`TRAINING_README.md`.
`PRODUCER_README.md` documents the exact extraction command. Its source-packet
language is historical; completion is established by the native receipts and
independent numeric review for this release. No retrained V6 identity is claimed.

The three immutable public input versions are:

- [Prepared spectra V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-spec-fp/versions/1)
- [Full fingerprint bank and supplied roles V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-full-fingerprint-inputs/versions/1)
- [Selected V6 checkpoint and code V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-v6-structure-uniform-checkpoint/versions/1)

## License and attribution — Other/component terms

`DATA-LICENSE.md` preserves the provided-training-artifact permission, original
library rights and COCONUT September 2026 attribution. New uploader source uses
Apache 2.0 (`LICENSE-SOURCE`); source licensing does not relicense data or weights.
The upstream checkpoint parameter permission is retained as `LICENSE-WEIGHTS.md`;
no parameter file is redistributed here. Preserve the original
[component attribution](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/ATTRIBUTION.md)
and [source/data scope](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/LICENSE-SCOPE.md).
