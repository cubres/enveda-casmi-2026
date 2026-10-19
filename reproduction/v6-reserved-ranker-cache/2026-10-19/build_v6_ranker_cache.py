"""Produce a NEW, fully bound CASMI ranker-training cache. Never submits or trains.

Uploader-authored source: Apache-2.0. Data/model permissions remain scoped by
the exact public V1 inputs. This does not reconstruct the historical rank cache.
Scientific imports and data/model reads happen only inside main().
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time
import traceback

SCHEMA = "casmi-v6-reserved-ranker-logits/1"
FEATURE_VERSION = "v6-step28000-single-view-raw-logits-f32-v1"
SEED = 20261019
CANARY_ROWS = 64
NBITS = 10395
WALL_SECONDS = 1800
MAX_RSS_BYTES = 20 * (1 << 30)
MAX_GPU_BYTES = 13 * (1 << 30)
MAX_OUTPUT_BYTES = 3 * (1 << 30)
CHECKPOINT = (197739081, "9c46ca4fcf19002fecbcded0d0808e8a81e3a25a143e684e259f265c44a5be31")
MANIFEST_SHA = "5b08ca4b830de1558be4ce568a10f0997b5fa2fe875a872dcd6a216f901fd9ef"
SPEC = (920788910, "99dbf966d2607e2da8085a6550206a71fc912d2c90b9555a725a2569e4af4500")
ROLE_SHA = "4d7b366293225a1ae67dfc0306480129b9ac1351a6d8581f0be40a269bdaff86"
SOURCES = {
    "fpmodel.py": "69f2656778a08233e22235bf4853f0b3d2420b431390a32d6c8ed453cde85c76",
    "train_fp4.py": "1daa2532ef186600c21fc96fa6a16e1729084b4e7257524a0dc33fc2adc7abb0",
    "structure_uniform_sampler.py": "d2edd84f6db5d0d9138b6576ccda94b6f322e04424fe7c2c2db448f045421ea6",
    "train_full_fingerprint.py": "df609595b23b37fa475b480057275dcc22b753ae4159726bc7ddff5442980a0e",
}
PUBLIC_INPUTS = {
    "spectra": "prvsiyan/casmi26-spec-fp/versions/1",
    "bank": "prvsiyan/casmi26-full-fingerprint-inputs/versions/1",
    "checkpoint": "prvsiyan/casmi26-v6-structure-uniform-checkpoint/versions/1",
}


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def bound_file(path, expected):
    size, sha = expected
    if not path.is_file() or path.stat().st_size != size or digest(path) != sha:
        raise ValueError("Exact input binding failed: " + path.name)
    return {"bytes": size, "sha256": sha}


def write_json(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def rss_bytes():
    native = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(native if sys.platform == "darwin" else native * 1024)


def eligible_queries(np, six, roles, s2p):
    """First cached spectrum per eligible odd trainer structure, in index order."""
    six = np.asarray(six)
    roles = np.asarray(roles)
    s2p = np.asarray(s2p)
    if six.ndim != 1 or roles.ndim != 1 or s2p.shape != roles.shape:
        raise ValueError("Invalid role/join dimensions")
    if np.any((six < 0) | (six >= len(roles))):
        raise ValueError("Invalid spectrum-to-structure join")
    valid = np.flatnonzero((roles[six] == 1) & (six % 2 == 1) & (s2p[six] >= 0))
    structures, first = np.unique(six[valid], return_index=True)
    spectra = valid[first]
    if not len(spectra) or not np.all(roles[structures] == 1) or not np.all(structures % 2 == 1):
        raise ValueError("Reserved ranker query selection failed")
    if not np.array_equal(six[spectra], structures):
        raise ValueError("First-spectrum query join failed")
    return structures.astype(np.int64), spectra.astype(np.int64)


def canary_indices(np, data, spectrum_ids):
    """Deterministic mixed rows, including peak-count extremes and metadata modes."""
    if len(spectrum_ids) < CANARY_ROWS:
        raise ValueError("At least 64 reserved ranker structures required")
    lengths = data.off[spectrum_ids + 1] - data.off[spectrum_ids]
    selected = {int(np.argmin(lengths)), int(np.argmax(lengths))}
    # Metadata coverage is a numerical preprocessing check, not a quality assay.
    triples = np.column_stack([data.mode[spectrum_ids], data.ad[spectrum_ids], data.ins[spectrum_ids]])
    _, first = np.unique(triples, axis=0, return_index=True)
    if len(first) > CANARY_ROWS - len(selected):
        first = first[np.linspace(0, len(first) - 1, CANARY_ROWS - len(selected), dtype=np.int64)]
    selected.update(map(int, first))
    rng = np.random.default_rng(SEED)
    for value in rng.permutation(len(spectrum_ids)):
        if len(selected) >= CANARY_ROWS:
            break
        selected.add(int(value))
    return np.asarray(sorted(selected), dtype=np.int64)


def assert_output_arrays(np, arrays):
    count = len(arrays["structure_indices"])
    if arrays["query_logits"].shape != (count, NBITS) or arrays["query_logits"].dtype != np.float32:
        raise ValueError("Logit shape/precision contract failed")
    if not np.isfinite(arrays["query_logits"]).all():
        raise ValueError("Nonfinite cached logits")
    for name in ("spectrum_indices", "source_rows", "positive_pool_indices", "structure_keys"):
        if len(arrays[name]) != count:
            raise ValueError("Query alignment failed: " + name)
    if len(np.unique(arrays["structure_indices"])) != count:
        raise ValueError("Duplicate query structures")
    if not np.all(np.diff(arrays["structure_indices"]) > 0) or not np.all(arrays["structure_indices"] % 2 == 1):
        raise ValueError("Reserved odd structure order failed")
    if len(np.unique(arrays["structure_keys"])) != count:
        raise ValueError("Duplicate structure keys")
    if arrays["truth_fp_packed"].shape != (count, (NBITS + 7) // 8):
        raise ValueError("Packed target shape failed")
    if arrays["truth_fp_packed"].dtype != np.uint8 or arrays["fp_bit_indices"].shape != (NBITS,):
        raise ValueError("Fingerprint target/order contract failed")
    if not np.all(np.diff(arrays["fp_bit_indices"]) > 0) or not np.all((arrays["fp_bit_indices"] >= 0) & (arrays["fp_bit_indices"] < 10407)):
        raise ValueError("Original fingerprint-column definition failed")
    for name in ("structure_indices", "spectrum_indices", "source_rows", "positive_pool_indices"):
        if arrays[name].dtype != np.int64 or np.any(arrays[name] < 0):
            raise ValueError("Numeric join type/range failed: " + name)
    if arrays["completion_bitmap"].dtype != np.bool_ or not np.all(arrays["completion_bitmap"]):
        raise ValueError("Incomplete prediction bitmap")


def run(args):
    started = time.monotonic()
    args.out.mkdir(parents=True, exist_ok=False)
    phase = "input_binding"
    receipt = {"schema": SCHEMA, "feature_version": FEATURE_VERSION, "status": "STARTED",
               "official_score": None, "model_training_performed": False, "completed_assay_repeated": False,
               "role2_or_role3_queries_used": False, "seed": SEED,
               "builder_sha256": digest(Path(__file__)), "public_inputs": PUBLIC_INPUTS,
               "limits": {"wall_seconds": WALL_SECONDS, "native_rss_bytes": MAX_RSS_BYTES,
                          "torch_allocated_gpu_bytes": MAX_GPU_BYTES, "output_bytes": MAX_OUTPUT_BYTES}}

    def budget():
        elapsed = time.monotonic() - started
        if elapsed > WALL_SECONDS or rss_bytes() >= MAX_RSS_BYTES:
            raise RuntimeError("Wall/native RSS budget exceeded; preserve partial outputs")
        return elapsed

    try:
        if digest(args.bank / "FULL_FINGERPRINT_MANIFEST.json") != MANIFEST_SHA:
            raise ValueError("Original public bank manifest drifted")
        manifest = json.loads((args.bank / "FULL_FINGERPRINT_MANIFEST.json").read_text())
        bank_binding = {}
        for name, entry in manifest["input_files"].items():
            if Path(name).name != name:
                raise ValueError("Manifest file names must be flat")
            bank_binding[name] = bound_file(args.bank / name, (entry["bytes"], entry["sha256"]))
            budget()
        receipt["bindings"] = {"bank_manifest_sha256": MANIFEST_SHA, "bank_files": bank_binding,
                               "spectra": bound_file(args.spec, SPEC),
                               "checkpoint": bound_file(args.checkpoint / "best_full_model.pt", CHECKPOINT)}
        for name, sha in SOURCES.items():
            if digest(args.checkpoint / name) != sha:
                raise ValueError("Original source mismatch: " + name)
        receipt["source_sha256"] = SOURCES
        budget()
        phase = "model_and_reserved_query_load"
        # Restrict to one worker. Provider-wide allocation must still be charged.
        os.environ["CUDA_VISIBLE_DEVICES"] = "0"
        import numpy as np
        import torch
        torch.set_num_threads(2)
        if not torch.cuda.is_available():
            raise RuntimeError("Scheduled CUDA device required")
        torch.manual_seed(SEED)
        np.random.seed(SEED)
        sys.path.insert(0, str(args.checkpoint.resolve()))
        from train_full_fingerprint import FullData
        from fpmodel import FPNet
        for name, sha in SOURCES.items():
            module = sys.modules.get(Path(name).stem)
            if module is None or Path(module.__file__).resolve() != (args.checkpoint / name).resolve() or digest(Path(module.__file__)) != sha:
                raise ValueError("Imported module is not the verified original source: " + name)
        receipt["environment"] = {"python": platform.python_version(), "numpy": np.__version__,
                                  "torch": torch.__version__, "cuda": torch.version.cuda,
                                  "device": torch.cuda.get_device_name(0), "used_devices": 1,
                                  "provider_allocation": "root records whole actual allocation separately",
                                  "precision": "FP32 model and inputs; CUDA FP16 autocast; raw logits saved as FP32",
                                  "num_threads": torch.get_num_threads()}
        data = FullData(args.bank, "cuda", args.spec)
        if hashlib.sha256(data.roles.tobytes()).hexdigest() != ROLE_SHA:
            raise ValueError("Decoded public role binding drifted")
        structures, spectra = eligible_queries(np, data.six, data.roles, data.s2p)
        if not np.all(data.roles[data.six[data.tr]] == 0):
            raise ValueError("Original optimizer-query source no longer role0 only")
        canary = canary_indices(np, data, spectra)
        weights = torch.load(args.checkpoint / "best_full_model.pt", map_location="cpu", weights_only=True)
        if tuple(weights.get(k) for k in ("nbits", "d", "layers", "step", "seed")) != (NBITS, 512, 8, 28000, 20261003):
            raise ValueError("Selected V6 checkpoint metadata mismatch")
        model = FPNet(NBITS, d=512, layers=8).cuda()
        model.load_state_dict(weights["model"], strict=True)
        del weights
        model.eval()
        packed = np.load(args.bank / "pool_fp.npy", mmap_mode="r", allow_pickle=False)
        positives = data.s2p[structures].astype(np.int64)
        with np.load(args.spec, allow_pickle=False) as original:
            source_rows = original["src"][spectra].astype(np.int64)
        arrays = {
            "structure_indices": structures, "spectrum_indices": spectra, "source_rows": source_rows,
            "positive_pool_indices": positives, "structure_keys": np.asarray([data.skeys[i] for i in structures], dtype=str),
            "fp_bit_indices": np.load(args.bank / "fp_bits.npy", allow_pickle=False),
            "truth_fp_packed": np.asarray(packed[positives], dtype=np.uint8),
        }
        estimated_output = len(spectra) * NBITS * 4 * 2 + arrays["truth_fp_packed"].nbytes * 2
        if estimated_output > MAX_OUTPUT_BYTES:
            raise RuntimeError("Projected numeric+NPZ outputs exceed preserved-output budget")
        arrays["query_logits"] = np.lib.format.open_memmap(args.out / "query_logits.npy", mode="w+", dtype=np.float32, shape=(len(spectra), NBITS))
        arrays["completion_bitmap"] = np.lib.format.open_memmap(args.out / "completion_bitmap.npy", mode="w+", dtype=np.bool_, shape=(len(spectra),))
        arrays["completion_bitmap"][:] = False
        receipt["split"] = {"query_role": 1, "query_trainer_structure_index_parity": "odd",
                            "representative": "lowest original cached spectrum index per eligible structure",
                            "queries": len(spectra), "optimizer_query_role": 0,
                            "checkpoint_selection_role": "role1 even; may share metric-equivalence groups with role1 odd",
                            "canonical_group_overlap_audited": False,
                            "qualification": "reserved raw-structure queries excluded from V6 optimizer; not claimed clean group OOF",
                            "ranker_fit_performed": False,
                            "reason_no_ranker_fit": "group-disjoint ranker train/validation audit is not in these public input artifacts"}

        def predict(query_rows):
            inputs, _, _ = data.batch(spectra[query_rows], K=0, rng=None, aug=False, merge_p=0.)
            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16):
                logits = model(*inputs)
            torch.cuda.synchronize()
            value = logits.float().cpu().numpy()
            if value.shape != (len(query_rows), NBITS) or not np.isfinite(value).all():
                raise RuntimeError("Invalid model output; preserve partial cache")
            if torch.cuda.max_memory_allocated() >= MAX_GPU_BYTES:
                raise RuntimeError("Torch GPU allocation budget exceeded")
            budget()
            return value

        phase = "64_query_canary"
        # Same tensor shapes on repetition isolate model/preprocessor repeatability.
        measured = time.monotonic()
        output = predict(canary)
        repeat = predict(canary)
        max_abs = float(np.max(np.abs(output - repeat)))
        if not np.allclose(output, repeat, rtol=0.001, atol=0.003):
            raise RuntimeError("Same-batch canary predictions are not stable within frozen tolerance")
        canary_seconds = time.monotonic() - measured
        arrays["query_logits"][canary] = output
        arrays["completion_bitmap"][canary] = True
        arrays["query_logits"].flush()
        arrays["completion_bitmap"].flush()
        reloaded = np.load(args.out / "query_logits.npy", mmap_mode="r", allow_pickle=False)
        reloaded_bitmap = np.load(args.out / "completion_bitmap.npy", mmap_mode="r", allow_pickle=False)
        if not np.array_equal(reloaded[canary], output) or not np.all(reloaded_bitmap[canary]):
            raise RuntimeError("Canary on-disk reload parity failed")
        del reloaded, reloaded_bitmap
        # Extrapolate two forwards/64 rows, then add 3x conservatism and 180s I/O.
        forecast_seconds = canary_seconds / (2 * CANARY_ROWS) * len(spectra) * 3 + 180
        gate = {"status": "PASS", "queries": CANARY_ROWS, "query_rows": canary.tolist(),
                "seconds_for_two_forwards": canary_seconds, "same_batch_repeat_max_absolute_error": max_abs,
                "repeat_tolerance": {"rtol": 0.001, "atol": 0.003},
                "shape": [CANARY_ROWS, NBITS], "all_finite": True,
                "disk_reload_exact": True, "full_batch_size": CANARY_ROWS,
                "forecast_seconds_including_3x_compute_and_180s_io": forecast_seconds,
                "native_process_peak_rss_bytes": rss_bytes(),
                "torch_peak_allocated_bytes": torch.cuda.max_memory_allocated()}
        if time.monotonic() - started + forecast_seconds > WALL_SECONDS:
            raise RuntimeError("Canary forecast exceeds total budget; full cache not admitted")
        write_json(args.out / "canary_gate.json", gate)
        print("RANKER_CACHE_CANARY_PASS", json.dumps(gate), flush=True)
        phase = "full_reserved_cache"
        for offset in range(0, len(spectra), CANARY_ROWS):
            rows = np.arange(offset, min(offset + CANARY_ROWS, len(spectra)))
            rows = rows[~arrays["completion_bitmap"][rows]]
            if len(rows):
                arrays["query_logits"][rows] = predict(rows)
                arrays["query_logits"].flush()
                arrays["completion_bitmap"][rows] = True
                arrays["completion_bitmap"].flush()
            if offset % 2048 == 0:
                print("RANKER_CACHE_PROGRESS", int(np.count_nonzero(arrays["completion_bitmap"])), len(spectra), flush=True)
        phase = "numeric_export_and_complete_verification"
        assert_output_arrays(np, arrays)
        np.savez(args.out / "ranker_cache.npz", **arrays)
        with np.load(args.out / "ranker_cache.npz", allow_pickle=False) as archive:
            if set(archive.files) != set(arrays):
                raise RuntimeError("NPZ inventory mismatch")
            for name in arrays:
                value = archive[name]
                if value.dtype != arrays[name].dtype or not np.array_equal(value, arrays[name]):
                    raise RuntimeError("NPZ reload parity failed: " + name)
        for name, value in arrays.items():
            if name not in ("query_logits", "completion_bitmap"):
                np.save(args.out / (name + ".npy"), value, allow_pickle=False)
        output_paths = sorted(args.out.glob("*.npy")) + [args.out / "ranker_cache.npz", args.out / "canary_gate.json"]
        outputs = {path.name: {"bytes": path.stat().st_size, "sha256": digest(path)} for path in output_paths}
        if sum(entry["bytes"] for entry in outputs.values()) > MAX_OUTPUT_BYTES:
            raise RuntimeError("Actual output budget exceeded")
        budget()
        receipt.update(status="COMPLETE_RESERVED_RANKER_CACHE", seconds=time.monotonic() - started,
                       complete_query_rows=len(spectra), role_table_sha256=ROLE_SHA,
                       native_process_peak_rss_bytes=rss_bytes(),
                       torch_peak_allocated_bytes=torch.cuda.max_memory_allocated(), outputs=outputs,
                       canary_gate=gate, historical_ranker_cache_reconstructed=False,
                       scope="new raw FP logits and exact public training joins; no score/ranker/full feature pipeline claim")
        write_json(args.out / "CACHE_MANIFEST.json", receipt)
        print("RANKER_CACHE_COMPLETE", json.dumps(receipt), flush=True)
    except BaseException as exc:
        receipt.update(status="INCOMPLETE_PRESERVE_ALL_PARTIAL_OUTPUTS", phase=phase,
                       seconds=time.monotonic() - started, native_process_peak_rss_bytes=rss_bytes(),
                       error_type=type(exc).__name__, error=str(exc))
        write_json(args.out / "INCOMPLETE_RECEIPT.json", receipt)
        traceback.print_exc()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
