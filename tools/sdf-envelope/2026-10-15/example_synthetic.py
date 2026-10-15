# SPDX-License-Identifier: MIT
"""Run a small invented-text demonstration; performs no file or network IO."""
import json

from strict_sdf_envelope import inspect_scoped_record

record = ('invented example\ntext only\n\n'
          '  0  0  0  0  0  0            999 V2000\nM  END\n')
for name, raw in (('single record', record), ('unframed trailing annotation',
                                           record + 'M  STY  1   1 SRU\n')):
    decision = inspect_scoped_record(raw, record_ordinal=1)
    print(json.dumps(dict(example=name, status=decision['status'], reason=decision['reason'],
                         record_sha256=decision['record_sha256']), sort_keys=True))
