# V43 public baseline adaptation: smoke evidence and hidden submission

**Status checked 20 October 2026, 18:03 UTC.** This record separates the visible smoke from Kaggle's accepted hidden rerun. No official score is available yet.

The credited public reference is [guhongbin's V465 V15 notebook](https://www.kaggle.com/code/guhongbin/casmi26-v465-v15-pop015?scriptVersionId=359783615), whose public notebook page displayed 0.456. The official [competition leaderboard](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/leaderboard) displayed a top score of 0.495 at the 16:43 UTC check. These are reference observations, not results from V43.

## What the strongest public notebook actually measured

The author’s [public 13-step walkthrough](https://www.kaggle.com/code/varshithakolupuri/casmi26-13-steps-to-0-456-what-each-one-added?scriptVersionId=360037850) attributes the largest displayed leaderboard jump, 0.384 to 0.440, to a **bundled** E006 integration: a second candidate/ranker engine, popularity priors, metric-identity fusion, a top-1-safe tail, a 40-candidate fusion window, and ICEBERG fallback. It does not isolate those components, so the +0.056 cannot be assigned to any single trick.

The same ladder reports earlier ICEBERG and GLACIER gains, then candidate-source gains from ChEBI/LIPID MAPS and PubChemLite. The later N1A proxy addition moved the displayed score by 0.000, and the final PubChem popularity-weight change from 0.25 to 0.15 moved it by 0.001. Those tiny differences are within the three-decimal public-score resolution. The practical signal in this public history is stronger support for testing genuinely new candidate or spectral evidence than for another weight-only sweep; the bundled changes and public-split reuse still prevent a causal or hidden-test claim.

At the latest leaderboard-page check around 18:02 UTC, the public top entries displayed 0.495. That is separate from V465’s 0.456 and from any V43 result. The leaderboard page states that its public score covers approximately 31% of the test data, so it is not the private score or final ranking.

## Exact V43 identity and artifacts

- Public notebook: [Analog Propagation — CASMI 2026 baseline, version 43](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline?scriptVersionId=360497306), scriptVersionId 360497306.
- The native run completed successfully in 27m25s on T4×2.
- The selected output artifact was submission.csv, SHA-256 **5c098f153b748a651757c5aea2f078a7d1d82cfb3ae89bd656c5cc81a203ce76**. It contains 400 rows, 400 unique molecule IDs, and 1–25 candidate strings per row. The local validator returned **PASS_FORMAT_ONLY**; this says nothing about ranking quality.
- Experiment E006 processed 12 of 400 visible molecules. Its smoke output changed one row and zero top-1 entries; no fallback fired. This visible cohort overlaps training and is not independent validation.
- The additional metric-safe tail left all 12 visible rows unchanged and added zero candidates, including zero DreaMS candidates. This is a measured no-op on the smoke cohort, not evidence of hidden benefit.

## Submission state

One submission was accepted through V43's native “Submit to Competition” menu as row 57448206. A fresh native submissions-page reload at 18:03 UTC still showed the V43 row as “Loading” (19 minutes old), with no score visible. The accepted attempt has not been resent. The visible smoke file's 388 placeholder rows are not a completed hidden prediction and must not be presented as a scored submission.

The next decision is to wait for this row to reach a terminal status, then record the official result. No new run or score claim is justified by the visible smoke alone.