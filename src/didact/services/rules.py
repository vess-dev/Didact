"""Rules in the library: the engine's Host (records, rolls, tables, changes) and pending rolls."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from didact.core.errors import ConflictError, DidactError, InvalidError, NotFoundError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.expr import Registry
from didact.expr.model import Value, to_json
from didact.expr.render import collect_flags, parts, symbol_counts
from didact.packs.library import PackSet
from didact.rules.engine import (
    Engine,
    EntityDone,
    FieldSet,
    ItemDone,
    PoolDone,
    Resolver,
    RollDone,
    Rule,
    Run,
    TableDone,
    UseDone,
)
from didact.schema.fields import item_name
from didact.schema.sheet import Sheet, sheet_for
from didact.services import assign, dice, hooks, records, sheets, state, tables
from didact.services import packs as pack_service
from didact.services.trackers import Reminder
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Located, Repo

RULE_KINDS = ("check", "action", "procedure", "trigger")
PENDING = "pending"


def find_rule(packs: PackSet, ref: str, from_pack: str = "") -> Rule:
    """A rule of any kind by `pack.id` or bare id (the asking pack's first)."""
    text = ref.strip().replace("/", ".")
    candidates = [text] if "." in text or not from_pack else [f"{from_pack}.{text}", text]
    for candidate in candidates:
        found = []
        for kind in RULE_KINDS:
            try:
                found.append(packs.find(kind, candidate))
            except NotFoundError:
                continue
        if len(found) == 1:
            item = found[0]
            return Rule(item.kind, item.qualified, item.pack, item.data, item.source)
        if found:
            options = ", ".join(f"{i.kind} {i.qualified}" for i in found)
            raise ConflictError(
                _("{ref} names several rules: {options}", ref=repr(ref), options=options),
                hint=_("use pack.id"),
            )
    raise NotFoundError(
        _("no rule {ref} in {packs}", ref=repr(ref), packs=", ".join(packs.ids)),
        hint=_("see `didact rules list`"),
    )


def all_rules(packs: PackSet) -> list[Rule]:
    return [
        Rule(item.kind, item.qualified, item.pack, item.data, item.source)
        for kind in RULE_KINDS
        for item in packs.all(kind)
    ]


@dataclass(slots=True)
class LibraryHost:
    repo: Repo
    cs: Changeset
    packs: PackSet
    dry: bool
    command: str | None
    stream: str | None = None  # seeds every roll ("sim:1", "sim:2", …) instead of the log
    registry: Registry = field(init=False)
    _paths: dict[str, Path] = field(default_factory=dict)
    _drawn: int = 0
    _system: str | None = field(init=False)
    _sheets: dict[str, Sheet] = field(default_factory=dict)  # by record type
    _values: dict[str, dict[str, Value]] = field(default_factory=dict)  # by record, until a set
    _reminders: list[Reminder] | None = None  # the reminders as this run leaves them
    _options: dict[str, JSON] | None = None  # the campaign's options, read once
    _now: dict[str, Value] | None = None  # where play stands, read once
    _made: dict[str, Located] = field(default_factory=dict)  # records this run made, by id

    def __post_init__(self) -> None:
        self.registry = self.packs.registry()
        self._system = sheets.active_system(self.repo)

    def roll(
        self, expression: str, reason: str, resolve: Resolver, faces: list[int] | None = None
    ) -> RollDone:
        seed = None
        if self.stream is not None:  # a simulation: seeded, and never logged
            self._drawn += 1
            seed = f"{self.stream}:{self._drawn}"
        outcome = dice.roll(
            self.repo,
            expression,
            seed=seed,
            reason=reason,
            command=self.command,
            resolver=resolve,
            keep=faces,
            dry=self.dry or self.stream is not None,
            registry=self.registry,
        )
        result = outcome.rolled.result
        kept, all_faces = _dice(result)
        shown = outcome.line.removesuffix(f" — {reason}")  # the rule's header already says why
        tagged = {k: v for k, v in parts(result).items() if isinstance(v, int | float | str | bool)}
        return RollDone(
            outcome.label,
            shown,
            result.value,
            kept,
            all_faces,
            collect_flags(result),
            cast(dict[str, Value], tagged),
            symbol_counts(result),
        )

    def record(self, ref: str, of: str | None = None) -> str:
        if ref in self._made:  # not in the index until the change applies
            return ref
        located = self.repo.resolve(ref, of=of)
        record_id = str(located.entity.id)
        self._paths[record_id] = located.path
        return record_id

    def _located(self, record_id: str) -> Located:
        """A record as `record` finds it, one this run made too."""
        return self._made.get(record_id) or self.repo.resolve(record_id)

    def _entity(self, record_id: str) -> Entity:
        path = self._paths.get(record_id)
        if path is None:
            self.record(record_id)
            path = self._paths[record_id]
        return records.planned(self.cs, path)

    def _sheet(self, type_: str) -> Sheet:
        found = self._sheets.get(type_)
        if found is None:
            try:
                found = sheet_for(self.packs, self._system, type_)
            except DidactError:
                found = Sheet(type_, self._system)
            self._sheets[type_] = found
        return found

    def values(self, record_id: str) -> dict[str, Value]:
        found = self._values.get(record_id)
        if found is None:
            entity = self._entity(record_id)
            found = self._values[record_id] = sheets.entity_values(entity, self._sheet(entity.type))
        return found

    def set_field(self, record_id: str, key: str, op: str, value: Value) -> FieldSet:
        self._values.clear()  # what anything reads next comes fresh
        entity = self._entity(record_id)
        sheet = self._sheet(entity.type)
        mode = sheets.strictness(self.repo)
        notes: list[str] = []
        fired = hooks.Outcome()

        def change(target: Entity) -> None:
            before = sheets.entity_values(target, sheet)
            assignment = assign.Assignment(assign.parse_key(key), op, to_json(value), True)  # type: ignore[arg-type]
            note = sheets.apply(target, assignment, sheet, mode)
            if note:
                notes.append(note)
            fired.extend(hooks.settle(target, sheet, before, mode))

        records.edit(self.cs, self._paths[record_id], change)
        return FieldSet("; ".join([*notes, *fired.notes]) or None, tuple(fired.triggers))

    def unset_field(self, record_id: str, key: str) -> FieldSet:
        self._values.clear()  # what anything reads next comes fresh
        entity = self._entity(record_id)
        sheet = self._sheet(entity.type)
        mode = sheets.strictness(self.repo)
        notes: list[str] = []
        fired = hooks.Outcome()

        def change(target: Entity) -> None:
            before = sheets.entity_values(target, sheet)
            note = sheets.unset(target, key, sheet)
            if note:
                notes.append(note)
            fired.extend(hooks.settle(target, sheet, before, mode))

        records.edit(self.cs, self._paths[record_id], change)
        return FieldSet("; ".join([*notes, *fired.notes]) or None, tuple(fired.triggers))

    def make(self, spec: dict[str, JSON], rule: Rule) -> EntityDone:
        from didact.services import drafts

        mode = sheets.strictness(self.repo)
        located, new = drafts.make(self.cs, self.packs, spec, rule, mode)
        record_id = str(located.entity.id)
        self._paths[record_id] = located.path
        if new:
            self._made[record_id] = located
        return EntityDone(record_id, located.entity.name, new)

    def give(self, record_id: str, item: str, data: dict[str, JSON]) -> ItemDone:
        from didact.services import inventory

        self._values.clear()  # what anything reads next comes fresh
        found, source = inventory.item_data(self.repo, item)
        mode = sheets.strictness(self.repo)
        done = inventory.add(self.cs, self._located(record_id), found | data, mode=mode)
        notes = list(done.notes)
        if source:  # as `inv add` says where its details came from
            notes.insert(0, _("{item}: details from {source}", item=found["name"], source=source))
        return ItemDone(item_name(done.item), "; ".join(notes) or None, tuple(done.fired.triggers))

    def take(self, record_id: str, item: str, count: int | None) -> ItemDone:
        from didact.services import inventory

        self._values.clear()  # what anything reads next comes fresh
        mode = sheets.strictness(self.repo)
        done = inventory.remove(self.cs, self._located(record_id), item, count, mode=mode)
        note = "; ".join(done.notes) or None
        return ItemDone(item_name(done.item), note, tuple(done.fired.triggers))

    def use(self, record_id: str, item: str, spend: int) -> UseDone:
        """An item used as `inv use` uses it: a usage die rolled as the rule's rolls are."""
        from didact.services import inventory

        self._values.clear()  # what anything reads next comes fresh
        rolled: list[RollDone] = []

        def roll(expression: str, reason: str) -> int:
            done = self.roll(expression, reason, lambda _path: None)
            rolled.append(done)
            return int(done.total) if isinstance(done.total, int | float) else 0

        mode = sheets.strictness(self.repo)
        done = inventory.use(self.cs, self._located(record_id), item, spend, roll=roll, mode=mode)
        values: dict[str, Value] = {
            "out": done.out,
            "gone": done.gone,
            "left": done.left,
            "die": done.die,
            "rolled": done.rolled,
        }
        return UseDone(  # its notes say what the usage die rolled; the roll's label is kept
            inventory.name_of(done.item),
            "; ".join(done.notes) or None,
            tuple(r.label for r in rolled),
            tuple(done.fired.triggers),
            values,
        )

    def item(
        self, record_id: str, field: str, path: str
    ) -> tuple[dict[str, JSON], tuple[str, ...]] | None:
        from didact.services import inventory

        entity = self._entity(record_id)
        return inventory.carried(entity, self._sheet(entity.type), field, path)

    def oracle_state(self, rule: Rule) -> str | None:
        """The state of the oracle a rule belongs to, for its `oracle` parameter; None in a
        dry run before the oracle has started one (a dry run starts nothing)."""
        try:
            return _oracle_state(self.repo, self.packs, rule, dry=self.dry, command=self.command)
        except InvalidError:
            return None

    def remind(self, text: str, after: str | None, every: str | None) -> str:
        """A reminder when so much game time has passed (`didact remind … --in …`)."""
        from didact.services import play, timeline, trackers

        cal = timeline.calendar(self.repo)
        period = cal.parse(every) if every else None
        delay = cal.parse(after) if after else period
        if delay is None:
            raise InvalidError(
                _("a remind step needs `in:` or `every:`"),
                hint=_("e.g. `remind: '…'` with `in: 1 hour`"),
            )
        now = play.load(self.repo).seconds
        if self._reminders is None:  # read once: a run can set several
            self._reminders = trackers.reminders(self.repo)
        self._reminders.append(trackers.Reminder(text, now + delay, period))
        trackers.save_reminders(self.cs, list(self._reminders))
        return _("reminder set for {time}: {text}", time=cal.describe(now + delay), text=text)

    def pool(self, record_id: str, *, roll: bool, drop: int, extra: int, reason: str) -> PoolDone:
        from didact.services import trackers

        self._values.clear()  # what anything reads next comes fresh
        done = trackers.roll_pool(
            self.cs, self._located(record_id), drop=drop, extra=extra, command=self.command,
            dry=self.dry, roll=roll,
        )  # fmt: skip
        values: dict[str, Value] = {
            "highest": done.highest or 0,
            "dropped": done.dropped,
            "left": done.left,
            "empty": done.empty,
            "faces": list[Value](done.faces),
        }
        return PoolDone(list(done.lines), list(done.rolls), values)

    def table(self, ref: str, inputs: dict[str, Value], reason: str) -> TableDone:
        seed = None
        if self.stream is not None:
            self._drawn += 1
            seed = f"{self.stream}:{self._drawn}"
        outcome = tables.roll_table(
            self.repo,
            ref,
            inputs=inputs,
            seed=seed,
            reason=reason,
            command=self.command,
            dry=self.dry or self.stream is not None,
            packs=self.packs,
        )
        first = outcome.results[0]
        path = [list[Value](step) for step in first.path()] if first.onward else []
        return TableDone(outcome.label, first.text, first.carried(), list[Value](path))

    def rule(self, ref: str, from_pack: str) -> Rule:
        return find_rule(self.packs, ref, from_pack)

    def settings(self, pack: str) -> dict[str, JSON]:
        return self.packs.settings(pack)

    def option(self, name: str) -> JSON:
        if self._options is None:
            from didact.services import options

            self._options = options.resolved(self.repo)
        if name in self._options:
            return self._options[name]
        return self._options.get(name.replace("_", "-"))  # `@option.rest_resets`: rest-resets

    def now(self) -> dict[str, Value]:
        if self._now is None:
            from didact.services import events

            self._now = events.now(self.repo)
        return self._now

    def party(self, pcs: bool) -> list[str]:
        from didact.services import party

        members = party.members(self.repo, gm=True)
        return [str(m.entity.id) for m in members if not pcs or m.role == "pc"]


def _dice(result: object) -> tuple[list[int], list[int]]:
    from didact.expr.engine import PoolResult
    from didact.expr.render import walk

    kept: list[int] = []
    faces: list[int] = []
    for node in walk(result):  # type: ignore[arg-type]
        if isinstance(node, PoolResult):
            for die in node.pool.dice:
                faces.append(die.face)
                if die.kept:
                    kept.append(die.value)
    return kept, faces


def run_hooks(
    repo: Repo, cs: Changeset, record: str, fired: hooks.Outcome, *, dry: bool, command: str | None
) -> list[str]:
    """Run the triggers field hooks fired for `record`; returns their lines and prompts."""
    if not fired.triggers:
        return []
    packs = pack_service.active(repo)
    host = LibraryHost(repo, cs, packs, dry, command)
    lines: list[str] = []
    for ref in fired.triggers:
        try:
            rule = find_rule(packs, ref)
        except NotFoundError:
            lines.append(
                _("hook: there's no rule {ref} to run (see the sheet's hooks)", ref=repr(ref))
            )
            continue
        args = {"who": record} if "who" in rule.params else {}
        result = Engine(host).run(rule, args, depth=1, preset={"hook.record": record})
        lines.extend(result.lines)  # its prompts among them
    return lines


def run(
    repo: Repo, cs: Changeset, ref: str, args: dict[str, str], *, dry: bool, command: str | None
) -> tuple[Rule, Run]:
    packs = pack_service.active(repo)
    host = LibraryHost(repo, cs, packs, dry, command)
    rule = find_rule(packs, ref)
    if "oracle" in rule.params and "oracle" not in args:  # an oracle's rules read its state
        args = {**args, "oracle": _oracle_state(repo, packs, rule, dry=dry, command=command)}
    result = Engine(host).run(rule, args)
    if result.options and not dry:
        key = result.rolls[0].lstrip("#") if result.rolls else rule.id
        saved = state.load(repo, PENDING)
        saved[key] = {
            "rule": rule.id,
            "texts": dict(_texts(rule, result)),
            "params": {k: to_json(v) for k, v in result.params.items()},
            "bound": {k: to_json(v) for k, v in result.bound.items()},
            "records": dict[str, JSON](result.records),
            "faces": {k: list[JSON](v) for k, v in result.faces.items()},
            "exprs": dict[str, JSON](result.exprs),
            "rolls": list[JSON](result.rolls),
            "options": dict[str, JSON](result.options),
        }
        state.plan(cs, PENDING, saved)
    return rule, result


def _oracle_state(repo: Repo, packs: PackSet, rule: Rule, *, dry: bool, command: str | None) -> str:
    """The state record of the oracle a rule belongs to (its pack's), else the campaign's."""
    from didact.services import oracles

    own = [o for o in packs.all("oracle") if o.pack == rule.pack]
    chosen = own[0] if own else oracles.pick(repo, None)
    found = oracles.ensure_state(repo, chosen, dry=dry, command=command, force=True)
    assert found is not None  # forced
    return found


def _texts(rule: Rule, result: Run) -> dict[str, JSON]:
    return {k: (v if isinstance(v, str) else str(to_json(v))) for k, v in result.params.items()}


def resolve(
    repo: Repo, cs: Changeset, key: str, option: str, *, command: str | None
) -> tuple[Rule, Run]:
    saved = state.load(repo, PENDING)
    wanted = key.lstrip("#")
    entry = saved.get(wanted)
    if not isinstance(entry, dict):
        waiting = ", ".join(f"#{k}" for k in saved) or _("none")
        raise NotFoundError(
            _("no pending roll {key}", key=key), hint=_("pending: {waiting}", waiting=waiting)
        )
    packs = pack_service.active(repo)
    host = LibraryHost(repo, cs, packs, False, command)
    rule = find_rule(packs, str(entry.get("rule")))
    try:
        result = Engine(host).resolve(rule, entry, option)
    except DidactError:
        raise
    del saved[wanted]
    state.plan(cs, PENDING, saved)
    return rule, result


def pending(repo: Repo) -> dict[str, JSON]:
    return state.load(repo, PENDING) if repo.active_world() is not None else {}
