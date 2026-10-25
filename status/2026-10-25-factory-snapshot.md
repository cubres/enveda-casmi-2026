# CASMI factory status — 25 October 2026

## Official result

The latest completed submission for prvsiyan is **0.456 MRR@25** (submission 57448206, completed 20 October). The current public leaderboard top observed on 25 October is **0.504**. These are official leaderboard scores, not validation results.

- [Competition leaderboard](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/leaderboard)
- [Competition data and scoring contract](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/data)

## Data rights and database work

The existing COCONUT candidate bank and proton-ion atlas list **CC BY-NC-SA 4.0** for their data. The host says winning solutions must allow commercial use and redistribution, and external data, models, and tools must be compatible. We therefore do not treat those assets as cleared for a prize-eligible solution.

A separate public COCONUT MetFrag source file is being assessed as a possible CC BY 4.0 source. In a deterministic sample, its stored InChIKey14 differed from the competition’s pinned tautomer-canonical key on **942 of 9,987 valid structures**. A complete exact-key rebuild was estimated at about 59 minutes and was not run. No replacement dataset has been published.

- [Host licensing clarification](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/741359)
- [Zenodo COCONUT source record](https://zenodo.org/records/5336447)

## Next experiment

First qualify a useful source-only mass index that preserves original row identity and makes no scorer-key claim. If its source, schema, mass channels, checksums, and quickstart pass review, publish it as a new dataset. Keep all competition spectra and labels out of that release. Then test it on identity-disjoint training splits. No notebook update or new submission was made in this snapshot.
