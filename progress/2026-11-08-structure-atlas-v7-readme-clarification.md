# CASMI Structure Atlas v7 README clarification

**Observed:** 2026-11-08 17:04 UTC. The public dataset `prvsiyan/casmi-structure-atlas-v2` (Kaggle dataset ID `12875911`) is public, CC0, and currently reports version 7. [Open the dataset](https://www.kaggle.com/datasets/prvsiyan/casmi-structure-atlas-v2).

The README now explains the different scopes of two receipts:

- `validation.json` records checks performed by the published dataset builder.
- `release-validation.json` records the later preflight checks for the release payload.

A fresh download of the current version confirmed the README correction. The Parquet data and source manifest are unchanged: SHA-256 `b2603bc552c921cdc35ec0639fc7edc783cb9fb96d2d1c46fb0e07baaebc1d17` and `edc7a8ae76eed9ce77f0cb9c5f115c6f5d4fb1f0685ff467e291b76aee683e33` respectively. Kaggle reported 22 files and usability rating `1.0` (maximum).

The version upload command was retried while the first upload was still reported in progress. Kaggle now reports version 7, so two versions may have been created with identical payloads. No version or dataset file was deleted.

This documentation change does not claim a new competition score or vote increase. CASMI submission row `58131924` was still pending at the latest check, so no notebook push or submission followed.
