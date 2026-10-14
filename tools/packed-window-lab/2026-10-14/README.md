# CASMI Packed Window Lab

A small NumPy companion for inspecting mass windows, keeping candidate arrays aligned, unpacking declared fingerprint rows and reporting exact-score ties. It is useful before connecting a spectrum-to-fingerprint model to a candidate bank: a wrong row join or bit order can silently change every ranking.

**All 14 registered synthetic controls passed in one completed run.** This release contains original MIT code and invented arrays only. It contains no molecular structures, spectra, real candidate identifiers, training labels, learned weights, third-party fingerprints or MACCS definitions. Real producer eligibility remains **UNKNOWN**; no model was fitted and no competition score was measured.

![The declared 277-byte layout and the two positions that never contribute](packing-layout.svg)

## Try the invented example

The completed control run used Python 3.12.14 and NumPy 2.2.6 on macOS arm64. The package declares Python 3.10+, but other environments have not been verified by this release. Use your own NumPy environment; `requirements-tested.txt` records the tested dependency.

```bash
cd original
python -B synthetic_demo.py
python -B synthetic_demo.py --bitorder little --mode balanced_prospective
python -B synthetic_demo.py --mass 175 --ppm 10
python -B -m unittest -v test_window_lab.py
```

The default fixture has repeated values on both 10 ppm endpoints and adjacent floating-point values outside them. Its shared row slice is `2:9`, containing seven invented rows. The empty-window example returns no candidates. The default fixture and these expectations are source-defined mechanics, not predictions about molecules.

## What this helps you check

- An inclusive neutral-mass window retains boundary duplicates and slices every aligned array with the same interval.
- Explicit `big` or `little` packing preserves declared binary positions; unknown packing is refused.
- Unused MACCS key 0 and final padding remain zero and cannot affect scores.
- Whole-window block standardization stays finite for empty, singleton and constant windows.
- Exact-score ties have deterministic token order and retain the full tie size at a top-k cutoff.

The normal scorer consumes caller-qualified **true logits**, using valid bits dotted with logits. The optional `balanced_prospective` formula is a fixed `z(Morgan) + 0.30*z(MACCS)` experiment, with no demonstrated ranking gain. Shapes cannot prove that inputs are logits, correct chemical descriptors or lawful to reuse.

Read [the integration guide](INTEGRATION.md) for the array contract, admission checks and a bounded comparison plan. [The original API guide](original/README.md) explains equations, limits and evaluation-only tie handling. [The completed mechanics result](MECHANICS_RESULT.json) records every passing control and its evidence commitments.

## Provenance and preserved source

The `original/` directory preserves all 11 source-packet files byte for byte. Its README, proposal and run-plan documents describe their earlier source-only state. **The later completed run is recorded by this release README and `MECHANICS_RESULT.json`.** The original hashes are listed in [the source manifest](ORIGINAL_SOURCE_MANIFEST.json); no controller implementation, local runtime paths or private runtime inventories are included.

Credit to [Aryan Awasthi's Morgan/MACCS candidate bank](https://www.kaggle.com/datasets/aryanawasthiteykik/casmi26-coconut-morgan-maccs-fingerprints) and [spectrum-to-fingerprint model](https://www.kaggle.com/datasets/aryanawasthiteykik/casmi26-spectrum-to-fingerprint-mlp), [prvsiyan's COCONUT candidates](https://www.kaggle.com/datasets/prvsiyan/coconut-casmi26-candidates), and the [COCONUT contributors](https://coconut.naturalproducts.net/). These resources motivated the companion; none of their data or implementation is bundled. [Sources and terms](original/SOURCES.md) preserve the dated provenance and the independent block-balancing hypothesis credit. External licenses and current competition eligibility require their own review; this release performs no new network verification.

[MIT](original/LICENSE.txt) covers the original package and added release documentation and diagram. It does not grant rights to external data, chemistry, models or code. A passing synthetic test suite establishes these tested mechanics only: it does not certify a real producer, chemical identities, scale performance, a solver's strength or future monitoring reliability.
