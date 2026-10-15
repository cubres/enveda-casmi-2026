# SPDX-License-Identifier: MIT
"""Additional invented V3000 framing fixtures, with no real chemical input."""
import unittest

from raw_molblock_sgroup_scope import inspect_sdf_record
from strict_sdf_envelope import inspect_scoped_record


def invented_v3000(group=False):
    lines = ['invented V3000 text', 'empty graph', '',
             '  0  0  0  0  0  0            999 V3000',
             'M  V30 BEGIN CTAB', 'M  V30 COUNTS 0 0 %d 0 0' % int(group)]
    if group:
        lines.extend(['M  V30 BEGIN SGROUP', 'M  V30 1 SRU 0 LABEL="n"',
                      'M  V30 END SGROUP'])
    lines.extend(['M  V30 END CTAB', 'M  END', '> <NOTES>', 'invented', ''])
    return ('\n'.join(lines) + '\n').encode()


class V3000EnvelopeTests(unittest.TestCase):
    def test_empty_v3000_scope_equality(self):
        raw = invented_v3000()
        new = inspect_scoped_record(raw, 73)
        self.assertEqual(new['status'], 'admit_scope')
        self.assertEqual(new['scope'], inspect_sdf_record(raw, 73))

    def test_sru_v3000_scope_equality(self):
        raw = invented_v3000(group=True)
        new = inspect_scoped_record(raw, 73)
        self.assertEqual(new['status'], 'exclude_scope')
        self.assertEqual(new['scope'], inspect_sdf_record(raw, 73))

    def test_undelimited_v3000_append_held(self):
        raw = invented_v3000() + invented_v3000(group=True)
        self.assertEqual(inspect_sdf_record(raw)['status'], 'admit_scope')
        new = inspect_scoped_record(raw)
        self.assertEqual(new['status'], 'hold')
        self.assertEqual(new['reason'], 'unexpected_text_outside_property_value')
        self.assertIsNone(new['scope'])


if __name__ == '__main__':
    unittest.main()
