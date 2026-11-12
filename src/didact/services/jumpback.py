"""Jumping back: take back everything that happened after a point in the history.

    didact undo --to e40             # everything after #e40, newest first
    didact undo --to e40 --dry-run   # what would go

Every step after the point that is still in effect is taken back, newest first:
- a change is undone (the undo is logged, so `redo` brings it back);
- an undo of a change from before the point is undone, which redoes that change;
- a roll is marked undone, and a roll from before the point that was marked undone after it
  stands again.

Steps whose effects already cancel out after the point (a change and its undo) are left alone,
and notes stay as they are. Nothing leaves the log: jumping back to a later point brings it all
back. Before anything is written, every step is checked against the files as they are, so a
jump goes through whole or not at all (`force` writes over what changed outside the history).
"""

from dataclasses import dataclass, field

from didact.core.errors import ConflictError, InvalidError
from didact.core.i18n import _
from didact.store import changeset as changesets
from didact.store.events import Event, cleared_before, rebuildable, undone_seqs
from didact.store.repo import Repo


@dataclass(frozen=True, slots=True)
class Plan:
    """What jumping back to an event takes back, newest first."""

    to: Event
    steps: tuple[Event, ...]
    marked: dict[int, tuple[int, bool]] = field(default_factory=dict)  # see `_marked_roll`

    @property
    def changes(self) -> list[Event]:
        """Changes to undo, and undos of earlier changes to undo (which redoes them)."""
        return [e for e in self.steps if e.files]

    @property
    def rolls(self) -> list[Event]:
        """Rolls to mark undone."""
        return [e for e in self.steps if e.kind == "roll"]

    @property
    def marks(self) -> list[Event]:
        """Marks on earlier rolls to take back: each roll stands again, or is undone again
        (`marked` says which)."""
        return [e for e in self.steps if e.kind == "undo" and not e.files]


def plan(repo: Repo, to: Event) -> Plan:
    """What jumping back to `to` would take back (nothing is changed)."""
    events = repo.log.all()
    cut = cleared_before(events)
    if not rebuildable(to.seq, cut):
        raise InvalidError(
            _(
                "can't jump back to {event}: the history before #e{cut} was cleared",
                event=to.label,
                cut=cut,
            ),
            hint=_("pick an event from #e{first} on (`didact history`)", first=cut - 1),
        )
    undone = undone_seqs(events)
    by_seq = {e.seq: e for e in events}
    steps: list[Event] = []
    marked: dict[int, tuple[int, bool]] = {}
    for event in reversed(events):
        if event.seq <= to.seq:
            break
        if event.seq in undone:
            continue  # it, or its effect, is already taken back
        if event.kind == "roll" or (event.kind == "change" and event.files):
            steps.append(event)
        elif event.kind == "undo" and event.undoes is not None and event.undoes <= to.seq:
            if event.files:
                steps.append(event)  # an earlier change taken back after the point
                continue
            roll = _marked_roll(by_seq, event)
            if roll is not None:  # a mark made after the point on an earlier roll
                steps.append(event)
                marked[event.seq] = roll
    return Plan(to, tuple(steps), marked)


def _marked_roll(by_seq: dict[int, Event], mark: Event) -> tuple[int, bool] | None:
    """The number of the roll an undo without files marks (through marks of marks), and
    whether the roll stands once the mark is taken back: an undone undo is a redo, so every
    other mark in the chain marks the roll undone."""
    depth = 1
    target = by_seq.get(mark.undoes) if mark.undoes is not None else None
    while target is not None and target.kind == "undo" and not target.files:
        depth += 1
        target = by_seq.get(target.undoes) if target.undoes is not None else None
    if target is None or target.kind != "roll":
        return None
    number = target.data.get("roll")
    if not isinstance(number, int) or isinstance(number, bool):
        return None
    return number, depth % 2 == 1


def check(repo: Repo, found: Plan, *, force: bool = False) -> None:
    """Refuse, before anything is written, if a step would find a file other than its change
    left it (changed outside the history, or by a forced change)."""
    if force:
        return
    texts: dict[str, str | None] = {}
    for event in found.steps:
        for change in event.files:
            if change.path not in texts:
                texts[change.path] = repo.read_text(repo.layout.abs(change.path))
            now = texts[change.path]
            if change.append is not None:
                text = now or ""
                if not text.endswith(change.append):
                    raise _conflict(change.path, event, found.to)
                rest = text[: len(text) - len(change.append)]
                texts[change.path] = None if change.before is None and not rest else rest
                continue
            if now != change.after:
                raise _conflict(change.path, event, found.to)
            texts[change.path] = change.before


def _conflict(path: str, event: Event, to: Event) -> ConflictError:
    return ConflictError(
        _("{path} was changed after {event}", path=path, event=event.label),
        hint=_(
            "it changed outside the history: `didact undo --to {event} --force` writes over it",
            event=f"e{to.seq}",
        ),
    )


def apply(
    repo: Repo, found: Plan, *, force: bool, reason: str | None, command: str | None
) -> list[Event]:
    """Take every step back, newest first; returns the events that did it."""
    from didact.services.dice import unmark, void_roll

    done: list[Event] = []
    for event in found.steps:
        if event.kind == "roll":
            done.append(void_roll(repo, event, reason=reason, command=command))
        elif event.files:
            done.append(changesets.undo(repo, event, force=force, reason=reason, command=command))
        else:
            done.append(unmark(repo, event, reason=reason, command=command))
    return done
