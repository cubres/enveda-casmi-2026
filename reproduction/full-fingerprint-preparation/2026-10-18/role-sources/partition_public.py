"""Prospective public-data partition proposal; performs no model evaluation.

Canonical equivalence follows the pinned CASMI metric implementation. Repeated
identical SMILES are processed once; raw InChIKey14 is not used as equivalence.
All outputs are exclusively created in this new research directory.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import multiprocessing as mp
import os
import pickle
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
WS = ROOT.parents[1]
OWN = Path("/Users/cubres/Documents/Clauding/casmi_work")
TABLE = WS / "research/enveda_glacier_cpu_20260930T163830Z/MassSpecGym1.5.tsv"
SAMPLE = WS / "research/enveda_glacier_cpu_20260930T163830Z/sample_input.tsv"
METRIC = WS / "research/enveda_casmi26_20260930_metric_dedup_155344Z/metric_distinct.py"
PINS = {
    TABLE: "50cfdd1d22f79543c59555f9ce43c6893bd788a19a42b21fb4e2e3a54673c06a",
    SAMPLE: "bcc37257be5231efe192592b316bf51b6dbaa914be4d871e0006b67a81774cb3",
    METRIC: "b4c0bbbafca0d821d872733d28f39518f41be53004970a9eeb725aef94a47b4f",
    OWN / "up_train/fp_meta.pkl": "d6ad0dd33bf66e92c5a85054b7f914b4ac538fc4b06c4aabca8d0df9f985b85b",
    OWN / "up_train/split.pkl": "25e00a31cd8acfdd97e0dd40e9a43aa257fefabd74416a0813f4710f62aa4b1e",
    OWN / "data/c2_np_recs2.pkl": "550b2d4ba4c206558cb0313df87dae23cfbe8726d89c168a7354cc4cd4666a64",
    OWN / "data/hard_feats.pkl": "84e5d837a0d34e584a48b73f34109e674e2bfe3944b043ad973116d6abaeab73",
}
SALT = "glacier-prospective-v1-20260930"
ROLES = ("optimizer", "checkpoint_selection", "fusion_selection", "final_test")
PROTOCOL = """Prospective original GLACIER pilot preparation, version1.
Input: pinned public MassSpecGym1.5 plus previously audited own public CASMI corpus.
Compute: at most2 CPU workers, inherited nice>=5, wall budget at most1200 seconds.
Equivalence: RDKit2026.03.3, default tautomer canonicalization, InChIKey14 plus
the official heavy-atom-composition gate. Exact repeated SMILES cached once.
Order: unique exact SMILES sorted lexically; output tables sorted by stable IDs.
Hash salt: glacier-prospective-v1-20260930. SHA256(salt + ':' + group_id), first
8 bytes interpreted big-endian, modulo10000; buckets0-7999 optimizer,
8000-8999 checkpoint_selection,9000-9499 fusion_selection,9500-9999 final_test.
Historical819 queried groups: optimizer-only. Other groups in the known2750
old checkpoint-selection raw-key list: remap final_test to optimizer.
The earlier256 selected structures were a schema/overlap audit only, without
model predictions, performance evaluation, or tuning; retain an exposure flag.
Original MassSpecGym fold is retained for audit but does not assign new roles.
Optimizer uses optimizer groups only. Checkpoint choice uses checkpoint_selection
only. Fusion choice uses fusion_selection only. Final_test is accessed once after
both choices are fixed. Every upstream learned component requires fresh training
and selection on the allowed groups; existing exposed weights are unsuitable.
Observed-spectrum retrieval references use optimizer groups only, for all held
roles. Apply exclusions to all spectra via corpus_structure_index -> six mapping;
also filter any additional library by the same metric-equivalence group.
Candidate molecular structures are distinct from observed-spectrum references:
freeze a blind candidate pool separately, never force-insert the known answer.
No model is evaluated in this preparation. This is a proposal, not evidence of
prediction performance. No finished partition is emitted unless every unique
input string receives a valid metric group before the deadline.
"""


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def tsv(path, fields, rows):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def group_identity(key):
    counts, inchikey = key
    comp = ",".join(f"{symbol}:{count}" for symbol, count in counts)
    payload = json.dumps([list(counts), inchikey], separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest(), comp, inchikey


def assign_role(group_id, historical, prior_selection):
    bucket = int.from_bytes(hashlib.sha256((SALT + ":" + group_id).encode()).digest()[:8], "big") % 10000
    role = ("optimizer" if bucket < 8000 else "checkpoint_selection" if bucket < 9000
            else "fusion_selection" if bucket < 9500 else "final_test")
    reason = "fixed_hash"
    if historical:
        role, reason = "optimizer", "historical819"
    elif prior_selection and role == "final_test":
        role, reason = "optimizer", "prior_checkpoint_selection"
    return role, reason, bucket


def worker_init():
    global equivalence_key
    assert os.getpriority(os.PRIO_PROCESS, 0) >= 5
    assert digest(METRIC) == PINS[METRIC]
    spec = importlib.util.spec_from_file_location("official_metric_equivalence", METRIC)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    equivalence_key = module.equivalence_key
    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.warning")
    RDLogger.DisableLog("rdApp.error")


def canonicalize(item):
    index, smiles = item
    key = equivalence_key(smiles)
    return (index, *group_identity(key), "valid") if key is not None else (index, "", "", "", "invalid")


def load_public_pickle(path):
    # These exact trusted local public-data artifacts are pinned above.
    with path.open("rb") as stream:
        return pickle.load(stream)


def save_hashes():
    files = sorted(x for x in ROOT.iterdir() if x.is_file() and x.name != "artifacts.tsv" and x.name != "run.log")
    tsv(ROOT / "artifacts.tsv", ["name", "bytes", "sha256"],
        ({"name": f.name, "bytes": f.stat().st_size, "sha256": digest(f)} for f in files))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=1200)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    assert 1 <= args.workers <= 2 and 1 <= args.seconds <= 1200
    assert os.getpriority(os.PRIO_PROCESS, 0) >= 5
    start = time.monotonic()
    # Reserve time for sorting, verification, and preservation of final tables.
    deadline = start + args.seconds - min(90, args.seconds // 10)
    summary = {"started_utc": datetime.now(timezone.utc).isoformat(), "seconds_cap": args.seconds,
        "workers": args.workers, "nice": os.getpriority(os.PRIO_PROCESS, 0),
        "model_evaluation_performed": False, "source_sha256": digest(Path(__file__))}
    (ROOT / "protocol.txt").open("x").write(PROTOCOL)
    for path, expected in PINS.items():
        assert digest(path) == expected, path
    tsv(ROOT / "inputs.tsv", ["path", "bytes", "sha256"],
        ({"path": str(p), "bytes": p.stat().st_size, "sha256": h} for p, h in PINS.items()))
    cols = ["identifier", "smiles", "inchikey", "fold", "simulation_challenge", "collision_energy"]
    df = pd.read_csv(TABLE, sep="\t", usecols=cols, dtype=str, keep_default_na=False)
    assert len(df) == 231104 and df.identifier.is_unique
    corpus = load_public_pickle(OWN / "up_train/fp_meta.pkl")
    assert len(corpus["keys"]) == len(corpus["smiles"]) == len(set(corpus["keys"])) == 275810
    prior = set(load_public_pickle(OWN / "up_train/split.pkl")["VAL"])
    history = {row["key"] for row in load_public_pickle(OWN / "data/c2_np_recs2.pkl")}
    history.update(row["key"] for row in load_public_pickle(OWN / "data/hard_feats.pkl")["meta"])
    assert len(history) == 819 and len(prior) == 2750
    assert history <= prior <= set(corpus["keys"])
    audited = pd.read_csv(SAMPLE, sep="\t", usecols=["smiles"], dtype=str)
    unique = sorted(set(df.smiles) | set(corpus["smiles"]))
    assert len(unique) == 287809 and all(isinstance(x, str) and x for x in unique)
    index_by_smiles = {s: i for i, s in enumerate(unique)}
    tsv(ROOT / "unique_input_strings.tsv", ["structure_index", "smiles"],
        ({"structure_index": i, "smiles": s} for i, s in enumerate(unique)))
    tsv(ROOT / "historical_query_keys.tsv", ["raw_inchikey14"],
        ({"raw_inchikey14": key} for key in sorted(history)))
    tsv(ROOT / "prior_selection_keys.tsv", ["raw_inchikey14"],
        ({"raw_inchikey14": key} for key in sorted(prior)))
    summary.update(public_spectra=len(df), own_public_structures=len(corpus["keys"]),
                   unique_exact_strings=len(unique), historical_raw_keys=len(history),
                   prior_selection_raw_keys=len(prior), schema_audit_raw_rows=len(audited))
    print(json.dumps(summary, sort_keys=True), flush=True)
    records = {}
    pool = mp.get_context("spawn").Pool(args.workers, initializer=worker_init)
    finished = False
    try:
        with (ROOT / "canonical_progress.tsv").open("x", newline="") as stream:
            writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
            writer.writerow(["structure_index", "group_id", "heavy_composition", "canonical_inchikey14", "status"])
            results = pool.imap_unordered(canonicalize, enumerate(unique), chunksize=1)
            while len(records) < len(unique) and time.monotonic() < deadline:
                try:
                    result = results.next(timeout=min(5, max(0.01, deadline - time.monotonic())))
                except mp.TimeoutError:
                    continue
                index = result[0]
                assert index not in records
                records[index] = result
                writer.writerow(result)
                if len(records) % 5000 == 0:
                    stream.flush()
                    print("canonicalized", len(records), "of", len(unique), "elapsed", round(time.monotonic()-start, 2), flush=True)
            finished = len(records) == len(unique)
    finally:
        if finished:
            pool.close()
        else:
            pool.terminate()
        pool.join()
    valid = sum(record[-1] == "valid" for record in records.values())
    fields = ["structure_index", "smiles", "group_id", "heavy_composition", "canonical_inchikey14", "status"]
    tsv(ROOT / "canonical_structures.tsv", fields,
        ({"structure_index": i, "smiles": unique[i], "group_id": r[1], "heavy_composition": r[2],
          "canonical_inchikey14": r[3], "status": r[4]} for i, r in sorted(records.items())))
    summary.update(canonical_processed=len(records), canonical_valid=valid,
        canonical_coverage_complete=finished, canonical_valid_complete=finished and valid == len(unique),
        canonical_elapsed_seconds=time.monotonic()-start)
    if not summary["canonical_valid_complete"]:
        summary["decision"] = "INCOMPLETE_NO_PARTITION"
    else:
        gid_for = {s: records[i][1] for s, i in index_by_smiles.items()}
        group_info = {}
        for record in records.values():
            _, gid, comp, ik, _ = record
            if gid in group_info:
                assert group_info[gid] == (comp, ik)
            group_info[gid] = (comp, ik)
        own_groups = [gid_for[s] for s in corpus["smiles"]]
        historical_groups = {g for k, g in zip(corpus["keys"], own_groups) if k in history}
        prior_groups = {g for k, g in zip(corpus["keys"], own_groups) if k in prior}
        old_optimizer_groups = {g for k, g in zip(corpus["keys"], own_groups) if k not in prior}
        schema_groups = {gid_for[s] for s in audited.smiles}
        msg_groups = [gid_for[s] for s in df.smiles]
        msg_counts = Counter(msg_groups)
        own_counts = Counter(own_groups)
        roles = {g: assign_role(g, g in historical_groups, g in prior_groups) for g in group_info}
        assert not any(roles[g][0] != "optimizer" for g in historical_groups)
        assert not any(roles[g][0] == "final_test" for g in prior_groups)
        partition_sets = {r: {g for g in group_info if roles[g][0] == r} for r in ROLES}
        assert sum(map(len, partition_sets.values())) == len(group_info)
        for i, role in enumerate(ROLES):
            for other in ROLES[i+1:]:
                assert not partition_sets[role] & partition_sets[other]
        group_fields = ["group_id", "heavy_composition", "canonical_inchikey14", "partition", "assignment_reason", "hash_bucket",
                        "historical819", "prior_selection2750", "old_optimizer_exposed", "schema_audit256", "msg_spectrum_count", "own_structure_count"]
        tsv(ROOT / "group_partitions.tsv", group_fields,
            ({"group_id": g, "heavy_composition": group_info[g][0], "canonical_inchikey14": group_info[g][1],
              "partition": roles[g][0], "assignment_reason": roles[g][1], "hash_bucket": roles[g][2],
              "historical819": g in historical_groups, "prior_selection2750": g in prior_groups,
              "old_optimizer_exposed": g in old_optimizer_groups,
              "schema_audit256": g in schema_groups, "msg_spectrum_count": msg_counts[g],
              "own_structure_count": own_counts[g]} for g in sorted(group_info)))
        assignments = df.assign(group_id=msg_groups)
        assignments["partition"] = assignments.group_id.map(lambda g: roles[g][0])
        assignments = assignments.rename(columns={"fold": "original_msg_fold"})
        assignments.sort_values("identifier").to_csv(ROOT / "msg_spectrum_partitions.tsv", sep="\t", index=False, mode="x", lineterminator="\n")
        own_rows = [{"corpus_structure_index": i, "raw_inchikey14": key, "group_id": gid,
                     "partition": roles[gid][0], "observed_spectrum_reference_allowed": roles[gid][0] == "optimizer"}
                    for i, (key, gid) in enumerate(zip(corpus["keys"], own_groups))]
        own_fields = list(own_rows[0])
        tsv(ROOT / "own_corpus_partitions.tsv", own_fields, own_rows)
        excluded = [row for row in own_rows if not row["observed_spectrum_reference_allowed"]]
        tsv(ROOT / "retrieval_reference_exclusions.tsv", own_fields, excluded)
        msg_excluded = assignments[assignments.partition != "optimizer"]
        msg_excluded[["identifier", "group_id", "partition"]].sort_values("identifier").to_csv(
            ROOT / "msg_reference_exclusions.tsv", sep="\t", index=False, mode="x", lineterminator="\n")
        assert not {r["group_id"] for r in own_rows if r["observed_spectrum_reference_allowed"]} & set(msg_excluded.group_id)
        summary.update(decision="COMPLETE_PROPOSAL_ONLY", metric_groups=len(group_info),
            group_role_counts={r: len(partition_sets[r]) for r in ROLES},
            msg_spectrum_role_counts=assignments.partition.value_counts().to_dict(),
            msg_group_role_counts=assignments.drop_duplicates("group_id").partition.value_counts().to_dict(),
            own_structure_role_counts=dict(Counter(row["partition"] for row in own_rows)),
            historical_metric_groups=len(historical_groups), prior_selection_metric_groups=len(prior_groups),
            schema_audit_metric_groups=len(schema_groups),
            schema_audit_final_groups=len(schema_groups & partition_sets["final_test"]),
            old_optimizer_exposed_final_groups=len(old_optimizer_groups & partition_sets["final_test"]),
            own_retrieval_excluded_structures=len(excluded), msg_retrieval_excluded_spectra=len(msg_excluded),
            pairwise_partition_overlap_groups=0, historical_final_overlap_groups=0,
            prior_selection_final_overlap_groups=0)
    summary["finished_utc"] = datetime.now(timezone.utc).isoformat()
    summary["elapsed_seconds"] = time.monotonic()-start
    with (ROOT / "summary.txt").open("x") as stream:
        for k, v in summary.items():
            stream.write(k + ": " + json.dumps(v, sort_keys=True) + "\n")
    save_hashes()
    print(json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
