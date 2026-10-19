"""Verify the public atlas release file manifest; no model or network."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = args.directory.resolve(strict=True)
    manifest = json.loads((root / 'RELEASE_FILES.json').read_bytes())
    seen = set()
    for item in manifest['files']:
        relative = Path(item['file'])
        if relative.is_absolute() or '..' in relative.parts or relative in seen:
            raise ValueError('Unsafe or duplicate manifest path')
        seen.add(relative)
        path = root / relative
        if not path.is_file() or any((root / Path(*relative.parts[:n])).is_symlink()
                                     for n in range(1, len(relative.parts) + 1)):
            raise ValueError(f'Missing file or symbolic link: {relative}')
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            while block := stream.read(1 << 20):
                digest.update(block)
        if path.stat().st_size != item['bytes'] or digest.hexdigest() != item['sha256']:
            raise ValueError(f'Byte/hash mismatch: {relative}')
    print(f'PASS {len(seen)} listed file identities; no score or quality claim')


if __name__ == '__main__':
    main()
