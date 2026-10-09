# Dataset descriptions: completed and verified

The description updates were completed on **October 10, 2026, Sofia**, between **21:31:17 and 21:34:08 UTC on October 9**. This follows the preserved before-state audit in [README.md](README.md); its statements about missing cards describe that earlier snapshot.

| Dataset | Completed change | Description characters | Preserved data version and files |
|---|---|---:|---|
| [ChEBI + LIPID MAPS candidates](https://www.kaggle.com/datasets/prvsiyan/chebi-lipidmaps-casmi26) | Added the reviewed file dictionary, usage examples, diagrams, provenance and limitations to the previously empty card | 0 → 6,582 | Version 1; three files |
| [PubChem popularity counts](https://www.kaggle.com/datasets/prvsiyan/pubchem-popularity-counts) | Added the reviewed count semantics, lookup examples, missing-value guidance, provenance and limitations | 347 → 7,824 | Version 1; nine files |
| [Fingerprint models v2](https://www.kaggle.com/datasets/prvsiyan/casmi26-fp-models-v2) | Corrected one stale license-label sentence to match the current **CC BY-NC-SA 4.0** setting | 4,603 → 4,624 | Version 1; two files |

Each target received exactly one successful metadata update. Fresh reads immediately before and after the update verified its numeric identity, reference, title, public visibility, file inventory, version history, cover identity and all ten readable metadata settings. An independent comparison confirmed that only the description changed, apart from the audit timestamp. Existing files and license settings were preserved. The fingerprint bundle correction changes its description of the license label; it does not relicense upstream material.

The two full cards are byte-identical to the [reviewed original dataset package](https://github.com/cubres/enveda-casmi-2026/tree/95c4c821b5dec8ba903c425245b393d9139b997b/dataset-usefulness-2026-10-09). That package includes the original starter and diagrams. Keep its provenance and scientific limitations when adapting examples.

For reproducibility, the verified UTF-8 description SHA256 values are:

```text
chebi-lipidmaps-casmi26   af3869cff3ca81b58fc9e957379f4217884992966d15f4431267951f3c137453
pubchem-popularity-counts b795ef63eb449ee8016e6bdd39dfce8f6e99f6bf2bce3a72037510e2ac3011a0
casmi26-fp-models-v2      ddc00c159780202ef623695ec52d4ae3d3a950d595694a5f2026ea7d3cc8dba9
```

The live cards are useful documentation improvements. We have not measured a resulting vote, download or leaderboard increase, and neither description length nor a metadata success response establishes one. The next useful work remains a safe offline checkpoint compatibility example for the v2 bundle and carefully documented PubChem previews. New files would require a separately reviewed data-version action.
