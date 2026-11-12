"""Deck and bag commands: draw, shuffle/fill, status."""

from typing import Annotated, cast

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.errors import InvalidError
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON, Out


def _draw(ctx: Context, kind: str, ref: str, count: int) -> Out:
    from didact.services import decks

    if count < 1:
        raise InvalidError(_("draw at least one"), hint=_("leave the count out to draw one"))
    repo = open_repo(ctx)
    pile = decks.find(repo, "deck" if kind == "deck" else "bag", ref)
    if ctx.dry_run and not decks.current(repo, pile):
        md = _("dry run: would shuffle {pile} and draw {count}", pile=pile.id, count=count)
        return Out(data={"dry_run": True}, md=md)
    cs = changeset(ctx, repo, N_("draw {count} from {pile}"), count=count, pile=pile.id)
    drawn, notes = decks.draw(cs, pile, count, reason=ctx.reason, command=ctx.command_line)
    cs.say(N_("draw from {pile}: {drawn}"), pile=pile.id, drawn=", ".join(drawn))
    return finish(
        ctx,
        cs,
        done=_("drew {drawn} from {pile}", drawn=", ".join(drawn), pile=pile.id),
        extra={"drawn": list[JSON](drawn), "pile": pile.id},
        notes=notes,
    )


def _shuffle(ctx: Context, kind: str, ref: str, counts: dict[str, int]) -> Out:
    from didact.services import decks

    repo = open_repo(ctx)
    pile = decks.find(repo, "deck" if kind == "deck" else "bag", ref)
    if ctx.dry_run:
        return Out(data={"dry_run": True}, md=_("dry run: would shuffle {pile}", pile=pile.id))
    order, label = decks.shuffle(
        repo, pile, counts=counts, reason=ctx.reason, command=ctx.command_line
    )
    cs = changeset(ctx, repo, N_("shuffle {pile} ({label})"), pile=pile.id, label=label)
    decks.plan(cs, pile, {"pile": list[JSON](order), "out": []})
    if kind == "deck":
        done = ngettext(
            "shuffled {pile}: {n} card ({label})",
            "shuffled {pile}: {n} cards ({label})",
            len(order),
            pile=pile.id,
            label=label,
        )
    else:
        done = ngettext(
            "shuffled {pile}: {n} token ({label})",
            "shuffled {pile}: {n} tokens ({label})",
            len(order),
            pile=pile.id,
            label=label,
        )
    return finish(ctx, cs, done=done, extra={"pile": pile.id})


def _status(ctx: Context, kind: str, ref: str) -> Out:
    from didact.services import decks

    repo = open_repo(ctx)
    pile = decks.find(repo, "deck" if kind == "deck" else "bag", ref)
    value = decks.current(repo, pile)
    left = [str(c) for c in cast(list[JSON], value.get("pile") or [])]
    out = [str(c) for c in cast(list[JSON], value.get("out") or [])]
    if not value:
        return Out(
            data={"pile": pile.id, "left": None, "out": []},
            md=_("{pile}: not shuffled yet", pile=pile.id),
        )
    lines = [_("{pile}: {left} left, {drawn} drawn", pile=pile.id, left=len(left), drawn=len(out))]
    if out:
        lines.append(_("drawn: {items}", items=", ".join(out)))
    return Out(
        data={"pile": pile.id, "left": len(left), "out": list[JSON](out)}, md="\n".join(lines)
    )


@command(
    "deck draw",
    summary="Draw cards from a deck (shuffles a new deck on first use)",
    writes=True,
    examples=("didact deck draw tarot", "didact deck draw action-deck 3"),
)
def deck_draw(
    ctx: Context,
    ref: Annotated[str, "the deck", Metavar("deck")],
    count: Annotated[int, "how many cards"] = 1,
) -> Out:
    return _draw(ctx, "deck", ref, count)


@command(
    "deck shuffle",
    summary="Shuffle every card back into a deck (a logged roll)",
    writes=True,
    examples=("didact deck shuffle action-deck",),
)
def deck_shuffle(ctx: Context, ref: Annotated[str, "the deck", Metavar("deck")]) -> Out:
    return _shuffle(ctx, "deck", ref, {})


@command(
    "deck status", summary="Cards left and drawn in a deck", examples=("didact deck status tarot",)
)
def deck_status(ctx: Context, ref: Annotated[str, "the deck", Metavar("deck")]) -> Out:
    return _status(ctx, "deck", ref)


@command(
    "bag fill",
    summary="Fill a bag with its tokens and shake it (a logged roll)",
    writes=True,
    examples=("didact bag fill initiative --with enemy=6",),
)
def bag_fill(
    ctx: Context,
    ref: Annotated[str, "the bag", Metavar("bag")],
    *,
    with_: Annotated[
        list[str] | None, "tokens of a kind: name=count", Metavar("name=count")
    ] = None,
) -> Out:
    counts: dict[str, int] = {}
    for text in with_ or []:
        name, sep, raw = text.partition("=")
        if not sep or not raw.strip().isdigit():
            raise InvalidError(
                _("invalid --with {value}", value=repr(text)), hint=_("write `--with enemy=6`")
            )
        counts[name.strip()] = int(raw)
    return _shuffle(ctx, "bag", ref, counts)


@command(
    "bag draw",
    summary="Draw tokens from a bag",
    writes=True,
    examples=("didact bag draw initiative",),
)
def bag_draw(
    ctx: Context,
    ref: Annotated[str, "the bag", Metavar("bag")],
    count: Annotated[int, "how many tokens"] = 1,
) -> Out:
    return _draw(ctx, "bag", ref, count)


@command(
    "bag status",
    summary="Tokens left and drawn in a bag",
    examples=("didact bag status initiative",),
)
def bag_status(ctx: Context, ref: Annotated[str, "the bag", Metavar("bag")]) -> Out:
    return _status(ctx, "bag", ref)
