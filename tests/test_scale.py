"""Scale: 1,000 records, fast search, atomic mass changes, exact undo, index parity."""

import statistics
import time
from pathlib import Path

import pytest

from didact.core.config import resolve_config
from didact.core.ids import EntityId, Scope
from didact.services import admin, records, worlds
from didact.store import changeset as changesets
from didact.store.changeset import Changeset
from didact.store.index import Index
from didact.store.repo import Repo, State, parse_entity

N = 1000
WORDS = ("forest", "sap", "grave", "hollow", "ember", "gate", "moss", "crow", "iron", "tide")


def _snapshot(home: Path) -> dict[str, bytes]:
    return {
        p.relative_to(home).as_posix(): p.read_bytes()
        for p in sorted((home / "worlds").rglob("*"))
        if p.is_file()
    }


@pytest.fixture(scope="module")
def big(tmp_path_factory: pytest.TempPathFactory) -> Repo:
    base = tmp_path_factory.mktemp("scale")
    repo = Repo(resolve_config(home=base / "home", cache=base / "cache"))
    repo.init()
    cs = Changeset(repo, summary="world")
    worlds.create_world(cs, "vale", name="Vale", system=None, description="")
    cs.apply()
    repo.save_state(State(world="vale"))
    world = Scope("world", "vale")
    cs = Changeset(repo, summary="bulk create")
    for i in range(N):
        name = f"{WORDS[i % 10].title()} Keeper {i}"
        entity = records.build_entity(
            EntityId("npc", f"keeper-{i}"),
            name,
            {"hp": i % 7, "home": f"The {WORDS[(i * 3) % 10]} of Vale"},
            body=f"Keeper number {i} tends the {WORDS[(i * 7) % 10]} near Vale.",
        )
        records.create(cs, world, entity)
    cs.apply()
    return repo


@pytest.mark.slow
def test_search_is_fast(big: Repo) -> None:
    index = big.index()
    scopes = [Scope("world", "vale")]
    timings = []
    for word in WORDS:
        start = time.perf_counter()
        hits = index.search(word, scopes, limit=20)
        timings.append(time.perf_counter() - start)
        assert hits
    assert statistics.median(timings) < 0.05


@pytest.mark.slow
def test_mass_replace_is_atomic_and_undo_is_byte_exact(big: Repo) -> None:
    before = _snapshot(big.home)
    cs = Changeset(big, summary="replace Vale")
    stats = admin.replace_text(
        cs, "Vale", "Valemark", scopes=[Scope("world", "vale")], whole_word=True
    )
    assert stats.replacements >= 2 * N
    change_id = cs.stage()
    assert _snapshot(big.home) == before  # previewing and staging change nothing
    event = Changeset.load_staged(big, change_id).apply()
    assert len(event.files) == N + 1  # every record plus world.yaml, in one event
    assert "Valemark" in (big.home / "worlds/vale/npc/keeper-0.md").read_text()
    changesets.undo(big, event)
    assert _snapshot(big.home) == before


@pytest.mark.slow
def test_rename_across_many_records(big: Repo) -> None:
    before = _snapshot(big.home)
    cs = Changeset(big, summary="link spree")
    target = big.resolve("npc:keeper-0")
    for i in range(1, 50):
        located = big.resolve(f"npc:keeper-{i}")
        records.edit(cs, located.path, lambda e: records.add_link(e, "ally", "npc:keeper-0"))
    links = cs.apply()
    cs = Changeset(big, summary="rename keeper-0")
    admin.rename(cs, target, "The First Keeper", reslug=True, rewrite_text=False, text_scopes=[])
    event = cs.apply()
    assert len(event.files) == 51  # delete + create + 49 re-pointed links
    assert "npc:the-first-keeper" in (big.home / "worlds/vale/npc/keeper-7.md").read_text()
    changesets.undo(big, event)
    changesets.undo(big, links)
    assert _snapshot(big.home) == before


@pytest.mark.slow
def test_rebuild_equals_incremental(big: Repo) -> None:
    incremental = big.index().dump()
    fresh = Index(big.config.index_path.with_name("fresh.sqlite"), big.home)
    fresh.sync(big.entity_files(), parse_entity)
    assert fresh.dump() == incremental
    fresh.close()
