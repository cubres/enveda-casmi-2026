"""Inert source-only bridge for the pinned Enveda mounted assets.

The resolver performs the byte checks. This bridge retains the CID build-map
lineage, binds companion reads, and changes only two original IO expressions.
It does not import models, read experiment labels, or start compute on import.
"""
from pathlib import Path
import json


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def qualify_mounts(resolver, input_root, bindings, original_pins, lineage):
    require(set(bindings) == set(original_pins) - {"cid.npy"}
            and len(bindings) == 18, "exact18 mounted asset contract")
    qualified, receipts = {}, {}
    for name, binding in bindings.items():
        require(binding["relative_filename"] == name
                and binding["expected_sha256"] == original_pins[name],
                "original mounted byte pin preserved: " + name)
        result = resolver.resolve_mapped_file(input_root, binding["owner"], binding["slug"],
            name, binding["expected_size"], binding["expected_sha256"])
        qualified[name] = result.path
        receipts[name] = dict(result.receipt, dataset_version_pin=binding["version"])

    # Original loaders read sibling files via the selected anchor's directory.
    # Resolve each sibling privately and prove it is the preflight-qualified file.
    families = {
        "coconut": ("coco_fp.npy", "coco_mass.npy", "coco_meta.pkl", "fp_bits.npy"),
        "massindex": ("mass_sorted.npy", "order.npy", "off.npy", "len.npy", "smiles.txt"),
        "popularity": ("ap2pop_manifest.json", "ap2pop_ik14.npy", "ap2pop_ik14_sid.npy",
            "ap2pop_ik14_pmid.npy", "ap2pop_store_sid.npy", "ap2pop_store_pmid.npy"),
        "fingerprint_weights": ("fp_merged_m1.pt", "fp_single_s2.pt"),
    }
    for family, names in families.items():
        parent = qualified[names[0]].parent
        try:
            coherent = all(qualified[name].parent == parent
                and (parent / name).resolve(strict=True) == qualified[name]
                and qualified[name].name == name for name in names)
        except (OSError, RuntimeError):
            coherent = False
        require(coherent, "qualified companion path coherence: " + family)

    require(type(lineage["expected_size"]) is int and 0 <= lineage["expected_size"] <= 4096,
            "bounded lineage metadata size")
    provenance = resolver.resolve_mapped_file(input_root, lineage["owner"], lineage["slug"],
        lineage["relative_filename"], lineage["expected_size"], lineage["expected_sha256"])
    try:
        with provenance.path.open("rb") as stream:
            raw = stream.read(4097)
    except OSError:
        raise RuntimeError("bounded lineage metadata unreadable") from None
    require(len(raw) == lineage["expected_size"] and len(raw) <= 4096,
            "exact bounded lineage metadata")
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise RuntimeError("lineage metadata JSON/UTF8 contract") from None
    require(type(body) is dict and type(body.get("store_alignment_source")) is dict,
            "lineage metadata object contract")
    store = body["store_alignment_source"]
    require(store.get("dataset") == "prvsiyan/pubchem-npformula-massindex"
            and type(store.get("version")) is int and store["version"] == 1
            and store.get("cid_map") == "cid.npy (local only, not part of that dataset)"
            and type(store.get("sha256")) is dict
            and store["sha256"].get("cid.npy") == original_pins["cid.npy"],
            "builder-only CID lineage exact dataset/version/hash contract")
    for name in ("len.npy", "off.npy", "order.npy"):
        require(store["sha256"].get(name) == original_pins[name],
                "published store alignment lineage: " + name)
    lineage_receipt = dict(provenance.receipt, dataset_version_pin=lineage["version"],
        cid_source_class="LOCAL_BUILDER_ONLY_NO_MOUNT", cid_mounted=False,
        cid_lineage_sha256=original_pins["cid.npy"],
        store_alignment_dataset=store["dataset"], store_alignment_version=store["version"],
        cid_map=store["cid_map"], actual_native_global_cid_count_observed=False)
    return qualified, dict(status="PASS_SCOPED_MOUNTED_18_AND_CID_BUILDER_LINEAGE",
        mounted_file_count=18, full_byte_pins={name:original_pins[name] for name in bindings},
        file_receipts=receipts, lineage_receipt=lineage_receipt,
        companion_families={name:list(files) for name,files in families.items()},
        actual_runtime_loader_binding_pending=True, official_score=None)


def bind_known_find(original_find, qualified):
    def mapped_find(name):
        if name in qualified:
            return str(qualified[name])
        # Competition test/TRAIN selection remains the original BANK4 behavior;
        # its same-run TRAIN source hash is retained. BIO and forward stay OFF.
        return original_find(name)
    return mapped_find


IO_SITES = {
    19: ("glob.glob('/kaggle/input/**/fp_*.pt', recursive=True)",
         "_DIAGNOSTIC_QUALIFIED_FP_PATHS"),
    20: ("glob.glob('/kaggle/input/**/mass_sorted.npy', recursive=True)",
         "_DIAGNOSTIC_QUALIFIED_MASS_PATHS"),
}


def transform_io_binding(index, source):
    if index not in IO_SITES:
        return source
    original, replacement = IO_SITES[index]
    require(source.count(original) == 1, "exact one original IO site: " + str(index))
    result = source.replace(original, replacement)
    require(result.count(replacement) == 1, "exact one qualified IO site: " + str(index))
    return result
