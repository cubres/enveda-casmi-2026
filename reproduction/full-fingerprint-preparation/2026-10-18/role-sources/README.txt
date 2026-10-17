Original role metadata generation for the full10395 fingerprint bank

For training from the supplied full-bank inputs, use the provided
roles_by_structure.b64 directly. The original full-bank trainer reads that file
from its --data directory and authenticates its decoded table. Regenerating the
partition is not required merely to consume the prepared training inputs.

This folder supplies the exact four original source files behind that role table.
They were copied without edits and were not executed for this source release.
SOURCE_INDEX.json records their hashes, upstream input pins and output contracts.
No role assignments, keys, SMILES, spectra, labels, model weights or predictions
are embedded in this source folder.

HOW THE SUPPLIED ROLE FILE IS USED

The table is aligned to the 275,810 rows of the original training fp_meta.pkl,
not to the 711,705 candidate-pool rows. Role codes are:

  0  optimizer
  1  checkpoint_selection
  2  fusion_selection
  3  final_test; also the default for structures with no spectra

The full trainer maps structure roles to spectra through spec.npz['six']. It
trains on role 0 spectra whose structures exist in the candidate pool. It chooses
checkpoints on role 1 spectra with even structure indices and a pool match.
Role 1 odd structures are reserved for later ranker work. This trainer does not
select role 2 or role 3 spectra for fitting or checkpoint selection.

The encoding is two bits per structure, most-significant bit first, packed with
NumPy packbits, compressed by zlib and encoded as base64. The supplied staged file
has 55,913 bytes, including its final newline:

  encoded-file SHA256:
  fe654a3f5f655df3897a344ca222e01a9f555a7dfd22a786e6cb32b126c76049

  decoded uint8 role-table SHA256, checked by the original trainer:
  4d7b366293225a1ae67dfc0306480129b9ac1351a6d8581f0be40a269bdaff86

The role generator originally writes 55,912 base64 characters without a newline.
The full-bank builder writes the stripped text plus one newline. These encoded
file bytes and the decoded-role bytes have different hashes by design. The full
trainer hardcodes the decoded hash. The fingerprint builder additionally reads
roles_by_structure.sha256 containing that decoded hash.

WHAT EACH ORIGINAL FILE DOES

metric_distinct.py provides the pinned grouping rule. It requires RDKit 2026.03.3
and groups structures by heavy-atom composition plus tautomer-canonical InChIKey14.
It contains original code implementing the referenced CASMI metric specification:
https://www.kaggle.com/code/metric/casmi-mean-reciprocal-rank

partition_public.py canonicalizes the union of own-corpus and MassSpecGym1.5
structure strings. It gives each canonical group a deterministic hash bucket,
then emits canonical_structures.tsv, group_partitions.tsv and aligned corpus
partition tables. It also writes an input/hash manifest and aggregate receipts.

filter_references.py authenticates the partition artifact manifest and exact
spec.npz, structure-metadata and source-row joins. It propagates structure roles
through six and emits spectrum_role_codes.npy, plus optimizer-only spectrum,
source and structure indices. It also emits audit tables and an auxiliary blind
candidate table derived from the own training catalogue.

make_role_table.py reads spectrum_role_codes.npy and spec.npz['six'], verifies
that each structure has one consistent role, and packs the per-structure table.
It emits roles_by_structure.b64, roles_by_structure.sha256, receipt.json and a
historical trainer_patch.txt describing the split change. It runs at module top
level and writes to its working directory; importing it would perform work.

PARTITION RECIPE AND PRIOR EXPOSURE

This is author-derived partition metadata, not a competition-provided split.
For group_id, the initial assignment is the first eight bytes, big-endian, of
SHA256('glacier-prospective-v1-20260930:' + group_id), modulo 10,000:

  0..7,999      optimizer              80%
  8,000..8,999  checkpoint_selection   10%
  9,000..9,499  fusion_selection        5%
  9,500..9,999  final_test              5%

These are bucket proportions, not promised final dataset proportions. Every
group matching the 819 historically queried keys is forced to optimizer. Among
the other groups in the old 2,750-key checkpoint-selection set, a final_test
assignment is remapped to optimizer. The original source records exposure flags;
the historical weights are not made independent of those exposures by this table.
MassSpecGym's original fold is retained for audit and does not assign these roles.

MassSpecGym supplies structural canonical-group references to this split/audit
pipeline. It does not cause these four files to add MassSpecGym query molecules
to the full candidate pool or append MassSpecGym spectra to spec.npz. The full
711,705-row pool separately comes from the existing training/COCONUT pipeline.
Its 436,389 novel rows are candidates, not additional training spectra, and do not
receive entries in the 275,810-row training-role table. The auxiliary candidate
table emitted by filter_references.py is not the full COCONUT-containing pool.

ORIGINAL COMMAND FORMS AND INPUTS

The following commands document the original invocation forms. In the retained
workspace the output folders already exist. To regenerate, use a new reproduction
layout and review the explicit path mappings while preserving these originals.
The copies retain historical absolute and root-relative paths; placing these
four files in one folder is not by itself a portable one-command reconstruction.
No wrapper here launches a computation or mutates a notebook.

1. From a fresh directory corresponding to enveda_glacier_partition_20260930T165020Z:

     nice -n 5 python partition_public.py --seconds 1200 --workers 2

   Requires exact MassSpecGym1.5.tsv and sample_input.tsv; metric_distinct.py;
   up_train/fp_meta.pkl and split.pkl; data/c2_np_recs2.pkl and hard_feats.pkl.
   The query caches supply historical-exposure keys, not prediction quality.
   Complete input hashes and sizes are in SOURCE_INDEX.json and the original code.
   The source writes canonical/group/corpus tables, exclusions, input/protocol
   records, summary.txt and artifacts.tsv. Incomplete canonicalization is marked
   INCOMPLETE_NO_PARTITION; it is not an accepted finished partition.

2. From a fresh directory corresponding to enveda_glacier_references_20260930T172626Z:

     nice -n 5 python filter_references.py

   Requires the exact fourteen-file partition artifact manifest and its files;
   up_train/spec.npz and fp_meta.pkl; data/struct_fp_meta.pkl and train_meta.parquet;
   and the pinned original build_dataset.py source. It verifies exact source-row
   and structure joins before writing spectrum_role_codes.npy and filtered indices.

3. From a fresh working directory corresponding to clean_fp_split_20261002T1652Z:

     python make_role_table.py

   Requires the exact spectrum_role_codes.npy and original up_train/spec.npz.
   Writes the four role-table artifacts listed above to the working directory.
   The source uses ordinary write mode for those outputs; do not invoke it in
   a directory containing the preserved originals.

metric_distinct.py is an imported helper, not a separate data-generation command.
Dependencies across this closure include NumPy, pandas, PyArrow and RDKit. RDKit
2026.03.3 is enforced by the grouping helper; the historical sources do not pin
every other package version. Source publication does not establish a fully pinned
runtime or authorize a resource allocation.

SOURCE, DATA AND PRIVACY SCOPE

The owner licenses only the following four original Python source files under
the Apache License, Version 2.0: metric_distinct.py, partition_public.py,
filter_references.py and make_role_table.py. See LICENSE-SOURCE for the full terms
and NOTICE for the copyright attribution and scope. Their original source bytes,
headers and public metric attribution remain unchanged.

This scoped source license does not license third-party dependencies, MassSpecGym,
COCONUT, competition data, role/data artifacts or other files in the repository.
Their existing terms and rights remain separate. No upstream grant is inferred.
The complete LICENSE-SOURCE text is an unmodified copy from the official URL:
https://www.apache.org/licenses/LICENSE-2.0.txt
SHA256: cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30

Historical /Users/cubres/... paths remain for byte-exact provenance and expose
the already-public account's local folder layout. They contain no credentials.
The originals use trusted local pickle reads, so their file hashes and input
provenance matter; they are not general-purpose loaders for arbitrary pickles.
No role values or source datasets were read or decoded while staging this folder.
