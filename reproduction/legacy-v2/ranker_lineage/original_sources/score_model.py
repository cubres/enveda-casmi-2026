"""Score candidates with the trained spectrum->fingerprint model: rank = fp_candidate . logits."""
import numpy as np, torch, pickle, fpmodel

class Scorer:
    def __init__(self, ckpt, device=None):
        self.dev = device or ('cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu')
        ck = torch.load(ckpt, map_location='cpu', weights_only=False)
        self.net = fpmodel.FPNet(ck['nbits'], d=ck['d'], layers=ck['layers']).to(self.dev).eval()
        self.net.load_state_dict(ck['model'])
        self.nbits = ck['nbits']; self.step = ck.get('step')
    @torch.no_grad()
    def logits(self, specs):
        """specs: list of dicts with mz, it, prec, adduct, instrument, ce, mode.
           Returns the fused logit vector (mean over the molecule's spectra)."""
        B=len(specs)
        if B==0: return np.zeros(self.nbits, np.float32)
        P=[fpmodel.prep_peaks(s['mz'], s['it'], s['prec']) for s in specs]
        N=max(max(len(a) for a,_ in P),1)
        mz=np.zeros((B,N),np.float32); it=np.zeros((B,N),np.float32); pad=np.ones((B,N),bool)
        for r,(a,b) in enumerate(P):
            mz[r,:len(a)]=a; it[r,:len(b)]=b; pad[r,:len(a)]=False
        T=lambda x: torch.as_tensor(x, device=self.dev)
        z=self.net(T(mz),T(it),T(pad),
                   T(np.array([s['prec'] for s in specs],np.float32)),
                   T(np.array([fpmodel.ADDUCT_IX.get(s['adduct'], fpmodel.ADDUCT_IX['<unk>']) for s in specs])),
                   T(np.array([fpmodel.instr_family(s.get('instrument')) for s in specs])),
                   T(np.array([s.get('ce',25.0) if s.get('ce',-1)>=0 else 25.0 for s in specs],np.float32)),
                   T(np.array([s.get('mode',1.0) for s in specs],np.float32)))
        return z.float().mean(0).cpu().numpy()

def candidate_scores(logits, cand_fp):
    """f . z  == exact Bayes log-likelihood up to a candidate-independent constant."""
    f = cand_fp.astype(np.float32)
    raw = f @ logits
    nb  = f.sum(1)
    return raw, nb
