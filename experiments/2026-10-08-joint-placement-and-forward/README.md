# 2026-10-08: joint tier placement rejected, forward-weight test predeclared

Three dated notes from the private research worker's Version 18 and the day's frontier read:

- [V18_JOINT_PLACEMENT_RESULT.md](V18_JOINT_PLACEMENT_RESULT.md): the matched diagnostic of fixed versus joint PubChem tier placement on 16 previously exposed public-development queries (MRR@25 0.9417 fixed vs 0.9375 joint). Only two queries opened the PubChem gate; in the one that lost, jointly ranked PubChem proposals took 21 of 25 slots and pushed the true pool candidate out. Decision: keep fixed slots. Query identities are reported only as hashes; this is a diagnostic on an exposed panel, not held-out evidence.
- [PUBLIC_FRONTIER_2026-10-08.md](PUBLIC_FRONTIER_2026-10-08.md): the public notebooks above our 0.340 (best 0.428; a byte-identical copy scored 0.423, so about 0.005 is noise). Ten of the eleven pulled notebooks mount our fingerprint models, ranker features and COCONUT bank and embed our engine as their second engine. Their main engine is non-commercial with unpublished training code, so we do not build on it.
- [F1_PREDECLARATION.md](F1_PREDECLARATION.md): the next official candidate, one line changed in the version behind our 0.340 (forward re-scoring weights ICEBERG 0 / GLACIER 1), with the decision rule fixed before any run: two draws; adopt if the mean is at least 0.348 and neither is below 0.340; reject if the mean is at most 0.341. It also corrects an earlier internal note: forward re-scoring was already on in that version.

No new official score is claimed here. Documentation is MIT like its siblings; data and model terms are unchanged.
