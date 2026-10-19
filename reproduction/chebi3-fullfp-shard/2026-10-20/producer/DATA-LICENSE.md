# Component-specific data terms

This packet preserves the original public source datasets and their identities.
It defines a new subset and representation; it does not replace or relicense
the source collections.

## ChEBI molecular records and derived representation: CC BY 4.0

The selected source is sergiomalv's **ChEBI + LIPID MAPS structures (CASMI
2026)**, Kaggle dataset ID 12431882, version 1:
https://www.kaggle.com/datasets/sergiomalv/casmi-chebi-lmsd-structures/versions/1 .
Preserve the downloaded original `ATTRIBUTION.md` unchanged with redistributed
source rows or derived records. Attribute the uploader and original databases,
retain their citations and source identifiers, link the licence, and describe
additional changes.

The selected subset uses ChEBI-source records only. The source card identifies
ChEBI release **255 (2026-09-09)** from
https://ftp.ebi.ac.uk/pub/databases/chebi/SDF/ . ChEBI's official data licence is
**Creative Commons Attribution 4.0 International**:
https://www.ebi.ac.uk/chebi/about and
https://creativecommons.org/licenses/by/4.0/ . Preserve the ChEBI citation
supplied in the original attribution: Hastings et al., *ChEBI in 2016*, Nucleic
Acids Research 44:D1214 (2016).

The original mixed collection also contains LIPID MAPS records. Their database
terms are CC BY 4.0 at https://www.lipidmaps.org/terms-of-use . This subset
selects `source == "ChEBI"`; it must not claim to contain LMSD-selected rows.
Retaining the mixed collection's original attribution also preserves its
original source context and the Sud et al. and Conroy et al. citations.

Additional changes for this proposed artifact are raw-key exclusion against the
existing bank, literal ChEBI three-star selection, finite 80–1,400 Da mass
filtering, deterministic 64-bin mass-balanced selection of 4,096 raw keys, and
re-encoding under the separately pinned full fingerprint definition and frozen
selected-bit mask. Record actual exclusions and joins when the coordinator
executes the qualified build. Source metadata and raw-key filtering do not
establish a new official metric identity or higher competition score.

## Existing V6 mask and other copied input components: separate terms

`prvsiyan/casmi26-full-fingerprint-inputs` V1, ID 12350648, remains an existing
public input with its separately documented competition-training-derived
component terms. This document does not grant CC BY, Apache 2.0 or CC0 rights to
the mask, training-derived metadata or any other copied component. Preserve the
existing notices and exact input hashes; do not redistribute the old bank as
part of this external-only subset. If a final release includes components with
different terms, use explicit per-file scope and **Other/component terms** for
the aggregate instead of assigning a blanket licence.

## Newly authored code: Apache 2.0

The new selector, budget utility and synthetic tests are source code, licensed
under Apache 2.0 as stated by `LICENSE-SOURCE`. Imported code retains its own
licence. Code licensing does not change molecular-record or frozen-mask terms.

## Scope limits

This source-only packet contains no new model weights, training labels,
competition spectra, completed assay results or verified submission score.
The 4,096-row selection and its numerical outputs still require the
coordinator's actual validation. No PubChemLite CC0 claim is inherited or used.
