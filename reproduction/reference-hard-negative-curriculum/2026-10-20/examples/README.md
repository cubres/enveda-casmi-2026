# Synthetic mechanics example

Run the small invented-data control from the package root:

```sh
python3 -B source/demo_tiny.py
```

It checks target-collision exclusion, identity-alias handling, empty pools, split constraints, deterministic train-only sampling, and fail-closed receipt handling with invented identifiers and tiny integer bit sets. Expected status: `PASS_INVENTED_MECHANICS_ONLY`.

This does not load CASMI rows, spectra, model weights, or a downloaded curriculum. It makes no chemical, spectral, or score claim. The fingerprint-derived R3 outputs previously linked from this directory have been withdrawn from the current branch pending clarification of component redistribution terms. See [the withdrawal notice](../DATA_WITHDRAWAL_NOTICE.md) and [data terms](../DATA-LICENSE.md).
