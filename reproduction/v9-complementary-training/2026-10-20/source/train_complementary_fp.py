"""Bounded role-0 complementary-view continuation of the selected CASMI V6.

This is a new treatment, not a reproduction, accuracy assay or submission.
The 64-step canary is the beginning of the same 3,000-step optimizer run.
No checkpoint-selection, fusion or sealed-role query is evaluated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time


CHECKPOINT_SHA = "9c46ca4fcf19002fecbcded0d0808e8a81e3a25a143e684e259f265c44a5be31"
CHECKPOINT_BYTES = 197739081
GIB = 1024 ** 3
SEED = 20261019
STEPS = 3000
CANARY_STEPS = 64
MAX_SECONDS = 2700
RESERVE_SECONDS = 120
RSS_LIMIT = 20 * GIB
CUDA_LIMIT = 13 * GIB
BASE_LR = 2e-5
WARMUP_STEPS = 128
SOURCE_NAMES = ("fpmodel.py", "train_fp4.py", "structure_uniform_sampler.py", "train_full_fingerprint.py")


class TrainingGateError(RuntimeError):
    pass


def require(condition, reason):
    if not condition:
        raise TrainingGateError(reason)


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            value.update(block)
    return value.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def peak_rss_bytes():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def conservative_step_seconds(times):
    """Keep compilation/startup out of no measurement: use all 64 canary steps."""
    ordered = sorted(times)
    p90 = ordered[min(len(ordered) - 1, math.ceil(0.9 * len(ordered)) - 1)]
    recent = sorted(times[-32:])
    median = (recent[(len(recent) - 1) // 2] + recent[len(recent) // 2]) / 2
    return max(p90, 1.2 * median)


def verify_inputs(args, source_dir):
    contract = json.loads((source_dir / "TRAINING_CONTRACT.json").read_text())
    records = {}
    for name in SOURCE_NAMES:
        expected = contract["source_files"][name]
        path = source_dir / name
        require(path.stat().st_size == expected["bytes"], f"Source size drift: {name}")
        actual = sha256(path)
        require(actual == expected["sha256"], f"Source SHA drift: {name}")
        records["source/" + name] = actual
    expected_inputs = dict(contract["inputs"]["bank_files"])
    expected_inputs[contract["inputs"]["manifest_name"]] = {
        "sha256": contract["inputs"]["manifest_sha256"]
    }
    for name, expected in expected_inputs.items():
        path = args.data / name
        if "bytes" in expected:
            require(path.stat().st_size == expected["bytes"], f"Input size drift: {name}")
        actual = sha256(path)
        require(actual == expected["sha256"], f"Input SHA drift: {name}")
        records["bank/" + name] = actual
    require(args.spec.stat().st_size == contract["inputs"]["spectra_bytes"], "Spectrum size drift")
    require(sha256(args.spec) == contract["inputs"]["spectra_sha256"], "Spectrum SHA drift")
    require(args.checkpoint.stat().st_size == CHECKPOINT_BYTES, "Warm-start checkpoint size drift")
    require(sha256(args.checkpoint) == CHECKPOINT_SHA, "Warm-start checkpoint SHA drift")
    records["spec.npz"] = contract["inputs"]["spectra_sha256"]
    records["warm_start_checkpoint"] = CHECKPOINT_SHA
    return contract, records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source_dir = Path(__file__).resolve().parent
    args.out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    state = dict(schema="casmi-complementary-fp-runtime/1", status="STARTING", actual_optimizer_steps=0,
                 requested_optimizer_steps=STEPS, canary_steps=CANARY_STEPS,
                 training_run=True, role0_optimizer_only=True, validation_spectrum_queries=0,
                 role1_spectrum_queries=0, role2_spectrum_queries=0, role3_spectrum_queries=0,
                 negative_candidates="Original shared mass-filtered fingerprint pool; spectrum-role embargo applies to queries and positive labels",
                 checkpoint_selection="final optimizer step only; no label-based selection",
                 assay_repeated=False, official_score=None, accuracy_claim=None,
                 cache_promotable=False, cache_promotability_reason="New checkpoint has no raw-logit cache or distinct approved evaluation",
                 max_seconds=MAX_SECONDS, serialization_reserve_seconds=RESERVE_SECONDS,
                 rss_limit_bytes=RSS_LIMIT, cuda_limit_bytes=CUDA_LIMIT,
                 starting_checkpoint_sha256=CHECKPOINT_SHA, starting_checkpoint_bytes=CHECKPOINT_BYTES)

    def alarm_handler(signum, frame):
        raise TrainingGateError("Internal phase deadline reached: " + state.get("phase", "startup/training"))

    signal.signal(signal.SIGALRM, alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, MAX_SECONDS - RESERVE_SECONDS)
    model = optimizer = scaler = rng = None
    times = []
    try:
        contract, input_binding = verify_inputs(args, source_dir)
        # No scientific dependencies are imported by the compile-only verifier.
        import numpy as np
        import torch
        from torch.nn import functional as F
        from fpmodel import FPNet
        from train_full_fingerprint import FullData, lookup_contract, scores

        require(torch.cuda.is_available(), "Scheduled CUDA worker is required")
        torch.set_num_threads(2)
        torch.manual_seed(SEED)
        np.random.seed(SEED)
        lookup = lookup_contract("cuda")
        data = FullData(args.data, "cuda", args.spec)
        require(data.nbits == 10395, "Expected full fingerprint width")
        require(data.receipt["optimizer_structures"] == 219140, "Optimizer structure eligibility drift")
        require(data.receipt["optimizer_spectra"] == 1886521, "Optimizer spectrum eligibility drift")
        original_peers = data.peers

        def checked_role0_peers(anchor, generator, kmax=4):
            peers = original_peers(anchor, generator, kmax)
            peer_ids = np.asarray(peers, dtype=np.int64)
            require(bool(np.all(data.roles[data.six[peer_ids]] == 0)), "Non-role-0 merged peer")
            require(bool(np.all(data.six[peer_ids] == data.six[anchor])), "Merged peer structure drift")
            return peers

        data.peers = checked_role0_peers
        model = FPNet(data.nbits, d=512, layers=8).cuda()
        initial = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
        require(initial["nbits"] == 10395 and initial["layers"] == 8 and initial["d"] == 512,
                "Checkpoint architecture drift")
        require(initial["step"] == 28000, "Unexpected original checkpoint step")
        model.load_state_dict(initial["model"], strict=True)
        for parameter in model.parameters():
            require(bool(torch.isfinite(parameter).all()), "Warm-start parameter is nonfinite")
        # Record one stable parameter for a genuine optimizer-change check.
        tracked_parameter = dict(model.named_parameters())["head.3.weight"]
        initial_parameter_digest = hashlib.sha256(tracked_parameter.detach().cpu().numpy().tobytes()).hexdigest()
        del initial
        optimizer = torch.optim.AdamW(model.parameters(), lr=BASE_LR, weight_decay=0.01, betas=(0.9, 0.98))
        scaler = torch.amp.GradScaler("cuda", init_scale=1024.0)
        rng = np.random.default_rng(SEED)
        recipe = dict(schema="casmi-complementary-fp-training-config/1", seed=SEED, layers=8, d=512,
                      nbits=data.nbits, batch_size=256, micro_batch_size=64, steps=STEPS,
                      canary_steps=CANARY_STEPS, canary_continued_without_reset=True,
                      merge_probability=0.5, augmentation=True, optimizer="AdamW", learning_rate=BASE_LR,
                      warmup_steps=WARMUP_STEPS, schedule="linear warmup; cosine to 2% of base LR",
                      weight_decay=0.01, betas=[0.9, 0.98], gradient_clip_norm=1.0,
                      grad_scaler_initial_scale=1024.0, objective="BCE full10395 plus original sampled63-decoy cross entropy",
                      checkpoint_start="selected V6 step28000; fresh optimizer, not historical optimizer continuation",
                      checkpoint_sha256=CHECKPOINT_SHA, split=data.receipt,
                      sampler=data.optimizer_sampler.receipt(), lookup_contract=lookup,
                      merge_semantics="Original FullData.peers and train_fp4.Data._merged/batch unchanged; peers share structure/adduct/mode/instrument; mean finite nonnegative peer CE; original microbatch-N peak truncation retained",
                      no_validation=True, no_accuracy_claim=True, assay_repeated=False,
                      source_sha256=sha256(__file__), input_sha256=input_binding,
                      python=sys.version, numpy=np.__version__, torch=torch.__version__,
                      cuda=torch.version.cuda, device=torch.cuda.get_device_name(0),
                      immutable_original_training_image=contract["environment"]["immutable_image"],
                      current_image_pin_not_inferred_from_original=True)
        write_json(args.out / "training_config.json", recipe)
        snapshot = args.out / "source"
        snapshot.mkdir(exist_ok=False)
        snapshot_names = (*SOURCE_NAMES, "train_complementary_fp.py", "TRAINING_CONTRACT.json",
                          "ORIGINAL_SOURCE_BINDING.json", "PERMISSION_SCOPE.json", "LICENSE-SOURCE",
                          "LICENSE-WEIGHTS.md", "NOTICE.md")
        for name in snapshot_names:
            (snapshot / name).write_bytes((source_dir / name).read_bytes())
        write_json(args.out / "source_binding.json", {
            name: dict(bytes=(snapshot / name).stat().st_size, sha256=sha256(snapshot / name))
            for name in snapshot_names})
        np.save(args.out / "optimizer_structure_indices.npy", data.optimizer_sampler.structures)
        np.save(args.out / "optimizer_eligible_spectrum_counts.npy", data.optimizer_sampler.counts)
        state["input_verification_seconds"] = round(time.monotonic() - started, 3)
        state["initial_parameter_sha256"] = initial_parameter_digest
        model.train()

        def resource_gate(training_phase=True):
            elapsed = time.monotonic() - started
            resources = dict(peak_rss_bytes=peak_rss_bytes(),
                             peak_cuda_allocated_bytes=int(torch.cuda.max_memory_allocated()),
                             peak_cuda_reserved_bytes=int(torch.cuda.max_memory_reserved()),
                             seconds=round(elapsed, 3))
            state.update(resources)
            require(resources["peak_rss_bytes"] < RSS_LIMIT, "Peak RSS budget exceeded")
            require(max(resources["peak_cuda_allocated_bytes"], resources["peak_cuda_reserved_bytes"]) < CUDA_LIMIT,
                    "Peak CUDA budget exceeded")
            limit = MAX_SECONDS - RESERVE_SECONDS if training_phase else MAX_SECONDS
            require(elapsed < limit, "Internal phase time budget exhausted")
            return elapsed

        resource_gate()
        for step in range(STEPS):
            resource_gate()
            if step >= CANARY_STEPS:
                forecast = conservative_step_seconds(times[-64:]) * (STEPS - step)
                require(time.monotonic() - started + forecast + RESERVE_SECONDS <= MAX_SECONDS,
                        "Measured rolling throughput no longer fits full recipe plus reserve")
            step_started = time.monotonic()
            warm = WARMUP_STEPS
            progress = max(0.0, (step - warm) / (STEPS - warm))
            lr = BASE_LR * (step + 1) / warm if step < warm else BASE_LR * (0.02 + 0.98 * 0.5 * (1 + math.cos(math.pi * progress)))
            for group in optimizer.param_groups:
                group["lr"] = lr
            ids = data.optimizer_sampler.sample(rng, 256)
            require(bool(np.all(data.roles[data.six[ids]] == 0)), "Non-role-0 optimizer query")
            optimizer.zero_grad(set_to_none=True)
            loss_value = bce_value = 0.0
            for offset in range(0, len(ids), 64):
                chunk = ids[offset:offset + 64]
                bce, ranking = scores(model, data, chunk, rng, 63, augment=True, merge_probability=0.5)
                loss = bce + F.cross_entropy(ranking, torch.zeros(len(chunk), dtype=torch.long, device="cuda"))
                require(bool(torch.isfinite(loss)), "Nonfinite optimizer loss")
                fraction = len(chunk) / len(ids)
                loss_value += float(loss.detach()) * fraction
                bce_value += float(bce.detach()) * fraction
                scaler.scale(loss * fraction).backward()
            scaler.unscale_(optimizer)
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
            require(bool(torch.isfinite(norm)), "Nonfinite optimizer gradient")
            scale_before = scaler.get_scale()
            scaler.step(optimizer)
            scaler.update()
            require(scaler.get_scale() >= scale_before, "GradScaler skipped a nonfinite optimizer step")
            torch.cuda.synchronize()
            state["actual_optimizer_steps"] += 1
            times.append(time.monotonic() - step_started)
            elapsed = resource_gate()
            if step + 1 == CANARY_STEPS:
                seconds_per_step = conservative_step_seconds(times)
                forecast = elapsed + seconds_per_step * (STEPS - CANARY_STEPS) + RESERVE_SECONDS
                canary = dict(status="PASS" if forecast <= MAX_SECONDS else "FAIL_BUDGET_FORECAST",
                              optimizer_steps=CANARY_STEPS, finite_losses=True, finite_gradients=True,
                              conservative_seconds_per_step=seconds_per_step,
                              measured_step_seconds=times.copy(),
                              estimator="max(all64 p90 nearest-rank, 1.2 times last32 median)",
                              projected_total_seconds_with_reserve=forecast,
                              canary_continued_without_reset=True, **{k: state[k] for k in
                                  ("peak_rss_bytes", "peak_cuda_allocated_bytes", "peak_cuda_reserved_bytes")})
                write_json(args.out / "canary_gate.json", canary)
                print("COMPLEMENT_CANARY", json.dumps(canary, allow_nan=False), flush=True)
                require(forecast <= MAX_SECONDS, "64-step canary forecast exceeds internal budget")
            if (step + 1) % 16 == 0:
                record = dict(step=step + 1, bce=bce_value, loss=loss_value, lr=lr,
                              gradient_norm=float(norm), seconds=elapsed,
                              step_seconds=times[-1], peak_rss_bytes=state["peak_rss_bytes"],
                              peak_cuda_allocated_bytes=state["peak_cuda_allocated_bytes"],
                              peak_cuda_reserved_bytes=state["peak_cuda_reserved_bytes"])
                with (args.out / "training_history.jsonl").open("a") as stream:
                    stream.write(json.dumps(record, allow_nan=False) + "\n")
                write_json(args.out / "progress.json", record)
                print("COMPLEMENT_STEP", json.dumps(record, allow_nan=False), flush=True)

        require(state["actual_optimizer_steps"] == STEPS, "Incomplete optimizer recipe")
        for parameter in model.parameters():
            require(bool(torch.isfinite(parameter).all()), "Final model parameter is nonfinite")
        for values in optimizer.state.values():
            require(int(values["step"].item()) == STEPS, "Optimizer step-state drift")
        final_digest = hashlib.sha256(tracked_parameter.detach().cpu().numpy().tobytes()).hexdigest()
        require(final_digest != initial_parameter_digest, "Optimizer did not change tracked parameter")
        state["final_parameter_sha256"] = final_digest
        # The training deadline leaves a real serialization window. Rearm the
        # same watchdog to the absolute whole-job deadline before any output save.
        state["phase"] = "serialization"
        remaining = MAX_SECONDS - (time.monotonic() - started)
        require(remaining > 0, "No serialization time remains")
        signal.setitimer(signal.ITIMER_REAL, remaining)
        state["status"] = "COMPLETE_OPTIMIZER_TRAINING_NO_ACCURACY_CLAIM"
        checkpoint_path = args.out / "complementary_full_model.pt"
        torch.save(dict(model=model.state_dict(), step=STEPS, nbits=10395, d=512, layers=8,
                        seed=SEED, split=data.receipt, treatment="50% metadata-compatible merged spectra",
                        parent_checkpoint_sha256=CHECKPOINT_SHA, validation=None), checkpoint_path)
        torch.save(dict(optimizer=optimizer.state_dict(), grad_scaler=scaler.state_dict(),
                        step=STEPS, numpy_generator_state=rng.bit_generator.state,
                        torch_rng_state=torch.get_rng_state(), cuda_rng_state=torch.cuda.get_rng_state_all(),
                        config=recipe), args.out / "optimizer_state.pt")
        state["outputs"] = {name: dict(bytes=(args.out / name).stat().st_size, sha256=sha256(args.out / name))
                            for name in ("complementary_full_model.pt", "optimizer_state.pt", "training_config.json")}
        resource_gate(training_phase=False)
        require(time.monotonic() - started <= MAX_SECONDS, "Serialization exceeded complete internal budget")
    except Exception as error:
        state["status"] = "STOPPED_UNPROMOTABLE"
        state["failure_type"] = type(error).__name__
        state["failure"] = str(error)
        state["cache_promotable"] = False
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        state["seconds"] = round(time.monotonic() - started, 3)
        state["peak_rss_bytes"] = peak_rss_bytes()
        state["source_only_result_is_not_training_evidence"] = False
        write_json(args.out / "runtime_receipt.json", state)
        print("COMPLEMENT_RESULT", json.dumps(state, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
