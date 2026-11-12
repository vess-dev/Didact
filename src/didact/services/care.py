"""Library care: what's in the data home and how big it is, backups, and relationship graphs.

- `library`: worlds and their campaigns, installed packs, the log and backups, with sizes.
- `snapshot`: the whole data home in one zip under `backups/` (never the backups themselves).
  Ending a session makes one too (`-auto`) and deletes all but the newest `AUTO_KEEP` of those.
  Pruning deletes only `snapshot-*.zip` files there, for good: backups aren't in the log.
- `restore`: a backup's contents in place of the library's (all but its backups), after a
  safety backup of the library as it was (`-before-restore`). The log is replaced too, so undo
  can't take a restore back: restoring the safety backup can. A `note` marker ends the restored
  log: a `Cleared` one that dropped nothing, numbered after the newest event either log had and
  holding the highest roll number either used, so no event or roll number comes round again.
- `reset`: the library emptied, as if Didact were newly installed, after a safety backup
  (`-before-reset`). The one deliberate break in the numbering: the next change is #e1 again.
  Backups stay, and installed packs unless asked.
- `graph`: a record and what it links to (or is linked from), as a Mermaid graph.
"""

import contextlib
import io
import json
import re
import shutil
import zipfile
import zlib
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from didact.core.errors import ConflictError, DidactError, InvalidError, NotFoundError
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON
from didact.core.phrases import english, phrase
from didact.store.events import CLEARED, RESTORED, SAY, Cleared, Event, EventLog
from didact.store.fsutil import atomic_write, reason
from didact.store.layout import Layout
from didact.store.repo import Repo

BACKUPS = "backups"
WORK = ".restore"  # where a restore unpacks a backup and sets the library's files aside
SKIP = frozenset({BACKUPS, ".lock", ".staging", WORK})
AUTO = "auto"  # a backup made as a session ends
SAFETY = "before-restore"  # a backup of the library a restore replaces
EMPTIED = "before-reset"  # a backup of the library a reset empties
# listings (marked for translation: shown through `i18n.translate`)
KINDS = {AUTO: N_("automatic"), SAFETY: N_("before a restore"), EMPTIED: N_("before a reset")}
DEMO_MARK = ".didact-demo"  # `serve --demo`'s mark on its library: a reset keeps it
AUTO_KEEP = 5  # the automatic backups kept: a session's end deletes older ones
STAMPED = re.compile(
    r"snapshot-(?P<stamp>\d{8}-\d{6})(?:-(?P<n>\d+))?"
    r"(?:-(?P<kind>auto|before-restore|before-reset))?\.zip"
)
# what reading or unpacking a zip can raise: the disk, or a damaged or unusual zip
UNZIPPING = (OSError, zipfile.BadZipFile, EOFError, zlib.error, NotImplementedError)


def _other() -> str:
    """The hint for a zip that isn't a backup Didact made."""
    return _("restore a backup Didact made: `didact snapshot --list`")


@dataclass(frozen=True, slots=True)
class Size:
    what: str
    path: str
    bytes: int
    files: int

    def to_data(self) -> dict[str, JSON]:
        return {"what": self.what, "path": self.path, "bytes": self.bytes, "files": self.files}


def measure(path: Path) -> tuple[int, int]:
    files = [p for p in path.rglob("*") if p.is_file()] if path.is_dir() else []
    return sum(p.stat().st_size for p in files), len(files)


def human(size: int) -> str:
    amount = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if amount < 1024 or unit == "GB":
            return f"{amount:.0f} {unit}" if unit == "B" else f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} GB"


def library(repo: Repo) -> list[Size]:
    found: list[Size] = []
    layout = repo.layout
    for world_id in repo.world_ids():
        world_dir = layout.world_dir(world_id)
        total, count = measure(world_dir)
        found.append(Size(f"world {world_id}", layout.rel(world_dir), total, count))
        campaigns = world_dir / "campaigns"
        for folder in sorted(campaigns.iterdir()) if campaigns.is_dir() else []:
            if folder.is_dir():
                total, count = measure(folder)
                found.append(Size(f"  campaign {folder.name}", layout.rel(folder), total, count))
    for what, path in (
        ("installed packs", layout.packs_dir),
        ("systems (homebrew)", layout.systems_dir),
        ("global", layout.global_root),
        ("event log", layout.log_file.parent),
        ("backups", repo.home / BACKUPS),
    ):
        total, count = measure(path)
        if count:
            found.append(Size(what, layout.rel(path), total, count))
    return found


def snapshot(repo: Repo, kind: str = "manual") -> Path:
    """Zip the data home (all but its backups) into `backups/snapshot-<time>[-<kind>].zip`,
    holding the lock so that no change lands halfway through."""
    with repo.writing():
        return _snapshot(repo, kind)


def _snapshot(repo: Repo, kind: str) -> Path:
    """`snapshot`, for a caller that holds the lock. A zip that fails halfway is deleted."""
    folder = repo.home / BACKUPS
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    tails = {k: f"-{k}" for k in KINDS}
    number = 1  # the nth backup this second, of any kind, so that names sort as they were made
    while any(
        (folder / f"snapshot-{stamp}{_nth(number)}{t}.zip").exists() for t in ("", *tails.values())
    ):
        number += 1
    target = folder / f"snapshot-{stamp}{_nth(number)}{tails.get(kind, '')}.zip"
    part = folder / f".{target.name}.part"  # not a backup until it's whole
    try:
        with zipfile.ZipFile(
            part, "w", compression=zipfile.ZIP_DEFLATED, strict_timestamps=False
        ) as archive:
            for path in sorted(repo.home.rglob("*")):
                rel = path.relative_to(repo.home)
                if path.is_file() and rel.parts[0] not in SKIP:
                    archive.write(path, rel.as_posix())
        part.replace(target)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    return target


def _nth(number: int) -> str:
    return f"-{number}" if number > 1 else ""


def snapshots(repo: Repo) -> list[Path]:
    """The backups in `backups/`, oldest first."""
    folder = repo.home / BACKUPS
    found = [p for p in folder.glob("snapshot-*.zip") if p.is_file()] if folder.is_dir() else []
    return sorted(found, key=_made)


def _made(path: Path) -> tuple[str, int, str]:
    """When a backup was made, for ordering: the time in its name, else the file's own."""
    match = STAMPED.fullmatch(path.name)
    if match:
        return match["stamp"], int(match["n"] or 1), path.name
    stamp = datetime.fromtimestamp(path.stat().st_mtime, UTC).strftime("%Y%m%d-%H%M%S")
    return stamp, 0, path.name


def made_at(path: Path) -> str:
    """When a backup was made, as an ISO UTC time: the time in its name, else the file's."""
    moment = datetime.strptime(_made(path)[0], "%Y%m%d-%H%M%S").replace(tzinfo=UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def kind_of(path: Path) -> str:
    """How a backup was made, from its name: `auto` (as a session ended), `before-restore` (by
    a restore, of the library it replaced), `before-reset` (by a reset) or `manual`."""
    match = STAMPED.fullmatch(path.name)
    return (match["kind"] if match else None) or "manual"


@dataclass(frozen=True, slots=True)
class AutoBackup:
    """The backup a session's end made, and the older automatic ones it deleted; or why none
    was made."""

    path: Path | None
    bytes: int = 0
    pruned: tuple[str, ...] = ()
    error: str | None = None

    @property
    def note(self) -> str:
        if self.path is None:
            return _(
                "the automatic backup failed ({error}); the session ended all the same, "
                "and `didact snapshot` backs up by hand",
                error=self.error,
            )
        return ngettext(
            "backed up the library: {name} ({size}; the newest {n} automatic backup is kept)",
            "backed up the library: {name} ({size}; the newest {n} automatic backups are kept)",
            AUTO_KEEP,
            name=self.path.name,
            size=human(self.bytes),
        )

    def to_data(self) -> dict[str, JSON]:
        if self.path is None:
            return {"error": self.error}
        return {
            "name": self.path.name,
            "path": str(self.path),
            "bytes": self.bytes,
            "pruned": list[JSON](self.pruned),
        }


def auto_backup(repo: Repo) -> AutoBackup:
    """Back the library up as a session ends, then delete all but the newest `AUTO_KEEP`
    automatic backups (never other backups). A failure comes back as the reason, never
    raised: the session has ended all the same."""
    try:
        target = snapshot(repo, AUTO)
        size = target.stat().st_size
    except (OSError, ValueError, DidactError) as exc:
        return AutoBackup(None, error=_why(exc))
    automatic = [p for p in snapshots(repo) if kind_of(p) == AUTO]
    pruned: list[str] = []
    for path in automatic[: max(0, len(automatic) - AUTO_KEEP)]:
        with contextlib.suppress(OSError):  # it stays, for the next session's end to delete
            path.unlink()
            pruned.append(path.name)
    return AutoBackup(target, size, tuple(pruned))


def _why(exc: Exception) -> str:
    """What went wrong, in a few words: `No space left on device`, `Permission denied: …`."""
    if isinstance(exc, DidactError):
        return exc.message
    if isinstance(exc, OSError):
        return reason(exc)
    return str(exc) or type(exc).__name__


def find_snapshot(repo: Repo, name: str) -> Path:
    """One of the backups, by its file name (`.zip` optional) or its path."""
    found = snapshots(repo)
    given = name.strip()
    if "/" in given or "\\" in given:
        target = Path(given).expanduser().resolve()
        matches = [p for p in found if p.resolve() == target]
    else:
        matches = [p for p in found if given in (p.name, p.stem)]
    if matches:
        return matches[0]
    listed = ", ".join(p.name for p in reversed(found[-5:])) + (", …" if len(found) > 5 else "")
    raise NotFoundError(
        _("no backup {name} in {folder}", name=repr(name), folder=repo.home / BACKUPS),
        hint=(
            _("backups, newest first: {listed} (`didact snapshot --list`)", listed=listed)
            if found
            else _("there are no backups yet: `didact snapshot` makes one")
        ),
    )


def remove_snapshot(repo: Repo, name: str) -> tuple[Path, int]:
    """Delete one backup for good; returns it and its size."""
    path = find_snapshot(repo, name)
    size = path.stat().st_size
    path.unlink()
    return path, size


def keep_snapshots(repo: Repo, keep: int) -> list[tuple[Path, int]]:
    """Delete all but the newest `keep` backups, for good; returns those deleted and sizes."""
    if keep < 0:
        raise InvalidError(
            _("--keep takes a count of backups, not {keep}", keep=keep),
            hint=_("e.g. `--keep 3` keeps three"),
        )
    found = snapshots(repo)
    gone: list[tuple[Path, int]] = []
    for path in found[: max(0, len(found) - keep)]:
        gone.append((path, path.stat().st_size))
        path.unlink()
    return gone


# ---------------------------------------------------------------------------- restoring


@dataclass(frozen=True, slots=True)
class LogFacts:
    """An event log at a glance."""

    events: int = 0
    last: int = 0  # the newest event's number
    rolls: int = 0  # the highest roll number it knows of (its rolls, a clear's marker)
    damaged: int = 0  # lines that aren't events


def log_facts(lines: Iterable[str]) -> LogFacts:
    """Count a log's events and find its highest event and roll numbers. A line that isn't an
    event is counted, not raised: a damaged library can still be restored over."""
    from didact.services.dice import highest_logged

    events = last = rolls = damaged = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            event = Event.from_data(json.loads(line))
        except ValueError, KeyError, TypeError, AttributeError, AssertionError:
            damaged += 1
            continue
        events += 1
        last = max(last, event.seq)
        rolls = max(rolls, highest_logged((event,)))
    return LogFacts(events, last, rolls, damaged)


@dataclass(frozen=True, slots=True)
class Holdings:
    """What a library holds: its worlds and campaigns, and its log."""

    worlds: tuple[str, ...]
    campaigns: tuple[str, ...]
    log: LogFacts

    def describe(self) -> str:
        """`1 world (vale), 2 campaigns (run, second), 57 events, up to #e57`."""
        worlds = ngettext(
            "{n} world{names}", "{n} worlds{names}", len(self.worlds), names=_named(self.worlds)
        )
        campaigns = ngettext(
            "{n} campaign{names}",
            "{n} campaigns{names}",
            len(self.campaigns),
            names=_named(self.campaigns),
        )
        events = ngettext("{n} event", "{n} events", self.log.events)
        if self.log.last:
            events = _("{events}, up to #e{last}", events=events, last=self.log.last)
        if self.log.damaged:
            damaged = ngettext("{n} damaged log line", "{n} damaged log lines", self.log.damaged)
            events = _("{events} ({damaged})", events=events, damaged=damaged)
        return _(
            "{worlds}, {campaigns}, {events}", worlds=worlds, campaigns=campaigns, events=events
        )

    def to_data(self) -> dict[str, JSON]:
        return {
            "worlds": list[JSON](self.worlds),
            "campaigns": list[JSON](self.campaigns),
            "events": self.log.events,
            "last_event": self.log.last,
        }


def _named(names: tuple[str, ...], limit: int = 5) -> str:
    if not names:
        return ""
    return f" ({', '.join(names[:limit])}{', …' if len(names) > limit else ''})"


def holdings(repo: Repo) -> Holdings:
    """What the library holds now; its highest roll number counts the roll counter too."""
    facts = LogFacts()
    if repo.layout.log_file.is_file():
        with repo.layout.log_file.open(encoding="utf-8", errors="replace") as handle:
            facts = log_facts(handle)
    counted = _count(_read_json(repo.layout.counters_file).get("rolls"))
    facts = LogFacts(facts.events, facts.last, max(facts.rolls, counted), facts.damaged)
    return Holdings(tuple(repo.world_ids()), tuple(sorted(repo.campaign_index())), facts)


@dataclass(frozen=True, slots=True)
class Backup:
    """A backup, looked into: how and when it was made, its size and what it holds."""

    path: Path
    kind: str
    made: str  # ISO UTC
    bytes: int
    holds: Holdings

    def to_data(self) -> dict[str, JSON]:
        return {
            "name": self.path.name,
            "path": str(self.path),
            "kind": self.kind,
            "made": self.made,
            "bytes": self.bytes,
            **self.holds.to_data(),
        }


def look(repo: Repo, name: str) -> Backup:
    """One of the backups (by name, as `find_snapshot` takes it) and what it holds. Refuses a
    zip that isn't a snapshot of a library (no state or log, a damaged log), and one with an
    entry that would land outside the library or among its backups."""
    path = find_snapshot(repo, name)
    base = (repo.home / WORK / "new").resolve()  # where a restore unpacks it
    state, log = (repo.layout.rel(p) for p in (repo.layout.state_file, repo.layout.log_file))
    try:
        with zipfile.ZipFile(path) as archive:
            entries = [e for i in archive.infolist() if (e := _entry(i.filename, path, base))]
            names = {"/".join(parts) for parts in entries}
            missing = [n for n in (state, log) if n not in names]
            if len(missing) == 2:
                raise InvalidError(
                    _(
                        "{name} isn't a Didact snapshot: it has no {first} and no {second}",
                        name=path.name,
                        first=missing[0],
                        second=missing[1],
                    ),
                    hint=_other(),
                )
            if missing:
                raise InvalidError(
                    _(
                        "{name} isn't a Didact snapshot: it has no {missing}",
                        name=path.name,
                        missing=missing[0],
                    ),
                    hint=_other(),
                )
            with archive.open(log) as raw:
                facts = log_facts(io.TextIOWrapper(raw, encoding="utf-8", errors="replace"))
    except UNZIPPING as exc:
        raise InvalidError(
            _("{name} isn't a readable zip: {why}", name=path.name, why=_why(exc)), hint=_other()
        ) from exc
    if facts.damaged:
        what = (
            _("{name} can't be restored: a line of its event log isn't an event", name=path.name)
            if facts.damaged == 1
            else ngettext(
                "{name} can't be restored: {n} line of its event log isn't an event",
                "{name} can't be restored: {n} lines of its event log aren't events",
                facts.damaged,
                name=path.name,
            )
        )
        raise InvalidError(what, hint=_other())
    worlds = sorted(
        p[1] for p in entries if len(p) == 3 and (p[0], p[2]) == ("worlds", "world.yaml")
    )
    campaigns = sorted(
        p[3]
        for p in entries
        if len(p) == 5 and (p[0], p[2], p[4]) == ("worlds", "campaigns", "campaign.yaml")
    )
    holds = Holdings(tuple(worlds), tuple(campaigns), facts)
    return Backup(path, kind_of(path), made_at(path), path.stat().st_size, holds)


def _entry(name: str, backup: Path, base: Path) -> tuple[str, ...] | None:
    """Where a zip entry goes in the library, as path parts (None for a folder: its files make
    it). `base` is the resolved folder it unpacks into. Refuses an entry that would land
    outside it, or among the library's backups and working files, which no snapshot holds."""
    if name.endswith("/"):
        return None
    path = PurePosixPath(name)
    parts = path.parts
    if (
        not parts
        or path.is_absolute()
        or ".." in parts
        or not base.joinpath(*parts).resolve().is_relative_to(base)  # e.g. a drive, on Windows
    ):
        raise InvalidError(
            _(
                "refusing {backup}: its entry {name} would be written outside the library",
                backup=backup.name,
                name=repr(name),
            ),
            hint=_other(),
        )
    if parts[0].lower() in SKIP:
        raise InvalidError(
            _(
                "{backup} isn't a Didact snapshot: it holds {name}, and snapshots never hold "
                "{skipped}",
                backup=backup.name,
                name=repr(name),
                skipped=", ".join(sorted(SKIP)),
            ),
            hint=_other(),
        )
    return parts


@dataclass(frozen=True, slots=True)
class Restored:
    """A restore that happened: the backup, what the library held before, the safety backup
    of that library, and the marker that carries the numbers on."""

    backup: Backup
    before: Holdings
    safety: Path
    marker: Event


def restore(repo: Repo, name: str, *, command: str | None = None) -> Restored:
    """Replace everything in the library but its backups with a backup's contents, after a
    safety backup of the library as it is, and rebuild the search index; all under the lock.
    Undo can't take it back (the log is replaced too): restoring the safety backup can."""
    with repo.writing():
        backup = look(repo, name)  # again, now that no one else writes
        before = holdings(repo)
        counters = _read_json(repo.layout.counters_file)
        try:
            safety = _snapshot(repo, SAFETY)
        except OSError as exc:
            raise ConflictError(
                _(
                    "couldn't back the library up first ({why}), so nothing was restored",
                    why=_why(exc),
                ),
                hint=_("make room (`didact snapshot --keep 3` deletes older backups), then retry"),
            ) from exc
        work, new = repo.home / WORK, repo.home / WORK / "new"
        rolls = max(before.log.rolls, backup.holds.log.rolls)
        marker = _marker(backup, before, safety, rolls, command)
        try:
            _clear(work)  # what an interrupted restore left
            _unpack(backup.path, new)
            Repo(replace(repo.config, home=new)).init()  # the usual folders: zips drop empty ones
            _carry_on(Layout(new), marker, counters, rolls)
        except UNZIPPING as exc:
            _abandon(work, safety)
            raise ConflictError(
                _(
                    "couldn't unpack {name} ({why}), so nothing was restored",
                    name=backup.path.name,
                    why=_why(exc),
                ),
                hint=_("make room and retry, or restore another backup: `didact snapshot --list`"),
            ) from exc
        except BaseException:
            _abandon(work, safety)
            raise
        try:
            _swap(repo.home, new, work / "old")
        except OSError as exc:
            again = f"didact snapshot --restore {safety.name} --yes"
            raise ConflictError(
                _(
                    "couldn't move {name}'s files into the library ({why})",
                    name=backup.path.name,
                    why=_why(exc),
                ),
                hint=_(
                    "if the library looks wrong, restore the safety backup: `{again}`", again=again
                ),
            ) from exc
        shutil.rmtree(work, ignore_errors=True)
        _reindex(repo)
    return Restored(backup, before, safety, marker)


@dataclass(frozen=True, slots=True)
class Emptied:
    """A reset that happened: what the library held, the backup of it, the packs removed."""

    before: Holdings
    safety: Path
    packs: tuple[str, ...]


def installed_packs(repo: Repo) -> tuple[str, ...]:
    """The packs installed into this library (`didact pack install`), by id."""
    folder = repo.layout.packs_dir
    return tuple(sorted(p.name for p in folder.iterdir() if p.is_dir())) if folder.is_dir() else ()


def reset(repo: Repo, *, packs: bool) -> Emptied:
    """Empty the library, as if Didact were newly installed: every world, campaign and record,
    the history and its numbers, drafts, save points and the search index go. The backups
    stay, and so do installed packs unless `packs`. A backup of the library as it was comes
    first: undo can't take a reset back, but restoring that backup can. All under the lock."""
    with repo.writing():
        before = holdings(repo)
        removed = installed_packs(repo) if packs else ()
        try:
            safety = _snapshot(repo, EMPTIED)
        except OSError as exc:
            raise ConflictError(
                _(
                    "couldn't back the library up first ({why}), so nothing was reset",
                    why=_why(exc),
                ),
                hint=_("make room (`didact snapshot --keep 3` deletes older backups), then retry"),
            ) from exc
        work = repo.home / WORK
        kept = {BACKUPS, ".lock", WORK, DEMO_MARK}
        kept |= set() if packs else {repo.layout.packs_dir.name}
        _clear(work)  # what an interrupted restore or reset left
        old = work / "old"
        old.mkdir(parents=True)
        moved: list[tuple[Path, Path]] = []  # (where it went, where it was)
        try:
            for item in sorted(repo.home.iterdir()):
                if item.name.lower() not in kept:
                    item.rename(old / item.name)
                    moved.append((old / item.name, item))
        except OSError as exc:
            for went, was in reversed(moved):
                went.rename(was)
            shutil.rmtree(work, ignore_errors=True)
            safety.unlink(missing_ok=True)
            raise ConflictError(
                _("couldn't clear the library ({why}), so nothing was reset", why=_why(exc)),
                hint=_("check that nothing else has the library's files open, then retry"),
            ) from exc
        repo.close()
        Repo(repo.config).init()  # the usual empty folders and a fresh state
        shutil.rmtree(work, ignore_errors=True)
        _reindex(repo)
    return Emptied(before, safety, removed)


def _marker(
    backup: Backup, before: Holdings, safety: Path, rolls: int, command: str | None
) -> Event:
    """The `note` that ends the restored log, numbered after the newest event of both logs: a
    `Cleared` marker that dropped nothing but keeps the highest roll number either used, so
    the dice counters and the history carry the numbers on."""
    words = phrase(
        N_(
            "restored backup {backup} (its log up to #e{last}); "
            "the library as it was is in {safety}"
        ),
        backup=backup.path.name,
        last=backup.holds.log.last,
        safety=safety.name,
    )
    data: dict[str, JSON] = {
        CLEARED: Cleared(events=0, before=0, rolls=rolls).to_data(),
        RESTORED: {"backup": backup.path.name, "safety": safety.name, "replaced": before.log.last},
        SAY: words,
    }
    number = max(before.log.last, backup.holds.log.last) + 1
    return Event.new(number, "note", english(words), command=command, data=data)


def _clear(work: Path) -> None:
    """Remove the working folder, even when it isn't a folder: nothing is unpacked through it."""
    if work.is_symlink() or work.is_file():
        work.unlink()
    elif work.exists():
        shutil.rmtree(work)


def _unpack(path: Path, new: Path) -> None:
    """Unpack a backup into `new`, each entry checked again on the way, with its permissions
    (never fewer than the owner's read and write)."""
    new.mkdir(parents=True)
    base = new.resolve()
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            parts = _entry(info.filename, path, base)
            if parts is None:
                continue
            target = base.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink)
            mode = (info.external_attr >> 16) & 0o777
            if mode:
                target.chmod(mode | 0o600)


def _carry_on(layout: Layout, marker: Event, counters: dict[str, JSON], rolls: int) -> None:
    """End the unpacked log with the marker, and keep the library's counters where they had
    got to, so no oracle answer, draft or roll number comes round again."""
    EventLog(layout.log_file).rewrite(lambda _event: True, then=[marker])
    restored = _read_json(layout.counters_file)
    for key, value in counters.items():  # the higher of the two stays
        if key not in restored or _count(value) > _count(restored[key]):
            restored[key] = value
    restored["rolls"] = max(_count(restored.get("rolls")), rolls)
    atomic_write(layout.counters_file, json.dumps(restored))


def _swap(home: Path, new: Path, old: Path) -> None:
    """Set the library's files aside (all but its backups and working files) and move the
    unpacked ones in. If a move fails, the moves so far are undone and the error raised."""
    old.mkdir()
    moved: list[tuple[Path, Path]] = []  # (where it went, where it was)
    try:
        for item in sorted(home.iterdir()):
            if item.name.lower() not in SKIP:
                item.rename(old / item.name)
                moved.append((old / item.name, item))
        for item in sorted(new.iterdir()):
            item.rename(home / item.name)
            moved.append((home / item.name, item))
    except OSError:
        for went, was in reversed(moved):
            went.rename(was)
        raise


def _abandon(work: Path, safety: Path) -> None:
    """A restore that stopped before touching the library leaves nothing behind."""
    shutil.rmtree(work, ignore_errors=True)
    safety.unlink(missing_ok=True)


def _reindex(repo: Repo) -> None:
    """Rebuild the search index from the restored files, as `didact reindex` does."""
    from didact.store.index import Index
    from didact.store.repo import parse_entity

    repo.close()
    index = Index(repo.config.index_path, repo.home)
    try:
        index.clear()
        index.sync(repo.entity_files(), parse_entity)
    finally:
        index.close()


def _read_json(path: Path) -> dict[str, JSON]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _count(value: JSON) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


# ---------------------------------------------------------------------------- graphs


def graph(repo: Repo, center: str, depth: int, *, gm: bool) -> list[str]:
    """Mermaid lines: the record, its links out and in, `depth` steps away."""
    index = repo.index()
    scopes = repo.chain()
    rows = {r.id: r for r in index.rows(scopes)}
    start = repo.resolve(center).entity
    seen = {str(start.id)}
    edges: set[tuple[str, str, str]] = set()
    frontier = [str(start.id)]
    for _ring in range(max(1, depth)):
        next_ring: list[str] = []
        for node in frontier:
            row = rows.get(node)
            links = row.data.get("links") if row is not None else None
            for link in links if isinstance(links, list) else []:
                if isinstance(link, dict):
                    target = str(link.get("to", "")).partition("@")[0]
                    edges.add((node, str(link.get("rel", "")), target))
                    if target not in seen:
                        seen.add(target)
                        next_ring.append(target)
            for back in index.backlinks([node]):
                source_id = back.source.id
                edges.add((source_id, back.rel, node))
                rows.setdefault(source_id, back.source)
                if source_id not in seen:
                    seen.add(source_id)
                    next_ring.append(source_id)
        frontier = next_ring
    hidden = {n for n in seen if (r := rows.get(n)) is not None and r.knowledge == "secret"}
    shown = seen if gm else seen - hidden
    lines = ["graph LR"]
    for node in sorted(shown):
        row = rows.get(node)
        name = (row.name if row is not None else node).replace('"', "'")
        lines.append(f'  {_key(node)}["{name}"]')
    for source, rel, target in sorted(edges):
        if source in shown and target in shown:
            lines.append(f"  {_key(source)} -- {rel or 'link'} --> {_key(target)}")
    return lines


def _key(node: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in node)
