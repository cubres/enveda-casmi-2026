# SPDX-License-Identifier: MIT
"""Synthetic text-only test SOURCE; authors/reviewers must not execute/import it.

No archive, public molecule, RDKit, model, fingerprint, bank or controller.
These invented CTAB strings test scanner framing, not chemical validity. A
future explicitly authorized test run would use stdlib unittest only.
"""
import hashlib
import unittest

from raw_molblock_sgroup_scope import MAX_BYTES, MAX_INTEGER_DIGITS, count_decision, inspect_sdf_record


def v2(properties=(), title='invented text fixture', metadata=None):
    lines = [title, 'synthetic source only', '',
             '  3  2  0  0  0  0            999 V2000',
             '    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0',
             '    1.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0',
             '    2.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0',
             '  1  2  1  0  0  0  0', '  2  3  1  0  0  0  0']
    lines.extend(properties)
    lines.append('M  END')
    lines.extend(metadata if metadata is not None else ['> <ChEBI ID>', 'CHEBI:999999999', ''])
    return '\n'.join(lines) + '\n'


def v3(group_lines=None, declared_groups=None, extra_ctab=(), metadata=None):
    """Noncontiguous IDs ensure membership is resolved against IDs, not counts."""
    count = (0 if group_lines is None else len(group_lines)) if declared_groups is None else declared_groups
    lines = ['invented V3000 fixture', 'synthetic source only', '',
             '  0  0  0  0  0  0            999 V3000',
             'M  V30 BEGIN CTAB', f'M  V30 COUNTS 2 1 {count} 0 0',
             'M  V30 BEGIN ATOM', 'M  V30 10 C 0 0 0 0', 'M  V30 20 O 1 0 0 0',
             'M  V30 END ATOM', 'M  V30 BEGIN BOND', 'M  V30 7 1 10 20', 'M  V30 END BOND']
    if group_lines is not None:
        lines.append('M  V30 BEGIN SGROUP')
        lines.extend('M  V30 ' + line for line in group_lines)
        lines.append('M  V30 END SGROUP')
    lines.extend(extra_ctab)
    lines.extend(['M  V30 END CTAB', 'M  END'])
    lines.extend(metadata if metadata is not None else ['> <ChEBI ID>', 'CHEBI:999999999', ''])
    return '\n'.join(lines) + '\n'


class RawScopeSyntheticTests(unittest.TestCase):
    def check_status(self, record, status, reason=None):
        decision = inspect_sdf_record(record, record_ordinal=17)
        self.assertEqual(decision['status'], status)
        self.assertEqual(decision['inspection_complete'], status != 'hold')
        if reason is not None:
            self.assertEqual(decision['reason'], reason)
        self.assertEqual(decision['record_ordinal'], 17)
        return decision

    def test_v2000_no_groups_scope_only(self):
        decision = self.check_status(v2(), 'admit_scope')
        self.assertEqual(decision['molfile_version'], 'V2000')
        self.assertEqual(decision['groups'], [])

    def test_metadata_keywords_never_become_annotations(self):
        metadata = ['> <ChEBI ID>', 'CHEBI:999999999', '', '> <NOTES>',
                    'M  STY  1   1 SRU', 'M  V30 BEGIN SGROUP', 'SRU',
                    '> <ChEBI ID>', 'CHEBI:111111111', '']
        for record in (v2(metadata=metadata), v3(metadata=metadata)):
            with self.subTest(version=record.splitlines()[3]):
                decision = self.check_status(record, 'admit_scope')
                self.assertEqual(decision['annotations'], [])
                self.assertEqual(decision['chebi_id'], 'CHEBI:999999999')

    def test_title_and_atom_alias_are_literal_text(self):
        decision = self.check_status(v2(['A    1', 'M  STY  1   1 SRU'],
                                       title='M  STY  1   1 SRU'), 'admit_scope')
        self.assertEqual(decision['annotations'], [])

    def test_v2000_sru_provenance(self):
        record = v2(['M  STY  1   1 SRU', 'M  SAL   1  2   1   2',
                     'M  SBL   1  1   2', 'M  SMT   1 n'])
        decision = self.check_status(record, 'exclude_scope',
            'source_polymer_sru_outside_finite_graph_contract')
        self.assertEqual(decision['record_sha256'], hashlib.sha256(record.encode()).hexdigest())
        self.assertEqual(decision['chebi_id'], 'CHEBI:999999999')
        self.assertEqual(decision['groups'][0]['atoms'], [1, 2])
        self.assertEqual(decision['groups'][0]['bonds'], [2])
        self.assertEqual(decision['groups'][0]['labels'], ['n'])
        self.assertEqual(decision['annotations'][0]['raw_lines'], ['M  STY  1   1 SRU'])

    def test_all_known_v2000_group_types_outside_contract(self):
        for kind in 'SRU MON COP CRO GRA MOD MER ANY COM MIX FOR SUP MUL DAT GEN'.split():
            with self.subTest(kind=kind):
                decision = self.check_status(v2([f'M  STY  1   1 {kind}']), 'exclude_scope')
                self.assertEqual(decision['source_group_types'], [kind])

    def test_v2000_orphan_membership_holds(self):
        decision = self.check_status(v2(['M  SAL   1  1   1']), 'hold',
                                     'orphan_v2000_sgroup_annotations')
        self.assertEqual(decision['annotations'][0]['code'], 'SAL')

    def test_v2000_malformed_membership_and_duplicate_id_hold(self):
        cases = [(['M  STY  1   1 SRU', 'M  SAL   1  2   1'], 'malformed_v2000_membership_count'),
                 (['M  STY  1   1 SRU', 'M  SAL   1  1   4'], 'v2000_membership_out_of_range'),
                 (['M  STY  2   1 SRU   1 SUP'], 'duplicate_v2000_group_id')]
        for properties, reason in cases:
            with self.subTest(reason=reason):
                decision = self.check_status(v2(properties), 'hold', reason)
                self.assertTrue(decision['annotations'])

    def test_v2000_unresolved_group_type_retained(self):
        decision = self.check_status(v2(['M  STY  1   1 ZZZ']), 'hold',
                                     'unresolved_source_sgroup_type')
        self.assertEqual(decision['source_group_types'], ['ZZZ'])
        self.assertEqual(decision['groups'][0]['category'], 'unresolved')

    def test_v2000_unknown_property_and_malformed_indicator_hold(self):
        for line in ('M  SZZ   1 x', 'M  STYjunk'):
            with self.subTest(line=line):
                decision = self.check_status(v2([line]), 'hold')
                self.assertEqual(decision['annotations'][0]['raw_lines'], [line])

    def test_oversized_integer_fields_hold_before_conversion(self):
        # Larger than any permitted field, including Python's default decimal
        # conversion limit; the scanner must return a decision, not ValueError.
        oversized = '9' * max(5000, MAX_INTEGER_DIGITS + 1)
        records = (v2([f'M  STY  {oversized}']),
                   v3([f'{oversized} SRU 0 ATOMS=(1 10)']))
        for record in records:
            with self.subTest(version=record.splitlines()[3]):
                decision = self.check_status(record, 'hold', 'integer_token_limit')
                self.assertTrue(decision['annotations'])

    def test_v2000_misplaced_indicator_holds(self):
        record = v2().replace('    0.0000    0.0000    0.0000 C', 'M  STY  1   1 SRU', 1)
        self.check_status(record, 'hold', 'v2000_sgroup_indicator_inside_atom_or_bond_block')

    def test_v3000_no_groups_and_literal_atom_label(self):
        record = v3().replace('10 C 0 0 0 0', '10 "SRU BEGIN SGROUP" 0 0 0 0')
        self.check_status(record, 'admit_scope')  # chemical validity belongs to the existing gate

    def test_v3000_sru_noncontiguous_membership(self):
        decision = self.check_status(v3(['1 SRU 0 ATOMS=(2 10 20) XBONDS=(1 7) LABEL="n"']),
            'exclude_scope', 'source_polymer_sru_outside_finite_graph_contract')
        self.assertEqual(decision['groups'][0]['atoms'], [10, 20])
        self.assertEqual(decision['groups'][0]['bonds'], [7])
        self.assertEqual(decision['groups'][0]['labels'], ['"n"'])

    def test_v3000_continuation_keeps_physical_annotation_lines(self):
        decision = self.check_status(v3(['1 SRU 0 ATOMS=(2 10 -', '20) LABEL="n"'], declared_groups=1),
                                     'exclude_scope')
        group_annotation = next(item for item in decision['annotations'] if item['code'] == 'V3000_SGROUP')
        self.assertEqual(len(group_annotation['raw_lines']), 2)
        self.assertEqual(decision['groups'][0]['atoms'], [10, 20])

    def test_v3000_known_other_type_and_unresolved_type(self):
        self.check_status(v3(['1 DAT 0 ATOMS=(1 10) FIELDNAME="SRU text"']), 'exclude_scope',
                          'source_substance_group_outside_supported_contract')
        decision = self.check_status(v3(['1 ZZZ 0 ATOMS=(1 10)']), 'hold',
                                     'unresolved_source_sgroup_type')
        self.assertEqual(decision['source_group_types'], ['ZZZ'])

    def test_all_known_v3000_group_types_outside_contract(self):
        for kind in 'SRU MON COP CRO GRA MOD MER ANY COM MIX FOR SUP MUL DAT GEN'.split():
            with self.subTest(kind=kind):
                decision = self.check_status(v3([f'1 {kind} 0 ATOMS=(1 10)']), 'exclude_scope')
                self.assertEqual(decision['source_group_types'], [kind])

    def test_v3000_membership_requires_actual_ids(self):
        self.check_status(v3(['1 SRU 0 ATOMS=(1 1)']), 'hold',
                          'v3000_membership_references_undeclared_id')

    def test_v3000_malformed_lists_and_count_mismatch_hold(self):
        cases = [(v3(['1 SRU 0 ATOMS=(2 10)']), 'malformed_v3000_list_count'),
                 (v3(['1 SRU 0 ATOMS=(2 10 10)']), 'duplicate_v3000_membership'),
                 (v3(['1 SRU 0 ATOMS=(1 10)'], declared_groups=2), 'v3000_sgroup_count_or_section_mismatch'),
                 (v3(declared_groups=1), 'v3000_sgroup_count_or_section_mismatch')]
        for record, reason in cases:
            with self.subTest(reason=reason):
                self.check_status(record, 'hold', reason)

    def test_v3000_malformed_quote_retains_raw_evidence(self):
        decision = self.check_status(v3(['1 SRU 0 ATOMS=(1 10) LABEL="unterminated']), 'hold',
                                     'unterminated_v3000_quote_or_list')
        self.assertTrue(any(item['code'] == 'V3000_UNRESOLVED_LOGICAL_RECORD'
                            for item in decision['annotations']))

    def test_v3000_missing_end_and_unresolved_section_hold(self):
        self.check_status(v3().replace('M  V30 END CTAB\n', ''), 'hold', 'incomplete_v3000_ctab')
        self.check_status(v3(extra_ctab=['M  V30 BEGIN UNKNOWN']), 'hold', 'unresolved_v3000_section')

    def test_bad_framing_and_record_limit_hold(self):
        self.check_status(v2().replace('M  END\n', ''), 'hold', 'molblock_end_missing')
        self.check_status(b'\xff', 'hold', 'invalid_utf8_record')
        self.check_status('x' * (MAX_BYTES + 1), 'hold', 'record_byte_limit')

    def test_hash_uses_input_bytes_and_only_one_record_is_accepted(self):
        raw = v2().replace('\n', '\r\n').encode()
        decision = self.check_status(raw, 'admit_scope')
        self.assertEqual(decision['record_sha256'], hashlib.sha256(raw).hexdigest())
        self.check_status(v2() + '$$$$\n', 'admit_scope')
        self.check_status(v2() + '$$$$\n' + v2(), 'hold', 'multiple_sdf_records_not_supported')

    def test_record_reason_totals_are_separate_from_group_totals(self):
        counts = {}
        record = v2(['M  STY  2   1 SRU   2 SUP'])
        decision = self.check_status(record, 'exclude_scope')
        count_decision(counts, decision)
        self.assertEqual(sum(counts['records_by_status'].values()), 1)
        self.assertEqual(sum(counts['records_by_reason'].values()), 1)
        self.assertEqual(sum(counts['groups_by_type'].values()), 2)


if __name__ == '__main__':
    unittest.main()
