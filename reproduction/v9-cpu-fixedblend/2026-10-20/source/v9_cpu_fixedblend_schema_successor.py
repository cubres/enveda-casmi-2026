"""Fixed NEW-held-set V9 CPU comparison; root-owned once execution only.

Apache-2.0. Credits: cubres CASMI FPNet/training preprocessing, exact selected
V6 serving neutral_mass, and public metric_distinct.py. No competitor outputs,
truth candidate insertion, optimizer, V6 forward, old assay, or alpha search.
SOURCE ONLY until the separately reviewed outer supervisor admits this file.
"""
import argparse
import ast
import collections
import hashlib
import importlib.util
import json
import math
import os
import pickle
import platform
import signal
import sys
import time
from pathlib import Path

N, BITS, GIB = 2653, 10395, 1 << 30
THREAD_ENV = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")
ARTIFACTS = ("raw_logits.npy", "completion_bitmap.npy", "ranked_group_ids.npy",
             "window_bounds.npy", "canary_indices.npy", "per_query_rr.npy", "group_rr.npy")
START = time.monotonic()
PEAK_RSS = 0


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    path = Path(path)
    need(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)), "REGULAR_NONLINK_FILE_REQUIRED")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            h.update(block)
    return {"bytes": path.stat().st_size, "sha256": h.hexdigest()}


def write_new(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(Path(path).parent)


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def sync_files(paths):
    for path in paths:
        with Path(path).open("rb") as stream:
            os.fsync(stream.fileno())
    sync_directory(Path(paths[0]).parent)


def bind_files(contract):
    result = {}
    for name, record in contract["files"].items():
        actual = digest(record["path"])
        need(actual == {k: record[k] for k in ("bytes", "sha256")}, "INPUT_BYTE_DRIFT:" + name)
        result[name] = actual
    return result


def budget():
    global PEAK_RSS
    import psutil
    rss = psutil.Process().memory_info().rss
    PEAK_RSS = max(PEAK_RSS, rss)
    need(rss < 6 * GIB, "CPU_RSS_CAP")
    need(time.monotonic() - START < 880, "CHILD_880_SECONDS_CAP")


def alarm(signum, frame):
    raise TimeoutError("CHILD_880_SECONDS_CAP")


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def neutral_converter(path):
    text = Path(path).read_text()
    nodes = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "neutral_mass"]
    need(len(nodes) == 1, "EXACT_NEUTRAL_FUNCTION")
    fragment = ast.get_source_segment(text, nodes[0])
    need(hashlib.sha256(fragment.encode()).hexdigest() == "72b0d5ee12defa38f7044f9d00266cf5aee78a7b4d14521db8de7c5cd1bad9f8", "EXACT_NEUTRAL_AST")
    ns = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<exact-public-neutral-mass>", "exec"), ns)
    return ns["neutral_mass"]


def window(np, sorted_mass, observed):
    # The query is observed precursor/adduct arithmetic, NEVER pool/truth mass.
    if not math.isfinite(observed) or observed <= 0:
        return (0, 0, 0, 1)
    for ppm in (10, 30):
        radius = observed * ppm * 1e-6
        lo = int(np.searchsorted(sorted_mass, observed - radius, side="left"))
        hi = int(np.searchsorted(sorted_mass, observed + radius, side="right"))
        if hi > lo:
            return (lo, hi, ppm, 3 if hi - lo > 4096 else 0)
    return (0, 0, 30, 2)


def group_id(key):
    if key is None:
        return ""
    counts, ik14 = key
    return hashlib.sha256(json.dumps([list(counts), ik14], separators=(",", ":")).encode()).hexdigest()


def blind_canary(np, peak_counts, bounds):
    """Unlabelled stress coverage, fixed64: long peaks, dense windows, random."""
    ids = np.arange(N, dtype=np.int64)
    count = np.where(bounds[:, 3] == 0, bounds[:, 1] - bounds[:, 0], 0)
    selected = []
    for order in (np.lexsort((ids, -peak_counts)), np.lexsort((ids, -count))):
        for i in order[:16]:
            if int(i) not in selected:
                selected.append(int(i))
    for i in np.random.default_rng(20261020).permutation(N):
        if int(i) not in selected:
            selected.append(int(i))
        if len(selected) == 64:
            break
    need(len(selected) == len(set(selected)) == 64, "FIXED64_BLIND_CANARY")
    return np.asarray(selected, dtype=np.int64)


def model_cpu(torch, fpmodel, checkpoint_path):
    unsafe = set(torch.serialization.get_unsafe_globals_in_checkpoint(checkpoint_path))
    need(unsafe <= {"torch.torch_version.TorchVersion"}, "UNAPPROVED_CHECKPOINT_GLOBAL")
    from torch.torch_version import TorchVersion
    with torch.serialization.safe_globals([TorchVersion]):
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True, mmap=True)
    need(set(checkpoint) == {"model", "step", "nbits", "d", "layers", "seed", "split", "treatment", "parent_checkpoint_sha256", "validation"}, "EXACT_V9_TOP_KEYS")
    for name, expected in {"step": 3000, "nbits": BITS, "d": 512, "layers": 8, "seed": 20261019,
                           "validation": None, "treatment": "50% metadata-compatible merged spectra",
                           "parent_checkpoint_sha256": "9c46ca4fcf19002fecbcded0d0808e8a81e3a25a143e684e259f265c44a5be31"}.items():
        need(type(checkpoint[name]) is type(expected) and checkpoint[name] == expected, "EXACT_V9_METADATA:" + name)
    model = fpmodel.FPNet(BITS, d=512, layers=8).to(device="cpu", dtype=torch.float32)
    state, expected = checkpoint["model"], model.state_dict()
    need(len(state) == len(expected) == 111 and set(state) == set(expected), "ALL111_STATE_KEYS")
    for name, value in state.items():
        need(type(value) is torch.Tensor and value.device.type == "cpu" and value.dtype == torch.float32
             and value.layout is torch.strided and value.shape == expected[name].shape
             and bool(torch.isfinite(value).all()), "EXACT_FINITE_CPU_STATE")
        budget()
    need(len(list(model.parameters())) == 108 and sum(p.numel() for p in model.parameters()) == 49424027, "EXACT108_MODEL_PARAMETERS")
    model.load_state_dict(state, strict=True)
    # Pinned checkpoint buffers are authoritative across Torch2.10 ->2.8;
    # constructor transcendental rounding is not a second scientific input.
    for name in ("mz_emb.inv", "nl_emb.inv", "prec_emb.inv"):
        need(tuple(state[name].shape) == (256,) and torch.equal(model.state_dict()[name], state[name]), "EXACT_RESTORED_SINUSOID_BUFFERS")
    model.eval()
    need(all(p.device.type == "cpu" and p.dtype == torch.float32 for p in model.parameters()), "CPU_FP32_PARAMETERS")
    return model, sorted(unsafe)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = Path(args.output)
    need(out.is_absolute() and not out.exists() and not any(p.is_symlink() for p in out.parents), "FRESH_ABSOLUTE_OUTPUT_ONLY")
    out.mkdir(mode=0o700)
    sync_directory(out.parent)
    write_new(out / "ATTEMPT_CONSUMED.json", {"status": "CONSUMED_NO_RETRY", "source_sha256": digest(__file__)["sha256"]})
    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, max(.001, 880 - (time.monotonic() - START)))
    for key in THREAD_ENV:
        need(os.environ.get(key) == "2", "TWO_CPU_THREAD_ENV_REQUIRED")
    need(os.environ.get("CUDA_VISIBLE_DEVICES") == "" and os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") == "0", "CPU_ONLY_ENV_REQUIRED")
    contract_bytes = Path(args.contract).read_bytes()
    contract = json.loads(contract_bytes)
    before = bind_files(contract)
    write_new(out / "INPUT_BYTES_BEFORE.json", before)
    budget()
    import numpy as np
    import torch
    import rdkit
    from threadpoolctl import threadpool_limits, threadpool_info
    need(np.__version__ == "2.2.6" and str(torch.__version__) == "2.8.0" and rdkit.__version__ == "2026.03.3", "EXACT_MAC_RUNTIME")
    need(platform.machine() == "arm64" and sys.platform == "darwin", "EXPLICIT_MAC_CPU_EXPERIMENT")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    thread_limit = threadpool_limits(limits=2)
    need(torch.get_num_threads() == 2 and torch.get_num_interop_threads() == 1 and all(v.get("num_threads", 0) <= 2 for v in threadpool_info()), "CPU_LIBRARY_THREAD_CAP")
    paths = {k: Path(v["path"]) for k, v in contract["files"].items()}
    fpmodel = module(paths["fpmodel"], "casmi_owned_fpmodel_cpu")
    helper = module(paths["input_helper"], "casmi_inputs_only_cpu")
    metric = module(paths["metric_source"], "casmi_pinned_metric_cpu")
    neutral = neutral_converter(paths["mass_source"])
    load = lambda key: np.load(paths[key], mmap_mode="r", allow_pickle=False)
    cache_rows, spectra, trainer = [load(key) for key in ("eligible_cache_rows", "eligible_spectrum_indices", "eligible_trainer_indices")]
    need(all(a.shape == (N,) and a.dtype == np.int64 for a in (cache_rows, spectra, trainer)), "FROZEN_NEW_QUERY_SCHEMA")
    need(len(np.unique(cache_rows)) == N and np.all((cache_rows >= 0) & (cache_rows < 13579)), "FROZEN_CACHE_ROW_RANGE")
    v7_spectra, v7_trainer, completion = [load(key) for key in ("v7_spectra", "v7_structures", "v7_completion")]
    need(np.array_equal(spectra, v7_spectra[cache_rows]) and np.array_equal(trainer, v7_trainer[cache_rows])
         and completion.shape == (13579,) and bool(np.all(completion)), "EXACT_PUBLIC_V7_QUERY_JOINS")
    logits6 = load("v7_logits")
    need(logits6.shape == (13579, BITS) and logits6.dtype == np.float32, "V7_RAW_FP32_CONTROL")
    bits, bits7 = load("fp_bits"), load("v7_fp_bits")
    need(bits.shape == (BITS,) and np.array_equal(bits, bits7), "EXACT_PUBLIC_FP_COLUMN_ORDER")
    with np.load(paths["spec"], allow_pickle=False) as archive:
        spec = {name: archive[name] for name in helper.INPUT_NAMES}
    helper.metadata_header_guard(np, spec, paths["spec_header_receipt"])
    pool_mass, packed = load("pool_mass"), load("pool_fp")
    need(pool_mass.shape == (711705,) and pool_mass.dtype == np.float64 and np.isfinite(pool_mass).all()
         and np.all(pool_mass[1:] >= pool_mass[:-1]) and np.all((pool_mass >= 80) & (pool_mass <= 1400)), "EXACT_SORTED_PUBLIC_POOL")
    need(packed.shape == (711705, 1300) and packed.dtype == np.uint8 and np.all((packed[:, -1] & 31) == 0), "MSB10395_ZERO_PADDING")
    bounds = np.asarray([window(np, pool_mass, neutral({"precursor_mz": float(spec["prec"][i]),
                          "adduct": fpmodel.ADDUCT_LIST[int(spec["ad"][i])] if 0 <= int(spec["ad"][i]) < len(fpmodel.ADDUCT_LIST) else "<unk>"})) for i in spectra], dtype=np.int64)
    counts = np.where(bounds[:, 3] == 0, bounds[:, 1] - bounds[:, 0], 0)
    need(int(counts.sum()) <= 2000000, "FROZEN_ALL_CANDIDATE_ROW_CAP")
    np.save(out / "window_bounds.npy", bounds, allow_pickle=False)
    peaks = np.minimum(spec["off"][spectra + 1] - spec["off"][spectra], 128)
    canary = blind_canary(np, peaks, bounds)
    np.save(out / "canary_indices.npy", canary, allow_pickle=False)
    # Exact-byte-owned primitive metadata only. No labels, truth FP or targets.
    with paths["pool_meta"].open("rb") as f:
        pool_meta = pickle.load(f)
    with paths["fp_meta"].open("rb") as f:
        structure_meta = pickle.load(f)
    # Exact actual 53c276a6 public pool schema, independently inspected with
    # the finite symbolic pickle grammar before this successor was admitted.
    # src/npl stay unused by ranking; their values remain bound by whole-file SHA.
    need(type(pool_meta) is dict and set(pool_meta) == {"keys", "smiles", "src", "npl", "nbits"}
         and type(pool_meta["nbits"]) is int and pool_meta["nbits"] == BITS, "EXACT_POOL_METADATA_KEYS")
    for name, dtype in (("keys", np.dtype("O")), ("smiles", np.dtype("O")),
                        ("src", np.dtype("i1")), ("npl", np.dtype("<f8"))):
        value = pool_meta[name]
        need(type(value) is np.ndarray and value.shape == (711705,) and value.dtype == dtype
             and value.flags.c_contiguous, "EXACT_POOL_METADATA_FIELD_SCHEMA")
    need(type(structure_meta) is dict and set(structure_meta) == {"keys", "smiles", "nbits"}
         and type(structure_meta["nbits"]) is int and structure_meta["nbits"] == BITS
         and type(structure_meta["keys"]) is list and type(structure_meta["smiles"]) is list
         and len(structure_meta["keys"]) == len(structure_meta["smiles"]) == 275810, "EXACT_STRUCTURE_METADATA")
    role_indices, role_groups = load("role01_indices"), load("role01_groups")
    need(role_indices.shape == role_groups.shape == (246674,) and role_indices.dtype == np.int64
         and role_groups.dtype.kind in "US" and np.all((role_indices >= 0) & (role_indices < 275810)), "PUBLIC_ROLE01_GROUP_CACHE")
    identities = {}
    for i, g in zip(role_indices, role_groups):
        smi, group = structure_meta["smiles"][int(i)], str(g)
        need(isinstance(smi, str) and len(group) == 64 and (smi not in identities or identities[smi] == group), "CANONICAL_CACHE_JOIN")
        identities[smi] = group
    # Prediction group identities can speed compaction; no target matching yet.
    def identity(pool_i):
        smi = pool_meta["smiles"][int(pool_i)]
        need(isinstance(smi, str), "POOL_SMILES_STRING")
        if smi not in identities:
            identities[smi] = group_id(metric.equivalence_key(smi))
        return identities[smi]
    model, unsafe = model_cpu(torch, fpmodel, paths["v9_checkpoint"])
    raw = np.lib.format.open_memmap(out / "raw_logits.npy", mode="w+", dtype=np.float32, shape=(N, BITS))
    done = np.lib.format.open_memmap(out / "completion_bitmap.npy", mode="w+", dtype=np.bool_, shape=(N,))
    ranked = np.lib.format.open_memmap(out / "ranked_group_ids.npy", mode="w+", dtype="U64", shape=(N, 2, 25))
    done[:] = False
    ranked[:] = ""
    ties = np.zeros((N, 2), dtype=np.int64)
    def forward(rows):
        budget()
        inp = helper.cpu_inputs(np, torch, spec, spectra[rows])
        with torch.inference_mode():
            prediction = model(*inp)
        need(prediction.device.type == "cpu" and prediction.dtype == torch.float32 and tuple(prediction.shape) == (len(rows), BITS)
             and bool(torch.isfinite(prediction).all()), "FINITE_NEW_V9_RAW_CPU_FP32")
        raw[rows] = prediction.numpy()
        done[rows] = True
        budget()
        return prediction
    def rank_rows(rows):
        for row in rows:
            budget()
            lo, hi, ppm, status = map(int, bounds[row])
            control = np.asarray(logits6[cache_rows[row]], dtype=np.float64)
            novel = np.asarray(raw[row], dtype=np.float64)
            need(np.isfinite(control).all() and np.isfinite(novel).all(), "FINITE_BOTH_ARM_LOGITS")
            if status:
                continue
            pool_ids = np.arange(lo, hi, dtype=np.int64)
            features = np.stack((control, .9 * control + .1 * novel), axis=1)
            scores = np.empty((hi - lo, 2), dtype=np.float64)
            for start in range(0, len(pool_ids), 128):
                selected = pool_ids[start:start + 128]
                unpacked = np.unpackbits(packed[selected], axis=1, count=BITS, bitorder="big").astype(np.float64)
                scores[start:start + len(selected)] = (unpacked @ features) / math.sqrt(BITS)
                budget()
            need(np.isfinite(scores).all(), "FINITE_FIXED_ARM_SCORES")
            for arm in range(2):
                order = np.lexsort((pool_ids, -scores[:, arm]))
                ordered = scores[order, arm]
                ties[row, arm] = np.count_nonzero(ordered[1:] == ordered[:-1])
                seen, selected = set(), []
                for pool_i in pool_ids[order]:
                    g = identity(pool_i)
                    if g and g not in seen:
                        seen.add(g)
                        selected.append(g)
                    if len(selected) == 25:
                        break
                ranked[row, arm, :len(selected)] = selected
    # No quality labels/MRR read by this canary. Repeat the same CPU model batch
    # only for numeric reproducibility; full run reuses first persisted output.
    canary_start = time.monotonic()
    reference_paths = {k: paths[k] for k in ("fpmodel", "train_fp4", "train_full_fingerprint")}
    helper.assert_prefix_parity(np, torch, spec, spectra[canary], reference_paths)
    first = forward(canary).clone()
    with torch.inference_mode():
        repeated = model(*helper.cpu_inputs(np, torch, spec, spectra[canary]))
    need(torch.allclose(first, repeated, rtol=.001, atol=.003), "FROZEN_REPEAT_TOLERANCE")
    need(bool(torch.isfinite(repeated).all()), "FINITE_REPEAT")
    rank_rows(canary)
    for arr in (raw, done, ranked):
        arr.flush()
    reread = np.load(out / "raw_logits.npy", mmap_mode="r", allow_pickle=False)
    need(np.array_equal(reread[canary], first.numpy()) and bool(np.all(done[canary])), "CANARY_FP32_DISK_EXACT")
    measured = time.monotonic() - canary_start
    elapsed = time.monotonic() - START
    forecast = elapsed + 3 * measured * (N - 64) / 64 + 180
    gate = forecast <= 850 and elapsed < 850 and PEAK_RSS < 6 * GIB
    write_new(out / "CPU_CANARY.json", {"status": "PASS" if gate else "STOPPED_FORECAST", "rows": 64,
        "labels_or_MRR_read": False, "prefix_parity": True, "finite": True, "repeat_rtol": .001,
        "repeat_atol": .003, "fp32_disk_exact": True, "measured_seconds": measured,
        "elapsed_seconds": elapsed, "forecast_total_seconds": forecast, "forecast_multiplier": 3,
        "IO_reserve_seconds": 180, "forecast_limit_seconds": 850, "gate": gate,
        "peak_rss_bytes": PEAK_RSS, "canary_reused_without_restart": True})
    need(gate, "FIXED64_CPU_FORECAST_GATE")
    remaining = np.flatnonzero(~done)
    for start in range(0, len(remaining), 64):
        rows = remaining[start:start + 64]
        forward(rows)
        rank_rows(rows)
    for arr in (raw, done, ranked):
        arr.flush()
    need(bool(np.all(done)) and np.isfinite(raw).all(), "COMPLETE_FINITE_NEW_PREDICTIONS")
    sync_files([out / name for name in ARTIFACTS[:5]])
    prediction_artifacts = {name: digest(out / name) for name in ARTIFACTS[:5]}
    write_new(out / "FROZEN_PREDICTIONS_MANIFEST.json", {"status": "FROZEN_BEFORE_TARGET_MATCHING",
        "rows": N, "raw_logits_shape": [N, BITS], "full_completion": True,
        "weights": [.9, .1], "candidate_windows_use_observed_precursor_adduct": True,
        "all_predictions_and_ranks_frozen_before_target_matching": True, "artifacts": prediction_artifacts})
    # First target matching occurs strictly after all model outputs/ranks frozen.
    truth = load("eligible_groups")
    need(truth.shape == (N,) and truth.dtype.kind in "US" and len(np.unique(truth)) == 2650, "FROZEN_NEW2650_TARGET_GROUPS")
    rr = np.zeros((N, 2), dtype=np.float64)
    for row in range(N):
        for arm in range(2):
            hits = np.flatnonzero(ranked[row, arm] == truth[row])
            if len(hits):
                rr[row, arm] = 1. / (int(hits[0]) + 1)
    unique, inverse = np.unique(truth, return_inverse=True)
    grr = np.zeros((len(unique), 2), dtype=np.float64)
    group_counts = np.bincount(inverse)
    for arm in range(2):
        grr[:, arm] = np.bincount(inverse, weights=rr[:, arm]) / group_counts
    delta = grr[:, 1] - grr[:, 0]
    rng = np.random.default_rng(20261020)
    bootstrap = np.empty(2000, dtype=np.float64)
    for i in range(2000):
        bootstrap[i] = delta[rng.integers(len(delta), size=len(delta))].mean()
        if i % 100 == 0:
            budget()
    np.save(out / "per_query_rr.npy", rr, allow_pickle=False)
    np.save(out / "group_rr.npy", grr, allow_pickle=False)
    sync_files([out / name for name in ARTIFACTS[5:]])
    need({name: digest(out / name) for name in ARTIFACTS[:5]} == prediction_artifacts, "FROZEN_PREDICTIONS_UNCHANGED_AFTER_MATCHING")
    after = bind_files(contract)
    need(after == before and Path(args.contract).read_bytes() == contract_bytes, "FINAL_ALL_INPUT_SOURCE_BYTE_RECHECK")
    write_new(out / "INPUT_BYTES_AFTER.json", after)
    budget()
    final = {"status": "COMPLETE_NEW_V9_FIXED_BLEND_CPU_MEASUREMENT", "source_sha256": digest(__file__)["sha256"],
        "input_bytes_unchanged_before_after": True, "rows": N, "groups": 2650, "raw_logits_shape": [N, BITS],
        "full_completion": True, "official_score": None, "weights": [.9, .1], "assay_repeated": False,
        "V6_forward_calls": 0, "role2_or3_forward_calls": 0, "optimizer_steps": 0,
        "unconditional_query_MRR25": rr.mean(axis=0).tolist(), "canonical_group_MRR25": grr.mean(axis=0).tolist(),
        "canonical_group_delta": float(delta.mean()), "bootstrap_repetitions": 2000,
        "bootstrap_group_delta_95pct": np.quantile(bootstrap, [.025, .975]).tolist(),
        "window_status_counts": {str(k): int(v) for k, v in collections.Counter(bounds[:, 3].tolist()).items()},
        "empty_or_rejected_window_policy": "RR0 retained in all2653 denominator; no fallback/truth insertion/truncation",
        "candidate_rows": int(counts.sum()), "score_ties": ties.sum(axis=0).tolist(),
        "unsafe_checkpoint_globals": unsafe,
        "precision_confound": "CUDAFP16-autocast V6 cache vs CPUFP32 V9; joint model/backend change, not isolated training ablation",
        "native_serving_qualified": False, "seconds": time.monotonic() - START, "peak_rss_bytes": PEAK_RSS,
        "device": "cpu", "numpy": np.__version__, "torch": str(torch.__version__), "rdkit": rdkit.__version__,
        "threads": 2, "artifacts": {name: digest(out / name) for name in ARTIFACTS}}
    write_new(out / "FINAL_EXPERIMENT_RECEIPT.json", final)
    signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == "__main__":
    main()
