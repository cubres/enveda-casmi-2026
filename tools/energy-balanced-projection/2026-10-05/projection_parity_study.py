"""Original synthetic linear-head parity experiment; no models or chemical data.

The frozen original NumPy energy objective is the numerical authority. This
independent implementation uses fixed host-built reduction and candidate masks.
Outputs are created exclusively. No encoders, caches, rankings or scores occur.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time

START_WALL = time.monotonic()
START_CPU = resource.getrusage(resource.RUSAGE_SELF)
resource.setrlimit(resource.RLIMIT_CPU, (60, 61))
signal.alarm(90)
import numpy as np

HERE = Path(__file__).resolve().parent
AUTHORITY = HERE.parent / 'codex_enveda_alignment_learning_20261005T144407Z/energy_balanced_objective.py'
AUTHORITY_SHA = 'da9b7861fd07bf49ad864dbf9a1e795dea8c573b3744b7d4d2665944ede3ad8c'
SEED = 20261005
ETA = 0.5
WIDTH = 256
SCALE = 1.0 / math.sqrt(WIDTH)
RATE = 0.05


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save_new(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def array_pin(array):
    a = np.ascontiguousarray(array)
    return {'shape': list(a.shape), 'dtype': str(a.dtype), 'bytes': a.nbytes,
            'sha256': digest(a.tobytes(order='C'))}


def fixed_plan(targets, energies, formulas, row_active, column_active):
    """Host-only immutable grouping. No device-side unique/nonzero/shape query."""
    molecules = np.flatnonzero(column_active)
    levels = np.unique(energies[row_active])
    if set(map(int, targets[row_active])) != set(map(int, molecules)):
        raise ValueError('each complete training candidate needs observed spectra')
    candidate = np.array([[bool(column_active[j]) and formulas[j] == formulas[m]
                           for j in range(len(formulas))] for m in molecules])
    if np.any(candidate.sum(axis=1) < 2):
        raise ValueError('complete same-formula membership needs at least two')
    membership = ((targets[None, None, :] == molecules[:, None, None]) &
                  (energies[None, None, :] == levels[None, :, None]) &
                  row_active[None, None, :])
    counts = membership.sum(axis=-1)
    observed = counts > 0
    reductions = membership.astype(np.float64) / np.maximum(counts, 1)[..., None]
    positives = np.zeros(candidate.shape, dtype=np.float64)
    positives[np.arange(len(molecules)), molecules] = 1.0
    plan = {'reduce': reductions, 'observed': observed, 'candidate': candidate,
            'positive': positives, 'molecules': molecules, 'levels': levels}
    for a in plan.values():
        a.flags.writeable = False
    return plan


def masked_ce(logits, candidates, positives):
    """Stable fixed-shape CE and all logit derivatives; excluded columns zero."""
    masked = np.where(candidates, logits, -np.inf)
    maximum = masked.max(axis=-1, keepdims=True)
    shifted = masked - maximum
    exp = np.exp(shifted)
    sums = exp.sum(axis=-1, keepdims=True)
    probs = exp / sums
    # Avoid the undefined product zero*(-inf); positives select original logits.
    target_logit = np.sum(logits * positives, axis=-1)
    values = np.log(sums[..., 0]) + maximum[..., 0] - target_logit
    return values, probs - positives


def static_loss(logits, plan):
    """Independent tensor reductions, equal molecule and observed-energy mass."""
    dtype = logits.dtype
    reduce = plan['reduce'].astype(dtype)
    observed = plan['observed'].astype(dtype)
    candidate = plan['candidate']
    positive = plan['positive'].astype(dtype)
    means = np.einsum('ger,rc->gec', reduce, logits, optimize=False)
    energy_weights = observed / observed.sum(axis=1, keepdims=True)
    pooled = np.einsum('ge,gec->gc', energy_weights, means, optimize=False)
    pooled_values, pooled_grad = masked_ce(pooled, candidate, positive)
    separate_values, separate_grad = masked_ce(
        means, candidate[:, None, :], positive[:, None, :])
    eta = dtype.type(ETA)
    n_molecules = dtype.type(len(plan['molecules']))
    loss = (eta * pooled_values + (dtype.type(1)-eta) *
            np.sum(separate_values * energy_weights, axis=1)).sum() / n_molecules
    d_means = energy_weights[..., None] * (
        eta * pooled_grad[:, None, :] + (dtype.type(1)-eta) * separate_grad) / n_molecules
    derivative = np.einsum('ger,gec->rc', reduce, d_means, optimize=False)
    return float(loss), derivative


def head_logits(spectral, molecular, spectral_head, molecular_head):
    return ((spectral @ spectral_head) @ (molecular @ molecular_head).T) * SCALE


def head_gradients(spectral, molecular, spectral_head, molecular_head, d_logits):
    zs, zm = spectral @ spectral_head, molecular @ molecular_head
    gs = spectral.T @ (d_logits @ zm) * SCALE
    gm = molecular.T @ (d_logits.T @ zs) * SCALE
    return gs, gm


def relative_l2(actual, expected):
    return float(np.linalg.norm(actual - expected) / max(np.linalg.norm(expected), 1e-30))


def difference(actual, expected):
    return {'maximum_absolute': float(np.max(np.abs(actual - expected))),
            'relative_l2': relative_l2(actual, expected)}


def replicated_ce(logits, plan, targets, row_active):
    """Explicit alternative: equal spectral rows, no energy/molecule balancing."""
    rows = np.flatnonzero(row_active)
    candidate_lookup = {int(m): i for i, m in enumerate(plan['molecules'])}
    masks = np.stack([plan['candidate'][candidate_lookup[int(targets[r])]] for r in rows])
    positives = np.stack([plan['positive'][candidate_lookup[int(targets[r])]] for r in rows])
    values, derivatives = masked_ce(logits[rows], masks, positives)
    full = np.zeros_like(logits)
    full[rows] = derivatives / len(rows)
    return float(values.mean()), full


def main():
    authority_bytes = AUTHORITY.read_bytes()
    if digest(authority_bytes) != AUTHORITY_SHA:
        raise RuntimeError('frozen numerical authority changed')
    with (HERE / 'frozen_energy_authority.py').open('xb') as stream:
        stream.write(authority_bytes)
    namespace = {'__name__': 'frozen_energy_authority'}
    exec(compile(authority_bytes, str(AUTHORITY), 'exec'), namespace)
    reference_loss = namespace['energy_balanced_loss']
    rng = np.random.default_rng(SEED)
    strata = [{20: 1, 40: 4}, {20: 2, 60: 1}, {40: 1},
              {20: 3, 40: 1, 60: 2}, {60: 1}, {20: 2, 40: 1}, {40: 2, 60: 1}]
    target_rows, energy_rows = [], []
    for m, histogram in enumerate(strata):
        for e, count in histogram.items():
            target_rows += [m] * count
            energy_rows += [e] * count
    n_rows = len(target_rows)
    targets = np.array(target_rows + [-1] * 3, dtype=np.int64)
    energies = np.array(energy_rows + [0] * 3, dtype=np.float64)
    row_active = np.arange(len(targets)) < n_rows
    column_active = np.arange(9) < 7
    formulas = np.array(['F_A'] * 3 + ['F_B'] * 2 + ['F_C'] * 2 + ['PAD'] * 2)
    keys = ['SYNTHETIC_MOLECULE_%d' % i for i in range(9)]
    spectral = rng.normal(size=(len(targets), 1024)).astype(np.float64)
    molecular = rng.normal(size=(9, 768)).astype(np.float64)
    spectral_head = rng.normal(0, 1 / math.sqrt(1024), size=(1024, WIDTH))
    molecular_head = rng.normal(0, 1 / math.sqrt(768), size=(768, WIDTH))
    plan = fixed_plan(targets, energies, formulas, row_active, column_active)
    arrays = {'spectral': spectral, 'molecular': molecular,
              'spectral_head': spectral_head, 'molecular_head': molecular_head,
              'targets': targets, 'energies': energies, 'row_active': row_active,
              'column_active': column_active, **{'mask_'+k: v for k, v in plan.items()}}
    initial_pins = {k: array_pin(v) for k, v in arrays.items()}
    save_new('frozen_input_protocol.json', {
        'scope': 'SYNTHETIC_NUMERICAL_ONLY_NO_ENCODERS_NO_RETRIEVAL_NO_SCORE',
        'seed': SEED, 'authority_source_sha256': AUTHORITY_SHA,
        'study_source_sha256': digest(Path(__file__).read_bytes()),
        'spectral_head_shape': [1024, 256], 'molecular_head_shape': [768, 256],
        'formula_groups': [3, 2, 2], 'molecules': 7, 'active_rows': n_rows,
        'padded_rows': 3, 'padded_columns': 2, 'strata': strata,
        'eta': ETA, 'logit_scale': SCALE, 'sgd_rate': RATE,
        'dtype_first': 'float64', 'dtype_second': 'float32',
        'all_array_pins': initial_pins,
        'cpu_absolute_seconds': 60, 'wall_failsafe_seconds': 90,
        'finite_difference_samples_each_head': 16, 'finite_difference_step': 1e-5,
        'fp64_full_gradient_rtol': 1e-11, 'fp64_full_gradient_atol': 1e-12,
        'finite_difference_atol': 2e-8, 'finite_difference_rtol': 2e-5,
        'fp32_measurement_only': True,
        'excluded': ['weights', 'chemical data', 'encoder conversions', 'TPU',
                     'competition targets', 'rankings', 'retrieval gain', 'GitHub', 'notebooks']})

    receipts = []
    def check(label, condition, detail=None):
        receipts.append({'check': label, 'passed': bool(condition), 'detail': detail})
        if not condition:
            raise AssertionError(label)

    def authority_on_full(x, ts=targets, es=energies, fs=formulas, ra=row_active, ca=column_active):
        active_columns = np.flatnonzero(ca)
        active_rows = np.flatnonzero(ra)
        lookup = {int(c): i for i, c in enumerate(active_columns)}
        compact_targets = np.array([lookup[int(ts[r])] for r in active_rows])
        value, grad = reference_loss(x[np.ix_(active_rows, active_columns)], compact_targets,
                                    es[active_rows], [keys[c] for c in active_columns],
                                    fs[active_columns].tolist(), eta=ETA)
        padded_gradient = np.zeros(x.shape, dtype=np.float64)
        padded_gradient[np.ix_(active_rows, active_columns)] = grad
        return value, padded_gradient

    logits = head_logits(spectral, molecular, spectral_head, molecular_head)
    authority_value, authority_gradient = authority_on_full(logits)
    value, gradient = static_loss(logits, plan)
    fp64_dlogits = difference(gradient, authority_gradient)
    check('FP64_loss_and_all_logit_derivatives',
          abs(value-authority_value) <= 1e-12 and
          np.allclose(gradient, authority_gradient, rtol=1e-11, atol=1e-12),
          {'loss_absolute_delta': abs(value-authority_value), 'gradient': fp64_dlogits})
    gs, gm = head_gradients(spectral, molecular, spectral_head, molecular_head, gradient)
    rs, rm = head_gradients(spectral, molecular, spectral_head, molecular_head, authority_gradient)
    check('FP64_complete_spectral_and_molecular_head_gradients',
          np.allclose(gs, rs, rtol=1e-11, atol=1e-12) and
          np.allclose(gm, rm, rtol=1e-11, atol=1e-12),
          {'spectral': difference(gs, rs), 'molecular': difference(gm, rm),
           'parameter_derivatives_compared': int(gs.size+gm.size)})
    updated_s, updated_m = spectral_head - RATE * gs, molecular_head - RATE * gm
    ref_updated_s, ref_updated_m = spectral_head - RATE * rs, molecular_head - RATE * rm
    check('FP64_one_explicit_SGD_update',
          np.allclose(updated_s, ref_updated_s, rtol=1e-11, atol=1e-12) and
          np.allclose(updated_m, ref_updated_m, rtol=1e-11, atol=1e-12),
          {'spectral': difference(updated_s, ref_updated_s),
           'molecular': difference(updated_m, ref_updated_m)})

    forbidden = ~row_active[:, None] | ~column_active[None, :] | (
        row_active[:, None] & (formulas[np.maximum(targets, 0), None] != formulas[None, :]))
    check('all_padding_and_cross_formula_derivatives_exact_zero',
          np.count_nonzero(gradient[forbidden]) == 0,
          {'excluded_logit_entries': int(forbidden.sum())})
    poisoned = logits.copy()
    poisoned[forbidden] = rng.choice([-1e4, 1e4], size=int(forbidden.sum()))
    pv, pg = static_loss(poisoned, plan)
    check('extreme_padding_and_cross_formula_logits_do_not_affect_loss_or_gradient',
          pv == value and np.array_equal(pg, gradient))

    row_perm, col_perm = rng.permutation(len(targets)), rng.permutation(len(formulas))
    inverse_col = np.argsort(col_perm)
    perm_targets = np.where(targets[row_perm] >= 0, inverse_col[np.maximum(targets[row_perm], 0)], -1)
    perm_plan = fixed_plan(perm_targets, energies[row_perm], formulas[col_perm],
                          row_active[row_perm], column_active[col_perm])
    perm_value, perm_gradient = static_loss(logits[np.ix_(row_perm, col_perm)], perm_plan)
    restored = np.empty_like(perm_gradient)
    restored[np.ix_(row_perm, col_perm)] = perm_gradient
    check('row_and_column_permutation_preserve_all_derivatives',
          abs(perm_value-value) <= 1e-12 and np.allclose(restored, gradient, rtol=1e-11, atol=1e-12))
    auth_perm, auth_perm_grad = authority_on_full(logits[np.ix_(row_perm, col_perm)],
        perm_targets, energies[row_perm], formulas[col_perm], row_active[row_perm], column_active[col_perm])
    check('permuted_static_loss_matches_frozen_authority',
          abs(auth_perm-perm_value) <= 1e-12 and
          np.allclose(auth_perm_grad, perm_gradient, rtol=1e-11, atol=1e-12))

    duplicate_row = np.flatnonzero((targets == 0) & (energies == 20))[0]
    duplications = np.r_[np.arange(n_rows), np.repeat(duplicate_row, 9)]
    duplicate_s = spectral[duplications]
    duplicate_targets, duplicate_energies = targets[duplications], energies[duplications]
    duplicate_active = np.ones(len(duplications), dtype=bool)
    duplicate_plan = fixed_plan(duplicate_targets, duplicate_energies, formulas,
                                duplicate_active, column_active)
    duplicate_logits = head_logits(duplicate_s, molecular, spectral_head, molecular_head)
    dv, dg = static_loss(duplicate_logits, duplicate_plan)
    dgs, dgm = head_gradients(duplicate_s, molecular, spectral_head, molecular_head, dg)
    check('replicating_one_CE_preserves_equal_energy_head_update',
          abs(dv-value) <= 1e-12 and np.allclose(dgs, gs, rtol=1e-11, atol=1e-12) and
          np.allclose(dgm, gm, rtol=1e-11, atol=1e-12))
    check('missing_collision_energies_are_masked_not_zero_imputed',
          np.array_equal(plan['observed'].sum(axis=1), np.array([2, 2, 1, 3, 1, 2, 2])))

    finite = []
    for head_name, head, analytic in [('spectral', spectral_head, gs), ('molecular', molecular_head, gm)]:
        sample = np.r_[int(np.argmax(np.abs(analytic))), rng.choice(head.size, size=15, replace=False)]
        for flat in sample:
            index = np.unravel_index(int(flat), head.shape)
            original = head[index]
            head[index] = original + 1e-5
            plus = static_loss(head_logits(spectral, molecular, spectral_head, molecular_head), plan)[0]
            head[index] = original - 1e-5
            minus = static_loss(head_logits(spectral, molecular, spectral_head, molecular_head), plan)[0]
            head[index] = original
            numerical = (plus-minus) / 2e-5
            exact = float(analytic[index])
            error = abs(numerical-exact)
            finite.append({'head': head_name, 'index': list(map(int, index)),
                           'analytic': exact, 'central_difference': numerical,
                           'absolute_error': error,
                           'passed': error <= 2e-8 + 2e-5 * abs(exact)})
    check('32_sampled_parameter_finite_differences', all(x['passed'] for x in finite),
          {'samples': len(finite), 'maximum_absolute_error': max(x['absolute_error'] for x in finite)})

    replicate_value, replicate_gradient = replicated_ce(logits, plan, targets, row_active)
    replicate_gs, replicate_gm = head_gradients(spectral, molecular, spectral_head, molecular_head, replicate_gradient)
    duplicate_replicate_value, duplicate_replicate_gradient = replicated_ce(
        duplicate_logits, duplicate_plan, duplicate_targets, duplicate_active)
    duplicate_rep_gs, duplicate_rep_gm = head_gradients(duplicate_s, molecular,
        spectral_head, molecular_head, duplicate_replicate_gradient)
    objective_difference = {'equal_energy_loss': value, 'replicate_weighted_loss': replicate_value,
        'spectral_update_delta_l2': float(RATE*np.linalg.norm(gs-replicate_gs)),
        'molecular_update_delta_l2': float(RATE*np.linalg.norm(gm-replicate_gm)),
        'equal_energy_replicate_duplication_gradient_relative_l2': relative_l2(dgs, gs),
        'replicate_weighted_duplication_gradient_relative_l2': relative_l2(duplicate_rep_gs, replicate_gs),
        'replicate_weighted_loss_after_duplication': duplicate_replicate_value,
        'meaning': 'Numerical objective/update behavior only; no quality, retrieval or score evidence'}
    check('equal_energy_and_replicate_weighted_objectives_make_distinct_updates',
          objective_difference['spectral_update_delta_l2'] > 1e-5 and
          objective_difference['molecular_update_delta_l2'] > 1e-5)
    check('replicate_weighted_update_changes_under_CE_replication',
          objective_difference['replicate_weighted_duplication_gradient_relative_l2'] > 1e-3)

    s32, m32, ws32, wm32 = [x.astype(np.float32) for x in (spectral, molecular, spectral_head, molecular_head)]
    logits32 = head_logits(s32, m32, ws32, wm32)
    value32, gradient32 = static_loss(logits32, plan)
    same_input_reference_value, same_input_reference_gradient = authority_on_full(logits32)
    gs32, gm32 = head_gradients(s32, m32, ws32, wm32, gradient32)
    reference32gs, reference32gm = head_gradients(s32.astype(np.float64), m32.astype(np.float64),
        ws32.astype(np.float64), wm32.astype(np.float64), same_input_reference_gradient)
    fp32 = {'authority_same_FP32_logit_loss': same_input_reference_value,
        'static_FP32_loss': value32, 'same_logit_loss_absolute_delta': abs(value32-same_input_reference_value),
        'same_logit_derivative': difference(gradient32.astype(np.float64), same_input_reference_gradient),
        'same_FP32_weights_features_spectral_gradient': difference(gs32.astype(np.float64), reference32gs),
        'same_FP32_weights_features_molecular_gradient': difference(gm32.astype(np.float64), reference32gm),
        'end_to_end_loss_delta_vs_original_FP64': abs(value32-value),
        'end_to_end_spectral_gradient_vs_original_FP64': difference(gs32.astype(np.float64), gs),
        'end_to_end_molecular_gradient_vs_original_FP64': difference(gm32.astype(np.float64), gm),
        'spectral_SGD_update_vs_original_FP64': difference((ws32-RATE*gs32).astype(np.float64), updated_s),
        'molecular_SGD_update_vs_original_FP64': difference((wm32-RATE*gm32).astype(np.float64), updated_m),
        'derivative_dtype': str(gradient32.dtype), 'logit_dtype': str(logits32.dtype),
        'interpretation': 'Measured CPU FP32 disagreement; no TPU/BF16 equivalence or speed claim'}
    check('FP32_excluded_derivatives_remain_exact_zero', np.count_nonzero(gradient32[forbidden]) == 0)
    check('all_synthetic_inputs_and_initial_weights_restored',
          initial_pins == {k: array_pin(v) for k, v in arrays.items()})
    check('original_authority_file_preserved', digest(AUTHORITY.read_bytes()) == AUTHORITY_SHA)
    cpu = resource.getrusage(resource.RUSAGE_SELF)
    cpu_seconds = cpu.ru_utime+cpu.ru_stime-START_CPU.ru_utime-START_CPU.ru_stime
    check('complete_study_cpu_under_60_seconds', cpu_seconds < 60)
    receipt = {'status': 'PASS_SYNTHETIC_FP64_PROJECTION_NUMERICAL_CONTRACT_ONLY',
        'source_sha256': digest(Path(__file__).read_bytes()),
        'authority_sha256': AUTHORITY_SHA,
        'protocol_sha256': digest((HERE/'frozen_input_protocol.json').read_bytes()),
        'checks': receipts, 'checks_passed': len(receipts), 'finite_differences': finite,
        'FP64': {'authority_loss': authority_value, 'static_loss': value,
                 'full_logit_derivative_comparison': fp64_dlogits},
        'FP32_measured_disagreement': fp32, 'objective_update_difference': objective_difference,
        'environment': {'python': sys.version.split()[0], 'numpy': np.__version__,
            'OPENBLAS_NUM_THREADS': os.environ.get('OPENBLAS_NUM_THREADS'),
            'MKL_NUM_THREADS': os.environ.get('MKL_NUM_THREADS'),
            'OMP_NUM_THREADS': os.environ.get('OMP_NUM_THREADS')},
        'elapsed_wall_seconds': time.monotonic()-START_WALL, 'process_cpu_seconds': cpu_seconds,
        'native_TPU_run': False, 'encoder_run': False, 'training_data_run': False,
        'retrieval_result': None, 'official_score': None}
    save_new('terminal_receipt.json', receipt)
    print(json.dumps({'status': receipt['status'], 'checks_passed': len(receipts),
        'cpu_seconds': cpu_seconds, 'wall_seconds': receipt['elapsed_wall_seconds'],
        'receipt_sha256': digest((HERE/'terminal_receipt.json').read_bytes()),
        'FP32_loss_absolute_delta': fp32['same_logit_loss_absolute_delta'],
        'maximum_finite_difference_error': max(x['absolute_error'] for x in finite)}, sort_keys=True))


if __name__ == '__main__':
    main()
