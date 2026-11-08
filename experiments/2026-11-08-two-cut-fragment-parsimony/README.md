# Two-cut fragment parsimony ablation — rejected

**Date:** 2026-11-08  
**Competition:** [Enveda CASMI26](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra)  
**Status:** Rejected; training-only evaluation; no notebook or submission change.

## Hypothesis and fixed test

A fixed two-bond fragment-parsimony treatment might improve ranking when one-bond fragment evidence is insufficient. It was evaluated at a predeclared 0.5 weight against the one-bond baseline on molecule-identity-disjoint data. Train and CC0 COCONUT candidate inputs were hash-pinned. The 64-identity canary and separate 186-identity holdout were kept distinct.

## Results

| Split | One-bond baseline MRR@25 | Two-cut candidate MRR@25 | Paired difference | 95% interval |
| --- | ---: | ---: | ---: | ---: |
| 64-identity canary | 0.2867 | 0.2573 | -0.02949 | [-0.0864, 0.0273] |
| 186-identity holdout | 0.27429 | 0.26978 | -0.00451 | [-0.02304, +0.01423] |

The candidate covered 182/186 holdout identities. It lost on the independent holdout and is rejected. No threshold or weight search followed this result.

## Kaggle state at the audit

- Version 46 submission row **58131924** was still **PENDING**; this experiment was not attached to it.
- The latest completed public row checked was **0.481** (row 58105549).
- No Kaggle kernel or dataset was updated, and no new submission was sent.

The experiment used training data only; no test labels were opened. The full local receipts and source hashes are retained in the campaign's experiment archive. This negative result is not a leaderboard score and does not replace the official row.
