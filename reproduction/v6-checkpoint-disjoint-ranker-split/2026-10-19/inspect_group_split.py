"""Inspect the frozen CASMI group-split metadata; does not read predictions."""
from pathlib import Path
import argparse, hashlib, json
import numpy as np

RECEIPT_SHA256 = "3776b5bd8a748944e6b8d91105be5879e25acdcd32672ec95752fd420a010eba"


def sha256(path):
 value=hashlib.sha256()
 with path.open("rb") as stream:
  for block in iter(lambda:stream.read(8<<20),b""):value.update(block)
 return value.hexdigest()


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("audit_directory",type=Path)
 args=parser.parse_args();root=args.audit_directory
 receipt_path=root/"GROUP_AUDIT_RECEIPT_PUBLIC.json"
 if sha256(receipt_path)!=RECEIPT_SHA256:raise ValueError("Exact audit receipt mismatch")
 receipt=json.loads(receipt_path.read_text())
 full_path=root/"FULL_REBUILD_RECEIPT_PUBLIC.json"
 if sha256(full_path)!="a851b88bb9690ba5b6d72eaa22ca238afaac1a9faf65105471d43ad693200dc4":raise ValueError("Exact full rebuild proof mismatch")
 full=json.loads(full_path.read_text())
 if full["status"]!="COMPLETE_METADATA_GROUP_AUDIT" or full["source_sha256"]!="0f5099865aee7c9c5179cd9ec943bf45b7cfdf9f8f4952c77efb3e609ccf7b9e" or full["outputs"]!=receipt["outputs"] or full["actual_process_exit_code"]!=0:raise ValueError("Full rebuild qualification mismatch")
 for name,binding in receipt["outputs"].items():
  path=root/name
  if path.stat().st_size!=binding["bytes"] or sha256(path)!=binding["sha256"]:raise ValueError("Exact array mismatch: "+name)
 groups=np.load(root/"canonical_group_ids.npy",mmap_mode="r",allow_pickle=False)
 split=np.load(root/"split_train0_development1.npy",mmap_mode="r",allow_pickle=False)
 rows=np.load(root/"cache_query_rows.npy",mmap_mode="r",allow_pickle=False)
 if not groups.shape==split.shape==rows.shape==(13512,):raise ValueError("Query-alignment mismatch")
 train=set(groups[split==0]);development=set(groups[split==1])
 if train&development:raise ValueError("Canonical groups cross split boundary")
 report={"status":"PASS_EXACT_SPLIT_METADATA","queries":len(rows),"canonical_groups":len(set(groups)),
 "training_queries":int(np.count_nonzero(split==0)),"training_groups":len(train),
 "development_queries":int(np.count_nonzero(split==1)),"development_groups":len(development),
 "excluded_checkpoint_overlaps":receipt["exclusion_counts"]["checkpoint_overlap"],
 "predictions_or_weights_read":False,"accuracy_or_official_score":None}
 print(json.dumps(report,indent=2,sort_keys=True))

if __name__=="__main__":main()
