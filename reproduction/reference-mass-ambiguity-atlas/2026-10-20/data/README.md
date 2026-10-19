# Reference exact-mass ambiguity atlas

All 4,096 public ChEBI reference rows are retained, with 4,092 canonical groups and 3,800 directed different-group confuser pairs. There are 1,262 queries using the 10 ppm window, 359 using the 30 ppm fallback and 2,475 with no different-group peer at 30 ppm.

These are molecular reference exact masses, not observed MS2 precursor measurements. For reference q, use the closed window mass[q] +/- mass[q]*ppm*1e-6; exclude all equal public canonical groups before choosing all 10 ppm rows or, only if none, all 30 ppm rows. The q-mass denominator and fallback make pairs directional.

`query_rows.csv` preserves every reference row and 10/30 ppm row/group counts. `pairs.csv.gz` contains all selected directed row pairs, exact intersection/union and on-bit counts, Jaccard and binary cosine on 10,395 MSB-first bits. Undefined ratios are blank. Display limits do not truncate stored data.

```bash
python demo_atlas.py --atlas-dir . --query-row 0 --limit 5
python demo_atlas.py --atlas-dir . --mass 400 --ppm 10 --limit 5
```

The numeric-mass example is a user-supplied illustration; without a query structure it cannot exclude a canonical group and performs no fingerprint ranking. See `REFERENCE_INPUTS.json` for the immutable source and file hashes, `ATLAS_COMPLETE.json` for measured counts/runtime, and `OUTPUT_MANIFEST.json` for output hashes.

Preserve `DATA-LICENSE.md`, `SOURCE_COMPONENT_LICENSE.md` and `SOURCE_ATTRIBUTION.md`: ChEBI CC BY 4.0 and separate frozen-mask component terms remain. This reference atlas establishes no validation recall, hidden-answer coverage, model quality or official score. Release admission also requires a successful outer owned wrapper and independent completed-output review.
