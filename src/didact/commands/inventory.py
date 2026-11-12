"""Inventory: show, add, drop, move, use and recharge items in a sheet's slots."""

from typing import TYPE_CHECKING, Annotated

from didact.commands._common import changeset, finish, open_repo, parse_data
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.errors import InvalidError, NotFoundError
from didact.core.i18n import N_, _
from didact.core.output import JSON, Out
from didact.core.phrases import Phrase, phrase, translated
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Located, Repo

if TYPE_CHECKING:
    from didact.services.inventory import Change
    from didact.services.sheets import Strictness


def _mode(ctx: Context, repo: Repo, force: bool) -> Strictness:
    from didact.services import sheets

    sheets.check_force(force, ctx.reason)
    return "freeform" if force else sheets.strictness(repo)


def _room(cs: Changeset, located: Located) -> str:
    """`6/10 slots · backpack 4/6 · body 2/4`, as it will be once the changes apply."""
    from didact.services import inventory, records, sheets

    entity = records.planned(cs, located.path)
    sh = sheets.sheet(cs.repo, entity.type)
    return inventory.room(entity, sh, inventory.find_bag(entity, sh)).line()


def _finish(
    ctx: Context, cs: Changeset, done: str, changes: list[Change], extra: dict[str, JSON]
) -> Out:
    """Run the triggers hooks fired, then apply (or preview) the changeset."""
    from didact.services import rules

    notes: list[str] = []
    for change in changes:
        notes.extend(change.notes)
        notes.extend(
            rules.run_hooks(
                cs.repo, cs, change.record, change.fired, dry=ctx.dry_run, command=ctx.command_line
            )
        )
    if cs.is_empty():  # e.g. a usage die that held: nothing to write, but something happened
        lines = [_("✔ {done}", done=done), *(_("note: {note}", note=n) for n in notes)]
        return Out(data={**extra, "changed": False}, md="\n".join(lines))
    return finish(ctx, cs, done=done, extra=extra, notes=notes)


@command(
    "inv show",
    summary="What a character carries: items, slots used and free, groups",
    examples=("didact inv show freya", "didact inv show tom --gm"),
)
def inv_show(
    ctx: Context,
    who: Annotated[str, "whose inventory", Metavar("record")],
    *,
    gm: Annotated[bool, "secret items too"] = False,
) -> Out:
    from didact.services import inventory, knowledge, sheets

    repo = open_repo(ctx)
    entity = repo.resolve(who).entity
    if not knowledge.visible(entity.knowledge, gm):
        return Out(
            data={"id": str(entity.id), "hidden": True},
            md=_("{id} is secret: `didact inv show {id} --gm` shows it", id=str(entity.id)),
        )
    sh = sheets.sheet(repo, entity.type)
    if not gm:  # what the players know: no secret items, no secret fields
        entity = knowledge.player_copy(entity, sh, knowledge.unknown(repo))[0]
    return Out(data=inventory.summary(entity, sh), md="\n".join(inventory.lines(entity, sh)))


@command(
    "inv add",
    summary="Give a character items: by name, from the compendium, or an item record",
    writes=True,
    examples=(
        "didact inv add freya Rope 'Iron Spikes'",
        "didact inv add freya Longsword      # size and damage from the compendium",
        "didact inv add freya Torch --count 2 --uses 3",
        "didact inv add freya Lantern --uses d8 --to backpack",
        "didact inv add freya 'Silver Moss' --size petty --data '{\"magic\": true}'",
    ),
    description=(
        "A name that matches a compendium item, or an `item:` record, brings its details:\n"
        "size, damage, armor, uses. The options apply to every item named. Going past the\n"
        "slots is refused (strict), warned about (lenient) or allowed with --force; filling\n"
        "them fires the sheet's `when_full` hook (HP dropping to 0, say)."
    ),
)
def inv_add(
    ctx: Context,
    who: Annotated[str, "who gets it", Metavar("record")],
    *items: Annotated[str, "item names (or item:<id> records)", Metavar("item")],
    size: Annotated[str | None, "petty, normal, bulky, or a number of slots"] = None,
    count: Annotated[int | None, "how many (they stack)", Metavar("n")] = None,
    uses: Annotated[
        str | None, "uses or charges (3), or a usage die (d8)", Metavar("n|die")
    ] = None,
    to: Annotated[str | None, "the slot group, e.g. backpack", Metavar("group")] = None,
    data: Annotated[str | None, "more details as JSON, e.g. '{\"armor\": 1}'"] = None,
    force: Annotated[bool, "allow going past the slots (needs --reason)"] = False,
) -> Out:
    from didact.services import inventory

    if not items:
        raise InvalidError(_("name an item"), hint=_("e.g. `didact inv add freya Rope`"))
    repo = open_repo(ctx)
    mode = _mode(ctx, repo, force)
    located = repo.resolve(who)
    details = parse_data(data) or {}
    found: list[dict[str, JSON]] = []
    sources: list[str] = []
    for name in items:
        item, source = inventory.item_data(repo, name)
        item |= details
        if size is not None:
            item["size"] = int(size) if size.isdigit() else size
        if count is not None:
            item["count"] = count
        if uses is not None:
            item["uses"] = inventory.uses_value(uses)
        if source:
            sources.append(_("{item}: details from {source}", item=item["name"], source=source))
        found.append(item)
    named = ", ".join(str(item["name"]) for item in found)  # as they're kept, not as typed
    cs = changeset(ctx, repo, N_("{who} gets {items}"), who=located.entity.name, items=named)
    cs.forced = force
    changes: list[Change] = [
        inventory.add(cs, located, item, group=to, mode=mode, force=force) for item in found
    ]
    if changes:
        changes[0].notes[:0] = sources
    done = _(
        "{who} gets {items} ({room})",
        who=located.entity.name,
        items=named,
        room=_room(cs, located),
    )
    extra: dict[str, JSON] = {"id": str(located.entity.id), "items": [c.item for c in changes]}
    return _finish(ctx, cs, done, changes, extra)


@command(
    "inv drop",
    summary="Take items out of an inventory (all of a stack, or --count of it)",
    writes=True,
    examples=("didact inv drop freya rope", "didact inv drop freya torch --count 1"),
)
def inv_drop(
    ctx: Context,
    who: Annotated[str, "whose item", Metavar("record")],
    item: Annotated[str, "the item (a unique part of its name will do)", Metavar("item")],
    *,
    count: Annotated[int | None, "how many of a stack", Metavar("n")] = None,
) -> Out:
    from didact.services import inventory

    repo = open_repo(ctx)
    located = repo.resolve(who)
    cs = changeset(ctx, repo, N_("{who} drops {item}"), who=located.entity.name, item=item)
    change = inventory.remove(cs, located, item, count, mode=_mode(ctx, repo, False))
    gone = inventory.name_of(change.item)
    shown = gone + (f" ×{inventory.count_of(change.item)}" if count else "")
    done = _(
        "{who} drops {item} ({room})",
        who=located.entity.name,
        item=shown,
        room=_room(cs, located),
    )
    return _finish(ctx, cs, done, [change], {"id": change.record, "item": change.item})


@command(
    "inv move",
    summary="Hand an item to someone else, or move it to another slot group",
    writes=True,
    examples=(
        "didact inv move freya rope sweeney",
        "didact inv move freya torch pc:ansel --count 1",
        "didact inv move freya lantern body       # a slot group",
    ),
)
def inv_move(
    ctx: Context,
    who: Annotated[str, "who has it now", Metavar("record")],
    item: Annotated[str, "the item", Metavar("item")],
    to: Annotated[str, "who gets it, or a slot group of the same sheet", Metavar("to")],
    *,
    count: Annotated[int | None, "how many of a stack", Metavar("n")] = None,
    force: Annotated[bool, "allow going past the slots (needs --reason)"] = False,
) -> Out:
    from didact.services import inventory, sheets

    repo = open_repo(ctx)
    mode = _mode(ctx, repo, force)
    located = repo.resolve(who)
    sh = sheets.sheet(repo, located.entity.type)
    if to in inventory.find_bag(located.entity, sh).groups:
        cs = changeset(
            ctx, repo, N_("{who}: {item} → {to}"), who=located.entity.name, item=item, to=to
        )
        cs.forced = force
        change = inventory.regroup(cs, located, item, to, mode=mode, force=force)
        name = inventory.name_of(change.item)
        done = _(
            "{who}: {item} → {group} ({room})",
            who=located.entity.name,
            item=name,
            group=to,
            room=_room(cs, located),
        )
        return _finish(ctx, cs, done, [change], {"id": change.record, "group": to})
    try:
        target = repo.resolve(to)
    except NotFoundError:
        groups = ", ".join(inventory.find_bag(located.entity, sh).groups) or _("none on this sheet")
        raise NotFoundError(
            _("{to} is neither a record nor a slot group", to=repr(to)),
            hint=_("name who gets it (a record), or a group ({groups})", groups=groups),
        ) from None
    if target.path == located.path:
        raise InvalidError(
            _("{who} already has it", who=located.entity.name), hint=_("name someone else")
        )
    cs = changeset(ctx, repo, _moved(located.entity, target.entity, item))
    cs.forced = force
    taken = inventory.remove(cs, located, item, count, mode=mode)
    moved = taken.item if isinstance(taken.item, dict) else {"name": str(taken.item)}
    given = inventory.add(cs, target, dict(moved), mode=mode, force=force)
    name = inventory.name_of(taken.item)
    _log_move(repo, cs, name, dict[str, JSON](moved), located.entity, target.entity)
    done = f"{translated(_moved(located.entity, target.entity, name))} ({_room(cs, target)})"
    extra: dict[str, JSON] = {"from": taken.record, "to": given.record, "item": taken.item}
    return _finish(ctx, cs, done, [taken, given], extra)


def _moved(giver: Entity, taker: Entity, name: str) -> Phrase:
    """`Freya gives Rope to Sweeney`, `leaves Sword at The Ford`, `puts Sword in Chest`, and
    `Freya takes Sword from Chest`: the event log's summary, and what's shown."""
    from didact.services import details

    values: dict[str, JSON] = {"giver": giver.name, "taker": taker.name, "item": name}
    people = details.PEOPLE_TYPES
    if taker.type in people:
        if giver.type not in people:
            return phrase(N_("{taker} takes {item} from {giver}"), **values)
        return phrase(N_("{giver} gives {item} to {taker}"), **values)
    if taker.type in details.PLACE_TYPES:
        return phrase(N_("{giver} leaves {item} at {taker}"), **values)
    return phrase(N_("{giver} puts {item} in {taker}"), **values)


def _log_move(
    repo: Repo, cs: Changeset, name: str, item: dict[str, JSON], giver: Entity, taker: Entity
) -> None:
    """During a session, a move is a journal beat about everyone involved: where things went
    stays in their chronicles (`didact where` follows the inventories themselves)."""
    from didact.services import play

    current = play.load(repo)
    if not current.session_open:
        return
    about = [str(giver.id), str(taker.id)]
    ref = item.get("ref")
    if isinstance(ref, str) and ref:
        about.append(ref)
    play.add_beat(cs, current, "note", f"{name}: {giver.name} → {taker.name}", about=about)


@command(
    "inv use",
    summary="Spend an item's uses or charges, or roll its usage die",
    writes=True,
    examples=(
        "didact inv use freya torch",
        "didact inv use freya wand --spend 2",
        "didact inv use freya lantern            # a usage die: rolled and logged",
    ),
)
def inv_use(
    ctx: Context,
    who: Annotated[str, "whose item", Metavar("record")],
    item: Annotated[str, "the item", Metavar("item")],
    *,
    spend: Annotated[int, "how many uses", Metavar("n")] = 1,
    got: Annotated[str | None, "a usage die you rolled yourself", Metavar("n")] = None,
) -> Out:
    from didact.services import dice, inventory

    if spend < 1:
        raise InvalidError(_("--spend must be at least 1"), hint=_("leave it out to spend one use"))
    repo = open_repo(ctx)
    located = repo.resolve(who)
    cs = changeset(ctx, repo, N_("{who} uses {item}"), who=located.entity.name, item=item)
    rolled: list[str] = []

    def roll(expression: str, reason: str) -> int:
        outcome = dice.roll(
            repo,
            expression,
            as_record=str(located.entity.id),
            got=got,
            reason=reason,
            command=ctx.command_line,
            dry=ctx.dry_run,
        )
        rolled.append(outcome.line)
        value = outcome.rolled.result.value
        return int(value) if isinstance(value, int | float) else 0

    change = inventory.use(cs, located, item, spend, roll=roll, mode=_mode(ctx, repo, False))
    change.notes[:0] = rolled
    done = _("{who} uses {item}", who=located.entity.name, item=item)
    return _finish(ctx, cs, done, [change], {"id": change.record, "rolls": list[JSON](rolled)})


@command(
    "inv recharge",
    summary="Refill an item's uses (to its max, or --to n); a usage die goes back to full",
    writes=True,
    examples=("didact inv recharge freya wand", "didact inv recharge freya torch --to 3"),
)
def inv_recharge(
    ctx: Context,
    who: Annotated[str, "whose item", Metavar("record")],
    item: Annotated[str, "the item", Metavar("item")],
    *,
    to: Annotated[int | None, "how many uses (default: its max)", Metavar("n")] = None,
) -> Out:
    from didact.services import inventory

    repo = open_repo(ctx)
    located = repo.resolve(who)
    cs = changeset(ctx, repo, N_("{who} recharges {item}"), who=located.entity.name, item=item)
    change = inventory.recharge(cs, located, item, to, mode=_mode(ctx, repo, False))
    done = _(
        "{who}: {item} recharged", who=located.entity.name, item=inventory.name_of(change.item)
    )
    return _finish(ctx, cs, done, [change], {"id": change.record, "item": change.item})
