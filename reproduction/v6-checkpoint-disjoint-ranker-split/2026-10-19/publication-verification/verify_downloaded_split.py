"""Verify the actual public CASMI V1 split download using NumPy only.

Uploader-authored Apache-2.0. No network, model, optimizer, spectrum, prediction
or score computation is performed. Exact public molecular metadata is trusted
only after its full SHA256 matches. Output JSON is exclusively created.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, re, zlib
from datetime import datetime, timezone
from pathlib import Path

DATASET_ID = 12716429
REF = "prvsiyan/casmi26-v6-checkpoint-disjoint-ranker-split"
PUBLIC_URL = "https://www.kaggle.com/datasets/" + REF + "/versions/1"
MANIFEST_SHA = "daf59ed830f9a8a0525d88b923f5296850a12f24e317b02aa1b22fe3cc34858a"
REBUILD_SOURCE_SHA = "0f5099865aee7c9c5179cd9ec943bf45b7cfdf9f8f4952c77efb3e609ccf7b9e"
META_SHA = "88411e98cec6f862f7b121dbc27b807e5e18782416219fe2b11566deb3254132"
ROLE_FILE_SHA = "fe654a3f5f655df3897a344ca222e01a9f555a7dfd22a786e6cb32b126c76049"
ROLE_ARRAY_SHA = "4d7b366293225a1ae67dfc0306480129b9ac1351a6d8581f0be40a269bdaff86"
SALT = "casmi-v6-role1odd-ranker-group-v1-20261019"
EIGHT = {"all_cache_exclusion_reason.npy", "cache_query_rows.npy", "canonical_group_ids.npy",
         "role01_canonical_group_ids.npy", "role01_trainer_structure_indices.npy",
         "split_buckets.npy", "split_train0_development1.npy", "trainer_structure_indices.npy"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text())


def verify(args):
    import numpy as np
    import pickle
    root = args.dataset_directory
    require(digest(root / "RELEASE_MANIFEST.json") == MANIFEST_SHA, "Exact public V1 manifest")
    manifest = load_json(root / "RELEASE_MANIFEST.json")
    expected = dict(manifest["files"])
    expected["RELEASE_MANIFEST.json"] = {"bytes": (root / "RELEASE_MANIFEST.json").stat().st_size, "sha256": MANIFEST_SHA}
    require(len(expected) == 26 and sum(v["bytes"] for v in expected.values()) == 71960601, "Exact V1 inventory count and total")
    actual = {}
    for name, binding in sorted(expected.items()):
        require(Path(name).name == name and not name.lower().endswith((".zip", ".tar", ".ipynb")), "Flat, non-archive, non-notebook payload")
        path = root / name
        require(path.is_file() and not path.is_symlink(), "Regular payload file: " + name)
        actual[name] = {"bytes": path.stat().st_size, "sha256": digest(path)}
        require(actual[name] == binding, "Actual downloaded file differs: " + name)
    require(manifest["identity"]["id"] == REF, "Exact dataset identity")
    arrays = {p.name: np.load(p, mmap_mode="r", allow_pickle=False) for p in sorted(root.glob("*.npy"))}
    require(len(arrays) == 10, "Ten downloaded NumPy arrays")
    schema = load_json(root / "DATA_SCHEMA.json")["arrays"]
    require(set(schema) == set(arrays), "Complete array schema")
    for name, a in arrays.items():
        require(str(a.dtype) == schema[name]["dtype"] and list(a.shape) == schema[name]["shape"], "Actual array schema: " + name)
    require(digest(args.public_bank_directory / "fp_meta.pkl") == META_SHA, "Public V1 fp_meta hash before trusted pickle")
    require(digest(args.public_bank_directory / "roles_by_structure.b64") == ROLE_FILE_SHA, "Public V1 encoded roles hash")
    with (args.public_bank_directory / "fp_meta.pkl").open("rb") as stream:
        metadata = pickle.load(stream)
    require(len(metadata["keys"]) == len(metadata["smiles"]) == 275810 and metadata["nbits"] == 10395, "Exact public metadata dimensions")
    packed = np.frombuffer(zlib.decompress(base64.b64decode((args.public_bank_directory / "roles_by_structure.b64").read_text().strip())), np.uint8)
    bits = np.unpackbits(packed)[:2 * len(metadata["keys"])].reshape(-1, 2)
    roles = (2 * bits[:, 0] + bits[:, 1]).astype(np.uint8)
    require(hashlib.sha256(roles.tobytes()).hexdigest() == ROLE_ARRAY_SHA, "Decoded role array hash")
    raw = arrays["structure_indices.npy"]
    raw_keys = arrays["structure_keys.npy"]
    universe = arrays["role01_trainer_structure_indices.npy"]
    universe_groups = arrays["role01_canonical_group_ids.npy"]
    require(np.array_equal(universe, np.flatnonzero(roles <= 1)), "Complete role0/1 exclusion universe")
    require(np.all(roles[raw] == 1) and np.all(raw % 2 == 1) and np.all(np.diff(raw) > 0), "Raw cache role1-odd order")
    require(np.array_equal(raw_keys, np.asarray(metadata["keys"])[raw]), "Every original cache key joins public V1 metadata")
    require(all(re.fullmatch("[0-9a-f]{64}", str(g)) for g in universe_groups), "Canonical group digest representation")
    groups_by_index = {int(i): str(g) for i, g in zip(universe, universe_groups)}
    optimizer = {str(g) for i, g in zip(universe, universe_groups) if roles[int(i)] == 0}
    checkpoint = {str(g) for i, g in zip(universe, universe_groups) if roles[int(i)] == 1 and int(i) % 2 == 0}
    raw_groups = [groups_by_index[int(i)] for i in raw]
    reasons = ["optimizer_and_checkpoint_overlap" if g in optimizer and g in checkpoint else
               "optimizer_overlap" if g in optimizer else "checkpoint_overlap" if g in checkpoint else "survives" for g in raw_groups]
    require(np.array_equal(arrays["all_cache_exclusion_reason.npy"], reasons), "Every actual downloaded exclusion reconstructed")
    expected_rows = np.asarray([i for i, reason in enumerate(reasons) if reason == "survives"], np.int64)
    rows = arrays["cache_query_rows.npy"]
    require(np.array_equal(rows, expected_rows), "Exact retained original cache rows")
    require(np.array_equal(arrays["trainer_structure_indices.npy"], raw[rows]), "Retained structure-index join")
    groups = arrays["canonical_group_ids.npy"]
    require(np.array_equal(groups, np.asarray(raw_groups)[rows]), "Retained group join")
    buckets = np.asarray([int.from_bytes(hashlib.sha256((SALT + ":" + str(g)).encode()).digest()[:8], "big") % 10000 for g in groups], np.int16)
    split = np.where(buckets < 8000, 0, 1).astype(np.uint8)
    require(np.array_equal(buckets, arrays["split_buckets.npy"]) and np.array_equal(split, arrays["split_train0_development1.npy"]), "Every frozen hash bucket and split reconstructed")
    train_groups, development_groups = set(groups[split == 0]), set(groups[split == 1])
    require(not train_groups & development_groups and not set(groups) & optimizer and not set(groups) & checkpoint, "Zero canonical overlap")
    counts = {"cached_queries": len(raw), "retained_queries": len(rows), "retained_groups": len(set(groups)),
              "training_queries": int((split == 0).sum()), "training_groups": len(train_groups),
              "development_queries": int((split == 1).sum()), "development_groups": len(development_groups),
              "excluded_checkpoint_overlapping_queries": reasons.count("checkpoint_overlap"),
              "excluded_optimizer_overlapping_queries": reasons.count("optimizer_overlap") + reasons.count("optimizer_and_checkpoint_overlap")}
    require(counts == {"cached_queries": 13579, "retained_queries": 13512, "retained_groups": 13478,
                       "training_queries": 10859, "training_groups": 10828, "development_queries": 2653,
                       "development_groups": 2650, "excluded_checkpoint_overlapping_queries": 67,
                       "excluded_optimizer_overlapping_queries": 0}, "All numeric counts")
    full_proof = load_json(root / "FULL_REBUILD_RECEIPT_PUBLIC.json")
    require(full_proof["status"] == "COMPLETE_METADATA_GROUP_AUDIT" and full_proof["actual_process_exit_code"] == 0 and
            full_proof["source_sha256"] == REBUILD_SOURCE_SHA and set(full_proof["outputs"]) == EIGHT, "Completed portable full rebuild proof")
    require(full_proof["seconds"] <= 1800 and full_proof["environment"]["rdkit"] == "2026.03.3", "Actual resource and metric version proof")
    rebuilt = {}
    if args.rebuilt_directory:
        for name in sorted(EIGHT):
            path = args.rebuilt_directory / name
            require({"bytes": path.stat().st_size, "sha256": digest(path)} == actual[name], "Fresh rebuilt bytes equal actual public download: " + name)
            a = np.load(path, mmap_mode="r", allow_pickle=False)
            require(a.dtype == arrays[name].dtype and np.array_equal(a, arrays[name]), "Fresh rebuilt numeric parity: " + name)
            rebuilt[name] = actual[name]
    result = {"schema": "casmi-public-split-publication-verification/1", "status": "PASS_ACTUAL_PUBLIC_V1_FILES_AND_NUMERIC_JOINS",
              "observed_utc": datetime.now(timezone.utc).isoformat(),
              "dataset": {"id": DATASET_ID, "ref": REF, "version": 1, "url": PUBLIC_URL},
              "published_files": actual, "published_file_count": 26, "published_payload_bytes": 71960601,
              "numeric_counts": counts, "canonical_group_overlap": {"train_development": 0, "survivor_optimizer": 0, "survivor_checkpoint_even": 0},
              "public_bank_inputs": {"ref": "prvsiyan/casmi26-full-fingerprint-inputs", "version": 1,
                 "fp_meta_sha256": META_SHA, "encoded_roles_sha256": ROLE_FILE_SHA, "decoded_roles_sha256": ROLE_ARRAY_SHA},
              "portable_full_rebuild": {"source_sha256": REBUILD_SOURCE_SHA, "public_proof_sha256": actual["FULL_REBUILD_RECEIPT_PUBLIC.json"]["sha256"],
                 "seconds": full_proof["seconds"], "environment": full_proof["environment"], "limits": full_proof["limits"],
                 "all_eight_fresh_local_arrays_compared_to_actual_public_files": len(rebuilt) == 8,
                 "fresh_local_array_hashes": rebuilt},
              "scope": {"verifier_network_access": False, "notebook_or_dataset_mutation": False,
                 "model_weights_or_logits_or_spectra_or_fingerprints_loaded": False,
                 "role2_role3_queries_loaded": False, "model_or_ranker_training": False,
                 "prediction_evaluation_or_previous_assay_repeated": False, "official_score_claimed": False},
              "verification_source_sha256": digest(Path(__file__)), "blockers": []}
    if args.acquisition_receipt:
        acquisition = load_json(args.acquisition_receipt)
        require(acquisition["status"] == "PASS_ANONYMOUS_PUBLIC_V1_ALL_26_RAW_FILES_EXACT" and acquisition["request_authentication"] is None and
                acquisition["dataset_id"] == DATASET_ID and acquisition["ref"] == REF and acquisition["version"] == 1 and
                acquisition["inventory"] == actual and acquisition["public_before_after"] is True and acquisition["create_or_upload_performed"] is False,
                "Exact anonymous public acquisition receipt")
        result["anonymous_public_acquisition"] = {"receipt_sha256": digest(args.acquisition_receipt), "request_authentication": None,
            "files": 26, "bytes": acquisition["total_payload_bytes"], "seconds": acquisition["seconds"],
            "started_utc": acquisition["started_utc"], "finished_utc": acquisition["finished_utc"],
            "public_before_after_observed": True, "license_name": acquisition["license_name"], "creation_or_upload_repeated": False}
    if args.metadata_observation:
        observation = load_json(args.metadata_observation); data = observation["metadata"]
        require(observation["request_authentication"] is None and observation["status_code"] == 200 and
                data["id"] == DATASET_ID and data["ref"] == REF and data["currentVersionNumber"] == 1 and data["isPrivate"] is False and
                data["totalBytes"] == 71960601 and data["ownerRef"] == "prvsiyan" and data["title"] == manifest["identity"]["title"],
                "Accepted public V1 anonymous metadata")
        require(data["description"] == (root / "README.md").read_text(), "Actual public description exactly matches frozen README")
        result["anonymous_metadata"] = {"observation_sha256": digest(args.metadata_observation), "observed_utc": observation["observed_utc"],
            "http_status": 200, "request_authentication": None, "id": data["id"], "ref": data["ref"], "version": data["currentVersionNumber"],
            "is_private": False, "owner": data["ownerRef"], "title": data["title"], "license_name": data["licenseName"],
            "total_payload_bytes": data["totalBytes"], "description_matches_frozen_readme_exactly": True}
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False); stream.write("\n")
    print(json.dumps({"status": result["status"], "dataset_id": DATASET_ID, "version": 1,
                      "files": 26, "bytes": 71960601, "numeric_counts": counts,
                      "all_eight_public_vs_fresh_rebuild_exact": len(rebuilt) == 8}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_directory", type=Path)
    parser.add_argument("--public-bank-directory", type=Path, required=True)
    parser.add_argument("--rebuilt-directory", type=Path)
    parser.add_argument("--acquisition-receipt", type=Path)
    parser.add_argument("--metadata-observation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args())

if __name__ == "__main__":
    main()
