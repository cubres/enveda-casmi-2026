# SPDX-License-Identifier: MIT
"""Original MIT source: conservative raw molblock SubstanceGroup scope inspection.

Pure text/stdlib only: no file IO, RDKit, fingerprints, canonicalization or bank.
An admit_scope decision means only that this scanner found no SGroup; all
existing chemical, mass, isotope/stereo, fingerprint and alignment gates remain.
Unknown/malformed source syntax is HOLD, never evidence of SGroup absence.
"""
from collections import Counter
import hashlib
import re

POLYMER = frozenset('SRU MON COP CRO GRA MOD MER ANY'.split())
FORMULATION = frozenset('COM MIX FOR'.split())
OTHER = frozenset('SUP MUL DAT GEN'.split())
GROUP_TYPES = POLYMER | FORMULATION | OTHER
# Type categories: RDKit Release_2026_03_3 Code/GraphMol/SubstanceGroup.h,
# lines 220-226; root supplied the primary-source observation. No RDKit import.
# Standard SGroup property records. Opaque free-text payloads remain verbatim;
# this scope scanner never needs to interpret them as molecular identities.
V2_GROUP_CODES = frozenset('STY SST SLB SCN SAL SPA SBL SMT SBV SDI SDS SDT SDD SCD SED SPL SNC SBT SAP SCL'.split())
V2_NON_GROUP_CODES = frozenset('CHG RAD ISO ALS RGP APO AAL LOG LIN RBC SUB UNS ZCH HYD ZBO'.split())
MAX_BYTES = 2 * 1024 * 1024
MAX_LINES = 100000
MAX_INTEGER_DIGITS = 32


class ScopeSyntaxError(ValueError):
    pass


def demand(ok, code):
    if not ok:
        raise ScopeSyntaxError(code)


def integer(token, minimum=0):
    # Bound conversion before int(): malformed, very long decimal fields must
    # return HOLD independently of Python's configurable conversion limit.
    demand(len(token) <= MAX_INTEGER_DIGITS, 'integer_token_limit')
    demand(re.fullmatch(r'[0-9]+', token) is not None, 'invalid_nonnegative_integer')
    value = int(token)
    demand(value >= minimum, 'integer_below_minimum')
    return value


def category(kind):
    return ('polymer' if kind in POLYMER else 'formulation_or_mixture' if kind in FORMULATION
            else 'other' if kind in OTHER else 'unresolved')


def new_group(identifier, kind):
    return dict(id=identifier, type=kind, category=category(kind), atoms=[], bonds=[],
                parent_atoms=[], labels=[], attributes=[], annotation_lines=[])


def source_id(lines, after_end):
    """Read only the ChEBI-ID property; metadata never enters annotation scans."""
    index, identifier = after_end, None
    while index < len(lines):
        if lines[index].strip() == '$$$$':
            break
        match = re.fullmatch(r'>\s*<([^>]+)>.*', lines[index])
        if match is None:
            index += 1
            continue
        index += 1
        values = []
        while index < len(lines) and lines[index] != '' and lines[index].strip() != '$$$$':
            values.append(lines[index])
            index += 1
        if match.group(1) == 'ChEBI ID':
            demand(identifier is None, 'duplicate_chebi_id_metadata')
            value = '\n'.join(values).strip()
            demand(re.fullmatch(r'CHEBI:[0-9]+', value) is not None, 'invalid_chebi_id_metadata')
            identifier = value
    return identifier


def annotation(result, code, raw, start, end=None):
    result['annotations'].append(dict(code=code, first_line=start + 1,
        last_line=(start if end is None else end) + 1, raw_lines=list(raw)))


def inspect_v2000(lines, end, result):
    counts = lines[3]
    atoms, bonds = integer(counts[:3].strip()), integer(counts[3:6].strip())
    result['declared_counts'] = dict(atoms=atoms, bonds=bonds)
    first_property = 4 + atoms + bonds
    demand(first_property <= end, 'truncated_v2000_atom_or_bond_block')
    for number in range(4, first_property):
        if re.match(r'M\s+S[A-Z0-9]{2}', lines[number]):
            annotation(result, 'V2000_MISPLACED_SGROUP_INDICATOR', [lines[number]], number)
            raise ScopeSyntaxError('v2000_sgroup_indicator_inside_atom_or_bond_block')
    groups, references = {}, []
    index = first_property
    while index < end:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        # An atom alias has one literal next line. A label containing an SGroup
        # keyword is text, not a property record.
        alias = re.fullmatch(r'A\s+([0-9]+)\s*', line)
        if alias:
            demand(1 <= integer(alias.group(1), 1) <= atoms and index + 1 < end,
                   'malformed_v2000_atom_alias')
            index += 2
            continue
        if re.fullmatch(r'V\s+[0-9]+\s+.*', line):
            index += 1
            continue
        match = re.fullmatch(r'M\s+([A-Z0-9]{3})(?:\s+(.*))?', line)
        if match is None:
            annotation(result, 'V2000_UNRESOLVED_PROPERTY', [line], index)
        demand(match is not None, 'unresolved_v2000_property_record')
        code, payload = match.group(1), match.group(2) or ''
        if code in V2_GROUP_CODES or code.startswith('S'):
            annotation(result, code, [line], index)
        demand(code in V2_GROUP_CODES | V2_NON_GROUP_CODES, 'unresolved_v2000_property_code')
        if code in V2_NON_GROUP_CODES:
            index += 1
            continue
        tokens = payload.split()
        if code == 'STY':
            demand(tokens, 'missing_v2000_sty_count')
            count = integer(tokens[0], 1)
            demand(len(tokens) == 1 + 2 * count, 'malformed_v2000_sty_pairs')
            for offset in range(count):
                identifier = integer(tokens[1 + 2 * offset], 1)
                demand(identifier not in groups, 'duplicate_v2000_group_id')
                group = new_group(identifier, tokens[2 + 2 * offset])
                group['annotation_lines'].append(index + 1)
                groups[identifier] = group
                result['groups'].append(group)
                demand(group['type'] in GROUP_TYPES, 'unresolved_source_sgroup_type')
        elif code in {'SAL', 'SPA', 'SBL'}:
            demand(len(tokens) >= 2, 'malformed_v2000_group_membership')
            identifier, count = integer(tokens[0], 1), integer(tokens[1])
            demand(len(tokens) == 2 + count, 'malformed_v2000_membership_count')
            members = [integer(token, 1) for token in tokens[2:]]
            limit = bonds if code == 'SBL' else atoms
            demand(all(member <= limit for member in members), 'v2000_membership_out_of_range')
            references.append((identifier, code, members, index + 1))
        elif code in {'SST', 'SLB', 'SCN', 'SPL', 'SNC', 'SBT'}:
            demand(tokens, 'missing_v2000_group_pair_count')
            count = integer(tokens[0], 1)
            demand(len(tokens) == 1 + 2 * count, 'malformed_v2000_group_pairs')
            for offset in range(count):
                identifier = integer(tokens[1 + 2 * offset], 1)
                references.append((identifier, code, tokens[2 + 2 * offset], index + 1))
        elif code == 'SDS':
            demand(len(tokens) >= 2 and tokens[0] == 'EXP', 'malformed_v2000_sds')
            count = integer(tokens[1], 1)
            demand(len(tokens) == 2 + count, 'malformed_v2000_sds_count')
            references.extend((integer(token, 1), code, payload, index + 1) for token in tokens[2:])
        else:
            demand(tokens, 'missing_v2000_annotation_group_id')
            identifier = integer(tokens[0], 1)
            demand(len(tokens) >= 2 or code in {'SCD', 'SED', 'SMT'}, 'missing_v2000_annotation_payload')
            references.append((identifier, code, payload[len(tokens[0]):].lstrip(), index + 1))
        index += 1
    demand(groups or not references, 'orphan_v2000_sgroup_annotations')
    for identifier, code, payload, line_number in references:
        demand(identifier in groups, 'orphan_v2000_sgroup_reference')
        group = groups[identifier]
        group['annotation_lines'].append(line_number)
        if code in {'SAL', 'SPA', 'SBL'}:
            name = {'SAL': 'atoms', 'SPA': 'parent_atoms', 'SBL': 'bonds'}[code]
            demand(not set(group[name]).intersection(payload) and len(payload) == len(set(payload)),
                   'duplicate_v2000_group_member')
            group[name].extend(payload)
        elif code == 'SMT':
            group['labels'].append(payload)
        else:
            group['attributes'].append(dict(code=code, value=payload))
    return groups


def v30_tokens(text):
    """V3000 whitespace tokens, quoted strings and balanced parenthesized lists."""
    tokens, current, depth, quoted, index = [], [], 0, False, 0
    while index < len(text):
        char = text[index]
        if char == '"':
            current.append(char)
            if quoted and index + 1 < len(text) and text[index + 1] == '"':
                current.append('"')
                index += 1
            else:
                quoted = not quoted
        elif not quoted and char in '()':
            depth += 1 if char == '(' else -1
            demand(depth >= 0, 'unbalanced_v3000_list')
            current.append(char)
        elif not quoted and depth == 0 and char.isspace():
            if current:
                tokens.append(''.join(current))
                current = []
        else:
            current.append(char)
        index += 1
    demand(not quoted and depth == 0, 'unterminated_v3000_quote_or_list')
    if current:
        tokens.append(''.join(current))
    return tokens


def v30_logical(lines, end, result):
    chunks, first = [], None
    for index in range(4, end):
        match = re.fullmatch(r'M\s+V30\s+(.*)', lines[index])
        if match is None:
            annotation(result, 'V3000_UNRESOLVED_PHYSICAL_RECORD', [lines[index]], index)
        demand(match is not None, 'unresolved_v3000_physical_record')
        body = match.group(1)
        if first is None:
            first = index
        continued = body.endswith('-')
        chunks.append(body[:-1] if continued else body)
        if not continued:
            try:
                tokens = v30_tokens(''.join(chunks))
            except ScopeSyntaxError:
                annotation(result, 'V3000_UNRESOLVED_LOGICAL_RECORD', lines[first:index + 1], first, index)
                raise
            yield tokens, first, index
            chunks, first = [], None
    if chunks:
        annotation(result, 'V3000_UNTERMINATED_CONTINUATION', lines[first:end], first, end - 1)
    demand(not chunks, 'unterminated_v3000_continuation')


def v30_list(value):
    demand(value.startswith('(') and value.endswith(')'), 'malformed_v3000_membership_list')
    tokens = value[1:-1].split()
    demand(tokens, 'missing_v3000_list_count')
    count = integer(tokens[0])
    demand(len(tokens) == count + 1, 'malformed_v3000_list_count')
    members = [integer(token, 1) for token in tokens[1:]]
    demand(len(members) == len(set(members)), 'duplicate_v3000_membership')
    return members


def inspect_v3000(lines, end, result):
    groups, stack, counts, atom_ids, bond_ids = {}, [], None, set(), set()
    seen_blocks = set()
    for tokens, first, last in v30_logical(lines, end, result):
        demand(tokens, 'empty_v3000_logical_record')
        if tokens[0] in {'BEGIN', 'END'}:
            if 'SGROUP' in tokens[1:]:
                annotation(result, 'V3000_' + tokens[0] + '_SGROUP', lines[first:last + 1], first, last)
            demand(len(tokens) == 2, 'malformed_v3000_section_directive')
            name = tokens[1]
            demand(name in {'CTAB', 'ATOM', 'BOND', 'SGROUP', 'COLLECTION'}, 'unresolved_v3000_section')
            if tokens[0] == 'BEGIN':
                demand(name not in seen_blocks and (not stack if name == 'CTAB' else stack == ['CTAB']),
                       'misnested_or_duplicate_v3000_section')
                if name != 'CTAB':
                    demand(counts is not None, 'v3000_counts_missing_before_section')
                seen_blocks.add(name)
                stack.append(name)
            else:
                demand(stack and stack[-1] == name, 'mismatched_v3000_section_end')
                stack.pop()
            continue
        demand(stack, 'v3000_record_outside_ctab')
        section = stack[-1]
        if section == 'CTAB':
            demand(tokens[0] == 'COUNTS' and counts is None and len(tokens) == 6,
                   'unresolved_v3000_ctab_record')
            counts = [integer(token) for token in tokens[1:]]
            result['declared_counts'] = dict(atoms=counts[0], bonds=counts[1], sgroups=counts[2])
            if counts[2]:
                annotation(result, 'V3000_DECLARED_SGROUP_COUNT', lines[first:last + 1], first, last)
            demand(counts[3] == 0, 'unsupported_v3000_3d_constraints')
        elif section in {'ATOM', 'BOND'}:
            identifier = integer(tokens[0], 1)
            ids = atom_ids if section == 'ATOM' else bond_ids
            demand(identifier not in ids and len(tokens) >= (6 if section == 'ATOM' else 4),
                   'malformed_or_duplicate_v3000_atom_bond_record')
            ids.add(identifier)
        elif section == 'COLLECTION':
            # Enhanced stereo collections remain for the original chemistry gate.
            demand(re.fullmatch(r'MDLV30/(?:STEABS|STEREL[1-9][0-9]*|STERAC[1-9][0-9]*)', tokens[0])
                   is not None, 'unresolved_v3000_collection')
        else:
            annotation(result, 'V3000_SGROUP', lines[first:last + 1], first, last)
            demand(len(tokens) >= 3, 'malformed_v3000_sgroup_record')
            identifier, kind = integer(tokens[0], 1), tokens[1]
            integer(tokens[2])  # external index
            demand(identifier not in groups, 'duplicate_v3000_sgroup_id')
            group = new_group(identifier, kind)
            group['annotation_lines'].extend(range(first + 1, last + 2))
            groups[identifier] = group
            result['groups'].append(group)
            demand(kind in GROUP_TYPES, 'unresolved_source_sgroup_type')
            keys = set()
            for token in tokens[3:]:
                demand('=' in token, 'malformed_v3000_sgroup_attribute')
                key, value = token.split('=', 1)
                demand(re.fullmatch(r'[A-Z][A-Z0-9_]*', key) is not None and key not in keys and value,
                       'duplicate_or_malformed_v3000_sgroup_attribute')
                keys.add(key)
                if key in {'ATOMS', 'PATOMS', 'XBONDS', 'CBONDS'}:
                    name = {'ATOMS': 'atoms', 'PATOMS': 'parent_atoms', 'XBONDS': 'bonds', 'CBONDS': 'bonds'}[key]
                    members = v30_list(value)
                    demand(not set(group[name]).intersection(members), 'duplicate_v3000_group_member')
                    group[name].extend(members)
                elif key == 'LABEL':
                    group['labels'].append(value)
                else:
                    group['attributes'].append(dict(code=key, value=value))
    demand(not stack and 'CTAB' in seen_blocks and counts is not None, 'incomplete_v3000_ctab')
    demand(len(atom_ids) == counts[0] and len(bond_ids) == counts[1], 'v3000_atom_bond_count_mismatch')
    demand(len(groups) == counts[2] and (bool(groups) == ('SGROUP' in seen_blocks)),
           'v3000_sgroup_count_or_section_mismatch')
    for group in groups.values():
        demand(set(group['atoms'] + group['parent_atoms']) <= atom_ids and set(group['bonds']) <= bond_ids,
               'v3000_membership_references_undeclared_id')
    return groups


def inspect_sdf_record(record, record_ordinal=None):
    """Return JSON-safe scope/provenance; do not canonicalize or validate chemistry."""
    body = record.encode('utf-8') if isinstance(record, str) else record
    if not isinstance(body, bytes):
        raise TypeError('record must be str or bytes')
    result = dict(schema='raw-molblock-sgroup-scope/1', record_ordinal=record_ordinal,
        record_sha256=hashlib.sha256(body).hexdigest(), record_bytes=len(body), chebi_id=None,
        molfile_version=None, status='hold', reason='unresolved_molblock_framing',
        inspection_complete=False, annotations=[], groups=[], source_group_types=[], declared_counts={})
    try:
        demand(len(body) <= MAX_BYTES, 'record_byte_limit')
        lines = body.decode('utf-8', errors='strict').splitlines()
        demand(4 <= len(lines) <= MAX_LINES, 'molblock_line_limit_or_missing_header')
        delimiters = [index for index, line in enumerate(lines) if line.strip() == '$$$$']
        demand(len(delimiters) <= 1 and
               (not delimiters or not any(line.strip() for line in lines[delimiters[0] + 1:])),
               'multiple_sdf_records_not_supported')
        end = next((index for index in range(4, len(lines)) if re.fullmatch(r'M\s+END\s*', lines[index])), None)
        demand(end is not None, 'molblock_end_missing')
        result['chebi_id'] = source_id(lines, end + 1)
        demand(not any(line.lstrip().startswith('>') or line.strip() == '$$$$' for line in lines[4:end]),
               'sdf_metadata_before_molblock_end')
        match = re.search(r'\b(V2000|V3000)\s*$', lines[3])
        demand(match is not None, 'unresolved_molfile_version')
        result['molfile_version'] = match.group(1)
        groups = (inspect_v2000 if match.group(1) == 'V2000' else inspect_v3000)(lines, end, result)
        result['groups'] = [groups[key] for key in sorted(groups)]
        result['source_group_types'] = sorted({group['type'] for group in groups.values()})
        result['inspection_complete'] = True
        if not groups:
            result.update(status='admit_scope', reason='no_source_substance_groups_detected')
        else:
            reason = ('source_polymer_sru_outside_finite_graph_contract' if 'SRU' in result['source_group_types']
                      else 'source_polymer_substance_group_outside_finite_graph_contract'
                      if any(kind in POLYMER for kind in result['source_group_types'])
                      else 'source_substance_group_outside_supported_contract')
            result.update(status='exclude_scope', reason=reason)
    except (ScopeSyntaxError, UnicodeError) as exc:
        result.update(status='hold', reason=str(exc) if isinstance(exc, ScopeSyntaxError) else 'invalid_utf8_record')
    result['source_group_types'] = sorted({group['type'] for group in result['groups']})
    return result


def count_decision(counts, decision):
    """Count once per inspected record; type counts are separate from reason counts."""
    counts.setdefault('records_by_status', Counter())[decision['status']] += 1
    counts.setdefault('records_by_reason', Counter())[decision['reason']] += 1
    for group in decision['groups']:
        counts.setdefault('groups_by_type', Counter())[group['type']] += 1
