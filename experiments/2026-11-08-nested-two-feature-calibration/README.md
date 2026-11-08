# Nested two-feature calibration experiment

**Decision: promising local validation result; not a leaderboard result.** The notebook and dataset remain unchanged while source rights and reproducibility are checked.

## Method

The candidate rank score was `fp_model_z + alpha × within-group zscore(frag_score)`. Alpha was selected from the predeclared grid `[0.0, 0.05, 0.1, 0.2, 0.4, 0.8]` using four-fold query-grouped cross-validation on the outer 80%. Both simulations of each query stayed together in every fold. The selected value was **alpha = 0.4**.

The untouched outer 20% contained 593 query identities and 1,186 query-simulation groups, with 100% truth coverage.

| Measure | `fp_model_z` baseline | Nested calibration |
|---|---:|---:|
| MRR@25 | 0.80300 | 0.83351 |

The paired gain was **+0.03051**. The query-cluster bootstrap 95% interval was **[+0.01504, +0.04604]**. The predeclared gate required a positive holdout gain, a positive lower confidence bound, and at least 75% coverage; all three passed.

A fixed reciprocal-rank blend was tested separately and rejected (0.78050 vs 0.80300). The learned within-query calibration is the only candidate supported by this holdout.

## Provenance and limits

The local staged metadata declares CC BY-NC-SA 4.0 for derived rows and CC BY-NC 4.0 for the CASMI training data. This experiment used only `fp_model_z` and `frag_score`; no data rows or prediction files are redistributed here. A Kaggle metadata request returned 403, so public visibility was not independently verified. Before using this in a public notebook, reproduce both channels from an authorized competition-data path and clear the applicable rights.

Kaggle submission **58131924** is COMPLETE at public score **0.481**. That is an existing official result and is not associated with this local holdout. No notebook or dataset was changed, and no new submission was made.
