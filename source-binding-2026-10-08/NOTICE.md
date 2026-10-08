# Scope, attribution and third-party terms

The MIT license in this directory covers our original source-binding helper
code, synthetic examples/tests, diagrams and explanatory documentation. The
resolver and bridge are byte-identical to the original helper modules reviewed
for the V18 experiment. The synthetic demo contains neutral invented bytes,
not campaign examples or third-party dataset records.

No dataset, model checkpoint, training-feature matrix, spectrum, target,
private experiment transport or RDKit wheel is distributed in this package.
The MIT grant does not relicense any of those resources. Preserve their own
terms and applicable upstream attribution when obtaining or using them.

The input cards record the inspected Kaggle license labels: CC0-1.0 for the
fingerprint-v2 bundle, ranker archive and two PubChem resources; CC BY 4.0 for
COCONUT candidates. Those labels do not establish the terms of all upstream
training sources. COCONUT attribution and upstream release citations remain
required where applicable. The offline-wheel dataset's inspected license
metadata is Other, with no description establishing the specific terms; this
package makes no redistribution-license claim for that wheel or RDKit.

Public resource references and upstream attribution are linked in INPUT_CARDS.md,
HOW_TO_RUN.md and the existing dataset cards. The public Analog Propagation
notebook is the consumer reference. This helper package changes only input
selection and provides no third-party competitor scoring code or payloads.

The scientific evidence boundary remains unchanged: V18 is a completed CPU
research run whose native qualification passed and whose matched diagnostic
finished (fixed 0.9417 vs joint 0.9375 MRR@25). Its sixteen development queries
were previously exposed.
No official score, held-out generalization or automatic promotion is claimed.
The MIT license for helper files does not alter any notebook-preservation rule.
