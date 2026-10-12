# Data dictionary

The source row position is implicit in every numerical array. There is deliberately no duplicated row-ID vector.

## Numerical arrays

| File / axis | Type | Meaning |
|---|---|---|
| `neutral_mass_da.npy[i]` | float64 | Supplied source neutral monoisotopic mass in Da at original row `i` |
| `ion_mz.npy[k, i]` | float64 | Theoretical precursor m/z for channel `k`, same original row `i` |
| `ion_mz.npy` axis 0 | Eight channel positions | Order declared in `adducts.csv` and `MANIFEST.json` |
| `ion_mz.npy` axis 1 | 436,389 source row positions | Nondecreasing for every channel; duplicates preserved |

There are no molecular identifier columns. A row position only identifies a numerical position in the SHA-pinned source. The file is not an experimentally measured spectrum.

## `adducts.csv`

| Column | Type | Definition |
|---|---|---|
| `adduct` | text | Literal supported label, e.g. `[M-2H]2-` |
| `array_file` | text | `ion_mz.npy` for every channel |
| `channel_index` | integer | Zero-based matrix axis-0 position, 0–7 |
| `polarity` | text | `positive` for positive signed charge; otherwise `negative` |
| `signed_charge` | integer | +1/+2/+3 or -1/-2/-3; division uses its absolute value |
| `molecule_multiplier` | integer | One monomer or a homodimer of two copies of the same mass |
| `signed_protons` | integer | Number of added protons; negative means subtracted protons |
| `mass_shift_da` | float text | `signed_protons × 1.0072764665789`, written to 17 significant digits |

The formulas represent proton addition/subtraction to a supplied neutral molecular mass. They include no sodium, halide, isotope or neutral-loss interpretation.

## `equal_mass_groups.csv`

| Column | Type | Definition |
|---|---|---|
| `neutral_mass_da` | float text | Exact underlying float64 mass, written to 17 significant digits |
| `source_row_start` | integer | First original source row in the run, inclusive |
| `source_row_stop_exclusive` | integer | Position after the last source row in the run |
| `row_count` | integer | Stop minus start; only runs with count greater than one occur |

Equality here is exact float64 equality. It is not chemical equivalence, an isomer assignment or a ppm cluster. Runs can be joined to source positions without changing their order.

## `mass_distribution.csv`

| Column | Type | Definition |
|---|---|---|
| `lower_da_inclusive` | integer | Included lower edge of a 50-Da neutral-mass bin |
| `upper_da_exclusive` | integer | Excluded upper edge of that bin |
| `source_rows` | integer | Source positions in the bin, counting equal masses separately |
| `distinct_exact_float64_mass_values` | integer | Distinct numerical mass values in that bin |

Bins run from `[100, 150)` through `[1250, 1300)`. Their counts sum to the complete retained mass source. This distribution is not query coverage or structural diversity.

## Query outputs

`query()` returns the adduct, polarity, signed charge, ppm convention, precursor m/z, converted neutral-mass center, neutral-mass half-width, positional `[start, stop)` slice and its count. The interval includes both numerical endpoints despite the half-open positional slice. No candidate ordering beyond original source position, cap, probability, score or molecular identity is added.

## Manifest

`MANIFEST.json` pins the dataset ref, numeric ID, version, filename, bytes and SHA-256. Numerical file hashes and full channel definitions are checked by `open_release()`, together with finite-positive ordering and every ion-to-neutral positional transformation. The manifest is a consistency record; obtain it from a trusted attributed release. It is not a cryptographic signature or a substitute for source licensing.
