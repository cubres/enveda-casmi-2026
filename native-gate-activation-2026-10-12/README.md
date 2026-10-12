# When a ranking improvement never gets called

A completed native development run processed **400 query groups**. The retrieval gate opened for **0 of 400**, so the new ranking intervention never ran naturally. Its effect on identification accuracy remains unmeasured.

![The retrieval gate stayed closed for all 400 groups.](native-gate-activation.svg)

The gate decides whether to request expensive forward evidence. A successful readiness canary proves that a route can execute; it does not show that real queries reach that route. Counting requests and interventions alongside final metrics exposes this distinction. Here, zero activation means the experiment did not test the proposed improvement.

This packet includes an original structural receipt auditor and the diagram generator. Both use Python's standard library. To regenerate the figure:

```bash
python -B make_gate_diagram.py
```

For a capture that follows the auditor's declared V24 fixed-panel schema:

```bash
python -B fixed_panel_audit.py --manifest capture/PRIVATE_CAPTURE_MANIFEST.json \
  --input-dir capture --output PRIVATE_AUDIT_RESULT.json
```

Use the producer's actual manifest filename. The auditor checks retained file bytes, hashes, panel membership, alignment and structural capture contracts. It does not estimate ranking efficacy, authenticate producer chronology, or accept the successor training-holdout schema. Read its module documentation before adapting it to another producer.

The next scientific question is whether the intervention activates when the selected molecules and their canonical aliases are withheld from the reference library. That experiment needs independent control and treatment outputs, complete same-call numerical vectors, and explicit accounting for missing results. It has no measured result yet.

Only the aggregate gate count is disclosed here. No raw spectra, chemical structures, acquisition identifiers, per-query predictions, private engine code or weights are distributed. This development result is separate from an official competition score. Original code and diagram are MIT licensed.
