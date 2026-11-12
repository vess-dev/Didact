"""Faction turns: the world moves on its own between (or during) sessions.

Each faction (a `faction` record that isn't archived or `status: gone`) takes a turn:
- if the system pack names a rule (`settings.factions.turn: faction-turn`), that rule runs with
  `who` = the faction;
- otherwise it rolls `settings.factions.roll` (default `d6`, logged). At `advance_on` or more
  (default 4) each of its clocks (`didact track new … --for faction:x`) ticks once.

The result says who moved and what filled; the LLM narrates the moves from each faction's
agenda and obstacle.
"""

from dataclasses import dataclass, field
from typing import cast

from didact.core.errors import DidactError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.rules.engine import Engine
from didact.services import dice, packs, rules, sheets, trackers
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Repo

GONE = frozenset({"gone", "destroyed", "disbanded"})


@dataclass(slots=True)
class Move:
    faction: Entity
    lines: list[str] = field(default_factory=list)
    advanced: bool = False
    filled: list[str] = field(default_factory=list)


def settings(repo: Repo) -> dict[str, JSON]:
    system = sheets.active_system(repo)
    if not system:
        return {}
    try:
        raw = packs.active(repo).settings(system).get("factions")
    except DidactError:
        return {}
    return raw if isinstance(raw, dict) else {}


def active(repo: Repo, *, gm: bool) -> tuple[list[Entity], int]:
    """The factions that act, and how many secret ones were left out."""
    found: list[Entity] = []
    hidden = 0
    for row in repo.index().rows(repo.chain(), types=["faction"]):
        if row.status in GONE:
            continue
        if row.knowledge == "secret" and not gm:
            hidden += 1
            continue
        found.append(repo.located(row).entity)
    return found, hidden


def turn(
    repo: Repo, cs: Changeset, factions: list[Entity], *, dry: bool, command: str | None
) -> list[Move]:
    config = settings(repo)
    rule_ref = config.get("turn")
    moves: list[Move] = []
    for faction in factions:
        move = Move(faction)
        if isinstance(rule_ref, str):
            _by_rule(repo, cs, rule_ref, move, dry=dry, command=command)
        else:
            _by_roll(repo, cs, config, move, dry=dry, command=command)
        moves.append(move)
    return moves


def _by_rule(
    repo: Repo, cs: Changeset, ref: str, move: Move, *, dry: bool, command: str | None
) -> None:
    active = packs.active(repo)
    rule = rules.find_rule(active, ref)
    args = {"who": str(move.faction.id)} if "who" in rule.params else {}
    result = Engine(rules.LibraryHost(repo, cs, active, dry, command)).run(rule, args)
    move.lines = list(result.lines)  # its prompts and reminders are among them
    move.advanced = result.changed


def _by_roll(
    repo: Repo,
    cs: Changeset,
    config: dict[str, JSON],
    move: Move,
    *,
    dry: bool,
    command: str | None,
) -> None:
    expression = str(config.get("roll") or "d6")
    threshold = config.get("advance_on", 4)
    rolled = dice.roll(
        repo,
        expression,
        as_record=str(move.faction.id),
        reason=f"faction turn: {move.faction.name}",
        command=command,
        dry=dry,
    )
    value = rolled.rolled.result.value
    move.advanced = isinstance(value, int | float) and value >= cast(float, threshold)
    move.lines.append(rolled.line)
    if not move.advanced:
        move.lines.append(_("holds: no progress this turn"))
        return
    clocks = trackers.owned(repo, str(move.faction.id))
    if not clocks:
        move.lines.append(_("advances (no clock yet: `didact track new '<plan>' --for …`)"))
        return
    for clock in clocks:
        entity, note = trackers.tick(cs, str(clock.id), "+=", 1)
        move.lines.append(_("advances: {clock}", clock=trackers.show(entity)))
        if note:
            move.filled.append(entity.name)


def prompt(move: Move) -> str:
    agenda = move.faction.fields.get("agenda")
    obstacle = move.faction.fields.get("obstacle")
    name = move.faction.name
    if agenda and obstacle:
        return _(
            "narrate what {name} did (agenda: {agenda} · obstacle: {obstacle})",
            name=name,
            agenda=agenda,
            obstacle=obstacle,
        )
    if agenda:
        return _("narrate what {name} did (agenda: {agenda})", name=name, agenda=agenda)
    if obstacle:
        return _("narrate what {name} did (obstacle: {obstacle})", name=name, obstacle=obstacle)
    return _("narrate what {name} did", name=name)
