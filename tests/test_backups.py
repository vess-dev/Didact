"""Backups: the automatic one each session's end makes (the newest five kept), and restoring a
backup (`snapshot --restore`): previewed first, a safety backup before it, the numbers carried
on, and nothing written outside the library."""

import errno
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)


def setup(cli: Cli) -> None:
    assert cli("world", "new", "vale", "--system", "mini-system").code == 0
    assert cli("campaign", "new", "run").code == 0
    cli("new", "pc", "Wren", "--set", "hp=4")


def files(home: Path) -> dict[str, bytes]:
    """Every file in the library but its backups and lock, by path."""
    found: dict[str, bytes] = {}
    for path in sorted(home.rglob("*")):
        rel = path.relative_to(home)
        if path.is_file() and rel.parts[0] not in ("backups", ".lock"):
            found[rel.as_posix()] = path.read_bytes()
    return found


def zipped(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def backups(home: Path) -> list[str]:
    folder = home / "backups"
    return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []


def snapshot(cli: Cli) -> Path:
    made = cli("snapshot", "--format", "json")
    assert made.code == 0, made.err
    return Path(json.loads(made.out)["snapshot"])


def events(home: Path) -> list[dict[str, Any]]:
    lines = (home / "log" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def restore(cli: Cli, name: str) -> dict[str, Any]:
    done = cli("snapshot", "--restore", name, "--yes", "--format", "json")
    assert done.code == 0, done.err
    return dict(json.loads(done.out))


# ---------------------------------------------------------------------------- automatic


def test_ending_a_session_backs_up_and_keeps_the_newest_five(cli: Cli, home: Path) -> None:
    setup(cli)
    manual = snapshot(cli)
    folder = home / "backups"
    older = [f"snapshot-2020010{day}-000000-auto.zip" for day in range(1, 7)]
    by_hand = ["snapshot-20200101-000000.zip", "snapshot-20200101-000000-before-restore.zip"]
    for name in [*older, *by_hand]:
        (folder / name).write_bytes(b"PK")
    cli("session", "start")
    cli("log", "action", "Wren crosses the ford")
    ended = cli("session", "end", "--summary", "Wren crossed the ford.")
    assert ended.code == 0 and "✔ session 1 ended" in ended.out
    note = ended.out.splitlines()[-1]
    assert note.startswith("note: backed up the library: snapshot-") and "-auto.zip" in note
    assert "the newest 5 automatic backups are kept" in note
    first = next(n for n in backups(home) if n.endswith("-auto.zip") and n not in older)
    inside = zipped(folder / first)
    campaign = "worlds/vale/campaigns/run"
    assert b"status: closed" in inside[f"{campaign}/session/1.md"]  # the session as it ended
    assert b"Wren crosses the ford" in inside[f"{campaign}/journal/session-001.jsonl"]

    cli("session", "start")
    second = json.loads(cli("session", "end", "--format", "json").out)["backup"]
    assert second["name"].endswith("-auto.zip") and second["pruned"] == [older[2]]
    automatic = [n for n in backups(home) if n.endswith("-auto.zip")]
    assert automatic == sorted([*older[3:], first, second["name"]])  # the newest five
    assert {manual.name, *by_hand} <= set(backups(home))  # others are never pruned by this

    listed = cli("snapshot", "--list").out
    assert f"- {first} (" in listed and f"- {manual.name} (" in listed
    assert listed.count(", automatic)") == 5 and listed.count(", before a restore)") == 1
    kinds = {
        b["name"]: b["kind"]
        for b in json.loads(cli("snapshot", "--list", "--format", "json").out)["snapshots"]
    }
    assert kinds[first] == "auto" and kinds[manual.name] == "manual"
    assert kinds[by_hand[1]] == "before-restore"
    assert cli("snapshot", "--remove", first).code == 0 and first not in backups(home)
    kept = cli("snapshot", "--keep", "2")  # --keep counts every backup, of any kind
    assert kept.code == 0 and backups(home) == sorted([manual.name, second["name"]])


def test_a_failed_backup_doesnt_stop_the_session_ending(
    cli: Cli, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup(cli)
    cli("session", "start")

    def full(*args: object, **kwargs: object) -> None:
        raise OSError(errno.ENOSPC, "No space left on device")

    with monkeypatch.context() as patched:
        patched.setattr(zipfile.ZipFile, "write", full)
        ended = cli("session", "end", "--summary", "Rain all day.")
    assert ended.code == 0 and "✔ session 1 ended" in ended.out
    assert "note: the automatic backup failed (No space left on device)" in ended.out
    assert "session ended all the same" in ended.out
    assert "(closed)" in cli("session", "show", "1").out.splitlines()[0]
    assert backups(home) == []  # no half-written zip is left behind

    (home / "backups").rmdir()
    (home / "backups").write_text("not a folder")
    cli("session", "start")
    ended = json.loads(cli("session", "end", "--format", "json").out)
    assert ended["backup"]["error"].startswith("File exists")
    assert "(closed)" in cli("session", "show", "2").out.splitlines()[0]


def test_a_dry_run_ends_nothing_and_backs_nothing_up(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("session", "start")
    dry = cli("session", "end", "--dry-run")
    assert dry.code == 0 and "backed up" not in dry.out and backups(home) == []


# ---------------------------------------------------------------------------- restoring


def test_restore_previews_then_restores_records_journal_and_log(cli: Cli, home: Path) -> None:
    setup(cli)
    cli("new", "npc", "Tom", "--body", "A miller with a limp.")
    cli("session", "start")
    cli("log", "action", "Wren knocks on the mill door")
    cli("roll", "d6")
    made = snapshot(cli)
    kept = zipped(made)

    cli("set", "wren", "hp=2")
    cli("rm", "npc:tom")
    cli("new", "npc", "Ann", "--body", "A tinker with a cart.")
    cli("log", "note", "Ann arrives at the mill")
    cli("roll", "d8")
    cli("world", "new", "isles")
    before, listed = files(home), backups(home)
    preview = cli("snapshot", "--restore", made.stem)  # `.zip` is optional, as for --remove
    assert preview.code == 0, preview.err
    lines = preview.out.splitlines()
    assert lines[0] == (
        f"Restoring {made.name} would replace everything in the library but its backups."
    )
    assert "- it holds: 1 world (vale), 1 campaign (run), " in preview.out
    assert "- the library now: 2 worlds (isles, vale), 1 campaign (run), " in preview.out
    assert "backed up into backups/ (snapshot-<time>-before-restore.zip)" in preview.out
    assert "undo can't take a restore back: restoring that safety backup can" in preview.out
    assert lines[-1] == f"Restore it with `didact snapshot --restore {made.name} --yes`."
    assert files(home) == before and backups(home) == listed  # a preview changes nothing

    done = cli("snapshot", "--restore", made.name, "--yes")
    assert done.code == 0 and done.out.startswith(f"✔ restored {made.name}, made ")
    assert "undo can't take a restore back" in done.out
    now = files(home)
    log, restored_log = now.pop("log/events.jsonl"), kept.pop("log/events.jsonl")
    now.pop("log/counters.json")
    kept.pop("log/counters.json")
    assert now == kept  # records, sheets, the journal and the state: exactly the backup's
    assert log.startswith(restored_log)  # the backup's log, then the restore's note
    assert len(log[len(restored_log) :].splitlines()) == 1
    assert not (home / ".restore").exists()

    assert "hp 4/4" in cli("show", "wren").out and "npc:tom" in cli("show", "Tom").out
    assert cli("show", "Ann").code == 1 and "isles" not in cli("world", "list").out
    journal = cli("session", "show", "1").out
    assert "Wren knocks on the mill door" in journal and "Ann arrives" not in journal
    assert "npc:tom" in cli("find", "miller").out  # the search index was rebuilt
    assert "npc:ann" not in cli("find", "tinker").out


def test_numbers_carry_on_after_a_restore(cli: Cli, home: Path) -> None:
    setup(cli)
    assert cli("roll", "d6").out.startswith("#r1 ")
    made = snapshot(cli)
    cli("roll", "d6")
    cli("roll", "d6")  # #r3
    cli("new", "npc", "Tom")
    last = events(home)[-1]["seq"]

    done = restore(cli, made.name)
    marker = events(home)[-1]
    assert done["event"] == marker["seq"] == last + 1  # after the newest number before it
    assert marker["kind"] == "note" and marker["summary"].startswith(f"restored backup {made.name}")
    assert marker["data"]["cleared"]["rolls"] == 3 and marker["data"]["cleared"]["events"] == 0
    assert marker["data"]["restored"]["safety"] == done["safety"]["name"]

    assert f"(#e{last + 2})" in cli("new", "npc", "Ann").out  # the next change
    assert cli("roll", "d6").out.startswith("#r4 ")  # the next roll
    assert "no roll #r2" in cli("undo", "--event", "r2").err  # it went with the old log

    history = cli("history").out
    assert f"- #e{last + 1} " in history and "restored backup" in history
    undo = cli("undo", "--event", f"e{last + 1}")
    assert undo.code == 1 and "no file changes to undo" in undo.err  # a restore can't be undone
    assert f"--restore {done['safety']['name']}" in undo.err  # but its safety backup goes back
    assert cli("undo").code == 0 and cli("show", "Ann").code == 1  # changes still can

    again = restore(cli, made.name)  # the log goes back to #r1; the marker keeps #r4
    assert again["event"] == last + 5 and events(home)[-1]["data"]["cleared"]["rolls"] == 4
    (home / "log" / "counters.json").unlink()  # without the counter, the log still knows
    assert cli("roll", "d6").out.startswith("#r5 ")


def test_the_safety_backup_takes_the_library_back(cli: Cli, home: Path) -> None:
    setup(cli)
    made = snapshot(cli)
    cli("new", "npc", "Tom", "--body", "A miller.")
    cli("session", "start")
    cli("log", "action", "Wren waves at Tom")
    cli("roll", "d20")
    were = files(home)

    done = restore(cli, made.name)
    safety = done["safety"]["name"]
    assert safety.endswith("-before-restore.zip") and (home / "backups" / safety).is_file()
    assert zipped(home / "backups" / safety) == were  # the library just as it was
    assert f"- {safety} (" in cli("snapshot", "--list").out
    assert cli("show", "Tom").code == 1

    back = cli("snapshot", "--restore", safety, "--yes")
    assert back.code == 0 and f"✔ restored {safety}" in back.out
    now = files(home)
    log, old_log = now.pop("log/events.jsonl"), were.pop("log/events.jsonl")
    assert now == were  # every record, journal and counter as it was
    assert log.startswith(old_log)
    notes = [json.loads(line) for line in log[len(old_log) :].splitlines()]
    assert [n["seq"] for n in notes] == [done["event"] + 1]  # one more note: numbers go on
    assert "A miller." in cli("show", "Tom").out
    assert "Wren waves at Tom" in cli("session", "show", "1").out
    assert len([n for n in backups(home) if n.endswith("-before-restore.zip")]) == 2


# ---------------------------------------------------------------------------- refusals


def plant(home: Path, name: str, entries: dict[str, str]) -> str:
    """A zip in the backups folder with exactly these entries, names as given."""
    with zipfile.ZipFile(home / "backups" / name, "w") as archive:
        for entry, text in entries.items():
            archive.writestr(zipfile.ZipInfo(entry), text)
    return name


def test_unsafe_and_foreign_zips_are_refused(cli: Cli, home: Path, tmp_path: Path) -> None:
    setup(cli)
    made = snapshot(cli)
    state = zipped(made)["state.yaml"].decode()
    log = (home / "log" / "events.jsonl").read_text(encoding="utf-8")
    good = {"state.yaml": state, "log/events.jsonl": log}
    outside = "would be written outside the library"
    cases: list[tuple[dict[str, str] | None, str]] = [
        ({**good, "../evil-1.txt": "x"}, outside),
        ({**good, f"{tmp_path}/evil-2.txt": "x"}, outside),
        ({**good, "worlds/../../evil-3.txt": "x"}, outside),
        ({**good, "backups/evil.zip": "x"}, "isn't a Didact snapshot: it holds 'backups/evil.zip'"),
        ({"state.yaml": state}, "isn't a Didact snapshot: it has no log/events.jsonl"),
        ({"log/events.jsonl": log}, "isn't a Didact snapshot: it has no state.yaml"),
        ({**good, "log/events.jsonl": "not an event\n"}, "a line of its event log isn't an event"),
        (None, "isn't a readable zip"),
    ]
    refused: dict[str, str] = {}
    for number, (entries, problem) in enumerate(cases, start=1):
        name = f"snapshot-20200101-00000{number}.zip"
        if entries is None:
            (home / "backups" / name).write_bytes(b"PK, but not a zip")
        else:
            plant(home, name, entries)
        refused[name] = problem
    before, listed = files(home), backups(home)
    for name, problem in refused.items():
        for yes in ([], ["--yes"]):
            result = cli("snapshot", "--restore", name, *yes)
            assert result.code == 1 and problem in result.err, (name, result.err)
            assert "`didact snapshot --list`" in result.err
    assert files(home) == before and backups(home) == listed  # no safety backup either
    assert not list(tmp_path.rglob("evil-*")) and not (home / ".restore").exists()

    missing = cli("snapshot", "--restore", "snapshot-nope", "--yes")
    assert missing.code == 1 and "no backup 'snapshot-nope'" in missing.err
    assert "(`didact snapshot --list`)" in missing.err
    assert cli("snapshot", "--yes").code == 2  # --yes goes with --restore
    both = cli("snapshot", "--restore", made.name, "--list")
    assert both.code == 2 and "pick one of" in both.err


# ---------------------------------------------------------------------------- the web app


def test_the_library_page_restores_a_backup(web: Browser, cli: Cli) -> None:  # noqa: F811
    cli("session", "start")
    cli("session", "end", "--summary", "Nothing much.")  # an automatic backup
    web.run("snapshot", next_="/library")  # and one made by hand
    listed = json.loads(cli("snapshot", "--list", "--format", "json").out)["snapshots"]
    auto = next(b["name"] for b in listed if b["kind"] == "auto")
    manual = next(b["name"] for b in listed if b["kind"] == "manual")
    library = web.get("/library").body
    for name in (auto, manual):
        assert f"/library/restore-backup?name={name}" in library
    assert "Restore…" in library and '<span class="chip is-dim"><span>auto</span></span>' in library
    assert "the newest 5 of those stay" in library

    asked = web.get(f"/library/restore-backup?name={auto}").body
    assert f"Restore the backup {auto}?" in asked
    assert 'class="card dialog-page is-wide"' in asked and 'class="dialog-text"' in asked
    assert "it holds: 1 world (vale), 1 campaign (run)" in asked and "safety backup" in asked
    assert 'value="--restore"' in asked and 'value="--yes"' in asked

    cli("new", "npc", "Latecomer")
    done = web.run("snapshot", "--restore", auto, "--yes", next_="/library#backups")
    assert f"restored {auto}" in done.body and "before restore</span>" in done.body
    assert cli("show", "Latecomer").code == 1 and "npc:sweeney" in cli("show", "Sweeney").out

    missing = web.get("/library/restore-backup?name=nope").body
    assert "no backup" in missing and "didact snapshot --list" in missing
    assert 'value="--yes"' not in missing
