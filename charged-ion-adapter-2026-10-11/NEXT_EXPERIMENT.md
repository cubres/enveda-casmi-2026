# A comparison worth running next

This is a prospective development protocol, not an approved production change or an executed ranking experiment. Freeze its numeric budget, cohort and decision threshold before the next labels are examined. Previously selected or fitted panels remain exposed development data even after a fresh file hash is recorded.

## First obtain the missing bindings

1. Retain the exact candidate pool and candidate ordering for every query, with a private row-to-candidate binding and a complete hash manifest. Do not add candidates while measuring a scoring change.
2. Retain current fitted-control probabilities and their model/source/configuration pins. Existing feature columns are not a substitute for the fitted control's scores.
3. Export raw fragment predictions in a reviewed, bounded numerical/JSON format. Each prediction must state whether its mass is neutral or already ion m/z, its charge/family, candidate binding, query binding and generator provenance. Do not load untrusted pickle caches to fill this gap.
4. Retain the original cleaned observed arrays, or preregister the owned cleaner as a separate preprocessing intervention. Its stable top-k tie order and Python precision have not been shown bitwise equal to the native arrays.
5. Supply acquisition bounds from instrument/acquisition records, together with their provenance, before using any uniform-window feature. If unavailable, hold the coverage/excess features and compare assignment-only evidence under a separately fitted model.
6. Establish that compared views belong to the same query/analyte before calling `compatible_groups`. Shared adduct, instrument and energy are metadata strata, not analyte identity.
7. Inventory every component's exposure: candidate analogue library, model training, pretraining where known, checkpoint selection, preprocessing and ranker fitting. A structure-disjoint ranker split alone does not prove independence of the whole pipeline.

## Keep the intervention interpretable

Start with explicit protonated/deprotonated singly charged fragment hypotheses and `abs_tol=0.01, ppm=0`. Hold unknown or contradictory annotations. Register retained-carrier branches separately, since precursor carrier presence does not prove fragment-carrier retention. Do not tune H-shift families after inspecting each query's answer.

Preserve three separately named quantities: old independent peak-explanation score, one-to-one assigned score, and their difference on the same arrays and ion bank. Report the hypothesis count and observed-peak count. Peak-interval overlap alone is only a potential-reuse diagnostic.

Compare one frozen control ranker with one newly fitted, explicitly versioned intervention ranker on an eligible, non-overlapping evaluation cohort. If only exposed development data are available, report that scope and use the result to debug the method; do not label it hidden transfer or a qualification score.

Register the handling of compatible views before labels: keep the same view availability, report per-view scores, and compute robust consensus only inside already-bound compatible groups. Do not drop disagreeing views after seeing outcomes. Hold unsupported groups and preserve a registered fallback to the current control.

## Report enough to decide

- Paired, query-level reciprocal rank at 25 with explicit tie handling and the same candidates for control and intervention.
- Candidate-pool recall and the ceiling it imposes, reported separately from within-pool ranking.
- Wins/losses/ties, invalid or held queries, all-zero fragment banks and carrier/energy coverage.
- Matching-score reuse gaps on actual predictions, rather than geometric opportunity counts.
- Numerical equality and runtime/memory bounds, with the run's exact code, input and model pins.
- A source-deduplicated uncertainty analysis only when the cohort can support it; duplicate saved regimes must not become independent samples.

Only the campaign coordinator may decide on a native execution or submission after these inputs and gates are reviewed. A completed official score belongs to its exact submission row. The already-rejected second-list arm remains rejected; this packet does not reopen it.
