# Component-specific data and code terms

## ChEBI records and derived representations: CC BY 4.0

The molecular records are selected from sergiomalv's public
[ChEBI + LIPID MAPS structures, version 1](https://www.kaggle.com/datasets/sergiomalv/casmi-chebi-lmsd-structures/versions/1),
Kaggle dataset ID 12431882. Retain the exact original `SOURCE_ATTRIBUTION.md`
with redistributed source rows or derived representations. Attribute the
uploader and original databases, preserve source identifiers and citations,
link the licence and describe additional changes.

This subset selects ChEBI-source records only. The source collection identifies
ChEBI release **255 (2026-09-09)** from the
[ChEBI SDF distribution](https://ftp.ebi.ac.uk/pub/databases/chebi/SDF/).
[ChEBI's official licence statement](https://www.ebi.ac.uk/chebi/about) specifies
[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).
Preserve the source citation: Hastings et al., *ChEBI in 2016*, Nucleic Acids
Research 44:D1214 (2016).

The original mixed collection also includes LMSD records, whose database terms
are [CC BY 4.0](https://www.lipidmaps.org/terms-of-use). Its original attribution
preserves the Sud et al. and Conroy et al. citations. This shard does not claim
to contain LMSD-selected rows or to reconstruct the complete original SDF
preparation from historical upstream files.

Additional changes are raw-key exclusion against the existing candidate bank;
literal ChEBI three-star and finite 80–1,400 Da mass filtering; deterministic
64-bin selection of 4,096 unique raw keys; and re-encoding with the declared
full fingerprint definition and frozen ordered mask. Exact source joins and
computed fields are retained. These transformations do not establish official
metric novelty, hidden-answer coverage or a score improvement.

## Frozen V6 mask and copied input components: separate existing terms

The frozen selection mask originates in
[`prvsiyan/casmi26-full-fingerprint-inputs`, V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-full-fingerprint-inputs/versions/1),
dataset ID 12350648, with separately documented competition-training-derived
component terms. This document does not grant CC BY, CC0 or Apache rights to
that mask, other training-derived metadata, competition data or model weights.
Preserve the existing notices and exact component hashes. The old candidate
bank and its pickle files are not part of this external-only shard.

When components have different terms, the aggregate dataset must use explicit
per-file component scope and **Other/component terms**. Do not relicense the
entire bundle as CC0 or Apache 2.0.

## Newly authored code: Apache 2.0

The new demonstration, tests and original preparation code carry Apache 2.0
where stated by their source notices and `LICENSE-SOURCE`. Imported code
retains its own licence. Code licensing does not change molecular-record,
frozen-mask or other data terms.

No PubChemLite mirror or its disputed CC0 claim is included. No licence or
scientific claim is made here for competition labels, model checkpoints,
unrelated third-party dependencies or notebook identities.
