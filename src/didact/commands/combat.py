"""Combat: start, join, leave, next, status, hit, condition, end."""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Annotated, Literal, cast

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core import labels
from didact.core.context import Context
from didact.core.errors import DidactError, InvalidError, NotFoundError, UsageError
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON, Out, code
from didact.core.phrases import counted
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Repo

if TYPE_CHECKING:
    from didact.services.combat import Fight, Fighter


def _settings(repo: object) -> dict[str, JSON]:
    from didact.services import packs, sheets
    from didact.store.repo import Repo

    assert isinstance(repo, Repo)
    system = sheets.active_system(repo)
    if not system:
        return {}
    try:
        raw = packs.active(repo).settings(system).get("combat")
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _stats(repo: object, refs: list[str], *, gm: bool = True) -> dict[str, str]:
    """Each fighter's numbers; a player view leaves their secret ones out."""
    from didact.services import knowledge, sheets
    from didact.store.repo import Repo

    assert isinstance(repo, Repo)
    hid = knowledge.NOTHING if gm else knowledge.unknown(repo)
    found: dict[str, str] = {}
    for ref in refs:
        try:
            entity = repo.resolve(ref).entity
        except DidactError:
            continue
        sh = sheets.sheet(repo, entity.type)
        shown = entity if gm else knowledge.player_copy(entity, sh, hid)[0]
        found[ref] = sheets.stat_line(shown, sh)
    return found


def _fighter(repo: Repo, token: str) -> tuple[Entity, str]:
    """`troll`, `npc:troll`, `troll:foes` or `npc:troll:foes` → (record, side)."""
    try:
        return repo.resolve(token).entity, ""
    except NotFoundError:
        record, sep, side = token.rpartition(":")
        if not sep or not record:
            raise
        return repo.resolve(record).entity, side


def _recruits(repo: Repo, tokens: Sequence[str], roster: list[Fighter]) -> list[Fighter]:
    """Fighters from `record` or `record:side` tokens, skipping any already on the roster:
    PCs and party members join the party side, everyone else the foes."""
    from didact.services import combat
    from didact.services import party as parties

    members = {str(m.entity.id) for m in parties.members(repo)}
    found: list[Fighter] = []
    for token in tokens:
        entity, side = _fighter(repo, token)
        if any(f.ref == str(entity.id) for f in [*roster, *found]):
            continue
        in_party = entity.type == "pc" or str(entity.id) in members
        found.append(
            combat.Fighter(str(entity.id), entity.name, side or ("party" if in_party else "foes"))
        )
    return found


def _initiative(
    ctx: Context, repo: Repo, settings: dict[str, JSON], fighters: list[Fighter]
) -> tuple[dict[str, float], list[str]]:
    """Each fighter rolls the pack's initiative (default d20), logged: (ref → value, roll lines)."""
    from didact.services import dice

    expression = str(settings.get("initiative") or "d20")
    initiative: dict[str, float] = {}
    lines: list[str] = []
    for fighter in fighters:
        rolled = dice.roll(
            repo,
            expression,
            as_record=fighter.ref,
            reason=f"initiative: {fighter.name}",
            command=ctx.command_line,
            dry=ctx.dry_run,
        )
        value = rolled.rolled.result.value
        initiative[fighter.ref] = float(value) if isinstance(value, int | float) else 0
        lines.append(rolled.line)
    return initiative, lines


def _no_fight() -> InvalidError:
    return InvalidError(_("no fight is on"), hint=_("`didact combat start …`"))


def _fire(ctx: Context, cs: Changeset, event: str, fight: Fight) -> list[str]:
    """Run the packs' `on: <event>` triggers inside this changeset, reading the fight that
    starts or ends (`@combat.round`, `@combat.fighters`); notes for the output."""
    from didact.services import combat, events

    preset = combat.values(fight)
    ran = events.fire(cs.repo, cs, event, preset, dry=ctx.dry_run, command=ctx.command_line)
    return [_("trigger {trigger}", trigger=line) for line in ran]


@command(
    "combat start",
    summary="Start a fight: who's in it (name or name:side), and the initiative mode",
    writes=True,
    examples=(
        "didact combat start freya troll wolf-1",
        "didact combat start freya bandit:foes merchant:bystanders --mode individual",
        "didact combat start --party troll wolf",
    ),
    description=(
        "Fighters are records; PCs join the party side and others the foes unless you say\n"
        "name:side. Modes: sides (alternate; the pack says who's first), individual (everyone\n"
        "rolls initiative, logged) or popcorn (whoever acted picks who's next). The default mode\n"
        "comes from the system pack's `settings.combat`."
    ),
)
def combat_start(
    ctx: Context,
    *fighters: Annotated[str, "fighters: a record, or record:side", Metavar("fighter")],
    mode: Annotated[Literal["individual", "sides", "popcorn"] | None, "initiative style"] = None,
    first: Annotated[str | None, "sides mode: the side that acts first", Metavar("side")] = None,
    party: Annotated[bool, "bring the whole party (PCs, companions, hirelings)"] = False,
) -> Out:
    from didact.services import combat
    from didact.services import party as parties

    repo = open_repo(ctx)
    settings = _settings(repo)
    chosen = mode or cast(
        combat.Mode, settings.get("mode") if settings.get("mode") in combat.MODES else "sides"
    )
    roster: list[combat.Fighter] = []
    if party:
        roster += [
            combat.Fighter(str(m.entity.id), m.entity.name, "party") for m in parties.members(repo)
        ]
    roster += _recruits(repo, fighters, roster)
    initiative: dict[str, float] = {}
    notes: list[str] = []
    if chosen == "individual":
        initiative, notes = _initiative(ctx, repo, settings, roster)
    fight = combat.start(
        repo, roster, chosen, first or cast(str | None, settings.get("first")), initiative
    )
    cs = changeset(
        ctx,
        repo,
        N_("combat starts: {fighters}"),
        fighters=", ".join(f.name for f in roster),
    )
    combat.save(cs, fight)
    round_one = settings.get("round_one")
    if isinstance(round_one, str):
        notes.append(_("round one: {text}", text=round_one))
    notes += _fire(ctx, cs, "combat_start", fight)
    out = finish(ctx, cs, done=_("the fight is on"), extra={"combat": fight.to_data()}, notes=notes)
    lines = [out.md, *combat.lines(fight, _stats(repo, [f.ref for f in fight.order]))]
    return Out(data=out.data, md="\n".join(lines), ok=out.ok)


@command(
    "combat join",
    summary="Fighters join the fight under way (name or name:side); individual mode rolls them in",
    writes=True,
    examples=(
        "didact combat join wolf-2 wolf-3",
        "didact combat join gannet:party",
    ),
    description=(
        "Sides as at `combat start`: PCs and party members join the party, others the foes,\n"
        "unless you say name:side. In individual mode each newcomer rolls initiative (logged)\n"
        "and takes their place in the order: one who rolled higher than whoever is acting now\n"
        "waits for the next round. In sides and popcorn modes they join at the end."
    ),
)
def combat_join(
    ctx: Context,
    *fighters: Annotated[str, "fighters: a record, or record:side", Metavar("fighter")],
) -> Out:
    from didact.services import combat

    if not fighters:
        raise UsageError(_("who joins the fight?"), hint=_("e.g. `didact combat join wolf-2`"))
    repo = open_repo(ctx)
    fight = combat.load(repo)
    if fight is None:
        raise _no_fight()
    newcomers = _recruits(repo, fighters, [])
    combat.refuse_doubles(fight, newcomers)  # before any initiative is rolled
    initiative: dict[str, float] = {}
    notes: list[str] = []
    if fight.mode == "individual":
        initiative, notes = _initiative(ctx, repo, _settings(repo), newcomers)
    combat.join(fight, newcomers, initiative)
    names = ", ".join(f"{f.name} ({f.side})" for f in newcomers)
    joins = counted(
        "{names} joins the fight", "{names} join the fight", len(newcomers), names=names
    )
    cs = changeset(ctx, repo, N_("combat: {joins}"), joins=joins)
    combat.save(cs, fight)
    extra: dict[str, JSON] = {"combat": fight.to_data(), "joined": [f.ref for f in newcomers]}
    done = ngettext(
        "{names} joins the fight", "{names} join the fight", len(newcomers), names=names
    )
    out = finish(ctx, cs, done=done, extra=extra, notes=notes)
    lines = [out.md, *combat.lines(fight, _stats(repo, [f.ref for f in fight.order]))]
    return Out(data=out.data, md="\n".join(lines), ok=out.ok)


@command(
    "combat leave",
    summary="A fighter leaves the fight (died, fled, surrendered); their conditions go too",
    writes=True,
    examples=(
        "didact combat leave troll --why fled",
        "didact combat leave wolf-2 --why died",
    ),
    description=(
        "Nobody's turn is skipped: if it was theirs, the next one is up. When only one side\n"
        "is left, end the fight with `didact combat end`."
    ),
)
def combat_leave(
    ctx: Context,
    fighter: Annotated[str, "the fighter", Metavar("fighter")],
    *,
    why: Annotated[str | None, "why: died, fled, surrendered, …", Metavar("text")] = None,
) -> Out:
    from didact.services import combat

    repo = open_repo(ctx)
    fight = combat.load(repo)
    if fight is None:
        raise _no_fight()
    found = combat.named(fight, fighter)
    if found is None:
        try:
            ref = str(repo.resolve(fighter).entity.id)
        except DidactError:
            ref = None
        found = next((f for f in fight.order if f.ref == ref), None)
    if found is None:
        inside = ", ".join(f"{f.name} ({f.ref})" for f in fight.order) or _("nobody")
        raise NotFoundError(
            _("{fighter} isn't in the fight", fighter=fighter),
            hint=_("in it: {inside}", inside=inside),
        )
    notes = combat.leave(fight, found.ref)
    cs = (
        changeset(ctx, repo, N_("combat: {name} leaves ({why})"), name=found.name, why=why)
        if why
        else changeset(ctx, repo, N_("combat: {name} leaves"), name=found.name)
    )
    combat.save(cs, fight)
    if why:
        done = _(
            "{name} leaves the fight ({why}); now: {current} (round {round})",
            name=found.name,
            why=why,
            current=fight.current,
            round=fight.round,
        )
    else:
        done = _(
            "{name} leaves the fight; now: {current} (round {round})",
            name=found.name,
            current=fight.current,
            round=fight.round,
        )
    extra: dict[str, JSON] = {"combat": fight.to_data(), "left": found.ref, "why": why}
    return finish(ctx, cs, done=done, extra=extra, notes=notes)


@command(
    "combat next",
    summary="Next turn (conditions tick down each round); popcorn: --to picks who's next",
    writes=True,
    examples=("didact combat next", "didact combat next --to troll"),
)
def combat_next(
    ctx: Context, *, to: Annotated[str | None, "popcorn: who goes next", Metavar("fighter")] = None
) -> Out:
    from didact.services import combat

    repo = open_repo(ctx)
    fight = combat.load(repo)
    if fight is None:
        raise _no_fight()
    notes = combat.advance(fight, to.casefold() if to else None)
    cs = changeset(
        ctx,
        repo,
        N_("combat: round {round}, {current}"),
        round=fight.round,
        current=fight.current,
    )
    combat.save(cs, fight)
    done = _("now: {current} (round {round})", current=fight.current, round=fight.round)
    return finish(ctx, cs, done=done, extra={"combat": fight.to_data()}, notes=notes)


@command(
    "combat status",
    summary="The fight: round, whose turn, fighters and conditions (--gm: where, doing, plan)",
    examples=("didact combat status", "didact combat status --gm"),
    description=(
        "--gm adds each fighter's `where`, `doing` and `plan` details: keep them current\n"
        "with `didact about <fighter> where='…' doing='…' plan='…'` as the fight moves.\n"
        "Fighters come and go: `didact combat join <fighter>` brings one in, and\n"
        "`didact combat leave <fighter> --why fled` takes one out."
    ),
)
def combat_status(
    ctx: Context,
    *,
    gm: Annotated[bool, "each fighter's where, doing and plan (GM eyes only)"] = False,
) -> Out:
    from didact.services import combat, details

    repo = open_repo(ctx)
    fight = combat.load(repo)
    if fight is None:
        return Out(data={"combat": None}, md=_("no fight is on"))
    data: dict[str, JSON] = {"combat": fight.to_data()}
    notes: dict[str, str] = {}
    if gm:
        noted: dict[str, JSON] = {}
        for fighter in fight.order:
            try:
                entity = repo.resolve(fighter.ref).entity
            except DidactError:
                continue
            found = {k: entity.details[k] for k in details.IN_SCENE if k in entity.details}
            if found:
                noted[fighter.ref] = dict[str, JSON](found)
                notes[fighter.ref] = " · ".join(
                    f"{labels.inline(k, labels.detail_name(k))}: {v}" for k, v in found.items()
                )
        data["details"] = noted
    stats = _stats(repo, [f.ref for f in fight.order], gm=gm)
    return Out(data=data, md="\n".join(combat.lines(fight, stats, notes)))


@command(
    "combat condition",
    summary="Put a condition on a fighter, for some rounds or until removed",
    writes=True,
    examples=(
        "didact combat condition troll stunned --rounds 1",
        "didact combat condition freya prone --remove",
    ),
)
def combat_condition(
    ctx: Context,
    fighter: Annotated[str, "the fighter", Metavar("fighter")],
    name: Annotated[str, "the condition", Metavar("condition")],
    *,
    rounds: Annotated[int | None, "how many rounds (default: until removed)", Metavar("n")] = None,
    remove: Annotated[bool, "take it off"] = False,
) -> Out:
    from didact.services import combat

    repo = open_repo(ctx)
    fight = combat.load(repo)
    if fight is None:
        raise _no_fight()
    ref = str(repo.resolve(fighter).entity.id)
    if remove:
        fight.conditions = [c for c in fight.conditions if not (c.ref == ref and c.name == name)]
    else:
        fight.conditions.append(combat.Condition(ref, name, rounds))
    said = N_("combat: {name} off {ref}") if remove else N_("combat: {name} on {ref}")
    cs = changeset(ctx, repo, said, name=name, ref=ref)
    combat.save(cs, fight)
    if remove:
        done = _("{name} off: {ref}", name=name, ref=ref)
    elif rounds:
        done = ngettext(
            "{name} on for {n} round: {ref}",
            "{name} on for {n} rounds: {ref}",
            rounds,
            name=name,
            ref=ref,
        )
    else:
        done = _("{name} on: {ref}", name=name, ref=ref)
    return finish(ctx, cs, done=done)


@command(
    "combat hit",
    summary="An attack: runs the system's attack rule (damage, armor, what follows)",
    writes=True,
    examples=("didact combat hit freya troll weapon=d8",),
)
def combat_hit(
    ctx: Context,
    attacker: Annotated[str, "who attacks", Metavar("attacker")],
    target: Annotated[str, "who's hit", Metavar("target")],
    *extra: Annotated[
        str, "more parameters for the attack rule: name=value", Metavar("name=value")
    ],
) -> Out:
    from didact.commands.rules import do

    repo = open_repo(ctx)
    rule = _settings(repo).get("attack")
    if not isinstance(rule, str):
        raise InvalidError(
            _("this system names no attack rule"),
            hint=_(
                "run it yourself ({command}) or set settings.combat.attack",
                command=code("didact do <attack> …"),
            ),
        )
    return do(ctx, rule, f"attacker={attacker}", f"target={target}", *extra)


@command("combat end", summary="End the fight", writes=True, examples=("didact combat end",))
def combat_end(ctx: Context) -> Out:
    from didact.services import combat

    repo = open_repo(ctx)
    fight = combat.load(repo)
    if fight is None:
        return Out(data={"combat": None}, md=_("no fight was on"))
    ended = counted("combat ends after {n} round", "combat ends after {n} rounds", fight.round)
    cs = changeset(ctx, repo, ended)
    combat.save(cs, None)
    notes = _fire(ctx, cs, "combat_end", fight)
    done = ngettext(
        "the fight ends after {n} round", "the fight ends after {n} rounds", fight.round
    )
    return finish(ctx, cs, done=done, notes=notes)
