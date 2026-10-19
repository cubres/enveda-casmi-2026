# Cache component terms — Other

The new cache uses only the exact already-public V1 prepared training spectra,
full fingerprint bank/role metadata, and selected V6 checkpoint named in the
README. It exports derived model predictions and the public query/structure/
source-row/pool joins and packed training targets needed to use those
predictions. It does not export raw spectra or competition test data.

The competition hosts' [provided-training-data clarification](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/745072)
permits qualifying artifacts derived from the open provided training compilation;
the noncommercial provision was intended for test data. This cache relies on
that provided-training-artifact permission. The uploader does not grant new
rights over every constituent library record or waive the contributors' terms.
Consult and retain the original [training-data source attribution and conditions](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/data).

The candidate bank combines provided training structures with the original
COCONUT September 2026 snapshot. COCONUT's publisher specifies CC0; credit its
[original authors and dataset](https://coconut.naturalproducts.net/about).
That component does not make the complete cache blanket CC0.

The exact source-input cards are:

- [Spectrum cache V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-spec-fp/versions/1)
- [Full fingerprint inputs V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-full-fingerprint-inputs/versions/1)
- [Selected checkpoint V1 and its parameter-use permission](https://www.kaggle.com/datasets/prvsiyan/casmi26-v6-structure-uniform-checkpoint/versions/1)

Retain the campaign [component attribution](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/ATTRIBUTION.md)
and [license-scope notice](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/LICENSE-SCOPE.md).
The checkpoint's `LICENSE-WEIGHTS.md` applies to its parameters; the original
training sources keep their own scoped Apache 2.0 grant and attribution.
The new builder, verifier and documentation are uploader-authored software under
the adjacent `LICENSE-SOURCE`; that software license does not relicense data or
weights. Record the source-input versions and all runtime output hashes with
any redistribution. No proprietary source redistribution is authorized here.
