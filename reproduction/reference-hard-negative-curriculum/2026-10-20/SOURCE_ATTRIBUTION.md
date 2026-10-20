# ChEBI + LIPID MAPS LMSD candidate structures (standardised, with fingerprints)

98,433 small-molecule structures from ChEBI (2/3-star) and the LIPID MAPS Structure Database that are not in the
public COCONUT candidate set `prvsiyan/coconut-casmi26-candidates`, standardised with RDKit 2026.03.3 (largest
organic fragment, uncharged; entries with R-groups / dummy atoms, isotopes or no carbon dropped), keyed by the
standard InChIKey first block, with neutral monoisotopic masses and 6,930-bit packed fingerprints (the
"two-ranker" CASMI 2026 engine format). Built only from the public sources below; **no competition data** (no
spectra, ids, labels, or any filtering based on the competition training/test sets) is included or was used.

## Files
- `bio_structures.parquet` — inchikey14, smiles, source (ChEBI / LIPID MAPS LMSD), source_id, chebi_star, monoisotopic_mass.
- `bio_meta.pkl` (dict of lists: keys, smiles, source, src_id, star), `bio_mass.npy` (float64), `bio_fp.npy`
  (uint8, 867 bytes = 6,930 packed bits per structure), row-aligned.
- `stats.json` — build counts.

## Sources and licences (both CC BY 4.0)
- **ChEBI** (Chemical Entities of Biological Interest), EMBL-EBI, release 255 (2026-09-09), `chebi.sdf.gz` from
  https://ftp.ebi.ac.uk/pub/databases/chebi/SDF/ — Creative Commons Attribution 4.0 International
  (https://creativecommons.org/licenses/by/4.0/). Cite: Hastings J. et al., "ChEBI in 2016", Nucleic Acids Res.
  44:D1214 (2016).
- **LIPID MAPS Structure Database (LMSD)**, `LMSD.sdf.zip` from https://www.lipidmaps.org/databases/lmsd/download
  (downloaded 2026-10-03) — "All LIPID MAPS databases are licensed under a Creative Commons Attribution 4.0
  International License" (https://www.lipidmaps.org/terms-of-use). Cite: Sud M. et al., "LMSD: LIPID MAPS
  structure database", Nucleic Acids Res. 35:D527 (2007); Conroy M.J. et al., "LIPID MAPS: update to databases and
  tools for the lipidomics community", Nucleic Acids Res. 52:D1677 (2024).

## Changes made
Structures were standardised and re-encoded (SMILES, InChIKey14, fingerprints, masses) as described above, and
entries whose InChIKey14 appears in `prvsiyan/coconut-casmi26-candidates` (public, CC BY 4.0) were removed.
Counts: 98,433 structures (ChEBI 77,997: 59,770 2-star + 18,227 3-star; LMSD 20,436); 162,180 unique before
the COCONUT removal.

Dataset licence: **CC BY 4.0** — please keep the attribution above.
