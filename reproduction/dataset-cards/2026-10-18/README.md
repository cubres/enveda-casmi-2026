# CASMI dataset cards and reproducibility boundaries

These cards bind the dataset versions observed on 18 October 2026 and separate uploader contributions, third-party licenses and competition reproducibility requirements. They accompany the [recovered source release](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/README.md) and the separate [selected V6 serving route](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/selected-v6-serving/README.md). Publishing these documents changes neither an existing dataset's license nor its visibility.

| Dataset | Observed version/access | What this update supplies |
| --- | --- | --- |
| [Fingerprint models](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/casmi26-fp-models-v2.md) | V1, public | S2/M1 bytes, original training commands, initialization/export limits |
| [Ranker features](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/casmi26-ranker-features.md) | V6, public | Exact 31-column contract, recovered builder and unresolved logit-cache lineage |
| [ChEBI + LIPID MAPS](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/chebi-lipidmaps-casmi26.md) | V1, public | Correct upstream license scope, candidate-bank schema and missing historical ingestion |
| [Legacy spectra/fingerprints](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/casmi26-spec-fp.md) | V1, private | Preparation chain, observed structure-role isolation and unsupported blanket CC0 concern |
| [Full fingerprint bank](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/casmi26-full-fingerprint-inputs.md) | V1, private | Distinct 10,395-bit route, exact selected checkpoint and missing portable role-creation chain |

Read [license scope](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/LICENSE-SCOPE.md) and [attribution](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/ATTRIBUTION.md) before reusing or redistributing inputs. Public accessibility alone does not establish permitted origins. A source-only release can expose and explain a remaining reproduction gap; it cannot certify that gap away.

The new [fingerprint contract demo](https://github.com/cubres/enveda-casmi-2026/blob/main/tools/fingerprint-contract/README.md) is immediately runnable with Python's standard library. Its invented fixtures show how to reject swapped 6,930/10,395-bit layouts, altered selection order and nonzero padding without loading pickle or a model. It contains no actual spectra, structures, roles or weights and makes no score claim.
