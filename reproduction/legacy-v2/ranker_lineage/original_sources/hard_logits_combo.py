"""Model channel for the 569 obscure molecules: m1 on MERGED input + s2 per-spectrum, averaged.
   Each model is fed the input distribution it was trained on (0.4904 vs 0.4799/0.4896 alone)."""
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
sc_m1=score_model.Scorer('fp_model_m1.pt'); sc_s2=score_model.Scorer('fp_model_s2.pt')

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
    specs=[dict(mz=mz,it=it,prec=float(L.precursor_mz[i]),adduct=L.adduct[i],
                instrument=L.instrument_type[i],ce=float(CE[i]),
                mode=1.0 if L.ionization_mode[i]=='positive' else -1.0)
           for (mz,it),i in zip(pairs,qidx)]
    z_s2 = sc_s2.logits(specs)
    mz,it = merge_peaks(pairs)
    z_m1 = sc_m1.logits([dict(mz=mz,it=it,prec=float(np.median([s['prec'] for s in specs])),
                              adduct=specs[0]['adduct'], instrument=specs[0]['instrument'],
                              ce=float(np.mean([s['ce'] for s in specs])),
                              mode=float(np.mean([s['mode'] for s in specs])))])
    out.append((z_m1+z_s2)/2.0)
    if n%150==0: print(' ',n,len(rows),'%.0fs'%(time.time()-t0), flush=True)
np.save('data/hard_model_logits.npy', np.stack(out))
print('saved', len(out), flush=True)
