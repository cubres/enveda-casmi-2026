# Enveda CASMI: dataset-card updates applied, 2026-10-11

The useful load recipes are now in the existing live Kaggle dataset descriptions. Each successful metadata request was followed by an immediate exact UTF8 description readback from both dataset routes. The complete current versioned filename/size inventory and all other protected SDK-readable fields matched before/after. No dataset file or data version was uploaded; no notebook or image was changed in this workflow.

| Live dataset | Existing data version | Verified readback UTC | Description characters |
|---|---:|---|---:|
| [casmi26-fp-models-v2](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v2) | 1 | 2026-10-11T20:29:28.413032+00:00 | 6,482 |
| [casmi26-fp-models-v4](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v4) | 1 | 2026-10-11T20:29:30.188118+00:00 | 6,502 |
| [coconut-casmi26-candidates](https://www.kaggle.com/datasets/prvsiyan/coconut-casmi26-candidates) | 2 | 2026-10-11T20:29:32.082649+00:00 | 7,269 |
| [casmi26-ranker-features](https://www.kaggle.com/datasets/prvsiyan/casmi26-ranker-features) | 6 | 2026-10-11T20:29:33.905259+00:00 | 6,884 |

The exact applied descriptions and original examples were published in [the source package at commit `7ccd7de5d9bd`](https://github.com/cubres/enveda-casmi-2026/tree/7ccd7de5d9bdf37fced42a8adb400a7d19b898f4/dataset-cards-2026-10-11-r1). [APPLIED_DESCRIPTION_RECEIPTS.json](APPLIED_DESCRIPTION_RECEIPTS.json) gives exact description hashes, source links and observation timestamps without exposing raw metadata captures. The `.md` source filenames retain `DESCRIPTION_PROPOSAL` for provenance; these specified bytes were subsequently read back from the live cards.

The first description-only request for the v2 fingerprint bundle was explicitly rejected because the endpoint required a title. An independent subsequent read confirmed that target's description and protected readable fields were unchanged. The repaired request mirrored the exact current title and other available metadata settings, changing only the intended description. The failed request remains documented; it was not a successful card update. Unknown outcomes were not retried.

Verification is limited to fields exposed by the installed SDK. Only the intended dataset-description paths and explicitly named observation counters were excluded from comparison; nested file/column descriptions, versions, licence labels, publicness, image URL and timestamps remained protected. No timestamp exception was used in any of these five successful readbacks. The SDK discards unknown server fields, and these observations do not establish general server merge/patch semantics, atomic safety or preservation of unavailable settings. They record these particular outcomes at the stated times; live descriptions may later evolve.

No current payload SHA256, model inference, independent validation split, new official score, medal or vote gain was established by this card work. The full load snippets were syntax checked rather than executed on dataset payloads. Existing October 7 payload/header observations remain historical. No additional rights were granted; the Knee dataset's unknown licence label was preserved.

The COCONUT load recipe now includes exact upper and lower mass-window endpoints, uses numeric no-pickle arrays and decodes selected rows. The ranker recipe checks schema while preserving the unresolved query/structure/exposure mapping caveat. The similarly named fingerprint releases get distinct version/file-size checks and restricted checkpoint inspection.

The endpoint arithmetic has one genuinely executed control on invented masses; its existing source is [pinned here](https://github.com/cubres/enveda-casmi-2026/blob/7ccd7de5d9bdf37fced42a8adb400a7d19b898f4/dataset-cards-2026-10-11-r1/examples/toy_mass_window.py). The retained [result](validation/TOY_MASS_WINDOW_RESULT.json) and [execution receipt](validation/TOY_MASS_WINDOW_EXECUTION.json) are copied unchanged. This addendum did not rerun it. Run the original toy with Python and NumPy if you want to reproduce the numeric boundary check; it reads no real candidate array, spectrum, molecule or query.

It selected 3 invented rows when both endpoints were included, compared with 2 under the old default upper endpoint; repeated exact endpoints selected 4, and an empty interval selected 0. These are row counts in a toy, not identification coverage or competition performance.
