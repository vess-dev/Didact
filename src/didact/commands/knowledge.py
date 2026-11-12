"""What the players know: reveal, the character sheet, the map, and visiting places."""

from typing import Annotated

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.errors import DidactError, InvalidError, NotFoundError
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON, Out, plain
from didact.store.entity import Entity, Knowledge
from didact.store.repo import Repo


@command(
    "reveal",
    summary="The players learn something: a secret record, a secret line, or a GM detail",
    writes=True,
    examples=(
        "didact reveal loc:hidden-vault",
        "didact reveal sweeney 'Anglwyst'      # moves that line of ## Secrets to ## Revealed",
        "didact reveal loc:drowned-tower --rumor   # they've only heard of it",
        "didact reveal sweeney --field parent      # a field `retcon --secret` hid",
        "didact reveal sweeney plan                # his `plan` detail (see `about`)",
    ),
    description=(
        "Without text, the record's knowledge becomes `known` (or `rumor`). With text, the\n"
        "first line of its `## Secrets` section that contains the text moves to `## Revealed`.\n"
        "Text that is exactly one of its details' names (`plan`) moves that GM detail there\n"
        "instead. During a session the reveal is also logged as a journal beat."
    ),
)
def reveal(
    ctx: Context,
    ref: Annotated[str, "the record", Metavar("record")],
    *text: Annotated[str, "words from the secret line to reveal", Metavar("text")],
    rumor: Annotated[bool, "they've only heard of it: knowledge becomes rumor"] = False,
    field: Annotated[list[str] | None, "a secret field to show (from `retcon --secret`)"] = None,
) -> Out:
    from didact.services import knowledge, play, records

    repo = open_repo(ctx)
    located = repo.resolve(ref)
    wanted = " ".join(text).strip()
    if wanted and rumor:
        raise InvalidError(_("--rumor reveals a record, not a line"), hint=_("leave out the text"))
    target: Knowledge = "rumor" if rumor else "known"
    cs = (
        changeset(ctx, repo, N_("reveal {id}: {what}"), id=str(located.entity.id), what=wanted)
        if wanted
        else changeset(ctx, repo, N_("reveal {id}"), id=str(located.entity.id))
    )
    said: list[str] = []

    def change(entity: Entity) -> None:
        if wanted and any(k.casefold() == wanted.casefold() for k in entity.details):
            said.append(f"{entity.name}'s {knowledge.reveal_detail(entity, wanted)}")
            if entity.knowledge == "secret":
                entity.knowledge = "known"
            return
        if field:
            keys = knowledge.secret_keys(entity)
            shown = [k for k in keys if any(k == f or k.endswith(f".{f}") for f in field)]
            if not shown:
                raise InvalidError(
                    _("{id} keeps no secret {field}", id=entity.id, field=repr(field[0])),
                    hint=_("its secret keys: {keys}", keys=", ".join(keys) or _("none")),
                )
            kept = [k for k in keys if k not in shown]
            if kept:
                entity.extra["secret_keys"] = list[JSON](kept)
            else:
                del entity.extra["secret_keys"]
            said.append(f"{entity.name}'s {', '.join(k.rpartition('.')[2] for k in shown)}")
            return
        if wanted:
            entity.body, line = knowledge.reveal_line(entity.body, wanted)
            said.append(f"{entity.name}: {line.lstrip('-* ').strip()}")
            if entity.knowledge == "secret":
                entity.knowledge = "known"  # knowing a secret about it, they know it exists
            return
        if entity.knowledge == target:
            return
        entity.knowledge = target
        said.append(f"{entity.name} ({target})")

    records.edit(cs, located.path, change)
    if not said:
        return Out(
            data={"id": str(located.entity.id), "knowledge": target, "changed": False},
            md=_("{id} is already {knowledge}", id=located.entity.id, knowledge=target),
        )
    current = play.load(repo)
    if current.session_open:
        play.add_beat(cs, current, "note", f"revealed: {said[0]}", about=[str(located.entity.id)])
    extra: dict[str, JSON] = {"id": str(located.entity.id), "knowledge": target}
    return finish(ctx, cs, done=_("revealed {what}", what=said[0]), extra=extra)


@command(
    "sheet",
    summary="A character sheet as the player sees it: stats, conditions, inventory, links",
    examples=("didact sheet freya", "didact sheet troll --gm", "didact sheet   # the party's PC"),
)
def sheet(
    ctx: Context,
    who: Annotated[str | None, "the character (default: the party's PC)", Metavar("record")] = None,
    *,
    gm: Annotated[bool, "show secret fields and notes too"] = False,
) -> Out:
    from didact.services import inventory, knowledge, party, sheets

    repo = open_repo(ctx)
    if who is None:
        pcs = [m.entity for m in party.members(repo, gm=gm) if m.role == "pc"]
        if len(pcs) != 1:
            names = ", ".join(e.name for e in pcs) or _("none yet")
            raise NotFoundError(
                _("whose sheet?"),
                hint=_("name one: `didact sheet <pc>` (PCs: {names})", names=names),
            )
        who = str(pcs[0].id)
    located = repo.resolve(who)
    entity = located.entity
    if not knowledge.visible(entity.knowledge, gm):
        return Out(
            data={"id": str(entity.id), "hidden": True},
            md=_("{id} is secret: `didact sheet {id} --gm` shows it", id=entity.id),
        )
    sh = sheets.sheet(repo, entity.type)
    hid = knowledge.NOTHING if gm else knowledge.unknown(repo)
    shown, hidden = (entity, knowledge.Hidden()) if gm else knowledge.player_copy(entity, sh, hid)
    label = sh.core.label if sh.core is not None else entity.type
    lines = [f"# {shown.name} ({label})"]
    bag = inventory.find_bag(shown, sh)
    has_bag = bag.spec is not inventory.PLAIN or bool(bag.items)
    for line in sheets.sheet_lines(shown, sh):
        if has_bag and line.lstrip().startswith(f"{bag.spec.label} ("):
            continue  # the inventory gets its own section below
        lines.append(line)
    known = {name for schema in sh.schemas for name in schema.fields}
    for key, value in shown.fields.items():  # open fields the sheet doesn't list: traits, bonds…
        if key in known or key in ("inventory", "map", "routes") or value in (None, "", [], {}):
            continue
        if key == "traits" and isinstance(value, dict):
            from didact.services import tables

            text = tables.traits_line(repo, value)
        elif isinstance(value, dict):
            text = ", ".join(f"{k} {plain(v)}" for k, v in value.items())
        else:
            text = plain(value)
        lines.append(f"{key.replace('_', ' ')}: {text}")
    if has_bag:
        lines += ["", *inventory.lines(shown, sh)]
    links = shown.links  # the player copy has dropped the secret ones
    if links:
        lines += [
            "",
            _(
                "Links: {links}",
                links="; ".join(f"{link.rel} → {_name(repo, link.to)}" for link in links),
            ),
        ]
    body = shown.body.strip()
    if body:
        lines += ["", body]
    tail = hidden.note(str(entity.id))
    if tail:
        lines.append(tail)
    data: dict[str, JSON] = {"id": str(entity.id), "name": shown.name, "sheet": shown.to_data()}
    data["inventory"] = inventory.summary(shown, sh) if has_bag else None
    return Out(data=data, md="\n".join(lines))


def _name(repo: Repo, ref: str) -> str:
    try:
        return repo.resolve(ref).entity.name
    except DidactError:
        return ref


@command(
    "map",
    summary="The places the party knows, how they connect, and where the party is",
    examples=("didact map", "didact map --within loc:the-wood", "didact map --gm"),
    description=(
        "Places are `loc` records: `region` nests them and links connect them\n"
        "(`didact link loc:mill road loc:bridge`). Visited places show their exits; an exit\n"
        "to a secret place shows as `?`. `didact visit <place>` moves the party and reveals it."
    ),
)
def map_(
    ctx: Context,
    *,
    within: Annotated[str | None, "only this place and what's in it", Metavar("place")] = None,
    gm: Annotated[bool, "every place, secret ones too"] = False,
) -> Out:
    from didact.services import maps

    repo = open_repo(ctx)
    root = str(repo.resolve(within, of=maps.PLACE_TYPES).entity.id) if within else None
    lines, data = maps.lines(repo, gm=gm, within=root)
    return Out(data=data, md="\n".join(lines))


@command(
    "visit",
    summary="The party goes somewhere: it's visited and known, and its exits show on the map",
    writes=True,
    examples=("didact visit 'Amber Grave'", "didact visit loc:the-hut"),
)
def visit(ctx: Context, place: Annotated[str, "the place (a loc record)", Metavar("place")]) -> Out:
    from didact.services import knowledge, maps

    repo = open_repo(ctx)
    located = repo.resolve(place, of=maps.PLACE_TYPES)
    if located.entity.type not in maps.PLACE_TYPES:
        raise InvalidError(
            _("{id} isn't a place", id=located.entity.id), hint=_("places are `loc` records")
        )
    cs = changeset(ctx, repo, N_("the party goes to {place}"), place=located.entity.name)
    notes = maps.visit(cs, located)
    known = maps.places(repo)
    here = known.get(str(located.entity.id))
    if here is not None:
        exits = [
            f"{how or _('way')} → " + (known[to].name if known[to].knowledge != "secret" else "?")
            for how, to in here.exits
            if not knowledge.secret_path(how)  # a hidden path is found in play, not listed
        ]
        notes.append(_("exits: {exits}", exits=" · ".join(exits) if exits else _("none known")))
    done = _("the party is at {place}", place=located.entity.name)
    return finish(ctx, cs, done=done, extra={"here": str(located.entity.id)}, notes=notes)


@command(
    "about",
    summary="GM notes on a record: looks, personality, wants, what it's doing and plans, …",
    writes=True,
    examples=(
        "didact about sweeney",
        "didact about sweeney plan='sell the route' doing='whittling by the fire'",
        "didact about sweeney looks='tall, one eye clouded' personality='jovial, greedy'",
        "didact about item:old-sword history='forged for the last king' where='in the crypt'",
        "didact about sweeney --clear doing",
    ),
    description=(
        "Details are short named notes for whoever runs the game; keep them current and the\n"
        "game stays consistent. Suggested names depend on the record (looks, personality,\n"
        "wants, fears, attitude, doing, plan, where, history, powers, state, secret,\n"
        "thoughts); any one-word name works. `thoughts` is for your own ideas about what you\n"
        "made. Players see only `looks`; `reveal <record> <name>` shows them another.\n"
        "Without values: the details, the suggestions still open, the record's chronicle\n"
        "(journal beats `--about` it), what it holds and where it is. This view is for the GM."
    ),
)
def about(
    ctx: Context,
    ref: Annotated[str, "the record", Metavar("record")],
    *values: Annotated[str, "name='text' (empty text clears it)", Metavar("name=text")],
    clear: Annotated[list[str] | None, "remove a detail", Metavar("name")] = None,
) -> Out:
    from didact.services import details, records

    repo = open_repo(ctx)
    located = repo.resolve(ref)
    pairs: dict[str, str] = {}
    for text in values:
        name, sep, value = text.partition("=")
        if not sep or not name.strip():
            raise InvalidError(
                _("can't read {text}", text=repr(text)), hint=_("write name='text', e.g. plan='…'")
            )
        pairs[name.strip()] = value
    if pairs or clear:
        cs = changeset(ctx, repo, N_("about {id}"), id=str(located.entity.id))
        said: list[str] = []
        entity = records.edit(
            cs, located.path, lambda e: said.extend(details.apply(e, pairs, clear or []))
        )
        extra: dict[str, JSON] = {
            "id": str(entity.id),
            "details": dict[str, JSON](entity.details),
            "suggested": list[JSON](details.missing(repo, entity)),
        }
        return finish(ctx, cs, done=f"{entity.name}: " + "; ".join(said), extra=extra)
    entity = located.entity
    return Out(data=_dossier_data(repo, entity), md="\n".join(_dossier(repo, entity)))


def _dossier_data(repo: Repo, entity: Entity) -> dict[str, JSON]:
    from didact.services import details

    data: dict[str, JSON] = {
        "id": str(entity.id),
        "name": entity.name,
        "details": dict[str, JSON](entity.details),
        "suggested": list[JSON](details.missing(repo, entity)),
        "chronicle": list[JSON](details.chronicle(repo, str(entity.id), gm=True)),
    }
    held = details.contents(repo, entity)
    if held:
        data["contents"] = list[JSON](held)
    chains = details.where(repo, str(entity.id))
    if chains:
        data["where"] = [[{"id": str(e.id), "name": e.name} for e in c] for c in chains]
    return data


def _dossier(repo: Repo, entity: Entity) -> list[str]:
    from didact.services import details

    lines = [_("{id} · {name}: GM notes", id=entity.id, name=entity.name)]
    lines += details.lines(entity, gm=True) or [_("(no details yet)")]
    open_ = details.missing(repo, entity)
    if open_:
        lines.append(
            _(
                "open: {names}: `didact about {id} {first}='…'`",
                names=", ".join(open_),
                id=entity.id,
                first=open_[0],
            )
        )
    for chain in details.where(repo, str(entity.id)):
        lines.append(_("whereabouts: {chain}", chain=details.chain_text(chain)))
    held = details.contents(repo, entity)
    if held:
        lines += [_("contents:"), *details.contents_lines(held)]
    beats = details.chronicle(repo, str(entity.id), gm=True)
    if beats:
        lines += [_("chronicle:"), *(f"- {details.chronicle_line(b)}" for b in beats[-12:])]
        if len(beats) > 12:
            lines.append(
                ngettext(
                    "({n} earlier: `didact about {id} --format json`)",
                    "({n} earlier: `didact about {id} --format json`)",
                    len(beats) - 12,
                    id=entity.id,
                )
            )
    return lines


@command(
    "where",
    summary="Where something is: who carries it, or what it's in and where that is",
    examples=(
        "didact where sword",
        "didact where item:silver-key",
        "didact where 'iron spikes' --gm",
    ),
    description=(
        "Follows the inventories: a sword in a chest in a house shows as `in Chest › at My\n"
        "House`. Put things somewhere with `didact inv move <who> <item> <record>`: a place\n"
        "or a container record holds items like a character does. The player view leaves out\n"
        "secret holders; --gm also shows a record's own `where` detail."
    ),
)
def where(
    ctx: Context,
    thing: Annotated[str, "an item's name, or a record", Metavar("thing")],
    *,
    gm: Annotated[bool, "include secret places and GM details"] = False,
) -> Out:
    from didact.services import details

    repo = open_repo(ctx)
    chains = details.where(repo, thing, gm=gm)
    lines = [f"{thing}: {details.chain_text(chain)}" for chain in chains]
    data: dict[str, JSON] = {
        "thing": thing,
        "where": [[{"id": str(e.id), "name": e.name} for e in c] for c in chains],
    }
    if gm:
        try:
            noted = repo.resolve(thing).entity.details.get("where")
        except DidactError:
            noted = None
        if noted:
            data["noted"] = noted
            lines.append(_("{thing} (its `where` detail): {noted}", thing=thing, noted=noted))
    if not lines:
        return Out(
            data=data,
            md=_(
                "nothing called {thing} is in an inventory here "
                "(put it somewhere: `didact inv move <who> <item> <place or container>`)",
                thing=repr(thing),
            ),
        )
    return Out(data=data, md="\n".join(lines))
