"""NEW OPT-IN recipe, not the historical S2/M1 training invocation.

Seeds initialization before the unchanged historical trainer, requests strict
PyTorch deterministic kernels, and fails on unsupported operations. This does
not reproduce old weights or guarantee identical results across software/hardware.
Requires a fresh Python process with PYTHONHASHSEED=<seed> and
CUBLAS_WORKSPACE_CONFIG=:4096:8 set before startup. Original trainer arguments
follow -- and must include the same explicit --seed and a new --out path.
This file does not launch Kaggle, download inputs, or modify companion sources.
"""
import argparse
import hashlib
import math
import os
from pathlib import Path
import random
import runpy
import sys
import types

PINS = {
    'train_fp3.py': '43bb618dd512def4ccb1119f813aabce2b9f9bcbfa681c9d2db5adfa05e66840',
    'train_fp4.py': 'e2eaef630c5f09f157eea3652095b8b9780cbe7fdffa6f0652ae5845d7b18c8a',
    'fpmodel.py': '69f2656778a08233e22235bf4853f0b3d2420b431390a32d6c8ed453cde85c76',
}
OPTIONS = {'--steps', '--bs', '--lr', '--d', '--layers', '--K', '--lam',
           '--warm', '--out', '--val_every', '--max_minutes', '--seed',
           '--spec', '--fpdir', '--pooldir'}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--trainer', choices=['train_fp3.py', 'train_fp4.py'], required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('trainer_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    require(args.trainer_args[:1] == ['--'], 'Separate original trainer argv with --')
    argv = args.trainer_args[1:]
    allowed = OPTIONS | ({'--merge_p'} if args.trainer == 'train_fp4.py' else set())
    require(len(argv) % 2 == 0, 'Use explicit --option value pairs')
    options = {}
    for key, value in zip(argv[::2], argv[1::2]):
        require(key in allowed and key not in options, 'Unknown/duplicate trainer option')
        options[key] = value
    require(0 <= args.seed < 2**32, 'Seed must be an unsigned 32-bit integer')
    require(options.get('--seed') == str(args.seed), 'Trainer --seed must exactly match launcher --seed')
    require({'--steps', '--max_minutes', '--out', '--spec', '--fpdir', '--pooldir'} <= options.keys(),
            'Supply explicit training budgets, inputs, and a new output file')
    require(int(options['--steps']) > 0, 'steps must be positive')
    minutes = float(options['--max_minutes'])
    require(math.isfinite(minutes) and minutes > 0, 'max_minutes must be finite and positive')
    destination = Path(options['--out'])
    require(not destination.exists() and not destination.is_symlink(), 'Output path must be new')
    require(not sys.flags.ignore_environment and not sys.flags.isolated,
            'Do not use Python -E or -I; startup PYTHONHASHSEED must be honored')
    require(os.environ.get('PYTHONHASHSEED') == str(args.seed),
            'Start Python with PYTHONHASHSEED equal to --seed')
    require(os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8',
            'Start Python with CUBLAS_WORKSPACE_CONFIG=:4096:8')
    require(os.environ.get('TORCH_ALLOW_TF32_CUBLAS_OVERRIDE', '0') == '0',
            'A forced TF32 override is incompatible with this recipe')
    require(not any(n in sys.modules for n in ['torch', 'fpmodel']),
            'Use a fresh process without preloaded Torch or fpmodel')
    source_dir = Path(__file__).resolve().parent / 'original_sources'
    sources = {}
    for name, expected in PINS.items():
        payload = (source_dir / name).read_bytes()
        require(hashlib.sha256(payload).hexdigest() == expected, 'Historical source hash mismatch: ' + name)
        sources[name] = payload
    os.environ['NVIDIA_TF32_OVERRIDE'] = '0'
    import numpy as np
    import torch
    require(torch.cuda.is_available() or not torch.backends.mps.is_available(),
            'This opt-in recipe supports CPU/CUDA only, not the historical MPS fallback')
    torch.use_deterministic_algorithms(True, warn_only=False)
    torch.set_float32_matmul_precision('highest')
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cuda.enable_flash_sdp(False)
    torch.backends.cuda.enable_mem_efficient_sdp(False)
    torch.backends.cuda.enable_cudnn_sdp(False)
    torch.backends.cuda.enable_math_sdp(True)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    # Load the already hash-checked model source, avoiding an unrelated import or pyc.
    module = types.ModuleType('fpmodel')
    module.__file__ = str(source_dir / 'fpmodel.py')
    exec(compile(sources['fpmodel.py'], module.__file__, 'exec'), module.__dict__)
    sys.modules['fpmodel'] = module
    trainer_path = source_dir / args.trainer
    require(trainer_path.read_bytes() == sources[args.trainer], 'Trainer changed before dispatch')
    sys.argv = [str(trainer_path)] + argv
    # Errors propagate: no warning-only fallback, retry, or nondeterministic recovery.
    runpy.run_path(str(trainer_path), run_name='__main__')


if __name__ == '__main__':
    main()
