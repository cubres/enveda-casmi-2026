# Component-specific data terms

The ChEBI and LIPID MAPS molecular records retain **CC BY 4.0**. Preserve
`SOURCE_ATTRIBUTION.md` unchanged, identify ChEBI release 255 (2026-09-09) and
the LMSD snapshot downloaded 2026-10-03, and cite the original databases and
papers recorded in that notice. The input is the public
`sergiomalv/casmi-chebi-lmsd-structures` V1 source table; original SDF files are
not represented here as independently byte-verified downloads.

The new transformation computes the already-published V6 fingerprint definition
with its frozen selected-bit indices, exact neutral masses, raw-key joins and
separate canonical-group audit identifiers. It retains all original source
rows/IDs and records duplicate and mass-range flags. No competition spectra,
hidden test rows, labels, model weights, or prediction caches are included.
The inherited card's 2/3-star claim and statistics file's 1/2/3-star list are
not silently reconciled: actual source/quality counts must be reported by the
completed builder.

The exact V6 bit mask is a competition-training-derived selection artifact.
Its existing host-permitted component terms remain applicable; source licensing
does not relicense it. The original candidate bank is an input for integrity and
overlap checks and is **not redistributed** by this shard. Its own original
training-library/COCONUT terms remain separate.

New uploader code is Apache 2.0 (`LICENSE-SOURCE`). The byte-identical uploader
`metric_distinct.py` and extracted `group_identity.py` retain their original
source notices. Code licensing does not grant rights over underlying data.

Use an **Other/component terms** dataset label if distributing the V6 mask and
these mixed artifacts together. Do not label this bundle blanket CC0 or apply
Apache 2.0 to molecular records. This source packet establishes neither a
competition score nor permission for unrelated participant weights.

Original publisher licensing:

- https://www.ebi.ac.uk/chebi/about
- https://www.lipidmaps.org/terms-of-use
- https://creativecommons.org/licenses/by/4.0/

The PubChemLite mirrors are outside this implementation. Their CC0 labels do
not resolve the original publisher's CC BY 4.0 release terms or exact lineage.

For the distinct Mac adapter, the output is only a 512-row external source
sample and its numeric integrity artifacts, plus the separate old-bank canary
receipt. The full-shard transformation described above is not executed by that
adapter, and no completed full dataset is claimed.
