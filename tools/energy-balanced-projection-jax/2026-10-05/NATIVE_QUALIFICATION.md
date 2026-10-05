# CPU result and the next native check

The retained pure-JAX kernel passed 15 synthetic CPU checks on JAX 0.11.0,
jaxlib 0.11.0 and NumPy 2.2.6. The run explicitly enabled float64 and used
`highest` matrix-multiplication precision. Its source and input protocol were
frozen before any loss or gradient evaluation.

All 458,752 JAX head derivatives matched independent analytic NumPy derivatives.
Maximum float64 absolute differences were 2.2898349882893854e-16 for the spectral
head and 5.551115123125783e-17 for the molecular head; the loss matched exactly.
The 15 checks cover same-logit derivatives, both complete head gradients, one
SGD update, extreme excluded logits, exact zero derivatives for padding and
cross-formula entries, row/column permutations, replicate duplication, missing
energies, 16 sampled parameter finite differences and repeated-JIT consistency.

Measured CPU float32 end-to-end gradient relative L2 differences were
3.1926544232492375e-7 and 6.51246369550798e-7. The loss difference was
1.699796727816505e-7. These values describe this CPU execution; no TPU or BF16
equivalence follows from them. Total process CPU use was 1.78676 seconds and
wall time 1.0457783339952584 seconds. First-call timings include compilation and
execution and are not speedup measurements.

## A later native TPU qualification

Keep this CPU probe intact. A separate native wrapper can reuse the frozen pure
kernel equations after verifying their source identity. It must record the
actual TPU device generation/count, runtime/backend/package versions, exact
input and initialization hashes, matrix precision, global batch, optimizer
equations and synchronization method. The existing CPU-only guard must remain
in this source. No package installation or hardware job has occurred here.

Begin with the same fixed synthetic input protocol and FP32 arrays. Compare
loss, every logit derivative, both full head gradients and the SGD update with
CPU evaluation of exactly those arrays. Proposed gates are loss absolute error
at most 1e-4 and full gradient/update relative L2 errors at most 1e-3, plus
absolute error checks on near-zero elements. Padding and cross-formula
derivatives must stay exactly zero. Repeat the missing-energy and permutation
adversaries. BF16 is a separately declared precision comparison.

For timing, warm up and synchronize every reported measurement using
`block_until_ready()`. Use at least 100 identical-shape useful steps, preserving
global batch and data semantics across devices. Record host input preparation,
transfer, compilation, steady-state execution and complete elapsed time.
Changing formula or candidate masks may change values, but must not introduce
unexpected shape changes or repeated compilation. Distributed averaging must
preserve equal molecule and energy weights rather than weight replicas or
shards equally by accident.

This tiny synthetic panel alone does not justify spending TPU quota. A planned
real workload needs an observed end-to-end advantage after startup and transfer
costs; 1.5x is a proposed operational threshold. That workload also needs verified
native encoder caches and an independently frozen complete training cohort.
The current metadata availability count is not such a training cohort.

No native TPU run, pretrained encoder, chemical data, retrieval result,
competition artifact, notebook update or public repository mutation is part
of this packet.

Framework references: [JAX benchmarking and synchronization](https://docs.jax.dev/en/latest/201/profiling.html)
and [explicit dtype policy](https://docs.jax.dev/en/latest/101/default_dtypes.html).
