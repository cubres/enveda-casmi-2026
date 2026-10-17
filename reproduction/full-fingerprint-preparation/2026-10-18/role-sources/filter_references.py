"""Authenticate the public corpus and materialize an optimizer-only index view.

This is original data preparation, with no model loading, predictions, or metric
evaluation. Source files are never modified. Each output is created exclusively.
"""
import csv
import hashlib
import json
import os
import pickle
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
PARTITION = WORKSPACE / "research/enveda_glacier_partition_20260930T165020Z"
CORPUS = Path("/Users/cubres/Documents/Clauding/casmi_work")
PARTITION_MANIFEST_SHA = "13930be94d0122a9de70f9dc9cae7f995a1a6f2d9c2c68e60d853306b3ed6ae6"
ROLES = ("optimizer", "checkpoint_selection", "fusion_selection", "final_test")
PINS = {
    "up_train/spec.npz": "99dbf966d2607e2da8085a6550206a71fc912d2c90b9555a725a2569e4af4500",
    "up_train/fp_meta.pkl": "d6ad0dd33bf66e92c5a85054b7f914b4ac538fc4b06c4aabca8d0df9f985b85b",
    "data/struct_fp_meta.pkl": "c2362f52eea6847b367e5b7be6cfe9769c4eae847764c7fb53e230d743f77b57",
    "data/train_meta.parquet": "69fc67b2974fc6fe651930eede166a2bb0aee76e55faab1fafe2203f5dbadff0",
    "build_dataset.py": "ec90d3d9ef3ec9b1e45d2dc9e2e766439ef7431cce8f8388ccb96b0be96a517b",
}
ARRAY_PINS = {
    "six": "7cc28caec1063dc85cc7f330430f3c7ccfda7b88ecf0dc5fe6786aa720e037da",
    "src": "6254dc793da71daa8160becb5a1e6171fdd06e341c0528b93a93bf4dae5390a4",
    "is_val": "fc48d61132c26236c79293ab7068b0809d18ece0c8c5e35924d428830f70cc80",
}
PROTOCOL = """Optimizer-only observed-spectrum reference view, proposal v1.
Require the independently pinned partition artifacts.tsv, all fourteen artifact
hashes/sizes, and COMPLETE_PROPOSAL_ONLY with complete canonical coverage.
Authenticate the whole public spec.npz archive and prior six/src/is_val array
hashes. Independently verify every six -> structure key equals the public
train_meta.parquet key at src. Structure metadata key/SMILES order must agree.
Assign every spectrum the official-equivalence group role of its structure.
Retain only optimizer spectra in original ascending archive row order. Exclude
checkpoint_selection, fusion_selection and final_test spectra, including every
alternative raw structure in their canonical group. The retained arrays are an
applied index view over the immutable archive, not a copied peak collection.
For a retained row j: original archive row = optimizer_spectrum_indices[j],
original public source row = optimizer_source_indices[j], structure index =
optimizer_structure_indices[j]. Read mz/it through original off[row:row+2].
Consumers must authenticate the output manifest and source archive before use;
they must use the filtered index view for every observed-spectrum retrieval.
Additional reference libraries need equivalent grouping and exclusion first.
The separate blind candidate proposal is the complete pre-existing public
structure catalogue, deduplicated by the already authenticated official group.
Choose the first original catalogue index per group; preserve that index order.
Pool construction reads structure identity only: no role, query identity, target,
prediction, score, or coverage result controls membership or representative.
Held molecules remain eligible generic candidates. No known answer is inserted
for a query. The public catalogue itself originates in public training data;
this is not a claim that its molecular identities are label-free or exhaustive.
No MassSpecGym query structure is appended merely because it is a query truth.
Future queries may filter this frozen pool only by observable acquisition data
under a separately frozen rule; no such per-query candidate selection occurs now.
No model executes and no performance is evaluated. Fresh fitting of every
learned component remains required by the preceding partition protocol.
"""


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_summary(path):
    return {key: json.loads(value) for key, value in
            (line.rstrip("\n").split(": ", 1) for line in Path(path).open())}


def authenticate_partition():
    manifest = PARTITION / "artifacts.tsv"
    require(sha256(manifest) == PARTITION_MANIFEST_SHA, "partition manifest hash mismatch")
    rows = list(csv.DictReader(manifest.open(), delimiter="\t"))
    require(len(rows) == 14 and len({r["name"] for r in rows}) == 14, "partition manifest coverage")
    for row in rows:
        require(Path(row["name"]).name == row["name"], "unsafe manifest path")
        p = PARTITION / row["name"]
        require(p.stat().st_size == int(row["bytes"]) and sha256(p) == row["sha256"],
                "partition artifact mismatch: " + row["name"])
    summary = read_summary(PARTITION / "summary.txt")
    validate_complete(summary)
    return rows


def validate_complete(summary):
    require(summary.get("decision") == "COMPLETE_PROPOSAL_ONLY", "partition not complete proposal")
    require(summary.get("canonical_coverage_complete") is True and
            summary.get("canonical_valid_complete") is True, "partial canonical coverage")
    require(type(summary.get("unique_exact_strings")) is int and summary["unique_exact_strings"] > 0,
            "missing or invalid canonical input count")
    require(summary.get("canonical_processed") == summary.get("unique_exact_strings") and
            summary.get("canonical_valid") == summary.get("unique_exact_strings"), "partial canonical counts")


def validate_mapping(six, src, keys, library_keys):
    require(six.ndim == src.ndim == 1 and len(six) == len(src), "mapping shape mismatch")
    require(six.dtype.kind in "iu" and src.dtype.kind in "iu", "mapping must be integral")
    require(len(six) > 0 and six.min() >= 0 and six.max() < len(keys), "structure mapping out of range")
    require(src.min() >= 0 and src.max() < len(library_keys), "source mapping out of range")
    require(np.all(np.diff(src) > 0), "source rows not unique ascending")
    require(np.array_equal(np.asarray(keys)[six], np.asarray(library_keys)[src]), "public source key join mismatch")


def reference_indices(six, structure_roles, structure_groups):
    roles = np.asarray(structure_roles)
    groups = np.asarray(structure_groups)
    require(roles.shape == groups.shape and roles.ndim == 1, "structure annotation shape")
    require(six.ndim == 1 and six.dtype.kind in "iu" and len(six) > 0 and
            six.min() >= 0 and six.max() < len(roles), "invalid spectrum structure index")
    require(set(roles.tolist()) <= set(ROLES), "unknown role")
    group_roles = {}
    for group, role in zip(groups, roles):
        require(group_roles.setdefault(group, role) == role, "canonical aliases span roles")
    codes = np.array([ROLES.index(role) for role in roles], dtype=np.uint8)
    spectrum_codes = codes[six]
    selected = np.flatnonzero(spectrum_codes == 0).astype(np.int64)
    rejected = np.flatnonzero(spectrum_codes != 0).astype(np.int64)
    allowed_groups = set(groups[np.unique(six[selected])])
    held_groups = {g for g, role in group_roles.items() if role != "optimizer"}
    require(not allowed_groups & held_groups, "held canonical group in references")
    require(len(selected) + len(rejected) == len(six), "incomplete spectrum filter")
    return selected, rejected, spectrum_codes


def candidate_representatives(structure_groups):
    """Membership depends solely on the fixed public catalogue's group order."""
    seen = set()
    result = []
    for index, group in enumerate(structure_groups):
        if group not in seen:
            seen.add(group)
            result.append(index)
    return result


def write_tsv(path, fields, rows):
    with Path(path).open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def save_array(name, values):
    with (ROOT / name).open("xb") as stream:
        np.save(stream, values, allow_pickle=False)


def main():
    start = time.monotonic()
    require(os.getpriority(os.PRIO_PROCESS, 0) >= 5, "requires nice >= 5")
    summary = {"started_utc": datetime.now(timezone.utc).isoformat(),
               "source_sha256": sha256(__file__), "workers": 1,
               "nice": os.getpriority(os.PRIO_PROCESS, 0), "seconds_cap": 900,
               "model_execution": False, "performance_evaluation": False}
    partition_manifest = authenticate_partition()
    inputs = [{"path": str(PARTITION / "artifacts.tsv"),
               "bytes": (PARTITION / "artifacts.tsv").stat().st_size, "sha256": PARTITION_MANIFEST_SHA}]
    for relative, expected in PINS.items():
        p = CORPUS / relative
        require(sha256(p) == expected, "corpus source mismatch: " + relative)
        inputs.append({"path": str(p), "bytes": p.stat().st_size, "sha256": expected})
    # Load only these exact authenticated, locally produced public data pickles.
    with (CORPUS / "up_train/fp_meta.pkl").open("rb") as stream:
        catalogue = pickle.load(stream)
    with (CORPUS / "data/struct_fp_meta.pkl").open("rb") as stream:
        original = pickle.load(stream)
    require(catalogue["keys"] == original["keys"] and catalogue["smiles"] == original["smiles"],
            "original and training catalogue order differs")
    require(len(catalogue["keys"]) == len(set(catalogue["keys"])) == 275810, "catalogue size/uniqueness")
    summary["metadata_nbits_original"] = original["nbits"]
    summary["metadata_nbits_training"] = catalogue["nbits"]
    library = pq.read_table(CORPUS / "data/train_meta.parquet", columns=["inchikey14", "ingest_lib"]).to_pandas()
    with np.load(CORPUS / "up_train/spec.npz", allow_pickle=False) as archive:
        six, src, is_val = (archive[name] for name in ("six", "src", "is_val"))
    for name, array in (("six", six), ("src", src), ("is_val", is_val)):
        require(hashlib.sha256(array.tobytes()).hexdigest() == ARRAY_PINS[name], "prior array pin mismatch: " + name)
    validate_mapping(six, src, catalogue["keys"], library.inchikey14.to_numpy())
    own = pd.read_csv(PARTITION / "own_corpus_partitions.tsv", sep="\t", dtype=str, keep_default_na=False)
    groups = pd.read_csv(PARTITION / "group_partitions.tsv", sep="\t", dtype=str, keep_default_na=False)
    canonical = pd.read_csv(PARTITION / "canonical_structures.tsv", sep="\t", dtype=str, keep_default_na=False)
    require(own.corpus_structure_index.astype(int).tolist() == list(range(len(catalogue["keys"]))), "partition index order")
    require(own.raw_inchikey14.tolist() == catalogue["keys"], "partition key order")
    canonical_map = dict(zip(canonical.smiles, canonical.group_id))
    require(own.group_id.tolist() == [canonical_map[s] for s in catalogue["smiles"]], "canonical membership mismatch")
    group_role_map = dict(zip(groups.group_id, groups.partition))
    require(own.partition.tolist() == [group_role_map[g] for g in own.group_id], "group role mismatch")
    require(own.observed_spectrum_reference_allowed.tolist() == [str(r == "optimizer") for r in own.partition],
            "reference eligibility mismatch")
    selected, rejected, spectrum_codes = reference_indices(six, own.partition, own.group_id)
    expected_excluded = pd.read_csv(PARTITION / "retrieval_reference_exclusions.tsv", sep="\t", dtype=str)
    require(expected_excluded.corpus_structure_index.astype(int).tolist() ==
            np.flatnonzero(own.partition.to_numpy() != "optimizer").tolist(), "structure exclusions differ")
    require(time.monotonic() - start < 840, "insufficient time remaining; no final artifacts")
    (ROOT / "protocol.txt").open("x").write(PROTOCOL)
    write_tsv(ROOT / "inputs.tsv", ["path", "bytes", "sha256"], inputs)
    write_tsv(ROOT / "array_authentication.tsv", ["name", "dtype", "shape", "raw_bytes_sha256"],
              ({"name": n, "dtype": str(a.dtype), "shape": str(a.shape), "raw_bytes_sha256": ARRAY_PINS[n]}
               for n, a in (("six", six), ("src", src), ("is_val", is_val))))
    save_array("optimizer_spectrum_indices.npy", selected)
    save_array("optimizer_source_indices.npy", src[selected])
    save_array("optimizer_structure_indices.npy", six[selected])
    save_array("excluded_spectrum_indices.npy", rejected)
    save_array("spectrum_role_codes.npy", spectrum_codes)
    role_counts = []
    group_array = own.group_id.to_numpy()
    for code, role in enumerate(ROLES):
        mask = spectrum_codes == code
        observed = np.unique(six[mask])
        role_counts.append({"role_code": code, "role": role, "spectra": int(mask.sum()),
             "catalogue_structures": int((own.partition == role).sum()), "observed_structures": len(observed),
             "observed_metric_groups": len(set(group_array[observed])),
             "historical_is_val_spectra": int(is_val[mask].sum())})
    write_tsv(ROOT / "role_counts.tsv", list(role_counts[0]), role_counts)
    library_names = library.ingest_lib.to_numpy()[src]
    library_counts = Counter(zip(library_names.tolist(), spectrum_codes.tolist()))
    write_tsv(ROOT / "library_role_counts.tsv", ["source_library", "role", "spectra"],
              ({"source_library": lib, "role": ROLES[code], "spectra": count}
               for (lib, code), count in sorted(library_counts.items())))
    aliases = Counter(group_array)
    held_alias_groups = {g for g, n in aliases.items() if n > 1 and group_role_map[g] != "optimizer"}
    held_alias_structures = np.array([g in held_alias_groups for g in group_array])
    require(not held_alias_structures[six[selected]].any(), "held alias retained")
    representatives = candidate_representatives(group_array)
    write_tsv(ROOT / "blind_candidate_pool.tsv", ["candidate_index", "corpus_structure_index", "raw_inchikey14", "smiles", "metric_group_id"],
              ({"candidate_index": j, "corpus_structure_index": i, "raw_inchikey14": catalogue["keys"][i],
                "smiles": catalogue["smiles"][i], "metric_group_id": group_array[i]}
               for j, i in enumerate(representatives)))
    observed_optimizer = np.unique(six[selected])
    write_tsv(ROOT / "optimizer_observed_structures.tsv", ["corpus_structure_index", "raw_inchikey14", "metric_group_id"],
              ({"corpus_structure_index": i, "raw_inchikey14": catalogue["keys"][i], "metric_group_id": group_array[i]}
               for i in observed_optimizer))
    # Read back every emitted index array before declaring a complete view.
    checks = {"optimizer_spectrum_indices.npy": selected, "optimizer_source_indices.npy": src[selected],
              "optimizer_structure_indices.npy": six[selected], "excluded_spectrum_indices.npy": rejected,
              "spectrum_role_codes.npy": spectrum_codes}
    for name, expected in checks.items():
        require(np.array_equal(np.load(ROOT / name, allow_pickle=False), expected), "array roundtrip mismatch")
    summary.update(decision="COMPLETE_FILTERED_REFERENCE_VIEW_PROPOSAL_ONLY", partition_artifacts_verified=len(partition_manifest),
         public_source_spectra=len(library), archive_spectra=len(six), exact_source_key_joins=len(six),
         catalogue_structures=len(catalogue["keys"]), retained_spectra=len(selected), excluded_spectra=len(rejected),
         retained_observed_structures=len(observed_optimizer), retained_metric_groups=len(set(group_array[observed_optimizer])),
         held_metric_groups_in_references=0, held_alias_groups_excluded=len(held_alias_groups),
         held_alias_structures_excluded=int(held_alias_structures.sum()),
         held_alias_spectra_excluded=int(held_alias_structures[six].sum()),
         blind_candidate_metric_groups=len(representatives), source_identity_authenticated=True,
         array_roundtrip_checks=len(checks), finished_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic()-start)
    require(summary["elapsed_seconds"] < 900, "wall budget exceeded; no complete receipt")
    with (ROOT / "summary.txt").open("x") as stream:
        for key, value in summary.items():
            stream.write(key + ": " + json.dumps(value, sort_keys=True) + "\n")
    files = sorted(p for p in ROOT.iterdir() if p.is_file() and p.name not in {"artifacts.tsv", "run.log"})
    write_tsv(ROOT / "artifacts.tsv", ["name", "bytes", "sha256"],
              ({"name": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in files))
    print(json.dumps(summary, sort_keys=True), flush=True)
    print("artifact_manifest_sha256", sha256(ROOT / "artifacts.tsv"), flush=True)


if __name__ == "__main__":
    main()
