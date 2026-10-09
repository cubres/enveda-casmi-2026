# Dataset cards: verified gaps and a licensing correction

Read-only audit performed on October 10, 2026, Sofia; primary responses were captured on October 9 at 21:17–21:22 UTC. No dataset mutation was made by this audit.

| Dataset | Data version | Description characters | Votes | Downloads | Notebook attachments |
|---|---:|---:|---:|---:|---:|
| [ChEBI + LIPID MAPS candidates](https://www.kaggle.com/datasets/prvsiyan/chebi-lipidmaps-casmi26) | 1 | 0 | 1 | 1,187 | 263 |
| [PubChem popularity counts](https://www.kaggle.com/datasets/prvsiyan/pubchem-popularity-counts) | 1 | 347 | unknown: omitted | 61 | 1 |
| [Fingerprint models v2](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v2) | 1 | 4,603 | 9 | 3,151 | 269 |
| [Fingerprint models v4](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v4) | 1 | 4,505 | 5 | 120 | 10 |

ChEBI and PubChem retain their original public dataset identities and complete version-1 file inventories. Their cards have not yet received the prepared descriptions. The [published dataset package](https://github.com/cubres/enveda-casmi-2026/tree/95c4c821b5dec8ba903c425245b393d9139b997b/dataset-usefulness-2026-10-09) supplies file dictionaries, diagrams, provenance limits and original NumPy examples. Fresh commit-pinned reads verified that both card drafts and the starter are byte-identical to the reviewed local publication. The starter's earlier invented-boundary tests are evidence about lookup/window logic; they do not certify every real fingerprint or count.

The two highest-vote cards are already substantial. The v2 model bundle needs one precise correction: current `GetDataset` and `GetDatasetMetadata` responses both report **CC BY-NC-SA 4.0**, while its unchanged description still says **CC0-1.0**. Correct the sentence to describe the current label, preserving the license setting and all attribution. The audit cannot determine when or why the setting changed. For v4, the description's CC0 label agrees with the current setting.

The [official metadata route](https://github.com/Kaggle/kaggle-cli/blob/main/docs/datasets_metadata.md) permits metadata changes separately from a new data version. A description-only CLI JSON is insufficient: the installed client reconstructs other settings from default values. Concrete local previews preserve the complete fresh settings and change only `description`; a coordinator must refresh them before use and verify the exact resulting card, identity, license, privacy, files and version afterwards. No upload success message is substituted for that read-back evidence.

After the two missing cards and the stale license sentence are addressed, the next useful addition is a safe, offline checkpoint compatibility example for the widely attached v2 bundle. A small PubChem preview would also help readers inspect the count semantics, but adding a new file to that dataset is a separate data-version action. Neither description length nor a synthetic compatibility check establishes a leaderboard improvement or guarantees more votes.

The owner inventory was limited to the first public page sorted by votes. List responses omit descriptions; separate card reads supplied the counts above. Missing vote fields remain unknown. Existing notebooks, datasets, versions and files were preserved throughout.
