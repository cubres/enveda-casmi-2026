# Enveda progress: separate candidate coverage from structural ranking

The official `prvsiyan` account snapshot at 19:11 UTC on 11 October 2026 contains two different completed results.

| Official evidence | Exact row | State |
|---|---:|---|
| Best completed result, F1 draw | 56956461 | COMPLETE — **0.344** |
| Latest completed result, GPU candidate-fusion arm, Version 23 | 57040985 | COMPLETE — **0.342** |

The [latest Version 23](https://www.kaggle.com/code/prvsiyan/zz-gpuchk-844231?scriptVersionId=357016624) did not exceed the [best completed F1 row](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline?scriptVersionId=356401066). A favorable exposed development comparison did not establish a leaderboard improvement. Candidate expansion and ranking quality therefore remain separate questions.

For ranking, one concrete weakness is repeated credit: independent fragment matching can let several nearby observed peaks claim the same predicted ion. A candidate with a broad ion bank may then look convincing for the wrong reason. The original one-to-one assignment utility limits each ion and centroid to one match. It makes this hypothesis inspectable; it has not demonstrated a competition gain.

The next isolated ablation keeps the candidate pool, ion hypotheses, tolerance, view aggregation and all other feature semantics fixed. It changes one raw fragment explanation feature from independent credit to assignment credit. A learned ranker must be refitted for the changed meaning even when the feature width is unchanged. Recomputing derived fragment features, adding consensus features and expanding candidates are separate experiments.

The paired comparison needs a sealed native export with exact candidate order, unchanged control probabilities, prediction-to-view bindings and refit provenance. A missing true structure contributes a pool miss rather than disappearing from the evaluation. Matching gains and losses within a covered pool must be reported separately from coverage. Precursor charge also does not establish fragment charge; an explicit, compatible ion interpretation is required before matching.

The original [assignment join](https://github.com/cubres/enveda-casmi-2026/tree/6147a6bc50a7a5d94d1a0cd62615189421837fc6/assignment-join-2026-10-11) supplies a runnable invented win/loss/pool-miss flow. The [fragment-consensus prototype](https://github.com/cubres/enveda-casmi-2026/tree/86719c8b662b21a9069055311e5b03da344e73b8/fragment-consensus-2026-10-11) explains the broader diagnostics. Neither their controls nor invented spectra count as native chemical validation. The [illustrated notebook companion](https://github.com/cubres/enveda-casmi-2026/blob/3bd12a31734d2572408c6fec73b9e10f099b3c03/notebook-companion-2026-10-11-r1/COMPANION.md) provides the forkable introduction.

The campaign continues to credit its public ICEBERG/GLACIER forward-scoring components and other upstream sources under their own terms. This original experiment does not redistribute their weights, candidate data or spectra.
