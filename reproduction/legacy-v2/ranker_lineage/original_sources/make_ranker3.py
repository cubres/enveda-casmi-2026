"""Ranker trained on BOTH validation sets (250 common NPs + 569 obscure structures),
   optionally with the spectrum->fingerprint model channel. Selects W1 against the
   leaderboard-calibrated objective ExpectedLB = 0.162*c1 + 0.20*c2."""
import numpy as np, pickle, os, sys, time, casmi_core as cc, rankfeat
from sklearn.ensemble import HistGradientBoostingClassifier
# Recalibrated against three scored submissions. The latest (0.266, with the fragmentation
# channel) implies B = (0.266 - 0.162*0.867)/0.539 = 0.233.
# Recalibrated on v7 (0.299, 4 channels): B = (0.299 - 0.162*0.8218)/0.6116 = 0.271
A_LB, B_LB = 0.162, 0.271
pool = cc.Pool('.')
USE_MODEL = '--model' in sys.argv

# ---- dataset A: 250 common natural products -------------------------------------
recsA = pickle.load(open('data/c2_np_recs2.pkl','rb'))
FA = {'c1': pickle.load(open('data/feat2_c1.pkl','rb')), 'c2': pickle.load(open('data/feat_c2.pkl','rb'))}
FSA = pickle.load(open('data/c2_fragscores.pkl','rb'))
def _ens(paths):
    import numpy as _np
    arrs=[_np.load(p) for p in paths if os.path.exists(p)]
    return _np.mean(arrs,axis=0) if arrs else None
# s2 alone beats every logit-average ensemble (0.480 vs 0.474/0.478) -- averaging logits
# across models breaks the f.z scale that makes the Bayes score work.
LOGA = _ens(['data/val_model_logits_combo.npy']) if USE_MODEL else None
# ---- dataset B: 569 obscure held-out structures ---------------------------------
H = pickle.load(open('data/hard_feats.pkl','rb'))
recsB = H['meta']; FSB = H['frag']
LOGB = _ens(['data/hard_model_logits.npy']) if USE_MODEL else None

def build(recs, feats, frags, logits, mode):
    Xs=[];Ys=[];Gs=[]
    for i,r in enumerate(recs):
        ls,an = feats[mode][i] if isinstance(feats, dict) else feats[mode][i]
        cand=r['cand']; cfp=pool.fps(cand)
        lv=np.array([ls.get(pool.keys[c],0.0) for c in cand],np.float32)
        ids=[];sims=[]
        for k,s in an[:rankfeat.N_ANALOG]:
            j=pool.k2i.get(k,-1)
            if j>=0: ids.append(j); sims.append(s)
        afp=pool.fps(np.array(ids)) if ids else None
        X=rankfeat.rank_features(cfp,lv,afp,np.array(sims,np.float32),
                                 logits[i] if logits is not None else None, frags[i])
        y=np.zeros(len(cand))
        if r['truth']>=0: y[r['truth']]=1
        Xs.append(X); Ys.append(y); Gs.append(np.full(len(cand),i))
    return np.vstack(Xs), np.concatenate(Ys), np.concatenate(Gs)

FB = {'c1': H['c1'], 'c2': H['c2']}
A1=build(recsA,FA,FSA,LOGA,'c1'); A2=build(recsA,FA,FSA,LOGA,'c2')
B1=build(recsB,FB,FSB,LOGB,'c1'); B2=build(recsB,FB,FSB,LOGB,'c2')
print('rows: A %d/%d  B %d/%d  (model=%s)'%(len(A1[1]),len(A2[1]),len(B1[1]),len(B2[1]),USE_MODEL), flush=True)

nA, nB = len(recsA), len(recsB)
foldsA = np.arange(nA)%5; foldsB = np.arange(nB)%5

def cv(w1):
    c1=[];c2=[]
    for f in range(5):
        Xs=[];Ys=[];Ws=[]
        for (X,Y,G),folds,w in [(A1,foldsA,w1),(A2,foldsA,1-w1),(B1,foldsB,w1),(B2,foldsB,1-w1)]:
            tr = folds[G.astype(int)]!=f
            Xs.append(X[tr]); Ys.append(Y[tr]); Ws.append(np.full(int(tr.sum()),w))
        m=HistGradientBoostingClassifier(max_depth=6,max_iter=500,learning_rate=0.03,
                                         min_samples_leaf=80,l2_regularization=1.0)
        m.fit(np.vstack(Xs),np.concatenate(Ys),sample_weight=np.concatenate(Ws))
        # EVALUATE only on dataset A (250 timsTOF natural products) -- that is the set whose
        # domain matches the hidden test, so the LB-calibrated objective stays valid.
        # Dataset B still contributes 3x more TRAINING rows.
        for (X,Y,G),folds,recs,acc in [(A1,foldsA,recsA,c1),(A2,foldsA,recsA,c2)]:
            for i,r in enumerate(recs):
                if folds[i]!=f: continue
                sel=G==i
                if not sel.any(): continue
                s=m.predict_proba(X[sel])[:,1]
                o=np.argsort(-s)[:25]; q=np.where(o==r['truth'])[0]
                acc.append(1.0/(q[0]+1) if len(q) else 0.0)
    return float(np.mean(c1)), float(np.mean(c2))

print('%6s %8s %8s %10s'%('W1','c1','c2','predLB'))
best=None
for w1 in [0.42,0.50]:
    a,b=cv(w1); pred=A_LB*a+B_LB*b
    print('%6.2f %8.4f %8.4f %10.4f'%(w1,a,b,pred), flush=True)
    if best is None or pred>best[0]: best=(pred,w1,a,b)
print('\nBEST W1=%.2f predLB=%.4f (c1=%.4f c2=%.4f)'%(best[1],best[0],best[2],best[3]))

w1=best[1]
X=np.vstack([A1[0],A2[0],B1[0],B2[0]]); Y=np.concatenate([A1[1],A2[1],B1[1],B2[1]])
M=np.concatenate([np.zeros(len(A1[1])),np.ones(len(A2[1])),np.zeros(len(B1[1])),np.ones(len(B2[1]))])
G=np.concatenate([A1[2],A2[2],B1[2]+nA,B2[2]+nA])
out='up_rank3'; os.makedirs(out,exist_ok=True)
np.savez_compressed(f'{out}/rank_train.npz', X=X, Y=Y, M=M, G=G)
pickle.dump({'w1':w1}, open('data/w1_v3.pkl','wb'))
print('saved', X.shape, 'W1=%.2f'%w1)
