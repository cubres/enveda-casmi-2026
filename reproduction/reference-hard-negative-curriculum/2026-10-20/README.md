# CASMI reference-target curriculum: source-only release

**Current branch status: source code and an invented mechanics demo only. Derived curriculum tables were withdrawn on 21 October 2026 pending clarification of input redistribution rights.**

This package contains deterministic code for constructing and consuming reference-target candidate pools. The method reuses the public reference-mass ambiguity atlas and a ChEBI structure shard. It filters exact selected-target collisions, deduplicates supplied identity aliases, keeps empty candidate pools explicit, and supports deterministic staged sampling within train-fold components.

![Reference rows flow through identity and target checks into component-contained pools](assets/curriculum.svg)

## Why the generated data are withheld

The earlier public tree included row-level CSV and JSON outputs computed using a frozen 10,395-bit fingerprint mask associated with CASMI training data. The independent publication review could not establish the mask component's exact redistribution scope. That is a rights-uncertainty finding, not a finding of infringement. We removed the derived tables and row-level example from the current `main` tree while preserving the source and run receipt. We did not rewrite Git history; prior commits may still contain those files. Please do not retrieve or redistribute copies from historical commits until the relevant terms are confirmed.

The prior CPU-only R3 run passed mechanics and resource checks. Its retained [result receipt](completed/RESULT.json) is not evidence of trained-model quality, a CASMI score, spectral distinguishability, or hidden-test improvement. No model training or inference was performed.

## Run the fully synthetic example

Python 3.10+ and the standard library are sufficient:

```sh
python3 -B source/demo_tiny.py
```

It prints `PASS_INVENTED_MECHANICS_ONLY`. The example uses invented identifiers and tiny integer bit sets; it makes no chemical or competition-data claim. We ran it with Python 3.12.14.

## Source and input boundary

The `source/` folder preserves the exact pinned R3 source files and contracts. `source/build_curriculum.py` is the scientific producer; `source/sample_curriculum.py` is a consumer for a separately authorized, completed data tree. This public package does not contain that tree, so the consumer cannot be run against this checkout.

The historical `source/run_owned_curriculum.py` is root-specific one-time orchestration tied to private admission and consumed-attempt records. It is archival evidence, not a public launch command. Do not set its internal guard variables manually or use it to repeat the consumed build.

The exact public ChEBI and reference-atlas pins are recorded in [INPUTS.md](INPUTS.md) and `source/INPUT_CONTRACT.json`. Input pins describe provenance; they do not grant redistribution rights. See [DATA-LICENSE.md](DATA-LICENSE.md) and the [withdrawal notice](DATA_WITHDRAWAL_NOTICE.md) before using any historical output. No positive spectra, licensed chemical join, trained weights, or performance claim is included.

`verify_release.py` checks the current package manifest and confirms that withdrawn output paths have not reappeared. The release keeps the original component attribution and terms in [SOURCE_ATTRIBUTION.md](SOURCE_ATTRIBUTION.md) and [SOURCE_COMPONENT_LICENSE.md](SOURCE_COMPONENT_LICENSE.md). Newly authored source files carry Apache-2.0 SPDX identifiers; that code license does not license input data.
