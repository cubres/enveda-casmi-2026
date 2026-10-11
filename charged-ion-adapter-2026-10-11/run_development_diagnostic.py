# SPDX-License-Identifier: MIT
"""Bounded private development diagnostic. No predictions, model loads or uploads.

Inputs remain private. Row ranks use existing numerical features, not the new
matching adapter or the incumbent fitted ranker's outputs.
"""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import sys
import time
import zipfile

from charged_ion_adapter import AdapterHold, adapt_spectrum, potential_reuse_intervals


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(4_194_304),b""):
            h.update(block)
    return h.hexdigest()


def inspect_rows_header(path):
    names=set()
    total=0
    with zipfile.ZipFile(path) as z:
        if len(z.infolist())!=4:raise ValueError("exactly four numerical row arrays required")
        for info in z.infolist():
            if info.filename in names:raise ValueError("duplicate array name")
            names.add(info.filename)
            if info.file_size>100_000_000:raise ValueError("oversized array")
            total+=info.file_size
            with z.open(info) as f:
                prefix=f.read(8)
                if prefix[:6]!=b"\x93NUMPY":raise ValueError("NPY magic required")
                version=tuple(prefix[6:8])
                if version not in ((1,0),(2,0)):raise ValueError("unsupported NPY version")
                size=int.from_bytes(f.read(2 if version==(1,0) else 4),"little")
                if not 1<=size<=16384:raise ValueError("NPY header length outside bounds")
                header=ast.literal_eval(f.read(size).decode("latin1"))
                if set(header)!={"descr","fortran_order","shape"}:raise ValueError("unexpected NPY header")
                if header["descr"] not in ("<f4","<f8","<i8"):raise ValueError("numeric little-endian arrays only")
                if type(header["shape"]) is not tuple or any(type(x) is not int or x<0 for x in header["shape"]):
                    raise ValueError("invalid numerical shape")
                if math.prod(header["shape"])>25_000_000:raise ValueError("shape outside bounds")
    if names!={"X.npy","Y.npy","M.npy","G.npy"} or total>120_000_000:
        raise ValueError("row archive contract mismatch")
    return total


def expected_rr25(scores,truth):
    """Uniform tie-order expectation; source candidate position gets no privilege."""
    s=float(scores[truth])
    higher=sum(float(x)>s for x in scores)
    tied=sum(float(x)==s for x in scores)
    if not tied:raise ValueError("truth not included in score ties")
    return sum(1.0/rank for rank in range(higher+1,min(25,higher+tied)+1))/tied


def run(train,rows,protocol,out):
    os.nice(5)
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    os.environ["OMP_NUM_THREADS"]="1"
    os.environ["OPENBLAS_NUM_THREADS"]="1"
    os.environ["MKL_NUM_THREADS"]="1"
    start=time.process_time()
    p=Path(protocol)
    if p.stat().st_size>32768:raise ValueError("protocol size outside bounds")
    pr=json.loads(p.read_text())
    if pr["status"]!="FROZEN_R2_DEVELOPMENT_BEFORE_NEW_LABEL_READ":
        raise ValueError("R2 protocol required")
    pins={x["path"]:x for x in pr["source_pins"]}
    for path in (train,rows):
        full=str(Path(path).resolve())
        if full not in pins or sha256(path)!=pins[full]["sha256"]:
            raise ValueError("frozen input hash mismatch")
    import numpy as np
    import pyarrow
    import pyarrow.parquet as pq
    columns=["ingest_lib","adduct","ionization_mode","precursor_mz","ms2_mzs",
             "ms2_normalized_intensities","instrument_type","collision_energy_ev",
             "collision_energy_orig_units"]
    pf=pq.ParquetFile(train)
    first=next(pf.iter_batches(batch_size=4096,columns=columns,use_threads=False))
    records=first.to_pylist()
    reasons=Counter();sources=Counter();adducts=Counter();modes=Counter()
    ready=windows=energy_comparable=overlap_spectra=overlap_pairs=adjacent_pairs=0
    kept_peaks=raw_peaks=0
    # Only physical first4096 rows. No structures/labels/IDs are read here.
    for record in records:
        library=record["ingest_lib"]
        if not isinstance(library,str) or not library.strip():
            reasons["HOLD_UNKNOWN_INGEST_SOURCE"]+=1
            continue
        if re.search(r"(?i)(?<![a-z])nist[0-9]*(?![a-z])",library):
            reasons["HOLD_NIST_SOURCE"]+=1
            continue
        sources[library]+=1
        try:
            view=adapt_spectrum(record)
        except (AdapterHold,TypeError) as error:
            reasons[str(error)]+=1
            continue
        ready+=1;adducts[view["metadata"]["adduct"]]+=1;modes[view["metadata"]["mode"]]+=1
        windows+=view["window"] is not None
        energy_comparable+=view["group_comparability"]!="HOLD"
        cleaned=view["cleaned"]
        raw_peaks+=cleaned["raw_peak_count"];kept_peaks+=cleaned["kept_peak_count"]
        geometry=potential_reuse_intervals(cleaned,abs_tol=.01,ppm=0)
        overlap_pairs+=geometry["overlapping_pairs"]
        adjacent_pairs+=geometry["adjacent_pairs"]
        overlap_spectra+=geometry["overlapping_pairs"]>0
    uncompressed=inspect_rows_header(rows)
    with np.load(rows,allow_pickle=False) as z:
        X=z["X"];Y=z["Y"];M=z["M"];G=z["G"]
        if X.shape!=(len(Y),31) or M.shape!=Y.shape or G.shape!=Y.shape:
            raise ValueError("row dimensions mismatch")
        if not all(np.isfinite(x).all() for x in (X,Y,M,G)):
            raise ValueError("nonfinite numerical row input")
        if not np.isin(Y,[0,1]).all() or not np.isin(M,[0,1]).all():
            raise ValueError("binary labels and two regimes required")
        chosen=np.unique(G)[:128]
        by_mode={}
        for regime in (0,1):
            records_out=[]
            for group in chosen:
                selected=(G==group)&(M==regime)
                xx=X[selected];yy=Y[selected]
                if len(xx)==0:continue
                positive=np.flatnonzero(yy==1)
                if len(positive)!=1:raise ValueError("each sampled group requires one positive")
                truth=int(positive[0]);base=xx[:,15];frag=xx[:,21]
                b=expected_rr25(base,truth);f=expected_rr25(frag,truth)
                negatives=frag[yy==0]
                records_out.append({
                    "candidates":len(xx),"fingerprint_feature_err25":b,
                    "fragment_feature_err25":f,"delta":f-b,
                    "fragment_all_zero":bool(np.all(frag==0)),
                    "positive_fragment_explain":float(frag[truth]),
                    "best_negative_fragment_explain":float(negatives.max()) if len(negatives) else None,
                })
            deltas=[x["delta"] for x in records_out]
            by_mode[str(regime)]={
                "groups":len(records_out),"candidates":sum(x["candidates"] for x in records_out),
                "mean_fingerprint_feature_err25":float(np.mean([x["fingerprint_feature_err25"] for x in records_out])),
                "mean_fragment_feature_err25":float(np.mean([x["fragment_feature_err25"] for x in records_out])),
                "paired_fragment_minus_fingerprint":float(np.mean(deltas)),
                "wins":sum(x>1e-12 for x in deltas),"losses":sum(x< -1e-12 for x in deltas),
                "ties":sum(abs(x)<=1e-12 for x in deltas),
                "all_zero_fragment_groups":sum(x["fragment_all_zero"] for x in records_out),
                "mean_positive_fragment_explain":float(np.mean([x["positive_fragment_explain"] for x in records_out])),
                "mean_best_negative_fragment_explain":float(np.mean([x["best_negative_fragment_explain"] for x in records_out if x["best_negative_fragment_explain"] is not None])),
            }
    result={
        "status":"EXPOSED_DEVELOPMENT_ONLY_NO_NEW_MATCHER_RANKING_OR_HIDDEN_TRANSFER",
        "utc":datetime.now(timezone.utc).isoformat(),
        "protocol_sha256":sha256(protocol),
        "input_sha256":{Path(x).name:sha256(x) for x in (train,rows)},
        "source_sha256":sha256(Path(__file__)),
        "adapter_source_sha256":sha256(Path(__file__).with_name("charged_ion_adapter.py")),
        "spectra":{
            "physical_rows_examined":len(records),"ready_assignment_metadata_rows":ready,
            "excluded_or_held":dict(reasons),"ingest_sources_examined":dict(sources),
            "ready_adducts":dict(adducts),"ready_modes":dict(modes),
            "rows_with_declared_acquisition_window":windows,
            "rows_with_comparable_declared_energy_and_instrument":energy_comparable,
            "raw_peak_total":raw_peaks,"kept_peak_total":kept_peaks,
            "adjacent_pairs":adjacent_pairs,"overlapping_tolerance_pairs":overlap_pairs,
            "spectra_with_at_least_one_potential_reuse_pair":overlap_spectra,
            "geometry_tolerance":{"abs_da":.01,"ppm":0},
            "observed_peak_extrema_used_as_window":False,
            "actual_fragment_hypothesis_reuse":"UNMEASURED_NO_BOUND_RAW_PREDICTION_INPUT",
            "native_cleaning_bitwise_parity":"UNVERIFIED_CHANGED_STABLE_TIE_PREPROCESSING",
        },
        "numeric_rows":{"uncompressed_bytes":uncompressed,"sample_rule":"first128sortedG, eachM",
                        "scores":"Existing Xcolumn15 fingerprint and Xcolumn21 fragment; no fitted ranker",
                        "new_feature_intervention":False,"by_regime":by_mode},
        "libraries":{"numpy":np.__version__,"pyarrow":pyarrow.__version__,"python":sys.version},
        "resources":{"cpu_seconds":time.process_time()-start,"maxrss_raw":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                     "maxrss_raw_units":"bytes" if sys.platform=="darwin" else "KiB","nice_adjustment":5,"cpu_limit_seconds":120},
        "publication":"PRIVATE_COMPETITION_DERIVED_AGGREGATES_PENDING_RIGHTS_REVIEW",
        "model_loads":0,"pickle_deserializations":0,"native_jobs":0,"submissions":0,
    }
    with Path(out).open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--train",required=True);parser.add_argument("--rows",required=True)
    parser.add_argument("--protocol",required=True);parser.add_argument("--out",required=True)
    args=parser.parse_args()
    run(args.train,args.rows,args.protocol,args.out)

