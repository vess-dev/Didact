"""Cut short: a crash or a full disk at any point of a write leaves the change whole or gone.

The sweep cuts every write of the undo sweep's session short in turn, once as if the process
died and once as if the disk were full, and the library must be exactly as it was before that
change, with the log to match; undo and redo still take the whole session back and forth.
"""

import errno
import json
import shlex
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

import didact.store.changeset as changeset_module
import didact.store.recovery as recovery_module
from didact.core.config import resolve_config
from didact.store import fsutil
from didact.store.changeset import Changeset
from didact.store.events import Event, EventLog
from didact.store.repo import Repo
from tests.conftest import Cli
from tests.test_undo_sweep import SESSION, _all_the_way, _differences, _files


class Killed(BaseException):
    """The process dying: nothing gets to clean up."""


@dataclass(slots=True)
class Fault:
    """Makes the `at`th file write of a change fail with `problem` (counting from 0)."""

    at: int = -1
    problem: BaseException | None = None
    count: int = 0
    fired: bool = False

    def arm(self, at: int, problem: BaseException) -> None:
        self.at, self.problem, self.count, self.fired = at, problem, 0, False

    def disarm(self) -> None:
        self.problem = None

    def check(self) -> None:
        if self.problem is not None and self.count == self.at:
            self.fired = True
            problem, self.problem = self.problem, None
            raise problem
        self.count += 1


@pytest.fixture
def fault(monkeypatch: pytest.MonkeyPatch) -> Iterator[Fault]:
    found = Fault()
    write, remove = fsutil.atomic_write, fsutil.remove_file

    def atomic_write(path: Path, text: str) -> None:
        found.check()
        write(path, text)

    def remove_file(path: Path) -> None:
        found.check()
        remove(path)

    monkeypatch.setattr(changeset_module, "atomic_write", atomic_write)
    monkeypatch.setattr(changeset_module, "remove_file", remove_file)
    yield found


@pytest.fixture
def befores(monkeypatch: pytest.MonkeyPatch, home: Path) -> list[dict[str, bytes]]:
    """The library's files as they were before each change was applied."""
    found: list[dict[str, bytes]] = []
    apply = Changeset.apply

    def recording(self: Changeset) -> Event:
        found.append(_files(home))
        return apply(self)

    monkeypatch.setattr(Changeset, "apply", recording)
    return found


def _repo(home: Path) -> Repo:
    return Repo(resolve_config(home=home, cache=home.parent / "cache"))


def _lines() -> list[str]:
    return [line for line in SESSION.strip().splitlines() if line.strip()]


def _events(home: Path) -> list[dict[str, object]]:
    text = (home / "log" / "events.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def test_every_write_of_a_session_killed_in_turn_is_taken_back(
    cli: Cli, home: Path, fault: Fault, befores: list[dict[str, bytes]]
) -> None:
    start = _files(home)
    kills = 0
    for line in _lines():
        for at in range(100):
            fault.arm(at, Killed())
            try:
                result = cli(*shlex.split(line))
            except Killed:
                kills += 1
                fault.disarm()
                after = cli("history")  # the next command, whatever it is, clears up
                assert "a change was cut short and taken back" in after.out, (line, at)
                assert _files(home) == befores[-1], (
                    line,
                    at,
                    _differences(befores[-1], _files(home)),
                )
                assert not (home / "log" / "applying.json").exists()
                continue
            assert not fault.fired
            fault.disarm()
            assert result.code == 0, (line, result.err)
            break
    assert kills > len(_lines())  # some commands write several files
    end = _files(home)
    undone = _all_the_way(cli, "undo")
    assert _files(home) == start, _differences(start, _files(home))
    assert _all_the_way(cli, "redo") == undone
    assert _files(home) == end, _differences(end, _files(home))
    numbers = [e["seq"] for e in _events(home)]
    assert numbers == list(range(1, len(numbers) + 1))  # none lost, none repeated


def test_every_write_of_a_session_refused_in_turn_changes_nothing(
    cli: Cli, home: Path, fault: Fault, befores: list[dict[str, bytes]]
) -> None:
    for line in _lines():
        for at in range(100):
            fault.arm(at, OSError(errno.ENOSPC, "No space left on device"))
            result = cli(*shlex.split(line))
            fault.disarm()
            if not fault.fired:
                assert result.code == 0, (line, result.err)
                break
            assert result.code != 0, (line, at)
            assert "nothing was changed" in result.err and "disk space" in result.err, result.err
            assert "Traceback" not in result.err
            assert _files(home) == befores[-1], (line, at, _differences(befores[-1], _files(home)))
            assert not (home / "log" / "applying.json").exists()
            assert all(e["kind"] != "note" for e in _events(home))  # nothing to clear up later


def _three_file_change(home: Path) -> tuple[Changeset, dict[str, bytes]]:
    repo = _repo(home)
    root = home / "global" / "note"
    root.mkdir(parents=True, exist_ok=True)
    (root / "old.md").write_text("old\n", encoding="utf-8")
    (root / "gone.md").write_text("gone\n", encoding="utf-8")
    before = _files(home)
    cs = Changeset(repo, summary="three files")
    cs.write(root / "old.md", "new\n")
    cs.write(root / "made.md", "made\n")
    cs.delete(root / "gone.md")
    cs.append(root / "journal.jsonl", '{"beat": 1}\n')
    return cs, before


@pytest.mark.parametrize("at", [0, 1, 2, 3])
def test_a_change_killed_part_way_is_taken_back_whole(
    cli: Cli, home: Path, fault: Fault, at: int
) -> None:
    cli("init")
    cs, before = _three_file_change(home)
    fault.arm(at, Killed())
    with pytest.raises(Killed):
        cs.apply()
    fault.disarm()
    assert (home / "log" / "applying.json").exists()
    shown = cli("doctor")
    assert "a change was cut short and is half written" in shown.out
    repaired = cli("doctor", "--repair")
    assert "note: a change was cut short and taken back: three files" in repaired.out
    assert _files(home) == before, _differences(before, _files(home))
    events = _events(home)
    assert events[-1]["kind"] == "note" and events[-1]["seq"] == len(events)
    assert "event log: " in cli("doctor").out and "cut short" not in cli("doctor").out


def test_a_crash_before_the_event_is_logged_leaves_nothing_to_take_back(
    cli: Cli, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli("init")
    cs, before = _three_file_change(home)

    def dying(self: EventLog, **_kwargs: object) -> Event:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write('{"seq": 1, "id": "x", "ts": "2026-')  # half of it got written
        raise Killed

    append = EventLog.append
    monkeypatch.setattr(EventLog, "append", dying)
    with pytest.raises(Killed):
        cs.apply()
    monkeypatch.setattr(EventLog, "append", append)
    assert cli("roll", "d6").code == 0
    assert _files(home) == before
    assert [e["kind"] for e in _events(home)] == ["roll"]
    assert not (home / "log" / "applying.json").exists()


def test_a_file_edited_after_the_crash_is_left_as_it_is(cli: Cli, home: Path, fault: Fault) -> None:
    cli("init")
    cs, _before = _three_file_change(home)
    fault.arm(2, Killed())
    with pytest.raises(Killed):
        cs.apply()
    fault.disarm()
    edited = home / "global" / "note" / "old.md"
    edited.write_text("edited by hand\n", encoding="utf-8")
    result = cli("history")
    assert "global/note/old.md was edited since, so it was left as it is" in result.out
    assert edited.read_text(encoding="utf-8") == "edited by hand\n"
    assert not (home / "global" / "note" / "made.md").exists()


def test_an_edit_back_by_hand_is_not_mistaken_for_a_crash(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("new", "npc", "Tom", "--body", "Runs the mill.")
    path = _repo(home).resolve("tom").path
    was = path.read_text(encoding="utf-8")
    cli("set", "tom", "mood=grim")
    path.write_text(was, encoding="utf-8")  # put back by hand, in an editor
    assert cli("roll", "d6").code == 0
    assert path.read_text(encoding="utf-8") == was


def test_an_identical_append_already_there_stays_when_its_twin_is_taken_back(
    cli: Cli, home: Path, fault: Fault
) -> None:
    cli("init")
    journal = home / "global" / "journal.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    journal.write_text("same\n", encoding="utf-8")
    cs = Changeset(_repo(home), summary="twins")
    cs.write(home / "global" / "first.md", "first\n")
    cs.append(journal, "same\n")
    fault.arm(1, Killed())  # the first file is in, the append isn't
    with pytest.raises(Killed):
        cs.apply()
    fault.disarm()
    cli("history")
    assert journal.read_text(encoding="utf-8") == "same\n"
    assert not (home / "global" / "first.md").exists()


def test_a_disk_still_full_while_taking_back_leaves_it_to_the_next_command(
    cli: Cli, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli("init")
    cs, before = _three_file_change(home)
    write = restore = fsutil.atomic_write
    calls = {"n": 0}

    def full(path: Path, text: str) -> None:
        calls["n"] += 1
        if calls["n"] > 1:
            raise OSError(errno.ENOSPC, "No space left on device")
        write(path, text)

    def still_full(path: Path, text: str) -> None:
        if path.name != "applying.json":  # the marker had its room: only the files are refused
            raise OSError(errno.ENOSPC, "No space left on device")
        restore(path, text)

    monkeypatch.setattr(changeset_module, "atomic_write", full)
    monkeypatch.setattr(recovery_module, "atomic_write", still_full)
    with pytest.raises(Exception, match="part of it is written"):
        cs.apply()
    monkeypatch.setattr(recovery_module, "atomic_write", restore)
    assert (home / "log" / "applying.json").exists()
    cli("history")
    assert _files(home) == before, _differences(before, _files(home))


@pytest.mark.parametrize("keep", [1, 9, 23, 40])
def test_a_torn_last_line_is_ignored_and_then_cut_off(cli: Cli, home: Path, keep: int) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("session", "start")
    cli("new", "npc", "Tom")
    log = home / "log" / "events.jsonl"
    whole = log.read_bytes()
    torn = '{"seq":99,"summary":"é—ü…'.encode()[:keep]  # cut, maybe inside a character
    log.write_bytes(whole + torn)
    for command in (["history"], ["rolls"], ["show", "tom"]):
        assert cli(*command).code == 0, command
    assert "its last line was cut short" in cli("doctor").out
    assert cli("set", "tom", "mood=grim").code == 0
    assert cli("roll", "d6").code == 0
    assert cli("log", "note", "after").code == 0
    numbers = [e["seq"] for e in _events(home)]
    assert numbers == list(range(1, len(numbers) + 1))
    assert cli("undo").code == 0


def test_doctor_repair_cuts_a_torn_line(cli: Cli, home: Path) -> None:
    cli("init")
    cli("roll", "d6")
    log = home / "log" / "events.jsonl"
    log.write_bytes(log.read_bytes() + b'{"seq":2,"id')
    assert "cut off a half-written line" in cli("doctor", "--repair").out
    assert log.read_bytes().endswith(b"\n")
    assert "nothing to repair" in cli("doctor", "--repair").out


def test_a_whole_last_line_that_lost_its_newline_stays(cli: Cli, home: Path) -> None:
    cli("init")
    cli("roll", "d6")
    log = home / "log" / "events.jsonl"
    log.write_bytes(log.read_bytes().rstrip(b"\n"))
    assert cli("roll", "d6").code == 0
    assert [e["seq"] for e in _events(home)] == [1, 2]


def test_a_corrupt_line_inside_the_log_is_reported_not_cut(cli: Cli, home: Path) -> None:
    cli("init")
    cli("roll", "d6")
    log = home / "log" / "events.jsonl"
    log.write_bytes(b"not json\n" + log.read_bytes())
    doctor = cli("doctor")
    assert doctor.code == 1 and "corrupt event log line 1" in doctor.out
    result = cli("rolls")
    assert result.code == 1 and "restore the line from a backup" in result.err
    assert log.read_bytes().startswith(b"not json\n")


def test_a_refusal_from_the_disk_is_an_error_with_a_fix(cli: Cli, tmp_path: Path) -> None:
    result = cli("batch", "--file", str(tmp_path / "missing.txt"))
    assert result.code == 1
    assert "error (storage): couldn't read or write a file: No such file" in result.err
    assert "fix: check the disk and the path" in result.err


def test_the_note_reaches_json_readers(cli: Cli, home: Path, fault: Fault) -> None:
    cli("init")
    cs, _before = _three_file_change(home)
    fault.arm(0, Killed())
    with pytest.raises(Killed):
        cs.apply()
    fault.disarm()
    data = json.loads(cli("history", "--format", "json").out)
    assert data["notices"] == ["a change was cut short and taken back: three files"]
