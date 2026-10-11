# Enveda CASMI: useful dataset-loading recipes, 2026-10-11

These description proposals correct the load instructions for existing public datasets. No asset was repackaged, no payload was downloaded, and no dataset was updated while preparing this packet. The source descriptions are the owner's existing cards; the revised software examples are original.

Each `cards/<slug>/` directory contains the full proposed description, a filename/size inventory for one exact Kaggle data version, and before/after description digests. `SOURCE_BINDINGS.json` records the exact identity/version/licence and limits. Filename and size agreement does not authenticate a payload. None of these selected releases lists `MANIFEST.json`, so a manifest-based flatpack verifier cannot be applied to them as-is. Previously stated array headers and October 7 hashes remain historical observations.

The proposals preserve dataset identity, title, slug, licence metadata, public visibility, files and versions. They add no rights, medal, performance, compatibility or independent-validation claim. This source package does not attest a live card update or Kaggle Markdown rendering. Description deployment requires an independent review and a fresh identity/version/description binding.

[Campaign experiments and reproduction notes](https://github.com/cubres/enveda-casmi-2026)

The COCONUT recipe includes exact lower and upper mass endpoints with `side="left"` / `side="right"`. Run the small independent numerical control on invented masses:

```bash
python examples/toy_mass_window.py
```

It requires NumPy; the retained execution used NumPy 2.2.6 and Python 3.12.14. It reads no candidate arrays, molecule/spectrum/query data or model. The controls select 3 rows when both boundaries are included, versus 2 for the old default upper endpoint; duplicated boundary masses select 4 and the empty interval selects 0. The result and execution receipt are retained beside the source. This is a numeric endpoint check, with no native or competition score.

The fingerprint snippets inspect one checkpoint at a time with restricted `weights_only=True` deserialization; a failure is a stop signal. The ranker snippet checks numeric schema while leaving the undocumented query/molecule split mapping unresolved. Dataset metadata names CC-BY-NC-SA-4.0; upstream and competition conditions still govern reuse.
