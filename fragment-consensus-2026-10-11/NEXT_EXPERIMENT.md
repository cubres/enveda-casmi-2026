# Proposed ablation: nine fragment-evidence columns

Status: proposed, unexecuted. This file is not a registered holdout protocol.
Do not count synthetic controls as local MRR or hidden-score improvement.

## Question and fixed intervention

Does removing ion reuse credit, exposing ion-density coverage, and retaining
cross-spectrum support improve structure ranking on genuinely unseen compounds?

Arm A: current 31-feature ranker and candidate pool, with its exact incumbent
training procedure and frozen stages.

Arm B: same candidate pool and procedure, appending all nine columns from
fragment_consensus.py in FEATURE_NAMES order. Keep the original fragment
columns so the ranker can learn when max-only evidence remains useful.
Refit the model; a 31-column fitted ranker must never receive 40 columns.

No second candidate list, RRF change, overlay, popularity change, top-rank shield,
new checkpoint, or forward-stage change is part of the intervention. Do not
replay the already rejected second-list competition submission.

## Before data access or execution

1. Pin Arm A code, models, candidate generation, library, all training inputs,
   chemistry adapter, cleaning, adduct groups, acquisition-window rule, fitting
   parameters, seeds, device, and per-stage status. Per-record external-data
   rights and source-file checks must pass independently.
2. Define an evaluation structure set disjoint from ranker fitting, fingerprint
   fitting/checkpoint selection, analog-library truth exposure, and all prior
   feature/hyperparameter selection. Merely choosing checkpoint-even structures
   is insufficient when a frozen component already saw them.
3. If that all-component holdout is unavailable, name the evaluation a reused
   diagnostic or cross-fit and retrain the affected components. It cannot be
   called independent transfer validation.
4. Keep all competition-data-derived rows, spectra, labels, and models private
   or regenerate them in the authorized participant runtime. This public
   packet requires none of them. Its MIT code licence does not authorize
   redistribution of those inputs.
5. Validate charged ion hypotheses against adduct/polarity/charge and group
   spectra before computing cross-view features. Freeze the peak-cleaning and
   acquisition-window rules once for both arms; never choose them by answers.
6. Compare bitwise or tolerance-qualified unchanged-stage outputs; matched
   exposure, query order, candidates, device, and scientific metric are required.
   Both native outputs must identify failed/skipped forward stages.
7. Profile a bounded pilot including the largest hypothesis/peak cases. Use
   one CPU thread first, then choose parallelism from measured memory/runtime.
   Over-budget rows HOLD with a recorded cause; do not silently bypass the
   feature for one arm.

## One evaluation; no winner selection on tiny slices

Fit once on the designated training portion. The complete 40-column intervention
is fixed; do not select max/median/null subsets by an observed small-slice win.

Primary: paired structure-level class-2 reciprocal-rank difference on the
independent evaluation panel. Report mean, 90% paired-bootstrap interval,
rank-1/rank-5 hits, losses/wins/ties, candidate recall, missing-feature rows,
and counts by adduct, collision-energy heterogeneity, number of spectra,
and hypothesis-count bins.

Prospective scientific gate for a coordinator to register:
- primary mean gain at least +0.010 and 90% lower bound above zero;
- class-1 guard mean at least zero and lower bound at least -0.001;
- no candidate recall loss and no unexplained input/stage/device drift;
- hold again on a separate all-component-unseen structure split.
These thresholds are a proposed conservative local gate, not empirical evidence.

Report the old S1/S2/S3 slices as reused diagnostics only. A COCONUT-only first
guess on a query whose generator truth always comes from the training library
is not natural-product validation.

If local gates pass and external rules/runtime/public-notebook gates also pass,
the sole submission coordinator may decide whether to authorize one new public
notebook output. Keep the F1 comparison band distinct from older V6 bands:
the later F1-relative band recorded in the current plan is adoption at >=0.352
and rejection at <=0.345. No competition draw is authorized or made by this
prototype.

## Failure is useful

Reject or narrow the feature if it penalizes correct single-energy fragments,
if learned coefficients merely recover candidate size or spectrum count,
if all improvement comes from repeated centroids that native cleaning removes,
or if mass-window choices create an artificial density advantage.

A positive prototype test proves numerical behavior only. An independent local
gain supports a new hypothesis. Only an exact completed official submission
row with a nonempty score establishes its competition result.

