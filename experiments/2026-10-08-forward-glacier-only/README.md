# 2026-10-08: F1, the GLACIER-only forward weight, and a public forward stack

**Hypothesis (predeclared in [F1_PREDECLARATION.md](../2026-10-08-joint-placement-and-forward/F1_PREDECLARATION.md)).** In the version behind our 0.340, forward re-scoring averaged ICEBERG and GLACIER (0.5 / 0.5). Public single-variable evidence suggested GLACIER alone is better. F1 changes exactly that one line (ICEBERG 0.0 / GLACIER 1.0). Decision rule, fixed before any run: two official draws; adopt if the mean is at least 0.348 and neither draw is below 0.340; reject if the mean is at most 0.341.

**Bench run.** The first attempt (worker version 19) died after 12 seconds for an infrastructure reason unrelated to the science: the new file-backed cell runner exec'd cells from strings, and numba's `cache=True` needs a real source file. Version 20 writes each cell to disk first and completed in 4,438 s with the forward canary passing and a visible-cohort CSV identical to the 0.340 version's, as the fidelity check requires ([bench-v20-run-receipt.json](bench-v20-run-receipt.json), [forward-canary.json](forward-canary.json)).

**Draw 1** was submitted from the bench at 12:23 UTC as row 56953547 ([draw1-accepted.json](draw1-accepted.json)); its score is unknown at this writing. Draw 2 will come from the public notebook, whose version 33 carries the same payload with the pipeline explained for readers.

**Forward stack made public.** So that version 33 is forkable, the dataset `prvsiyan/casmi26-forward-reference-stack` (unmodified MIT ms-pred source at commit 708148c, the upstream MassSpecGym-trained ICEBERG and GLACIER checkpoints, pinned wheels, and our runner) is now public under "Other" terms spelled out in its card: it contains no competition data, no reference library and no NIST-derived weights; the NVIDIA runtime wheels ship unmodified under NVIDIA's EULA as the runner's dependency closure ([forward-stack-dataset-published.json](forward-stack-dataset-published.json)). The popularity-count dataset was already public under CC0.

No score is claimed here. Documentation is MIT like its siblings.

## Update, 13:45 UTC: draw 2 from the public notebook

Version 33 of the public notebook [Analog Propagation — CASMI 2026 baseline](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline) is an in-place update carrying the same F1 payload with the pipeline explained for readers (engine, popularity prior, PubChem tier with fixed slots, forward re-scoring and why GLACIER-only, the file-backed owned runner, the ledger of all official rows, credits and licences); all 37 earlier cells are preserved. Its commit run completed in 62 minutes with the V6 fidelity check and the forward canary passing ([public-v33-commit-run-receipt.json](public-v33-commit-run-receipt.json)). Draw 2 was submitted from it at 13:44 UTC as row 56956461 ([draw2-public-v33-accepted.json](draw2-public-v33-accepted.json)); both scores are unknown at this writing and the predeclared rule will be applied to the pair.

## Update, 17:01 UTC: both draws scored

Both F1 draws scored **0.344**: row 56953547 from bench version 20 and row 56956461 from public version 33. The incumbent V6 rows (56824628, 56859903) still show **0.340**. None of our 35 rows has changed since the host announced it would rerun every submission on corrected test data, so that rescore is not yet visible.

**Decision under the rule frozen before scoring.** Against R = 0.340 the gain is +0.004, which falls between the reject bound (R + 0.001) and the adopt bound (R + 0.008). The result is **inconclusive**: V6 stays the incumbent and no third draw is spent.

The final call waits for the rescored incumbent:
- F1 is adopted only if the rescored V6 is ≤ 0.336;
- F1 is rejected only if the rescored V6 is ≥ 0.343.

Independently of that, the public notebook's card now shows 0.344 ([f1-scores.json](f1-scores.json)).

## Final, 20:17 UTC: the incumbent measured on the corrected data

The exact incumbent version (bench V6) was resubmitted as row 56963908 and scored **0.340**, so R = 0.340. The F1 mean of 0.344 is R + 0.004, which falls between the reject bound (0.341) and the adopt bound (0.348). The decision is **inconclusive**: V6 stays the incumbent for decisions, and no further F1 draw is spent.

Every draw reproduced exactly (V6: 0.340 three times; F1: 0.344 twice). The pipeline is deterministic, so the uncertainty lies in the roughly 132-molecule public split rather than in run-to-run noise. A gain of +0.004 is about half of one molecule moved to rank 1.
