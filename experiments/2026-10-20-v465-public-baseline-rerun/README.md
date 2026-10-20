# V43 public baseline adaptation: smoke evidence and hidden submission

**Status checked 20 October 2026, 17:53 UTC.** This record separates the visible smoke from Kaggle's accepted hidden rerun. No official score is available yet.

The credited public reference is [guhongbin's V465 V15 notebook](https://www.kaggle.com/code/guhongbin/casmi26-v465-v15-pop015?scriptVersionId=359783615), whose public notebook page displayed 0.456. The official [competition leaderboard](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/leaderboard) displayed a top score of 0.495 at the 16:43 UTC check. These are reference observations, not results from V43.

## Exact V43 identity and artifacts

- Public notebook: [Analog Propagation — CASMI 2026 baseline, version 43](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline?scriptVersionId=360497306), scriptVersionId 360497306.
- The native run completed successfully in 27m25s on T4×2.
- The selected output artifact was submission.csv, SHA-256 **5c098f153b748a651757c5aea2f078a7d1d82cfb3ae89bd656c5cc81a203ce76**. It contains 400 rows, 400 unique molecule IDs, and 1–25 candidate strings per row. The local validator returned **PASS_FORMAT_ONLY**; this says nothing about ranking quality.
- Experiment E006 processed 12 of 400 visible molecules. Its smoke output changed one row and zero top-1 entries; no fallback fired. This visible cohort overlaps training and is not independent validation.
- The additional metric-safe tail left all 12 visible rows unchanged and added zero candidates, including zero DreaMS candidates. This is a measured no-op on the smoke cohort, not evidence of hidden benefit.

## Submission state

One submission was accepted through V43's native “Submit to Competition” menu as row 57448206. At 17:53 UTC Kaggle still showed “Notebook Running” / pending; it had no public score, private score, or completed output bytes. The accepted attempt has not been resent. The visible smoke file's 388 placeholder rows are not a completed hidden prediction and must not be presented as a scored submission.

The next decision is to wait for this row to reach a terminal status, then record the official result. No new run or score claim is justified by the visible smoke alone.