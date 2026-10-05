"""Run the byte-exact numerical study in a fresh, retained POSIX directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PINS = {
    'projection_parity_study.py': '9203c656c783d86244469a43816ffe13e77e43663d0ee14a92892342c7828678',
    'frozen_energy_authority.py': 'da9b7861fd07bf49ad864dbf9a1e795dea8c573b3744b7d4d2665944ede3ad8c',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='New run directory; its parent must exist. Existing paths are refused.')
    args = parser.parse_args()
    if os.name != 'posix' or sys.version_info[:2] != (3, 12):
        parser.error('The verified runtime requires POSIX and Python3.12 for resource limits.')
    try:
        import numpy
    except ImportError:
        parser.error('Install the NumPy dependency in requirements.txt first.')
    if numpy.__version__ != '2.2.6':
        parser.error('The verified runtime requires numpy==2.2.6.')
    source_bytes = {}
    for name, expected in PINS.items():
        content = (HERE / name).read_bytes()
        if hashlib.sha256(content).hexdigest() != expected:
            parser.error('Source pin mismatch: ' + name)
        source_bytes[name] = content
    destination = args.output.expanduser().resolve()
    if destination.exists():
        parser.error('Output already exists; choose a fresh run directory.')
    if not destination.parent.is_dir():
        parser.error('Output parent directory does not exist.')
    destination.mkdir(exist_ok=False)
    study = destination / 'study'
    authority = destination / 'codex_enveda_alignment_learning_20261005T144407Z'
    study.mkdir()
    authority.mkdir()
    with (study / 'projection_parity_study.py').open('xb') as stream:
        stream.write(source_bytes['projection_parity_study.py'])
    with (authority / 'energy_balanced_objective.py').open('xb') as stream:
        stream.write(source_bytes['frozen_energy_authority.py'])
    environment = os.environ.copy()
    environment.update(PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1',
                       MKL_NUM_THREADS='1', OMP_NUM_THREADS='1')
    process = subprocess.run([sys.executable, str(study / 'projection_parity_study.py')],
                             cwd=str(destination), env=environment, timeout=90, check=False)
    if process.returncode != 0:
        print('Study failed; retained partial artifacts are in ' + str(destination), file=sys.stderr)
        return process.returncode
    receipt_path = study / 'terminal_receipt.json'
    receipt = json.loads(receipt_path.read_text())
    if receipt.get('status') != 'PASS_SYNTHETIC_FP64_PROJECTION_NUMERICAL_CONTRACT_ONLY':
        print('Terminal numerical contract did not pass.', file=sys.stderr)
        return 2
    print(json.dumps({'retained_run': str(destination), 'receipt': str(receipt_path),
                      'checks_passed': receipt['checks_passed']}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
