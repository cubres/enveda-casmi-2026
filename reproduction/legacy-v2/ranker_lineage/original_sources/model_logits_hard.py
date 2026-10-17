"""Model logits for the 569 obscure held-out molecules (same query-spectrum selection as
   gen_feats_hard.py, so rows line up with hard_feats.pkl)."""
import numpy as np, pickle, time, sys, libsearch, score_model, pyarrow.parquet as pq
from collections import defaultdict
L=libsearch.Lib(); AMZ=np.ascontiguousarray(L.mz); AIN=np.ascontiguousarray(L.it)
H=pickle.load(open('data/hard_feats.pkl','rb')); rows=H['meta']
ce_ev=pq.read_table('data/train.parquet', columns=['collision_energy_ev']).to_pandas().collision_energy_ev.values
CE=np.array([float(np.mean(v)) if v is not None and len(v)>0 else -1.0 for v in ce_ev], np.float32)
keyset={r['key'] for r in rows}
bykey=defaultdict(list)
for i,k in enumerate(L.inchikey14):
    if k in keyset: bykey[k].append(i)
CKPTS = sys.argv[1:] or ['fp_model.pt','fp_model_aug.pt']
SCS=[score_model.Scorer(c) for c in CKPTS]
print('models:', [(c, s.step) for c,s in zip(CKPTS,SCS)], flush=True)
out=[]; t0=time.time()
for n,r in enumerate(rows):
    idxs=bykey[r['key']]; qlib=L.ingest_lib[idxs[0]]
    qidx=[i for i in idxs if L.ingest_lib[i]==qlib][:5]
    specs=[dict(mz=AMZ[L.off[i]:L.off[i+1]], it=AIN[L.off[i]:L.off[i+1]],
                prec=float(L.precursor_mz[i]), adduct=L.adduct[i],
                instrument=L.instrument_type[i], ce=float(CE[i]),
                mode=1.0 if L.ionization_mode[i]=='positive' else -1.0) for i in qidx]
    out.append(np.mean([s.logits(specs) for s in SCS], axis=0))
    if n%100==0: print(' ',n,len(rows),'%.0fs'%(time.time()-t0), flush=True)
np.save('data/hard_model_logits.npy', np.stack(out))
print('saved', len(out), flush=True)
