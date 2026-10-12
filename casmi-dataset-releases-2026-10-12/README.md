# CASMI companion dataset releases — 12 October 2026

Two original companion releases are now **public, Version 1 and READY** on Kaggle. Native readback verified their exact downloadable file names and sizes; canonical Settings observations explicitly selected Public. Raw native privacy fields were unavailable, so a default SDK value alone was not treated as visibility evidence. Dataset numeric IDs below came from native readback, not from a UI field.

| Public dataset | Native ID | Downloadable files | Total file bytes | Contents and terms |
|---|---:|---:|---:|---|
| [CASMI Candidate Interop Kit](https://www.kaggle.com/datasets/prvsiyan/casmi-candidate-interop-kit) | 12541448 | 20 | 352,243 | Original MIT code, documentation, diagrams and invented fixtures. Kaggle displays “Other (specified in description)”. |
| [COCONUT Proton Ion Atlas](https://www.kaggle.com/datasets/prvsiyan/coconut-proton-ion-mass-index) | 12541801 | 20 | 33,288,188 | CC BY-NC-SA 4.0 numerical data and derivatives; original code and explanatory diagram separately MIT. |

The kit's initial creation response was inconclusive and remains recorded as such. Its later canonical public dataset and READY readback establish the release's current state; they do not retroactively turn that creation response into a raw accepted receipt. The atlas had an accepted creation response followed by a separate READY/public verification. **Server file contents were not downloaded or verified by SHA-256 in these publication checks.** Payload manifests describe their source releases; names and sizes alone do not prove content identity. No leaderboard result or scientific improvement follows from publication.

## Start with the interop kit

The [published source package](https://github.com/cubres/enveda-casmi-2026/tree/80fc6e202097bc353cb023efe17493ae8f539289/casmi-candidate-interop-kit) supplies inclusive mass-window and ion-conversion examples, explicit fingerprint-contract checks, stable ranking helpers and existing adverse tests. Its 12 mass rows and 2048/166-width bitfields are **invented**. They are neither chemical fingerprints nor model outputs; equal widths do not qualify a real Morgan/MACCS contract.

Use Python 3.10+ with NumPy. On Kaggle, add the dataset as an input and run its `quickstart.py` from the full input path, or copy the **whole flat package**, including arrays and manifest, into a new working folder. Copying only helper code omits its fixtures. For a downloaded flat package:

```sh
KIT_DIR=/path/to/kit
PYTHONDONTWRITEBYTECODE=1 python "$KIT_DIR/quickstart.py"
```

The example checks retrieval mechanics on invented candidates. Adapt the helpers only after binding your own mass/adduct convention, descriptor generator, packing order, model coordinates and row alignment. The kit does not verify those declarations for a real external bank.

## Query the ion atlas

The [published atlas source and documentation](https://github.com/cubres/enveda-casmi-2026/tree/15fd28118761a3cdab182456a622fb1748ded041/coconut-proton-ion-atlas) explain **436,389 real source positions** and eight declared theoretical protonation, charge and homodimer channels. The Kaggle release supplies the large `(436389,)` neutral-mass and `(8,436389)` theoretical precursor-m/z arrays; the GitHub source package does not include those large arrays.

Use NumPy and keep the Kaggle files together. The loader verifies its numerical manifests and channel transformations, then uses read-only memory maps. The existing quickstart checks a numerical source-row round trip, not identification of a competition molecule:

```sh
ATLAS_DIR=/path/to/atlas
PYTHONDONTWRITEBYTECODE=1 python "$ATLAS_DIR/quickstart.py" "$ATLAS_DIR"
```

The interval result is a range of zero-based positions in the exact version-2 `prvsiyan/coconut-casmi26-candidates` mass source. It is not a molecular accession or an InChIKey. Keep this source order intact. A separately sorted candidate bank requires a verified key mapping; the atlas's positions have not been joined to Aryan Awasthi's Morgan/MACCS bank. Eight theoretical ion channels do not establish observed adduct assignments, query coverage or structural uniqueness.

## Credits, rights and an experiment boundary

Credit **prvsiyan** for the attributed source candidate dataset and the **COCONUT team** for the natural-products collection. Credit **Aryan Awasthi** for the useful linked [Morgan/MACCS candidate bank](https://www.kaggle.com/datasets/aryanawasthiteykik/casmi26-coconut-morgan-maccs-fingerprints) and [spectrum-to-fingerprint MLP recipe](https://www.kaggle.com/datasets/aryanawasthiteykik/casmi26-spectrum-to-fingerprint-mlp). These companion products do not redistribute that publisher's implementation or learned weights.

Preserve the atlas's [numerical data attribution and NC-SA terms](https://github.com/cubres/enveda-casmi-2026/blob/15fd28118761a3cdab182456a622fb1748ded041/coconut-proton-ion-atlas/DATA_LICENSE.md). MIT licensing of original helpers grants no extra rights to linked numerical data, fingerprints, checkpoints or competition material. Restricted competition training structures and spectra are not included; do not redistribute them through a companion release. Verify the exact training-data, weight and code-sharing terms before combining external resources.

The [original fingerprint integration guide](https://github.com/cubres/enveda-casmi-2026/tree/69b91570b31a7357a0f755393bebe546babaeaf3/casmi-fingerprint-integration-guide) explains BIG packing, the 2048 + 167 + 1 layout, V2 model dimensions and the published ranking order. Real checkpoint compatibility and scientific quality remain unqualified there. These releases provide tools for reproducible checks; their publication is not a new score, and [Enveda V34](../enveda-v34-presentation-2026-10-12/STATUS_UPDATE.md) remains a terminal source-packaging run.
