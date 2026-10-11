# Precise native export request

This is an input/export request for a reviewed private development experiment. It does not authorize a new competition submission or establish an improvement.

## Export the live native values safely

Use one eligible, fixed own development panel whose complete candidate pools and ion banks fit the packet's bounds. Register the query-selection rule from acquisition/runtime eligibility before labels. Do not select favorable answers, crop candidates or truncate hypotheses to force eligibility. Preserve current candidate generation, availability of views, scorer configuration and fitted-control model.

The native producer must retain:

| Object | Required fields |
|---|---|
| Query | Opaque caller-established same-query token; exact ordered candidate IDs |
| Each native cleaned view | Query/view IDs; sorted m/z and aligned linear intensity arrays; exact cleaning-source pin; precursor annotation/polarity/m/z; instrument; declared eV list; optional acquisition bounds and their source pin |
| Each candidate/view prediction | Query/candidate/view IDs in complete row-major order; neutral or charged-m/z representation; explicit family/charge/H shifts; full mass vector; generator source pin; `READY` or genuinely `VALID_EMPTY` status |
| Current control | Exact candidate order; actual fitted-control probabilities; original 31-column float32 feature matrix; original independent explanation per candidate/view before float32 max aggregation; control model and runtime pins |
| Review manifest | Authorized private-data scope; data/component review pins; every referenced cleaner/generator/control model/runtime pin; reviewed code license and usage; explicit component exposure |

Capture values directly from a trusted reviewed native execution, before information is discarded by max aggregation or logging. The old fragment wrapper catches generation failures and can return empty arrays: an exception-derived empty is not proof of `VALID_EMPTY`. Export failure status and let the join hold it. Do not deserialize untrusted pickle caches or infer vectors from scalar stage/service receipts.

`seal_native_export(draft)` takes the JSON-native draft schema shown concretely in `invented_flow.fixture`, computes order/array/prediction/control hashes and returns the sealed export. Conversion of trusted live numerical arrays to ordinary lists happens in the producer; this packet never runs dataset code, a fragment generator or a model. Keep the resulting export private.

## Freeze before labels

Retain exact code/helper, model, data, rights/exposure, native-export and label-payload pins and a durable timestamped review receipt before interpreting new label values. `freeze_protocol` builds the fixed 0.01 Da/zero-ppm/raw-column21/max-view protocol and binds the current join source and original helper hashes. A status string or a newly hashed already-exposed panel does not prove independent evaluation.

Protocol export/label/probability digests are over the packet's canonical JSON representation of the parsed value; code/helper pins are hashes of actual source-file bytes. A raw SHA of an arbitrary pretty-printed JSON file does not generally equal its protocol digest. A label custodian should write exactly `canonical(labels)` as bytes, without added whitespace/newlines, and supply that sealed file's raw SHA before the scorer interprets values. In that representation its raw SHA and canonical digest coincide. Existing labels that have influenced checkpoint selection, candidates, fitting or decisions remain exposed development labels.

The initial label-blind run verifies alignment and native explanation/feature parity. If it fails, preserve the failure and stop; do not tune mass families, tolerances, windows, tie policies or query selection against answers. The coordinator owns the shared exclusive attempt ledger and any reviewed subsequent repair.

## Two separate comparisons

First measure old independent explanation versus one-to-one assignment on exactly the same candidate/view arrays and hypotheses. The exported float32 max must agree with native column21. Candidate-pool recall and per-view reuse gaps are separate outcomes. Max across views remains the old aggregation; it is not a consensus claim.

For a fitted ranking comparison, fit a separate 31-column raw21 ablation using the joined matrices on a reviewed fitting cohort. Preserve old fragment-derived columns22–24 deliberately and document the mixed semantics. Retain its training/refit/exposure receipts and model pin. Export its actual candidate-order probabilities bound to the exact joined feature matrix hash. Freeze their hash before evaluation labels. Supply the complete `ENVEDA_REFITTED_ASSIGNMENT_V1` payload, as illustrated by the clearly invented fixture. Never present that fixture's symbolic model/receipt values as evidence of actual training.

The fitting/evaluation query-token disjointness gate is necessary but insufficient: audit chemical/source duplication and exposure through fingerprint pretraining, analogues, checkpoint selection and candidate generation separately. The evaluator cannot authenticate those declarations. A full assignment-derived feature family or 40-column branch needs a distinct protocol and refit.

## Preserve and report

Run the bounded private CPU consumer once against the frozen export and shared ledger. Preserve its result or failure, actual effective CPU/priority limits and all pins. Keep every competition-derived input, output and metric private until redistribution rights are separately established. Report feature-only effects, fitted-ranker effects, candidate-pool misses and official completed submission rows separately. No real-data or hidden-score gain is established by this packet.
