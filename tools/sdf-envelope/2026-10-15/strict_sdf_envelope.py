# SPDX-License-Identifier: MIT
"""Fail closed on unframed text after a single SDF record's first M END.

Original, stdlib-only, in-memory source; no file IO or chemistry.  This is a
conservative supported-envelope contract, not a complete CTfile parser.  Keep
the original scope scanner and every subsequent chemistry gate unchanged.
"""
import hashlib
import re

from raw_molblock_sgroup_scope import MAX_BYTES, MAX_LINES, inspect_sdf_record


def inspect_envelope(record):
    """Return source-bound evidence for the record's outer metadata envelope.

    A property value continues to a truly empty line, as in the pinned scope
    scanner.  Strings such as ``M  END`` and ``> <NAME>`` inside a value remain
    literal text.  ``$$$$`` always terminates the supplied record.  Without a
    property header, unexpected trailing text is held instead of ignored.
    """
    body = record.encode('utf-8') if isinstance(record, str) else record
    if not isinstance(body, bytes):
        raise TypeError('record must be str or bytes')
    result = dict(schema='strict-single-sdf-envelope/1',
                  record_sha256=hashlib.sha256(body).hexdigest(),
                  record_bytes=len(body), status='hold', reason=None,
                  inspection_complete=False, molblock_end_line=None,
                  delimiter_line=None, property_headers=[], offending_line=None)

    def hold(reason, line=None):
        result.update(reason=reason, offending_line=line)
        return result

    if len(body) > MAX_BYTES:
        return hold('record_byte_limit')
    try:
        # splitlines deliberately matches the existing scope scanner.
        lines = body.decode('utf-8', errors='strict').splitlines()
    except UnicodeError:
        return hold('invalid_utf8_record')
    if not 4 <= len(lines) <= MAX_LINES:
        return hold('molblock_line_limit_or_missing_header')
    end = next((index for index in range(4, len(lines))
                if re.fullmatch(r'M\s+END\s*', lines[index])), None)
    if end is None:
        return hold('molblock_end_missing')
    result['molblock_end_line'] = end + 1
    for index, line in enumerate(lines[:end]):
        if line.strip() == '$$$$':
            return hold('delimiter_before_molblock_end', index + 1)

    state = 'outside_value'
    for index in range(end + 1, len(lines)):
        line = lines[index]
        if state == 'after_delimiter':
            if line.strip():
                return hold('content_after_record_delimiter', index + 1)
            continue
        if line.strip() == '$$$$':
            result['delimiter_line'] = index + 1
            state = 'after_delimiter'
        elif state == 'in_value':
            if line == '':
                state = 'outside_value'
        elif not line.strip():
            continue
        else:
            # Intentionally only supports the same direct > <NAME> property
            # header family as the pinned scanner's ChEBI metadata reader.
            header = re.fullmatch(r'>\s*<([^<>]+)>.*', line)
            if header is None:
                return hold('unexpected_text_outside_property_value', index + 1)
            if not header.group(1).strip():
                return hold('empty_property_name', index + 1)
            result['property_headers'].append(dict(name=header.group(1), line=index + 1))
            state = 'in_value'
    result.update(status='admit_envelope', reason='supported_single_record_envelope',
                  inspection_complete=True)
    return result


def inspect_scoped_record(record, record_ordinal=None):
    """Apply the new envelope preflight before the unchanged scope scanner.

    An envelope HOLD prevents the scanner from returning an apparent admission
    for a partially consumed input.  Admission here still says nothing about
    chemical validity, fingerprints, mass, model utility, or release rights.
    """
    envelope = inspect_envelope(record)
    result = dict(schema='enveloped-sgroup-scope/1', record_ordinal=record_ordinal,
                  record_sha256=envelope['record_sha256'],
                  record_bytes=envelope['record_bytes'], status='hold',
                  reason=envelope['reason'], envelope=envelope, scope=None)
    if envelope['status'] == 'admit_envelope':
        scope = inspect_sdf_record(record, record_ordinal=record_ordinal)
        result.update(status=scope['status'], reason=scope['reason'], scope=scope)
    return result
