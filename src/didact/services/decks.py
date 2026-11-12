"""Decks and bags in a campaign: shuffle (a logged roll), draw, discard, refill."""

import secrets
from dataclasses import dataclass
from typing import Literal, cast

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.services import packs as pack_service
from didact.services import state
from didact.services.dice import Described, logged
from didact.store.changeset import Changeset
from didact.store.repo import Repo
from didact.tables import decks

type PileKind = Literal["deck", "bag"]


@dataclass(frozen=True, slots=True)
class Pile:
    kind: PileKind
    id: str  # qualified pack.id
    data: dict[str, JSON]

    @property
    def state_name(self) -> str:
        return "decks" if self.kind == "deck" else "bags"


def find(repo: Repo, kind: PileKind, ref: str) -> Pile:
    item = pack_service.active(repo).find(kind, ref)
    return Pile(kind, item.qualified, item.data)


def shuffle(
    repo: Repo,
    pile: Pile,
    *,
    counts: dict[str, int] | None = None,
    reason: str | None,
    command: str | None,
) -> tuple[list[str], str]:
    """A fresh shuffled pile: a logged roll, so the order is reproducible. Returns (order, #r)."""
    items = decks.cards(pile.data) if pile.kind == "deck" else decks.tokens(pile.data, counts or {})
    if not items:
        raise InvalidError(
            _("{pile} is empty", pile=pile.id),
            hint=_("give the bag its token counts: `--with name=N`"),
        )

    def perform(stream: str | None) -> list[str]:
        return decks.shuffled(items, stream or secrets.token_hex(8))

    def describe(order: list[str], label: str) -> Described:
        what = "shuffle" if pile.kind == "deck" else "fill"
        unit = "cards" if pile.kind == "deck" else "tokens"
        summary = f"{label} {what} {pile.id} ({len(order)} {unit})"
        data: dict[str, JSON] = {"kind": "shuffle", "pile": pile.id, "items": list[JSON](items)}
        return summary, data | {"order": list[JSON](order)}

    done = logged(
        repo, perform, describe, seed=None, physical=False, reason=reason, command=command
    )
    return done.value, done.summary.split(" ", 1)[0]


def current(repo: Repo, pile: Pile) -> dict[str, JSON]:
    return decks.pile(state.load(repo, pile.state_name), pile.id)


def plan(cs: Changeset, pile: Pile, value: dict[str, JSON]) -> None:
    data = state.load(cs.repo, pile.state_name)
    data[pile.id] = value
    state.plan(cs, pile.state_name, data)


def draw(
    cs: Changeset, pile: Pile, count: int, *, reason: str | None, command: str | None
) -> tuple[list[str], list[str]]:
    """Draw `count`; shuffles first (logged) when there's no pile yet. Returns (drawn, notes)."""
    repo = cs.repo
    notes: list[str] = []
    value = current(repo, pile)
    remaining = [str(c) for c in cast(list[JSON], value.get("pile") or [])]
    if not value:
        remaining, label = shuffle(repo, pile, reason=reason, command=command)
        notes.append(
            _("shuffled a new deck ({label})", label=label)
            if pile.kind == "deck"
            else _("shuffled a new bag ({label})", label=label)
        )
    if count > len(remaining):
        raise InvalidError(
            _(
                "{pile} has {left} left, can't draw {count}",
                pile=pile.id,
                left=len(remaining),
                count=count,
            ),
            hint=_("reshuffle with `didact {kind} shuffle {pile}`", kind=pile.kind, pile=pile.id),
        )
    drawn, rest = remaining[:count], remaining[count:]
    out = [*cast(list[JSON], value.get("out") or []), *drawn]
    plan(cs, pile, {"pile": list[JSON](rest), "out": list[JSON](out)})
    ends = str(pile.data.get("ends_round", ""))
    if pile.kind == "bag" and ends and ends in drawn:
        notes.append(
            _(
                "{token}: the round ends; refill with `didact bag fill {pile}`",
                token=ends,
                pile=pile.id,
            )
        )
    if pile.kind == "deck" and any(c.startswith("Joker") for c in drawn):
        notes.append(_("a Joker: reshuffle after this round (`didact deck shuffle`)"))
    return drawn, notes


def replay_shuffle(data: dict[str, JSON]) -> str | None:
    """Re-shuffle from the logged stream; None if the order comes out the same."""
    stream, items, order = data.get("stream"), data.get("items"), data.get("order")
    if not isinstance(stream, str) or not isinstance(items, list):
        return _("the log entry has no stream or items")
    again = decks.shuffled([str(i) for i in items], stream)
    return None if again == order else _("came out in a different order")
