#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 cubres
"""One-pass CPU validation of the completed complementary FP checkpoint.

Scores the exact preselected role-1-even 2,048-structure split against its
bound V6 starting checkpoint, preserving all 63 fixed candidate draws per
query, including repeated indices from the with-replacement sampling. The first
64 queries are a mechanics and resource canary; after it passes, the full split
is evaluated once. This is a local proxy evaluation, not an official score.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import resource
import sys
import time

import numpy as np
import torch

ROOT = pathlib.Path("/Users/cubres/Documents/Neurogolf/research")
PACKET = ROOT / "codex_casmi_complementary_fp_3000_source_20261019"
OUTPUT_ROOT = PACKET / "ROOT_EXACT_V9_OUTPUT_20261019T2114Z/data"
TRAIN_OUTPUT = OUTPUT_ROOT / "casmi_complementary_fp_3000_training_20261019"
RUNTIME_SOURCE = TRAIN_OUTPUT / "source"
INPUTS = PACKET / "ROOT_V9_HELDOUT_VALIDATION_INPUTS_V1_20261020"
DATA_DIR = INPUTS / "full-fingerprint-inputs/extracted"
SPEC_PATH = INPUTS / "spec-fp/extracted/spec.npz"
CONTRACT_PATH = PACKET / "TRAINING_CONTRACT.json"
BASELINE_CKPT = ROOT / "codex_casmi_v6_checkpoint_public_release_20261018/dataset/best_full_model.pt"
SPLIT_DIR = ROOT / "codex_campaign_20261003T1439Z/full_fp_pair_v4_output/full_spectrum"
QUERY_IDS = SPLIT_DIR / "checkpoint_spectrum_ids.npy"
FIXED_NEGATIVES = SPLIT_DIR / "checkpoint_decoy_indices.npy"
BASELINE_SHA = "9c46ca4fcf19002fecbcded0d0808e8a81e3a25a143e684e259f265c44a5be31"
CANDIDATE_CKPT = TRAIN_OUTPUT / "complementary_full_model.pt"
CANDIDATE_SHA = "c1c7650411d507f395e3077e90db72a8b1d692493e91c7f13ba6f55e6359b286"
SOURCE_BINDING = TRAIN_OUTPUT / "source_binding.json"
SOURCE_BINDING_SHA = "3797c232ce0f8911c6d3a0b779803d12f259f9cf34261ddcfba4203b4b38f6f0"
CONTRACT_BYTES = 9549
CONTRACT_SHA = "092a0ad1b46dbdf369a78d70fde409395eb3db53f0027da6240bc62e0c8f75f6"
TRAINING_CONFIG = TRAIN_OUTPUT / "training_config.json"
TRAINING_CONFIG_SHA = "4e766f7d2d9b17b809c1aece155be43e55e0eebe75cfe7e7a7adf030800c06a0"
QUERY_SHA = "b16cc570c4db9716cfe4cb8a19efb73185b5f663c136d3ed75e2c2c13cc9112a"
NEGATIVE_SHA = "2714697b0d21c956b883e5d4860bd67cae4d7b5a2f2a689edd198321ba3647ea"
BASELINE_REFERENCE_MRR25 = 0.7074749658368091
MAX_SECONDS = 1800
MAX_RSS_BYTES = 12 * 1024**3
CANARY_ROWS = 64
FULL_ROWS = 2048


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def check_budget(started: float) -> None:
    if time.monotonic() - started > MAX_SECONDS:
        raise TimeoutError("whole-validation CPU time budget exceeded")
    if peak_rss_bytes() > MAX_RSS_BYTES:
        raise MemoryError("monitored peak RSS budget exceeded")


def verify_file(path: pathlib.Path, expected_bytes: int | None, expected_sha: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    if expected_bytes is not None and path.stat().st_size != expected_bytes:
        raise ValueError(f"byte-count mismatch: {path.name}")
    if sha256(path) != expected_sha:
        raise ValueError(f"SHA-256 mismatch: {path.name}")


def load_binding() -> tuple[dict, dict]:
    # Pin the source manifest and local contract before parsing the contract.
    verify_file(SOURCE_BINDING, 1461, SOURCE_BINDING_SHA)
    verify_file(CONTRACT_PATH, CONTRACT_BYTES, CONTRACT_SHA)
    emitted_sources = json.loads(SOURCE_BINDING.read_text())
    contract_pin = emitted_sources.get("TRAINING_CONTRACT.json")
    if contract_pin != {"bytes": CONTRACT_BYTES, "sha256": CONTRACT_SHA}:
        raise ValueError("source manifest does not bind the expected training contract")
    contract = json.loads(CONTRACT_PATH.read_text())
    checked = {"training_contract": CONTRACT_SHA}
    for name, spec in contract["inputs"]["bank_files"].items():
        path = DATA_DIR / name
        verify_file(path, spec["bytes"], spec["sha256"])
        checked[f"bank/{name}"] = spec["sha256"]
    manifest = DATA_DIR / contract["inputs"]["manifest_name"]
    verify_file(manifest, None, contract["inputs"]["manifest_sha256"])
    checked["bank/" + manifest.name] = contract["inputs"]["manifest_sha256"]
    verify_file(SPEC_PATH, contract["inputs"]["spectra_bytes"], contract["inputs"]["spectra_sha256"])
    checked["spec.npz"] = contract["inputs"]["spectra_sha256"]
    verify_file(BASELINE_CKPT, 197739081, BASELINE_SHA)
    verify_file(CANDIDATE_CKPT, 197740262, CANDIDATE_SHA)
    verify_file(QUERY_IDS, 16512, QUERY_SHA)
    verify_file(FIXED_NEGATIVES, 1032320, NEGATIVE_SHA)
    verify_file(TRAINING_CONFIG, 11314, TRAINING_CONFIG_SHA)
    for name, spec in emitted_sources.items():
        path = RUNTIME_SOURCE / name
        verify_file(path, spec["bytes"], spec["sha256"])
        checked["runtime_source/" + name] = spec["sha256"]
    training_config = json.loads(TRAINING_CONFIG.read_text())
    if (training_config.get("steps") != 3000
            or training_config.get("no_validation") is not True
            or training_config.get("assay_repeated") is not False
            or training_config.get("checkpoint_sha256") != BASELINE_SHA
            or training_config.get("input_sha256", {}).get("spec.npz")
                != contract["inputs"]["spectra_sha256"]):
        raise ValueError("training configuration does not match the V9 checkpoint/data contract")
    checked.update({
        "baseline_checkpoint": BASELINE_SHA,
        "candidate_checkpoint": CANDIDATE_SHA,
        "checkpoint_spectrum_ids": QUERY_SHA,
        "checkpoint_decoy_indices": NEGATIVE_SHA,
        "source_binding": SOURCE_BINDING_SHA,
        "training_config": TRAINING_CONFIG_SHA,
    })
    return contract, checked


def construct_model(FPNet, checkpoint: pathlib.Path) -> torch.nn.Module:
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    if state.get("nbits") != 10395 or state.get("layers") != 8 or state.get("d") != 512:
        raise ValueError(f"unexpected checkpoint architecture: {checkpoint.name}")
    model = FPNet(10395, d=512, layers=8).cpu()
    model.load_state_dict(state["model"], strict=True)
    del state
    if not all(bool(torch.isfinite(p).all()) for p in model.parameters()):
        raise ValueError(f"nonfinite parameter in {checkpoint.name}")
    return model.eval()


def evaluate(model, data, ids: np.ndarray, decoys: np.ndarray, started: float) -> np.ndarray:
    values = []
    with torch.inference_mode():
        for offset in range(0, len(ids), 32):
            batch_ids = ids[offset:offset + 32]
            batch_decoys = decoys[offset:offset + len(batch_ids)]
            inputs, _, _ = data.batch(batch_ids, K=0, rng=np.random.default_rng(20261004),
                                      aug=False, merge_p=0.0)
            positives = data.s2p[data.six[batch_ids]]
            if np.any(positives < 0):
                raise ValueError("held-out positive missing from the pinned candidate pool")
            candidates = torch.as_tensor(np.column_stack([positives, batch_decoys]), dtype=torch.long)
            logits = model(*inputs).float()
            if not bool(torch.isfinite(logits).all()):
                raise ValueError("nonfinite model logits")
            fingerprints = data.PFP[candidates].float()
            raw = torch.bmm(fingerprints, logits.unsqueeze(-1)).squeeze(-1)
            rank_logits = (raw - raw.mean(dim=1, keepdim=True)) / math.sqrt(data.nbits)
            order = torch.argsort(rank_logits, dim=1, descending=True, stable=True)
            positions = (order == 0).to(torch.int64).argmax(1) + 1
            mrr = torch.where(positions <= 25, 1.0 / positions.float(), 0.0)
            values.extend(mrr.cpu().numpy().astype(float).tolist())
            check_budget(started)
    return np.asarray(values, dtype=np.float64)


def bootstrap_delta_ci(delta: np.ndarray, seed: int = 20261020, draws: int = 5000) -> list[float]:
    rng = np.random.default_rng(seed)
    means = np.empty(draws, dtype=np.float64)
    for i in range(draws):
        means[i] = delta[rng.integers(0, len(delta), size=len(delta))].mean()
    return [float(x) for x in np.quantile(means, [0.025, 0.975])]


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(f"output path already exists; preserving it: {args.out}")

    # Complete the fixed-hash/data/split preflight before consuming the one-use
    # output path. No model is constructed or evaluated in this section.
    started = time.monotonic()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    contract, hashes = load_binding()
    sys.path.insert(0, str(RUNTIME_SOURCE))
    from fpmodel import FPNet
    from train_full_fingerprint import FullData

    data = FullData(DATA_DIR, "cpu", SPEC_PATH)
    ids = np.load(QUERY_IDS, allow_pickle=False)
    decoys = np.load(FIXED_NEGATIVES, allow_pickle=False)
    if ids.shape != (FULL_ROWS,) or decoys.shape != (FULL_ROWS, 63):
        raise ValueError(f"unexpected held-out shapes: {ids.shape}, {decoys.shape}")
    structures = data.six[ids]
    if len(np.unique(structures)) != FULL_ROWS:
        raise ValueError("held-out list is not one query per structure")
    if not bool(np.all(data.roles[structures] == 1)) or not bool(np.all(structures % 2 == 0)):
        raise ValueError("held-out roles differ from the predeclared role-1-even split")
    if not bool(np.all(data.roles[data.six[data.tr]] == 0)):
        raise ValueError("optimizer data includes a non-role-0 structure")
    positives = data.s2p[structures]
    out_of_range = int(np.count_nonzero((decoys < 0) | (decoys >= len(data.pkeys))))
    positive_overlap_rows = int(np.count_nonzero(np.any(decoys == positives[:, None], axis=1)))
    repeated_rows = int(np.count_nonzero([len(np.unique(row)) != row.size for row in decoys]))
    repeated_draws = int(decoys.size - sum(len(np.unique(row)) for row in decoys))
    if out_of_range or np.any(positives < 0) or positive_overlap_rows:
        raise ValueError(f"fixed candidate draws fail range/positive checks: out_of_range={out_of_range}, missing_positive={int(np.count_nonzero(positives < 0))}, positive_overlap_rows={positive_overlap_rows}")
    draw_receipt = {
        "rows": int(decoys.shape[0]), "draws_per_query": int(decoys.shape[1]),
        "sampling_with_replacement": True, "repeated_rows": repeated_rows,
        "repeated_draws": repeated_draws, "duplicates_preserved_in_ranking": True,
        "out_of_range_indices": out_of_range, "positive_overlap_rows": positive_overlap_rows,
    }
    check_budget(started)

    # Claim the new attempt only after source, data, and split checks pass.
    args.out.mkdir(parents=False, exist_ok=False)
    receipt = {
        "schema": "casmi-v9-complementary-fp-heldout-validation/3",
        "status": "STARTED_ONCE",
        "observed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scope": "local CPU proxy only; no official score or submission",
        "canary_rows": CANARY_ROWS,
        "full_rows": FULL_ROWS,
        "metric": "structure-weighted sampled-draw MRR@25 on fixed role-1-even queries and 63 preselected candidate draws; repeated draws remain repeated candidates",
        "device": "CPU FP32 for both baseline and candidate; not CUDA autocast FP16 parity",
        "threads": 2,
        "script_sha256": sha256(pathlib.Path(__file__).resolve()),
        "input_and_source_sha256": hashes,
        "fixed_candidate_draws": draw_receipt,
        "max_seconds": MAX_SECONDS,
        "max_monitored_peak_rss_bytes": MAX_RSS_BYTES,
        "attempt_marker": "created after hash, data, and split preflight; before any model construction/inference",
        "historical_baseline_match_is_diagnostic_only": True,
    }
    (args.out / "ONCE_CONSUMED.json").write_text(json.dumps(receipt, indent=2) + "\n")
    try:
        # The canary gates numerical stability, memory, and projected runtime.
        # Its score is recorded but is not a model-quality threshold.
        canary_started = time.monotonic()
        baseline = construct_model(FPNet, BASELINE_CKPT)
        canary_base = evaluate(baseline, data, ids[:CANARY_ROWS], decoys[:CANARY_ROWS], started)
        del baseline
        candidate = construct_model(FPNet, CANDIDATE_CKPT)
        canary_candidate = evaluate(candidate, data, ids[:CANARY_ROWS], decoys[:CANARY_ROWS], started)
        del candidate
        canary_seconds = time.monotonic() - canary_started
        projected_full_seconds = canary_seconds * (FULL_ROWS / CANARY_ROWS) * 1.2
        if (len(canary_base) != CANARY_ROWS or len(canary_candidate) != CANARY_ROWS
                or not np.isfinite(canary_base).all() or not np.isfinite(canary_candidate).all()
                or peak_rss_bytes() > MAX_RSS_BYTES or projected_full_seconds > 1500):
            raise RuntimeError("canary gate failed; full evaluation not admitted")
        receipt["canary"] = {
            "status": "PASS_MECHANICS_RESOURCE_AND_NUMERICS",
            "rows": CANARY_ROWS,
            "baseline_mrr25": float(canary_base.mean()),
            "candidate_mrr25": float(canary_candidate.mean()),
            "candidate_minus_baseline": float((canary_candidate - canary_base).mean()),
            "seconds": round(canary_seconds, 3),
            "projected_full_seconds": round(projected_full_seconds, 3),
            "performance_not_used_as_gate": True,
        }
        (args.out / "CANARY_GATE.json").write_text(json.dumps(receipt["canary"], indent=2) + "\n")

        baseline = construct_model(FPNet, BASELINE_CKPT)
        base_values = evaluate(baseline, data, ids, decoys, started)
        del baseline
        candidate = construct_model(FPNet, CANDIDATE_CKPT)
        candidate_values = evaluate(candidate, data, ids, decoys, started)
        del candidate
        delta = candidate_values - base_values
        base_mrr = float(base_values.mean())
        candidate_mrr = float(candidate_values.mean())
        receipt.update({
            "status": "COMPLETE_HELDOUT_VALIDATION_NO_COMPETITION_SCORE",
            "baseline": {"checkpoint_sha256": BASELINE_SHA, "mrr25": base_mrr,
                         "historical_reference_mrr25": BASELINE_REFERENCE_MRR25,
                         "matches_historical_within_0_002": abs(base_mrr - BASELINE_REFERENCE_MRR25) <= 0.002},
            "candidate": {"checkpoint_sha256": CANDIDATE_SHA, "training_steps": 3000,
                          "mrr25": candidate_mrr},
            "paired_delta": {
                "candidate_minus_baseline_mrr25": float(delta.mean()),
                "bootstrap_95_percentile_ci_seed20261020_draws5000": bootstrap_delta_ci(delta),
            },
            "queries": FULL_ROWS,
            "unique_structures": int(len(np.unique(structures))),
            "candidate_draws_per_query": 63,
            "fixed_candidate_draws": draw_receipt,
            "official_score": None,
            "submission_performed": False,
            "cuda_fp16_rank_parity_claimed": False,
        })
        with (args.out / "PER_QUERY_MRR.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["query_row", "spectrum_id", "structure_index", "baseline_mrr25", "candidate_mrr25", "delta"])
            for i, (base_value, candidate_value) in enumerate(zip(base_values, candidate_values)):
                writer.writerow([i, int(ids[i]), int(structures[i]), f"{base_value:.12g}", f"{candidate_value:.12g}", f"{candidate_value-base_value:.12g}"])
    except Exception as error:
        receipt.update({"status": "STOPPED_UNQUALIFIED", "failure_type": type(error).__name__,
                        "failure": str(error)})
        raise
    finally:
        receipt["seconds"] = round(time.monotonic() - started, 3)
        receipt["peak_rss_bytes"] = peak_rss_bytes()
        (args.out / "RESULT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
