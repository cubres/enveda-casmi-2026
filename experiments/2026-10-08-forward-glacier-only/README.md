# 2026-10-08: F1, the GLACIER-only forward weight, and a public forward stack

**Hypothesis (predeclared in [F1_PREDECLARATION.md](../2026-10-08-joint-placement-and-forward/F1_PREDECLARATION.md)).** In the version behind our 0.340, forward re-scoring averaged ICEBERG and GLACIER (0.5 / 0.5). Public single-variable evidence suggested GLACIER alone is better. F1 changes exactly that one line (ICEBERG 0.0 / GLACIER 1.0). Decision rule, fixed before any run: two official draws; adopt if the mean is at least 0.348 and neither draw is below 0.340; reject if the mean is at most 0.341.

**Bench run.** The first attempt (worker version 19) died after 12 seconds for an infrastructure reason unrelated to the science: the new file-backed cell runner exec'd cells from strings, and numba's `cache=True` needs a real source file. Version 20 writes each cell to disk first and completed in 4,438 s with the forward canary passing and a visible-cohort CSV identical to the 0.340 version's, as the fidelity check requires ([bench-v20-run-receipt.json](bench-v20-run-receipt.json), [forward-canary.json](forward-canary.json)).

**Draw 1** was submitted from the bench at 12:23 UTC as row 56953547 ([draw1-accepted.json](draw1-accepted.json)); its score is unknown at this writing. Draw 2 will come from the public notebook, whose version 33 carries the same payload with the pipeline explained for readers.

**Forward stack made public.** So that version 33 is forkable, the dataset `prvsiyan/casmi26-forward-reference-stack` (unmodified MIT ms-pred source at commit 708148c, the upstream MassSpecGym-trained ICEBERG and GLACIER checkpoints, pinned wheels, and our runner) is now public under "Other" terms spelled out in its card: it contains no competition data, no reference library and no NIST-derived weights; the NVIDIA runtime wheels ship unmodified under NVIDIA's EULA as the runner's dependency closure ([forward-stack-dataset-published.json](forward-stack-dataset-published.json)). The popularity-count dataset was already public under CC0.

No score is claimed here. Documentation is MIT like its siblings.
