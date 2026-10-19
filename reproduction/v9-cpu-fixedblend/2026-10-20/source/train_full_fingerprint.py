"""Optimizer-only full-bank training with packed candidate targets and fixed validation.

The spectrum encoder and augmentation come from this account's original FP code.
The input bank, role audit, packed lookup, seed order and checkpoint protocol are
explicit here. Public competitor code is not used.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import pickle
import time
import zlib
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F
from train_fp4 import Data as OriginalSpectrumData
from fpmodel import FPNet
from structure_uniform_sampler import StructureUniformSampler

ROLE_SHA='4d7b366293225a1ae67dfc0306480129b9ac1351a6d8581f0be40a269bdaff86'
BASELINE_SOURCE_SHA='d844db07e729768ff1f47a3651dd7861295f0eaceda801f9714c9105bc2e53c0'
FIXED_VALIDATION_SHA={
    'checkpoint_spectrum_ids.npy':'b16cc570c4db9716cfe4cb8a19efb73185b5f663c136d3ed75e2c2c13cc9112a',
    'checkpoint_decoy_indices.npy':'2714697b0d21c956b883e5d4860bd67cae4d7b5a2f2a689edd198321ba3647ea',
}

class PackedFingerprints:
    def __init__(self, packed, nbits, device):
        self.values=torch.as_tensor(packed,device=device)
        self.nbits=int(nbits)
        self.device=self.values.device
        self.shifts=torch.arange(7,-1,-1,device=device,dtype=torch.uint8)

    def __getitem__(self, indices):
        selected=self.values[indices]
        bits=(selected.unsqueeze(-1).bitwise_right_shift(self.shifts)&1)
        return bits.flatten(-2)[...,:self.nbits]

class FullData(OriginalSpectrumData):
    def __init__(self, folder, device, spectra_path=None):
        folder=Path(folder);z=np.load(spectra_path if spectra_path is not None else folder/'spec.npz')
        for name in ('off','mz','it','prec','ad','ins','ce','mode','six'):
            setattr(self,name,z[name])
        self.ad=self.ad.astype(np.int64);self.ins=self.ins.astype(np.int64)
        meta=pickle.load((folder/'fp_meta.pkl').open('rb'))
        pool=pickle.load((folder/'pool_meta.pkl').open('rb'))
        self.nbits=int(meta['nbits']);self.skeys=meta['keys'];self.pkeys=pool['keys']
        assert self.nbits==10395 and pool['nbits']==self.nbits
        self.pmass=np.load(folder/'pool_mass.npy')
        assert np.isfinite(self.pmass).all() and np.all(self.pmass[1:]>=self.pmass[:-1])
        index={key:i for i,key in enumerate(self.pkeys)}
        self.s2p=np.array([index.get(key,-1) for key in self.skeys],np.int64)
        self.device=device
        packed=np.load(folder/'pool_fp.npy')
        assert packed.dtype==np.uint8 and packed.shape==(len(self.pkeys),(self.nbits+7)//8)
        self.PFP=PackedFingerprints(packed,self.nbits,device)
        encoded=(folder/'roles_by_structure.b64').read_text().strip()
        raw=np.frombuffer(zlib.decompress(base64.b64decode(encoded)),np.uint8)
        b=np.unpackbits(raw)[:2*len(self.skeys)].reshape(-1,2)
        roles=(2*b[:,0]+b[:,1]).astype(np.uint8)
        assert hashlib.sha256(roles.tobytes()).hexdigest()==ROLE_SHA
        valid=self.s2p[self.six]>=0
        self.tr=np.flatnonzero((roles[self.six]==0)&valid)
        self.va=np.flatnonzero((roles[self.six]==1)&(self.six%2==0)&valid)
        self.roles=roles
        order=np.argsort(self.six,kind='stable')
        self._grp_order=order
        self._grp_bounds=np.searchsorted(self.six[order],np.arange(len(self.skeys)+1))
        assert len(self.tr)>0 and len(self.va)>0
        self.receipt=dict(nbits=self.nbits,pool_rows=len(self.pkeys),optimizer_spectra=len(self.tr),
            checkpoint_even_spectra=len(self.va),optimizer_structures=len(np.unique(self.six[self.tr])),
            checkpoint_even_structures=len(np.unique(self.six[self.va])),
            role_table_sha256=ROLE_SHA,role_index='trainer fp_meta order',
            candidate_storage='MSB-first packed uint8; decode only the selected batch',
            merge_conditions='same structure, adduct, ionization mode and instrument family',
            merged_collision_energy='mean finite nonnegative energy of the selected peers; 25 eV if unavailable')
        self.optimizer_sampler=StructureUniformSampler(self.tr,self.six,self.roles,self.s2p)

    def peers(self, i, rng, kmax=4):
        structure=self.six[i]
        a,b=self._grp_bounds[structure:structure+2]
        candidates=self._grp_order[a:b]
        good=(self.ad[candidates]==self.ad[i])&(self.ins[candidates]==self.ins[i])&(self.mode[candidates]==self.mode[i])
        candidates=candidates[good]
        if len(candidates)<2:return [i]
        count=int(rng.integers(2,min(kmax,len(candidates))+1))
        chosen=rng.choice(candidates,size=count,replace=False)
        if i not in chosen:chosen=np.concatenate([[i],chosen[:-1]])
        energies=np.asarray(self.ce[chosen],float)
        energies=energies[np.isfinite(energies)&(energies>=0)]
        self._merged_ce[int(i)]=float(energies.mean()) if len(energies) else 25.
        assert np.all(self.ad[chosen]==self.ad[i]) and np.all(self.ins[chosen]==self.ins[i]) and np.all(self.mode[chosen]==self.mode[i])
        return list(chosen)

    def batch(self, ids, **kwargs):
        self._merged_ce={}
        inputs,truth,candidates=super().batch(ids,**kwargs)
        if self._merged_ce:
            energies=inputs[6].clone()
            for row,i in enumerate(ids):
                if int(i) in self._merged_ce:energies[row]=self._merged_ce[int(i)]
            inputs=(*inputs[:6],energies,inputs[7])
        return inputs,truth,candidates

def scores(model, data, ids, rng, negatives, augment=False, merge_probability=0., fixed_negatives=None):
    inp,truth,candidates=data.batch(ids,K=negatives if fixed_negatives is None else 0,rng=rng,aug=augment,merge_p=merge_probability)
    if fixed_negatives is not None:
        positive=data.s2p[data.six[ids]]
        candidates=torch.as_tensor(np.column_stack([positive,fixed_negatives]),device=data.PFP.device)
    with torch.autocast('cuda',dtype=torch.float16):
        logits=model(*inp)
    logits=logits.float()
    bce=F.binary_cross_entropy_with_logits(logits,truth)
    fingerprints=data.PFP[candidates].float()
    raw=torch.bmm(fingerprints,logits.unsqueeze(-1)).squeeze(-1)
    rank_logits=(raw-raw.mean(dim=1,keepdim=True))/math.sqrt(data.nbits)
    return bce,rank_logits

def lookup_contract(device):
    rng=np.random.default_rng(20261003)
    raw=rng.integers(0,2,size=(47,137),dtype=np.uint8)
    packed=np.packbits(raw,axis=1)
    table=PackedFingerprints(packed,137,device)
    selection=torch.tensor([[0,4,13],[46,1,0]],device=device)
    actual=table[selection].float()
    expected=torch.tensor(raw[np.array([[0,4,13],[46,1,0]])],device=device,dtype=torch.float32)
    assert torch.equal(actual,expected)
    logits=torch.randn((2,137),device=device,requires_grad=True)
    left=torch.bmm(actual,logits.unsqueeze(-1)).squeeze(-1)
    right=torch.bmm(expected,logits.unsqueeze(-1)).squeeze(-1)
    gleft=torch.autograd.grad(left.square().sum(),logits,retain_graph=True)[0]
    gright=torch.autograd.grad(right.square().sum(),logits)[0]
    assert torch.equal(left,right) and torch.equal(gleft,gright)
    return dict(status='PASS',bit_parity=True,score_parity=True,gradient_parity=True,
                bits=137,non_byte_aligned=True,device=device)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--spec',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--seed',type=int,default=20261003)
    parser.add_argument('--layers',type=int,default=8)
    parser.add_argument('--batch-size',type=int,default=256)
    parser.add_argument('--micro-batch-size',type=int,default=128)
    parser.add_argument('--steps',type=int,default=30000)
    parser.add_argument('--max-minutes',type=float,default=450)
    parser.add_argument('--validation-every',type=int,default=2000)
    parser.add_argument('--merge-probability',type=float,default=0.)
    parser.add_argument('--probe-only',action='store_true')
    args=parser.parse_args()
    assert args.merge_probability==0.,'This treatment is one single-spectrum view'
    assert 0<args.micro_batch_size<=args.batch_size
    assert torch.cuda.is_available(),'Full training requires the scheduled CUDA worker'
    args.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(2)
    torch.manual_seed(args.seed);np.random.seed(args.seed)
    started=time.monotonic()
    contract=lookup_contract('cuda')
    data=FullData(args.data,'cuda',args.spec)
    model=FPNet(data.nbits,d=512,layers=args.layers).cuda()
    optimizer=torch.optim.AdamW(model.parameters(),lr=2e-4,weight_decay=.01,betas=(.9,.98))
    scaler=torch.amp.GradScaler('cuda')
    rng=np.random.default_rng(args.seed)
    recipe=dict(vars(args))
    recipe.update(data=str(args.data),spec=str(args.spec) if args.spec is not None else None,out=str(args.out),
        parameters=sum(p.numel() for p in model.parameters()),lookup_contract=contract,split=data.receipt,
        fixed_validation_seed=20261004,validation_metric='structure-weighted sampled-decoy MRR@25',
        seed_before_model_creation=True,optimizer_only=True,final_test_used=False,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        baseline_source_sha256=BASELINE_SOURCE_SHA,sampler=data.optimizer_sampler.receipt())
    (args.out/'sampler_distribution.json').write_text(json.dumps(recipe['sampler'],indent=2))
    np.save(args.out/'optimizer_structure_indices.npy',data.optimizer_sampler.structures)
    np.save(args.out/'optimizer_eligible_spectrum_counts.npy',data.optimizer_sampler.counts)
    (args.out/'training_recipe.json').write_text(json.dumps(recipe,indent=2))
    print('FULL_TRAINING_RECIPE',json.dumps(recipe),flush=True)
    # A representative of each checkpoint structure keeps the proxy group-balanced.
    validation_rng=np.random.default_rng(20261004)
    structures,first=np.unique(data.six[data.va],return_index=True)
    chosen=validation_rng.choice(len(structures),size=min(2048,len(structures)),replace=False)
    validation_ids=data.va[first[chosen]]
    np.save(args.out/'checkpoint_spectrum_ids.npy',validation_ids)
    validation_negatives=data.sample_negs(data.s2p[data.six[validation_ids]],63,rng=np.random.default_rng(20261005))
    np.save(args.out/'checkpoint_decoy_indices.npy',validation_negatives)
    validation_hashes={name:hashlib.sha256((args.out/name).read_bytes()).hexdigest() for name in FIXED_VALIDATION_SHA}
    assert validation_hashes==FIXED_VALIDATION_SHA,'Fixed owned single-spectrum checkpoint validation drifted'
    (args.out/'fixed_validation_binding.json').write_text(json.dumps(dict(
        checkpoint_structures=len(validation_ids),file_sha256=validation_hashes,
        spectrum_selection_seed=20261004,decoy_seed=20261005,decoys=63,
        role='role 1 with even trainer fp_meta structure index',baseline_source_sha256=BASELINE_SOURCE_SHA),indent=2))
    best=-1.;times=[];nonfinite=0;actual_steps=0

    def validate(step):
        model.eval();rank_values=[];bce_total=0.;count=0
        local_rng=np.random.default_rng(20261004)
        with torch.inference_mode():
            for offset in range(0,len(validation_ids),128):
                ids=validation_ids[offset:offset+128]
                bce,rank_logits=scores(model,data,ids,local_rng,63,
                                       merge_probability=args.merge_probability,
                                       fixed_negatives=validation_negatives[offset:offset+len(ids)])
                order=torch.argsort(rank_logits,dim=1,descending=True,stable=True)
                positions=(order==0).to(torch.int64).argmax(1)+1
                values=torch.where(positions<=25,1./positions.float(),0.)
                rank_values.extend(values.cpu().tolist());bce_total+=bce.item()*len(ids);count+=len(ids)
        model.train()
        return dict(step=step,mrr25=float(np.mean(rank_values)),bce=bce_total/count,
                    checkpoint_structures=count,seconds=round(time.monotonic()-started,1))

    for step in range(64 if args.probe_only else args.steps):
        step_started=time.monotonic()
        warm=min(2000,args.steps//10)
        progress=max(0,(step-warm)/max(1,args.steps-warm))
        lr=2e-4*(step+1)/max(1,warm) if step<warm else 2e-4*(.02+.98*.5*(1+math.cos(math.pi*min(1,progress))))
        for group in optimizer.param_groups:group['lr']=lr
        ids=data.optimizer_sampler.sample(rng,args.batch_size)
        optimizer.zero_grad(set_to_none=True)
        bce_value=0.;loss_value=0.;valid_step=True
        for offset in range(0,len(ids),args.micro_batch_size):
            chunk=ids[offset:offset+args.micro_batch_size]
            bce,ranking=scores(model,data,chunk,rng,63,True,args.merge_probability)
            loss=bce+F.cross_entropy(ranking,torch.zeros(len(chunk),dtype=torch.long,device='cuda'))
            if not torch.isfinite(loss):
                nonfinite+=1;valid_step=False
                assert nonfinite<5,'Repeated nonfinite training losses'
                break
            fraction=len(chunk)/len(ids)
            bce_value+=bce.item()*fraction;loss_value+=loss.item()*fraction
            scaler.scale(loss*fraction).backward()
        if not valid_step:
            optimizer.zero_grad(set_to_none=True)
            continue
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
        scaler.step(optimizer);scaler.update()
        torch.cuda.synchronize();actual_steps+=1;times.append(time.monotonic()-step_started)
        if (step+1)%16==0:
            record=dict(step=step+1,bce=round(bce_value,5),loss=round(loss_value,5),
                        step_seconds=round(float(np.median(times[-16:])),4),
                        peak_gpu_bytes=torch.cuda.max_memory_allocated(),seconds=round(time.monotonic()-started,1))
            (args.out/'progress.json').write_text(json.dumps(record,indent=2))
            print('FULL_TRAINING_STEP',json.dumps(record),flush=True)
        if not args.probe_only and ((step+1)%args.validation_every==0 or step+1==args.steps):
            record=validate(step+1)
            with (args.out/'checkpoint_history.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')
            print('FULL_CHECKPOINT',json.dumps(record),flush=True)
            if record['mrr25']>best:
                best=record['mrr25']
                torch.save(dict(model=model.state_dict(),step=step+1,nbits=data.nbits,d=512,layers=args.layers,
                                validation=record,split=data.receipt,seed=args.seed),args.out/'best_full_model.pt')
                (args.out/'best_checkpoint.json').write_text(json.dumps(record,indent=2))
        if (time.monotonic()-started)/60>=args.max_minutes:break
    if not args.probe_only and best<0:
        record=validate(actual_steps);best=record['mrr25']
        torch.save(dict(model=model.state_dict(),step=actual_steps,nbits=data.nbits,d=512,layers=args.layers,
                        validation=record,split=data.receipt,seed=args.seed),args.out/'best_full_model.pt')
        (args.out/'best_checkpoint.json').write_text(json.dumps(record,indent=2))
    receipt=dict(status='PASS_PROBE' if args.probe_only else 'COMPLETE_TRAINING',
                 actual_steps=actual_steps,nonfinite_steps=nonfinite,
                 median_step_seconds=float(np.median(times[8:])) if len(times)>8 else float(np.median(times)),
                 projected_30000_step_hours=float(np.median(times[8:]))*30000/3600 if len(times)>8 else None,
                 peak_gpu_bytes=torch.cuda.max_memory_allocated(),best_checkpoint_mrr25=None if args.probe_only else best,
                 measured_device=torch.cuda.get_device_name(0),final_test_used=False,
                 seconds=round(time.monotonic()-started,1))
    (args.out/'runtime_receipt.json').write_text(json.dumps(receipt,indent=2))
    print('FULL_TRAINING_DONE',json.dumps(receipt),flush=True)

if __name__=='__main__':main()
