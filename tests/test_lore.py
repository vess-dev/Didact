"""Lore and memory: keyword-triggered entries, cards, rulings, isolation and speed."""

import json
import statistics
import time
from pathlib import Path

import pytest

from didact.core.config import resolve_config
from didact.core.ids import EntityId, Scope
from didact.services import lore, records, worlds
from didact.store.changeset import Changeset
from didact.store.repo import Repo, State
from tests.conftest import Cli


def setup(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli(
        "new", "npc", "Sweeney", "--set", "role=ferryman", "--alias", "Old Sweeney",
        "--body", "Guards the wood.\n\n## Secrets\n- He is Anglwyst's son.\n",
    )  # fmt: skip


def scan(cli: Cli, *text: str) -> list[str]:
    data = json.loads(cli("lore", "scan", *text, "--gm", "--format", "json").out)
    return [str(h["id"]) for h in data["hits"]]


def test_sweeney_in_world_a_is_not_sweeney_in_world_b(cli: Cli) -> None:
    setup(cli)
    cli("lore", "add", "Sweeney owes the river witch a debt.", "--keys", "sweeney")
    a = cli("lore", "scan", "we meet Sweeney").out
    assert "Sweeney (npc): ferryman" in a and "owes the river witch" in a
    cli("world", "new", "other", "--system", "mini-system")
    cli("campaign", "new", "elsewhere")
    cli("new", "npc", "Sweeney", "--set", "role=baker")
    b = cli("lore", "scan", "we meet Sweeney").out
    assert "Sweeney (npc): baker" in b
    assert "ferryman" not in b and "river witch" not in b


def test_matching_whole_words_plurals_phrases_and_regex(cli: Cli) -> None:
    setup(cli)
    cli("lore", "add", "Cats guard the granary.", "--keys", "cat", "--name", "cats")
    cli("lore", "add", "Wolves hunt in threes.", "--keys", "wolf", "--name", "wolves")
    cli("lore", "add", "The witch hates iron.", "--keys", "river witch", "--name", "witch")
    cli("lore", "add", "Bells ring at dusk.", "--keys", "/bell(s|ry)/", "--name", "bells")
    cli("lore", "add", "Too short.", "--keys", "ox", "--name", "ox")
    assert scan(cli, "the catalog") == []  # whole words only
    assert scan(cli, "three cats and the wolves") == ["lore:cats", "lore:wolves"]
    assert "npc:sweeney" in scan(cli, "Sweeney's boat")  # possessive
    assert "npc:sweeney" in scan(cli, "old sweeney waves")  # an alias
    assert scan(cli, "the river witch") == ["lore:witch"]
    assert scan(cli, "a witch by the river") == []  # a phrase is in order
    assert scan(cli, "up in the belfry") == [] and scan(cli, "the belfry bells") == ["lore:bells"]
    assert scan(cli, "an ox") == []  # keys under 3 letters never fire


def test_secondary_logic_priority_budget_and_groups(cli: Cli) -> None:
    setup(cli)
    for logic, name in (
        ("and_any", "any"),
        ("and_all", "all"),
        ("not_any", "none"),
        ("not_all", "some"),
    ):
        cli("lore", "add", f"{name} fires.", "--keys", "fog", "--secondary", "night, river",
            "--logic", logic, "--name", name)  # fmt: skip
    assert scan(cli, "fog at night") == ["lore:any", "lore:some"]
    assert scan(cli, "fog at night by the river") == ["lore:all", "lore:any"]
    assert scan(cli, "fog") == ["lore:none", "lore:some"]
    cli("lore", "add", "High.", "--keys", "moss", "--priority", "90", "--name", "high")
    cli("lore", "add", "Low. " + "x " * 400, "--keys", "moss", "--priority", "10", "--name", "low")
    small = json.loads(cli("lore", "scan", "moss", "--budget", "50", "--format", "json").out)
    assert [h["id"] for h in small["hits"]] == ["lore:high"] and small["omitted"] == 1
    cli("lore", "add", "Sunny.", "--keys", "weather", "--group", "sky", "--priority", "30",
        "--name", "sunny")  # fmt: skip
    cli("lore", "add", "Stormy.", "--keys", "weather", "--group", "sky", "--priority", "70",
        "--name", "stormy")  # fmt: skip
    assert scan(cli, "the weather") == ["lore:stormy"]


def test_probability_is_seeded_per_turn(cli: Cli) -> None:
    setup(cli)
    cli("lore", "add", "Never.", "--keys", "omen", "--probability", "0", "--name", "never")
    cli("lore", "add", "Always.", "--keys", "omen", "--probability", "100", "--name", "always")
    cli("lore", "add", "Maybe.", "--keys", "omen", "--probability", "50", "--name", "maybe")
    first = scan(cli, "an omen")
    assert "lore:always" in first and "lore:never" not in first
    assert scan(cli, "an omen") == first  # the same turn draws the same
    seen = set()
    for _ in range(12):
        cli("turn", "begin")
        seen.add("lore:maybe" in scan(cli, "an omen"))
    assert seen == {True, False}
    assert "probability 0% didn't come up" in cli("lore", "explain", "lore:never", "omen").out


def test_timing_cooldown_sticky_and_delay(cli: Cli) -> None:
    setup(cli)
    cli("session", "start")
    cli("lore", "add", "Rests.", "--keys", "bell", "--cooldown", "2", "--name", "rests")
    cli("lore", "add", "Lingers.", "--keys", "bell", "--sticky", "2", "--name", "lingers")
    cli("lore", "add", "Later.", "--keys", "bell", "--delay", "3", "--name", "later")
    cli("turn", "begin")  # t1
    fired = cli("log", "note", "a bell tolls").out
    assert "lore:rests" in fired and "lore:lingers" in fired and "lore:later" not in fired
    cli("turn", "begin")  # t2
    assert "lore:rests" not in scan(cli, "the bell again")  # cooling down
    assert "lore:lingers" in scan(cli, "nothing about it")  # sticky
    for _ in range(3):
        cli("turn", "begin")  # t5
    now = scan(cli, "the bell again")
    assert "lore:rests" in now and "lore:later" in now and "lore:lingers" in now


def test_recursion_and_shadowing(cli: Cli) -> None:
    setup(cli)
    cli("lore", "add", "The crown lies with the river witch.", "--keys", "crown", "--name", "crown")
    cli("lore", "add", "The river witch hates iron.", "--keys", "river witch", "--name", "witch")
    cli("lore", "add", "Iron rusts in the swamp.", "--keys", "iron", "--name", "iron")
    cli("lore", "add", "Swamps drown the careless.", "--keys", "swamp", "--name", "swamp")
    cascade = json.loads(cli("lore", "scan", "the crown", "--format", "json").out)["hits"]
    reasons = {h["id"]: h["reason"] for h in cascade}
    assert reasons["lore:crown"] == 'key "crown"'
    assert reasons["lore:witch"] == "via lore:crown" and reasons["lore:iron"] == "via lore:witch"
    assert "lore:swamp" not in reasons  # two steps deep at most
    cli("set", "lore:crown", "recursive=false")
    assert scan(cli, "the crown") == ["lore:crown"]
    cli("lore", "add", "World canon.", "--keys", "tower", "--scope", "world", "--name", "tower")
    cli("lore", "add", "Our version.", "--keys", "tower", "--name", "tower")
    hits = json.loads(cli("lore", "scan", "the tower", "--format", "json").out)["hits"]
    assert [h["text"] for h in hits] == ["Our version."]


def test_the_hook_and_tool_results_carry_lore(cli: Cli) -> None:
    setup(cli)
    cli("session", "start")
    cli("lore", "add", "Never describe spiders.", "--constant", "--kind", "preference")
    cli("lore", "add", "Sweeney owes a debt.", "--keys", "sweeney", "--name", "debt")
    prompt = json.dumps({"prompt": "I ask Sweeney about the river", "session_id": "s"})
    hooked = cli("capture", "--hook", "--text", prompt).out
    assert hooked.startswith("Didact lore for this message")
    assert "secret: He is Anglwyst's son." in hooked and "GM only" not in hooked.split("\n")[1]
    assert "Sweeney owes a debt." in hooked and "spiders" not in hooked  # constants: the brief
    again = cli("capture", "--hook", "--text", prompt).out
    assert again == ""  # shown a turn ago: not repeated yet
    assert "Always: Never describe spiders." in cli("brief").out
    cli("new", "loc", "Amber Grave", "--body", "A pool of sap.")
    pushed = cli("log", "action", "Freya reaches Amber Grave").out
    assert 'note: lore: [loc:amber-grave] (card; key "amber grave")' in pushed
    assert "lore:" not in cli("log", "action", "Back at Amber Grave").out


def test_rulings_and_explain(cli: Cli) -> None:
    setup(cli)
    cli("ruling", "add", "Can you push a scramble twice?", "No.", "--rule", "scramble")
    cli("ruling", "add", "Do boats need oars?", "Yes.", "--keys", "boat, raft")
    assert any(i.startswith("ruling:can-you-push") for i in scan(cli, "I scramble up"))
    assert any(i.startswith("ruling:do-boats") for i in scan(cli, "we build a raft"))
    explained = cli("lore", "explain", "npc:sweeney", "the ferryman").out
    assert "keys: Sweeney, Old Sweeney" in explained and "no key appears" in explained
    assert "matched: Sweeney" in cli("lore", "explain", "sweeney", "hello Sweeney").out
    cli("session", "start")
    assert (
        "never comes up in scans (it's a session record)" in cli("lore", "explain", "session:1").out
    )


@pytest.fixture(scope="module")
def big(tmp_path_factory: pytest.TempPathFactory) -> Repo:
    base = tmp_path_factory.mktemp("lore-scale")
    repo = Repo(resolve_config(home=base / "home", cache=base / "cache"))
    repo.init()
    cs = Changeset(repo, summary="world")
    worlds.create_world(cs, "vale", name="Vale", system=None, description="")
    cs.apply()
    repo.save_state(State(world="vale"))
    cs = Changeset(repo, summary="5,000 lore entries")
    for i in range(5000):
        entity = records.build_entity(
            EntityId("lore", f"entry-{i}"),
            f"Entry {i}",
            {"fields": {"keys": [f"keyword{i}", f"thing {i % 97}"], "priority": i % 100}},
            body=f"Entry {i} is about keyword{i}.",
        )
        records.create(cs, Scope("world", "vale"), entity)
    cs.apply()
    return repo


@pytest.mark.slow
def test_a_scan_over_5000_entries_is_fast(big: Repo) -> None:
    text = " ".join(f"then keyword{i * 97} went down to the old mill" for i in range(40))
    timings = []
    for _ in range(10):
        start = time.perf_counter()
        found = lore.scan(big, text, gm=True, budget=10**6)
        timings.append(time.perf_counter() - start)
    assert len(found.hits) >= 40
    assert statistics.median(timings) < 0.03, f"median {statistics.median(timings):.4f}s"


def test_lore_isnt_a_card_and_cards_have_no_bookkeeping(home: Path, cli: Cli) -> None:
    setup(cli)
    cli("session", "start", "Sweeney day")  # a session named after Sweeney
    assert [i for i in scan(cli, "Sweeney") if i.startswith("session")] == []
