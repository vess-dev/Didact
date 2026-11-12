"""Filesystem safety: atomic writes, the single-writer lock, and refusals from the disk."""

import contextlib
import errno
import importlib
import os
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from didact.core.errors import ConflictError, StorageError
from didact.core.i18n import _

_WINDOWS = sys.platform.startswith("win")


def atomic_write(path: Path, text: str) -> None:
    """Write text so readers see either the old file or the new one, never half of it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    sync_dir(path.parent)


def sync_dir(path: Path) -> None:
    """Make a folder's latest renames and deletions survive a power cut."""
    if _WINDOWS:
        return  # Windows can't open a folder like this
    with contextlib.suppress(OSError):  # and not every filesystem can do it
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def remove_file(path: Path) -> None:
    """Delete a file and prune empty parent type directories."""
    path.unlink(missing_ok=True)
    parent = path.parent
    try:
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
    except OSError:
        pass


def reason(exc: OSError) -> str:
    """What the disk said, in a few words: `No space left on device`, `Permission denied: …`."""
    if exc.strerror and exc.filename:
        return f"{exc.strerror}: {exc.filename}"
    return exc.strerror or str(exc) or type(exc).__name__


def fix_for(exc: OSError) -> str:
    """How to get past a refusal from the disk."""
    if exc.errno in (errno.ENOSPC, errno.EDQUOT):
        return _("free up some disk space, then run it again")
    if exc.errno in (errno.EACCES, errno.EPERM, errno.EROFS):
        return _("make sure Didact may write there, then run it again")
    return _("check the disk and the path, then run it again")


def storage_error(exc: OSError) -> StorageError:
    """A refusal from the disk as an error that says what happened and how to get past it."""
    return StorageError(
        _("couldn't read or write a file: {why}", why=reason(exc)), hint=fix_for(exc)
    )


def _lock_module() -> Any:
    return importlib.import_module("msvcrt" if _WINDOWS else "fcntl")


@contextmanager
def exclusive_lock(lock_path: Path, timeout: float = 10.0) -> Iterator[None]:
    """Hold an exclusive advisory lock on `lock_path` (one writer per data home)."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    module = _lock_module()
    deadline = time.monotonic() + timeout
    with lock_path.open("a+b") as handle:
        while True:
            try:
                if _WINDOWS:
                    handle.seek(0)
                    module.locking(handle.fileno(), module.LK_NBLCK, 1)
                else:
                    module.flock(handle.fileno(), module.LOCK_EX | module.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() > deadline:
                    raise ConflictError(
                        _("another didact process is writing to this data home"),
                        hint=_("wait a moment and retry"),
                    ) from exc
                time.sleep(0.05)
        try:
            yield
        finally:
            if _WINDOWS:
                handle.seek(0)
                module.locking(handle.fileno(), module.LK_UNLCK, 1)
            else:
                module.flock(handle.fileno(), module.LOCK_UN)
