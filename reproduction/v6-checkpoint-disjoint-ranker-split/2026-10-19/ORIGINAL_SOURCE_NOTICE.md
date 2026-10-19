# Source attribution and scope

The original uploader-authored grouping sources are already published in the CASMI campaign repository:

- metric_distinct.py: https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/full-fingerprint-preparation/2026-10-18/role-sources/metric_distinct.py ; SHA256 b4c0bbbafca0d821d872733d28f39518f41be53004970a9eeb725aef94a47b4f.
- partition_public.py: https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/full-fingerprint-preparation/2026-10-18/role-sources/partition_public.py ; SHA256 20302057f22303340ed339360d3c43ad2d9f7da2bccc9dcdc0b193af8073b9fc.

The bundled metric helper is byte-identical. The bundled group_identity.py contains the unchanged AST of the pure identifier function, with its minimal imports and a new scope notice. It avoids importing the original data-preparation module. The new standalone rebuild and inspector are uploader-authored Apache2.0 software.

Grouping is an original implementation of the published metric specification: https://www.kaggle.com/code/metric/casmi-mean-reciprocal-rank . This packet does not appropriate another participant's notebook or claim an upstream score as its own. Software licensing does not change the molecular metadata's component terms.
