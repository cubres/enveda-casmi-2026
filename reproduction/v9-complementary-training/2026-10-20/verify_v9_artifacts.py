"""Verify two already-downloaded native V9 artifacts; no network or model imports."""
import argparse
import hashlib
import json
from pathlib import Path


def check(directory, manifest):
    if manifest['native_run_id'] != 360180749 or manifest['public_version'] != 9:
        raise ValueError('Manifest must identify native V9 / 360180749')
    expected_names = {'complementary_full_model.pt', 'optimizer_state.pt'}
    items = manifest['files']
    if len(items) != 2 or {item['file'] for item in items} != expected_names:
        raise ValueError('Expected the two V9 model/state artifacts')
    for item in items:
        name = item['file']
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Missing file or symbolic link: {name}')
        if path.stat().st_size != item['bytes']:
            raise ValueError(f'Byte count mismatch: {name}')
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            while block := stream.read(8 << 20):
                digest.update(block)
        if digest.hexdigest() != item['sha256']:
            raise ValueError(f'SHA256 mismatch: {name}')
    return len(items)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(Path(__file__).with_name('ARTIFACTS.json').read_bytes())
    count = check(args.directory, manifest)
    print(f'PASS {count} native V9 artifact byte/hash identities; no quality or eligibility claim')


if __name__ == '__main__':
    main()
