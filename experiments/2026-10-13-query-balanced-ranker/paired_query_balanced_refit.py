# SPDX-License-Identifier: MIT
"""Original, root-reviewed LOCAL CASMI objective screen; no remote operations.

One treatment changes training-row weights, keeping every original 31D feature,
candidate, label, row order, fold, fit roster and HGB parameter unchanged. Four
new fits compare ordinary simulation weights with equal query/simulation mass.
This is reused historical development evidence, not a native or official gain.
"""
import time
START = time.monotonic()
import os
for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[name] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
import argparse
import hashlib
import json
import resource
import signal
import sys
import threading
from pathlib import Path

WALL_CAP, CPU_CAP, RSS_CAP = 240.0, 180.0, 2 * (1 << 30)
DEADLINE = START + WALL_CAP
resource.setrlimit(resource.RLIMIT_CPU, (int(CPU_CAP), int(CPU_CAP) + 1))

def rss_bytes():
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * (1 if sys.platform == 'darwin' else 1024)

def tick():
    if time.monotonic() >= DEADLINE - 2 or rss_bytes() > RSS_CAP:
        raise TimeoutError('original wall/RSS envelope exhausted')

def watchdog():
    while True:
        if time.monotonic() >= DEADLINE or rss_bytes() > RSS_CAP:
            os._exit(87)
        time.sleep(0.05)

threading.Thread(target=watchdog, daemon=True).start()
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('original 240s envelope')))
signal.setitimer(signal.ITIMER_REAL, max(0.001, DEADLINE - time.monotonic()))

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''):
            tick()
            h.update(block)
    return h.hexdigest()

def load_pinned(row):
    path = Path(row['path'])
    assert path.is_file() and not path.is_symlink()
    assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256']
    return path

def closed_json(path, obj):
    tick()
    raw = json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    assert len(raw) < 8 * (1 << 20)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    assert digest(path) == hashlib.sha256(raw).hexdigest()
    return hashlib.sha256(raw).hexdigest()

ap = argparse.ArgumentParser()
ap.add_argument('--root-reviewed-local-benchmark', action='store_true', required=True)
ap.add_argument('--source-sha256', required=True)
ap.add_argument('--registration', type=Path, required=True)
ap.add_argument('--registration-sha256', required=True)
ap.add_argument('--peer', type=Path, required=True)
ap.add_argument('--peer-sha256', required=True)
ap.add_argument('--output', type=Path, required=True)
args = ap.parse_args()
HERE = Path(__file__).resolve().parent
assert not any(os.environ.get(k) for k in ('KAGGLE_API_TOKEN', 'KAGGLE_KEY', 'KAGGLE_USERNAME'))
assert not sys.flags.optimize and digest(Path(__file__)) == args.source_sha256
assert args.registration.resolve().parent == HERE and digest(args.registration) == args.registration_sha256
reg = json.loads(args.registration.read_bytes())
assert reg['schema'] == 'CASMI_QUERY_BALANCED_HISTORICAL_RANK_SCREEN_REGISTRATION_V1'
assert reg['status'] == 'PREREGISTERED_SOURCE_ONLY_NO_FITS_EXECUTED'
assert reg['source_sha256'] == args.source_sha256
assert reg['caps'] == {'original_wall_seconds': 240, 'process_CPU_seconds': 180,
                      'sampled_peak_RSS_bytes': RSS_CAP, 'math_threads': 1,
                      'child_processes': 0, 'fit_calls': 4, 'max_iter': 128}
assert digest(args.peer) == args.peer_sha256
peer = json.loads(args.peer.read_bytes())
assert peer['qualification'] == 'PASS_SOURCE_ONLY_CASMI_QUERY_BALANCED_RANK_SCREEN_V1'
assert peer['source_sha256'] == args.source_sha256
assert peer['registration_sha256'] == args.registration_sha256
assert peer['checks'] and all(v is True for v in peer['checks'].values())
assert peer['fit_calls_performed'] == 0 and peer['blocking_findings'] == []
assert args.output.resolve().parent == HERE and not args.output.exists()
args.output.mkdir(parents=False, exist_ok=False)

import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_info, threadpool_limits

def query_balanced_weights(query_ids, simulation_ids):
    """Equal group mass, then one scalar preserving baseline total weight.

    Counts come from this fit's actual rows. No held labels or feature values
    enter the weighting rule. It intentionally changes weighted positive prior
    and relative leaf regularization; this is not a new class-balancing arm.
    """
    q, m = np.asarray(query_ids), np.asarray(simulation_ids)
    if q.ndim != 1 or q.shape != m.shape or not len(q):
        raise ValueError('nonempty joined training vectors required')
    if q.dtype.kind not in 'iu' or m.dtype.kind not in 'iu' or np.any(q < 0) or not np.isin(m, [0, 1]).all():
        raise ValueError('nonnegative queries and simulation0/1 required')
    group = q.astype(np.int64) * 2 + m.astype(np.int64)
    unique, inverse, counts = np.unique(group, return_inverse=True, return_counts=True)
    if not np.array_equal(unique[::2] + 1, unique[1::2]) or not np.all(unique[::2] % 2 == 0):
        raise ValueError('both simulations of every training query required')
    if not np.array_equal(counts[::2], counts[1::2]):
        raise ValueError('paired simulations must retain identical pool sizes')
    baseline = np.where(m == 0, 0.30, 0.70).astype(np.float64)
    treatment = baseline / counts[inverse]
    treatment *= baseline.sum(dtype=np.float64) / treatment.sum(dtype=np.float64)
    if not np.isfinite(treatment).all() or not np.all(treatment > 0):
        raise ValueError('invalid treatment weights')
    if not np.isclose(treatment.sum(), baseline.sum(), rtol=1e-13, atol=1e-10):
        raise ValueError('global weighted loss scale changed')
    return baseline, treatment, group

def expected_rank_metrics(scores, labels):
    """Expected RR@25/top1/top25 under uniform order of exact score ties.

    Ties extending past rank25 include zero contributions beyond rank25. The
    positive position is never selected by source order or an identity hash.
    """
    score, y = np.asarray(scores), np.asarray(labels)
    if score.ndim != 1 or y.shape != score.shape or not np.isfinite(score).all():
        raise ValueError('finite complete candidate group required')
    if not np.isin(y, [0, 1]).all() or int(y.sum()) != 1:
        raise ValueError('exactly one positive required')
    truth_score = score[np.flatnonzero(y)[0]]
    above, tied = int((score > truth_score).sum()), int((score == truth_score).sum())
    assert tied >= 1
    positions = np.arange(above + 1, min(above + tied, 25) + 1, dtype=np.float64)
    reciprocal = float((1.0 / positions).sum() / tied)
    top1 = 1.0 / tied if above == 0 else 0.0
    top25 = float(max(0, min(tied, 25 - above)) / tied)
    return reciprocal, top1, top25, tied

prior_path = load_pinned(reg['physical_inputs']['prior_registration'])
prior = json.loads(prior_path.read_bytes())
sidecar = json.loads(load_pinned(reg['physical_inputs']['ordered_positive_pool_sidecar']).read_bytes())
bridge = json.loads(load_pinned(reg['physical_inputs']['ordered_native_bridge']).read_bytes())
path = load_pinned(reg['physical_inputs']['numeric_rows_npz'])
prior_oof_path = load_pinned(reg['physical_inputs']['prior_oof_predictions'])
assert prior['schema'] == 'CASMI_HISTORICAL_ANONYMOUS_TIE_REFIT_REGISTRATION_V1'
assert reg['fit_params'] == prior['fit_params'] and reg['fit_params']['max_iter'] == 128
assert reg['fit_roster_G'] == prior['fit_roster_G'] and reg['fold_for_G'] == prior['fold_for_G']
assert reg['features'] == prior['features'] and reg['runtime_required'] == prior['runtime']
assert reg['runtime_required'] == {'numpy': np.__version__, 'sklearn': sklearn.__version__, 'platform': sys.platform}
assert sidecar['schema'] == 'CASMI_NUMERIC_ROWS_ORDERED_QUERY_POSITIVE_POOL_ID_SIDECAR_V1'
assert all(sidecar['evidence'].values()) and len(sidecar['queries']) == 2965
assert [r['query_index'] for r in sidecar['queries']] == list(range(2965))
assert bridge['schema'] == 'CASMI_PRIVATE_ORDERED_NUMERIC_G_NATIVE_CLASS_BRIDGE_V1'
assert bridge['qualification'] == 'PASS_DATA_ONLY_ORDERED_CANDIDATE_AND_NATIVE_IDENTITY_BRIDGE'
assert len(bridge['ordered_bridge']) == 2965
assert bridge['evidence']['crossfold_alias_pairs'] == 0
assert bridge['evidence']['crossfold_alias_evaluations_with_fit_roster_counterpart'] == 0
for g, row in enumerate(bridge['ordered_bridge']):
    assert row['query_index'] == g and row['positive_pool_id'] == sidecar['queries'][g]['positive_pool_id']
    assert row['root_registered_fold'] == prior['fold_for_G'][g]
    assert row['root_fit_roster_member'] == (g in set(prior['fit_roster_G']))
with np.load(path, allow_pickle=False) as z:
    assert set(z.files) == {'X', 'Y', 'M', 'G', 'feature_names', 'simulation_names'}
    X, Y, M, G = (z[k] for k in ('X', 'Y', 'M', 'G'))
    assert z['feature_names'].tolist() == reg['features']
assert X.dtype == np.float32 and X.shape == (736788, 31) and np.isfinite(X).all()
assert Y.shape == M.shape == G.shape == (len(X),) and set(np.unique(Y)) == {0, 1}
assert np.array_equal(np.unique(G), np.arange(2965)) and np.isin(M, [0, 1]).all()
pair = G.astype(np.int64) * 2 + M.astype(np.int64)
order = np.argsort(pair, kind='stable')
starts = np.r_[0, np.flatnonzero(np.diff(pair[order])) + 1]
ends = np.r_[starts[1:], len(order)]
assert len(starts) == 5930
for a, b in zip(starts, ends):
    assert int(Y[order[a:b]].sum()) == 1
    tick()
folds = np.asarray(prior['fold_for_G'], dtype=np.int64)
selected = np.zeros(2965, dtype=bool)
assert len(prior['fit_roster_G']) == len(set(prior['fit_roster_G'])) == 512
selected[prior['fit_roster_G']] = True
assert set(folds) == {0, 1}
reg_sha = closed_json(args.output / 'PRIVATE_PRE_FIT_REGISTRATION.json', reg)
assert reg_sha == args.registration_sha256
closed_json(HERE / 'LOCAL_FIT_ONCE.json', {
    'schema': 'CASMI_QUERY_BALANCED_SCREEN_ONE_LOCAL_ATTEMPT_V1',
    'source_sha256': args.source_sha256, 'registration_sha256': reg_sha,
    'peer_sha256': args.peer_sha256, 'output': str(args.output),
    'never_retry_consumed_or_ambiguous_attempt': True, 'fit_calls_planned': 4,
})
predictions = np.full((2, len(X)), np.nan, dtype=np.float64)
fits = []
with threadpool_limits(limits=1):
    assert all(p['num_threads'] == 1 for p in threadpool_info())
    for fold in (0, 1):
        tr = np.flatnonzero(selected[G] & (folds[G] != fold))
        ev = np.flatnonzero(folds[G] == fold)
        tr_queries, ev_queries = set(map(int, G[tr])), set(map(int, G[ev]))
        assert tr_queries and ev_queries and tr_queries.isdisjoint(ev_queries)
        assert set(bridge['ordered_bridge'][g]['native_group_id'] for g in tr_queries).isdisjoint(
            bridge['ordered_bridge'][g]['native_group_id'] for g in ev_queries)
        weights = query_balanced_weights(G[tr], M[tr])
        unique, inverse = np.unique(weights[2], return_inverse=True)
        assert len(unique) == 2 * len(tr_queries)
        assert np.all(np.bincount(inverse, weights=Y[tr]) == 1)
        for arm, weight in enumerate(weights[:2]):
            tick()
            before = time.monotonic()
            estimator = HistGradientBoostingClassifier(**reg['fit_params'])
            estimator.fit(X[tr], Y[tr], sample_weight=weight)
            tick()
            predictions[arm, ev] = estimator.predict_proba(X[ev])[:, 1]
            assert estimator.n_iter_ == 128
            group_mass = np.bincount(inverse, weights=weight)
            fits.append({
                'fold': fold, 'arm': ('original', 'query_balanced')[arm],
                'train_queries': len(tr_queries), 'train_rows': len(tr),
                'evaluation_queries': len(ev_queries), 'evaluation_rows': len(ev),
                'iterations': int(estimator.n_iter_), 'seconds': time.monotonic() - before,
                'weight_sum': float(weight.sum()),
                'weight_sum_by_simulation': [float(weight[M[tr] == m].sum()) for m in (0, 1)],
                'weighted_positive_prevalence': float(weight @ Y[tr] / weight.sum()),
                'group_mass_min_max_by_simulation': [
                    [float(group_mass[unique % 2 == m].min()), float(group_mass[unique % 2 == m].max())]
                    for m in (0, 1)],
            })
            del estimator
            tick()
assert len(fits) == 4 and np.isfinite(predictions).all()
pred_path = args.output / 'PRIVATE_OOF_PREDICTIONS.npz'
with pred_path.open('xb') as stream:
    np.savez(stream, scores=predictions, G=G, M=M)
    stream.flush()
    os.fsync(stream.fileno())
pred_sha = digest(pred_path)
closed_json(args.output / 'PRIVATE_PREDICTION_SEAL.json', {
    'schema': 'CASMI_QUERY_BALANCED_COMPLETE_PRE_METRIC_PREDICTION_SEAL_V1',
    'prediction_sha256': pred_sha, 'registration_sha256': reg_sha,
    'fit_calls': 4, 'OOF_scores_complete': True, 'held_query_rank_metrics_not_yet_joined': True,
    'feature_matrix_unchanged_both_arms': True, 'native_validation_qualified': False,
})
with np.load(prior_oof_path, allow_pickle=False) as z:
    assert set(z.files) == {'scores', 'G', 'M'}
    assert np.array_equal(z['G'], G) and np.array_equal(z['M'], M)
    assert np.array_equal(predictions[0], z['scores'][0]), 'fresh control failed exact prior-OOF parity'
metrics = np.zeros((2, 2965, 2, 3), dtype=np.float64)
ties = np.zeros((2, 2), dtype=np.int64)
for a, b in zip(starts, ends):
    ix = order[a:b]
    g, m = int(G[ix[0]]), int(M[ix[0]])
    for arm in (0, 1):
        rr, top1, top25, tied = expected_rank_metrics(predictions[arm, ix], Y[ix])
        metrics[arm, g, m] = [rr, top1, top25]
        ties[arm, m] += int(tied > 1)
    tick()
rng = np.random.default_rng(20261013)
summaries = []
for m in (0, 1):
    delta = metrics[1, :, m, 0] - metrics[0, :, m, 0]
    bootstrap = np.empty(5000, dtype=np.float64)
    for a in range(0, 5000, 100):
        bootstrap[a:a + 100] = delta[rng.integers(0, 2965, size=(100, 2965))].mean(axis=1)
        tick()
    summaries.append({
        'simulation': m, 'endpoint_role': 'primary_Class2' if m == 1 else 'secondary_Class1',
        'anonymous_queries': 2965, 'tied_prediction_metric': 'uniform_exact_tie_expectation',
        'arms': {name: {
            'conditional_expected_MRR25': float(metrics[arm, :, m, 0].mean()),
            'expected_top1_count': float(metrics[arm, :, m, 1].sum()),
            'expected_top25_count': float(metrics[arm, :, m, 2].sum()),
            'positive_prediction_tie_groups': int(ties[arm, m]),
            'count_only_zero_extended_expected_MRR3000': float(metrics[arm, :, m, 0].sum() / 3000),
        } for arm, name in enumerate(('original', 'query_balanced'))},
        'paired_delta_conditional_expected_MRR25': float(delta.mean()),
        'query_CI95': np.quantile(bootstrap, [0.025, 0.975]).tolist(),
        'query_bootstrap_repetitions': 5000, 'native_class_CI_qualified': False,
        'wins': int((delta > 0).sum()), 'losses': int((delta < 0).sum()), 'ties': int((delta == 0).sum()),
    })
result = {
    'schema': 'CASMI_QUERY_BALANCED_HISTORICAL_RANK_SCREEN_RESULT_V1',
    'status': 'PASS_COMPLETED_LOCAL_HISTORICAL_SCREEN_ONLY',
    'registration_sha256': reg_sha, 'prediction_sha256': pred_sha,
    'source_sha256': args.source_sha256, 'peer_sha256': args.peer_sha256,
    'fresh_original_control_exact_prior_OOF_parity': True,
    'fits': fits, 'summaries': summaries, 'fit_calls': 4,
    'elapsed_before_receipt_seconds': time.monotonic() - START,
    'CPU_seconds': resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
    'peak_RSS_bytes': rss_bytes(), 'child_processes_created': 0,
    'checkpoint_selection_exposure': 'UNKNOWN', 'native_validation_qualified': False,
    'official_score': None, 'native_score': None, 'promotion_qualified': False,
    'limitations': reg['limitations'],
}
result_sha = closed_json(args.output / 'PRIVATE_LOCAL_BENCHMARK_RESULT.json', result)
tick()
print(json.dumps({'status': result['status'], 'fit_calls': 4,
                  'result_sha256': result_sha, 'prediction_sha256': pred_sha,
                  'output': str(args.output), 'official_score': None,
                  'promotion_qualified': False}, sort_keys=True), flush=True)
tick()
