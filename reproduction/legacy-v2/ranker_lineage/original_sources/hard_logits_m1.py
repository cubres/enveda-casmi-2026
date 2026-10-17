"""Model channel for the 569 obscure molecules: m1 (50k-step merge-trained) on MERGED input.
   m1 alone (0.5173) beats every combination that includes s2 (0.5112)."""
import numpy as np, pickle, time, libsearch, score_model, pyarrow.parquet as pq
from collections import defaultdict
L=libsearch.Lib(); AMZ=np.ascontiguousarray(L.mz); AIN=np.ascontiguousarray(L.it)
H=pickle.load(open('data/hard_feats.pkl','rb')); rows=H['meta']
ce_ev=pq.read_table('data/train.parquet', columns=['collision_energy_ev']).to_pandas().collision_energy_ev.values
CE=np.array([float(np.mean(v)) if v is not None and len(v)>0 else -1.0 for v in ce_ev], np.float32)
keyset={r['key'] for r in rows}
bykey=defaultdict(list)
for i,k in enumerate(L.inchikey14):
    if k in keyset: bykey[k].append(i)
sc=score_model.Scorer('fp_model_m1.pt')
def merge_peaks(pairs):
    mz=np.concatenate([np.asarray(m,np.float64) for m,_ in pairs])
    it=np.concatenate([np.asarray(i,np.float64)/max(np.asarray(i,np.float64).max(),1e-9) for _,i in pairs])
    o=np.argsort(mz); mz,it=mz[o],it[o]
    keep=np.ones(len(mz),bool)
    for j in range(1,len(mz)):
        if mz[j]-mz[j-1]<0.005:
            if it[j]>=it[j-1]: keep[j-1]=False
            else: keep[j]=False
    return mz[keep], it[keep]
out=[]; t0=time.time()
for n,r in enumerate(rows):
    idxs=bykey[r['key']]; qlib=L.ingest_lib[idxs[0]]
    qidx=[i for i in idxs if L.ingest_lib[i]==qlib][:5]
    pairs=[(AMZ[L.off[i]:L.off[i+1]], AIN[L.off[i]:L.off[i+1]]) for i in qidx]
    mz,it=merge_peaks(pairs)
    out.append(sc.logits([dict(mz=mz,it=it,prec=float(np.median([L.precursor_mz[i] for i in qidx])),
        adduct=L.adduct[qidx[0]], instrument=L.instrument_type[qidx[0]],
        ce=float(np.mean([CE[i] for i in qidx])),
        mode=float(np.mean([1.0 if L.ionization_mode[i]=='positive' else -1.0 for i in qidx])))]))
    if n%200==0: print(' ',n,len(rows),'%.0fs'%(time.time()-t0), flush=True)
np.save('data/hard_model_logits.npy', np.stack(out)); print('saved', len(out), flush=True)
