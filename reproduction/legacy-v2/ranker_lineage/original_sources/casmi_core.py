"""Shared retrieval core: Class-1 library search + Class-2 pool retrieval + blending."""
import numpy as np, pickle, math
import engine, speclib

MZTOL=0.01; FLOOR=0.002; TOPK=256

# ---------- spectral similarity ----------
def prep(mz, it):
    return engine.prep_spectrum(np.asarray(mz,np.float32), np.asarray(it,np.float32), FLOOR, TOPK)

def lib_scores(L, AMZ, AIN, spectra, nm_target, ppm=10.0, exclude=None, mztol=MZTOL, analog_da=0.0):
    """spectra: list of (mz, it). Returns dict ik14 -> best similarity, over a ppm mass window."""
    tol = nm_target*ppm/1e6
    cand = L.window(nm_target, tol)
    if exclude is not None and len(cand): cand = cand[~exclude[cand]]
    if len(cand)==0: return {}, np.array([],dtype=np.int64)
    shift = np.zeros(len(cand), np.float32)
    agg = {}
    for mz,it in spectra:
        q,qi = prep(mz,it)
        if len(q)==0: continue
        sc = engine.search_window(q,qi,cand,L.off,AMZ,AIN,mztol,FLOOR,TOPK,shift)
        for c,s in zip(cand,sc):
            k=L.inchikey14[c]
            if s>agg.get(k,-1.0): agg[k]=float(s)
    return agg, cand

def analog_scores(L, AMZ, AIN, spectra, prec_mz, nm_target, window=200.0, max_cand=60000, mztol=0.01):
    """Modified-cosine analog search over a WIDE neutral-mass window (finds related scaffolds)."""
    lo = np.searchsorted(L.snm[:L.n_ok], nm_target-window, 'left')
    hi = np.searchsorted(L.snm[:L.n_ok], nm_target+window, 'right')
    cand = L.order[lo:hi]
    if len(cand)>max_cand:
        cand = cand[np.random.default_rng(0).choice(len(cand), max_cand, replace=False)]
    if len(cand)==0: return {}
    shift = (nm_target - L.nm[cand]).astype(np.float32)
    agg={}
    for mz,it in spectra:
        q,qi=prep(mz,it)
        if len(q)==0: continue
        sc = engine.search_window(q,qi,cand,L.off,AMZ,AIN,mztol,FLOOR,TOPK,shift)
        for c,s in zip(cand,sc):
            k=L.inchikey14[c]
            if s>agg.get(k,-1.0): agg[k]=float(s)
    return agg

# ---------- candidate pool ----------
class Pool:
    def __init__(self, d='.', nbits=None):
        self.mass = np.load(f'{d}/pool_mass.npy')
        m = pickle.load(open(f'{d}/pool_meta.pkl','rb'))
        self.keys=m['keys']; self.smiles=m['smiles']; self.src=m['src']; self.npl=m['npl']
        self.nbits=m['nbits']
        self._packed = np.load(f'{d}/pool_fp.npy', mmap_mode='r')
        self.k2i = {k:i for i,k in enumerate(self.keys)}
    def window(self, target, ppm=10.0, lo_ppm=None, hi_ppm=None):
        lo = target*(1 - (lo_ppm if lo_ppm is not None else ppm)/1e6)
        hi = target*(1 + (hi_ppm if hi_ppm is not None else ppm)/1e6)
        a=np.searchsorted(self.mass, lo,'left'); b=np.searchsorted(self.mass, hi,'right')
        return np.arange(a,b)
    def fps(self, idx):
        return np.unpackbits(np.asarray(self._packed[idx]), axis=1)[:, :self.nbits]

def mrr_at(ranked_keys, truth, n=25):
    for r,k in enumerate(ranked_keys[:n],1):
        if k==truth: return 1.0/r
    return 0.0
