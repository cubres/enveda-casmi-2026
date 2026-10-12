# Provenance and exact claim boundaries

All package code, invented numbers/bit patterns, expected outputs and diagrams were written specifically for this companion kit on October 12, 2026. No upstream code, chemical table, spectrum, learned checkpoint, private competition artifact, third-party README or notebook artwork is included.

Primary references checked during construction:

- [NumPy searchsorted](https://numpy.org/doc/stable/reference/generated/numpy.searchsorted.html): sorted-array requirement and left/right insertion semantics.
- [NumPy unpackbits](https://numpy.org/doc/stable/reference/generated/numpy.unpackbits.html): explicit bit order and requested bit count. The helper additionally rejects unused nonzero bits instead of silently discarding them.
- [NumPy load](https://numpy.org/doc/stable/reference/generated/numpy.load.html): `allow_pickle=False`, read-only memory mapping and header limit. No claim of general hostile-file containment is made.
- [RDKit MACCS implementation header](https://github.com/rdkit/rdkit/blob/master/Code/GraphMol/Fingerprints/MACCS.h): 167 positions for the 166 numbered public keys. No SMARTS definitions or RDKit implementation are copied.
- [RDKit BitOps implementation](https://github.com/rdkit/rdkit/blob/master/Code/DataStructs/BitOps.cpp): binary-text byte packing is little-bit-order; binary empty/empty Tanimoto returns zero. No code is copied.
- [RDKit Morgan generator documentation](https://www.rdkit.org/docs/source/rdkit.Chem.rdFingerprintGenerator.html): width is not a complete feature convention. The kit requires an explicit chosen contract rather than inferring a generator from a shape.
- [NIST proton mass in u](https://physics.nist.gov/cgi-bin/cuu/Value?mpu%7Csearch_for=proton+mass): 2022 CODATA `1.0072764665789`. The package fixes this value for transparent numerical reproduction.

User-supplied lead, publisher description checked by the campaign coordinator on October 12:

- [aryanawasthiteykik COCONUT fingerprints](https://www.kaggle.com/datasets/aryanawasthiteykik/casmi26-coconut-morgan-maccs-fingerprints), visible Version 1: publisher describes 436,389 mass-sorted rows, Morgan radius 2 with 2048 bits, MACCS 167 positions and one padding bit, totaling 2216 model outputs; plain Parquet/NumPy files. These are publisher declarations; complete arrays were not downloaded or chemically checked for this kit.
- [aryanawasthiteykik spectrum-to-fingerprint MLP](https://www.kaggle.com/datasets/aryanawasthiteykik/casmi26-spectrum-to-fingerprint-mlp), visible Version 3: current description recommends Version 2's 2216-output model. Historical Version 1 paragraphs describe 2048 outputs separately. No checkpoint is bundled or run.
- The linked cards display CC BY-NC-SA 4.0. MIT applies solely to our original companion kit and does not relabel those resources.
- Both the publisher and this kit credit [prvsiyan's original COCONUT candidates](https://www.kaggle.com/datasets/prvsiyan/coconut-casmi26-candidates) and the [COCONUT project](https://coconut.naturalproducts.net/).

The fixture manifest proves reproducible bytes of invented arrays. It does not prove chemistry, identify a real candidate, establish lawful third-party redistribution, resolve model–candidate feature compatibility, measure held-out quality, or imply a leaderboard score.
