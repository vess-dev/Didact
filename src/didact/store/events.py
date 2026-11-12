"""The append-only event log: every change, with full before/after file snapshots.

One log per data home (`log/events.jsonl`), so undo and cross-scope changes have a single order.
Events are numbered (`#e1`, `#e2`, …) for humans and LLMs, and carry a uuid7 for uniqueness.
Clearing the history (`didact history --clear`) is the one thing that rewrites the log: it
drops old events and leaves a `note` marker (`Cleared`) that keeps the numbering going.
The event of a change that never finished is cut off its end (`store/recovery.py`).
"""

import json
import os
import tempfile
import uuid
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Literal, cast

from didact.core.clock import now_iso
from didact.core.errors import InvalidError, NotFoundError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.core.phrases import shown as shown_phrase

type EventKind = Literal["change", "undo", "roll", "note"]

SAY = "say"  # the data key of an event's summary as a phrase (`core/phrases.py`)


@dataclass(frozen=True, slots=True)
class FileChange:
    """One file's state before and after (None = absent), or text appended to it.

    Appends (journals, transcripts) log only the new text, so growing files don't bloat the
    log. For an append, `before` is None when the append created the file, else "".
    """

    path: str  # relative to the data home, POSIX style
    before: str | None
    after: str | None
    append: str | None = None

    @property
    def action(self) -> Literal["create", "delete", "update", "append"]:
        if self.append is not None:
            return "append"
        if self.before is None:
            return "create"
        if self.after is None:
            return "delete"
        return "update"

    def to_data(self) -> dict[str, JSON]:
        if self.append is not None:
            return {"path": self.path, "append": self.append, "created": self.before is None}
        return {"path": self.path, "before": self.before, "after": self.after}

    @classmethod
    def from_data(cls, data: dict[str, JSON]) -> FileChange:
        if isinstance(data.get("append"), str):
            created = bool(data.get("created"))
            return cls(str(data["path"]), None if created else "", None, str(data["append"]))
        before, after = data.get("before"), data.get("after")
        return cls(
            path=str(data["path"]),
            before=before if isinstance(before, str) else None,
            after=after if isinstance(after, str) else None,
        )


@dataclass(frozen=True, slots=True)
class Event:
    seq: int
    id: str
    ts: str
    kind: EventKind
    summary: str
    command: str | None = None
    reason: str | None = None
    forced: bool = False
    entities: tuple[str, ...] = ()
    files: tuple[FileChange, ...] = ()
    undoes: int | None = None
    data: dict[str, JSON] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"#e{self.seq}"

    @classmethod
    def new(
        cls,
        seq: int,
        kind: EventKind,
        summary: str,
        *,
        command: str | None = None,
        reason: str | None = None,
        forced: bool = False,
        entities: tuple[str, ...] = (),
        files: tuple[FileChange, ...] = (),
        undoes: int | None = None,
        data: dict[str, JSON] | None = None,
    ) -> Event:
        """An event numbered `seq`, stamped now, with a fresh uuid7."""
        return cls(
            seq=seq,
            id=str(uuid.uuid7()),
            ts=now_iso(),
            kind=kind,
            summary=summary,
            command=command,
            reason=reason,
            forced=forced,
            entities=entities,
            files=files,
            undoes=undoes,
            data=data or {},
        )

    def to_data(self) -> dict[str, JSON]:
        record: dict[str, JSON] = {
            "seq": self.seq,
            "id": self.id,
            "ts": self.ts,
            "kind": self.kind,
            "summary": self.summary,
        }
        if self.command:
            record["command"] = self.command
        if self.reason:
            record["reason"] = self.reason
        if self.forced:
            record["forced"] = True
        if self.entities:
            record["entities"] = list(self.entities)
        if self.files:
            record["files"] = [f.to_data() for f in self.files]
        if self.undoes is not None:
            record["undoes"] = self.undoes
        if self.data:
            record["data"] = self.data
        return record

    @classmethod
    def from_data(cls, record: dict[str, JSON]) -> Event:
        files = record.get("files") or []
        entities = record.get("entities") or []
        undoes = record.get("undoes")
        data = record.get("data")
        assert isinstance(files, list) and isinstance(entities, list)
        return cls(
            seq=int(cast(int, record["seq"])),
            id=str(record["id"]),
            ts=str(record["ts"]),
            kind=cast(EventKind, record["kind"]),
            summary=str(record["summary"]),
            command=cast(str | None, record.get("command")),
            reason=cast(str | None, record.get("reason")),
            forced=bool(record.get("forced", False)),
            entities=tuple(str(e) for e in entities),
            files=tuple(FileChange.from_data(cast(dict[str, JSON], f)) for f in files),
            undoes=int(undoes) if isinstance(undoes, int) else None,
            data=data if isinstance(data, dict) else {},
        )


class EventLog:
    """Reads and appends `log/events.jsonl`. Callers must hold the data-home lock to append
    or rewrite."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def __iter__(self) -> Iterator[Event]:
        for event, _line in self.entries():
            yield event

    def entries(self) -> Iterator[tuple[Event, str]]:
        """Each event with its line exactly as stored (newline included)."""
        if not self.path.exists():
            return
        with self.path.open("rb") as handle:
            for number, raw in enumerate(handle, start=1):
                if not raw.strip():
                    continue
                try:
                    line = raw.decode("utf-8")
                    event = _parse(line)
                except _UNREADABLE as exc:
                    if not raw.endswith(b"\n"):
                        return  # cut short by a crash: it never happened (`heal`)
                    raise InvalidError(
                        _("corrupt event log line {number}: {error}", number=number, error=exc),
                        where=str(self.path),
                        hint=_("restore the line from a backup or remove it"),
                    ) from exc
                yield event, line

    def all(self) -> list[Event]:
        return list(self)

    def last(self) -> Event | None:
        """The newest whole event, read from the end of the file."""
        if not self.path.exists():
            return None
        with self.path.open("rb") as handle:
            torn = _torn_at(handle)
            line = _line_before(handle, handle.seek(0, os.SEEK_END) if torn is None else torn)[1]
        if not line.strip():
            return None
        try:
            return _parse(line)
        except _UNREADABLE:
            return self.all()[-1]  # reads from the start, and says which line is bad

    def last_seq(self) -> int:
        """The newest sequence number, read from the end of the file."""
        event = self.last()
        return event.seq if event is not None else 0

    def torn(self) -> bool:
        """Whether the log ends with a line a crash cut short."""
        if not self.path.exists():
            return False
        with self.path.open("rb") as handle:
            return _torn_at(handle) is not None

    def heal(self) -> bool:
        """Mend the end of the log after a crash: cut off a half-written last line (that write
        never happened), or finish a whole one that lost its newline. True if it cut one off."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            return False
        with self.path.open("r+b") as handle:
            end = handle.seek(-1, os.SEEK_END)
            if handle.read(1) == b"\n":
                return False
            torn = _torn_at(handle)
            if torn is None:
                handle.seek(end + 1)
                handle.write(b"\n")
            else:
                handle.truncate(torn)
            handle.flush()
            os.fsync(handle.fileno())
        return torn is not None

    def drop_last(self) -> None:
        """Cut off the newest event: only for a change that never finished."""
        with self.path.open("r+b") as handle:
            handle.truncate(_line_before(handle, handle.seek(0, os.SEEK_END))[0])
            handle.flush()
            os.fsync(handle.fileno())

    def get(self, seq: int) -> Event:
        cut = 0
        for event in self:
            if event.seq == seq:
                return event
            mark = Cleared.of(event)
            if mark is not None:
                cut = max(cut, mark.before)
        if seq < cut:
            raise NotFoundError(
                _("no event #e{seq}: the history before #e{cut} was cleared", seq=seq, cut=cut),
                hint=_("see `didact history` for what's left"),
            )
        raise NotFoundError(_("no event #e{seq}", seq=seq), hint=_("see `didact history`"))

    def append(
        self,
        *,
        kind: EventKind,
        summary: str,
        command: str | None = None,
        reason: str | None = None,
        forced: bool = False,
        entities: tuple[str, ...] = (),
        files: tuple[FileChange, ...] = (),
        undoes: int | None = None,
        data: dict[str, JSON] | None = None,
    ) -> Event:
        self.heal()
        event = Event.new(
            self.last_seq() + 1,
            kind,
            summary,
            command=command,
            reason=reason,
            forced=forced,
            entities=entities,
            files=files,
            undoes=undoes,
            data=data,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(encode(event))
            handle.flush()
            os.fsync(handle.fileno())
        return event

    def rewrite(self, keep: Callable[[Event], bool], *, then: Sequence[Event] = ()) -> int:
        """Replace the log with the events `keep` accepts, then `then`; return its new size.

        Kept lines are copied as they are. The new log is written to a temporary file that
        replaces the old one in one step, so readers see one or the other, never half.
        Callers hold the data-home lock. This can't be undone: it's how history is cleared.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                for event, line in self.entries():
                    if keep(event):
                        handle.write(line if line.endswith("\n") else line + "\n")
                for event in then:
                    handle.write(encode(event))
                handle.flush()
                os.fsync(handle.fileno())
            tmp.replace(self.path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        return self.path.stat().st_size


def encode(event: Event) -> str:
    """An event as one log line."""
    return json.dumps(event.to_data(), ensure_ascii=False, separators=(",", ":")) + "\n"


_UNREADABLE = (ValueError, KeyError, TypeError, AssertionError)


def _parse(line: str | bytes) -> Event:
    return Event.from_data(json.loads(line))


def _line_before(handle: BinaryIO, end: int) -> tuple[int, bytes]:
    """The last line that ends by `end`: where it starts, and its bytes without the newline."""
    position, chunk = end, b""
    while position > 0:
        step = min(65536, position)
        position -= step
        handle.seek(position)
        chunk = handle.read(step) + chunk
        line = chunk.rstrip(b"\n")
        start = line.rfind(b"\n") + 1
        if start:
            return position + start, line[start:]
    return 0, chunk.rstrip(b"\n")


def _torn_at(handle: BinaryIO) -> int | None:
    """Where the last line starts if a crash cut it short: it has no newline and isn't whole
    (the start of an event is never a whole one). None when the log ends properly."""
    end = handle.seek(0, os.SEEK_END)
    if end == 0:
        return None
    handle.seek(end - 1)
    if handle.read(1) == b"\n":
        return None
    start, line = _line_before(handle, end)
    try:
        _parse(line)
    except _UNREADABLE:
        return start
    return None


def said(event: Event) -> JSON:
    """What an event's summary says: its phrase when it was logged with one, else the
    English summary itself (older events, rolls)."""
    found = event.data.get(SAY)
    return found if isinstance(found, dict) else event.summary


def shown(event: Event) -> str:
    """An event's summary in the reader's language (its English summary when it has no phrase)."""
    return shown_phrase(event.data.get(SAY), event.summary)


# ---------------------------------------------------------------------- cleared history

CLEARED = "cleared"  # the data key of a history clear's marker
RESTORED = "restored"  # the data key a restore's marker has beside its `cleared` one


@dataclass(frozen=True, slots=True)
class Cleared:
    """What a history clear left in the log: a `note` event that keeps the numbering going.

    Only events numbered below `before` (the cut) were dropped, `kinds` says which, and
    `rolls` is the highest roll number used by then, so no roll number repeats even if the
    rolls went too and the counters file is lost.
    """

    events: int
    before: int
    rolls: int
    kinds: tuple[str, ...] = ()
    bytes: int = 0

    @property
    def dice(self) -> bool:
        """Whether the dice record (rolls and notes) went too."""
        return "roll" in self.kinds

    def to_data(self) -> dict[str, JSON]:
        return {
            "events": self.events,
            "before": self.before,
            "rolls": self.rolls,
            "kinds": list[JSON](self.kinds),
            "bytes": self.bytes,
        }

    @classmethod
    def of(cls, event: Event) -> Cleared | None:
        """The clear an event marks, if it is a marker."""
        raw = event.data.get(CLEARED) if event.kind == "note" else None
        if not isinstance(raw, dict):
            return None

        def number(key: str) -> int:
            value = raw.get(key)
            return value if isinstance(value, int) and not isinstance(value, bool) else 0

        kinds = raw.get("kinds")
        return cls(
            events=number("events"),
            before=number("before"),
            rolls=number("rolls"),
            kinds=tuple(str(k) for k in kinds) if isinstance(kinds, list) else (),
            bytes=number("bytes"),
        )


def cleared_before(events: Iterable[Event]) -> int:
    """The latest clear's cut: changes numbered below it may be gone (0: never cleared)."""
    cut = 0
    for event in events:
        mark = Cleared.of(event)
        if mark is not None:
            cut = max(cut, mark.before)
    return cut


def rebuildable(event: int, cut: int) -> bool:
    """Whether the log can still rebuild files as they were right after `event`.

    That walks back through every change after it, so none of those may have been cleared:
    everything numbered from `cut` on is still there.
    """
    return event >= cut - 1


def undone_seqs(events: list[Event]) -> set[int]:
    """Sequence numbers whose effects are currently undone (an undone undo is a redo).

    An undo whose target a history clear dropped has nothing left to mark: it's skipped.
    """
    undoers: dict[int, list[int]] = {}
    for event in events:
        if event.kind == "undo" and event.undoes is not None:
            undoers.setdefault(event.undoes, []).append(event.seq)
    undone: dict[int, bool] = {}
    # An undo always comes after its target, so newest-first resolves every dependency in one pass.
    for event in sorted(events, key=lambda e: e.seq, reverse=True):
        undone[event.seq] = any(not undone.get(u, False) for u in undoers.get(event.seq, ()))
    return {seq for seq, flag in undone.items() if flag}
