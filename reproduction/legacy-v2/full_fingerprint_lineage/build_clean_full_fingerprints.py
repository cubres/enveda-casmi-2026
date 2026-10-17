"""Prepare private optimizer-selected full fingerprint targets with additive files."""
import base64
import datetime
import hashlib
import json
import multiprocessing
import os
import pickle
from pathlib import Path
import time
import zlib

import numpy as np
import pandas as pd
from rdkit import Chem,RDLogger
from rdkit.Chem import rdFingerprintGenerator,MACCSkeys

ROOT=Path(__file__).resolve().parent
SOURCE=Path('/Users/cubres/Documents/Clauding/casmi_work')
PART=ROOT.parent/'enveda_glacier_partition_20260930T165020Z'
SPLIT=ROOT.parent/'claude_campaign_20261002/enveda/clean_fp_split_20261002T1652Z'
RAW_BITS=10407
GENERATORS=None
SELECTED=None

def initialize(bits):
    global GENERATORS,SELECTED
    RDLogger.DisableLog('rdApp.*');SELECTED=bits
    GENERATORS=[rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=4096),
                rdFingerprintGenerator.GetMorganGenerator(radius=3,fpSize=4096),
                rdFingerprintGenerator.GetRDKitFPGenerator(fpSize=2048,maxPath=6)]

def fingerprint(smiles):
    molecule=Chem.MolFromSmiles(smiles)
    if molecule is None:raise ValueError('Candidate structure is invalid')
    raw=np.concatenate([g.GetFingerprintAsNumPy(molecule).astype(np.uint8) for g in GENERATORS]
                       +[np.asarray(MACCSkeys.GenMACCSKeys(molecule),np.uint8)])
    assert len(raw)==RAW_BITS
    return np.packbits(raw[SELECTED])

def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8<<20),b''):digest.update(block)
    return digest.hexdigest()

def main():
    os.nice(5);started=time.monotonic()
    out=ROOT/('clean_full_fp_data_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    out.mkdir(exist_ok=False)
    structures=pickle.load((SOURCE/'data/struct_fp_meta.pkl').open('rb'))
    selected_meta=pickle.load((SOURCE/'up_train/fp_meta.pkl').open('rb'))
    assert structures['keys']==selected_meta['keys'] and structures['smiles']==selected_meta['smiles']
    raw=np.load(SOURCE/'data/struct_fp.npy',mmap_mode='r');assert raw.shape==(len(structures['keys']),1301)
    encoded=(SPLIT/'roles_by_structure.b64').read_text().strip()
    b=np.unpackbits(np.frombuffer(zlib.decompress(base64.b64decode(encoded)),np.uint8))[:2*len(raw)].reshape(-1,2)
    roles=(2*b[:,0]+b[:,1]).astype(np.uint8)
    expected_role_sha=(SPLIT/'roles_by_structure.sha256').read_text().split()[0]
    assert hashlib.sha256(roles.tobytes()).hexdigest()==expected_role_sha
    canonical=pd.read_csv(PART/'canonical_structures.tsv',sep='\t',usecols=['structure_index','group_id','smiles'])
    groups=pd.read_csv(PART/'group_partitions.tsv',sep='\t',usecols=['group_id','partition'])
    canonical=canonical.merge(groups,on='group_id',validate='many_to_one').set_index('smiles')
    assert canonical.index.is_unique
    canonical=canonical.reindex(structures['smiles'])
    assert canonical.group_id.notna().all()
    role_codes={'optimizer':0,'checkpoint_selection':1,'fusion_selection':2,'final_test':3}
    six=np.load(SOURCE/'up_train/spec.npz')['six']
    observed=np.zeros(len(raw),bool);observed[np.unique(six)]=True
    assert np.array_equal(canonical.partition.map(role_codes).to_numpy()[observed],roles[observed])
    assert (roles[~observed]==3).all()
    optimizer=np.flatnonzero(roles==0);counts=np.zeros(RAW_BITS,np.int64)
    for offset in range(0,len(optimizer),4096):
        block=np.unpackbits(np.asarray(raw[optimizer[offset:offset+4096]]),axis=1)[:,:RAW_BITS]
        counts+=block.sum(axis=0,dtype=np.int64)
    bits=np.flatnonzero((counts>0)&(counts<len(optimizer)))
    np.save(out/'fp_bits.npy',bits);np.save(out/'optimizer_bit_counts.npy',counts)
    print('FULL_BIT_SELECTION',out,'optimizer',len(optimizer),'bits',len(bits),flush=True)
    # Preserve the exact existing candidate order and mass index.
    pool=pickle.load((SOURCE/'up_pool/pool_meta.pkl').open('rb'))
    keys=np.asarray(pool['keys']);smiles=np.asarray(pool['smiles'])
    train_index={key:i for i,key in enumerate(structures['keys'])}
    indices=np.asarray([train_index.get(k,-1) for k in keys])
    matrix=np.lib.format.open_memmap(out/'pool_fp.npy',mode='w+',dtype=np.uint8,
                                    shape=(len(keys),(len(bits)+7)//8))
    known=np.flatnonzero(indices>=0)
    for offset in range(0,len(known),4096):
        destination=known[offset:offset+4096]
        block=np.unpackbits(np.asarray(raw[indices[destination]]),axis=1)[:,:RAW_BITS]
        matrix[destination]=np.packbits(block[:,bits],axis=1)
    unknown=np.flatnonzero(indices<0)
    with multiprocessing.get_context('fork').Pool(2,initializer=initialize,initargs=(bits,)) as workers:
        for j,packed in enumerate(workers.imap(fingerprint,smiles[unknown],chunksize=128)):
            matrix[unknown[j]]=packed
            if (j+1)%20000==0:
                matrix.flush()
                (out/'progress.json').write_text(json.dumps(dict(pool_rows=len(keys),known_rows=len(known),novel_rows_done=j+1,
                      novel_rows=len(unknown),seconds=round(time.monotonic()-started,1)),indent=2))
                print('FULL_POOL_FINGERPRINTS',j+1,'/',len(unknown),round(time.monotonic()-started,1),flush=True)
    matrix.flush()
    # These unmodified input files are linked locally for staging. No source is changed.
    os.symlink(SOURCE/'up_train/spec.npz',out/'spec.npz')
    os.symlink(SOURCE/'up_pool/pool_mass.npy',out/'pool_mass.npy')
    (out/'roles_by_structure.b64').write_text(encoded+'\n')
    model_metadata=dict(selected_meta,nbits=len(bits))
    (out/'fp_meta.pkl').write_bytes(pickle.dumps(model_metadata,protocol=4))
    (out/'pool_meta.pkl').write_bytes(pickle.dumps(dict(pool,nbits=len(bits)),protocol=4))
    initialize(bits)
    sample=np.linspace(0,len(keys)-1,128).astype(int)
    for row in sample:assert np.array_equal(fingerprint(smiles[row]),matrix[row]),int(row)
    report=dict(status='PASS_DATA_PREPARATION',raw_bits=RAW_BITS,selected_bits=len(bits),optimizer_structures=len(optimizer),
                bit_selection='nonconstant bits among optimizer structures only; no held-role frequencies',
                index_alignment='model structure order joined to canonical groups by exact SMILES; observed roles verified',
                pool_rows=len(keys),pool_order_preserved=True,known_train_rows=len(known),novel_structure_rows=len(unknown),
                sample_fingerprint_parity=len(sample),role_table_sha256=expected_role_sha,
                structure_roles=dict(zip(*np.unique(roles,return_counts=True))),
                rdkit=__import__('rdkit').__version__,source_raw_sha256=sha(SOURCE/'data/struct_fp.npy'),
                files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in out.iterdir() if p.is_file() and p.name!='progress.json'},
                training_started=False,uploaded=False,public=False,seconds=round(time.monotonic()-started,1))
    report['structure_roles']={str(k):int(v) for k,v in report['structure_roles'].items()}
    (out/'preparation_receipt.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2),flush=True)

if __name__=='__main__':main()
