"""Bounded metadata-only canonical-group audit for the public CASMI V7 cache.

Never reads logits, spectra, fingerprints, weights, held query arrays, or scores.
Never imports the original role builder/partition module. Apache-2.0.

Public-input rebuild recipe. No unpublished canonical map is required.
This full recomputation source has not been executed for the dataset release;
the released metadata was produced by exact original-map joins and checked
independently. Resource admission remains strict on the user's actual machine.
"""
from __future__ import annotations
import argparse, ast, base64, hashlib, importlib.util, json, multiprocessing as mp
import os, pickle, resource, sys, time, zlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

META_SHA = "88411e98cec6f862f7b121dbc27b807e5e18782416219fe2b11566deb3254132"
ROLES_FILE_SHA = "fe654a3f5f655df3897a344ca222e01a9f555a7dfd22a786e6cb32b126c76049"
ROLES_RAW_SHA = "4d7b366293225a1ae67dfc0306480129b9ac1351a6d8581f0be40a269bdaff86"
METRIC_SHA = "b4c0bbbafca0d821d872733d28f39518f41be53004970a9eeb725aef94a47b4f"
GROUP_IDENTITY_SHA = "dd4c1750cf4816cdc3d880df837bdffec6a2beb62f3b676cc5ca663107ee042d"
CACHE_PINS = {
 "structure_indices.npy": "600e5b6d56cfc4884b51ad6ea2dd31c3030d393f43a77d44de5140a147c9b168",
 "structure_keys.npy": "b5b2db064052c00cb616000a0f4f7b92b38b6455c6e199fd6bdf2fe38e5728b8",
}
EXPECTED_RELEASE_OUTPUTS = {
  "all_cache_exclusion_reason.npy": {
    "bytes": 2172768,
    "sha256": "f03a63aa617ce5de27686e1f61b4e1885cd2e673efe37df04e0d4327f23009a9"
  },
  "cache_query_rows.npy": {
    "bytes": 108224,
    "sha256": "7f3b442fe4aafd89b4057221390c94eb2ef005c0d8086437984e9a9255f82a92"
  },
  "canonical_group_ids.npy": {
    "bytes": 3459200,
    "sha256": "445c1ee8b5bf6744c0a970643a037a20eb00b0fe6c32586349208097de9e4288"
  },
  "role01_canonical_group_ids.npy": {
    "bytes": 63148672,
    "sha256": "680232954b7ffdd70e36d3fe6c57bdd3ca2b54d1308602ffb265225352253884"
  },
  "role01_trainer_structure_indices.npy": {
    "bytes": 1973520,
    "sha256": "f0f7046c107d8f2641e0ff93706a38e0dd78f0ffbf8c27541699cf5300b2220c"
  },
  "split_buckets.npy": {
    "bytes": 27152,
    "sha256": "bebf14e37d8d29704dceeafdc3f2e783d99b669a983ff4ed4409791cbfc06a71"
  },
  "split_train0_development1.npy": {
    "bytes": 13640,
    "sha256": "414b7bd6f4227b0459bafb901eeb1a191fce1c1b46fa1fb7526789248482a57b"
  },
  "trainer_structure_indices.npy": {
    "bytes": 108224,
    "sha256": "4a1399ef1ef8abc42b5c0d56c3b8143c460006df1c9ea83ed5f5df659b59ad56"
  }
}
SALT = "casmi-v6-role1odd-ranker-group-v1-20261019"
WORKERS = 2
SECONDS = 1800
MAX_WORKER_RSS = 1 << 30
MAX_PARENT_RSS = 2 << 30


def digest(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for b in iter(lambda:f.read(8<<20),b""): h.update(b)
 return h.hexdigest()


def require(value, message):
 if not value: raise ValueError(message)


def pinned(path, sha):
 require(digest(path)==sha,"Input hash mismatch: "+str(path))
 return {"path":str(path),"bytes":Path(path).stat().st_size,"sha256":sha}


def rss():
 r=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
 return int(r if sys.platform=="darwin" else r*1024)


def write_json(path, value):
 with Path(path).open("x") as f: json.dump(value,f,sort_keys=True,indent=2); f.write("\n")


def load_converter(metric, partition):
 pinned(metric,METRIC_SHA);pinned(partition,GROUP_IDENTITY_SHA)
 spec=importlib.util.spec_from_file_location("pinned_metric_distinct",metric)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 # Extract ONLY this pure function; never execute pandas/data-reading role builder.
 tree=ast.parse(Path(partition).read_text())
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="group_identity")
 namespace={"json":json,"hashlib":hashlib}
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(partition),"exec"),namespace)
 return module.equivalence_key,namespace["group_identity"]


def worker_init(metric,partition):
 global convert,identify
 os.nice(5)
 require(os.getpriority(os.PRIO_PROCESS,0)>=5,"Worker nice level")
 convert,identify=load_converter(metric,partition)
 from rdkit import RDLogger
 RDLogger.DisableLog("rdApp.*")


def canonicalize(item):
 i,s=item
 key=convert(s)
 group=identify(key)[0] if key is not None else ""
 usage=rss()
 require(usage<=MAX_WORKER_RSS,"Worker RSS cap")
 return i,group,usage


def split_bucket(group):
 return int.from_bytes(hashlib.sha256((SALT+":"+group).encode()).digest()[:8],"big")%10000


def exclusion(group, optimizer, selection):
 if not group: return "invalid_metric_group"
 if group in optimizer and group in selection: return "optimizer_and_checkpoint_overlap"
 if group in optimizer: return "optimizer_overlap"
 if group in selection: return "checkpoint_overlap"
 return "survives"


def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--bank",required=True,type=Path);ap.add_argument("--cache",required=True,type=Path)
 ap.add_argument("--source-dir",default=Path(__file__).resolve().parent,type=Path);ap.add_argument("--out",required=True,type=Path)
 args=ap.parse_args()
 if os.getpriority(os.PRIO_PROCESS,0)<5: os.nice(5-os.getpriority(os.PRIO_PROCESS,0))
 require(os.getpriority(os.PRIO_PROCESS,0)>=5,"Parent nice level")
 started=time.monotonic();deadline=started+SECONDS-30
 args.out.mkdir(parents=True,exist_ok=False)
 report={"schema":"casmi-v7-canonical-reserved-group-audit/1","status":"STARTED",
 "started_utc":datetime.now(timezone.utc).isoformat(),"source_sha256":digest(__file__),"full_recompute_recipe":True,
 "limits":{"workers":WORKERS,"wall_seconds":SECONDS,"parent_rss_bytes":MAX_PARENT_RSS,"worker_rss_bytes":MAX_WORKER_RSS},
 "scope":{"metadata_only":True,"logits_read":False,"spectra_read":False,"fingerprints_read":False,"weights_read":False,
 "model_or_ranker_training":False,"model_evaluation":False,"old_assay_repeated":False,"role2_or_role3_canonicalized":False,
 "fp_meta_all_structure_metadata_loaded":True,"role2_or_role3_queries_loaded":False},"official_score":None}
 pool=None
 try:
  import numpy as np,rdkit
  require(rdkit.__version__=="2026.03.3","Exact metric RDKit pin")
  inputs={"fp_meta":pinned(args.bank/"fp_meta.pkl",META_SHA),"roles_file":pinned(args.bank/"roles_by_structure.b64",ROLES_FILE_SHA),
   "metric_source":pinned(args.source_dir/"metric_distinct.py",METRIC_SHA),"group_identity_source":pinned(args.source_dir/"group_identity.py",GROUP_IDENTITY_SHA)}
  for name,sha in CACHE_PINS.items():inputs[name]=pinned(args.cache/name,sha)
  report["inputs"]=inputs
  with (args.bank/"fp_meta.pkl").open("rb") as f:meta=pickle.load(f)
  require(set(meta)=={"keys","smiles","nbits"},"Metadata schema")
  require(len(meta["keys"])==len(meta["smiles"])==275810 and meta["nbits"]==10395,"Metadata dimensions")
  raw=np.frombuffer(zlib.decompress(base64.b64decode((args.bank/"roles_by_structure.b64").read_text().strip())),np.uint8)
  bits=np.unpackbits(raw)[:2*len(meta["keys"])].reshape(-1,2)
  roles=(2*bits[:,0]+bits[:,1]).astype(np.uint8)
  require(hashlib.sha256(roles.tobytes()).hexdigest()==ROLES_RAW_SHA,"Decoded roles SHA")
  ids=np.load(args.cache/"structure_indices.npy",allow_pickle=False)
  keys=np.load(args.cache/"structure_keys.npy",allow_pickle=False)
  require(ids.shape==(13579,) and ids.dtype==np.int64,"Cache index schema")
  require(np.all((ids>=0)&(ids<len(roles))) and np.all(np.diff(ids)>0),"Cache index order")
  require(np.all(roles[ids]==1) and np.all(ids%2==1),"Cache reserved role/parity")
  require(np.array_equal(keys,np.asarray(meta["keys"])[ids]),"Cache exact public metadata key join")
  selected=np.flatnonzero(roles<=1)
  # Ignore all role2/3 strings when constructing canonicalization workload.
  unique=sorted(set(meta["smiles"][int(i)] for i in selected))
  require(all(isinstance(s,str) and s for s in unique),"Nonempty role0/1 SMILES")
  report["role_structure_counts"]={str(k):int(v) for k,v in Counter(map(int,roles)).items()}
  report["canonicalization_unique_smiles"]=len(unique)
  pool=mp.get_context("spawn").Pool(WORKERS,initializer=worker_init,initargs=(str(args.source_dir/"metric_distinct.py"),str(args.source_dir/"group_identity.py")))
  # Metadata throughput canary only. No logits, candidates, training, or scores.
  sample=np.linspace(0,len(unique)-1,256,dtype=np.int64)
  tasks=[(int(i),unique[int(i)]) for i in sample]
  warm=pool.imap_unordered(canonicalize,tasks[:2],chunksize=1)
  warm_results=[warm.next(timeout=max(.001,deadline-time.monotonic())) for _ in tasks[:2]]
  t0=time.monotonic();canary=[]
  it=pool.imap_unordered(canonicalize,tasks,chunksize=1)
  for _ in tasks:
   canary.append(it.next(timeout=max(.001,deadline-time.monotonic())))
  canary_seconds=time.monotonic()-t0
  forecast=canary_seconds/len(tasks)*len(unique)*1.5+60
  report["metadata_canary"]={"strings":len(tasks),"seconds":canary_seconds,"forecast_seconds":forecast,"all_valid":all(g for _,g,_ in canary)}
  require(all(g for _,g,_ in canary),"Invalid metadata canary group")
  require(forecast<deadline-time.monotonic(),"Metadata throughput forecast exceeds remaining deadline; no full workload started")
  print(json.dumps({"phase":"metadata_canary_pass","unique_strings":len(unique),"seconds":canary_seconds,"forecast_seconds":forecast}),flush=True)
  groups={i:g for i,g,_ in canary};peak_worker=max(u for _,_,u in canary)
  remaining=((i,s) for i,s in enumerate(unique) if i not in groups)
  it=pool.imap_unordered(canonicalize,remaining,chunksize=1)
  next_notice=time.monotonic()+30
  for _ in range(len(unique)-len(groups)):
   i,g,u=it.next(timeout=max(.001,deadline-time.monotonic()))
   groups[i]=g;peak_worker=max(peak_worker,u)
   require(time.monotonic()<deadline,"Metadata wall cap")
   if time.monotonic()>=next_notice:
    require(rss()<=MAX_PARENT_RSS,"Parent RSS cap")
    print(json.dumps({"phase":"canonicalizing_metadata","complete":len(groups),"total":len(unique),"elapsed_seconds":time.monotonic()-started}),flush=True)
    next_notice=time.monotonic()+30
  pool.close();pool.join();pool=None
  require(len(groups)==len(unique),"Missing canonicalization results")
  require(all(groups.values()),"Invalid full role0/role1 exclusion universe; no qualified survivors emitted")
  by_smiles={s:groups[i] for i,s in enumerate(unique)}
  by_structure={int(i):by_smiles[meta["smiles"][int(i)]] for i in selected}
  optimizer={g for i,g in by_structure.items() if roles[i]==0 and g}
  selection={g for i,g in by_structure.items() if roles[i]==1 and i%2==0 and g}
  all_query_groups=[by_structure[int(i)] for i in ids]
  reasons=[exclusion(g,optimizer,selection) for g in all_query_groups]
  keep=np.asarray([r=="survives" for r in reasons],np.bool_)
  survivors=ids[keep]
  surviving_groups=np.asarray(all_query_groups,dtype="U64")[keep]
  buckets=np.asarray([split_bucket(str(g)) for g in surviving_groups],np.int16)
  split=np.where(buckets<8000,0,1).astype(np.uint8)
  train_groups=set(surviving_groups[split==0]);val_groups=set(surviving_groups[split==1])
  require(not train_groups&val_groups,"Train-validation canonical group overlap")
  require(not set(surviving_groups)&(optimizer|selection),"Excluded group survived")
  require(np.all(roles[survivors]==1) and np.all(survivors%2==1),"Survivor role drift")
  outputs={"role01_trainer_structure_indices":selected.astype(np.int64),
   "role01_canonical_group_ids":np.asarray([by_structure[int(i)] for i in selected],dtype="U64"),
   "cache_query_rows":np.flatnonzero(keep).astype(np.int64),"trainer_structure_indices":survivors,
   "canonical_group_ids":surviving_groups,"split_buckets":buckets,"split_train0_development1":split,
   "all_cache_exclusion_reason":np.asarray(reasons,dtype="U40")}
  for name,array in outputs.items():
   with (args.out/(name+".npy")).open("xb") as f:np.save(f,array,allow_pickle=False)
  report.update(status="COMPLETE_METADATA_GROUP_AUDIT",finished_utc=datetime.now(timezone.utc).isoformat(),
   cache_queries=len(ids),optimizer_structure_count=int(np.count_nonzero(roles==0)),
   checkpoint_even_structure_count=int(np.count_nonzero((roles==1)&(np.arange(len(roles))%2==0))),
   optimizer_canonical_groups=len(optimizer),checkpoint_even_canonical_groups=len(selection),
   invalid_role0_or_role1_structures=sum(not g for g in by_structure.values()),
   exclusion_counts=dict(Counter(reasons)),surviving_queries=len(survivors),surviving_canonical_groups=len(set(surviving_groups)),
   train_queries=int(np.count_nonzero(split==0)),train_canonical_groups=len(train_groups),
   development_queries=int(np.count_nonzero(split==1)),development_canonical_groups=len(val_groups),
   canonical_group_overlap={"train_vs_development":0,"survivors_vs_optimizer":0,"survivors_vs_checkpoint_even":0},
   split={"salt":SALT,"hash":'sha256(salt+":"+group_id), first8bytes big-endian mod10000',"train":"0..7999","development":"8000..9999"},
   qualification="Group-excluded public V7 logits metadata. No new ranker, OOF claim, accuracy metric, or official score.",
   environment={"python":sys.version,"numpy":np.__version__,"rdkit":rdkit.__version__,"workers":WORKERS},
   peak_parent_rss_bytes=rss(),peak_worker_rss_bytes=peak_worker,seconds=time.monotonic()-started,
   outputs={n+".npy":{"bytes":(args.out/(n+".npy")).stat().st_size,"sha256":digest(args.out/(n+".npy"))} for n in outputs})
  require(report["seconds"]<=SECONDS and rss()<=MAX_PARENT_RSS,"Final budget gate")
  require(report["outputs"]==EXPECTED_RELEASE_OUTPUTS,"Exact released split-byte parity gate")
  write_json(args.out/"GROUP_AUDIT_RECEIPT.json",report)
  print(json.dumps({k:report[k] for k in ("status","surviving_queries","surviving_canonical_groups","train_queries","development_queries","exclusion_counts","seconds")}),flush=True)
 except Exception as error:
  report.update(status="STOPPED_METADATA_AUDIT_UNQUALIFIED",error_type=type(error).__name__,error=str(error),seconds=time.monotonic()-started)
  write_json(args.out/"STOPPED_RECEIPT.json",report)
  raise
 finally:
  if pool is not None:pool.terminate();pool.join()

if __name__=="__main__":main()
