"""The `grimwild-ce` pack's rules in play: criticals and thorns, magical twists, stakes and
interrupts, damage and being dropped, suspense, quarrels, pools, factions, the session's rhythm,
downtime, and solo play's side characters."""

import json
from typing import Any

import pytest

from tests.conftest import Cli

pytestmark = pytest.mark.usefixtures("system_packs")


def setup(cli: Cli, seed: str) -> None:
    assert cli("world", "new", "wild", "--system", "grimwild-ce", "--seed", seed).code == 0
    assert cli("campaign", "new", "c", "--seed", seed).code == 0
    cli(
        "new", "pc", "Kestrel",
        "--set", "brawn=2", "--set", "agility=3", "--set", "wits=1", "--set", "presence=2",
    )  # fmt: skip
    cli(
        "new", "pc", "Wren",
        "--set", "brawn=1", "--set", "agility=2", "--set", "wits=3", "--set", "presence=2",
    )  # fmt: skip


def _json(cli: Cli, *args: str) -> Any:  # parsed JSON, read freely in tests
    out = cli(*args, "--format", "json")
    assert out.code == 0, out.err
    return json.loads(out.out)


def _sheet(cli: Cli, ref: str) -> dict[str, Any]:
    return dict(_json(cli, "show", ref)["mechanics"]["grimwild-ce"])


def _text(run: dict[str, Any]) -> str:
    return "\n".join(str(line) for line in run["lines"])


def _until(cli: Cli, outcome: str, *args: str) -> dict[str, Any]:
    """Run a check until it comes up with the outcome (seeded: the same every time)."""
    for _ in range(60):
        run: dict[str, Any] = _json(cli, "do", *args)
        if run["outcome"] == outcome:
            return run
    raise AssertionError(f"no {outcome} in 60 of {args}")


def test_criticals_ignore_thorns_on_every_roll(cli: Cli) -> None:
    setup(cli, "crits")
    cut_criticals = dict.fromkeys(("action", "defense", "story-roll"), 0)
    for _ in range(90):
        for rule, args in (
            ("action", ("who=kestrel", "stat=agility", "thorns=3")),
            ("defense", ("who=kestrel", "stat=agility", "thorns=3")),
            ("story-roll", ("dice=3", "thorns=3")),
        ):
            run = _json(cli, "do", rule, *args)
            values = run["values"]
            dice, thorns = values["roll.dice"], values["thorn.dice"]
            cuts = sum(1 for t in thorns if t >= 7)
            if dice.count(6) >= 2:  # two 6s: thorns can't cut it
                assert run["outcome"] == ("perfect" if rule == "story-roll" else "critical")
                cut_criticals[rule] += 1 if cuts else 0
            else:
                level = {6: 3, 5: 2, 4: 2}.get(max(dice), 1) - cuts
                expected = {3: "perfect", 2: "messy", 1: "grim"}.get(level, "disaster")
                assert run["outcome"] == expected, (rule, dice, thorns)
    assert all(cut_criticals.values()), cut_criticals  # each met a critical a thorn would cut


def test_a_twist_counts_the_thorns_ones(cli: Cli) -> None:
    setup(cli, "twists")
    plain = _json(cli, "do", "action", "who=kestrel", "stat=wits", "spell", "thorns=3")
    assert "twist" not in _text(plain).lower()  # no sorcery, no dangerous magic
    cli("set", "kestrel", "path=Sorcerer", "talents+=sorcerer-sorcery", "path_notes+=twists: curse")
    by_thorns = twists = 0
    for _ in range(80):
        run = _json(cli, "do", "action", "who=kestrel", "stat=wits", "spell", "thorns=3")
        values = run["values"]
        ones = values["roll.dice"].count(1) + values["thorn.dice"].count(1)
        twisted = "Magical twist (Sorcery" in _text(run)
        assert twisted == (ones >= 2), values
        if twisted:
            assert "Curse: the GM takes +1 suspense" in _text(run)
            by_thorns += values["roll.dice"].count(1) < 2
            twists += 1
    assert by_thorns  # thorns included (p. 76)
    assert _json(cli, "oracle", "show")["state"]["suspense"] == twists  # each curse: +1
    cli("campaign", "profile", "magic=dangerous")
    for _ in range(60):
        run = _json(cli, "do", "action", "who=wren", "stat=wits", "spell", "thorns=3")
        values = run["values"]
        ones = values["roll.dice"].count(1) + values["thorn.dice"].count(1)
        assert ("Dangerous magic (p. 172): a magical twist" in _text(run)) == (ones >= 2)


def test_stakes_interrupts_and_solo_guide_the_impact_move(cli: Cli) -> None:
    setup(cli, "stakes")
    said: dict[str, str] = {}
    for _ in range(40):
        for stakes in ("low", "dire"):
            run = _json(cli, "do", "action", "who=kestrel", "stat=wits", f"stakes={stakes}")
            said[f"{stakes} {run['outcome']}"] = _text(run)
            cli("set", "kestrel", "spark=0")
    assert "weighs 1 mark, or softer" in said["low grim"]
    assert "drops Kestrel (`didact do dropped who=pc:kestrel`)" in said["dire grim"]
    assert "drops Kestrel" not in said.get("dire perfect", "")
    cli("campaign", "profile", "flavor=cozy")  # low stakes by default (p. 187)
    grim = _until(cli, "grim", "action", "who=kestrel", "stat=wits")
    assert "Low stakes" in _text(grim)
    messy = _until(cli, "messy", "action", "who=kestrel", "stat=brawn", "interrupt")
    assert "the GM keeps (or takes) their suspense" in _text(messy)
    assert _json(cli, "oracle", "show")["state"]["suspense"] == 1  # taken by itself
    cli("campaign", "profile", "flavor=heroic", "solo=on")
    solo = _until(cli, "messy", "action", "who=kestrel", "stat=brawn")
    assert "(you have 1 suspense): are you in a scene with a challenge" in _text(solo)
    cli("do", "suspense", "take=2")
    solo = _until(cli, "messy", "action", "who=kestrel", "stat=brawn")
    assert "you have 3 suspense, 3 or more: make an impact move" in _text(solo)


def test_harm_ends_in_dropped_and_retirement_in_death(cli: Cli) -> None:
    setup(cli, "ladder")
    cli("do", "harm", "who=kestrel", "kind=bloodied")
    cli("do", "harm", "who=kestrel", "kind=rattled")  # another kind: no step up (p. 121)
    assert "desperate" in cli("do", "harm", "who=kestrel", "kind=rattled").out
    assert "dropped, out of the scene" in cli("do", "harm", "who=kestrel", "kind=bloodied").out
    assert "already dropped" in cli("do", "harm", "who=kestrel", "kind=rattled").out
    assert _sheet(cli, "kestrel")["harm"] == ["bloodied", "rattled", "desperate", "dropped"]
    cli("set", "kestrel", "spark=1")
    run = _json(cli, "do", "dropped", "who=kestrel", "spark=1")
    assert len(run["values"]["roll.dice"]) == 3 and _sheet(cli, "kestrel")["spark"] == 0
    direct = _json(cli, "do", "dropped", "who=wren")  # called directly: dropped goes on harm
    assert direct["outcome"] in ("perfect", "messy", "grim")
    assert "dropped" in _sheet(cli, "wren")["harm"]
    cli("do", "end-story", "who=wren", "end=retirement")
    assert _sheet(cli, "wren")["retiring"] is True
    assert _json(cli, "do", "dropped", "who=wren")["outcome"] == "perished"
    cli("campaign", "profile", "flavor=sword-and-sorcery")  # its own 1d, not deadly (p. 184)
    assert len(_json(cli, "do", "dropped", "who=kestrel")["values"]["roll.dice"]) == 1
    assert "urgent condition" not in cli("do", "harm", "who=wren", "kind=bloodied").out


def test_suspense_is_taken_spent_and_kept_by_challenges(cli: Cli) -> None:
    setup(cli, "suspense")
    assert "GM suspense: 0." in cli("do", "suspense").out
    assert "GM suspense: 3." in cli("do", "suspense", "take=3", "why=skipped moves").out
    refused = cli("do", "suspense", "spend=4")
    assert refused.code == 0 and "The GM has 3 suspense, not 4" in refused.out
    cli("track", "new", "Bandits", "--kind", "pool", "--size", "4")
    spent = cli("do", "suspense", "spend=1", "pool=bandits")
    assert "GM suspense: 2." in spent.out and "Bandits drops 1d anyway (3d left)" in spent.out
    assert _json(cli, "oracle", "show")["state"]["suspense"] == 2  # the story oracle keeps it
    challenge = '{"dice": 6, "name": "Stop the Ritual"}'
    made = cli("gen", "run", "grimwild-ce.challenge", "--auto", "--prefill", challenge)
    assert "suspense: 2" in made.out
    assert cli("gen", "commit", "g1").code == 0
    own = cli("do", "suspense", "spend=1", "challenge=stop-the-ritual")
    assert "Stop the Ritual's bonus suspense: 1" in own.out
    assert "GM suspense: 2." in cli("do", "suspense").out  # the GM's own is untouched
    built = cli("do", "suspense-move", "move=build-up")  # a suspense move takes suspense
    assert "GM suspense: 3." in built.out and "takes spark" in built.out
    assert "No suspense for it" in cli("do", "suspense-move", "move=foreshadow").out
    assert _json(cli, "oracle", "show")["state"]["suspense"] == 3


def test_supplies_come_up_as_days_pass(cli: Cli) -> None:
    setup(cli, "supplies")
    assert "supplies-day" not in cli("time", "advance", "1 day").out  # not without the option
    cli("campaign", "profile", "supplies=on")
    assert "roll each PC's supplies pool" in cli("time", "advance", "1 day").out
    assert "supplies-day" not in cli("time", "advance", "2 hours").out


def test_a_quarrel_goes_to_the_highest_die_and_everyone_takes_spark(cli: Cli) -> None:
    setup(cli, "quarrel")
    cli("new", "pc", "Ash")
    outcomes: set[str] = set()
    for _ in range(12):
        run = _json(cli, "do", "quarrel", "first=kestrel", "second=wren", "helps_first=ash")
        values = run["values"]
        best_a = max(max(values["side_a.dice"]), max(values["help_a.dice"]))
        best_b = max(values["side_b.dice"])
        expected = "first" if best_a > best_b else "second" if best_b > best_a else "tie"
        assert run["outcome"] == expected
        outcomes.add(run["outcome"])
        for pc in ("kestrel", "wren", "ash"):  # all who took part, the helper too
            assert _sheet(cli, pc)["spark"] >= 1
            cli("set", pc, "spark=0")
    assert {"first", "second"} <= outcomes


def test_vex_is_chosen_or_rolled(cli: Cli) -> None:
    setup(cli, "vex")
    assert "choose an immediate, instinctive response" in cli("do", "vex", "who=kestrel").out
    chosen = cli("do", "vex", "who=kestrel", "response=flight")
    assert "flight, running from the subject" in chosen.out
    cli("campaign", "profile", "flavor=grimdark")  # random vex, lasting marks (p. 182)
    rolled = _json(cli, "do", "vex", "who=kestrel")
    assert "the response is rolled (random vex)" in _text(rolled) and rolled["rolls"]
    cli("do", "mark", "who=kestrel", "stat=wits")
    run = _json(cli, "do", "action", "who=kestrel", "stat=wits")
    assert run["values"]["total_thorns"] == 1 and _sheet(cli, "kestrel")["marks"] == ["wits"]


def test_pools_push_to_0d_tick_and_roll_as_actions(cli: Cli) -> None:
    setup(cli, "pools")
    cli("track", "new", "Ogre", "--kind", "pool", "--linked", "1+1")
    first = cli("do", "push", "who=kestrel", "pool=ogre", "stat=brawn")
    assert "phase 2 of 2 begins at 1d" in first.out and "brawn" in _sheet(cli, "kestrel")["marks"]
    second = cli("do", "push", "who=kestrel", "pool=ogre", "stat=wits")
    assert "Ogre is empty" in second.out
    assert "already empty" in cli("do", "push", "who=kestrel", "pool=ogre", "stat=agility").out
    assert "tick-pools=on" in cli("do", "tick", "pool=ogre").out  # an option
    cli("track", "new", "Wand", "--kind", "pool", "--size", "8", "--pool", "power")
    cli("set", "kestrel", "spark=1")
    run = _json(cli, "do", "pool-action", "who=kestrel", "pool=wand", "spark=1")
    values = run["values"]
    faces, along = values["rolled.faces"], values["along.dice"]
    assert len(faces) == 8 and len(along) == 1  # the spark die rolls along
    assert values["rolled.left"] == 8 - sum(1 for f in faces if f <= 3)  # it never drops
    assert values["highest"] == max(faces + along)
    assert _json(cli, "show", "wand")["fields"]["value"]["value"] == values["rolled.left"]


def test_a_faction_turn_rolls_its_pools(cli: Cli) -> None:
    setup(cli, "factions")
    made = cli(
        "gen", "run", "grimwild-ce.faction", "--auto", "--prefill",
        '{"name": "The Oldgrove Druids", "goal_1": "Quiet the horrors", "pool_1": 4,'
        ' "goal_2": "Parley with Shaz", "pool_2": 4}',
    )  # fmt: skip
    assert made.code == 0, made.err
    cli("gen", "commit", "g1")
    druids = _json(cli, "show", "the-oldgrove-druids")["fields"]
    assert druids["pool_1"] == "track:quiet-the-horrors"
    before = _json(cli, "show", "quiet-the-horrors")["fields"]["value"]["value"]
    turn = cli("faction", "turn")
    assert "pool Quiet the horrors" in turn.out and "pool Parley with Shaz" in turn.out
    assert _json(cli, "show", "quiet-the-horrors")["fields"]["value"]["value"] <= before
    for _ in range(8):
        turn = cli("faction", "turn")
        if "goal comes to pass" in turn.out:
            break
    assert "goal comes to pass" in turn.out and "Read the story roll from" in turn.out
    goal = cli("do", "faction-goal", "who=the-oldgrove-druids", "pool=parley-with-shaz")
    assert "Parley with Shaz is empty" in goal.out or "goal comes to pass" in goal.out


def test_sessions_bring_pre_session_and_experience(cli: Cli) -> None:
    setup(cli, "sessions")
    cli("set", "kestrel", "talents+=bard-bardic-lore", "talents+=druid-augury", "thread=0")
    started = cli("session", "start")
    assert "pre-session" not in started.out  # not before the first
    ended = cli("session", "end", "--summary", "One.")
    assert "session-experience (Kestrel)" in ended.out and _sheet(cli, "kestrel")["xp"] == 1
    again = cli("session", "start")
    assert "pre-session-each (Kestrel)" in again.out and "pre-session-gm" in again.out
    kestrel = _sheet(cli, "kestrel")
    assert kestrel["thread"] == 3 and kestrel["spark"] == 1  # Bardic Lore: 1 extra thread
    assert len(kestrel["omens"]) == 2  # Augury: 2d rolled before each session
    assert "GM suspense: 1." in again.out  # the GM takes suspense at pre-session, by itself
    cli("session", "end", "--summary", "Two.")
    cli("campaign", "profile", "rest-resets=on")
    third = cli("session", "start")
    assert "pre-session-each" not in third.out  # rests bring them instead
    assert "GM suspense: 2." in third.out
    rested = cli("do", "rest", "who=wren")
    assert "Rest resets (an option): Wren takes spark" in rested.out
    assert "GM suspense: 4." in rested.out  # 2 for the party's reset
    again_rested = cli("do", "rest", "who=kestrel")  # the same reset: once for the party
    assert "took this reset's 2 suspense already" in again_rested.out
    cli("do", "harm", "who=wren", "kind=bloodied")
    cli("do", "harm", "who=wren", "kind=bloodied")
    assert "heals 1 harm: desperate" in cli("do", "reset", "who=wren", "heal=desperate").out
    assert _sheet(cli, "wren")["harm"] == ["bloodied"]
    cli("scene", "new", "The next morning")  # a new scene: the next reset is a new one
    assert "GM suspense: 6." in cli("do", "reset", "who=kestrel").out


def test_cozy_bonds_and_arcs_earn_xp_at_the_session_end(cli: Cli) -> None:
    setup(cli, "cozy")
    cli("campaign", "profile", "flavor=cozy")
    cli("set", "kestrel", "bonds+=playful rivalry with Wren")
    changed = cli(
        "do", "change-bond", "who=kestrel", "toward=wren", "bond=growing respect",
        "old=playful rivalry with Wren",
    )  # fmt: skip
    assert "Wren has 1 spark" in changed.out
    assert _sheet(cli, "kestrel")["bonds"] == ["growing respect with Wren"]
    cli("session", "start")
    ended = cli("session", "end", "--summary", "Tea.")
    assert "changing a bond or completing a story arc" in ended.out
    kestrel, wren = _sheet(cli, "kestrel"), _sheet(cli, "wren")
    assert (kestrel["xp"], kestrel["grew"], wren["xp"]) == (2, False, 1)
    refused = cli("do", "experience", "who=wren", "why=carousing")  # sword & sorcery's
    assert "Carousing earns XP in sword & sorcery" in refused.out


def test_downtime_and_carousing(cli: Cli) -> None:
    setup(cli, "downtime")
    cli("do", "harm", "who=kestrel", "kind=bloodied")
    healed = cli("do", "downtime", "who=kestrel")
    assert "fully heals" in healed.out and "`didact faction turn`" in healed.out
    assert not _sheet(cli, "kestrel")["harm"]
    cli("campaign", "profile", "expanded-downtime=on")
    assert "pick a downtime action" in cli("do", "downtime", "who=kestrel").out
    cli("track", "new", "Retrain", "--kind", "pool", "--size", "2")
    done = cli("do", "downtime", "who=kestrel", "act=pursue", "goal=retrain", "also=unwind")
    assert "works on Retrain" in done.out and _sheet(cli, "kestrel")["spark"] == 1
    assert "replaces carousing" in cli("do", "carouse", "who=kestrel").out
    cli("campaign", "profile", "expanded-downtime=off", "flavor=sword-and-sorcery", "wealth=on")
    cli("track", "new", "Coins", "--kind", "pool", "--size", "4", "--pool", "power")
    caroused = cli("do", "carouse", "who=wren", "coins=coins")
    assert "Coins grows: 6d of 6d" in caroused.out and "carousing earns Wren +1 XP" in caroused.out


def test_side_characters_are_streamlined(cli: Cli) -> None:
    setup(cli, "side")
    cli("campaign", "profile", "solo=on")
    made = _json(
        cli, "char", "new", "grimwild-ce.side-character", "--mode", "random", "--prefill",
        '{"name": "Pip"}',
    )["draft"]  # fmt: skip
    fields = made["entities"][0]["fields"]
    assert fields["side"] is True and "path" not in fields and len(fields["talents"]) == 1
    assert len(fields["traits"]) == 2 and "wises" not in fields
    assert cli("char", "commit", made["id"]).code == 0
    assert "harm instead" in cli("do", "mark", "who=pip", "stat=brawn").out
    assert _sheet(cli, "pip")["harm"] == ["bloodied"] and not _sheet(cli, "pip").get("marks")
    assert "no spark or thread" in cli("do", "take-spark", "who=pip").out
    cli("session", "start")
    ended = cli("session", "end", "--summary", "Alone.")
    assert "(Pip)" not in ended.out and "(Kestrel)" in ended.out
    refused = cli("char", "advance", "pip")
    assert refused.code == 1 and "side characters don't add XP or advance" in refused.err


def test_exploration_tokens(cli: Cli) -> None:
    setup(cli, "tokens")
    assert "exploration tokens: 3" in cli("do", "tokens", "who=kestrel", "take=3").out
    assert "tokens: 1" in cli("do", "tokens", "who=kestrel", "spend=2", "buys=a point").out
    short = cli("do", "tokens", "who=kestrel", "spend=2")
    assert "Not enough exploration tokens: Kestrel has 1, not 2" in short.out
    cli("do", "tokens", "who=kestrel", "thread")
    assert _sheet(cli, "kestrel")["thread"] == 1
    assert "unspent tokens disappear" in cli("do", "tokens", "who=kestrel", "clear").out
    assert _sheet(cli, "kestrel")["tokens"] == 0
