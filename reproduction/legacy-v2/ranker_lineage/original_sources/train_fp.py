import numpy as np, torch, torch.nn as nn, torch.nn.functional as F, time, pickle, os, sys, math
import fpmodel

def get_device():
    if torch.cuda.is_available(): return 'cuda'
    if torch.backends.mps.is_available(): return 'mps'
    return 'cpu'

class SpecData:
    def __init__(self, dsdir='ds', fpdir='data', bit_lo=0.005, bit_hi=0.995):
        z = np.load(f'{dsdir}/spec.npz')
        self.off=z['off']; self.mz=z['mz']; self.it=z['it']
        self.prec=z['prec']; self.ad=z['ad'].astype(np.int64); self.ins=z['ins'].astype(np.int64)
        self.ce=z['ce']; self.mode=z['mode']; self.six=z['six']; self.is_val=z['is_val']
        packed = np.load(f'{fpdir}/struct_fp.npy')
        meta = pickle.load(open(f'{fpdir}/struct_fp_meta.pkl','rb'))
        FP = np.unpackbits(packed, axis=1)[:, :meta['nbits']]
        freq = FP.mean(0)
        self.bits = np.where((freq>=bit_lo)&(freq<=bit_hi))[0]
        self.FP = np.ascontiguousarray(FP[:, self.bits])
        self.keys = meta['keys']; self.smiles = meta['smiles']
        self.nbits = len(self.bits)
        self.tr = np.where(~self.is_val)[0]; self.va = np.where(self.is_val)[0]
        print(f'bits={self.nbits}  train={len(self.tr)}  val={len(self.va)}', flush=True)

    def batch(self, ids, maxlen=fpmodel.MAX_PEAKS, device='cpu'):
        B=len(ids)
        lens = np.minimum(self.off[ids+1]-self.off[ids], maxlen)
        N = max(int(lens.max()),1)
        mz=np.zeros((B,N),np.float32); it=np.zeros((B,N),np.float32); pad=np.ones((B,N),bool)
        for r,(i,l) in enumerate(zip(ids,lens)):
            a=self.off[i]
            mz[r,:l]=self.mz[a:a+l]; it[r,:l]=self.it[a:a+l]; pad[r,:l]=False
        y = self.FP[self.six[ids]].astype(np.float32)
        T=lambda x,d=None: torch.as_tensor(x, device=device) if d is None else torch.as_tensor(x,dtype=d,device=device)
        ce = np.where(self.ce[ids]<0, 25.0, self.ce[ids]).astype(np.float32)
        return (T(mz),T(it),T(pad),T(self.prec[ids]),T(self.ad[ids]),T(self.ins[ids]),T(ce),T(self.mode[ids])), T(y)

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--steps', type=int, default=60000)
    ap.add_argument('--bs', type=int, default=256)
    ap.add_argument('--lr', type=float, default=3e-4)
    ap.add_argument('--d', type=int, default=512)
    ap.add_argument('--layers', type=int, default=6)
    ap.add_argument('--out', default='fp_model.pt')
    ap.add_argument('--warm', type=int, default=2000)
    ap.add_argument('--val_every', type=int, default=4000)
    ap.add_argument('--max_minutes', type=float, default=1e9)
    ap.add_argument('--resume', default='')
    a=ap.parse_args()
    dev=get_device(); print('device',dev, flush=True)
    D=SpecData()
    model=fpmodel.FPNet(D.nbits, d=a.d, layers=a.layers).to(dev)
    print('params %.1fM'%(sum(p.numel() for p in model.parameters())/1e6), flush=True)
    opt=torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01, betas=(0.9,0.98))
    scaler = torch.amp.GradScaler('cuda') if dev=='cuda' else None
    start=0
    if a.resume and os.path.exists(a.resume):
        ck=torch.load(a.resume, map_location=dev); model.load_state_dict(ck['model']); opt.load_state_dict(ck['opt']); start=ck['step']
        print('resumed at', start, flush=True)
    def lr_at(s):
        if s<a.warm: return a.lr*s/max(1,a.warm)
        p=(s-a.warm)/max(1,a.steps-a.warm); return a.lr*(0.5*(1+math.cos(math.pi*min(p,1.0))))*0.98+a.lr*0.02
    rng=np.random.default_rng(1234)
    t0=time.time(); run=0.0; nrun=0
    for step in range(start, a.steps):
        for g in opt.param_groups: g['lr']=lr_at(step)
        ids=rng.choice(D.tr, size=a.bs, replace=False)
        (mz,it,pad,prec,ad,ins,ce,mode),y = D.batch(ids, device=dev)
        opt.zero_grad(set_to_none=True)
        if dev=='cuda':
            with torch.autocast('cuda', dtype=torch.bfloat16):
                lo=model(mz,it,pad,prec,ad,ins,ce,mode)
                loss=F.binary_cross_entropy_with_logits(lo.float(), y)
            loss.backward()
        else:
            lo=model(mz,it,pad,prec,ad,ins,ce,mode)
            loss=F.binary_cross_entropy_with_logits(lo,y); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        run+=loss.item(); nrun+=1
        if step%200==0:
            el=time.time()-t0
            print(f'step {step} loss {run/max(1,nrun):.4f} lr {lr_at(step):.2e} {el:.0f}s {(step-start+1)*a.bs/max(el,1):.0f} spec/s', flush=True)
            run=0; nrun=0
        if (step+1)%a.val_every==0 or step==a.steps-1:
            model.eval(); vs=[]
            with torch.no_grad():
                vids=rng.choice(D.va, size=min(4096,len(D.va)), replace=False)
                for s in range(0,len(vids),256):
                    (mz,it,pad,prec,ad,ins,ce,mode),y = D.batch(vids[s:s+256], device=dev)
                    lo=model(mz,it,pad,prec,ad,ins,ce,mode)
                    vs.append(F.binary_cross_entropy_with_logits(lo.float(),y).item())
            print(f'  VAL step {step} bce {np.mean(vs):.4f}', flush=True)
            model.train()
            torch.save({'model':model.state_dict(),'opt':opt.state_dict(),'step':step+1,
                        'bits':D.bits,'nbits':D.nbits,'d':a.d,'layers':a.layers}, a.out)
        if (time.time()-t0)/60 > a.max_minutes:
            print('time budget reached', flush=True)
            torch.save({'model':model.state_dict(),'opt':opt.state_dict(),'step':step+1,
                        'bits':D.bits,'nbits':D.nbits,'d':a.d,'layers':a.layers}, a.out); break
    print('done', flush=True)

if __name__=='__main__': main()
