"""Light combat: who's in it, whose turn it is, rounds, and conditions that run out.

No enemy AI: the LLM narrates and decides; Didact keeps the order, the round, the durations,
and runs the system's attack rule. Fighters can join and leave while it goes on, and nobody's
turn is skipped when they do. Where each fighter is, what it's doing and what it means to do
next are its details (`didact about goblin where='on the bridge' plan='cut the rope'`), shown
by `combat status --gm`. Packs set the style in `settings.combat`:

    combat:
      mode: sides            # individual (roll initiative) | sides (alternate) | popcorn
      initiative: d20        # individual mode: each fighter rolls this (with --as them)
      first: party           # sides mode: who acts first
      round_one: "Each PC makes a DEX save to act: `didact do save who=<pc> attr=DEX`."
      attack: attack         # the rule `combat hit` runs
"""

from dataclasses import dataclass, field
from typing import Literal, cast

from didact.core import labels
from didact.core.errors import ConflictError, InvalidError
from didact.core.i18n import _, ngettext
from didact.core.output import JSON
from didact.expr.model import Value
from didact.services import state
from didact.store.changeset import Changeset
from didact.store.repo import Repo

COMBAT = "combat"
type Mode = Literal["individual", "sides", "popcorn"]
MODES: tuple[Mode, ...] = ("individual", "sides", "popcorn")


@dataclass(slots=True)
class Fighter:
    ref: str
    name: str
    side: str
    init: float = 0

    def to_data(self) -> dict[str, JSON]:
        return {"ref": self.ref, "name": self.name, "side": self.side, "init": self.init}


@dataclass(slots=True)
class Condition:
    ref: str
    name: str
    rounds: int | None  # None: until removed

    def to_data(self) -> dict[str, JSON]:
        return {"ref": self.ref, "name": self.name, "rounds": self.rounds}


@dataclass(slots=True)
class Fight:
    mode: Mode = "sides"
    round: int = 1
    turn: int = 0  # index into order (individual, popcorn) or sides (sides mode)
    order: list[Fighter] = field(default_factory=list)
    sides: list[str] = field(default_factory=list)
    acted: list[str] = field(default_factory=list)  # popcorn: who has gone this round
    conditions: list[Condition] = field(default_factory=list)

    @property
    def current(self) -> str:
        """Whose turn: a fighter's name, or a side."""
        if not self.order:
            return "nobody"
        if self.mode == "sides":
            side = self.sides[self.turn % len(self.sides)]
            return f"{side}: " + ", ".join(f.name for f in self.order if f.side == side)
        return self.order[self.turn % len(self.order)].name

    def to_data(self) -> dict[str, JSON]:
        return {
            "active": True,
            "mode": self.mode,
            "round": self.round,
            "turn": self.turn,
            "order": [f.to_data() for f in self.order],
            "sides": list[JSON](self.sides),
            "acted": list[JSON](self.acted),
            "conditions": [c.to_data() for c in self.conditions],
        }

    @classmethod
    def from_data(cls, data: dict[str, JSON]) -> Fight:
        order = [
            Fighter(
                str(f["ref"]),
                str(f["name"]),
                str(f["side"]),
                float(cast(float, f.get("init") or 0)),
            )
            for f in cast(list[dict[str, JSON]], data.get("order") or [])
        ]
        conditions = [
            Condition(str(c["ref"]), str(c["name"]), _rounds(c.get("rounds")))
            for c in cast(list[dict[str, JSON]], data.get("conditions") or [])
        ]
        mode = data.get("mode")
        return cls(
            mode=_mode(mode),
            round=int(cast(int, data.get("round") or 1)),
            turn=int(cast(int, data.get("turn") or 0)),
            order=order,
            sides=[str(s) for s in cast(list[JSON], data.get("sides") or [])],
            acted=[str(a) for a in cast(list[JSON], data.get("acted") or [])],
            conditions=conditions,
        )


def _rounds(raw: JSON) -> int | None:
    return raw if isinstance(raw, int) and not isinstance(raw, bool) else None


def _mode(raw: JSON) -> Mode:
    for mode in MODES:
        if raw == mode:
            return mode
    return "sides"


def load(repo: Repo) -> Fight | None:
    data = state.load(repo, COMBAT)
    return Fight.from_data(data) if data.get("active") else None


def values(fight: Fight) -> dict[str, Value]:
    """What rules read of a fight: `@combat.round`, and who is in it (`@combat.fighters`, ids)."""
    return {"combat.round": fight.round, "combat.fighters": list[Value](f.ref for f in fight.order)}


def save(cs: Changeset, fight: Fight | None) -> None:
    state.plan(cs, COMBAT, fight.to_data() if fight is not None else {"active": False})


def start(
    repo: Repo, fighters: list[Fighter], mode: Mode, first: str | None, initiative: dict[str, float]
) -> Fight:
    if load(repo) is not None:
        raise ConflictError(
            _("a fight is already on"), hint=_("`didact combat end` first, or `combat status`")
        )
    if len(fighters) < 2:
        raise InvalidError(
            _("a fight needs at least two sides or fighters"),
            hint=_("e.g. `didact combat start --party goblin`"),
        )
    fight = Fight(mode=mode)
    if mode == "individual":
        for fighter in fighters:
            fighter.init = initiative.get(fighter.ref, 0)
        fight.order = sorted(fighters, key=lambda f: -f.init)
    else:
        fight.order = fighters
    sides = list(dict.fromkeys(f.side for f in fighters))
    if first and first in sides:
        sides.remove(first)
        sides.insert(0, first)
    fight.sides = sides
    return fight


def advance(fight: Fight, to: str | None) -> list[str]:
    """Move to the next turn. Returns notes: new round, conditions that ran out."""
    if not fight.order:
        raise InvalidError(
            _("nobody is left in the fight"),
            hint=_("`didact combat end`, or `didact combat join <fighter>`"),
        )
    new_round = False
    if fight.mode == "popcorn":
        fight.acted.append(fight.order[fight.turn].ref)
        waiting = [i for i, f in enumerate(fight.order) if f.ref not in fight.acted]
        if to is not None:
            index = next(
                (
                    i
                    for i, f in enumerate(fight.order)
                    if to in (f.ref, f.name.casefold(), f.ref.partition(":")[2])
                ),
                None,
            )
            if index is None or index not in waiting:
                raise InvalidError(
                    _("{fighter} can't go next", fighter=to),
                    hint=_("pick someone who hasn't acted this round"),
                )
            fight.turn = index
        elif waiting:
            fight.turn = waiting[0]
        else:
            new_round = True
            fight.acted = []
            fight.turn = 0
    else:
        size = len(fight.sides) if fight.mode == "sides" else len(fight.order)
        fight.turn += 1
        if fight.turn >= size:
            fight.turn = 0
            new_round = True
    return _next_round(fight) if new_round else []


def _next_round(fight: Fight) -> list[str]:
    """A new round begins and conditions tick down. Returns notes."""
    fight.round += 1
    notes = [_("round {round}", round=fight.round)]
    kept: list[Condition] = []
    for condition in fight.conditions:
        if condition.rounds is None:
            kept.append(condition)
            continue
        condition.rounds -= 1
        if condition.rounds <= 0:
            notes.append(
                _("{condition} ends for {ref}", condition=condition.name, ref=condition.ref)
            )
        else:
            kept.append(condition)
    fight.conditions = kept
    return notes


def named(fight: Fight, word: str) -> Fighter | None:
    """The fighter a word names: its ref, its slug or its name, in any case."""
    wanted = word.strip().casefold()
    for fighter in fight.order:
        ref = fighter.ref.casefold()
        if wanted in (ref, ref.partition(":")[2], fighter.name.casefold()):
            return fighter
    return None


def refuse_doubles(fight: Fight, fighters: list[Fighter]) -> None:
    """Nobody joins a fight they're already in."""
    inside = {f.ref for f in fight.order}
    doubled = [f.name for f in fighters if f.ref in inside]
    if doubled:
        raise ConflictError(
            _("already in the fight: {fighters}", fighters=", ".join(doubled)),
            hint=_("`didact combat status` shows who's in it"),
        )


def join(fight: Fight, fighters: list[Fighter], initiative: dict[str, float]) -> None:
    """Bring fighters into a fight under way; the turn stays with whoever has it.

    Individual mode slots each one in by initiative (after those with the same roll), so one
    who rolled higher than the fighter now acting waits for the next round. Sides and popcorn
    add them at the end; a new side acts last in the round.
    """
    refuse_doubles(fight, fighters)
    for fighter in fighters:
        if fight.mode == "individual":
            fighter.init = initiative.get(fighter.ref, 0)
            index = next(
                (i for i, f in enumerate(fight.order) if f.init < fighter.init), len(fight.order)
            )
            if fight.order and index <= fight.turn:
                fight.turn += 1  # ahead of the fighter whose turn it is
            fight.order.insert(index, fighter)
        else:
            fight.order.append(fighter)
        if fighter.side not in fight.sides:
            fight.sides.append(fighter.side)


def leave(fight: Fight, ref: str) -> list[str]:
    """Take a fighter out of the fight, with their conditions. Returns notes.

    Nobody's turn is skipped: when it was the leaver's turn (or their side's, and they were
    its last), the next one is up, and after the last one of the round a new round begins.
    """
    index = next((i for i, f in enumerate(fight.order) if f.ref == ref), None)
    if index is None:
        raise InvalidError(
            _("{ref} isn't in the fight", ref=ref),
            hint=_("`didact combat status` shows who's in it"),
        )
    gone = fight.order.pop(index)
    fight.conditions = [c for c in fight.conditions if c.ref != ref]
    fight.acted = [a for a in fight.acted if a != ref]
    notes: list[str] = []
    emptied = gone.side in fight.sides and all(f.side != gone.side for f in fight.order)
    if fight.mode == "sides":
        if emptied:
            at = fight.sides.index(gone.side)
            fight.sides.pop(at)
            if at < fight.turn:
                fight.turn -= 1
            elif at == fight.turn and fight.turn >= len(fight.sides) and fight.sides:
                fight.turn = 0
                notes += _next_round(fight)
    else:
        if emptied:
            fight.sides.remove(gone.side)
        if index < fight.turn:
            fight.turn -= 1
        elif index == fight.turn and fight.order:
            waiting = [i for i, f in enumerate(fight.order) if f.ref not in fight.acted]
            if fight.mode == "popcorn" and waiting:
                fight.turn = waiting[0]
            elif fight.mode == "popcorn" or fight.turn >= len(fight.order):
                fight.turn = 0
                fight.acted = []
                notes += _next_round(fight)
    if not fight.order:
        fight.turn = 0
        return [*notes, _("nobody is left in the fight: `didact combat end`")]
    left = list(dict.fromkeys(f.side for f in fight.order))
    if len(left) == 1:
        notes.append(
            _("only one side is left ({side}): `didact combat end` when it's over", side=left[0])
        )
    return notes


def lines(fight: Fight, stats: dict[str, str], notes: dict[str, str] | None = None) -> list[str]:
    """The fight as lines; `notes` (the GM's view) adds each fighter's where, doing and plan."""
    head = _(
        "round {round} · {mode} · now: {current}",
        round=fight.round,
        mode=labels.inline(fight.mode, labels.initiative_mode(fight.mode)),
        current=fight.current,
    )
    out = [head]
    for index, fighter in enumerate(fight.order):
        marker = "→ " if fight.mode != "sides" and index == fight.turn % len(fight.order) else "  "
        init = (
            " " + _("[init {init}]", init=f"{fighter.init:g}") if fight.mode == "individual" else ""
        )
        conditions = [c for c in fight.conditions if c.ref == fighter.ref]
        cond_text = ""
        if conditions:
            cond_text = " · " + ", ".join(
                ngettext(
                    "{condition} ({n} rounds)",
                    "{condition} ({n} rounds)",
                    c.rounds,
                    condition=c.name,
                )
                if c.rounds
                else c.name
                for c in conditions
            )
        stat = f" · {stats[fighter.ref]}" if stats.get(fighter.ref) else ""
        out.append(f"{marker}{fighter.name} ({fighter.side}){init}{stat}{cond_text}")
        if notes and notes.get(fighter.ref):
            out.append(f"    {notes[fighter.ref]}")
    return out
