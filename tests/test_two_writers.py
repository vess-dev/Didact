"""Two writers at once, as when an LLM plays from the command line while the browser app is
open: nothing is lost and no number repeats. Every write holds the library's lock, and a
change planned before another one landed on the same file is refused rather than applied.
"""

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from didact.core.config import resolve_config
from didact.core.errors import ConflictError
from didact.store.changeset import Changeset
from didact.store.fsutil import exclusive_lock
from didact.store.repo import Repo
from tests.conftest import Cli


def _repo(home: Path) -> Repo:
    return Repo(resolve_config(home=home, cache=home.parent / "cache"))


def test_a_change_planned_before_another_landed_is_refused(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("new", "npc", "Tom", "--body", "Runs the mill.")
    repo = _repo(home)
    path = repo.resolve("tom").path
    planned = Changeset(repo, summary="the slow writer")
    planned.write(path, path.read_text(encoding="utf-8").replace("Runs", "Owns"))
    cli("set", "tom", "mood=grim")  # the other writer gets there first
    with pytest.raises(ConflictError, match="changed since this change was planned"):
        planned.apply()
    shown = json.loads(cli("show", "tom", "--format", "json").out)
    assert shown["fields"]["mood"] == "grim" and "Runs the mill." in shown["body"]


def test_a_writer_waits_for_the_lock_and_then_goes_ahead(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("new", "npc", "Tom")
    lock = _repo(home).layout.lock_file
    holding, release = threading.Event(), threading.Event()

    def hold() -> None:
        with exclusive_lock(lock):
            holding.set()
            release.wait(5)

    other = threading.Thread(target=hold)
    other.start()
    assert holding.wait(5)
    with (
        pytest.raises(ConflictError, match="another didact process is writing"),
        exclusive_lock(lock, timeout=0.2),
    ):
        pass
    threading.Timer(0.3, release.set).start()
    started = time.monotonic()
    assert cli("set", "tom", "mood=grim").code == 0  # waits for the lock, then writes
    assert time.monotonic() - started >= 0.2
    other.join(5)


def test_two_processes_writing_at_once_lose_nothing(cli: Cli, home: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    script = (
        "import sys\n"
        "from didact.cli.main import main\n"
        "for i in range(12):\n"
        "    assert main(['new', 'npc', f'{sys.argv[1]} {i}']) == 0\n"
        "    assert main(['roll', 'd6']) == 0\n"
    )
    env = dict(os.environ)
    writers = [
        subprocess.Popen([sys.executable, "-c", script, name], env=env, stdout=subprocess.DEVNULL)
        for name in ("Ash", "Birch")
    ]
    assert [w.wait(120) for w in writers] == [0, 0]
    listed = cli("find", "--type", "npc", "--limit", "100", "--format", "json")
    found = json.loads(listed.out)["results"]
    assert len(found) == 24  # every record made it
    events = [
        json.loads(line)
        for line in (home / "log" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    numbers = [e["seq"] for e in events]
    assert numbers == list(range(1, len(numbers) + 1))  # none lost, none repeated
    rolls = [e["summary"].split()[0] for e in events if e["kind"] == "roll"]
    assert len(rolls) == len(set(rolls)) == 24  # #r1 … #r24, each once
