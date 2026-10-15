#!/usr/bin/env python3
"""Small, attributable ChEBI record download and schema check; standard library only.

This does not calculate fingerprints, qualify chemistry, evaluate a model, or
claim that an API snapshot belongs to a monthly ChEBI release.
"""
import argparse
import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import urllib.request

MAX_BYTES = 256 * 1024
BASE = 'https://www.ebi.ac.uk/chebi/backend/api/public/compound/'
LICENSE = 'https://creativecommons.org/licenses/by/4.0/'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def nonfinite(_value):
        raise ValueError('Nonfinite JSON number')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def validate_record(record, expected_id):
    require(type(record) is dict, 'Expected a JSON object')
    require(type(record.get('id')) is int and record['id'] == expected_id,
            'ChEBI numeric ID differs')
    require(record.get('chebi_accession') == f'CHEBI:{expected_id}', 'Accession differs')
    require(record.get('is_released') is True, 'Record is not marked released')
    require(type(record.get('stars')) is int and record['stars'] == 3,
            'This example accepts three-star curated records only')
    chemical = record.get('chemical_data')
    structure = record.get('default_structure')
    require(type(chemical) is dict and type(structure) is dict,
            'Explicit chemical data and a default structure are required')
    require(type(chemical.get('charge')) is int and chemical['charge'] == 0,
            'This example accepts neutral entities only')
    require(structure.get('is_r_group') is False, 'R-group status is absent or not false')
    for field, source in [('formula', chemical), ('smiles', structure),
                          ('standard_inchi', structure), ('standard_inchi_key', structure)]:
        require(type(source.get(field)) is str and bool(source[field].strip()),
                f'Missing string: {field}')
    require(structure['standard_inchi'].startswith('InChI=1S/'), 'Expected standard InChI')
    require(re.fullmatch(r'[A-Z]{14}-[A-Z]{10}-[A-Z]', structure['standard_inchi_key']) is not None,
            'Unexpected standard InChIKey syntax')
    for name in ('mass', 'monoisotopic_mass'):
        require(type(chemical.get(name)) is str, f'Expected decimal string: {name}')
        try:
            value = Decimal(chemical[name])
        except InvalidOperation as error:
            raise ValueError(f'Invalid decimal: {name}') from error
        require(value.is_finite() and value > 0, f'Nonpositive or nonfinite {name}')
    return {
        'chebi_accession': record['chebi_accession'], 'name': record.get('name'),
        'formula': chemical['formula'], 'charge': chemical['charge'],
        'average_mass_da': chemical['mass'],
        'monoisotopic_mass_da': chemical['monoisotopic_mass'],
        'smiles': structure['smiles'], 'standard_inchi': structure['standard_inchi'],
        'standard_inchi_key': structure['standard_inchi_key'],
        'source_modified_on': record.get('modified_on'),
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect refused; inspect the official endpoint before changing it')


def read_small(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, 'Response exceeds 256 KiB')
    return raw


def fetch_small(url):
    request = urllib.request.Request(url, headers={
        'Accept': 'application/json', 'User-Agent': 'CASMI-ChEBI-schema-demo/1.0'})
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=20) as response:
        require(response.status == 200 and response.url == url, 'Unexpected response')
        require(response.headers.get_content_type() == 'application/json', 'Expected JSON content type')
        length = response.headers.get('Content-Length')
        require(length is None or int(length) <= MAX_BYTES, 'Response exceeds 256 KiB')
        raw = response.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, 'Response exceeds 256 KiB')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chebi-id', type=int, default=27732)
    parser.add_argument('--output', type=Path, required=True, help='A new directory; never overwritten')
    parser.add_argument('--input', type=Path, help='Validate an existing API JSON without network access')
    parser.add_argument('--expected-sha256', help='Optional exact raw API snapshot hash')
    args = parser.parse_args()
    require(0 < args.chebi_id <= 10**9, 'Invalid ChEBI ID')
    require(not args.output.exists(), 'Choose a new output directory')
    url = BASE + str(args.chebi_id) + '/'
    raw = read_small(args.input) if args.input else fetch_small(url)
    digest = hashlib.sha256(raw).hexdigest()
    require(args.expected_sha256 is None or digest == args.expected_sha256,
            'Snapshot hash differs; no silent refresh')
    candidate = validate_record(strict_json(raw), args.chebi_id)
    receipt = {
        'schema': 'chebi-small-candidate-schema-demo/1', 'source_url': url,
        'validated_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'input_mode': 'existing_snapshot' if args.input else 'fresh_public_GET',
        'bytes': len(raw), 'sha256': digest, 'monthly_data_release': None,
        'data_license': 'CC-BY-4.0', 'license_url': LICENSE,
        'attribution': 'ChEBI, EMBL-EBI; source URL and snapshot hash above; CC BY 4.0.',
        'transformation': 'Selected and renamed fields only; original decimal strings and structure identifiers retained.',
        'scope': 'Schema checks only. No chemical normalization, polymer qualification, fingerprint compatibility, model evaluation or competition score.',
    }
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / 'source.json').open('xb') as stream:
        stream.write(raw)
    for name, value in [('candidate.json', candidate), ('receipt.json', receipt)]:
        with (args.output / name).open('x') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    print(json.dumps({'accession': candidate['chebi_accession'], 'bytes': len(raw),
                      'sha256': digest, 'output': str(args.output)}, sort_keys=True))


if __name__ == '__main__':
    main()
