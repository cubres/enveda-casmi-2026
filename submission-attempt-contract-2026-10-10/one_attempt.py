"""Original source-only local intent latch; contains no Kaggle/network operations."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Callable


class Hold(RuntimeError):
    """The caller must reconcile evidence read-only, never retry this mutation."""


@dataclass(frozen=True)
class Binding:
    competition: str
    ref: str
    version: int
    file_name: str
    artifact_sha256: str

    def validate(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", self.competition):
            raise ValueError("invalid competition")
        if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_-]+", self.ref):
            raise ValueError("invalid ref")
        if type(self.version) is not int or self.version < 1:
            raise ValueError("invalid version")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", self.file_name):
            raise ValueError("invalid file name")
        if not re.fullmatch(r"[0-9a-f]{64}", self.artifact_sha256):
            raise ValueError("invalid artifact hash")

    def identity(self) -> dict:
        self.validate()
        # The hash is evidence, not an escape hatch to repeat a frozen version.
        return dict(competition=self.competition.casefold(), ref=self.ref.casefold(),
                    version=self.version)

    def key(self) -> str:
        payload = json.dumps(self.identity(), sort_keys=True,
                             separators=(",", ":")).encode()
        return hashlib.sha256(payload).hexdigest()


def _durable_exclusive_json(path: Path, value: dict) -> None:
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short journal write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


class IntentStore:
    """Permanent local latch. Existing intents, including partial ones, hold."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        if self.directory.is_symlink():
            raise ValueError("intent directory must not be a symlink")
        self.directory.mkdir(parents=True, exist_ok=True)

    def admit(self, binding: Binding) -> None:
        record = dict(schema=1, state="REQUEST_MAY_HAVE_STARTED",
                      **binding.identity(), file_name=binding.file_name,
                      artifact_sha256=binding.artifact_sha256)
        try:
            _durable_exclusive_json(self.directory / (binding.key() + ".intent.json"), record)
        except FileExistsError as exc:
            raise Hold("existing intent: reconcile the exact server row read-only") from exc
        # Other write/fsync failures propagate before callback admission. Any
        # retained intent still holds on the next invocation; nothing is removed.

    def record_outcome(self, binding: Binding, accepted_ref: str | None) -> dict:
        intent = self.directory / (binding.key() + ".intent.json")
        if not intent.exists():
            raise Hold("missing durable intent")
        expected = dict(schema=1, state="REQUEST_MAY_HAVE_STARTED",
                        **binding.identity(), file_name=binding.file_name,
                      artifact_sha256=binding.artifact_sha256)
        try:
            actual = json.loads(intent.read_text())
        except (OSError, ValueError) as exc:
            raise Hold("incomplete intent") from exc
        if actual != expected:
            raise Hold("intent binding mismatch")
        accepted = (isinstance(accepted_ref, str)
                    and bool(re.fullmatch(r"[0-9]+", accepted_ref))
                    and int(accepted_ref) > 0)
        result = dict(schema=1, state="ACCEPTED_UNSCORED" if accepted else "UNKNOWN",
                      **binding.identity(), file_name=binding.file_name,
                      artifact_sha256=binding.artifact_sha256,
                      accepted_ref=accepted_ref if accepted else None)
        _durable_exclusive_json(self.directory / (binding.key() + ".outcome.json"), result)
        return result


def request_once(store: IntentStore, binding: Binding,
                 request: Callable[[], str | None]) -> dict:
    """Invoke an already-qualified, no-retry adapter once; exceptions hold.

    All identity, source/output, account, scientific, runtime, quota and raw
    accepted-row checks belong BEFORE this function. It does not implement them.
    The callback must disable transport retries and return only its accepted row
    reference, never a model/prompt/output payload. An accepted reference is not
    a completed score. No exception text or callback output is logged.
    """
    store.admit(binding)
    try:
        accepted_ref = request()
    except BaseException:
        try:
            store.record_outcome(binding, None)
        except BaseException:
            pass  # The durable intent already prevents another request.
        raise Hold("request outcome unknown: reconcile read-only") from None
    try:
        result = store.record_outcome(binding, accepted_ref)
    except BaseException:
        raise Hold("post-request receipt incomplete: reconcile read-only") from None
    if result["state"] == "UNKNOWN":
        raise Hold("no accepted reference: reconcile read-only")
    return result

