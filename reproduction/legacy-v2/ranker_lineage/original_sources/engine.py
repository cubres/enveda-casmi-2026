import numpy as np, numba, pickle, time
from numba import njit, prange

@njit(cache=True, fastmath=True)
def _prep(mz, it, floor, topk, out_mz, out_it):
    n = len(mz)
    if n == 0: return 0
    mx = 0.0
    for i in range(n):
        if it[i] > mx: mx = it[i]
    thr = floor * mx
    # collect indices above floor
    cnt = 0
    for i in range(n):
        if it[i] >= thr: cnt += 1
    idx = np.empty(cnt, np.int64); c=0
    for i in range(n):
        if it[i] >= thr: idx[c]=i; c+=1
    if cnt > topk:
        vals = np.empty(cnt, np.float32)
        for i in range(cnt): vals[i] = it[idx[i]]
        order = np.argsort(vals)[cnt-topk:]
        keep = np.empty(topk, np.int64)
        for i in range(topk): keep[i] = idx[order[i]]
        keep.sort()
        idx = keep; cnt = topk
    ssq = 0.0
    for i in range(cnt):
        v = np.sqrt(it[idx[i]])
        out_mz[i] = mz[idx[i]]; out_it[i] = v
        ssq += v*v
    if ssq > 0:
        nrm = np.sqrt(ssq)
        for i in range(cnt): out_it[i] /= nrm
    return cnt

@njit(cache=True, fastmath=True)
def prep_spectrum(mz, it, floor=0.002, topk=256):
    o_mz = np.empty(len(mz), np.float32); o_it = np.empty(len(mz), np.float32)
    n = _prep(mz, it, floor, topk, o_mz, o_it)
    return o_mz[:n].copy(), o_it[:n].copy()

@njit(cache=True, fastmath=True)
def cosine_greedy(qmz, qit, cmz, cit, tol):
    """Greedy one-to-one matching cosine (peaks assumed sorted by m/z)."""
    i=0; j=0; n=len(qmz); m=len(cmz); dot=0.0
    while i<n and j<m:
        d = qmz[i]-cmz[j]
        if d < -tol: i+=1
        elif d > tol: j+=1
        else:
            dot += qit[i]*cit[j]; i+=1; j+=1
    return dot

@njit(cache=True, fastmath=True)
def modcos(qmz, qit, cmz, cit, tol, shift):
    """Modified cosine: best of direct and neutral-loss-shifted alignment, union-greedy."""
    direct = cosine_greedy(qmz, qit, cmz, cit, tol)
    if shift < 0.001 and shift > -0.001:
        return direct
    # shifted
    i=0; j=0; n=len(qmz); m=len(cmz); dot=0.0
    while i<n and j<m:
        d = (qmz[i]-shift)-cmz[j]
        if d < -tol: i+=1
        elif d > tol: j+=1
        else:
            dot += qit[i]*cit[j]; i+=1; j+=1
    return direct if direct > dot else dot

@njit(cache=True, fastmath=True, parallel=True)
def search_window(qmz, qit, cand, off, allmz, allin, tol, floor, topk, prec_shift):
    """Score query against library spectra listed in `cand`. Returns array of scores."""
    out = np.zeros(len(cand), np.float32)
    for k in prange(len(cand)):
        c = cand[k]
        a = off[c]; b = off[c+1]
        if b <= a: continue
        cm, ci = prep_spectrum(allmz[a:b], allin[a:b], floor, topk)
        if len(cm) == 0: continue
        out[k] = modcos(qmz, qit, cm, ci, tol, prec_shift[k])
    return out
