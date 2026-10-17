# License scope and permitted data access

This notice distinguishes the uploader's contributions from third-party inputs. It does not replace those inputs' licenses or authorize use of restricted data. The prepared-input dataset identities, licenses, descriptions, V1 file inventories and anonymous public access were verified on 18 October 2026 after their in-place release.

| Component | Observed terms / provenance | Scope |
| --- | --- | --- |
| `casmi26-fp-models-v2` V1 | Published Kaggle label: CC BY-NC-SA 4.0 | Existing uploader-selected terms for the checkpoint bundle; no new license is granted over its training sources. |
| `casmi26-ranker-features` V6 | Published Kaggle label: CC BY-NC-SA 4.0 | Existing uploader-selected terms for contributed feature data; original source data keeps its own terms. |
| `chebi-lipidmaps-casmi26` V1 | Published Kaggle label: CC BY-NC-SA 4.0 | This label must not be read as relicensing the underlying ChEBI or LIPID MAPS databases. Historical source-release provenance still needs its own binding. |
| `casmi26-full-fingerprint-inputs` V1 | Public; Other (specified in description) | Exact training-derived metadata/counts/role assignments plus training–COCONUT candidate bank. Host-permitted training artifacts and original component rights remain distinct; see its dataset description. |
| `casmi26-spec-fp` V1 | Public; Other (specified in description) | Prepared provided-training spectra, structure fingerprints and exact legacy split. Corrected component-specific notice replaces the unsupported blanket CC0 label. |
| `casmi26-pool` V1 | Public; Other (specified in description) | Aligned 6,930-bit training–COCONUT candidate pool required by the original S2/M1 trainers; it is distinct from the 10,395-bit full bank. |
| Legacy preparation, FPNet, S2/M1 trainers and ranker source | Apache 2.0, limited to the 29 source paths in its `NOTICE` | Original/reconstructed source only; all original code bytes and attributions retained. Excludes upstream data, weights, dependencies and the unlisted documentation/metadata files. |
| Selected V6 training source | Apache 2.0, scoped by its `LICENSE-SOURCE` and `NOTICE.md` | Original five-file trainer/model closure, archived training cell and named supporting source/documentation; excludes data, weights and dependencies. |
| Original full-bank role-generation source | Apache 2.0, scoped by `LICENSE-SOURCE` and `NOTICE` | Only the four named original Python files; excludes generated role artifacts, upstream data, dependencies and other repository files. |
| New fingerprint-contract tool and invented fixtures | MIT, as scoped in their `LICENSE-CODE.txt` | Original code and invented test data only. No external spectra, structures or checkpoints are included. |

The existing NC-SA labels are the observed publisher choices. This update does not infer that the publisher intended CC0, MIT or a different license for the existing data bundles. The three prepared-input datasets now use Other with explicit component terms; this does not change the three existing NC-SA bundle labels or grant blanket rights over upstream records.

## Third-party material

- **ChEBI:** the [official licensing page](https://www.ebi.ac.uk/chebi/about/) identifies CC BY 4.0. Preserve attribution, the license link, source identifiers and the changes made. The current notice does not identify the historical downloaded release used for an old derived bank.
- **LIPID MAPS:** its [terms](https://www.lipidmaps.org/terms-of-use) identify CC BY 4.0 for its databases. Follow the [resource-specific citation guidance](https://www.lipidmaps.org/how-to-link), retain LM identifiers when available, and describe transformations.
- **COCONUT:** the [publisher's about page](https://coconut.naturalproducts.net/about) identifies CC0 for its curated dataset and MIT for infrastructure code. These are separate scopes. Retain release provenance and source citations; the Kaggle companion bundle's separate label does not change the original database's terms.
- **Competition training data:** obtain it through the [competition](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra), with the permitted constituent sources and applicable conditions. Do not treat a compilation or its preprocessing as a blanket grant to every source. Hidden test data is not part of this source release.

Original data remains available under its own license; a narrower notice on an uploader's original additions cannot revoke rights already granted in that original material. See the official [CC BY](https://creativecommons.org/licenses/by/4.0/), [CC BY-NC](https://creativecommons.org/licenses/by-nc/4.0/) and [CC BY-NC-SA](https://creativecommons.org/licenses/by-nc-sa/4.0/) terms. Software licenses do not automatically license model-training data, and a checkpoint's license does not automatically attach to independently obtained candidate structures.

## Competition reproducibility requirements

The hosts' [14 October clarification](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/748882) requires original training code and access to permitted training data for reused participant weights, including leaderboard or medal submissions. Publishing a weight file or calling a dataset public is insufficient. Preserve the original training/preprocessing recipe when reproducing a checkpoint; proposed preprocessing changes are separate experiments.

In the [training-data discussion](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/745072), hosts allow artifacts derived from the open training compilation and permit some open noncommercial sources. This is eligibility guidance, not a new blanket CC0 license. Proprietary or prohibited source material is not made permissible by repackaging it.

## What publication must make explicit

Each release needs a version/file-hash manifest, original source and train/prep/build commands, the exact model architecture and fingerprint selection, and its split/initialization provenance. A reconstructed export bridge must be labelled as reconstructed. If a historical source snapshot or random initialization is unbound, say so; do not promise byte-identical retraining. Keep competition eligibility, copyright permissions and public accessibility as separate checks.

## Prepared inputs now publicly accessible

The same existing identities and data versions are available at [spec-fp V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-spec-fp/versions/1), [legacy candidate pool V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-pool/versions/1) and [full fingerprint inputs V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-full-fingerprint-inputs/versions/1). Their 5/3/9 file inventories and exact payload bindings were retained through the metadata and visibility changes. Publication did not regenerate files or train new checkpoints.

The retained spectra contain 2,334,531 prepared rows with verified joins to the provided training compilation. Both candidate banks have the same 711,705 structure/SMILES pairs in the same order: 275,316 from the training metadata and 436,389 additional COCONUT structures. The bounded checks establish those origins and alignments; they do not constitute a new model evaluation, full chemical rebuild or independent audit of every upstream library record.

The original [legacy training recipe](https://github.com/cubres/enveda-casmi-2026/tree/main/reproduction/legacy-v2) consumes the supplied `spec.is_val` split and matching 6,930-bit pool. The [selected V6 training source](https://github.com/cubres/enveda-casmi-2026/tree/main/reproduction/selected-v6-training/2026-10-18) uses the separately documented full-bit contract and explicit author-created roles. The [original role-generation sources](https://github.com/cubres/enveda-casmi-2026/tree/main/reproduction/full-fingerprint-preparation/2026-10-18/role-sources) retain their actual historical-exposure rules; the provided role file can be consumed directly without regenerating that history. Public access does not promise bit-identical historical checkpoints or resolve the separate historical ranker-cache producer question.

The legacy source grant is enumerated in [NOTICE](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/NOTICE), with the complete [Apache 2.0 text](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/LICENSE-SOURCE) and [per-file source/header audit](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/SOURCE_LICENSE_AUDIT.json). The 29 source paths are licensed explicitly; a repository-wide or third-party data grant is not inferred.
