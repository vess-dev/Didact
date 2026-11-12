"""Turn groups: everything done in answer to one player message, taken back together.

The Claude Code hook's `didact capture` opens a new turn on each player message (other
clients use `didact turn begin`). While a turn is open, every change and roll carries its id,
and `didact undo --turn` reverts the latest turn's changes (newest first) and marks its rolls
undone. The transcript and journal history are not taken back, only the turn's effects.

The open turn lives in its own state file (`state/turn.yaml`), so opening the next turn never
conflicts with undoing the last one.
"""

from dataclasses import dataclass, field

from didact.core.errors import DidactError, NotFoundError
from didact.core.i18n import _
from didact.store.changeset import Changeset
from didact.store.events import Event, cleared_before, undone_seqs
from didact.store.repo import Repo

TURN = "turn"


def current(repo: Repo) -> str | None:
    """The open turn's id, if a campaign has one open."""
    from didact.services import state

    try:
        if not repo.initialized() or repo.active_campaign() is None:
            return None
        found = state.load(repo, TURN).get("turn")
    except DidactError:
        return None
    return found if isinstance(found, str) else None


def begin(cs: Changeset, label: str | None = None) -> str:
    from didact.services import state

    data = state.load(cs.repo, TURN)
    count = data.get("count")
    number = (count if isinstance(count, int) else 0) + 1
    turn = f"t{number}"
    state.plan(cs, TURN, {"turn": turn, "count": number, "label": label or ""})
    cs.turn = None  # opening a turn isn't part of any turn
    return turn


def end(cs: Changeset) -> str | None:
    from didact.services import state

    data = state.load(cs.repo, TURN)
    was = data.get("turn")
    if isinstance(was, str):
        state.plan(cs, TURN, {**data, "turn": None})
    cs.turn = None
    return was if isinstance(was, str) else None


@dataclass(slots=True)
class Group:
    turn: str
    changes: list[Event] = field(default_factory=list)  # newest first
    rolls: list[Event] = field(default_factory=list)


def group(repo: Repo, turn: str | None = None) -> Group:
    """A turn's effects still in place: the latest turn with any, or the one named.

    Turns from before a history clear's cut are over: their changes are gone, so their rolls
    alone can't be taken back as the turn.
    """
    events = repo.log.all()
    undone = undone_seqs(events)
    cut = cleared_before(events)
    live = [
        e
        for e in events
        if e.seq >= cut
        and e.seq not in undone
        and isinstance(e.data.get("turn"), str)
        and ((e.kind == "change" and e.files) or e.kind == "roll")
    ]
    wanted = turn.strip().lower() if turn else None
    if wanted is None:
        if not live:
            raise NotFoundError(
                _("no turn to take back"),
                hint=_("turns begin with `didact capture` or `turn begin`"),
            )
        wanted = str(live[-1].data["turn"])
    found = Group(wanted)
    for event in reversed(live):
        if event.data.get("turn") != wanted:
            continue
        (found.changes if event.kind == "change" else found.rolls).append(event)
    if not found.changes and not found.rolls:
        raise NotFoundError(
            _("turn {turn} has nothing left to undo", turn=wanted),
            hint=_("see `didact history`; the history before #e{cut} was cleared", cut=cut)
            if cut
            else _("see `didact history`"),
        )
    return found
