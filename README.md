# Enveda CASMI 2026: experiments and public notebook

## Fold-safe top-identity gate · 20 October

A deterministic 64-query canary and the full 250-molecule cached panel replay support a small top-1-preserving fold-safe FPNet blend: gated MRR@25 **0.51443 vs 0.51198 baseline** (paired 95% interval for the gain: **+0.00009 to +0.00534**), with top-1 unchanged. This is public development-panel evidence, not an official score; the [recipe, runnable script, exact hashes, and limits](experiments/2026-10-20-fold0-identity-gate/README.md) are recorded separately. The current panel dataset’s embedded manifests have several mismatched file pins; the release binds the exact Kaggle version 7 inputs by hash.

As of the dated **2026-10-20 16:00 UTC** public leaderboard snapshot, the top score was **0.495** and the prvsiyan row was **0.345** (rank 1,954 of 3,670). That row is not evidence for this cached panel experiment or the current notebook source. See the [dated snapshot](experiments/2026-10-20-fold0-identity-gate/leaderboard_snapshot.json) and [live leaderboard](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/leaderboard).


## Checkpoint and ranker reproducibility audit · 20 October

The source, prepared inputs and recorded S2/M1 commands are now linked in a [public, source-pinned audit](reproduction/legacy-v2/public-reproducibility-audit/2026-10-20/README.md). It separates the parts that can be inspected and rerun from the unresolved historical checkpoint-to-ranker-cache binding and raw ChEBI/LIPID MAPS ingestion lineage; it makes no new score claim.

## Verified ChEBI fingerprint shard · 20 October

The [producer, numerical checks and runnable retrieval demo](reproduction/chebi3-fullfp-shard/2026-10-20/README.md) cover 4,096 ChEBI three-star records absent by raw key and exact SMILES from our older candidate bank. All 45 producer outputs passed their hash and numerical checks; the shard contains 4,092 canonical groups. [The pipeline diagram](reproduction/chebi3-fullfp-shard/2026-10-20/assets/pipeline.png) shows the row and fingerprint contracts. Kaggle packaging is pending; score improvement and canonical novelty against the entire old bank remain unmeasured.

## Verified public split · 19 October

The [public V1 dataset](https://www.kaggle.com/datasets/prvsiyan/casmi26-v6-checkpoint-disjoint-ranker-split/versions/1) excludes 67 checkpoint-overlapping queries and retains 10,859 training / 2,653 development queries with zero canonical-group overlap. A full public-input rebuild reproduced all eight arrays in 954.258 seconds. Anonymous downloads matched every one of the 26 published files (71,960,601 bytes).

[Run the rebuild and NumPy demo](reproduction/v6-checkpoint-disjoint-ranker-split/2026-10-19/README.md), or [audit the downloaded files and joins](reproduction/v6-checkpoint-disjoint-ranker-split/2026-10-19/publication-verification/README.md). Source, split rules, measured proof and component licenses are included. This release claims no new model accuracy or official score.

![Verified checkpoint-disjoint split](reproduction/v6-checkpoint-disjoint-ranker-split/2026-10-19/split_flow.png)

## Completed complementary training · 20 October

The [V9 reproducibility release](reproduction/v9-complementary-training/2026-10-20/README.md) records 3,000 completed role-0 FPNet updates after a 64-update canary, with the exact source, public V1 inputs, recipe, runtime and independent CPU artifact checks. Its 197.7 MB checkpoint and 395.5 MB optimizer state remain in [the exact public V9 Output](https://www.kaggle.com/code/prvsiyan/casmi-fp-trainer-merged-spectra?scriptVersionId=360180749); version-specific download instructions and hashes prevent a silent latest-version substitution. Quality and serving remain unmeasured, and historical S2/M1/ranker-cache provenance gaps are still stated explicitly.

## Recovered training and preparation sources · 18 October

The [reproducibility release](reproduction/legacy-v2/README.md) publishes the original spectrum preparation, FPNet, S2/M1 training recipes and `make_ranker3.py`, with checkpoint hashes, all 31 ranker feature definitions and runnable invented-data examples. Configured training limits and selected checkpoint steps are documented separately. Historical initialization was seeded late, and the exact producer of the retained ranker FP caches remains unresolved; this is a transparent source release with stated gaps, not a claim of complete historical weight reproduction.

The [dataset cards and license scope](reproduction/dataset-cards/2026-10-18/README.md) separate uploader contributions from upstream rights and identify private inputs and unresolved provenance. The [fingerprint contract checker](tools/fingerprint-contract/README.md) runs with the Python standard library and includes reproducible invented 6,930-bit and 10,395-bit fixtures; all eight adversarial controls passed. Layout checks do not certify chemical parity or model quality.

The [V37 incident analysis and portable supervisor tests](incidents/2026-10-18-v37-wrapper/README.md) reproduce sixteen process-observation boundary cases. The proposed observer fix preserves all original limits; its effect on the actual native incident remains unverified.

The [selected V6 serving sources](reproduction/selected-v6-serving/README.md) are pinned to the actual public V37 source. V37's driver reported completion for 400 molecules, but its process/RSS supervisor failed: the notebook is **ERROR and ineligible for submission**. No official V6 score is claimed. Legacy 6,930-bit and later 10,395-bit fingerprint coordinates are distinct.

```mermaid
flowchart LR
    A[Permitted spectra and structures] --> B[Original preparation and structure split]
    B --> C[Selected legacy fingerprints]
    C --> D[S2 and M1 training recipes]
    D --> E[Explicit FP logit cache producer]
    E --> F[31-column ranker builder]
    F --> G[Measured validation]
```

Four [public conceptual illustrations](https://www.kaggle.com/datasets/prvsiyan/four-campaign-notebook-illustrations) include full prompts, alt text, file hashes and a Kaggle display helper. They make no scientific or score claim. Existing notebook opening artwork is preserved.

## Latest runnable utility · 14 October

[Packed Window Lab](tools/packed-window-lab/2026-10-14/README.md) checks inclusive mass windows, aligned candidate rows, explicit bit packing, dummy-bit masks and exact-score ties. The original NumPy package passed **all 14 synthetic controls** in one completed, bounded run. It includes portable source, examples, integration notes and two diagrams. No model was fitted; real producer eligibility and competition performance remain unmeasured.

![The fingerprint row layout and its ignored positions](tools/packed-window-lab/2026-10-14/packing-layout.svg)

## Earlier measured experiment · 12 October

[Four-group fallback pilot](experiments/2026-10-12-v25-negative-fallback/README.md): **0 gains, 1 loss and 3 ties**, with MRR@25 changing from **1.000 to 0.875**. These four exposed development groups were deliberately selected for poor library coverage; this negative result supports holding the fallback and reproducing the stronger public baseline before more tuning.

![Control and fallback comparison](experiments/2026-10-12-v25-negative-fallback/control_fallback.svg)

## Earlier gate diagnosis · 12 October

[Native gate activation](native-gate-activation-2026-10-12/README.md) explains a completed negative result: **0 of 400 query groups activated the new ranking path**. Read the diagnosis, regenerate the figure, or reuse the original structural capture auditor. Ranking efficacy remains unmeasured; the next reference-library holdout is a separate experiment.

![Native retrieval-gate activation](native-gate-activation-2026-10-12/native-gate-activation.svg)

## Earlier experiments worth reading

Existing public campaign notebook: [Analog Propagation - CASMI 2026 baseline](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline). This stable identity was observed public in the retained 11 October snapshot; the guide makes no current run-status or score claim.

The permanent archive includes [Energy-balanced projection](https://github.com/cubres/enveda-casmi-2026/blob/0c5cf4615cf1de050e7e3dc769630c5b760f284b/tools/energy-balanced-projection/2026-10-05/README.md) and [Protected candidate/control comparison](https://github.com/cubres/enveda-casmi-2026/blob/1832b0157cc151f8e1afe3ac363763348a9ec784/protected-candidate-control-2026-10-09/README.md). Read their original claim limits and provenance before a fork. Failures and unexecuted ideas remain part of the record; invented controls are separate from native qualification and official scores.

The shared [Static notebook execution map](https://github.com/cubres/gemma-4-developer-agent/blob/4b21f05ee4542c9f0c5a9dfd2a6d7081385af6d7/tools/notebook-execution-map/2026-10-05/README.md) provides a read-only first look at direct configuration bindings. It does not execute notebooks or infer effective runtime.
