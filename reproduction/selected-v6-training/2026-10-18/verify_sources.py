"""Verify the selected V6 training source without importing or running it."""
import ast
import hashlib
import json
from pathlib import Path


def check_sources(sources, contract, notebook_cell):
    expected = contract['source_files']
    if set(sources) != set(expected) or len(sources) != 5:
        raise ValueError('EXACT_FIVE_TRAINING_SOURCES_REQUIRED')
    imports = set()
    for name, raw in sources.items():
        pin = expected[name]
        if len(raw) != pin['bytes'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('TRAINING_SOURCE_BYTES_CHANGED')
        tree = ast.parse(raw, filename=name)
        compile(tree, name, 'exec')  # Compile only; do not execute the code object.
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module.split('.')[0])
    if hashlib.sha256(notebook_cell).hexdigest() != contract['native_fit']['training_cell_sha256']:
        raise ValueError('HISTORICAL_NOTEBOOK_CELL_CHANGED')
    literals = {}
    for node in ast.parse(notebook_cell).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in (
                    'STRUCTURE_UNIFORM_FILES', 'STRUCTURE_UNIFORM_SHA256',
                    'RUN_STRUCTURE_UNIFORM_TRAINING',
                ):
                    literals[target.id] = ast.literal_eval(node.value)
    if (literals.get('RUN_STRUCTURE_UNIFORM_TRAINING') is not True
            or set(literals.get('STRUCTURE_UNIFORM_FILES', {})) != set(sources)
            or literals.get('STRUCTURE_UNIFORM_SHA256') != {
                name: pin['sha256'] for name, pin in expected.items()}):
        raise ValueError('HISTORICAL_SOURCE_BINDING_CHANGED')
    if any(literals['STRUCTURE_UNIFORM_FILES'][name].encode('utf-8') != raw
           for name, raw in sources.items()):
        raise ValueError('HISTORICAL_PAYLOAD_BYTES_CHANGED')
    return {'status': 'PASS_SELECTED_V6_TRAINING_SOURCE_ONLY', 'source_files': 5,
            'exact_historical_notebook_payload_match': True,
            'import_names_found_by_ast': sorted(imports),
            'scientific_modules_imported': False, 'data_or_weights_read': False,
            'training_launched': False, 'assay_repeated': False}


def main():
    folder = Path(__file__).resolve().parent
    contract = json.loads((folder / 'TRAINING_CONTRACT.json').read_text())
    sources = {name: (folder / name).read_bytes() for name in contract['source_files']}
    result = check_sources(sources, contract,
                           (folder / 'historical_notebook_training_cell.source.txt').read_bytes())
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
