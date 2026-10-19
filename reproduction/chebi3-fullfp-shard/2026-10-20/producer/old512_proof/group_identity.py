"""Pure group identifier extracted unchanged from the public role builder.

Uploader-authored Apache-2.0. Original complete source SHA256:
20302057f22303340ed339360d3c43ad2d9f7da2bccc9dcdc0b193af8073b9fc.
Only the pure function is needed; no data-reading role builder is imported.
"""
import hashlib
import json

def group_identity(key):
    counts, inchikey = key
    comp = ",".join(f"{symbol}:{count}" for symbol, count in counts)
    payload = json.dumps([list(counts), inchikey], separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest(), comp, inchikey
