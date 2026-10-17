import numpy as np, torch, torch.nn as nn, torch.nn.functional as F, time, pickle, os, math, argparse
import fpmodel

class Data:

    def __init__(self, spec='ds/spec.npz', fpdir='up_train', pooldir='.', device='cpu', pool_on_gpu=True):
        z = np.load(spec)
        self.off = z['off']
        self.mz = z['mz']
        self.it = z['it']
        self.prec = z['prec']
        self.ad = z['ad'].astype(np.int64)
        self.ins = z['ins'].astype(np.int64)
        self.ce = z['ce']
        self.mode = z['mode']
        self.six = z['six']
        self.is_val = z['is_val']
        m = pickle.load(open(f'{fpdir}/fp_meta.pkl', 'rb'))
        self.nbits = m['nbits']
        self.skeys = m['keys']
        pm = pickle.load(open(f'{pooldir}/pool_meta.pkl', 'rb'))
        self.pmass = np.load(f'{pooldir}/pool_mass.npy')
        PFP = np.unpackbits(np.load(f'{pooldir}/pool_fp.npy'), axis=1)[:, :self.nbits]
        self.pkeys = pm['keys']
        k2p = {k: i for i, k in enumerate(self.pkeys)}
        self.s2p = np.array([k2p.get(k, -1) for k in self.skeys], dtype=np.int64)
        self.device = device
        if pool_on_gpu and device == 'cuda':
            self.PFP = torch.from_numpy(np.ascontiguousarray(PFP)).to(device)
        else:
            self.PFP = torch.from_numpy(np.ascontiguousarray(PFP))
        order = np.argsort(self.six, kind='mergesort')
        s_sorted = self.six[order]
        bounds = np.searchsorted(s_sorted, np.arange(s_sorted.max() + 2))
        self._grp_order = order
        self._grp_bounds = bounds
        self.tr = np.where(~self.is_val)[0]
        self.va = np.where(self.is_val)[0]
        keep = self.s2p[self.six[self.tr]] >= 0
        self.tr = self.tr[keep]
        print(f'nbits={self.nbits} pool={len(self.pmass)} train={len(self.tr)} val={len(self.va)}', flush=True)

    def sample_negs(self, pos_pidx, K, ppm=10.0, rng=None):
        m = self.pmass[pos_pidx]
        tol = m * ppm / 1000000.0
        lo = np.searchsorted(self.pmass, m - tol, 'left')
        hi = np.searchsorted(self.pmass, m + tol, 'right')
        out = np.empty((len(pos_pidx), K), dtype=np.int64)
        for r, (a, b, p) in enumerate(zip(lo, hi, pos_pidx)):
            n = b - a
            if n <= 1:
                out[r] = rng.integers(0, len(self.pmass), K)
            else:
                c = rng.integers(a, b, K)
                bad = c == p
                if bad.any():
                    c[bad] = np.where(c[bad] + 1 < b, c[bad] + 1, a)
                out[r] = c
        return out

    def peers(self, i, rng, kmax=4):
        """Other spectra of the same structure (for merge augmentation)."""
        s = self.six[i]
        a, b = (self._grp_bounds[s], self._grp_bounds[s + 1])
        if b - a <= 1:
            return [i]
        cand = self._grp_order[a:b]
        k = int(rng.integers(2, min(kmax, b - a) + 1))
        pick = rng.choice(cand, size=min(k, len(cand)), replace=False)
        if i not in pick:
            pick = np.concatenate([[i], pick[:-1]])
        return list(pick)

    def _merged(self, idxs, maxlen):
        mzs = []
        its = []
        for j in idxs:
            a, b = (self.off[j], min(self.off[j] + maxlen, self.off[j + 1]))
            mzs.append(self.mz[a:b])
            its.append(self.it[a:b])
        mz = np.concatenate(mzs)
        it = np.concatenate(its)
        o = np.argsort(mz)
        mz, it = (mz[o], it[o])
        keep = np.ones(len(mz), bool)
        for j in range(1, len(mz)):
            if mz[j] - mz[j - 1] < 0.005:
                if it[j] >= it[j - 1]:
                    keep[j - 1] = False
                else:
                    keep[j] = False
        mz, it = (mz[keep], it[keep])
        if len(mz) > maxlen:
            top = np.argsort(-it)[:maxlen]
            top.sort()
            mz, it = (mz[top], it[top])
        return (mz, it)

    def batch(self, ids, K=0, rng=None, ppm=10.0, aug=False, merge_p=0.0):
        B = len(ids)
        L = fpmodel.MAX_PEAKS
        lens = np.minimum(self.off[ids + 1] - self.off[ids], L)
        N = max(int(lens.max()), 1)
        mz = np.zeros((B, N), np.float32)
        it = np.zeros((B, N), np.float32)
        pad = np.ones((B, N), bool)
        for r, (i, l) in enumerate(zip(ids, lens)):
            a = self.off[i]
            mz[r, :l] = self.mz[a:a + l]
            it[r, :l] = self.it[a:a + l]
            pad[r, :l] = False
        if merge_p > 0 and rng is not None:
            for r, i in enumerate(ids):
                if rng.random() >= merge_p:
                    continue
                pk = self.peers(i, rng)
                if len(pk) < 2:
                    continue
                m2, i2 = self._merged(pk, N)
                n2 = len(m2)
                mz[r, :] = 0
                it[r, :] = 0
                pad[r, :] = True
                mz[r, :n2] = m2
                it[r, :n2] = i2
                pad[r, :n2] = False
        if aug and rng is not None:
            keep = rng.random((B, N)) > rng.uniform(0.0, 0.3, size=(B, 1))
            pad = pad | ~keep
            it = it * np.exp(rng.normal(0.0, 0.25, size=(B, N))).astype(np.float32)
            mz = mz * (1.0 + rng.normal(0.0, 5e-06, size=(B, N))).astype(np.float32)
            allpad = pad.all(1)
            if allpad.any():
                pad[allpad, 0] = False
        d = self.device
        T = lambda x: torch.as_tensor(x, device=d)
        ce = np.where(self.ce[ids] < 0, 25.0, self.ce[ids]).astype(np.float32)
        inp = (T(mz), T(it), T(pad), T(self.prec[ids]), T(self.ad[ids]), T(self.ins[ids]), T(ce), T(self.mode[ids]))
        pos = self.s2p[self.six[ids]]
        cand = None
        if K > 0:
            negs = self.sample_negs(pos, K, ppm, rng)
            cand = np.concatenate([pos[:, None], negs], 1)
            cand = torch.as_tensor(cand, device=self.PFP.device)
        ypos = self.PFP[torch.as_tensor(pos, device=self.PFP.device)].to(d).float()
        return (inp, ypos, cand)
