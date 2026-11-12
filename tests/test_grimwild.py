"""The `grimwild-ce` pack: action rolls with thorns, damage, pools, story rolls."""

import json
import re

import pytest

from tests.conftest import PACKS, Cli

PACK = PACKS / "grimwild-ce"
pytestmark = pytest.mark.usefixtures("system_packs")
LEVELS = {6: 3, 5: 2, 4: 2, 3: 1, 2: 1, 1: 1}


def setup(cli: Cli, seed: str = "wilds") -> None:
    cli("world", "new", "wild", "--system", "grimwild-ce", "--seed", seed)
    cli("campaign", "new", "c", "--seed", seed)
    cli(
        "new", "pc", "Kestrel",
        "--set", "brawn=2", "--set", "agility=3", "--set", "wits=1", "--set", "presence=2",
    )  # fmt: skip


def act(cli: Cli, *args: str) -> dict[str, object]:
    done = cli("do", "action", "who=kestrel", *args, "--format", "json")
    assert done.code == 0, done.err
    data: dict[str, object] = json.loads(done.out)
    return data


def test_the_highest_die_sets_the_result_and_thorns_cut_it(cli: Cli) -> None:
    setup(cli)
    seen: set[str] = set()
    for _ in range(40):
        run = act(cli, "stat=agility", "thorns=2")
        values = run["values"]
        assert isinstance(values, dict)
        dice = values["roll.dice"]
        thorns = values["thorn.dice"]
        assert isinstance(dice, list) and isinstance(thorns, list)
        assert len(dice) == 3 and len(thorns) == 2
        cuts = sum(1 for t in thorns if t >= 7)
        level = LEVELS[max(dice)] - cuts
        expected = (
            "critical" if dice.count(6) >= 2
            else {3: "perfect", 2: "messy", 1: "grim"}.get(level, "disaster")
        )  # fmt: skip
        assert run["outcome"] == expected, (dice, thorns)
        seen.add(str(run["outcome"]))
        if run["outcome"] == "disaster":
            cli("set", "kestrel", "spark=0")  # disasters give spark; keep the next rolls clean
    assert len(seen) >= 3


def test_damage_adds_thorns_and_spark_is_spent(cli: Cli) -> None:
    setup(cli)
    cli("set", "kestrel", "spark=2")
    spent = act(cli, "stat=agility", "spark=2")
    values = spent["values"]
    assert isinstance(values, dict) and len(values["roll.dice"]) == 5  # 3 + 2 spark
    kestrel = json.loads(cli("show", "kestrel", "--format", "json").out)
    assert kestrel["mechanics"]["grimwild-ce"]["spark"] in (0, 1)  # 1 if it was a disaster
    assert "spark to spend" in cli("do", "action", "who=kestrel", "stat=wits", "spark=3").out
    cli("do", "mark", "who=kestrel", "stat=wits")
    marked = act(cli, "stat=wits")
    marked_values = marked["values"]
    assert isinstance(marked_values, dict) and marked_values["total_thorns"] == 1
    assert "wits" not in json.loads(cli("show", "kestrel", "--format", "json").out)["mechanics"][
        "grimwild-ce"
    ].get("marks", [])  # a used mark clears
    cli("do", "mark", "who=kestrel", "stat=brawn")
    second = cli("do", "mark", "who=kestrel", "stat=brawn")
    assert "that's harm instead" in second.out and "bloodied" in second.out
    assert "desperate" not in cli("do", "harm", "who=kestrel", "kind=rattled").out  # p. 121
    assert "desperate" in cli("do", "harm", "who=kestrel", "kind=bloodied").out  # a second
    hurt = act(cli, "stat=brawn")
    hurt_values = hurt["values"]
    assert (
        isinstance(hurt_values, dict) and hurt_values["total_thorns"] == 3
    )  # mark, bloodied, desperate
    assert "dropped" in cli("do", "harm", "who=kestrel", "kind=rattled").out  # desperate again
    assert cli("do", "rest", "who=kestrel").code == 0
    harm = json.loads(cli("show", "kestrel", "--format", "json").out)["mechanics"]["grimwild-ce"]
    assert not harm.get("harm") and not harm.get("marks")


def test_protecting_montages_and_spark_on_story_rolls(cli: Cli) -> None:
    setup(cli, "extras")
    guard = json.loads(
        cli("do", "defense", "who=kestrel", "stat=agility", "protect", "--format", "json").out
    )
    assert len(guard["values"]["roll.dice"]) == 1  # 1d to protect an ally, not Agility's 3d
    cli("do", "harm", "who=kestrel", "kind=bloodied")
    run = json.loads(cli("do", "montage", "who=kestrel", "stat=brawn", "--format", "json").out)
    assert len(run["values"]["roll.dice"]) == 2 and run["values"]["total_thorns"] == 1
    calm = json.loads(cli("do", "montage", "who=kestrel", "--format", "json").out)
    assert calm["values"]["total_thorns"] == 0  # bloodied only counts for a related stat
    cli("set", "kestrel", "spark=1")
    lucky = cli("do", "story-roll", "who=kestrel", "spark=1", "--format", "json")
    assert len(json.loads(lucky.out)["values"]["roll.dice"]) == 3
    assert "needs who=" in cli("do", "story-roll", "spark=1").out


def test_a_scene_with_thorns_a_task_pool_and_a_story_roll(cli: Cli) -> None:
    setup(cli, "scene")
    cli("session", "start")
    cli("scene", "new", "The goblin bridge")
    assert cli("track", "new", "Goblins", "--kind", "pool", "--size", "4").code == 0
    outcomes: list[str] = []
    for _ in range(12):
        run = act(cli, "stat=brawn", "thorns=1")
        outcomes.append(str(run["outcome"]))
        if run["outcome"] in ("critical", "perfect", "messy"):
            rolled = json.loads(cli("track", "roll", "goblins", "--format", "json").out)
            if rolled["empty"]:
                break
            if rolled["dropped"] == 0:  # push through: a mark for 1d
                pushed = cli("do", "push", "who=kestrel", "pool=goblins", "stat=brawn")
                assert pushed.code == 0 and "pushes" in pushed.out
        cli("do", "rest", "who=kestrel")  # keep damage from piling up in this test
    story = cli("do", "story-roll", "question=Do more goblins come?", "--format", "json")
    assert json.loads(story.out)["outcome"] in ("perfect", "messy", "grim", "disaster")
    journal = cli("session", "show").out
    assert "grimwild-ce.action" in journal and "pool Goblins" in journal
    assert "grimwild-ce.story-roll" in journal
    assert outcomes


def test_a_random_adventurer_never_contradicts_itself(cli: Cli) -> None:
    cli("world", "new", "wild", "--system", "grimwild-ce", "--seed", "chargen")
    cli("campaign", "new", "c", "--seed", "chargen")
    for _ in range(8):
        made = json.loads(cli("char", "new", "--mode", "random", "--format", "json").out)["draft"]
        assert made["waiting"] == "name"  # the book has no name tables
        fields = made["entities"][0]["fields"]
        first, second = fields["backgrounds"]
        assert first != second and len(fields["wises"]) == 6
        for key in ("traits", "desires"):  # two yes, one no, and never both
            *yes, no = fields[key]
            assert len(set(yes)) == 2 and no.startswith("not ") and no[4:] not in yes
        core, talent = fields["talents"]
        assert core != talent and core.startswith(fields["path"].casefold())
        assert sum(fields[s] for s in ("brawn", "agility", "wits", "presence")) == 8  # 4 + 4
    refused = cli("char", "roll", made["id"])
    assert refused.code == 1 and "nothing to roll name from" in refused.err
    assert cli("char", "choose", made["id"], "Wren").code == 0
    assert cli("char", "commit", made["id"]).code == 0
    assert cli("char", "check", "wren").code == 0
    sheet = cli("sheet", "wren").out
    assert f"backgrounds {first}, {second}" in sheet and "wises" in sheet


def test_the_pack_validates_and_its_tests_pass(cli: Cli) -> None:
    assert cli("pack", "validate", str(PACK)).code == 0
    result = cli("pack", "test", str(PACK))
    assert result.code == 0, result.out + result.err


def test_its_arcana_paths_and_potions_come_out_whole(cli: Cli) -> None:
    setup(cli)
    glove = cli("spawn", "everflame-glove", "--format", "json")  # its sensories aren't notes
    assert glove.code == 0, glove.err
    glove = json.loads(cli("show", "everflame-glove", "--format", "json").out)
    assert glove["mechanics"]["grimwild-ce"]["sensories"][0].startswith("charred leather")
    assert cli("spawn", "psion").code == 0
    psion = json.loads(cli("show", "psion", "--format", "json").out)
    assert psion["mechanics"]["grimwild-ce"]["extra_path"] is True  # not taken for bookkeeping
    potion = cli("table", "roll", "potion-qualities").out
    assert re.search(r": It's a \w+ \w+ with [\w-]+ \w+ inside\.", potion)


def test_a_generator_offers_each_option_once(cli: Cli) -> None:
    setup(cli)
    made = json.loads(cli("gen", "run", "grimwild-ce.weapon", "--format", "json").out)["draft"]
    assert made["waiting"] == "styles"
    listed = made["open"]["note"].split("from: ")[1].split(" (")[0].split(", ")
    assert len(listed) == len(set(listed)) == 18  # the table prints each style in two cells


MAGICAL = {
    "Artificer",
    "Cleric",
    "Druid",
    "Psion",
    "Sorcerer",
    "Summoner",
    "Warlock",
    "Witch",
    "Wizard",
}


def test_the_magic_dial_shapes_characters_and_arcana(cli: Cli) -> None:
    setup(cli)
    assert cli("campaign", "profile", "magic=none").code == 0
    for n in range(6):  # no magic: the magical paths are out
        made = json.loads(
            cli("char", "new", "--mode", "random", "--prefill", f'{{"name": "Hero {n}"}}',
                "--format", "json").out
        )["draft"]  # fmt: skip
        assert made["entities"][0]["fields"]["path"] not in MAGICAL
    refused = cli("gen", "run", "grimwild-ce.arcana", "--auto")
    assert refused.code != 0 and "No magic (an option): there's no arcana" in refused.err
    assert cli("campaign", "profile", "magic=common", "scale=larger").code == 0
    made = json.loads(
        cli(
            "char", "new", "--mode", "random", "--prefill", '{"name": "Cy", "path": "Fighter"}',
            "--format", "json",
        ).out
    )["draft"]  # fmt: skip
    hero, *rest = made["entities"]  # the core, one more, and a talent each for levels 2 and 3
    assert hero["fields"]["level"] == 3 and len(hero["fields"]["talents"]) == 4
    assert [e["type"] for e in rest] == ["arcana"] and hero["fields"]["arcana"] == [rest[0]["key"]]


def test_levels_bring_a_talent_the_core_growth_and_stop_at_the_cap(cli: Cli) -> None:
    setup(cli, "levels")
    cli("set", "kestrel", "path=Bard", "talents+=bard-inspiration", "xp=2")
    started = cli(
        "char",
        "advance",
        "kestrel",
        "--prefill",
        '{"talent_list": "Fighter", "talent": "fighter-bulwark"}',
    )
    assert started.code == 0, started.err
    assert (
        "Level 2: the core talent grows. At levels 2, 4, and 6, gain +1 inspiration" in started.out
    )
    draft = re.search(r"#(c\d+) pc:kestrel", started.out)
    assert draft is not None
    assert cli("char", "commit", draft.group(1)).code == 0
    sheet = json.loads(cli("show", "kestrel", "--format", "json").out)["mechanics"]["grimwild-ce"]
    assert (sheet["level"], sheet["xp"]) == (2, 0)
    assert sheet["talents"] == ["bard-inspiration", "fighter-bulwark"]
    assert "level 2: bard-inspiration grows" in sheet["path_notes"][0]

    cli("campaign", "profile", "scale=smaller", "milestone-levels=on")  # no XP; at most level 3
    again = cli(
        "char",
        "advance",
        "kestrel",
        "--prefill",
        '{"talent_list": "Bard", "talent": "bard-wordplay"}',
    )
    assert again.code == 0, again.err
    assert "Level 3" not in again.out  # a bard's core grows at 2, 4 and 6
    assert cli("char", "commit", str(re.findall(r"#(c\d+)", again.out)[0])).code == 0
    capped = cli("char", "advance", "kestrel")
    assert capped.code == 1 and "the highest level this game allows (3)" in capped.err
