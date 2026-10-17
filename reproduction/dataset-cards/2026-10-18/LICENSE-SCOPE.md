# License scope and permitted data access

This notice distinguishes the uploader's contributions from third-party inputs. It does not replace those inputs' licenses or authorize use of restricted data. The dataset metadata was checked on 18 October 2026.

| Component | Observed terms / provenance | Scope |
| --- | --- | --- |
| `casmi26-fp-models-v2` V1 | Published Kaggle label: CC BY-NC-SA 4.0 | Existing uploader-selected terms for the checkpoint bundle; no new license is granted over its training sources. |
| `casmi26-ranker-features` V6 | Published Kaggle label: CC BY-NC-SA 4.0 | Existing uploader-selected terms for contributed feature data; original source data keeps its own terms. |
| `chebi-lipidmaps-casmi26` V1 | Published Kaggle label: CC BY-NC-SA 4.0 | This label must not be read as relicensing the underlying ChEBI or LIPID MAPS databases. Historical source-release provenance still needs its own binding. |
| `casmi26-full-fingerprint-inputs` V1 | Private; metadata says CC BY-NC 4.0 | Mixed derived input bank. The label does not establish every constituent's terms or make the data publicly available. |
| `casmi26-spec-fp` V1 | Private; metadata currently says CC0; card is empty | The CC0 label is not evidence that the uploader may waive rights in competition-derived spectra. A component-specific correction is required before a public release. |
| New fingerprint-contract tool and invented fixtures | MIT, as scoped in their `LICENSE-CODE.txt` | Original code and invented test data only. No external spectra, structures or checkpoints are included. |

The existing NC-SA labels are the observed publisher choices. This update does not infer that the publisher intended CC0, MIT or a different license for the existing data bundles. No broad relicensing is proposed.

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
