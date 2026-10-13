# SPDX-License-Identifier: MIT
"""Root-reviewed LOCAL anonymous historical benchmark, never a Kaggle carrier.

Four new CPU fits, two folds and two matched treatments. All 2,965 historical
queries receive OOF predictions; each fit uses only a fixed 512-query roster's
opposite fold. Pool identity groups both simulations, but tautomer alias closure
and learned-feature checkpoint exposure are unqualified. No native score,
model export, new fingerprint producer, public publication, or promotion.
"""
import time
START = time.monotonic()  # First operation; startup consumes the same 240s cap.
import os
for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
import argparse, hashlib, json, resource, signal, sys, threading
from pathlib import Path

WALL_CAP, CPU_CAP, RSS_CAP = 240., 180., 2 * (1 << 30)
DEADLINE = START + WALL_CAP
resource.setrlimit(resource.RLIMIT_CPU, (int(CPU_CAP), int(CPU_CAP) + 1))
def rss_bytes():
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * (1 if sys.platform == 'darwin' else 1024)
def guard():
    while True:
        if time.monotonic() >= DEADLINE or rss_bytes() > RSS_CAP:
            # This worker creates no child process. No receipt means no success.
            os._exit(87)
        time.sleep(.05)
threading.Thread(target=guard, daemon=True).start()
def tick():
    if time.monotonic() >= DEADLINE - 2 or rss_bytes() > RSS_CAP:
        raise TimeoutError('original wall/RSS envelope exhausted')
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('original240s envelope')))
signal.setitimer(signal.ITIMER_REAL,max(.001,DEADLINE-time.monotonic()))

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8<<20),b''):
            tick();h.update(block)
    return h.hexdigest()

ap=argparse.ArgumentParser()
ap.add_argument('--root-reviewed-local-benchmark',action='store_true',required=True)
ap.add_argument('--source-sha256',required=True)
ap.add_argument('--feature-sha256',required=True)
ap.add_argument('--sidecar',type=Path,required=True)
ap.add_argument('--sidecar-sha256',required=True)
ap.add_argument('--output',type=Path,required=True)
args=ap.parse_args()
HERE=Path(__file__).resolve().parent
assert digest(Path(__file__))==args.source_sha256
assert digest(HERE/'tie_neutral_features.py')==args.feature_sha256
assert digest(args.sidecar)==args.sidecar_sha256
assert args.sidecar_sha256=='c52e4641fa5d237b7f8555b6063540626ec47c3b55645aca14e68bd6000d1286'
assert not args.output.exists()
args.output.mkdir(parents=False,exist_ok=False)
def write_json(name,obj):
    tick()
    raw=json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    assert len(raw)<8*(1<<20)
    with (args.output/name).open('xb') as f:f.write(raw)
    return hashlib.sha256(raw).hexdigest()

import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits,threadpool_info
sys.path.insert(0,str(HERE))
from tie_neutral_features import FEATURES,transform_query_features,group_query_simulation
sidecar=json.loads(args.sidecar.read_text())
assert sidecar['schema']=='CASMI_NUMERIC_ROWS_ORDERED_QUERY_POSITIVE_POOL_ID_SIDECAR_V1'
assert all(sidecar['evidence'].values())
qrows=sidecar['queries']
assert len(qrows)==2965 and [q['query_index'] for q in qrows]==list(range(2965))
positive_ids=[q['positive_pool_id'] for q in qrows]
assert len(set(positive_ids))==2965 and all(type(v)is int and v>=0 for v in positive_ids)
path=Path(sidecar['physical_inputs']['numeric_rows_npz']['path'])
assert path.stat().st_size==44702864 and digest(path)=='085fe385803d33a76b62533300315e0dd722236f7895c7f9c6e9dcf1fb0fea88'
with np.load(path,allow_pickle=False) as z:
    assert set(z.files)=={'X','Y','M','G','feature_names','simulation_names'}
    X,Y,M,G=(z[k] for k in ('X','Y','M','G'))
    assert z['feature_names'].tolist()==list(FEATURES)
assert X.dtype==np.float32 and X.shape==(736788,31) and np.isfinite(X).all()
assert Y.shape==M.shape==G.shape==(len(X),) and set(np.unique(Y))=={0,1}
assert np.array_equal(np.unique(G),np.arange(2965))
pair=group_query_simulation(G,M)
order=np.argsort(pair,kind='stable');starts=np.r_[0,np.flatnonzero(np.diff(pair[order]))+1];ends=np.r_[starts[1:],len(order)]
assert len(starts)==5930
Xt=np.empty_like(X)
for a,b in zip(starts,ends):
    ix=order[a:b];assert int(Y[ix].sum())==1
    Xt[ix]=transform_query_features(X[ix]);tick()

hash_identity=lambda salt,i:hashlib.sha256((salt+str(i)).encode()).digest()
folds=np.array([int.from_bytes(hash_identity('casmi-tie-neutral-fold-20261013:',i)[:8],'big')%2 for i in positive_ids],np.int64)
selection=sorted(range(2965),key=lambda g:hash_identity('casmi-tie-neutral-fit512-20261013:',positive_ids[g]))[:512]
selected=np.zeros(2965,bool);selected[selection]=True
fit_params=dict(max_depth=6,max_iter=128,learning_rate=.03,min_samples_leaf=80,l2_regularization=1.,early_stopping=False,random_state=0)
registration={'schema':'CASMI_HISTORICAL_ANONYMOUS_TIE_REFIT_REGISTRATION_V1','scope':'Historical anonymous candidate-ranking development only',
    'source_sha256':args.source_sha256,'feature_sha256':args.feature_sha256,'sidecar_sha256':args.sidecar_sha256,
    'input_sha256':digest(path),'features':list(FEATURES),'fit_params':fit_params,
    'queries':2965,'fit_roster_queries':512,'fit_roster_G':selection,'fold_for_G':folds.tolist(),
    'weights':{'class1':.30,'class2':.70},'fold_unit':'anonymous positive pool identity; both simulations together',
    'all_fit_heads_reused':False,'no_hyperparameter_search':True,'native_alias_disjoint':False,
    'FP_native_checkpoint_exclusion_qualified':False,'Full1_used':False,'modern_Morgan_MACCS_parity_qualified':False,
    'missing35_zero_extension':'aggregate historical-count arithmetic only; no ordered omission identity bridge',
    'caps':{'original_wall_seconds':WALL_CAP,'process_CPU_seconds':CPU_CAP,'peak_RSS_bytes':RSS_CAP,'math_threads':1,'child_processes':0,'fit_calls':4},
    'runtime':{'numpy':np.__version__,'sklearn':sklearn.__version__,'platform':sys.platform},'official_score':None}
reg_sha=write_json('PRIVATE_PRE_FIT_REGISTRATION.json',registration)
predictions=np.full((2,len(X)),np.nan,np.float64)
fits=[]
with threadpool_limits(limits=1):
    assert all(p['num_threads']==1 for p in threadpool_info())
    for fold in (0,1):
        tr=np.flatnonzero(selected[G] & (folds[G]!=fold));ev=np.flatnonzero(folds[G]==fold)
        train_queries=set(map(int,G[tr]));eval_queries=set(map(int,G[ev]))
        assert train_queries and eval_queries and not(train_queries&eval_queries)
        assert set(positive_ids[g] for g in train_queries).isdisjoint(positive_ids[g] for g in eval_queries)
        weight=np.where(M[tr]==0,.30,.70)
        for arm,matrix in enumerate((X,Xt)):
            tick();before=time.monotonic()
            estimator=HistGradientBoostingClassifier(**fit_params)
            estimator.fit(matrix[tr],Y[tr],sample_weight=weight)
            tick();predictions[arm,ev]=estimator.predict_proba(matrix[ev])[:,1]
            assert estimator.n_iter_==128
            fits.append({'fold':fold,'arm':'original' if arm==0 else 'tie_neutral','train_queries':len(train_queries),'train_rows':len(tr),'evaluation_queries':len(eval_queries),'evaluation_rows':len(ev),'iterations':int(estimator.n_iter_),'seconds':time.monotonic()-before})
            del estimator
            tick()
assert len(fits)==4 and np.isfinite(predictions).all()
# All OOF score bytes are sealed before evaluating any held-query label ranks.
with (args.output/'PRIVATE_OOF_PREDICTIONS.npz').open('xb') as f:
    np.savez(f,scores=predictions,G=G,M=M)
pred_sha=digest(args.output/'PRIVATE_OOF_PREDICTIONS.npz')
write_json('PRIVATE_PREDICTION_SEAL.json',{'prediction_sha256':pred_sha,'registration_sha256':reg_sha,'fit_calls':4,'OOF_scores_complete':True,'heldout_rank_metrics_not_yet_joined':True,'native_alias_qualification':False})
metrics=np.zeros((2,2965,2,3),np.float64) # arm,query,simulation -> RR,top1,top25
for a,b in zip(starts,ends):
    ix=order[a:b];g=int(G[ix[0]]);m=int(M[ix[0]])
    for arm in (0,1):
        ranking=np.argsort(-predictions[arm,ix],kind='stable')
        truth=int(np.flatnonzero(Y[ix[ranking]])[0])+1
        metrics[arm,g,m]=[1/truth if truth<=25 else 0.,int(truth==1),int(truth<=25)]
    tick()
rng=np.random.default_rng(20261013);summaries=[]
for m in (0,1):
    delta=metrics[1,:,m,0]-metrics[0,:,m,0]
    # Query bootstrap is explicitly not native-class bootstrap (bridge absent).
    boot=np.empty(5000)
    for a in range(0,5000,100):
        boot[a:a+100]=delta[rng.integers(0,2965,size=(100,2965))].mean(axis=1);tick()
    summaries.append({'simulation':m,'anonymous_observed_queries':2965,
        'arms':{name:{'conditional_MRR25':float(metrics[arm,:,m,0].mean()),'top1_count':int(metrics[arm,:,m,1].sum()),'top25_count':int(metrics[arm,:,m,2].sum()),'count_only_zero_extended_MRR3000':float(metrics[arm,:,m,0].sum()/3000)} for arm,name in enumerate(('original','tie_neutral'))},
        'paired_delta_conditional_MRR25':float(delta.mean()),'query_CI95':np.quantile(boot,[.025,.975]).tolist(),
        'native_class_CI_qualified':False,'wins':int((delta>0).sum()),'losses':int((delta<0).sum()),'ties':int((delta==0).sum())})
tick()
result={'schema':'CASMI_HISTORICAL_ANONYMOUS_TIE_REFIT_RESULT_V1','status':'PASS_COMPLETED_LOCAL_ANONYMOUS_BENCHMARK_ONLY',
    'registration_sha256':reg_sha,'prediction_sha256':pred_sha,'fits':fits,'summaries':summaries,
    'elapsed_before_receipt_seconds':time.monotonic()-START,'CPU_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
    'peak_RSS_bytes':rss_bytes(),'child_processes_created':0,'native_score':None,'official_score':None,'promotion_qualified':False,
    'limitations':['Two native alias pairs may cross anonymous folds; ordered class bridge absent.','13 odd query keys have checkpoint-even native aliases; actual FP checkpoint sampling unknown.','Historical feature/model-selection exposure; neither fresh end-to-end holdout nor modern2215 FP comparison.','Anonymous candidate MRR lacks native-class candidate deduplication.','Count-only35-failure zero extension is not an ordered physical full-panel join.']}
write_json('PRIVATE_LOCAL_BENCHMARK_RESULT.json',result)
tick()
print(json.dumps({'status':result['status'],'fit_calls':4,'output':str(args.output),'promotion_qualified':False,'official_score':None}),flush=True)
tick()
