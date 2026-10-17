"""One-view CUDA driver candidate; source preparation is not launch admission.

Root must verify notebook identity, terminal V5, mounts/use rights, image and the
whole actual provider allocation/quota before incorporating this source in place.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


BASELINE_INPUT_MANIFEST_SHA256 = '5b08ca4b830de1558be4ce568a10f0997b5fa2fe875a872dcd6a216f901fd9ef'
BASELINE_TRAINING_SPECTRA_DATASET = 'prvsiyan/casmi26-spec-fp'
BASELINE_TRAINING_SPECTRA_SHA256 = '99dbf966d2607e2da8085a6550206a71fc912d2c90b9555a725a2569e4af4500'


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''):
            result.update(block)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=Path('/kaggle/input/casmi26-full-fingerprint-inputs'))
    parser.add_argument('--spec', type=Path, default=Path('/kaggle/input/casmi26-spec-fp/spec.npz'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.data = args.data.resolve()
    args.spec = args.spec.resolve()
    args.out = args.out.resolve()
    source_dir = Path(__file__).resolve().parent
    manifest_path = args.data / 'FULL_FINGERPRINT_MANIFEST.json'
    assert digest(manifest_path) == BASELINE_INPUT_MANIFEST_SHA256, 'Owned baseline input manifest drifted'
    manifest = json.loads(manifest_path.read_text())
    assert manifest['training_spectra_dataset'] == BASELINE_TRAINING_SPECTRA_DATASET
    assert manifest['training_spectra_sha256'] == BASELINE_TRAINING_SPECTRA_SHA256
    for name, expected in manifest['input_files'].items():
        assert digest(args.data / name) == expected['sha256'], name
    assert digest(args.spec) == BASELINE_TRAINING_SPECTRA_SHA256, 'Owned baseline training spectra drifted'
    input_binding = dict(manifest_sha256=BASELINE_INPUT_MANIFEST_SHA256,
                         training_spectra_dataset=BASELINE_TRAINING_SPECTRA_DATASET,
                         training_spectra_sha256=BASELINE_TRAINING_SPECTRA_SHA256)
    source_hashes = {name: digest(source_dir / name) for name in (
        'train_full_fingerprint.py', 'structure_uniform_sampler.py', 'train_fp4.py', 'fpmodel.py',
    )}
    assert source_hashes['train_fp4.py'] == '1daa2532ef186600c21fc96fa6a16e1729084b4e7257524a0dc33fc2adc7abb0'
    assert source_hashes['fpmodel.py'] == '69f2656778a08233e22235bf4853f0b3d2420b431390a32d6c8ed453cde85c76'
    import torch
    visible_devices = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
    assert visible_devices and all('T4' in name for name in visible_devices), 'Scheduled CUDA T4 worker required'
    # Only one view/worker is used even when the provider allocates two T4s.
    # These visible devices do not certify account quota or the full allocation.
    args.out.mkdir(parents=True, exist_ok=False)
    budget = dict(
        steps=30000, max_minutes_per_model=330, batch_size=256, micro_batch_size=128,
        layers=8, validation_every=2000, probe_steps=64, seed=20261003,
        view='single spectrum', merge_probability=0.0, workers=1, cuda_visible_devices='0',
        visible_devices=visible_devices, visible_device_count=len(visible_devices),
        quota_accounting='whole actual provider allocation, startup and concurrency; root verification required',
        weekly_paid_compute=False,
        scope='optimizer weights, fixed checkpoint-even selection; no fusion/final role evaluation',
    )
    (args.out / 'single_view_budget.json').write_text(json.dumps(budget, indent=2))
    driver_started = time.monotonic()

    def failure_receipt(status, phase, return_code):
        reports = {}
        for name in ('probe_spectrum', 'full_spectrum'):
            try:
                reports[name] = json.loads((args.out / name / 'runtime_receipt.json').read_text())
            except (OSError, json.JSONDecodeError):
                continue
        receipt = dict(status=status, phase=phase, return_code=return_code,
                       reports=reports, budget=budget, source_sha256=source_hashes,
                       input_binding=input_binding,
                       input_hashes_verified=True, final_test_used=False, official_score=None,
                       seconds=round(time.monotonic() - driver_started, 1))
        (args.out / 'single_view_training_receipt.json').write_text(json.dumps(receipt, indent=2))
        print('SINGLE_VIEW_FAILURE', json.dumps(receipt), flush=True)

    def run_phase(probe):
        tag = 'probe_spectrum' if probe else 'full_spectrum'
        output = args.out / tag
        command = [
            sys.executable, '-u', str(source_dir / 'train_full_fingerprint.py'),
            '--data', str(args.data), '--spec', str(args.spec), '--out', str(output),
            '--seed', '20261003', '--merge-probability', '0', '--steps', '30000',
            '--max-minutes', '15' if probe else '330', '--batch-size', '256',
            '--micro-batch-size', '128', '--layers', '8', '--validation-every', '2000',
        ]
        if probe:
            command.append('--probe-only')
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='0', OMP_NUM_THREADS='2',
                   MKL_NUM_THREADS='2', PYTHONUNBUFFERED='1')
        limit = 1200 if probe else 360 * 60
        started = time.monotonic()
        last_step = None
        with (args.out / (tag + '.log')).open('x') as log:
            try:
                process = subprocess.Popen(command, cwd=str(source_dir), stdout=log,
                                           stderr=subprocess.STDOUT, env=env)
            except OSError:
                failure_receipt('FAILED_LAUNCH', tag, None)
                raise
            while process.poll() is None:
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    progress = output / 'progress.json'
                    if progress.exists():
                        try:
                            value = json.loads(progress.read_text())
                        except (OSError, json.JSONDecodeError):
                            value = {}
                        if value.get('step') is not None and value['step'] != last_step:
                            print('SINGLE_VIEW_PROGRESS', tag, json.dumps(value), flush=True)
                            last_step = value['step']
                    if time.monotonic() - started > limit:
                        process.terminate()
                        try:
                            process.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=30)
                        failure_receipt('TIMEOUT', tag, process.returncode)
                        raise TimeoutError('Single-view training phase reached its time limit')
        if process.returncode != 0:
            failure_receipt('FAILED_CHILD', tag, process.returncode)
            raise RuntimeError(dict(phase=tag, return_code=process.returncode))
        try:
            report = json.loads((output / 'runtime_receipt.json').read_text())
        except (OSError, json.JSONDecodeError):
            failure_receipt('MISSING_RUNTIME_RECEIPT', tag, process.returncode)
            raise
        return output, report

    probe_output, probe = run_phase(True)
    if not (probe['status'] == 'PASS_PROBE' and probe['actual_steps'] == 64
            and probe['nonfinite_steps'] == 0 and probe['peak_gpu_bytes'] < 13 * (1 << 30)):
        failure_receipt('FAILED_PROBE_GATE', 'probe_spectrum', 0)
        raise RuntimeError('Single-view probe did not satisfy the frozen runtime gate')
    (args.out / 'single_view_probe_gate.json').write_text(json.dumps(dict(status='PASS', report=probe), indent=2))
    print('SINGLE_VIEW_PROBE_GATE', json.dumps(probe), flush=True)
    output, report = run_phase(False)
    complete = (report['status'] == 'COMPLETE_TRAINING' and report['actual_steps'] == 30000
                and report['nonfinite_steps'] == 0 and (output / 'best_full_model.pt').exists())
    if (output / 'best_full_model.pt').exists():
        report.update(weight_sha256=digest(output / 'best_full_model.pt'),
                      weight_bytes=(output / 'best_full_model.pt').stat().st_size)
    receipt = dict(
        status='COMPLETE_TRAINING' if complete else 'INCOMPLETE_RECIPE', report=report,
        probe_report=probe, budget=budget, source_sha256=source_hashes,
        input_binding=input_binding,
        input_hashes_verified=True, final_test_used=False, official_score=None,
        dataset='prvsiyan/casmi26-full-fingerprint-inputs',
        spectra_dataset='prvsiyan/casmi26-spec-fp', seconds=round(time.monotonic() - driver_started, 1),
    )
    (args.out / 'single_view_training_receipt.json').write_text(json.dumps(receipt, indent=2))
    print('SINGLE_VIEW_COMPLETE', json.dumps(receipt), flush=True)
    assert complete, 'Full 30,000-step zero-nonfinite recipe did not complete; preserve partial outputs'


if __name__ == '__main__':
    main()
