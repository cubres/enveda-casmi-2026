# Preserved execution lineage

The original source proposal's first 64 anchors missed every identical-target
collision. Before execution, additive R2 changed its 64-anchor canary to include
285→3018 and required qualified owning-result/hash gates in the consumer.

R2 then completed the scientific child but **failed** its 128-MiB conservative
resource gate: 135,626,752 bytes were charged against 134,217,728. The observer
accounting reused aggregate child high-water RSS and charged it twice. This
was deliberate conservative accounting, not measured simultaneous whole RSS.
`R2_FAILED_RESOURCE_RESULT.json` is the unchanged failed owning receipt. It
was not sampled, published as qualified, reset or retroactively passed.

A separately reviewed/admitted R3 retained the exact scientific recipe and
same accounting, with a prospective 160-MiB ceiling. Its actual owning result
passed at 136,429,568 bytes, 0.242065 seconds wall and 0.257484 CPU seconds.
The public receipt omits operational admission/attempt bookkeeping only;
`verification/PUBLIC_CPU_RESULT_PROVENANCE.json` pins the original receipt
and records the transformation. No private admission, machine path or human
approval reference is distributed.

The default system interpreter's Python-version preflight stopped before the
new attempt. The accepted run used the project's Python 3.12.14 environment.
The early preflight was not a second scientific execution. Private operational
preflight/admission/marker files are intentionally excluded; scientific source,
actual measurements and all output bytes are retained here.

No historical FP checkpoint lineage, downstream spectrum rights, model
training result or score is qualified by this utility. The selected-mask terms
and unresolved historical lineage limits remain explicit in the component
notices. No prior notebook, source, failed result or public input was replaced.
