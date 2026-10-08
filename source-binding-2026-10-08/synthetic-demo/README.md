# Make the file you check the file you load

A filename is not a source identity. A recursive search can pick a second copy of
a checkpoint or array, even after a preflight check verified the intended file.
This small package demonstrates a stricter contract with neutral synthetic data.

Run with Python 3.10 or later. No installation, model downloads, accelerator or
network connection is required:

~~~sh
python demo.py --output-root synthetic_runs
python test_demo.py
~~~

Fixtures and JSON receipts remain on disk. Nothing is deleted. On a platform
that cannot create symlinks, the alias example reports a skip; all ordinary
source, ambiguity and hash checks still run.

The demo covers:

- One canonical scoped file passes the exact size and SHA256 checks.
- Two mount aliases resolving to that same canonical path count as one source.
- Two different canonical paths fail, including files with identical bytes.
- A same-size file with the wrong SHA256 fails.
- A known-file lookup uses the qualified path; unknown names retain the original selector.
- The two supported loader selectors change only their exact IO expression.
  The surrounding source is restored byte-for-byte by the inverse replacement.

The output contains declared relative paths, source classes, counts and hashes.
The canonical OS path remains private in the returned object.

## API and a verified manifest

~~~python
resolved = resolver.resolve_mapped_file(
    input_root,
    owner="example-lab",
    slug="synthetic-assets",
    relative_filename="example.bin",
    expected_size=verified_size,
    expected_sha256=verified_sha256,
)
path_to_load = resolved.path
audit_record = resolved.receipt
~~~

The two accepted layouts below the input root are
datasets/OWNER/SLUG/RELATIVE_FILENAME and SLUG/RELATIVE_FILENAME. There is no
filename-only recursive fallback. Relative paths containing traversal or
absolute paths fail. Escaping file symlinks fail.

For a real experiment, derive the file size and full SHA256 from a trusted,
verified source and record its owner, dataset slug, exact dataset version,
relative filename and provenance. Never infer a version from a mounted folder
name. Never generate a new expected hash from whatever file happens to be
mounted and call that source verification.

Cache the returned paths, and ensure the actual loader consumes them.
For companion arrays read through an anchor's parent directory, check that
every sibling resolves to its separately qualified path.

native_mount_bridge.py contains the original Enveda-specific helper:
qualify_mounts checks its 18-file manifest, companion families and a separately
pinned, bounded PROVENANCE.json. Its CID map is builder-only lineage rather
than a required mounted file. That helper retains the campaign's fixed public
lineage source contract; adapting it to another dataset requires an explicit,
reviewed lineage contract. This neutral demo exercises the reusable lookup and
selector helpers without pretending to qualify real campaign assets.

These checks use CPU file IO and hashing. GPU and TPU are unnecessary for the
demo; choosing model-training hardware is a separate decision. A synthetic
PASS establishes the source-binding behavior only. It is not a native model
validation, a competition score or evidence of score improvement.

The copied resolver and bridge are unchanged and pinned by their full source
SHA256 in demo.py and the execution receipts.

