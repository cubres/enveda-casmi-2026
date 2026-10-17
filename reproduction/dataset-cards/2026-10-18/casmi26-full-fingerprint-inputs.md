# CASMI26 full fingerprint inputs: V1 scope and reproduction boundary

[Dataset V1](https://www.kaggle.com/datasets/prvsiyan/casmi26-full-fingerprint-inputs/versions/1), id **12350648**, was **private** on 18 October 2026. The current metadata label is **CC BY-NC 4.0**. This is the 10,395-target input bank for the later full-fingerprint route, not a substitute for the legacy 6,930-target bundles.

| File | Current V1 listed bytes |
| --- | ---: |
| `pool_fp.npy` | 925216628 |
| `pool_mass.npy` | 5693768 |
| `pool_meta.pkl` | 64843052 |
| `fp_bits.npy` | 83288 |
| `fp_meta.pkl` | 17095875 |
| `optimizer_bit_counts.npy` | 83384 |
| `roles_by_structure.b64` | 55913 |
| `FULL_FINGERPRINT_MANIFEST.json` | 3347 |
| `README.md` | 907 |

The existing owner description states that the bank preserves 711,705 candidate rows and selects 10,395 nonconstant target bits using optimizer-role structures only. Role indices refer to trainer metadata order joined to canonical groups by exact SMILES. These are producer claims to verify against the build manifest; a fresh metadata/file-list read is not a recomputation of the arrays or roles.

## Keep the full and legacy routes distinct

The later route consumes a separate full-output FPNet checkpoint from the merged-spectrum trainer's V6 output, plus this bank and the spectra inputs. Its selected checkpoint is **197739081 bytes**, SHA256 `9c46ca4fcf19002fecbcded0d0808e8a81e3a25a143e684e259f265c44a5be31`. It is not the public `casmi26-fp-models-v2` checkpoint pair. The legacy `prepare_legacy_exports.py selected` command selects a different feature set and **must not be advertised as this full-bank builder**.

The distinct [selected V6 serving source](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/selected-v6-serving/README.md) supplies exact FPNet/preprocessing/scoring source and input pins. From that directory, `python3 -B verify_sources.py` checks source hashes and syntax without loading a model or dataset. This is a source check, not the missing full-bank preparation or training command, and it does not qualify a completed full inference.

The original [build_clean_full_fingerprints.py](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/full_fingerprint_lineage/build_clean_full_fingerprints.py) and a retained [full manifest](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/legacy-v2/full_fingerprint_lineage/FULL_FINGERPRINT_MANIFEST.json) were recovered. The manifest's SHA256 is `5b08ca4b830de1558be4ce568a10f0997b5fa2fe875a872dcd6a216f901fd9ef`. Its builder depends on earlier canonical-structure/group partitions and a clean-role construction whose complete portable creation chain has not yet been reconstructed or published. This is a known prerequisite gap, not a missing generic fingerprint implementation.

A complete publishable build recipe still needs that role/join creation chain, input training/pool hashes, ordered bit indices, output file hashes, dependency versions and corresponding training command/checkpoint. The current legacy source release does not establish those full-route bindings. No invented replacement command is supplied as historical reproduction. Publish the original full producer and permitted data-access path alongside the manifest before presenting this private input as a reproducible public full-route artifact.

The [fingerprint contract tool](https://github.com/cubres/enveda-casmi-2026/blob/main/tools/fingerprint-contract/README.md) provides a useful preliminary check: 10,395 selected bits require 1,300 packed bytes per row with five zero trailing bits. Bind the real integer selection file and packed-bank hashes from the trusted producer manifest before using it. The included two-row example is wholly invented and does not validate this actual dataset. A packing check cannot certify canonical-role joins, leakage isolation or checkpoint semantics.

## License and attribution

Retain the existing label for uploader-controlled contributions while documenting competition-derived and COCONUT components separately. The [host's open-training clarification](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/745072) is not a blanket CC0 grant. The [original-code/data requirement](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/748882) also applies to this later training route.

See [LICENSE-SCOPE.md](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/LICENSE-SCOPE.md) and [ATTRIBUTION.md](https://github.com/cubres/enveda-casmi-2026/blob/main/reproduction/dataset-cards/2026-10-18/ATTRIBUTION.md). No visibility change, new training run, official score or full-route qualification follows from this card. Original notebook identities and existing input versions remain preserved.
