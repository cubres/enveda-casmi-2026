# Data and code terms: source-only package

The current public tree contains source code, documentation, a synthetic mechanics example, and execution provenance. It does **not** distribute the generated curriculum CSVs or row-level JSON outputs.

## Input data

The ChEBI records and derived structure representations retain the attribution and CC BY 4.0 scope described in [SOURCE_ATTRIBUTION.md](SOURCE_ATTRIBUTION.md) and [SOURCE_COMPONENT_LICENSE.md](SOURCE_COMPONENT_LICENSE.md). The upstream [ChEBI licence statement](https://www.ebi.ac.uk/chebi/about) identifies CC BY 4.0. The reference-mass atlas keeps its own component terms and attribution at its [immutable public source commit](https://github.com/cubres/enveda-casmi-2026/tree/8f2fd96360ddeb878053bc89298401657fe3e25d/reproduction/reference-mass-ambiguity-atlas/2026-10-20).

The selected 10,395-bit fingerprint mask is associated with the public Kaggle dataset [prvsiyan/casmi26-full-fingerprint-inputs, V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-full-fingerprint-inputs/versions/1) and is described as competition-training-derived. This package's review did not establish its exact redistribution terms. A public URL or the presence of an uploader's licence label is not a new grant over the mask or derived fields.

For that reason, the previously published fingerprint-derived tables and row-level example were removed from the current `main` branch. Earlier commits may retain historical copies; do not redistribute or rely on those copies until the component terms are confirmed. This is a precautionary publication hold, not a legal finding.

No blanket CC0, Apache, or CC BY licence is offered for any aggregate data. Independently licensed positive spectra and a qualified chemical join would also be required before supervised optimizer use.

## Source code

Newly authored Python files carry SPDX-License-Identifier: Apache-2.0 where marked and are accompanied by [LICENSE-SOURCE](LICENSE-SOURCE). This license applies to marked code only; it does not relicense molecular records, masks, input datasets, imported code, or dependencies.
