# Enveda CASMI 2026: experiments and public notebook

## Latest runnable utility · 14 October

[Packed Window Lab](tools/packed-window-lab/2026-10-14/README.md) checks inclusive mass windows, aligned candidate rows, explicit bit packing, dummy-bit masks and exact-score ties. The original NumPy package passed **all 14 synthetic controls** in one completed, bounded run. It includes portable source, examples, integration notes and two diagrams. No model was fitted; real producer eligibility and competition performance remain unmeasured.

![The fingerprint row layout and its ignored positions](tools/packed-window-lab/2026-10-14/packing-layout.svg)

## Earlier measured experiment · 12 October

[Four-group fallback pilot](experiments/2026-10-12-v25-negative-fallback/README.md): **0 gains, 1 loss and 3 ties**, with MRR@25 changing from **1.000 to 0.875**. These four exposed development groups were deliberately selected for poor library coverage; this negative result supports holding the fallback and reproducing the stronger public baseline before more tuning.

![Control and fallback comparison](experiments/2026-10-12-v25-negative-fallback/control_fallback.svg)

## Earlier gate diagnosis · 12 October

[Native gate activation](native-gate-activation-2026-10-12/README.md) explains a completed negative result: **0 of 400 query groups activated the new ranking path**. Read the diagnosis, regenerate the figure, or reuse the original structural capture auditor. Ranking efficacy remains unmeasured; the next reference-library holdout is a separate experiment.

![Native retrieval-gate activation](native-gate-activation-2026-10-12/native-gate-activation.svg)

## Earlier experiments worth reading

Existing public campaign notebook: [Analog Propagation - CASMI 2026 baseline](https://www.kaggle.com/code/prvsiyan/analog-propagation-casmi-2026-baseline). This stable identity was observed public in the retained 11 October snapshot; the guide makes no current run-status or score claim.

The permanent archive includes [Energy-balanced projection](https://github.com/cubres/enveda-casmi-2026/blob/0c5cf4615cf1de050e7e3dc769630c5b760f284b/tools/energy-balanced-projection/2026-10-05/README.md) and [Protected candidate/control comparison](https://github.com/cubres/enveda-casmi-2026/blob/1832b0157cc151f8e1afe3ac363763348a9ec784/protected-candidate-control-2026-10-09/README.md). Read their original claim limits and provenance before a fork. Failures and unexecuted ideas remain part of the record; invented controls are separate from native qualification and official scores.

The shared [Static notebook execution map](https://github.com/cubres/gemma-4-developer-agent/blob/4b21f05ee4542c9f0c5a9dfd2a6d7081385af6d7/tools/notebook-execution-map/2026-10-05/README.md) provides a read-only first look at direct configuration bindings. It does not execute notebooks or infer effective runtime.
