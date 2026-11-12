"""Clearing the history: drop old events from the log, to shrink it and to forget for good.

Every change keeps its files' full text from before and after in the log, so the log grows
with play, and deleted worlds and records live on in it. `didact history --clear` drops:
- by default, the changes and undos: the file snapshots, most of the bytes and all the deleted
  content. Rolls and notes stay, so the dice record (`rolls`, `replay`, the roll lines in
  session views) is untouched;
- with `rolls`, the rolls and notes too.

Only events numbered below the cut go (`before`; by default, everything so far). A `note`
marker takes the next number, so event numbers never restart, and it keeps the highest roll
number, so roll numbers never repeat (it stands in for earlier markers `rolls` drops). Save
points the log can no longer rebuild are removed, as one ordinary change. The rewrite itself
can't be undone: that's what it is for.
"""

from dataclasses import dataclass

from didact.core.errors import InvalidError
from didact.core.i18n import N_, _
from didact.core.phrases import Phrase, counted, english, phrase
from didact.services import savepoints
from didact.services.care import human
from didact.services.savepoints import Placed
from didact.store.changeset import Changeset
from didact.store.events import CLEARED, SAY, Cleared, Event
from didact.store.repo import Repo

CHANGES = ("change", "undo")
DICE = ("roll", "note")


@dataclass(frozen=True, slots=True)
class Plan:
    """What clearing the history would drop, and what it would take with it."""

    cut: int  # events numbered below it are cleared
    rolls: bool  # the dice record (rolls and notes) goes too
    last: int  # the newest event now: the marker takes the next number
    events: int  # the events that go
    bytes: int  # their size in the log
    size: int  # the log's size now
    changes: int  # of those, changes and undos
    dice: int  # of those, rolls and notes (and rolls marked undone)
    markers: int  # of those, earlier clears' markers (the new one carries their numbers on)
    kept: int  # rolls and notes before the cut that stay
    horizon: int  # the cut the log has after this clear (an earlier one may be later)
    saves: tuple[Placed, ...]  # save points the log could no longer rebuild

    @property
    def nothing(self) -> bool:
        """Nothing to drop but earlier markers: a new one would only replace them."""
        return self.events == self.markers

    @property
    def kinds(self) -> tuple[str, ...]:
        return (*CHANGES, *DICE) if self.rolls else CHANGES


@dataclass(frozen=True, slots=True)
class Done:
    """A clear that happened: its plan, the marker, and the save points it removed."""

    plan: Plan
    marker: Event
    size: int  # the log's size afterwards
    saves: tuple[Placed, ...]
    saves_event: Event | None  # the change that removed them (undo brings them back, unusable)


def parse_cut(text: str) -> int:
    """`e58`, `#e58` or `58`: the first event to keep."""
    cleaned = text.strip().lstrip("#").lower()
    digits = cleaned[1:] if cleaned.startswith("e") else cleaned
    if not digits.isdigit() or int(digits) < 1:
        raise InvalidError(
            _("--before takes an event, not {text}", text=repr(text)),
            hint=_("e.g. `--before e58`; `didact history` shows the event numbers"),
        )
    return int(digits)


def drops(event: Event, cut: int, rolls: bool) -> bool:
    """Whether clearing the history before `cut` drops this event."""
    if event.seq >= cut:
        return False
    if event.kind == "change" or (event.kind == "undo" and event.files):
        return True
    # The dice record: rolls, rolls marked undone (an undo without files) and notes. Earlier
    # clears' markers are notes too: the new marker carries their roll number and cut on.
    return rolls


def plan(repo: Repo, *, before: int | None = None, rolls: bool = False) -> Plan:
    """What `clear` would do. `before` keeps that event and everything after it."""
    last = repo.log.last_seq()
    if before is not None and last and before > last:
        raise InvalidError(
            _("there's no #e{before} yet: the newest event is #e{last}", before=before, last=last),
            hint=_("leave out --before to clear everything so far"),
        )
    cut = last + 1 if before is None else before
    events = dropped = changes = dice = markers = kept = earlier = 0
    for event, line in repo.log.entries():
        mark = Cleared.of(event)
        if mark is not None:
            earlier = max(earlier, mark.before)
        if drops(event, cut, rolls):
            events += 1
            dropped += len(line.encode("utf-8"))
            if event.kind == "change" or (event.kind == "undo" and event.files):
                changes += 1
            else:
                dice += 1
                if mark is not None:
                    markers += 1
        elif event.seq < cut and mark is None:
            kept += 1
    horizon = max(cut, earlier)
    return Plan(
        cut=cut,
        rolls=rolls,
        last=last,
        events=events,
        bytes=dropped,
        size=repo.log.path.stat().st_size if repo.log.path.is_file() else 0,
        changes=changes,
        dice=dice,
        markers=markers,
        kept=kept,
        horizon=horizon,
        saves=tuple(savepoints.stale(repo, horizon)) if events > markers else (),
    )


def said(found: Plan) -> Phrase:
    """The marker's line in `didact history`."""
    what = phrase(N_("rolls and notes too")) if found.rolls else phrase(N_("rolls and notes kept"))
    return phrase(
        N_("history cleared: {events} before #e{cut} dropped ({size}); {what}"),
        events=counted("{n} event", "{n} events", found.events),
        cut=found.cut,
        size=human(found.bytes),
        what=what,
    )


def clear(
    repo: Repo, *, before: int | None = None, rolls: bool = False, command: str | None = None
) -> Done | None:
    """Rewrite the log without the cleared events, then remove the save points that went
    with them. None when there's nothing to clear. Can't be undone."""
    from didact.services.dice import highest_roll

    if not repo.initialized():
        return None
    with repo.writing():
        found = plan(repo, before=before, rolls=rolls)  # again, now that no one else writes
        if found.nothing:
            return None
        mark = Cleared(
            events=found.events,
            before=found.cut,
            rolls=highest_roll(repo),
            kinds=found.kinds,
            bytes=found.bytes,
        )
        words = said(found)
        marker = Event.new(
            found.last + 1,
            "note",
            english(words),
            command=command,
            data={CLEARED: mark.to_data(), SAY: words},
        )
        size = repo.log.rewrite(lambda e: not drops(e, found.cut, rolls), then=[marker])
    # The save points it took with it: an ordinary change (it takes the lock itself), in no turn
    gone: tuple[Placed, ...] = ()
    saves_event: Event | None = None
    cs = Changeset(repo, summary="", command=command).say(N_("remove save points"))
    removed = savepoints.prune(cs, found.horizon)
    if removed and not cs.is_empty():
        labels = ", ".join(repr(p.point.label) for p in removed)
        cs.say(
            N_("remove {points} older than the cleared history: {labels}"),
            points=counted("{n} save point", "{n} save points", len(removed)),
            labels=labels,
        )
        saves_event = cs.apply()
        gone = tuple(removed)
    return Done(found, marker, size, gone, saves_event)
