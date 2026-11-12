"""Shared fixtures: an isolated data home, a CLI runner, and a pack with a dice plugin."""

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from didact.cli.main import main

FIXTURE_PACKS = Path(__file__).parent / "fixtures" / "packs"
PACKS = Path(__file__).resolve().parents[1] / "packs"


@dataclass(frozen=True, slots=True)
class Run:
    code: int
    out: str
    err: str


type Cli = Callable[..., Run]


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An isolated, not-yet-created data home and cache for one test."""
    data_home = tmp_path / "home"
    monkeypatch.setenv("DIDACT_HOME", str(data_home))
    monkeypatch.setenv("DIDACT_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("DIDACT_PACK_PATH", str(FIXTURE_PACKS))
    monkeypatch.setenv("DIDACT_PACK_UPDATES", "")  # no test looks online
    monkeypatch.delenv("DIDACT_LANG", raising=False)
    return data_home


@pytest.fixture
def lucky(home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The `lucky` pack (a Python dice plugin, see tests/plugin_pack.py) on the pack path."""
    from tests.plugin_pack import write

    pack = write(tmp_path / "extra")
    paths = os.pathsep.join([str(FIXTURE_PACKS), str(pack.parent)])
    monkeypatch.setenv("DIDACT_PACK_PATH", paths)
    return pack


@pytest.fixture
def system_packs(home: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The pack folders in the repository's `packs/` on the pack path, as when developing them
    (the packs that ship with Didact are otherwise only there to install)."""
    monkeypatch.setenv("DIDACT_PACK_PATH", os.pathsep.join([str(FIXTURE_PACKS), str(PACKS)]))
    return PACKS


@pytest.fixture
def thesaurus(cli: Cli) -> None:
    """A tiny WordNet for synonyms (tests/fixtures/wordnet-mini.xml), in the test's cache."""
    mini = Path(__file__).parent / "fixtures" / "wordnet-mini.xml"
    assert cli("setup", "thesaurus", "--from", str(mini)).code == 0


@pytest.fixture
def cli(home: Path, capsys: pytest.CaptureFixture[str]) -> Cli:
    """Run `didact <args>` in-process and capture its output."""

    def run(*args: str) -> Run:
        code = main(list(args))
        captured = capsys.readouterr()
        return Run(code, captured.out, captured.err)

    return run
