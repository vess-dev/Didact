"""The `grimwild-ce` pack's advancement: experience and its options, level caps, the levels a
campaign starts at, level 0, which talents a level can bring, and what each core talent has a
character choose at creation and as it grows."""

import json
import re
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests.conftest import PACKS, Cli
from tests.test_grimwild import MAGICAL

pytestmark = pytest.mark.usefixtures("system_packs")
SORCERY_PATHS = {"blood", "decay", "flame", "frost", "lux", "shadow", "stone", "tempest"}
STATS = ("brawn", "agility", "wits", "presence")


def setup(cli: Cli, seed: str) -> None:
    assert cli("world", "new", "wild", "--system", "grimwild-ce", "--seed", seed).code == 0
    assert cli("campaign", "new", "c", "--seed", seed).code == 0


def _json(cli: Cli, *args: str) -> Any:  # parsed JSON, read freely in tests
    out = cli(*args, "--format", "json")
    assert out.code == 0, out.err
    return json.loads(out.out)


def _sheet(cli: Cli, ref: str) -> dict[str, Any]:
    return dict(_json(cli, "show", ref)["mechanics"]["grimwild-ce"])


def _made(cli: Cli, *extra: str, **prefill: object) -> dict[str, Any]:
    """A random character's draft, with what the prefill decides (the book has no name tables:
    it gives the name)."""
    args = ("char", "new", *extra, "--mode", "random", "--prefill", json.dumps(prefill))
    draft: dict[str, Any] = _json(cli, *args)["draft"]
    return draft


def _entities(cli: Cli, **prefill: object) -> list[dict[str, Any]]:
    return list(_made(cli, **prefill)["entities"])


def _fields(cli: Cli, **prefill: object) -> dict[str, Any]:
    return dict(_entities(cli, **prefill)[0]["fields"])


def _pc(cli: Cli, name: str, path: str) -> str:
    """A random character on a path, committed; its id."""
    draft = _made(cli, name=name, path=path)
    assert cli("char", "commit", draft["id"]).code == 0
    return f"pc:{name.casefold()}"


def _advance(cli: Cli, ref: str, prefill: str = "{}") -> str:
    """Level a character up (the dice decide what the prefill doesn't), committed; its text."""
    started = cli("char", "advance", ref, "--mode", "random", "--prefill", prefill)
    assert started.code == 0, started.err
    draft = re.search(r"#(c\d+) pc:", started.out)
    assert draft is not None, started.out
    assert cli("char", "commit", draft.group(1)).code == 0
    return started.out


def test_slow_progression_and_focused_growth_double_the_xp(cli: Cli) -> None:
    setup(cli, "xp")
    cli("new", "pc", "Kestrel", "--set", "path=Fighter", "--set", "xp=2")
    assert "level 2 is ready" in cli("do", "experience", "who=kestrel").out  # 3 of 2
    profiles = ("slow-progression=on", "focused-growth=on", "flavor=low", "flavor=cozy")
    for n, profile in enumerate(profiles):
        cli("campaign", "new", f"c{n}", "--seed", "xp")  # a flavor implies slow progression
        cli("campaign", "profile", profile)
        cli("new", "pc", "Kestrel", "--set", "path=Fighter", "--set", "xp=2")
        refused = cli("char", "advance", "kestrel")
        assert refused.code == 1 and "has 2 of 4 XP" in refused.err, profile
    cli("campaign", "profile", "flavor=sword-and-sorcery")  # slow xp, but carousing earns +1
    assert "3 of 4 XP" in cli("do", "experience", "who=kestrel", "why=carousing").out
    unthemed = cli("do", "experience", "who=kestrel", "why=theme")
    assert "Themed XP comes with focused growth" in unthemed.out
    cli("campaign", "profile", "focused-growth=on")
    themed = cli("do", "experience", "who=kestrel", "why=theme")
    assert "a bonus XP for what happened" in themed.out and "level 2 is ready" in themed.out
    quest = cli("do", "experience", "who=kestrel", "why=quest")
    assert "The quest is complete" in quest.out


def test_levels_stop_at_the_cap(cli: Cli) -> None:
    setup(cli, "caps")
    cli("new", "pc", "Kestrel", "--set", "path=Fighter", "--set", "level=3", "--set", "xp=40")
    for profile in ("scale=smaller", "flavor=low", "flavor=cozy"):
        cli("campaign", "profile", "scale=standard", "flavor=heroic")
        cli("campaign", "profile", profile)
        capped = cli("char", "advance", "kestrel")
        assert capped.code == 1, profile
        assert "the highest level this game allows (3)" in capped.err, profile
    cli("campaign", "profile", "scale=standard", "flavor=heroic")
    assert "reaches level 4" in _advance(cli, "kestrel")
    cli("set", "kestrel", "level=7")
    assert "allows (7)" in cli("char", "advance", "kestrel").err


def test_a_campaign_can_start_above_level_1(cli: Cli) -> None:
    setup(cli, "starts")
    cli("campaign", "profile", "scale=larger")
    larger = _fields(cli, name="Lars", path="Fighter")
    assert larger["level"] == 3 and len(larger["talents"]) == 4
    assert "level 3: fighter-weapon-mastery grows" in " ".join(larger["path_notes"])
    cli("campaign", "profile", "scale=standard", "flavor=noblebright")
    noble, *others = _entities(cli, name="Nell", path="Fighter")  # a talent's pool, arcana
    assert noble["fields"]["level"] == 2 and len(noble["fields"]["talents"]) == 3
    arcana = [e for e in others if e["type"] == "arcana"]
    assert [a["fields"]["tier"] for a in arcana] == ["minor"]
    cli("campaign", "profile", "flavor=high")  # 2 minor arcana or 1 major (p. 186)
    high, *others = _entities(cli, name="Hal", path="Fighter", arcana_start="2 minor arcana")
    assert high["fields"]["level"] == 3
    assert [e["fields"]["tier"] for e in others if e["type"] == "arcana"] == ["minor", "minor"]
    cli("campaign", "profile", "magic=none")  # no arcana at all
    assert "arcana" not in [e["type"] for e in _entities(cli, name="Nia", path="Fighter")]


def test_level_0_reaches_level_1_with_its_core_and_last_stat_point(cli: Cli) -> None:
    setup(cli, "zero")
    cli("campaign", "profile", "level-zero=on")
    half_core = "fighter-arcane-training"
    draft = _made(cli, name="Zed", path="Wizard", talent_list="Fighter", talent=half_core)
    fields = draft["entities"][0]["fields"]
    assert fields["level"] == 0 and fields["talents"] == [half_core]  # allowed before the core
    assert sum(fields[s] for s in STATS) == 7  # 4 + 3 points
    assert sum(1 for n in fields["path_notes"] if n.startswith("theorem: ")) == 3  # its own
    cli("char", "commit", draft["id"])
    cli("set", "zed", "xp=1")
    done = _advance(cli, "zed")
    zed = _sheet(cli, "zed")
    core, other = zed["talents"]  # the half core gives way to the core and another talent
    assert (zed["level"], core) == (1, "wizard-spellcraft") and other != half_core
    assert f"replaces the half core talent {half_core}" in done
    assert sum(zed[s] for s in STATS) == 8 and not zed.get("stat_raised")  # the last point
    assert sum(1 for n in zed["path_notes"] if n.startswith("theorem: ")) == 7  # + Spellcraft's 4
    back = cli("do", "switch-talent", "who=zed", f"drop={other}", f"take={half_core}")
    assert "own half core talent" in back.out


def test_level_1_brings_the_core_talents_pools(cli: Cli) -> None:
    setup(cli, "pools")
    cli("campaign", "profile", "level-zero=on")
    draft = _made(cli, name="Cleo", path="Cleric", talent_list="Cleric")
    assert [e["type"] for e in draft["entities"]] == ["pc"]  # no core talent, no rites yet
    cli("char", "commit", draft["id"])
    cli("set", "cleo", "xp=1")
    _advance(cli, "cleo")
    rites = [t for t in _json(cli, "track", "list")["tracks"] if t["name"].startswith("Cleo's ")]
    assert sorted(t["value"]["max"] for t in rites) == [4, 4, 6]  # a major and two minor rites
    pool = _json(cli, "show", rites[0]["id"])
    assert {"rel": "of", "to": "pc:cleo"} in pool["links"]
    assert any(n.startswith("rites: major ") for n in _sheet(cli, "cleo")["path_notes"])


def test_talents_bring_their_pools(cli: Cli) -> None:
    setup(cli, "talent-pools")
    grenades = {"talent_list": "Artificer", "talent": "artificer-grenades"}
    draft = _made(cli, name="Tink", path="Fighter", **grenades)
    _pc, pool = draft["entities"]  # made after the name, at creation
    assert pool["name"] == "Tink's Grenades" and pool["fields"]["value"] == {"value": 3, "max": 3}
    cli("char", "commit", draft["id"])
    cli("set", "tink", "xp=2")
    _advance(cli, "tink", '{"talent_list": "Rogue", "talent": "rogue-poisoner"}')
    pools = {t["name"]: t["value"]["max"] for t in _json(cli, "track", "list")["tracks"]}
    assert pools == {"Tink's Grenades": 3, "Tink's Poisons": 4}  # and at a level
    cli("campaign", "profile", "armor=on")  # Bulwark is reworked into the armor pool
    bulwark = {"talent_list": "Fighter", "talent": "fighter-bulwark"}
    names = [e["name"] for e in _entities(cli, name="Bul", path="Fighter", **bulwark)]
    assert "Bul's Bulwark" not in names and "Bul's armor" in names


def test_a_level_keeps_out_what_the_path_or_the_magic_rules_out(cli: Cli) -> None:
    setup(cli, "eligible")
    bard = _pc(cli, "Bea", "Bard")
    cli("set", bard, "xp=20")
    lists = _json(cli, "char", "advance", bard)["draft"]
    assert lists["waiting"] == "talent_list"
    assert "Legacy talents (ask your GM)" in lists["open"]["options"]
    berserker = _json(cli, "char", "choose", lists["id"], "Berserker")["draft"]["open"]["options"]
    assert "berserker-warcry" not in berserker  # [Prohibited: Bard]
    assert "berserker-mighty" in berserker
    cli("char", "discard", lists["id"])
    cli("campaign", "profile", "magic=none")
    options = _json(cli, "char", "advance", bard)["draft"]["open"]["options"]
    assert not MAGICAL & set(options) and "Background talents" in options
    cli("campaign", "profile", "magic=standard")
    rolled: set[str] = set()
    for _ in range(12):  # the dice never take a legacy talent: those need the GM's OK
        text = _advance(cli, bard)
        found = re.search(r"talent-lists: ([^\n]+)", text)
        assert found is not None
        rolled.add(found.group(1).split(" · ")[0])
        cli("set", bard, "level=1", "xp=20")
    assert not any("Legacy" in r for r in rolled) and len(rolled) > 3


def test_the_second_talent_comes_from_any_list_but_not_the_half_core(cli: Cli) -> None:
    setup(cli, "second")
    lists: set[str] = set()
    for n in range(14):
        core, second = _fields(cli, name=f"Bard {n}", path="Bard")["talents"]
        assert core == "bard-inspiration" and second != "berserker-warcry"
        lists.add(second.split("-")[0])
    assert len(lists) > 3  # own path, other paths, background talents
    heritage = _fields(cli, name="Ash", path="Fighter", talent_list="Background talents")
    assert heritage["talents"][1].startswith("background-")


def test_character_creation_makes_the_core_talents_choices(cli: Cli) -> None:
    setup(cli, "cores")
    witch = _fields(cli, name="Wyn", path="Witch")
    assert len(set(witch["words"])) == 6  # 6 words of power from the crucible (p. 84)
    rogue = _fields(cli, name="Rook", path="Rogue")
    assert len(set(rogue["skills"])) == 3
    sorcerer = _fields(cli, name="Sol", path="Sorcerer")
    magic = set(sorcerer["magic"])
    assert len(magic) == 4 and magic & SORCERY_PATHS and magic - SORCERY_PATHS  # 1 of each
    assert any(n.startswith("twists: ") for n in sorcerer["path_notes"])
    fighter = _fields(cli, name="Fay", path="Fighter", fighting_style="ranged")
    assert "fighting style: ranged" in fighter["path_notes"]
    warlock, pool = _entities(cli, name="Wick", path="Warlock")
    assert len(warlock["fields"]["talents"]) == 3 and pool["name"] == "Wick's Patience"
    assert pool["fields"]["value"] == {"value": 8, "max": 8}
    cleric = _entities(cli, name="Cleo", path="Cleric")
    assert [e["fields"]["value"]["max"] for e in cleric[1:]] == [6, 4, 4]  # the rites
    druid = _entities(cli, name="Dru", path="Druid")
    assert druid[1]["name"] == "Dru's Wild Shape" and druid[1]["fields"]["value"]["max"] == 2
    summoner = _entities(cli, name="Sum", path="Summoner", aspect="telepathic")
    assert summoner[0]["fields"]["aspects"] == ["telepathic"]
    assert summoner[1]["name"] == "Sum's vassal"
    artificer = _fields(cli, name="Art", path="Artificer")
    assert len(artificer["touchstones"]) == 6


@pytest.mark.parametrize(
    ("path", "level", "field", "grows"),
    [
        ("Witch", 2, "words", 2),
        ("Sorcerer", 2, "magic", 1),
        ("Artificer", 2, "touchstones", 2),
        ("Psion", 3, "bastions", 1),
        ("Rogue", 3, "skills", 1),
        ("Summoner", 3, "aspects", 1),
    ],
)
def test_core_talents_grow_with_their_choices(
    cli: Cli, path: str, level: int, field: str, grows: int
) -> None:
    setup(cli, f"grow-{path}")
    pc = _pc(cli, "Hero", path)
    before = len(_sheet(cli, pc)[field])
    cli("set", pc, f"level={level - 1}", "xp=20")
    text = _advance(cli, pc)
    after = _sheet(cli, pc)[field]
    assert f"Level {level}: the core talent grows" in text
    assert len(after) == before + grows and len(set(after)) == len(after)


def test_theorems_and_eldritch_talents_grow_too(cli: Cli) -> None:
    setup(cli, "grow-more")
    wizard = _pc(cli, "Merra", "Wizard")
    cli("set", wizard, "xp=20")
    _advance(cli, wizard)
    notes = _sheet(cli, wizard)["path_notes"]
    assert sum(1 for n in notes if n.startswith("theorem: ")) == 5  # 4, +1 at level 2
    warlock = _pc(cli, "Wick", "Warlock")
    cli("set", warlock, "level=2", "xp=20")
    _advance(cli, warlock)
    sheet = _sheet(cli, warlock)
    assert sum(1 for n in sheet["path_notes"] if n.startswith("Eldritch Talent: ")) == 2
    assert len(sheet["talents"]) == 5  # core, second, level 3's, and two Eldritch Talents


def test_stat_progression_is_once_per_character(cli: Cli) -> None:
    setup(cli, "stats")
    cli("campaign", "profile", "stat-progression=on")
    pc = _pc(cli, "Kes", "Fighter")
    cli("set", pc, "xp=20", "brawn=1")
    _advance(cli, pc, '{"growth": "stat", "stat": "brawn"}')
    sheet = _sheet(cli, pc)
    assert sheet["stat_raised"] is True and sheet["brawn"] == 2 and sheet["level"] == 2
    again = _json(cli, "char", "advance", pc, "--prefill", '{"talent_list": "Monk"}')["draft"]
    assert again["waiting"] == "talent"  # the stat is spent: no question, a talent


def test_the_talent_lists_match_the_paths() -> None:
    text = (PACKS / "grimwild-ce" / "tables" / "paths.yaml").read_text()
    documents = list(YAML(typ="safe").load_all(text))
    tables = {str(doc["table"]): doc for doc in documents if isinstance(doc, dict)}
    paths = {str(e["text"]): e["data"] for e in tables["paths"]["entries"]}
    lists = {str(e["text"]): e["data"] for e in tables["talent-lists"]["entries"]}
    for name, data in paths.items():
        assert lists[name]["talents"] == data["talents"], name
        assert lists[name]["magical"] == data["magical"] == (name in MAGICAL), name
    assert set(lists) - set(paths) == {"Background talents", "Legacy talents (ask your GM)"}
