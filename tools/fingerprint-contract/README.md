# Fingerprint file contracts without pickle or a model

A small standard-library tool for catching fingerprint-bank mixups before inference. A 6,930-bit selected bank uses **867 bytes per row and six padding bits**; a 10,395-bit bank uses **1,300 bytes and five padding bits**. Equal row widths alone never prove matching descriptor order.

The checker verifies C-order uint8 NPY shape and file length, exact file SHA256, an ordered integer selection vector, unique in-range selected indices and zero trailing padding bits. It does not deserialize pickle, import NumPy/PyTorch, load weights or execute a model. Large banks are hashed as streams; padding checks use bounded row blocks.

Run the invented fixed-seed demos from this directory:

```bash
python3 -B make_demo.py demo6930 --bits 6930
python3 -B check_fp_contract.py demo6930/manifest.json demo6930/packed.npy demo6930/indices.npy
python3 -B make_demo.py demo10395 --bits 10395
python3 -B check_fp_contract.py demo10395/manifest.json demo10395/packed.npy demo10395/indices.npy
python3 -B -m unittest -v test_contract.py
```

The generator requires a new output directory. Its two rows contain deterministic invented bytes and its index vector is a demonstration, **not the selection vector from any trained checkpoint**. No chemical structures, labels, spectra or third-party records are included.

For a real release, obtain the manifest's hashes from the trusted producer's version-bound build record. Replace the demo inputs with the exact files named by that record. If the original release uses a boolean mask, the producer must publish the corresponding ordered integer positions and bind that conversion. Do not silently reinterpret the mask or regenerate a new bit selection. A manifest made from whatever files happen to be present cannot prove their compatibility.

A passing result certifies bytes and packing only. It does **not** establish chemical descriptor semantics, fingerprint-family definitions, RDKit version, candidate row alignment with a separate metadata table, training provenance, license eligibility or compatibility with a particular checkpoint. Bind those separately in the release manifest.

Eight tests include valid layouts, 6,930/10,395 width swaps, reordered/duplicate selections, nonzero padding, extra payload bytes and object-array rejection. Tests use invented data only. Original code and fixtures are MIT-licensed; see [LICENSE-CODE.txt](LICENSE-CODE.txt). External data keeps its own terms.
