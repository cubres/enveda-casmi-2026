# SPDX-License-Identifier: MIT
"""Invented CTAB text only. No archive, real molecule, bank, or controller."""
import hashlib
import unittest

from raw_molblock_sgroup_scope import MAX_BYTES, MAX_LINES, inspect_sdf_record
from strict_sdf_envelope import inspect_envelope, inspect_scoped_record


def invented_record(properties=(), metadata=(), newline='\n'):
    # Zero atom/bond counts make the fixture's lack of chemistry explicit.
    lines = ['invented empty-graph test', 'text fixture, not a molecule', '',
             '  0  0  0  0  0  0            999 V2000',
             *properties, 'M  END', *metadata]
    return (newline.join(lines) + newline).encode('utf-8')


class StrictEnvelopeTests(unittest.TestCase):
    def check(self, raw, status, reason=None):
        result = inspect_scoped_record(raw, record_ordinal=41)
        self.assertEqual(result['status'], status)
        if reason is not None:
            self.assertEqual(result['reason'], reason)
        self.assertEqual(result['record_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['record_bytes'], len(raw))
        self.assertEqual(result['record_ordinal'], 41)
        return result

    def test_no_metadata_admits_scope_only(self):
        self.check(invented_record(), 'admit_scope')

    def test_valid_metadata_preserves_exact_old_decision(self):
        raw = invented_record(metadata=['> <ChEBI ID>', 'CHEBI:999999997', '',
                                        '> <NOTES>', 'invented text', ''])
        result = self.check(raw, 'admit_scope')
        self.assertEqual(result['scope'], inspect_sdf_record(raw, 41))
        self.assertEqual(result['scope']['chebi_id'], 'CHEBI:999999997')
        self.assertEqual([row['name'] for row in result['envelope']['property_headers']],
                         ['ChEBI ID', 'NOTES'])

    def test_undelimited_second_ctab_was_ignored_now_held(self):
        raw = invented_record() + invented_record(properties=['M  STY  1   1 SRU'])
        self.assertEqual(inspect_sdf_record(raw)['status'], 'admit_scope')
        result = self.check(raw, 'hold', 'unexpected_text_outside_property_value')
        self.assertIsNone(result['scope'])
        self.assertEqual(result['envelope']['offending_line'], 6)

    def test_unframed_group_property_was_ignored_now_held(self):
        raw = invented_record(metadata=['M  STY  1   1 SRU'])
        self.assertEqual(inspect_sdf_record(raw)['status'], 'admit_scope')
        self.check(raw, 'hold', 'unexpected_text_outside_property_value')

    def test_second_end_outside_property_held(self):
        self.check(invented_record(metadata=['', 'M  END']), 'hold',
                   'unexpected_text_outside_property_value')

    def test_ctab_and_header_strings_inside_value_are_literal(self):
        raw = invented_record(metadata=['> <NOTES>', 'M  END', '> <ChEBI ID>',
                                        'CHEBI:999999998', 'M  STY  1   1 SRU', ''])
        result = self.check(raw, 'admit_scope')
        self.assertIsNone(result['scope']['chebi_id'])
        self.assertEqual(len(result['envelope']['property_headers']), 1)

    def test_empty_property_value(self):
        self.check(invented_record(metadata=['> <NOTES>', '', '> <MORE>', '', '']),
                   'admit_scope')

    def test_whitespace_value_does_not_create_false_header(self):
        raw = invented_record(metadata=['> <NOTES>', ' ', '> <ChEBI ID>',
                                        'CHEBI:999999998', ''])
        result = self.check(raw, 'admit_scope')
        self.assertEqual(len(result['envelope']['property_headers']), 1)
        self.assertIsNone(result['scope']['chebi_id'])

    def test_delimiter_and_trailing_blank_lines(self):
        self.check(invented_record(metadata=['$$$$', '', '  ', '\t']), 'admit_scope')

    def test_delimiter_ends_unterminated_value(self):
        result = self.check(invented_record(metadata=['> <NOTES>', 'x', '$$$$']), 'admit_scope')
        self.assertEqual(result['envelope']['delimiter_line'], 8)

    def test_content_or_second_delimiter_after_delimiter_held(self):
        for trailing in ('$$$$', 'second title', '> <NOTES>'):
            with self.subTest(trailing=trailing):
                self.check(invented_record(metadata=['$$$$', trailing]), 'hold',
                           'content_after_record_delimiter')

    def test_delimiter_before_end_held(self):
        self.check(invented_record(properties=['$$$$']), 'hold',
                   'delimiter_before_molblock_end')

    def test_valid_group_is_still_excluded_by_unchanged_scanner(self):
        raw = invented_record(properties=['M  STY  1   1 SRU'])
        result = self.check(raw, 'exclude_scope')
        self.assertEqual(result['scope'], inspect_sdf_record(raw, 41))

    def test_scanner_hold_is_not_relaxed(self):
        raw = invented_record(properties=['M  STY  1   1 ZZZ'])
        result = self.check(raw, 'hold', 'unresolved_source_sgroup_type')
        self.assertEqual(result['envelope']['status'], 'admit_envelope')
        self.assertIsNotNone(result['scope'])

    def test_duplicate_chebi_metadata_still_holds(self):
        raw = invented_record(metadata=['> <ChEBI ID>', 'CHEBI:999999997', '',
                                        '> <ChEBI ID>', 'CHEBI:999999997', ''])
        self.check(raw, 'hold', 'duplicate_chebi_id_metadata')

    def test_malformed_and_empty_headers_hold(self):
        for header in ('> not-a-header', '> <>', '> < >', '> <<NAME>>'):
            with self.subTest(header=header):
                self.check(invented_record(metadata=[header, 'value']), 'hold')

    def test_crlf_hash_is_exact_and_differs_from_lf(self):
        raw = invented_record(newline='\r\n')
        result = self.check(raw, 'admit_scope')
        self.assertNotEqual(result['record_sha256'], hashlib.sha256(invented_record()).hexdigest())

    def test_str_and_bytes_equivalent(self):
        raw = invented_record()
        self.assertEqual(inspect_scoped_record(raw), inspect_scoped_record(raw.decode()))

    def test_invalid_utf8_size_line_and_missing_end_limits_hold(self):
        for raw, reason in ((b'\xff', 'invalid_utf8_record'),
                            (b'x' * (MAX_BYTES + 1), 'record_byte_limit'),
                            (b'\n' * (MAX_LINES + 1), 'molblock_line_limit_or_missing_header'),
                            (b'a\nb\nc\nV2000\n', 'molblock_end_missing')):
            with self.subTest(reason=reason):
                self.check(raw, 'hold', reason)

    def test_type_error_has_no_implicit_coercion(self):
        for raw in (None, bytearray(b'text'), 12):
            with self.subTest(kind=type(raw).__name__):
                with self.assertRaises(TypeError):
                    inspect_envelope(raw)


if __name__ == '__main__':
    unittest.main()
