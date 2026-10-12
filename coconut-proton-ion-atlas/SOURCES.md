# Sources and production provenance

## Pinned numerical source

- Dataset: [prvsiyan — COCONUT 2.0 candidates + fingerprints (CASMI26)](https://www.kaggle.com/datasets/prvsiyan/coconut-casmi26-candidates).
- Data version: **2**. Numeric dataset ID: **12039473**.
- File: `coco_mass.npy`, 3,491,240 bytes, NPY 1.0, C-order, little-endian float64, `(436389,)`.
- File timestamp in the preserved versioned public inventory: **2026-09-15T19:42:46.833Z**.
- SHA-256: `2b2af92c3185fa8cd52a4a3e3e7fd7eda4d94e8b9402662a3a4c55ffb13c6e5c`.
- Source license recorded on the public card as of October 12, 2026: **CC BY-NC-SA 4.0**. The derived numerical payload retains it.

The source card attributes the structures and neutral masses to COCONUT. It also explains that its selected fingerprints may involve competition-derived bit selection. This atlas uses only the supplied neutral masses; it does not use the selected bits, packed fingerprints, pickle metadata, competition structures or query spectra. It nevertheless retains the source's current restrictive data license rather than reclassifying a subcomponent by inference.

The source's earlier October 7 card recorded CC BY 4.0, whereas its later card records CC BY-NC-SA 4.0. The earlier card does not override the current notice. The current source card's separate upstream CC BY 4.0 statement is not a verified release-specific grant for this atlas. Changing COCONUT's license on a later download page would not relabel these exact older derivative bytes.

## Upstream credit

[COCONUT — COlleCtion of Open Natural prodUcTs](https://coconut.naturalproducts.net/), and its contributors, provide the upstream natural-products resource. Cite the specific COCONUT release used in any independently rebuilt pool. The exact original COCONUT snapshot date is not established by the supplied mass file.

For background, the source is introduced in [Sorokina et al., *COCONUT online: Collection of Open Natural Products database*](https://doi.org/10.1186/s13321-020-00478-9). This citation does not establish which snapshot or original chemical normalization produced the retained array.

## Declared physical constant and transformations

[NIST, CODATA 2022 proton mass in u](https://physics.nist.gov/cgi-bin/cuu/Value?mpu) gives `1.0072764665789 u`, with standard uncertainty `0.0000000000083 u`. The numerical generator fixes that recommended central value and records it in the manifest. It does not treat proton mass as atomic hydrogen mass.

Each channel is an original explicit affine transformation of the supplied neutral masses:

```text
m/z = (number_of_molecules × neutral_mass + signed_protons × proton_mass) / absolute_charge
```

No peak prediction, spectral simulation or molecular feasibility determination is performed. These lookup hypotheses preserve source positions. Candidate-ranking quality requires a separate experiment.

## Related public work

The latest useful source lead is [aryanawasthiteykik's COCONUT Morgan/MACCS fingerprint dataset](https://www.kaggle.com/datasets/aryanawasthiteykik/casmi26-coconut-morgan-maccs-fingerprints), which credits prvsiyan's candidate bank and the COCONUT team. Its plain Parquet/NumPy interface motivated readable, pickle-free candidate contracts. None of its data, weights or code are included here. It has a different descriptor contract; no positional or molecular-key join is asserted.

## What can be reproduced

The original MIT loader and generator rebuild all eight channel arrays, the source mass bins and exact-mass duplicate runs from the single pinned file. `MANIFEST.json` records actual source measurements; `RELEASE_FILES.json` hashes the code, explanatory material and derived data. The rebuild refuses existing output directories and keeps partial outputs intact on failure.

The public release contains no private source paths, authentication material or per-query competition evidence. Creation times refer to this derivation, not to an invented historical upstream download. Source verification, mechanics tests and any later ranking/submission results should remain distinct in experiment records.
