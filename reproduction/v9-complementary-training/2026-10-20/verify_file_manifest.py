"""Byte/hash verification only; no model imports, source execution or deletion."""
import argparse
import hashlib
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    root = args.directory.resolve(strict=True)
    manifest = json.loads((root / 'PUBLIC_FILE_MANIFEST.json').read_bytes())
    seen = set()
    for item in manifest['files']:
        relative = Path(item['file'])
        if relative.is_absolute() or '..' in relative.parts or relative in seen:
            raise ValueError(f'Unsafe or repeated manifest path: {relative}')
        seen.add(relative)
        path = root / relative
        if not path.is_file() or any((root / Path(*relative.parts[:n])).is_symlink()
                                     for n in range(1, len(relative.parts) + 1)):
            raise ValueError(f'Missing file or symbolic link: {relative}')
        if path.stat().st_size != item['bytes']:
            raise ValueError(f'Byte count mismatch: {relative}')
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            while block := stream.read(8 << 20):
                digest.update(block)
        if digest.hexdigest() != item['sha256']:
            raise ValueError(f'SHA256 mismatch: {relative}')
    print('PASS listed bytes/SHA256; no model or score qualification')

if __name__=='__main__':main()
