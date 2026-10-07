# Existing Enveda dataset cards — October 7, 2026

Four empty descriptions were updated on the existing `prvsiyan` datasets using Kaggle's metadata-only `UpdateDatasetMetadata` method. Exact readback completed at 23:44 Europe/Sofia. Each public card in this directory is byte-identical to the published description recorded in `publication-receipts.json`.

| Existing dataset | Kaggle data version | Before → after description characters |
|---|---:|---:|
| [Fingerprint v2](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v2) | 1 | 0 → 4,603 |
| [Fingerprint v4](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v4) | 1 | 0 → 4,505 |
| [COCONUT candidates](https://www.kaggle.com/datasets/prvsiyan/coconut-casmi26-candidates) | 2 | 0 → 5,560 |
| [Ranker features](https://www.kaggle.com/datasets/prvsiyan/casmi26-ranker-features) | 6 | 0 → 5,740 |

The updates document actual file inventories, dimensions/dtypes, selected fingerprint ordering and bit packing, loading examples, candidate-relative ranker features, release history, provenance gaps, licensing and experiment limits. Each card links the existing public baseline and this GitHub project. Identity, title, privacy, license, other settings, complete file inventories, file sizes and data-version history were checked immediately before and after each update and remained identical. No files or data versions were uploaded, no notebooks changed, and no dataset was created or replaced.

## Why these cards

A complete vote-sorted SDK inventory found 136 public owned datasets. The top four had 6/4/4/4 votes and empty descriptions. FP v2, COCONUT and ranker assets were already attached to 227/236/224 notebooks. A primary-card comparison found that useful related resources explain row alignment, dtypes, working loaders, versioned provenance and evaluation limits. Documentation therefore serves an existing audience. Vote counts alone do not establish why a card is popular.

Examples inspected as documentation references, without copying their text or redistributing their assets:

- [CASMI26 PubChem popularity prior](https://www.kaggle.com/datasets/dmitriigluzdov/casmi26-pubchem-popularity-prior): row alignment, loader alternatives and source snapshots.
- [Natural-product panel benchmark](https://www.kaggle.com/datasets/dmitriigluzdov/casmi26-natural-product-panel-benchmark): withholding definitions, complete denominators and honest contamination limits.
- [Attributed reproduction assets](https://www.kaggle.com/datasets/dmitriigluzdov/casmi26-attributed-v4g-reproduction-assets): per-file provenance and component-specific terms.
- [Harmonized MassBank](https://www.kaggle.com/datasets/samartalwar/casmi-2026-spectral-library-massbankharmonized): schemas, coverage and preserved record provenance.
- [Fold-safe FPNet](https://www.kaggle.com/datasets/dmitriigluzdov/casmi26-fold-safe-fpnet): executable model contracts and seen/unseen split distinctions.

## Evidence boundaries

Checkpoint ZIP metadata was inspected without executing pickle and without downloading full weight files. NPY/NPZ headers established shapes and dtypes. Full hashes were obtained for the small mass/bit-selection arrays and the public ranker archive; training targets were not inspected. Large candidate/checkpoint files have prefix or metadata hashes only, which do not certify the complete payloads. Full checkpoint inference examples were not executed. Ranker grouping semantics remain explicitly unproven by the archive alone.

The public baseline binding records V32, its source hash, relevant attached datasets and exact `rank_features` AST parity with the reviewed feature contract. That source binding is not a new official submission or evaluation result.

After publication, votes and usability counters were unchanged in the immediate SDK readback. No leaderboard, upvote or usability gain is claimed. The schemas and documentation are substantive publication progress; scoring requires independent competition experiments.
