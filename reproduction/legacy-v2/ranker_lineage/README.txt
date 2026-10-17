Recovered CASMI ranker source: review candidate only

The untouched original make_ranker3.py is in original_sources/. Its direct feature
recipe, FPNet architecture, scorer and relevant training/cache-producer sources
are retained byte-for-byte. The publication allowlist pins the original sources; RANKER_COMMANDS.txt records the prerequisites, build command and remaining gaps.

The local public rank_train.npz copy and up_rank3 copy are byte-identical by
streaming SHA256. Headers show X=(142762,31). No numerical arrays were loaded,
no pickle was deserialized, and no pipeline or model was executed.

This is not yet a complete one-command reproduction. The builder expects
several precomputed caches, and multiple historical scripts overwrite the same
logits cache path. The exact checkpoint/cache generation chain is unresolved.
The historical training seed is set after model initialization; ranker CV also
omits random_state. Do not describe this code as deterministic reproduction.

FP evidence uses raw logits, not probabilities: candidate_bits @ logits, six
within-query score features and six model-agreement features. FEATURE_COLUMNS.json
provides all 31 zero-based column names and formulas. Cached logits have width
6930; this is distinct from the later full-fingerprint V4/V6 serving lineage.

Source copies contain local-path references and historical comments but no
actual records, credentials, weight files or notebook identities. They retain
unsafe trusted-pickle loading present in the originals and must not be imported
or run against untrusted assets. The scoped source license is now documented in ../NOTICE and ../LICENSE-SOURCE
for the enumerated original/reconstructed source paths. This README grants no
additional rights over upstream data or dependencies. Preserve original sources,
caches and every notebook identity.

FP-cache boundary: columns 15–20 and 25–30 require the two exact cache inputs
`data/val_model_logits_combo.npy` (A) and `data/hard_model_logits.npy` (B).
`--model` only enables optional loading; it does not identify their producers.
A missing flag or missing cache silently yields twelve zero FP columns for the
corresponding query set. The original A producer remains unknown and B has
multiple writers. This release recovers the feature-builder contract; it does
not establish a byte-exact historical invocation or regeneration. Original
source files remain byte-for-byte preserved.
