***************************************************************************
*
* Title:                 ChEBI SDF data dumps
*
* ChEBI Release:         256
*
* Date of last update:   2026-10-06
*
***************************************************************************

Contents of this directory:
---------------------------

README                               This file

LICENSE                              License data is released under:
                                     Creative Commons Attribution 4.0 International License.

chebi_lite.sdf.gz                    SDF format file for all compound structures. LITE variant includes 4 fields only:
                                     molfile, chebi_id (e.g. CHEBI:15377), chebi_name (e.g. water) and star (e.g. 3)

chebi_lite_3_stars.sdf.gz            SDF format file only for 3 stars compounds. Lite variant includes 4 fields
                                     mentioned above.

chebi.sdf.gz                         SDF format file for all compound structures. It has same information than the
                                     LITE variant plus synonyms, manual curated cross-references (WIP), chemical data (charge,
                                     mass, monoisotopicmass and formula), structure data (smiles, inchi and inchikey),
                                     secondary ids, and WURCS for carbohydrates. It is the most complete sdf version.

chebi_3_stars.sdf.gz                 Same than the above only for 3 stars compounds.


Final Notes:

Note that all SDF files exclude any ontological information as ontological classes are not able to be represented as they do not
contain a structure.
