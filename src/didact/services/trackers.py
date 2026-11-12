"""Trackers (clocks, tracks, counters, resources, uses, timers), reminders, and quests.

Trackers are records (`track:<slug>`) whose `value` field uses the sheet field kinds, so
`track tick` clamps and reports like `set` does. Timers expire at an in-game time; reminders
live in campaign state and fire when time passes them.
"""

from dataclasses import dataclass
from typing import Literal, cast

from didact.core.errors import InvalidError, NotFoundError
from didact.core.i18n import _, ngettext
from didact.core.ids import EntityId
from didact.core.output import JSON
from didact.schema import fields as kinds
from didact.services import records, state
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Located, Repo

type TrackKind = Literal["clock", "track", "counter", "resource", "uses", "timer", "pool"]
TRACK_KINDS: tuple[TrackKind, ...] = (
    "clock", "track", "counter", "resource", "uses", "timer", "pool",
)  # fmt: skip
POOL_TYPES = ("task", "pressure", "timer", "resource", "power", "campaign")
QUEST_TYPES = ("quest", "thread", "task")
REMINDERS = "reminders"


def spec_for(entity: Entity) -> kinds.FieldSpec:
    kind = str(entity.fields.get("kind", "counter"))
    options: dict[str, JSON] = {}
    for key in ("size", "min", "max"):
        if key in entity.fields:
            options[key] = entity.fields[key]
    return kinds.FieldSpec(
        "value", cast(kinds.FieldKind, "counter" if kind == "timer" else kind), options
    )


def new_track(
    cs: Changeset,
    name: str,
    kind: TrackKind,
    *,
    size: int | None,
    maximum: int | None,
    start: int,
    expires: int | None,
    note: str,
    owner: str | None = None,
    pool: str | None = None,
    phases: list[int] | None = None,
) -> Entity:
    fields: dict[str, JSON] = {"kind": kind}
    if kind in ("clock", "track"):
        fields["size"] = size or (4 if kind == "clock" else 10)
    if kind == "pool":
        sizes = phases or [size or 4]
        if any(n < 1 for n in sizes):
            raise InvalidError(
                _("a pool starts with 1d or more"), hint=_("e.g. --size 4, or --linked 4+4")
            )
        start = start or sizes[0]
        fields["pool"] = pool or "task"
        if len(sizes) > 1:
            fields["phases"] = list[JSON](sizes)
            fields["phase"] = 1
    if maximum is not None:
        fields["max"] = maximum
    if kind == "timer":
        if expires is None:
            raise InvalidError(_("a timer needs --lasts"), hint=_("e.g. `--lasts '6 turns'`"))
        fields["expires"] = expires
    if note:
        fields["note"] = note
    entity = records.build_entity(records.new_id("track", name), name, {"fields": fields})
    if kind != "timer":
        spec = spec_for(entity)
        raw: JSON = start
        if kind in ("resource", "uses"):
            raw = {"value": start or maximum or 0, "max": maximum or start or 0}
        if kind == "pool":
            raw = {"value": start, "max": start}
        entity.fields["value"] = kinds.coerce(spec, raw)
    if owner:
        records.add_link(entity, "of", owner)  # a faction's plan, a PC's corruption, …
    records.create(cs, cs.repo.default_scope("track"), entity)
    return entity


def owned(repo: Repo, owner: str) -> list[Entity]:
    """Trackers that belong to a record (`track new … --for faction:x`)."""
    return [
        repo.located(b.source).entity
        for b in repo.index().backlinks([owner])
        if b.source.type == "track" and b.rel == "of"
    ]


def tick(cs: Changeset, ref: str, op: str, amount: int) -> tuple[Entity, str | None]:
    located = cs.repo.resolve(ref, of="track")  # a name a foe shares is its tracker here
    if located.entity.type != "track":
        raise InvalidError(
            _("{id} isn't a tracker", id=located.entity.id),
            hint=_("trackers are made with `didact track new`"),
        )
    notes: list[str | None] = []

    def change(entity: Entity) -> None:
        new, note = kinds.change(spec_for(entity), entity.fields.get("value"), op, amount)
        entity.fields["value"] = new
        notes.append(note)

    entity = records.edit(cs, located.path, change)
    return entity, notes[0] if notes else None


def show(entity: Entity, now: int | None = None) -> str:
    kind = str(entity.fields.get("kind"))
    if kind == "timer":
        expires = entity.fields.get("expires")
        if isinstance(expires, int) and now is not None:
            left = expires - now
            if left <= 0:
                return _("{name}: expired", name=entity.name)
            return _("{name}: {span} left", name=entity.name, span=_span(left))
        return _("{name}: timer", name=entity.name)
    return f"{entity.name} {kinds.display(spec_for(entity), entity.fields.get('value'))}"


def _span(seconds: int) -> str:
    if seconds >= 86400:
        return ngettext("{n} day", "{n} days", seconds // 86400)
    if seconds >= 3600:
        return ngettext("{n} hour", "{n} hours", seconds // 3600)
    if seconds >= 60:
        return ngettext("{n} minute", "{n} minutes", seconds // 60)
    return _("{n} seconds", n=seconds)


def active(repo: Repo, types: tuple[str, ...], *, gm: bool) -> list[Entity]:
    found: list[Entity] = []
    for row in repo.index().rows(repo.chain(), types=list(types)):
        if row.knowledge == "secret" and not gm:
            continue
        entity = repo.located(row).entity
        if str(entity.fields.get("status", entity.status)) in (
            "done",
            "failed",
            "abandoned",
            "closed",
        ):
            continue
        found.append(entity)
    return found


def expired_timers(repo: Repo, before: int, after: int) -> list[Entity]:
    return [
        e
        for e in active(repo, ("track",), gm=True)
        if e.fields.get("kind") == "timer"
        and isinstance(e.fields.get("expires"), int)
        and before < cast(int, e.fields["expires"]) <= after
    ]


# ---------------------------------------------------------------------------- reminders


@dataclass(frozen=True, slots=True)
class Reminder:
    text: str
    at: int
    every: int | None


def reminders(repo: Repo) -> list[Reminder]:
    raw = state.load(repo, REMINDERS).get("items")
    found: list[Reminder] = []
    for item in raw if isinstance(raw, list) else []:
        if (
            isinstance(item, dict)
            and isinstance(item.get("text"), str)
            and isinstance(item.get("at"), int)
        ):
            every = item.get("every")
            found.append(
                Reminder(
                    str(item["text"]),
                    cast(int, item["at"]),
                    every if isinstance(every, int) else None,
                )
            )
    return found


def pending(repo: Repo) -> list[Reminder]:
    """The reminders still to come, soonest first: the numbering `remind --list` shows."""
    return sorted(reminders(repo), key=lambda r: r.at)


def find_reminder(items: list[Reminder], which: str) -> Reminder:
    """A reminder by its number in `pending` (from 1), or the first whose text has the words."""
    wanted = which.strip()
    if wanted.isdigit():
        if 1 <= int(wanted) <= len(items):
            return items[int(wanted) - 1]
    else:
        words = wanted.casefold().split()
        for item in items:
            if words and all(word in item.text.casefold() for word in words):
                return item
    listed = " · ".join(f"{n}. {r.text}" for n, r in enumerate(items[:10], 1))
    raise NotFoundError(
        _("no reminder {number}", number=wanted)
        if wanted.isdigit()
        else _("no reminder mentions {words}", words=repr(wanted)),
        hint=_("pending: {listed}", listed=listed) if items else _("no reminders are pending"),
    )


def period(seconds: int, units: dict[str, int]) -> str:
    """A span in the largest unit that measures it exactly: `1 day`, `2 watches`, `90 minutes`."""
    for name, size in sorted(units.items(), key=lambda u: -u[1]):
        if 0 < size <= seconds and seconds % size == 0:
            count = seconds // size
            many = name + ("es" if name.endswith(("s", "x", "ch", "sh")) else "s")
            return f"{count} {name if count == 1 else many}"
    return _("{n} seconds", n=seconds)


def save_reminders(cs: Changeset, items: list[Reminder]) -> None:
    data: list[JSON] = []
    for r in sorted(items, key=lambda r: r.at):
        entry: dict[str, JSON] = {"text": r.text, "at": r.at}
        if r.every:
            entry["every"] = r.every
        data.append(entry)
    state.plan(cs, REMINDERS, {"items": data})


def fire_reminders(items: list[Reminder], now: int) -> tuple[list[Reminder], list[Reminder]]:
    """(due now, what stays scheduled); recurring ones move to their next time."""
    due: list[Reminder] = []
    keep: list[Reminder] = []
    for item in items:
        if item.at > now:
            keep.append(item)
            continue
        due.append(item)
        if item.every:
            next_at = item.at
            while next_at <= now:
                next_at += item.every
            keep.append(Reminder(item.text, next_at, item.every))
    return due, keep


# ---------------------------------------------------------------------------- quests


def new_quest(cs: Changeset, type_: str, name: str, goal: str, milestones: list[str]) -> Entity:
    if type_ not in QUEST_TYPES:
        raise InvalidError(
            _("use one of: {types}", types=", ".join(QUEST_TYPES)), hint=_("e.g. --type thread")
        )
    fields: dict[str, JSON] = {"status": "open"}
    if goal:
        fields["goal"] = goal
    if milestones:
        fields["milestones"] = [{"text": m, "done": False} for m in milestones]
    entity = records.build_entity(
        EntityId(type_, records.new_id(type_, name).slug), name, {"fields": fields}
    )
    records.create(cs, cs.repo.default_scope(type_), entity)
    return entity


def progress(cs: Changeset, ref: str, *, milestone: str | None, status: str | None) -> Entity:
    located = cs.repo.resolve(ref, of=QUEST_TYPES)
    if located.entity.type not in QUEST_TYPES:
        raise InvalidError(
            _("{id} isn't a quest, thread or task", id=located.entity.id),
            hint=_("`didact quest list` shows the open ones"),
        )

    def change(entity: Entity) -> None:
        if milestone is not None:
            listed = entity.fields.get("milestones")
            items = (
                [dict(m) for m in listed if isinstance(m, dict)] if isinstance(listed, list) else []
            )
            index = (
                int(milestone) - 1
                if milestone.isdigit()
                else next(
                    (
                        i
                        for i, m in enumerate(items)
                        if str(m.get("text", "")).casefold() == milestone.casefold()
                    ),
                    -1,
                )
            )
            if not 0 <= index < len(items):
                items.append({"text": milestone, "done": True})
            else:
                items[index]["done"] = True
            entity.fields["milestones"] = list[JSON](items)
        if status is not None:
            entity.fields["status"] = status

    return records.edit(cs, located.path, change)


def quest_line(entity: Entity) -> str:
    listed = entity.fields.get("milestones")
    items = [m for m in listed if isinstance(m, dict)] if isinstance(listed, list) else []
    done = sum(1 for m in items if m.get("done"))
    goal = entity.fields.get("goal")
    if items and goal:
        return _(
            "{name} ({done}/{total} milestones): {goal}",
            name=entity.name,
            done=done,
            total=len(items),
            goal=goal,
        )
    if items:
        return _(
            "{name} ({done}/{total} milestones)", name=entity.name, done=done, total=len(items)
        )
    if goal:
        return _("{name}: {goal}", name=entity.name, goal=goal)
    return entity.name


# ---------------------------------------------------------------------------- pools


@dataclass(frozen=True, slots=True)
class PoolRoll:
    entity: Entity
    faces: list[int]
    extra: list[int]
    dropped: int
    left: int
    highest: int | None
    lines: list[str]
    empty: bool
    rolls: tuple[str, ...] = ()  # the rolls' labels (#r12)


def roll_pool(
    cs: Changeset,
    located: Located,
    *,
    drop: int,
    extra: int,
    command: str | None,
    dry: bool,
    roll: bool = True,
) -> PoolRoll:
    """Roll a diminishing pool (as this change leaves it: a rule may have made it): every die
    showing 1-3 drops. `drop` dice go first (greater effect, potency); `extra` dice (spark on a
    power pool) roll along but never drop. At 0d a linked pool starts its next phase; the last
    phase empty means the event happens. `roll=False` only drops `drop` dice (a push, a tick),
    with the same phases and events."""
    from didact.services import dice

    entity = records.planned(cs, located.path)
    if entity.type != "track" or entity.fields.get("kind") != "pool":
        raise InvalidError(
            _("{id} isn't a pool", id=entity.id),
            hint=_("make one: `didact track new '…' --kind pool --size 4`"),
        )
    value = entity.fields.get("value")
    current = int(cast(int, value.get("value"))) if isinstance(value, dict) else 0
    if current <= 0:
        raise InvalidError(
            _("{name} is already empty", name=entity.name), hint=_("its event has happened")
        )
    lines: list[str] = []
    current = max(0, current - drop)
    if drop:
        lines.append(_("{n}d dropped before rolling", n=drop))
    faces: list[int] = []
    labels: list[str] = []
    if current and roll:
        rolled = dice.roll(
            cs.repo, f"{current}d6", reason=f"pool {entity.name}", command=command, dry=dry
        )
        faces = [int(d) for d in _faces(rolled)]
        lines.append(rolled.line)
        labels.append(rolled.label)
    bonus: list[int] = []
    if extra and roll:
        rolled = dice.roll(
            cs.repo,
            f"{extra}d6",
            reason=f"pool {entity.name}: extra dice",
            command=command,
            dry=dry,
        )
        bonus = [int(d) for d in _faces(rolled)]
        lines.append(rolled.line)
        labels.append(rolled.label)
    dropped = sum(1 for f in faces if f <= 3)
    left = current - dropped
    highest = max([*faces, *bonus], default=None)
    phases = entity.fields.get("phases")
    phase = entity.fields.get("phase")
    empty = False
    new_value: dict[str, JSON] = {
        "value": left,
        "max": value.get("max") if isinstance(value, dict) else left,
    }
    new_phase = phase
    if left == 0:
        sizes = [int(cast(int, n)) for n in phases] if isinstance(phases, list) else []
        at = int(phase) if isinstance(phase, int) else len(sizes)
        if at < len(sizes):
            new_phase = at + 1
            new_value = {"value": sizes[at], "max": sizes[at]}
            lines.append(
                _(
                    "phase {phase} is done; phase {next} of {total} begins at {size}d",
                    phase=at,
                    next=at + 1,
                    total=len(sizes),
                    size=sizes[at],
                )
            )
        else:
            empty = True
            note = str(entity.fields.get("note") or _("its event happens"))
            lines.append(_("{name} is empty: {note}", name=entity.name, note=note))

    def change(target: Entity) -> None:
        target.fields["value"] = new_value
        if new_phase is not None:
            target.fields["phase"] = new_phase
        if empty:
            target.fields["status"] = "done"

    edited = records.edit(cs, located.path, change)
    left_now = int(cast(int, new_value["value"]))
    return PoolRoll(edited, faces, bonus, dropped, left_now, highest, lines, empty, tuple(labels))


def _faces(rolled: object) -> list[int]:
    from didact.expr.engine import PoolResult
    from didact.expr.render import walk

    found: list[int] = []
    result = getattr(getattr(rolled, "rolled", None), "result", None)
    for node in walk(result) if result is not None else []:
        if isinstance(node, PoolResult):
            found.extend(die.value for die in node.pool.dice)
    return found
