"""Inventory: add, drop, move and use items in a sheet's `slots` field.

Items are stored as `Rope` or `{name, size, count, uses, group, …}`; any other key is kept and
readable by expressions (`armor: 1` → `@inventory.armor`). The field's options set the room:

    inventory: {kind: slots, capacity: 10, groups: {backpack: 6, body: 4},
                sizes: {petty: 0, normal: 1, bulky: 2}, when_full: {set: {hp: 0}}}

- Room: item sizes × counts, plus counters that `occupies` the field (fatigue, say). Going past
  the capacity (or a group's) is refused in strict mode, warned about in lenient mode, and
  allowed with `--force`. Reaching it fires the field's `when_full` hook (see `hooks`).
- Uses: `uses: 3` or `{value: 2, max: 3}` count down; a usage die `{die: d6, full: d8}` is rolled
  and steps down on 1–2. An item whose uses run out is gone unless it can `recharge` or says
  `keep: true`; in a stack, the next one starts full.
- An item's own keys change with `set` (`set freya inventory.sword.damage=d10`, a rule's `set`
  step too), checked as `inv add` checks the item; a rule reads one as
  `@{who.inventory.$item.damage}` (`carried`).
- An item is named by its name or a part of only one name (`find_item`): of several of a name,
  the first; to spend a use (`inv use`, a rule's `use:`, `set …uses-=1`), the first with one.
  In a dotted path (`inventory.12.7mm pistol.damage`) the name is the longest run of parts that
  names an item carried (`item_keys`), so a name may hold dots of its own.
- `inv add` and a rule's `give:` find an entry as the compendium does (`item_data`: its id, its
  name or an alias), among the types one carries (`carried_types`: the usual ones, and any type
  of a pack's that `extends` one); a text that isn't a record's id is a name, `:` and all.
- Records without a slots field (no system yet) keep a plain `fields.inventory` list.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import cast

from didact.core.errors import ConflictError, DidactError, InvalidError, NotFoundError
from didact.core.i18n import _, ngettext
from didact.core.ids import EntityId
from didact.core.output import JSON
from didact.expr.model import CHAINS
from didact.packs.library import PackSet
from didact.schema import fields as kinds
from didact.schema.sheet import Sheet
from didact.services import assign, hooks, records, sheets
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Located, Repo

PLAIN = kinds.FieldSpec("inventory", "slots")  # for records whose sheet has no slots field
HIDDEN = frozenset({"name", "count", "size", "group", "entry", "ref", "price"})  # not details
ITEM_TYPES = frozenset({
    "item", "gear", "weapon", "armor", "relic", "spellbook", "tool", "treasure", "consumable",
    "artifact",
})  # fmt: skip
PROSE = frozenset({"description", "summary", "notes"})
USE_KEYS = ("uses", "charges")  # a relic's charges spend like uses


def uses_key(entry: dict[str, JSON]) -> str:
    """Which key holds an item's uses: `uses`, or a relic's `charges`."""
    return next((k for k in USE_KEYS if k in entry), "uses")


USAGE_DOWN = 2  # a usage die steps down on this or lower


@dataclass(slots=True)
class Bag:
    """One record's inventory field, read from its sheet."""

    spec: kinds.FieldSpec
    block: str  # "fields" or the system pack id
    items: list[JSON] = field(default_factory=list)

    @property
    def groups(self) -> dict[str, int]:
        raw = self.spec.opt("groups")
        if not isinstance(raw, dict):
            return {}
        return {str(k): v for k, v in raw.items() if isinstance(v, int)}


def find_bag(entity: Entity, sh: Sheet, name: str | None = None) -> Bag:
    for schema in sh.schemas:
        for spec in schema.fields.values():
            if spec.kind == "slots" and name in (None, spec.name):
                core = schema.pack == "core"
                container = entity.fields if core else entity.mechanics.get(schema.pack)
                raw = container.get(spec.name) if isinstance(container, dict) else None
                items = list(raw) if isinstance(raw, list) else []
                return Bag(spec, "fields" if core else schema.pack, items)
    raw = entity.fields.get(PLAIN.name)
    return Bag(PLAIN, "fields", list(raw) if isinstance(raw, list) else [])


def _store(entity: Entity, bag: Bag) -> None:
    items = list[JSON](bag.items)
    if bag.block == "fields":
        entity.fields[bag.spec.name] = items
        return
    block = entity.mechanics.get(bag.block)
    if not isinstance(block, dict):
        block = {}
        entity.mechanics[bag.block] = block
    block[bag.spec.name] = items


# ---------------------------------------------------------------------------- items


def name_of(item: JSON) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or item.get("ref") or "?")
    return str(item)


def count_of(item: JSON) -> int:
    count = item.get("count", 1) if isinstance(item, dict) else 1
    return count if isinstance(count, int) and not isinstance(count, bool) and count > 0 else 1


def _as_dict(item: JSON) -> dict[str, JSON]:
    return dict(item) if isinstance(item, dict) else {"name": name_of(item)}


def _compact(entry: dict[str, JSON]) -> JSON:
    """`{name: Rope}` is stored as plain `Rope`."""
    return entry["name"] if list(entry) == ["name"] else entry


def with_count(item: JSON, count: int) -> JSON:
    entry = _as_dict(item)
    if count == 1:
        entry.pop("count", None)
    else:
        entry["count"] = count
    return _compact(entry)


def _details(item: JSON) -> dict[str, JSON]:
    return {k: v for k, v in _as_dict(item).items() if k not in ("name", "count")}


def _same(a: JSON, b: JSON) -> bool:
    """Items that stack: the same name and details, whatever their counts."""
    return name_of(a).casefold() == name_of(b).casefold() and _details(a) == _details(b)


def find_item(bag: Bag, name: str, *, usable: bool = False) -> int:
    """An item's index by name: its name (any case), else a part of only one name. Several
    items of that name (a full and an empty Rations): the first; to spend a use (`usable`:
    `inv use`, a rule's `use:`, `set …uses-=1`), the first that has one left."""
    wanted = name.strip().casefold()
    found = [i for i, item in enumerate(bag.items) if name_of(item).casefold() == wanted]
    if not found:
        found = [i for i, item in enumerate(bag.items) if wanted in name_of(item).casefold()]
        names = list(dict.fromkeys(name_of(bag.items[i]) for i in found))
        if len({n.casefold() for n in names}) > 1:
            raise ConflictError(
                _("{name} could be: {options}", name=repr(name), options=", ".join(names)),
                hint=_("use the full name"),
            )
    if not found:
        have = ", ".join(name_of(i) for i in bag.items)
        raise InvalidError(
            _("no {name} here", name=repr(name)),
            hint=_("carrying: {items}", items=have) if have else _("carrying: nothing"),
        )
    if usable:
        return next((i for i in found if has_uses(bag.items[i])), found[0])
    return found[0]


def item_keys(bag: Bag, parts: Sequence[str]) -> tuple[str, tuple[str, ...]]:
    """An item's name and the keys after it, of a dotted path into a slots field
    (`sword.damage`, `12.7mm pistol.uses.max`). A name may hold dots itself, so the longest run
    of parts that names an item carried, as `inv` names one, is the name."""
    for cut in range(len(parts), 1, -1):
        name = ".".join(parts[:cut])
        try:
            find_item(bag, name)
        except InvalidError:  # nothing of that name: a shorter one, then
            continue
        return name, tuple(parts[cut:])
    return parts[0], tuple(parts[1:])


def has_uses(item: JSON) -> bool:
    """Whether an item has a use left to spend: uses or charges above 0, or a usage die."""
    uses = item.get(uses_key(item)) if isinstance(item, dict) else None
    if isinstance(uses, dict):
        value = uses.get("value")
        return "die" in uses or (isinstance(value, int) and value > 0)
    return isinstance(uses, int) and not isinstance(uses, bool) and uses > 0


def describe_item(bag: Bag, item: JSON) -> str:
    """`Longsword (bulky, 2 slots): damage d10`"""
    size = kinds.item_size(bag.spec, item)
    count = count_of(item)
    label = name_of(item) + (f" ×{count}" if count > 1 else "")
    raw_size = item.get("size") if isinstance(item, dict) else None
    kind = f"{raw_size}, " if isinstance(raw_size, str) else ""
    head = ngettext(
        "{label} ({kind}{n} slot)", "{label} ({kind}{n} slots)", size, label=label, kind=kind
    )
    details: list[str] = []
    for key, value in _details(item).items():
        if key in HIDDEN:
            continue
        if isinstance(value, dict) and "value" in value:
            details.append(f"{key} {value.get('value')}/{value.get('max')}")
        elif isinstance(value, dict) and "die" in value:
            details.append(f"{key} {value['die']}")
        elif value is True:
            details.append(key)
        else:
            details.append(f"{key} {value}")
    return head + (": " + ", ".join(details) if details else "")


# ---------------------------------------------------------------------------- room


@dataclass(frozen=True, slots=True)
class Room:
    used: int
    capacity: int | None
    groups: dict[str, tuple[int, int]]  # group → (used, capacity)

    def line(self) -> str:
        if self.capacity is None:  # a place or a chest: no room limit, just what's there
            parts = [ngettext("{n} slot used", "{n} slots used", self.used)]
        else:
            parts = [_("{used}/{capacity} slots", used=self.used, capacity=self.capacity)]
        parts += [f"{name} {used}/{cap}" for name, (used, cap) in self.groups.items()]
        return " · ".join(parts)


def room(entity: Entity, sh: Sheet, bag: Bag) -> Room:
    if bag.spec is PLAIN:
        used: object = sum(kinds.item_size(bag.spec, i) for i in bag.items)
        capacity: object = None
    else:
        found = sheets.entity_values(entity, sh)
        used, capacity = found.get(f"{bag.spec.name}.used"), found.get(f"{bag.spec.name}.capacity")
    groups: dict[str, tuple[int, int]] = {}
    for name, cap in bag.groups.items():
        taken = sum(kinds.item_size(bag.spec, i) for i in bag.items if group_of(bag, i) == name)
        groups[name] = (taken, cap)
    return Room(
        used if isinstance(used, int) else 0,
        capacity if isinstance(capacity, int) else None,
        groups,
    )


def group_of(bag: Bag, item: JSON) -> str | None:
    raw = item.get("group") if isinstance(item, dict) else None
    return raw if isinstance(raw, str) and raw in bag.groups else None


def _place(bag: Bag, entry: dict[str, JSON], wanted: str | None) -> None:
    """Put an item in a group: the one asked for, else the first with room."""
    groups = bag.groups
    if not groups:
        if wanted:
            raise InvalidError(
                _("{field} has no groups", field=bag.spec.label), hint=_("leave out --to")
            )
        entry.pop("group", None)
        return
    if wanted is not None:
        if wanted not in groups:
            raise InvalidError(
                _("no group {group}", group=repr(wanted)),
                hint=_("groups: {groups}", groups=", ".join(groups)),
            )
        entry["group"] = wanted
        return
    if entry.get("group") in groups:
        return
    size = kinds.item_size(bag.spec, entry)
    for name, cap in groups.items():
        taken = sum(kinds.item_size(bag.spec, i) for i in bag.items if group_of(bag, i) == name)
        if taken + size <= cap:
            entry["group"] = name
            return
    entry["group"] = next(iter(groups))


def over(before: Room, after: Room) -> list[str]:
    """What a change overfilled beyond where it already was."""
    found: list[str] = []
    if after.capacity is not None and after.used > max(before.used, after.capacity):
        found.append(_("{used}/{capacity} slots", used=after.used, capacity=after.capacity))
    for name, (used, cap) in after.groups.items():
        was = before.groups.get(name, (0, cap))[0]
        if used > max(was, cap):
            found.append(f"{name} {used}/{cap}")
    return found


# ---------------------------------------------------------------------------- changes


@dataclass(slots=True)
class Change:
    """What an inventory command did to one record (a use: whether its last use went, `out`;
    whether none of it is left, `gone`; the uses `left`; the usage `die` now and what it
    `rolled`)."""

    record: str
    name: str
    notes: list[str] = field(default_factory=list)
    fired: hooks.Outcome = field(default_factory=hooks.Outcome)
    item: JSON = None
    out: bool = False
    gone: bool = False
    left: int = 0
    die: str = ""
    rolled: int = 0


type Work = Callable[[Entity, Bag, Change], None]


def _edit(
    cs: Changeset, located: Located, mode: sheets.Strictness, force: bool, work: Work
) -> Change:
    """Load the record's bag, let `work` change it, check the room, and fire hooks."""
    sh = sheets.sheet(cs.repo, located.entity.type)
    change = Change(str(located.entity.id), located.entity.name)

    def mutate(entity: Entity) -> None:
        bag = find_bag(entity, sh)
        before = room(entity, sh, bag)
        values = sheets.entity_values(entity, sh)
        work(entity, bag, change)
        _store(entity, bag)
        overfull = over(before, room(entity, sh, bag))
        if overfull and not force:
            if mode == "strict":
                raise InvalidError(
                    _(
                        "{name} can't carry that: {over}",
                        name=entity.name,
                        over=", ".join(overfull),
                    ),
                    hint=_("drop or move something first, or pass --force --reason '…'"),
                )
            if mode == "lenient":
                change.notes.append(
                    _(
                        "warning: {name} can't carry that: {over}",
                        name=entity.name,
                        over=", ".join(overfull),
                    )
                )
        if force:
            change.notes.extend(hooks.skipped(entity, sh, values))
            return
        fired = hooks.settle(entity, sh, values, mode)
        change.fired.extend(fired)
        change.notes.extend(fired.notes)

    records.edit(cs, located.path, mutate)
    return change


def add(
    cs: Changeset,
    located: Located,
    item: dict[str, JSON],
    *,
    group: str | None = None,
    mode: sheets.Strictness = "strict",
    force: bool = False,
) -> Change:
    def work(entity: Entity, bag: Bag, change: Change) -> None:
        try:
            coerced = cast(list[JSON], kinds.coerce(bag.spec, [cast(JSON, item)]))
        except kinds.FieldError as exc:
            raise InvalidError(str(exc), hint=_("e.g. `didact inv add freya Rope`")) from exc
        entry = _as_dict(coerced[0])
        for key in USE_KEYS:
            raw_uses = entry.get(key)
            if isinstance(raw_uses, int | str) and not isinstance(raw_uses, bool):
                entry[key] = uses_value(str(raw_uses))  # `uses: 3` from the compendium → 3/3
        _place(bag, entry, group)
        for index, held in enumerate(bag.items):
            if _same(held, entry):
                bag.items[index] = with_count(held, count_of(held) + count_of(entry))
                break
        else:
            bag.items.append(_compact(entry))
        change.item = _compact(entry)

    return _edit(cs, located, mode, force, work)


def remove(
    cs: Changeset,
    located: Located,
    name: str,
    count: int | None = None,
    *,
    mode: sheets.Strictness = "strict",
) -> Change:
    """Take an item out (a whole stack, or `count` of it). `Change.item` is what came out."""

    def work(entity: Entity, bag: Bag, change: Change) -> None:
        index = find_item(bag, name)
        held = bag.items[index]
        have = count_of(held)
        taking = have if count is None else count
        if not 1 <= taking <= have:
            raise InvalidError(
                _("{name} has {count} {item}", name=entity.name, count=have, item=name_of(held)),
                hint=_("check --count"),
            )
        if taking == have:
            bag.items.pop(index)
        else:
            bag.items[index] = with_count(held, have - taking)
        change.item = with_count(held, taking)

    return _edit(cs, located, mode, False, work)


def regroup(
    cs: Changeset,
    located: Located,
    name: str,
    group: str,
    *,
    mode: sheets.Strictness = "strict",
    force: bool = False,
) -> Change:
    """Move an item between the field's groups (backpack → body)."""

    def work(entity: Entity, bag: Bag, change: Change) -> None:
        index = find_item(bag, name)
        entry = _as_dict(bag.items[index])
        _place(bag, entry, group)
        bag.items[index] = _compact(entry)
        change.item = bag.items[index]

    return _edit(cs, located, mode, force, work)


def use(
    cs: Changeset,
    located: Located,
    name: str,
    spend: int = 1,
    *,
    roll: Callable[[str, str], int],
    mode: sheets.Strictness = "strict",
) -> Change:
    """Spend uses or charges, or roll a usage die (`roll(expression, reason)`, logged). Of
    several items of the name, the first with a use left (`find_item`)."""

    def work(entity: Entity, bag: Bag, change: Change) -> None:
        index = find_item(bag, name, usable=True)
        entry = _as_dict(bag.items[index])
        label = name_of(entry)
        change.item = _compact(dict(entry))
        key = uses_key(entry)
        uses = entry.get(key)
        if uses is None:
            raise InvalidError(
                _("{item} has no uses to spend", item=label),
                hint=_(
                    "give it uses: `didact inv recharge {record} {item} --to 3`",
                    record=change.record,
                    item=repr(label),
                ),
            )
        if isinstance(uses, dict) and "die" in uses:
            left_die = _usage_die(str(uses["die"]), label, roll, change)
            if left_die is None:
                change.out = True
                change.gone = _spent(bag, index, entry, change)
            else:
                entry[key] = {**uses, "die": left_die}
                bag.items[index] = _compact(entry)
                change.die, change.left = left_die, 1
            return
        left, cap = _uses(uses, label)
        if left < spend:
            raise InvalidError(
                ngettext("{item} has {n} use left", "{item} has {n} uses left", left, item=label),
                hint=_(
                    "refill it with `didact inv recharge {record} {item}`",
                    record=change.record,
                    item=repr(label),
                ),
            )
        left -= spend
        change.left = left
        entry[key] = {"value": left, "max": cap} if cap is not None else left
        if left == 0:
            change.out = True
            change.gone = _spent(bag, index, entry, change)
            return
        bag.items[index] = _compact(entry)
        change.notes.append(
            ngettext("{item}: {n} use left", "{item}: {n} uses left", left, item=label)
        )

    return _edit(cs, located, mode, False, work)


def uses_value(raw: str) -> JSON:
    """`--uses 3` → `{value: 3, max: 3}`; `--uses d8` → a usage die `{die: d8, full: d8}`."""
    text = raw.strip().lower()
    if text.startswith("d") and text[1:].isdigit():
        if int(text[1:]) not in CHAINS["standard"]:
            raise InvalidError(
                _("a usage die is d4–d12, not {raw}", raw=repr(raw)), hint=_("e.g. --uses d6")
            )
        return {"die": text, "full": text}
    if text.isdigit() and int(text) > 0:
        return {"value": int(text), "max": int(text)}
    raise InvalidError(
        _("--uses takes a number or a usage die, not {raw}", raw=repr(raw)), hint=_("e.g. 3 or d8")
    )


def _uses(raw: JSON, label: str) -> tuple[int, int | None]:
    if isinstance(raw, int) and not isinstance(raw, bool):
        return raw, None
    if isinstance(raw, dict):
        value, cap = raw.get("value"), raw.get("max")
        if isinstance(value, int):
            return value, cap if isinstance(cap, int) else None
    raise InvalidError(
        _("{item}'s uses must be a number or {{value, max}}, not {raw}", item=label, raw=repr(raw)),
        hint=_("e.g. uses: 3, or uses: {value: 2, max: 3}"),
    )


def _usage_die(die: str, label: str, roll: Callable[[str, str], int], change: Change) -> str | None:
    """Roll a usage die; on 1–2 it steps down (a d4 is used up). Returns the die left."""
    chain = CHAINS["standard"]
    digits = die.removeprefix("d")
    if not digits.isdigit() or int(digits) not in chain:
        raise InvalidError(
            _("{item}'s usage die {die} isn't one of d4–d12", item=label, die=repr(die)),
            hint=_("e.g. d6"),
        )
    result = roll(die, f"usage die: {label}")
    change.rolled = result
    if result > USAGE_DOWN:
        change.notes.append(
            _(
                "{item}: usage die holds at {die} (rolled {result})",
                item=label,
                die=die,
                result=result,
            )
        )
        return die
    position = chain.index(int(digits))
    if position == 0:
        change.notes.append(
            _("{item}: usage die {die} rolled {result}", item=label, die=die, result=result)
        )
        return None
    smaller = f"d{chain[position - 1]}"
    change.notes.append(
        _(
            "{item}: usage die steps down to {die} (rolled {result})",
            item=label,
            die=smaller,
            result=result,
        )
    )
    return smaller


def _spent(bag: Bag, index: int, entry: dict[str, JSON], change: Change) -> bool:
    """The last use is gone: keep what recharges, start the next of a stack, drop the rest.
    True when none of it is left."""
    label = name_of(entry)
    if entry.get("recharge") or entry.get("keep"):
        bag.items[index] = _compact(entry)
        change.notes.append(_("{item} is spent until it recharges", item=label))
        return False
    count = count_of(entry)
    if count > 1:
        fresh = dict(entry)
        fresh[uses_key(entry)] = _full(entry.get(uses_key(entry)))
        bag.items[index] = with_count(_compact(fresh), count - 1)
        change.notes.append(
            ngettext(
                "one {item} is used up; {n} left",
                "one {item} is used up; {n} left",
                count - 1,
                item=label,
            )
        )
        return False
    bag.items.pop(index)
    change.notes.append(_("{item} is used up and gone", item=label))
    return True


def _full(uses: JSON) -> JSON:
    if isinstance(uses, dict):
        if isinstance(uses.get("max"), int):
            return {**uses, "value": uses["max"]}
        if isinstance(uses.get("full"), str):
            return {**uses, "die": uses["full"]}
    return uses


def recharge(
    cs: Changeset,
    located: Located,
    name: str,
    to: int | None = None,
    *,
    mode: sheets.Strictness = "strict",
) -> Change:
    """Refill uses to their max (or `to`); a usage die goes back to its full size."""

    def work(entity: Entity, bag: Bag, change: Change) -> None:
        index = find_item(bag, name)
        entry = _as_dict(bag.items[index])
        label = name_of(entry)
        key = uses_key(entry)
        uses = entry.get(key)
        if isinstance(uses, dict) and "die" in uses:
            die = f"d{to}" if to is not None else str(uses.get("full") or uses["die"])
            entry[key] = {**uses, "die": die}
            change.notes.append(_("{item}: usage die back to {die}", item=label, die=die))
        else:
            left, cap = _uses(uses, label) if uses is not None else (0, None)
            target = to if to is not None else cap
            if target is None:
                raise InvalidError(
                    _("{item} has no max uses", item=label), hint=_("say how many: --to 3")
                )
            entry[key] = {"value": target, "max": max(cap or target, target)}
            change.notes.append(
                _("{item}: {left} → {target} uses", item=label, left=left, target=target)
            )
        bag.items[index] = _compact(entry)
        change.item = bag.items[index]

    return _edit(cs, located, mode, False, work)


def set_key(
    entity: Entity,
    sh: Sheet,
    spec: kinds.FieldSpec,
    assignment: assign.Assignment,
    mode: sheets.Strictness,
) -> str | None:
    """A key of an item a slots field holds, set as `set` sets a field (`set freya
    inventory.sword.damage=d10`, a rule's `set: who.inventory.$item.charges`): the item named as
    `inv` names it, its uses or charges changed as a `uses` field's are (`charges+=2` stops at
    its max), and the item and the room checked as `inv add` checks them (`--force`: not the
    room). Returns a note."""
    path = assignment.path
    at = 2 if path[0] == "fields" else 3  # past the field: the item, then its keys
    bag = find_bag(entity, sh, spec.name)
    name, keys = item_keys(bag, path[at:])
    if not name:
        raise assign.invalid_key(assignment.key)
    if not keys:
        raise InvalidError(
            _("{item} is an item: set one of its keys", item=repr(name)),
            hint=_("e.g. {example}", example=f"`{spec.name}.{name}.damage=d10`"),
        )
    before = room(entity, sh, bag)
    counted = keys[0] in USE_KEYS and len(keys) == 1
    index = find_item(bag, name, usable=counted and assignment.op == "-=")  # spending: one left
    entry = _as_dict(bag.items[index])
    note: str | None = None
    try:
        if counted:  # counted down and refilled like `uses`
            uses = kinds.FieldSpec(keys[0], "uses")
            entry[keys[0]], note = kinds.change(
                uses, entry.get(keys[0]), assignment.op, assignment.value
            )
        else:
            assign.apply_nested(entry, keys, assignment)
        bag.items[index] = cast(list[JSON], kinds.coerce(spec, [cast(JSON, entry)]))[0]
    except kinds.FieldError as exc:
        raise InvalidError(
            str(exc), hint=_("see `didact template` for {name}'s format", name=spec.name)
        ) from exc
    _store(entity, bag)
    overfull = over(before, room(entity, sh, bag))
    if overfull and mode == "strict":
        raise InvalidError(
            _("{name} can't carry that: {over}", name=entity.name, over=", ".join(overfull)),
            hint=_("drop or move something first, or pass --force --reason '…'"),
        )
    if overfull and mode == "lenient":
        warning = _(
            "warning: {name} can't carry that: {over}", name=entity.name, over=", ".join(overfull)
        )
        note = f"{note}; {warning}" if note else warning
    return note


# ---------------------------------------------------------------------------- lookups


def item_data(repo: Repo, name: str) -> tuple[dict[str, JSON], str | None]:
    """An item as it will be stored, and where its details came from: an item record
    (`item:lantern`), a compendium entry of a type one carries, found as the compendium finds
    one (`compendium.locate`: its id, its name, or an alias), or neither: then what was
    written is the item's name, a `:` in it or not (`Series 1: Grit`)."""
    from didact.services import compendium, packs

    text = name.strip()
    if EntityId.looks_like(text.partition("@")[0]):  # a record: `item:lantern`
        entity = repo.resolve(text).entity
        details = {k: v for k, v in entity.fields.items() if k not in PROSE}
        return {"name": entity.name, **details, "ref": str(entity.id)}, str(entity.id)
    try:
        active = packs.active(repo)
    except DidactError:
        return {"name": text}, None
    try:
        entry = compendium.locate(active, text, kinds=carried_types(active))
    except NotFoundError:
        return {"name": text}, None
    details = {k: v for k, v in entry.data.items() if k not in compendium.ENTRY_CORE | PROSE}
    found = {"name": str(entry.data.get("name") or text), **details, "entry": entry.qualified}
    return found, entry.qualified


def carried_types(packs: PackSet) -> frozenset[str]:
    """The types one carries: the usual ones (`ITEM_TYPES`), and any type of the packs in play
    that `extends` one of them, as a perk magazine `extends: item`."""
    bases: dict[str, set[str]] = {}
    for kind in packs.all("type"):
        raw = kind.data.get("extends")
        if isinstance(raw, str) and raw:
            bases.setdefault(kind.id, set()).add(raw.replace("/", ".").rpartition(".")[2])
    found = set(ITEM_TYPES)
    grew = True
    while grew:  # a type extending a type that extends an item is one too
        grew = False
        for type_, parents in bases.items():
            if type_ not in found and parents & found:
                found.add(type_)
                grew = True
    return frozenset(found)


def carried(
    entity: Entity, sh: Sheet, field_name: str, path: str
) -> tuple[dict[str, JSON], tuple[str, ...]] | None:
    """One item a record's slots field holds and the keys asked of it, from the dotted path a
    rule reads (`@{who.inventory.$item.damage}` → `Iron Sword.damage`: the item named as `inv`
    names it, a dot in its name or not, `item_keys`); None when there's no such field or item."""
    bag = find_bag(entity, sh, field_name)
    if bag.spec.name != field_name:
        return None
    try:
        name, keys = item_keys(bag, path.split("."))
        return (_as_dict(bag.items[find_item(bag, name)]), keys) if name else None
    except InvalidError:  # not carried: absent, so `default(…)` gives its fallback
        return None


def lines(entity: Entity, sh: Sheet) -> list[str]:
    bag = find_bag(entity, sh)
    space = room(entity, sh, bag)
    out = [f"{entity.name} · {bag.spec.label}: {space.line()}"]
    occupying = space.used - sum(kinds.item_size(bag.spec, i) for i in bag.items)
    if bag.groups:
        for group in bag.groups:
            held = [i for i in bag.items if group_of(bag, i) == group]
            out.append(_("{group}: empty", group=group) if not held else f"{group}:")
            out.extend(f"- {describe_item(bag, i)}" for i in held)
        loose = [i for i in bag.items if group_of(bag, i) is None]
        if loose:
            out.append(_("in no group yet (they count as carried):"))
            out.extend(f"- {describe_item(bag, i)}" for i in loose)
    else:
        out.extend(f"- {describe_item(bag, i)}" for i in bag.items)
        if not bag.items:
            out.append(_("- nothing"))
    if occupying > 0:
        takers = [
            s.label
            for schema in sh.schemas
            for s in schema.fields.values()
            if s.kind == "counter" and s.opt("occupies") == bag.spec.name
        ]
        out.append(
            ngettext(
                "- also taken: {n} slot ({takers})",
                "- also taken: {n} slots ({takers})",
                occupying,
                takers=", ".join(takers),
            )
            if takers
            else ngettext(
                "- also taken: {n} slot (other fields)",
                "- also taken: {n} slots (other fields)",
                occupying,
            )
        )
    return out


def summary(entity: Entity, sh: Sheet) -> dict[str, JSON]:
    bag = find_bag(entity, sh)
    space = room(entity, sh, bag)
    groups: dict[str, JSON] = {k: {"used": u, "capacity": c} for k, (u, c) in space.groups.items()}
    return {
        "record": str(entity.id),
        "field": bag.spec.name,
        "used": space.used,
        "capacity": space.capacity,
        "groups": groups,
        "items": list[JSON](bag.items),
    }
