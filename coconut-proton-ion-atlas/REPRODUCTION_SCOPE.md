# Reproduction scope

This repository packet contains original source, documentation, the two PNG figures, the 24-bin aggregate source-mass CSV, the channel table, numerical payload hashes and actual mechanics evidence. It deliberately omits the 27.9-MB ion matrix, the 3.49-MB neutral source file and the 1.67-MB repeated-mass table. The full payload belongs in the single Kaggle dataset; no molecule rows, spectra or weights have been added to this source packet.

To rebuild it, supply the exact attributed public COCONUT version-2 mass file, install NumPy and Pillow, and run `build_ion_index.py --source-mass /path/to/coco_mass.npy --output /path/to/a-new-directory`. The builder refuses a pre-existing destination. To query a full downloaded or rebuilt payload, call `open_release()` with that full payload directory. The hash inventories describe the full numerical release, rather than pretending the omitted large files exist in this GitHub folder.

The source SHA-256, immutable numerical matrix hash, original code, diagrams, mass-bin aggregates and actual local CPU result are recorded here. The verified maximum resident set size was 101,957,632 bytes and elapsed generation time was 0.52 seconds on the author machine; these are observations, not promises for another environment.

`PUBLIC_VALIDATION.json` separates 17 actual tests on invented fixtures from the full real numeric channel check and the example source-row query. No molecular identity, unknown-query coverage, model accuracy or competition score is claimed. Both source data and their numerical derivatives retain CC BY-NC-SA 4.0; original code and explanatory diagram retain MIT.

At packet creation, Kaggle creation and GitHub publication are pending root coordination. No future commit, public dataset receipt or score is fabricated in this packet.
