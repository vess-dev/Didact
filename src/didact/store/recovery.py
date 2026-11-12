"""Changes cut short: a crash or a full disk never leaves half a change behind.

A change is written in order, under the data-home lock: a marker naming it (`log/applying.json`),
then its event, then its files. The marker goes once the last file is in, and until then the
change hasn't happened: whoever finds the marker puts each file back from the event's text and
drops the event. Only the marker can tell a change still being written from a file that someone
later edited back by hand, which nothing here may touch.

Everything here runs with the data-home lock held (`Repo.writing`).
"""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from didact.core.i18n import N_, _
from didact.core.phrases import english, phrase
from didact.store.events import SAY, Event, EventLog, FileChange, said, shown
from didact.store.fsutil import atomic_write, remove_file, sync_dir
from didact.store.layout import Layout


@dataclass(frozen=True, slots=True)
class TakenBack:
    """A change that never finished and is gone again: its event, and the files left as they
    were because someone edited them after it was cut short."""

    event: Event
    kept: tuple[str, ...] = ()

    def notices(self) -> list[str]:
        """What to tell the reader, in their language."""
        found = [_("a change was cut short and taken back: {what}", what=shown(self.event))]
        found += [_("{path} was edited since, so it was left as it is", path=p) for p in self.kept]
        return found


def begin(layout: Layout, seq: int, files: Iterable[FileChange]) -> None:
    """Say that the change about to be logged as `seq` is being written. An append's event
    holds only the new text, so the marker keeps how long each file was."""
    sizes = {c.path: _size(layout, c.path) for c in files if c.append is not None}
    atomic_write(layout.applying_file, json.dumps({"seq": seq, "sizes": sizes}))


def end(layout: Layout) -> None:
    """The change is all written: it has happened."""
    layout.applying_file.unlink(missing_ok=True)
    sync_dir(layout.applying_file.parent)


def take_back(layout: Layout, log: EventLog) -> TakenBack | None:
    """Put back whatever the marked change wrote and drop its event. None if it never reached
    the log, in which case no file was touched. Safe to run again if it is itself cut short."""
    marker = _marker(layout)
    if marker is None:
        return None
    seq, sizes = marker
    log.heal()
    event = log.last()
    if event is None or event.seq != seq:
        end(layout)
        return None
    kept = tuple(c.path for c in event.files if not _restore(layout, c, sizes))
    log.drop_last()
    end(layout)
    return TakenBack(event, kept)


def recover(layout: Layout, log: EventLog) -> TakenBack | None:
    """Clear up after a change a crash cut short, if there is one, and say so in the log."""
    if not layout.applying_file.exists():
        return None
    gone = take_back(layout, log)
    if gone is not None:
        words = phrase(N_("a change was cut short and taken back: {what}"), what=said(gone.event))
        log.append(
            kind="note", summary=english(words), command=gone.event.command, data={SAY: words}
        )
    return gone


def _size(layout: Layout, rel: str) -> int:
    path = layout.abs(rel)
    return path.stat().st_size if path.is_file() else 0


def _marker(layout: Layout) -> tuple[int, Mapping[str, int]] | None:
    """The marked change's number and file sizes. It's written whole, so one that can't be
    read wasn't ours: nothing can be taken back from it."""
    try:
        data = json.loads(layout.applying_file.read_text(encoding="utf-8"))
        return int(data["seq"]), {str(k): int(v) for k, v in data["sizes"].items()}
    except FileNotFoundError:
        return None
    except ValueError, KeyError, TypeError, AttributeError:
        layout.applying_file.unlink(missing_ok=True)
        return None


def _restore(layout: Layout, change: FileChange, sizes: Mapping[str, int]) -> bool:
    """Put one file back as it was, if it holds what the change wrote. False: it holds neither
    the old text nor the new, so someone edited it, and it stays."""
    path = layout.abs(change.path)
    try:
        current = path.read_text(encoding="utf-8") if path.is_file() else None
    except UnicodeDecodeError:
        return False
    if change.append is not None:
        text = current or ""
        size, start = len(text.encode("utf-8")), sizes.get(change.path, 0)
        if current is None or size == start:
            return True  # it never got this far
        if size != start + len(change.append.encode("utf-8")) or not text.endswith(change.append):
            return False
        rest = text[: len(text) - len(change.append)]
        before = None if change.before is None else rest
    else:
        if current == change.before:
            return True
        if current != change.after:
            return False
        before = change.before
    if before is None:
        remove_file(path)
    else:
        atomic_write(path, before)
    return True
