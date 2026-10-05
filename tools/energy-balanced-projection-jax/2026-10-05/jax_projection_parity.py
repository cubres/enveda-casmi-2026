"""Original pure-JAX fixed-mask numerical kernel; synthetic inputs only.

Independent automatic differentiation is compared with the frozen original
NumPy energy objective and its full analytic head derivatives. No encoder,
training corpus, ranking, package installation or accelerator job is involved.
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

START = time.monotonic()
INITIAL_CPU = resource.getrusage(resource.RUSAGE_SELF)
resource.setrlimit(resource.RLIMIT_CPU, (30, 31))
signal.alarm(60)
import numpy as np
import jax
import jax.numpy as jnp
from jax.scipy.special import logsumexp

jax.config.update('jax_enable_x64', True)
jax.config.update('jax_default_matmul_precision', 'highest')
HERE = Path(__file__).resolve().parent
AUTHORITY = HERE.parent / 'codex_enveda_projection_parity_20261005T160447Z/frozen_energy_authority.py'
AUTHORITY_SHA = 'da9b7861fd07bf49ad864dbf9a1e795dea8c573b3744b7d4d2665944ede3ad8c'
SEED, ETA, WIDTH, RATE = 20261005, 0.5, 256, 0.05
SCALE = 1 / math.sqrt(WIDTH)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save_new(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def array_pin(a):
    a = np.ascontiguousarray(a)
    return {'shape': list(a.shape), 'dtype': str(a.dtype), 'sha256': sha(a.tobytes())}


def host_plan(targets, energies, formulas, active_rows, active_columns):
    """Host-only grouping; fixed masks are ordinary arguments of every kernel."""
    molecules = [i for i, active in enumerate(active_columns) if active]
    levels = sorted({float(e) for e, active in zip(energies, active_rows) if active})
    if {int(t) for t, active in zip(targets, active_rows) if active} != set(molecules):
        raise ValueError('complete candidate membership requires observations')
    reduction = np.zeros((len(molecules), len(levels), len(targets)), dtype=np.float64)
    energy_weights = np.zeros((len(molecules), len(levels)), dtype=np.float64)
    candidates = np.zeros((len(molecules), len(formulas)), dtype=bool)
    positives = np.zeros(candidates.shape, dtype=np.float64)
    for g, molecule in enumerate(molecules):
        candidates[g] = [bool(active_columns[c]) and f == formulas[molecule]
                         for c, f in enumerate(formulas)]
        if sum(candidates[g]) < 2:
            raise ValueError('each formula requires two distinct complete candidates')
        positives[g, molecule] = 1
        observed = 0
        for e, energy in enumerate(levels):
            rows = [r for r in range(len(targets)) if active_rows[r] and
                    targets[r] == molecule and energies[r] == energy]
            if rows:
                reduction[g, e, rows] = 1 / len(rows)
                energy_weights[g, e] = 1
                observed += 1
        energy_weights[g] /= observed
    return reduction, energy_weights, candidates, positives


def jax_masked_loss(logits, reduction, energy_weights, candidates, positives):
    """A pure, static-shape JAX expression; no host/device membership queries."""
    reduction = reduction.astype(logits.dtype)
    energy_weights = energy_weights.astype(logits.dtype)
    positives = positives.astype(logits.dtype)
    means = jnp.einsum('ger,rc->gec', reduction, logits, precision='highest')
    pooled = jnp.einsum('ge,gec->gc', energy_weights, means, precision='highest')
    pooled_ce = logsumexp(jnp.where(candidates, pooled, -jnp.inf), axis=-1) - jnp.sum(pooled*positives, axis=-1)
    per_energy_ce = logsumexp(jnp.where(candidates[:, None, :], means, -jnp.inf), axis=-1) - jnp.sum(means*positives[:, None, :], axis=-1)
    balanced_ce = jnp.sum(per_energy_ce*energy_weights, axis=-1)
    return jnp.mean(ETA*pooled_ce + (1-ETA)*balanced_ce)


def jax_head_loss(ws, wm, spectral, molecular, reduction, energy_weights, candidates, positives):
    zs = jnp.matmul(spectral, ws, precision='highest')
    zm = jnp.matmul(molecular, wm, precision='highest')
    logits = jnp.matmul(zs, zm.T, precision='highest') * SCALE
    return jax_masked_loss(logits, reduction, energy_weights, candidates, positives)


LOGIT_VG = jax.jit(jax.value_and_grad(jax_masked_loss, argnums=0))
HEAD_VG = jax.jit(jax.value_and_grad(jax_head_loss, argnums=(0, 1)))
HEAD_VALUE = jax.jit(jax_head_loss)


def await_arrays(tree):
    return jax.tree.map(lambda x: x.block_until_ready(), tree)


def numpy_tree(tree):
    return jax.tree.map(np.asarray, await_arrays(tree))


def metrics(actual, expected):
    delta = np.asarray(actual, dtype=np.float64) - np.asarray(expected, dtype=np.float64)
    return {'maximum_absolute': float(np.max(np.abs(delta))),
            'relative_l2': float(np.linalg.norm(delta) / max(np.linalg.norm(expected), 1e-30))}


def main():
    devices = jax.devices()
    if any(d.platform != 'cpu' for d in devices) or jax.default_backend() != 'cpu':
        raise RuntimeError('Only the inspected CPU backend is authorized')
    if jax.__version__ != '0.11.0' or np.__version__ != '2.2.6':
        raise RuntimeError('Inspected package versions drifted')
    authority_bytes = AUTHORITY.read_bytes()
    if sha(authority_bytes) != AUTHORITY_SHA:
        raise RuntimeError('Frozen NumPy authority drift')
    with (HERE/'frozen_energy_authority.py').open('xb') as stream:
        stream.write(authority_bytes)
    namespace = {'__name__': 'frozen_energy_authority'}
    exec(compile(authority_bytes, str(AUTHORITY), 'exec'), namespace)
    authority = namespace['energy_balanced_loss']
    strata = [{20:1, 40:4}, {20:2, 60:1}, {40:1}, {20:3, 40:1, 60:2},
              {60:1}, {20:2, 40:1}, {40:2, 60:1}]
    tr, er = [], []
    for m, histogram in enumerate(strata):
        for e, count in histogram.items():
            tr += [m]*count
            er += [e]*count
    active_count = len(tr)
    targets, energies = np.array(tr+[-1]*3), np.array(er+[0]*3, dtype=np.float64)
    row_active, col_active = np.arange(len(targets)) < active_count, np.arange(9) < 7
    formulas = np.array(['F_A']*3+['F_B']*2+['F_C']*2+['PAD']*2)
    rng = np.random.default_rng(SEED)
    spectral = rng.normal(size=(len(targets), 1024))
    molecular = rng.normal(size=(9, 768))
    ws = rng.normal(0, 1/math.sqrt(1024), size=(1024, WIDTH))
    wm = rng.normal(0, 1/math.sqrt(768), size=(768, WIDTH))
    plan = host_plan(targets, energies, formulas, row_active, col_active)
    pins = {'spectral':array_pin(spectral), 'molecular':array_pin(molecular),
            'spectral_head':array_pin(ws), 'molecular_head':array_pin(wm),
            **{'plan_%d'%i:array_pin(x) for i,x in enumerate(plan)}}
    source_sha = sha(Path(__file__).read_bytes())
    save_new('frozen_protocol.json', {
        'scope':'SYNTHETIC_CPU_PURE_JAX_NUMERICAL_READINESS_ONLY', 'source_sha256':source_sha,
        'authority_sha256':AUTHORITY_SHA, 'seed':SEED, 'strata':strata, 'eta':ETA,
        'width':WIDTH, 'sgd_rate':RATE, 'all_input_initialization_and_plan_pins':pins,
        'jax':'0.11.0', 'jaxlib':'0.11.0', 'numpy':'2.2.6',
        'x64_explicitly_enabled':True, 'matmul_precision':'highest',
        'hard_CPU_seconds':30, 'wall_failsafe_seconds':60,
        'FP64_loss_atol':1e-11, 'FP64_gradient_rtol':1e-10, 'FP64_gradient_atol':1e-11,
        'finite_difference_samples_per_head':8, 'finite_difference_step':1e-5,
        'finite_difference_atol':2e-8, 'finite_difference_rtol':2e-5,
        'FP32':'Record disagreement separately; no TPU precision extrapolation',
        'pure_kernel_dynamic_shapes':False, 'host_metadata_only_grouping':True,
        'no_competition_model_data_weights_or_TPU_call':True})
    checks, timings = [], {}
    def check(name, condition, evidence=None):
        checks.append({'check':name, 'passed':bool(condition), 'evidence':evidence})
        if not condition:
            raise AssertionError(name)
    def reference(logits, ts=targets, es=energies, fs=formulas, ra=row_active, ca=col_active):
        cs, rs = np.flatnonzero(ca), np.flatnonzero(ra)
        lookup = {int(c):i for i,c in enumerate(cs)}
        mapped = np.array([lookup[int(ts[r])] for r in rs])
        loss, compact_gradient = authority(logits[np.ix_(rs,cs)], mapped, es[rs],
            ['SYNTHETIC_%d'%c for c in cs], fs[cs].tolist(), eta=ETA)
        gradient = np.zeros(logits.shape, dtype=np.float64)
        gradient[np.ix_(rs,cs)] = compact_gradient
        return loss, gradient
    def analytical_heads(s, m, sw, mw, gradient):
        zs, zm = s@sw, m@mw
        return s.T@(gradient@zm)*SCALE, m.T@(gradient.T@zs)*SCALE

    x = ((spectral@ws)@(molecular@wm).T)*SCALE
    rv, rg = reference(x)
    start = time.monotonic()
    jv, jg = numpy_tree(LOGIT_VG(jnp.asarray(x), *map(jnp.asarray, plan)))
    timings['FP64_logit_value_gradient_first_compile_and_execution_seconds'] = time.monotonic()-start
    check('JAX_FP64_same_logit_loss_and_all_225_derivatives_match_authority',
          abs(float(jv)-rv) <= 1e-11 and np.allclose(jg,rg,rtol=1e-10,atol=1e-11),
          {'loss_absolute_delta':abs(float(jv)-rv),'derivatives':metrics(jg,rg)})
    start=time.monotonic()
    hv,(hs,hm)=numpy_tree(HEAD_VG(*map(jnp.asarray,(ws,wm,spectral,molecular,*plan))))
    timings['FP64_head_value_gradients_first_compile_and_execution_seconds']=time.monotonic()-start
    rs,rm=analytical_heads(spectral,molecular,ws,wm,rg)
    head64={'loss_absolute_delta':abs(float(hv)-rv),'spectral_gradient':metrics(hs,rs),
            'molecular_gradient':metrics(hm,rm),'full_gradient_parameter_count':int(hs.size+hm.size)}
    check('independent_JAX_autodiff_all_458752_head_derivatives_match_analytic_NumPy',
          abs(float(hv)-rv)<=1e-11 and np.allclose(hs,rs,rtol=1e-10,atol=1e-11) and
          np.allclose(hm,rm,rtol=1e-10,atol=1e-11),head64)
    check('one_full_SGD_update_matches_authority',
          np.allclose(ws-RATE*hs,ws-RATE*rs,rtol=1e-10,atol=1e-11) and
          np.allclose(wm-RATE*hm,wm-RATE*rm,rtol=1e-10,atol=1e-11))
    forbidden=~row_active[:,None]|~col_active[None,:]|(
        row_active[:,None]&(formulas[np.maximum(targets,0),None]!=formulas[None,:]))
    check('every_padding_and_cross_formula_logit_derivative_is_exact_zero',np.count_nonzero(jg[forbidden])==0)
    poisoned=x.copy();poisoned[forbidden]=rng.choice([-1e4,1e4],size=int(forbidden.sum()))
    pv,pg=numpy_tree(LOGIT_VG(jnp.asarray(poisoned),*map(jnp.asarray,plan)))
    check('excluded_extreme_logits_leave_JAX_loss_and_every_derivative_unchanged',
          float(pv)==float(jv) and np.array_equal(pg,jg))
    rp,cp=rng.permutation(len(targets)),rng.permutation(len(formulas))
    inverse=np.argsort(cp)
    pt=np.where(targets[rp]>=0,inverse[np.maximum(targets[rp],0)],-1)
    pp=host_plan(pt,energies[rp],formulas[cp],row_active[rp],col_active[cp])
    perm_value,perm_gradient=numpy_tree(LOGIT_VG(jnp.asarray(x[np.ix_(rp,cp)]),*map(jnp.asarray,pp)))
    restored=np.empty_like(perm_gradient);restored[np.ix_(rp,cp)]=perm_gradient
    check('row_column_permutation_preserves_loss_and_all_logit_derivatives',
          abs(float(perm_value)-float(jv))<=1e-11 and np.allclose(restored,jg,rtol=1e-10,atol=1e-11))
    perm_hv,(perm_hs,perm_hm)=numpy_tree(HEAD_VG(*map(jnp.asarray,(ws,wm,spectral[rp],molecular[cp],*pp))))
    check('row_column_permutation_preserves_both_complete_head_gradients',
          abs(float(perm_hv)-float(hv))<=1e-11 and np.allclose(perm_hs,hs,rtol=1e-10,atol=1e-11) and
          np.allclose(perm_hm,hm,rtol=1e-10,atol=1e-11))
    duplicate_row=np.flatnonzero((targets==0)&(energies==20))[0]
    duplicate_indices=np.r_[np.arange(active_count),np.repeat(duplicate_row,9)]
    dp=host_plan(targets[duplicate_indices],energies[duplicate_indices],formulas,
                 np.ones(len(duplicate_indices),dtype=bool),col_active)
    duplicate_v,(duplicate_gs,duplicate_gm)=numpy_tree(HEAD_VG(*map(jnp.asarray,
        (ws,wm,spectral[duplicate_indices],molecular,*dp))))
    check('CE_replication_preserves_equal_energy_JAX_loss_and_full_head_gradients',
          abs(float(duplicate_v)-float(hv))<=1e-11 and np.allclose(duplicate_gs,hs,rtol=1e-10,atol=1e-11) and
          np.allclose(duplicate_gm,hm,rtol=1e-10,atol=1e-11),
          {'spectral':metrics(duplicate_gs,hs),'molecular':metrics(duplicate_gm,hm)})
    check('missing_CEs_have_zero_weights_and_each_molecule_sums_to_one',
          np.array_equal((plan[1]>0).sum(axis=1),np.array([2,2,1,3,1,2,2])) and
          np.allclose(plan[1].sum(axis=1),1,rtol=0,atol=1e-15))
    repeated_v,(repeated_gs,repeated_gm)=numpy_tree(HEAD_VG(*map(jnp.asarray,(ws,wm,spectral,molecular,*plan))))
    check('same_JIT_arguments_repeat_bit_identically_on_this_CPU',
          np.array_equal(repeated_v,hv) and np.array_equal(repeated_gs,hs) and np.array_equal(repeated_gm,hm))

    finite=[]
    for name,head,analytic in [('spectral',ws,hs),('molecular',wm,hm)]:
        samples=np.r_[int(np.argmax(np.abs(analytic))),rng.choice(head.size,size=7,replace=False)]
        for flat in samples:
            index=np.unravel_index(int(flat),head.shape)
            plus,minus=head.copy(),head.copy();plus[index]+=1e-5;minus[index]-=1e-5
            args_plus=(plus,wm) if name=='spectral' else (ws,plus)
            args_minus=(minus,wm) if name=='spectral' else (ws,minus)
            pv=float(await_arrays(HEAD_VALUE(*map(jnp.asarray,(*args_plus,spectral,molecular,*plan)))))
            mv=float(await_arrays(HEAD_VALUE(*map(jnp.asarray,(*args_minus,spectral,molecular,*plan)))))
            numerical=(pv-mv)/2e-5;exact=float(analytic[index]);error=abs(numerical-exact)
            finite.append({'head':name,'index':list(map(int,index)),'analytic':exact,
                           'central_difference':numerical,'absolute_error':error,
                           'passed':error<=2e-8+2e-5*abs(exact)})
    check('16_parameter_finite_differences_match_independent_JAX_autodiff',all(f['passed'] for f in finite),
          {'maximum_absolute_error':max(f['absolute_error'] for f in finite)})

    ws32,wm32,s32,m32=[a.astype(np.float32) for a in (ws,wm,spectral,molecular)]
    p32=tuple(a if a.dtype.kind=='b' else a.astype(np.float32) for a in plan)
    start=time.monotonic()
    v32,(gs32,gm32)=numpy_tree(HEAD_VG(*map(jnp.asarray,(ws32,wm32,s32,m32,*p32))))
    timings['FP32_head_value_gradients_first_compile_and_execution_seconds']=time.monotonic()-start
    # Compare against FP64 evaluation of the exact FP32 initial arrays, as well as
    # the original FP64 initialization, separating rounding from dtype arithmetic.
    x32_initials=((s32.astype(np.float64)@ws32.astype(np.float64))@
                 (m32.astype(np.float64)@wm32.astype(np.float64)).T)*SCALE
    ref32value,ref32gradient=reference(x32_initials)
    ref32gs,ref32gm=analytical_heads(s32.astype(np.float64),m32.astype(np.float64),
                                    ws32.astype(np.float64),wm32.astype(np.float64),ref32gradient)
    fp32={'JAX_loss':float(v32),'authority_FP64_of_exact_FP32_arrays_loss':ref32value,
          'same_initial_arrays_loss_absolute_delta':abs(float(v32)-ref32value),
          'same_initial_arrays_spectral_gradient':metrics(gs32,ref32gs),
          'same_initial_arrays_molecular_gradient':metrics(gm32,ref32gm),
          'end_to_end_loss_absolute_delta_vs_original_FP64':abs(float(v32)-rv),
          'end_to_end_spectral_gradient':metrics(gs32,rs),
          'end_to_end_molecular_gradient':metrics(gm32,rm),
          'spectral_one_SGD_update':metrics(ws32-RATE*gs32,ws-RATE*rs),
          'molecular_one_SGD_update':metrics(wm32-RATE*gm32,wm-RATE*rm),
          'loss_dtype':str(v32.dtype),'spectral_gradient_dtype':str(gs32.dtype),
          'molecular_gradient_dtype':str(gm32.dtype),'TPU_BF16_equivalence_claim':None}
    check('explicit_FP32_outputs_remain_FP32_with_global_x64_enabled',
          v32.dtype==gs32.dtype==gm32.dtype==np.dtype('float32'))
    value32logits,grad32logits=numpy_tree(LOGIT_VG(jnp.asarray(x.astype(np.float32)),*map(jnp.asarray,p32)))
    check('FP32_JAX_padding_and_cross_formula_derivatives_still_exact_zero',np.count_nonzero(grad32logits[forbidden])==0)
    check('frozen_authority_and_all_initial_arrays_preserved',sha(AUTHORITY.read_bytes())==AUTHORITY_SHA and pins=={
        'spectral':array_pin(spectral),'molecular':array_pin(molecular),'spectral_head':array_pin(ws),
        'molecular_head':array_pin(wm),**{'plan_%d'%i:array_pin(x) for i,x in enumerate(plan)}})
    current=resource.getrusage(resource.RUSAGE_SELF)
    cpu=current.ru_utime+current.ru_stime-INITIAL_CPU.ru_utime-INITIAL_CPU.ru_stime
    wall=time.monotonic()-START
    check('complete_CPU_and_wall_budgets_pass',cpu<30 and wall<60,{'process_CPU_seconds':cpu,'wall_seconds':wall})
    receipt={'status':'PASS_CPU_JAX_SYNTHETIC_FIXED_MASK_NUMERICAL_READINESS_ONLY',
        'source_sha256':source_sha,'authority_sha256':AUTHORITY_SHA,
        'protocol_sha256':sha((HERE/'frozen_protocol.json').read_bytes()),
        'checks':checks,'checks_passed':len(checks),'FP64':head64,'FP32_measured_disagreement':fp32,
        'finite_differences':finite,'measured_first_call_times_include_compile_and_execution':timings,
        'runtime':{'python':sys.version.split()[0],'jax':jax.__version__,'jaxlib':'0.11.0',
                   'numpy':np.__version__,'x64':bool(jax.config.jax_enable_x64),
                   'matmul_precision':str(jax.config.jax_default_matmul_precision),
                   'devices':[{'platform':d.platform,'device_kind':d.device_kind,'id':d.id} for d in devices]},
        'elapsed_process_CPU_seconds':cpu,'elapsed_wall_seconds':wall,
        'speedup_claim':None,'native_TPU_readiness':'HOLD_FOR_NATIVE_TPU_RUNTIME_PARITY_AND_TIMING',
        'encoder_model_chemical_data_retrieval_or_competition_calls':False}
    save_new('terminal_receipt.json',receipt)
    print(json.dumps({'status':receipt['status'],'checks_passed':len(checks),'CPU_seconds':cpu,
        'wall_seconds':wall,'source_sha256':source_sha,
        'receipt_sha256':sha((HERE/'terminal_receipt.json').read_bytes())},sort_keys=True))


if __name__=='__main__':
    main()
