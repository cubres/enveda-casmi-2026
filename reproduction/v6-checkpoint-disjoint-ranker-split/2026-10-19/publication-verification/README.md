# Published CASMI checkpoint-disjoint split: independent verification

The dataset is published as [CASMI V6 Checkpoint-Disjoint Ranker Split, V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-v6-checkpoint-disjoint-ranker-split/versions/1), numeric ID **12716429**. An anonymous acquisition retrieved all **26 files / 71,960,601 bytes** and matched every published file hash. The independent checks also reconstruct the numeric joins and compare all eight split arrays with the completed full public-input rebuild.

| Partition | Queries | Canonical groups |
|---|---:|---:|
| Training | 10,859 | 10,828 |
| Development | 2,653 | 2,650 |
| Retained total | 13,512 | 13,478 |

The audit excluded 67 queries overlapping checkpoint-selection canonical groups. There is zero overlap with optimizer groups or across the frozen train/development split. The exclusion universes are conservative: all 219,470 role0 structures cover the 219,140 optimizer-eligible subset; all 13,614 role1-even structures cover the 2,048 sampled checkpoint queries.

The full rebuild freshly canonicalized all 246,674 role0/1 metadata structures in 954.258 seconds with two CPU workers, using Python 3.12.14, NumPy 2.2.6 and RDKit 2026.03.3. Every regenerated split array matched the actual public download byte-for-byte and numerically. Source SHA256: `0f5099865aee7c9c5179cd9ec943bf45b7cfdf9f8f4952c77efb3e609ccf7b9e`.

`PUBLICATION_VERIFICATION.json` records exact public identity, anonymous access observations, all 26 file hashes, numeric joins, runtime proof, and scoped non-performance claims. It contains no credentials, signed URLs or operational local paths. This repository receipt does not modify the frozen Kaggle dataset. No model fit, prediction assay or official score is claimed.

## Verify a download with NumPy only

Download the published V1 dataset and the exact `fp_meta.pkl` and `roles_by_structure.b64` files from [full fingerprint inputs V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-full-fingerprint-inputs/versions/1). With NumPy installed:

```bash
python -B verify_downloaded_split.py /path/to/split-v1 \
  --public-bank-directory /path/to/full-fingerprint-inputs-v1 \
  --output /path/to/new-verification.json
```

The verifier does not make network requests. It checks the exact 26-file manifest, all ten NumPy schemas, complete role0/1 group-universe joins, every exclusion, each salted split bucket, and zero overlap. It loads trusted metadata only after its complete public V1 SHA256 matches. It does not load spectra, fingerprints, model weights, predictions or role2/3 queries.

To compare a fresh rebuild on your own machine, run the dataset's `rebuild_canonical_split.py` first, then add `--rebuilt-directory /path/to/completed-rebuild` to the verifier command. This optional flag requires all eight rebuilt arrays to match the actual dataset download. Private acquisition or observation receipts are not required to run the public verifier.

Uploader-authored verifier and documentation: Apache 2.0 (`LICENSE-SOURCE`). Molecular metadata retains the published dataset's Other/component permissions; this software license does not change those terms.
