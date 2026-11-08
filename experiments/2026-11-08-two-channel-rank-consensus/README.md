# Two-channel rank-consensus experiment

**Decision: reject.** This experiment did not improve the validated CASMI ranker and is not a leaderboard result.

## Method

A fixed tie-aware reciprocal-rank fusion (k=60) combined the fingerprint-model score `fp_model_z` with the fragment-explanation score `frag_score`. The comparison baseline used `fp_model_z` alone.

Validation held out 593 query identities together across two simulations (1,186 query-simulation groups). Every group had one true candidate, for 100% truth coverage. The split was fixed before scoring.

| Measure | Fingerprint baseline | RRF candidate |
|---|---:|---:|
| MRR@25 | 0.80300 | 0.78050 |

The paired difference was **−0.02250**. A query-cluster bootstrap gave a 95% interval of **[−0.04561, +0.00015]**. The predeclared promotion gate required a gain of at least 0.005, a positive lower confidence bound, and at least 75% truth coverage. It failed the first two conditions.

## Provenance and scope

Local metadata for `prvsiyan/casmi-2026-second-list-ranker-rows` declares CC BY-NC-SA 4.0 for derived rows and CC BY-NC 4.0 for source training data. This experiment used only the CASMI-derived `fp_model_z` and `frag_score` channels. It excluded library and analog channels because their individual external-source provenance was not fully screened. A Kaggle metadata request returned 403, so current page visibility was not verified. No dataset rows or third-party files are redistributed here.

This is a local grouped training-holdout metric. It must not be compared with the official public score. The latest official completed row remains submission **58131924**, public score **0.481**; it is not associated with this experiment. No notebook was edited or pushed, and no submission was made.
