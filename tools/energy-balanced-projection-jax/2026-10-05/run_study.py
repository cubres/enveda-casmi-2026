"""Reproduce the preserved CPU-only pure-JAX study in a fresh retained directory."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PINS = {
    'jax_projection_parity.py': 'a584784cf625740528d1b3dc0dcb51d4292dc7e564bc0f87ea10fabeadca7741',
    'frozen_energy_authority.py': 'da9b7861fd07bf49ad864dbf9a1e795dea8c573b3744b7d4d2665944ede3ad8c',
}
DEPENDENCIES = {'jax': '0.11.0', 'jaxlib': '0.11.0', 'numpy': '2.2.6'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path,
                        help='Fresh retained run directory; its parent must exist.')
    args = parser.parse_args()
    if os.name != 'posix' or sys.version_info[:2] != (3, 12):
        parser.error('The verified resource-limited runtime requires POSIX Python3.12.')
    for distribution, expected in DEPENDENCIES.items():
        try:
            observed = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            parser.error('Missing dependency: ' + distribution)
        if observed != expected:
            parser.error('Pinned dependency mismatch: ' + distribution)
    content = {}
    for name, expected in PINS.items():
        data = (HERE / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            parser.error('Source pin mismatch: ' + name)
        content[name] = data
    destination = args.output.expanduser().resolve()
    if destination.exists():
        parser.error('Output already exists; choose a fresh directory.')
    if not destination.parent.is_dir():
        parser.error('Output parent does not exist.')
    destination.mkdir(exist_ok=False)
    study = destination / 'study'
    authority = destination / 'codex_enveda_projection_parity_20261005T160447Z'
    study.mkdir()
    authority.mkdir()
    with (study / 'jax_projection_parity.py').open('xb') as stream:
        stream.write(content['jax_projection_parity.py'])
    with (authority / 'frozen_energy_authority.py').open('xb') as stream:
        stream.write(content['frozen_energy_authority.py'])
    environment = os.environ.copy()
    environment.update(PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1',
                       MKL_NUM_THREADS='1', OMP_NUM_THREADS='1',
                       TF_NUM_INTRAOP_THREADS='1', TF_NUM_INTEROP_THREADS='1',
                       JAX_PLATFORMS='cpu', XLA_FLAGS='--xla_cpu_multi_thread_eigen=false')
    try:
        result = subprocess.run([sys.executable, str(study/'jax_projection_parity.py')],
                                cwd=str(destination), env=environment,
                                timeout=60, check=False)
    except subprocess.TimeoutExpired:
        print('Wall limit reached; partial artifacts are retained in '+str(destination), file=sys.stderr)
        return 124
    if result.returncode != 0:
        print('Study failed; partial artifacts are retained in '+str(destination), file=sys.stderr)
        return result.returncode
    receipt_path = study/'terminal_receipt.json'
    receipt = json.loads(receipt_path.read_text())
    expected_status = 'PASS_CPU_JAX_SYNTHETIC_FIXED_MASK_NUMERICAL_READINESS_ONLY'
    if receipt.get('status') != expected_status or receipt.get('checks_passed') != 15:
        print('Terminal numerical contract did not pass.', file=sys.stderr)
        return 2
    print(json.dumps({'receipt':str(receipt_path), 'retained_run':str(destination),
                      'checks_passed':receipt['checks_passed']}, sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
