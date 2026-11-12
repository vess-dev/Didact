"""Drafts in the library: generators and character creation build them; `commit` writes them.

    gen run my-system.region            → draft #g7 (nothing written yet)
    gen show g7 / gen choose g7 … / gen edit g7 poi-1.name='Amber Grave'
    gen commit g7                        → records, links and the map, in one change

Drafts are state files (`state/drafts/g7.yaml`) written through changesets, so running,
answering, editing and committing are each logged and undoable. Every roll is a logged roll.
A draft remembers its trail (every value rolled or chosen, in order): answering an open choice
replays the procedure with the trail, so nothing is rolled twice.

A chargen procedure with `advances: <type>` changes a record instead (a level-up: `char
advance <pc>`): the draft starts from a copy of the record, its steps read the record as
`@who`, and committing writes what changed to it.
"""

import json
from dataclasses import dataclass, field
from typing import cast

from didact.core import labels
from didact.core.clock import now_iso
from didact.core.errors import DidactError, InvalidError, NotFoundError
from didact.core.i18n import N_, _, ngettext
from didact.core.ids import EntityId, Scope
from didact.core.output import JSON
from didact.core.phrases import Phrase, phrase
from didact.core.phrases import shown as shown_phrase
from didact.expr.model import Value, from_json, to_json
from didact.packs.library import Item, PackSet
from didact.rules import drafts as engine_drafts
from didact.rules.drafts import Draft, DraftEntity
from didact.rules.engine import Engine, Rule, answered
from didact.schema.sheet import Sheet
from didact.services import assign, counters, packs, records, rules, sheets, state, tables
from didact.store import frontmatter
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.events import SAY, Event, undone_seqs
from didact.store.events import shown as shown_event
from didact.store.repo import Located, Repo
from didact.tables.engine import MAX_DEPTH, FindTable
from didact.tables.model import Entry, Table
from didact.tables.model import about as table_about

PREFIX = {"generator": "g", "chargen": "c"}


ROUTE_KEYS = ("distance", "watches", "hidden", "type", "details")  # kept on the place


@dataclass(slots=True)
class Stored:
    id: str  # g7, c3
    kind: str  # generator | chargen
    source: str  # the pack item, qualified
    params: dict[str, str] = field(default_factory=dict)
    prefill: dict[str, JSON] = field(default_factory=dict)
    auto: bool = False
    trail: list[tuple[str, Value]] = field(default_factory=list)
    draft: Draft = field(default_factory=Draft)
    prompts: list[str] = field(default_factory=list)
    rolls: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    waiting: str | None = None
    created: str = ""
    target: str | None = None  # the record an advancement changes
    base: dict[str, JSON] = field(default_factory=dict)  # its fields when the draft last ran

    def to_data(self) -> dict[str, JSON]:
        open_choice = self.draft.open.to_data() if self.draft.open is not None else None
        return {
            "id": self.id,
            "kind": self.kind,
            "source": self.source,
            "params": dict[str, JSON](self.params),
            "prefill": self.prefill,
            "auto": self.auto,
            "trail": [[name, to_json(value)] for name, value in self.trail],
            "entities": [e.to_data() for e in self.draft.entities],
            "counters": dict[str, JSON](self.draft.counters),
            "open": open_choice,
            "map": self.draft.map,
            "prompts": list[JSON](self.prompts),
            "rolls": list[JSON](self.rolls),
            "lines": list[JSON](self.lines),
            "waiting": self.waiting,
            "created": self.created,
            **({"target": self.target, "base": self.base} if self.target else {}),
        }

    @classmethod
    def from_data(cls, data: dict[str, JSON]) -> Stored:
        draft = Draft(auto=bool(data.get("auto")))
        draft.entities = [
            DraftEntity.from_data(e) for e in cast(list[JSON], data.get("entities") or [])
            if isinstance(e, dict)
        ]  # fmt: skip
        raw_counters = data.get("counters")
        if isinstance(raw_counters, dict):
            draft.counters = {str(k): int(cast(int, v)) for k, v in raw_counters.items()}
        raw_open = data.get("open")
        if isinstance(raw_open, dict):
            draft.open = engine_drafts.Choice.from_data(raw_open)
        raw_map = data.get("map")
        draft.map = raw_map if isinstance(raw_map, dict) else {}
        trail: list[tuple[str, Value]] = []
        for pair in cast(list[JSON], data.get("trail") or []):
            if isinstance(pair, list) and len(pair) == 2:
                value = from_json(pair[1])
                if value is not None:
                    trail.append((str(pair[0]), value))
        params = data.get("params")
        prefill = data.get("prefill")
        waiting = data.get("waiting")
        target = data.get("target")
        base = data.get("base")
        return cls(
            str(data["id"]),
            str(data["kind"]),
            str(data["source"]),
            {str(k): str(v) for k, v in params.items()} if isinstance(params, dict) else {},
            dict(prefill) if isinstance(prefill, dict) else {},
            bool(data.get("auto")),
            trail,
            draft,
            [str(p) for p in cast(list[JSON], data.get("prompts") or [])],
            [str(r) for r in cast(list[JSON], data.get("rolls") or [])],
            [str(line) for line in cast(list[JSON], data.get("lines") or [])],
            str(waiting) if isinstance(waiting, str) else None,
            str(data.get("created") or ""),
            str(target) if isinstance(target, str) else None,
            dict(base) if isinstance(base, dict) else {},
        )


# ---------------------------------------------------------------------------- storing


def _name(draft_id: str) -> str:
    return f"drafts/{draft_id}"


def load(repo: Repo, draft_id: str) -> Stored:
    wanted = draft_id.strip().lstrip("#").lower()
    data = state.load(repo, _name(wanted))
    if not data:
        raise NotFoundError(_("no draft #{draft}", draft=wanted), hint=_("see `didact gen drafts`"))
    return Stored.from_data(data)


def save(cs: Changeset, stored: Stored) -> None:
    state.plan(cs, _name(stored.id), stored.to_data())


def listing(repo: Repo) -> list[Stored]:
    folder = state.state_path(repo, "drafts/x").parent
    if not folder.is_dir():
        return []
    found: list[Stored] = []
    for path in sorted(folder.glob("*.yaml")):
        try:
            found.append(load(repo, path.stem))
        except DidactError:
            continue
    return found


# ---------------------------------------------------------------------------- running


def items(repo: Repo, kind: str) -> list[Item]:
    return list(packs.active(repo).all(kind))


def start(
    cs: Changeset,
    kind: str,
    ref: str,
    params: dict[str, str],
    prefill: dict[str, JSON],
    *,
    auto: bool,
    dry: bool,
    command: str | None,
    keep: bool = True,
    target: str | None = None,
) -> Stored:
    """Run a generator or chargen into a new draft (`keep=False`: don't save it, e.g. to
    commit it in the same change). `target`: the record an advancement changes."""
    item = packs.active(cs.repo).find(kind, ref)
    modes = item.data.get("modes")
    if auto and isinstance(modes, list) and "random" not in modes:
        raise InvalidError(
            _("{source} goes step by step: the dice can't answer it all", source=item.qualified),
            hint=_("leave out --mode random (answer each question, or `roll` one at a time)"),
        )
    if target is not None:
        params = {**params, "who": target}
    number = 0 if dry or not keep else counters.next_number(cs.repo, "drafts")
    stored = Stored(f"{PREFIX[kind]}{number or '?'}", kind, item.qualified, params, prefill, auto)
    stored.created = now_iso()
    stored.target = target
    return run(cs, stored, dry=dry, command=command, keep=keep)


def creations(repo: Repo) -> list[Item]:
    """The character creations here (a chargen with `advances:` changes a record instead)."""
    return [c for c in items(repo, "chargen") if "advances" not in c.data]


def advancement(repo: Repo, type_: str) -> Item | None:
    """The system's way to advance a record of this type (`advances: <type>`), if it has one."""
    found = [c for c in items(repo, "chargen") if c.data.get("advances") == type_]
    system = sheets.active_system(repo)
    found.sort(key=lambda c: c.pack != system)  # the system's own first
    return found[0] if found else None


def flat_fields(entity: Entity, sh: Sheet) -> dict[str, JSON]:
    """A record's fields as a draft holds them: Didact's own and the system's, side by side,
    with the sheet's defaults for those not written down (a level 1 nobody set; an empty list
    to add to)."""
    block = entity.mechanics.get(sh.system) if sh.system else None
    merged = {**entity.fields, **(block if isinstance(block, dict) else {})}
    for schema in sh.schemas:
        for spec in schema.fields.values():
            default = spec.opt("default", [] if spec.kind == "list" else None)
            if spec.name not in merged and default is not None and spec.kind != "derived":
                merged[spec.name] = default
    return cast(dict[str, JSON], json.loads(json.dumps(merged)))  # a copy of its own


def run(
    cs: Changeset,
    stored: Stored,
    *,
    dry: bool,
    command: str | None,
    keep: bool = True,
    once: bool = False,
) -> Stored:
    """Run (or replay and continue) the procedure into the draft, then save the draft.
    `once`: the dice make the first open choice, and the run stops at the next one."""
    repo = cs.repo
    active = packs.active(repo)
    item = active.find(stored.kind, stored.source)
    rule = Rule(stored.kind, item.qualified, item.pack, item.data, item.source)
    find = tables.finder(active)

    def options(table: str) -> list[str]:
        """Each entry once: a table printed in columns repeats one over several rolls."""
        return list(dict.fromkeys(e.text for e in find(table, item.pack).entries if e.text))

    def entry_data(table: str, text: str, path: Value | None = None) -> dict[str, JSON] | None:
        """An entry's data, by its text; a roll that went on to other tables (its `path`:
        each entry it took, as [table, entry]) brings theirs too, as it did when rolled."""
        if isinstance(path, list):
            data: dict[str, JSON] = {}
            for step in path:
                taken = entry_at(step)
                for key, value in (taken.data if taken is not None else {}).items():
                    data.setdefault(key, value)
            return data
        for entry in find(table, item.pack).entries:
            if entry.text == text:
                return entry.data
        return None

    def entry_at(step: Value) -> Entry | None:
        """The entry a path's step names, as [table, entry] (None: it isn't there any more)."""
        if not isinstance(step, list) or len(step) != 2:
            return None
        try:
            found = find(str(step[0]), item.pack)
        except DidactError:
            return None
        return next((e for e in found.entries if e.label == step[1]), None)

    def prefilled(table: str, name: str, value: Value) -> tuple[Value, Value | None]:
        """A value prefilled for a table's entry, as that entry (`answered`): by its text, its
        data's `id`, a roll that lands on it, or an entry further down, at any depth, of a table
        an entry goes on to (one it rolls instead, or `then:`), with the path a roll would have
        taken (`_further`); one close to any of them but none is refused, naming the nearest."""
        found = find(table, item.pack)
        if found.lookup or found.columns:  # read or put together, not an entry: as given
            return value, None
        texts = list(dict.fromkeys(e.text for e in found.entries if e.text))
        text = str(value)
        if text.casefold() in {t.casefold() for t in texts}:
            return answered(name, value, texts), None
        named = next((e for e in found.entries if e.data.get("id") == value), None)
        if named is None and text.isdigit():  # a roll: the entry it lands on
            named = found.landing(int(text))
            if named is None:
                low, high = (
                    (1, sum(e.weight for e in found.entries)) if found.weighted else found.span()
                )
                raise InvalidError(
                    _(
                        "prefilled {name} {value} isn't one of its options",
                        name=name,
                        value=repr(text),
                    ),
                    hint=_(
                        "give one of its entries, or a roll from {low} to {high}",
                        low=low,
                        high=high,
                    ),
                )
            if not named.text and named.table:
                raise InvalidError(
                    _(
                        "prefilled {name} {value} rolls on {table}",
                        name=name,
                        value=repr(text),
                        table=named.table,
                    ),
                    hint=_("prefill one of its entries instead"),
                )
        if named is not None:
            return named.text, None
        taken, path, nearby = _further(found, text, value, find)
        if taken is not None:
            return taken.text, path
        return answered(name, value, list(dict.fromkeys([*texts, *nearby]))), None

    def onward(
        table: str, text: str, label: str | None = None
    ) -> tuple[Value, list[str], list[str]] | None:
        """A chosen entry that goes on (`then:`, or a table instead) rolls on now, as a roll
        landing on it would: the path it took, the log line and the roll's label. The entry by
        its text, or by its `label` (one a prefill found further down). None: it doesn't go on,
        or isn't there."""
        found = find(table, item.pack)
        entry = next(
            (
                e
                for e in found.entries
                if e.text and (e.label == label if label else e.text == text)
            ),
            None,
        )
        if entry is None or not _onward(entry):
            return None
        outcome = tables.roll_table(
            repo, found.id, entry=entry.label, reason=item.qualified, command=command,
            dry=dry, packs=active,
        )  # fmt: skip
        first = outcome.results[0]
        path = list[Value](list[Value](step) for step in first.path())
        return path, outcome.lines(), [outcome.label]

    def compendium_entry(ref: str) -> dict[str, JSON] | None:
        return _start(active, item.pack, ref)

    def records_of(type_: str) -> list[str]:
        """The records of a type here, by id (`records:` in a choice)."""
        return [row.id for row in repo.index().rows(repo.chain(), types=[type_])]

    entries: dict[str, dict[str, JSON]] = {}  # the compendium, by `pack.id` and by bare id
    alone: dict[str, list[dict[str, JSON]]] = {}

    def entry_named(ref: str) -> dict[str, JSON] | None:
        """The compendium entry an option or a table entry names, as its pack wrote it: by
        `pack.id`, by an id in the procedure's own pack, or by an id only one pack has."""
        if not entries:
            for found in active.all("entry"):
                entries[found.qualified] = found.data
                alone.setdefault(found.id, []).append(found.data)
        if "." in ref:
            return entries.get(ref)
        mine = entries.get(f"{item.pack}.{ref}")
        if mine is not None:
            return mine
        others = alone.get(ref, [])
        return others[0] if len(others) == 1 else None

    def option_notes(table: str, offered: list[str]) -> tuple[dict[str, str], dict[str, str]]:
        """What each option means, and the names of options that are ids: a table entry's
        note or its table's `about:`, else the compendium entry it names (its data's `id:`),
        or the one the option itself is (a talent's id)."""
        about: dict[str, str] = {}
        labels: dict[str, str] = {}
        if table:
            found = find(table, item.pack)
            for entry in found.entries:
                if entry.text not in offered or entry.text in about:
                    continue
                ref = entry.data.get("id")
                said = table_about(found, entry) or (
                    summary(entry_named(ref)) if isinstance(ref, str) else ""
                )
                if said:
                    about[entry.text] = said
        for option in offered:
            data = entry_named(option) if option not in about else None
            if data is None:
                continue
            name = data.get("name")
            if isinstance(name, str) and name.strip() and name != option:
                labels[option] = name
            said = summary(data)
            if said:
                about[option] = said
        return about, labels

    draft = Draft(auto=stored.auto, once=once)
    preset: dict[str, Value] = {}
    if stored.target is not None:  # an advancement starts from the record as it is now
        record = repo.resolve(stored.target).entity
        stored.base = flat_fields(record, sheets.sheet(repo, record.type))
        main = engine_drafts.DraftEntity(engine_drafts.MAIN, record.type, record.name)
        main.fields = cast(dict[str, JSON], json.loads(json.dumps(stored.base)))
        draft.entities.append(main)
        for key, value in stored.base.items():
            shown = from_json(value)
            if shown is not None:
                preset[f"character.{key}"] = shown
    host = rules.LibraryHost(repo, cs, active, dry, command)
    given = engine_drafts.given_from(stored.trail, stored.prefill)
    extra: dict[str, object] = {
        "draft": draft,
        "table_options": options,
        "entry_data": entry_data,
        "prefilled": prefilled,
        "onward": onward,
        "compendium": compendium_entry,
        "records_of": records_of,
        "option_notes": option_notes,
    }
    result = Engine(host, engine_drafts.HANDLERS).run(
        rule, stored.params, preset=preset, given=given, extra=extra
    )
    if result.stopped is not None and draft.open is None:  # a `stop:` step: not here, not now
        if stored.target is not None:
            hint = _("nothing changed: advance it again when it can")
        elif result.stopped_by_option:  # it sat under an `if:` reading a campaign option
            hint = _(
                "nothing was drafted: change what stopped it (the campaign's options: "
                "`didact session zero`), then run it again"
            )
        else:
            hint = _("nothing was drafted: it stops here, for the reason it gives")
        raise InvalidError(result.stopped, hint=hint)
    creates = item.data.get("creates")
    for entity in draft.entities:
        if entity.key == engine_drafts.MAIN and isinstance(creates, str) and not stored.target:
            entity.type = creates
    stored.trail = list(result.trail)
    stored.draft = draft
    stored.prompts = list(result.prompts)
    stored.rolls = [*stored.rolls, *result.rolls]
    stored.lines = list(result.lines)
    stored.waiting = draft.open.name if draft.open is not None else None
    if keep and not dry:
        save(cs, stored)
    return stored


def _onward(entry: Entry) -> list[str]:
    """The tables an entry goes on to: the one it rolls instead, then its `then:` tables."""
    found = [entry.table] if entry.table else []
    for step in entry.then:
        if isinstance(step, str):
            found.append(step)
        elif isinstance(step, dict) and isinstance(step.get("table"), str):
            found.append(str(step["table"]))
    return found


def _further(
    top: Table, text: str, value: Value, find: FindTable
) -> tuple[Entry | None, Value | None, list[str]]:
    """An entry a prefill names further down a table, at any depth (by its text in any letter
    case, or its data's `id`), and the path a roll would have taken to it, as [table, entry].
    The nearest is meant: the fewest steps down, then the first in the tables' order. Only as
    deep as a roll goes (`MAX_DEPTH`), and each table once, so tables that go on to each other
    in a ring end. Not found: the texts of every table on the way, for the nearest miss."""
    folded = text.casefold()
    reached = {top.id}
    level: list[tuple[list[Value], Table]] = [([], top)]
    nearby: list[str] = []
    for _depth in range(MAX_DEPTH):
        deeper: list[tuple[list[Value], Table]] = []
        for steps, table in level:
            for entry in table.entries:
                for onward in _onward(entry):
                    try:
                        inner = find(onward, table.pack)
                    except DidactError:
                        continue
                    if inner.id in reached:  # reached nearer, or earlier at this depth
                        continue
                    reached.add(inner.id)
                    way = [*steps, list[Value]([table.id, entry.label])]
                    taken = next(
                        (
                            e
                            for e in inner.entries
                            if e.text.casefold() == folded or e.data.get("id") == value
                        ),
                        None,
                    )
                    if taken is not None:
                        return taken, list[Value]([*way, [inner.id, taken.label]]), nearby
                    nearby += [e.text for e in inner.entries if e.text]
                    deeper.append((way, inner))
        level = deeper
    return None, None, nearby


def _start(active: PackSet, pack: str, ref: str) -> dict[str, JSON] | None:
    """An entity's start (`entity: {from: …}`): the compendium entry as `spawn` makes it. A bare
    id is looked for in the asking pack first."""
    from didact.services import compendium

    for wanted in ([f"{pack}.{ref}"] if "." not in ref else []) + [ref]:
        try:
            found = active.find("entry", wanted)
        except DidactError:
            continue
        return {"type": found.data.get("type"), **compendium.record_data(found)}
    return None


def summary(data: dict[str, JSON] | None) -> str:
    """A compendium entry in a sentence or two: its tagline and summary, its description or
    its effect, else its text's first paragraph."""
    if not data:
        return ""
    said = " ".join(
        str(data[key]).strip()
        for key in ("tagline", "summary")
        if isinstance(data.get(key), str) and str(data[key]).strip()
    )
    for key in ("description", "effect", "body"):
        if said:
            break
        text = data.get(key)
        if not isinstance(text, str):
            continue
        for part in text.split("\n\n"):
            line = " ".join(part.split())
            if line and not line.startswith((">", "#", "|", "- ", "* ")):
                said = line
                break
    return said


def choose(cs: Changeset, stored: Stored, value: str, *, dry: bool, command: str | None) -> Stored:
    """Answer the draft's open choice and carry on from there."""
    choice = stored.draft.open
    if choice is None:
        raise InvalidError(
            _("#{draft} isn't waiting for a choice", draft=stored.id),
            hint=_("commit it, or edit it"),
        )
    if not value.strip():
        verb = "char" if stored.kind == "chargen" else "gen"
        raise InvalidError(
            _("{choice} needs an answer", choice=choice.name),
            hint=_("`didact {verb} choose {draft} <value>`", verb=verb, draft=stored.id),
        )
    if choice.options and value not in choice.options and not choice.pick:  # picks: on replay
        matches = [o for o in choice.options if o.casefold() == value.casefold()]
        if matches:
            value = matches[0]
        elif not choice.free:  # a name can be one of the options, or your own
            raise InvalidError(
                _(
                    "{choice} is one of: {options}",
                    choice=choice.name,
                    options=", ".join(choice.options[:20]),
                ),
                hint=_("not {value}", value=repr(value)),
            )
    stored.trail.append((choice.name, _typed(value)))
    return run(cs, stored, dry=dry, command=command)


def _typed(text: str) -> Value:
    return int(text) if text.lstrip("-").isdigit() else text


def roll_open(
    cs: Changeset, stored: Stored, *, dry: bool, command: str | None, one: bool = False
) -> Stored:
    """Let the dice make the open choice and any later ones (`one`: that choice only)."""
    choice = stored.draft.open
    if choice is not None and not choice.dice:
        verb = "char" if stored.kind == "chargen" else "gen"
        raise InvalidError(
            _("there's nothing to roll {choice} from", choice=choice.name),
            hint=_("give it: `didact {verb} choose {draft} <value>`", verb=verb, draft=stored.id),
        )
    if one:
        return run(cs, stored, dry=dry, command=command, once=True)
    stored.auto = True
    return run(cs, stored, dry=dry, command=command)


# ---------------------------------------------------------------------------- going back


@dataclass(frozen=True, slots=True)
class Step:
    """A draft's last step, as the history has it: the change that took it (an answer, a roll
    or an edit), and the rolls it made that still stand."""

    event: Event
    rolls: tuple[Event, ...]


def last_step(repo: Repo, stored: Stored) -> Step:
    """The step `back` takes back: the newest change still in effect that wrote the draft,
    when it was one of the draft's own steps (its commands name the draft in what they log).

    The change that started the draft isn't a step to go back over (discarding it is), and
    another change that wrote it (a rewind, a rename) is the history's to undo."""
    path = repo.layout.rel(state.state_path(repo, _name(stored.id)))
    verb = "char" if stored.kind == "chargen" else "gen"
    events = repo.log.all()
    undone = undone_seqs(events)
    for event in reversed(events):
        if event.kind != "change" or event.seq in undone:
            continue
        change = next((f for f in event.files if f.path == path), None)
        if change is None:
            continue
        if not _of_draft(event, stored.id):
            raise InvalidError(
                _(
                    "#{draft} last changed with {event} ({summary}), not one of its own steps",
                    draft=stored.id,
                    event=event.label,
                    summary=shown_event(event),
                ),
                hint=_(
                    "undo that from the history if you mean to: `didact undo --event e{n}`",
                    n=event.seq,
                ),
            )
        if change.before is None:
            raise InvalidError(
                _("#{draft} is at its first step: there's nothing to go back to", draft=stored.id),
                hint=_(
                    "to start again, discard it: `didact {verb} discard {draft}`",
                    verb=verb,
                    draft=stored.id,
                ),
            )
        made = _rolls_in(change.after) - _rolls_in(change.before)
        rolls = tuple(
            e
            for e in events
            if e.kind == "roll" and e.seq not in undone and f"#r{e.data.get('roll')}" in made
        )
        return Step(event, rolls)
    raise InvalidError(
        _("#{draft}'s earlier steps aren't in the history any more", draft=stored.id),
        hint=_(
            "the history was cleared since: to start again, discard it: "
            "`didact {verb} discard {draft}`",
            verb=verb,
            draft=stored.id,
        ),
    )


def _of_draft(event: Event, draft_id: str) -> bool:
    """Whether a change was one of a draft's own steps: what it logged names the draft."""
    said = event.data.get(SAY)
    values = said.get("values") if isinstance(said, dict) else None
    return isinstance(values, dict) and values.get("draft") == draft_id


def _rolls_in(text: str | None) -> set[str]:
    """The rolls a draft's saved text lists (`#r12`)."""
    if not text:
        return set()
    try:
        data = frontmatter.to_plain(frontmatter.load(text, where="draft"))
    except DidactError:
        return set()
    found = data.get("rolls") if isinstance(data, dict) else None
    return {str(r) for r in found} if isinstance(found, list) else set()


def back(repo: Repo, step: Step, *, reason: str | None, command: str | None) -> list[Event]:
    """Take a draft's last step back: undo its change, and mark the rolls it made undone."""
    from didact.services.dice import void_roll
    from didact.store import changeset as changesets

    done = [changesets.undo(repo, step.event, reason=reason, command=command)]
    done += [void_roll(repo, roll, reason=reason, command=command) for roll in step.rolls]
    return done


# ---------------------------------------------------------------------------- editing


def edit(
    stored: Stored, changes: list[str], drop: list[str], add: list[dict[str, JSON]]
) -> list[Phrase]:
    """`key.field=value`, `key.name=…`, dropping and adding entities. Returns what changed."""
    draft = stored.draft
    done: list[Phrase] = []
    for text in changes:
        left, sep, raw = text.partition("=")
        key, dot, path = left.strip().partition(".")
        if not sep or not dot or not path:
            raise InvalidError(
                _("can't read {text}", text=repr(text)),
                hint=_("use key.field=value, e.g. poi-1.name='Amber Grave'"),
            )
        entity = draft.get(key)
        value = assign.parse_value(raw)
        if path == "name":
            entity.name = str(value)
        elif path == "body":
            entity.body = str(value)
        elif path == "type":
            entity.type = str(value)
        else:
            target: dict[str, JSON] = entity.fields
            parts = path.removeprefix("fields.").split(".")
            for part in parts[:-1]:
                nested = target.setdefault(part, {})
                if not isinstance(nested, dict):
                    raise InvalidError(
                        _("{key}.{part} isn't a group of fields", key=key, part=part),
                        hint=_("set it as a whole: `{key}.fields.{part}=…`", key=key, part=part),
                    )
                target = nested
            target[parts[-1]] = value
        done.append(phrase(N_("{key}.{path} = {value}"), key=key, path=path, value=raw.strip()))
    for key in drop:
        entity = draft.get(key)
        draft.entities.remove(entity)
        for other in draft.entities:
            other.links = [link for link in other.links if link.get("to") != key]
        done.append(phrase(N_("dropped {key}"), key=key))
    for data in add:
        type_ = str(data.get("type") or "note")
        key = draft.next_key(type_)
        fields = {k: v for k, v in data.items() if k not in ("type", "name", "body")}
        draft.entities.append(
            DraftEntity(
                key, type_, str(data.get("name") or key), fields, str(data.get("body") or "")
            )
        )
        done.append(phrase(N_("added {key}"), key=key))
    return done


# ---------------------------------------------------------------------------- committing


def commit(cs: Changeset, stored: Stored, *, force: bool, saved: bool = True) -> list[str]:
    """Write the draft: records (checked against their sheets), links and routes. Returns ids."""
    if stored.draft.open is not None:
        verb = "char" if stored.kind == "chargen" else "gen"
        raise InvalidError(
            _(
                "#{draft} is waiting for {choice}",
                draft=stored.id,
                choice=stored.draft.open.name,
            ),
            hint=_("answer it: `didact {verb} choose {draft} <value>`", verb=verb, draft=stored.id),
        )
    repo = cs.repo
    mode: sheets.Strictness = "freeform" if force else sheets.strictness(repo)
    ids: dict[str, str] = {}
    made: list[str] = []
    if stored.target is not None:  # the record changes; anything else the draft made is new
        ids[engine_drafts.MAIN] = stored.target
        made.append(stored.target)
    for item in stored.draft.entities:  # ids first: fields and links may name other entities
        if item.key in ids:
            continue
        if not item.name.strip():
            raise InvalidError(
                _("{key} has no name", key=item.key),
                hint=_("`… edit {draft} {key}.name='…'`", draft=stored.id, key=item.key),
            )
        ids[item.key] = str(_free_id(repo, item.type, item.name, set(ids.values())))
    named = _named(stored, ids)  # what a field or a link naming a key becomes
    if stored.target is not None and not _advance(cs, stored, mode, named) and len(ids) == 1:
        raise InvalidError(
            _("#{draft} changes nothing", draft=stored.id),
            hint=_("discard it: `didact char discard {draft}`", draft=stored.id),
        )
    routes = cast(list[JSON], stored.draft.map.get("routes") or [])
    planned: list[tuple[DraftEntity, Entity, Scope]] = []
    for item in stored.draft.entities:
        if stored.target is not None and item.key == engine_drafts.MAIN:
            continue  # written by `_advance`
        entity = _record(repo, item, ids, routes, mode, named)
        planned.append((item, entity, _scope_of(repo, item)))
    for _unused, entity, where in planned:
        records.create(cs, where, entity)
    if saved:
        cs.delete(state.state_path(repo, _name(stored.id)))
    return [*made, *(ids[item.key] for item, _entity, _where in planned)]


def make(
    cs: Changeset, active: PackSet, spec: dict[str, JSON], rule: Rule, mode: sheets.Strictness
) -> tuple[Located, bool]:
    """A rule's `entity:` step: the record it describes, written at once as `commit` writes a
    drafted one, unless one of that type and name is here already (the rule ran before): then
    that one, as it is. Where it is, and whether it's new."""
    repo = cs.repo
    ref = spec.get("from")
    start = _start(active, rule.pack, str(ref)) if ref else {}
    if start is None:
        raise InvalidError(
            _("{rule}: there's no compendium entry {entry}", rule=rule.id, entry=repr(ref)),
            hint=_("check the entry: `didact compendium find <words>`"),
        )
    type_ = str(spec.get("type") or start.get("type") or "note")
    item = DraftEntity.described(str(spec.get("key") or type_), type_, spec, start)
    entity_id = records.new_id(item.type, item.name)
    where = _scope_of(repo, item)
    path = repo.entity_path(where, entity_id)
    if repo.index().by_id(str(entity_id), repo.chain()):
        return repo.resolve(str(entity_id)), False
    if cs.planned_text(path) is not None:  # made earlier in this change
        return Located(records.planned(cs, path), where, path), False
    ids = {item.key: str(entity_id)}
    named = ids if spec.get("key") else {}  # no `key:`, nothing to swap: `kind: track` stays
    entity = _record(repo, item, ids, [], mode, named)
    records.create(cs, where, entity)
    return Located(entity, where, path), True


def _named(stored: Stored, ids: dict[str, str]) -> dict[str, str]:
    """The draft's keys a field or a link can name (the record's id at commit): those the pack
    wrote (`key:`, or a name to refer to it by, `as:`) and the character's; an entity made with
    neither has none, so a field that happens to read like its key stays as written."""
    keyed = {e.key for e in stored.draft.entities if e.keyed} | {engine_drafts.MAIN}
    return {key: record for key, record in ids.items() if key in keyed}


def _record(
    repo: Repo,
    item: DraftEntity,
    ids: dict[str, str],
    routes: list[JSON],
    mode: sheets.Strictness,
    named: dict[str, str],
) -> Entity:
    """A drafted entity as the record `commit` writes, checked against its sheet: a field or a
    link naming a key of the draft (one of `named`) holds that record's id, and its routes go
    with it."""
    payload = cast(dict[str, JSON], _swap_keys(item.fields, named))  # a key → its new record
    entity = records.build_entity(
        EntityId.parse(ids[item.key]),
        item.name,
        payload,
        tags=item.tags,
        body=item.body or None,
    )
    for link in item.links:
        target = str(link.get("to", ""))
        records.add_link(entity, str(link.get("rel") or "related"), named.get(target, target))
    mine = [
        {
            "to": ids.get(str(r.get("to")), str(r.get("to"))),
            **{k: v for k, v in r.items() if k in ROUTE_KEYS},
        }
        for r in routes
        if isinstance(r, dict) and r.get("from") == item.key
    ]
    if mine:
        entity.fields["routes"] = list[JSON](mine)
    sh = sheets.sheet(repo, item.type)
    sheets.route_bare(entity, sh, list(payload))
    sheets.validate(entity, sh, mode)
    return entity


def _scope_of(repo: Repo, item: DraftEntity) -> Scope:
    """Where a drafted entity goes: its `scope` (world, campaign or a full scope), else where
    `new` puts a record of its type."""
    return (
        repo.check_scope(Scope.parse(item.scope))
        if item.scope and ":" in item.scope
        else _scope_named(repo, item.scope)
        if item.scope
        else repo.default_scope(item.type)
    )


def _advance(cs: Changeset, stored: Stored, mode: sheets.Strictness, ids: dict[str, str]) -> bool:
    """Write what an advancement changed to its record, checked against the sheet like `set`:
    a field naming a key of the draft holds that record's id. False when the record itself
    doesn't change."""
    repo = cs.repo
    located = repo.resolve(str(stored.target))
    sh = sheets.sheet(repo, located.entity.type)
    main = stored.draft.main()
    changed = {k: _swap_keys(v, ids) for k, v in main.fields.items() if stored.base.get(k) != v}
    if not changed:
        return False
    main.fields.update(changed)  # with ids for keys, as the commit reports it

    def change(entity: Entity) -> None:
        before = sheets.problems(entity, sh)
        for key, value in changed.items():
            sheets.apply(entity, assign.Assignment(("fields", key), "=", value, True), sh, mode)
        sheets.validate(entity, sh, mode, before=before)

    records.edit(cs, located.path, change)
    return True


def _swap_keys(value: JSON, ids: dict[str, str]) -> JSON:
    if isinstance(value, str):
        return ids.get(value, value)
    if isinstance(value, list):
        return [_swap_keys(v, ids) for v in value]
    if isinstance(value, dict):
        return {k: _swap_keys(v, ids) for k, v in value.items()}
    return value


def _scope_named(repo: Repo, text: str) -> Scope:
    chain = {s.kind: s for s in repo.chain()}
    if text in chain:
        return chain[text]
    raise InvalidError(
        _("no {scope} scope here", scope=text), hint=_("use world, campaign or a full scope")
    )


def _free_id(repo: Repo, type_: str, name: str, taken: set[str]) -> EntityId:
    base = records.new_id(type_, name)
    candidate = base
    number = 2
    while str(candidate) in taken or repo.index().by_id(str(candidate), repo.chain()):
        candidate = EntityId(type_, f"{base.slug}-{number}")
        number += 1
    return candidate


def generate(
    cs: Changeset, ref: str, prefill: dict[str, JSON], *, dry: bool, command: str | None
) -> tuple[Stored, list[str]]:
    """Describe it, get it: run a generator with every choice made (by the prefill or the
    dice) and commit it in this change. Prefill keys that are the generator's parameters
    are passed as parameters; the rest decide choices and rolls."""
    item = packs.active(cs.repo).find("generator", ref)
    names = set(cast(dict[str, JSON], item.data.get("params") or {}))
    params = {k: str(v) for k, v in prefill.items() if k in names}
    given = {k: v for k, v in prefill.items() if k not in names}
    stored = start(
        cs, "generator", ref, params, given, auto=True, dry=dry, command=command, keep=False
    )
    return stored, commit(cs, stored, force=False, saved=False)


def discard(cs: Changeset, stored: Stored) -> None:
    cs.delete(state.state_path(cs.repo, _name(stored.id)))


# ---------------------------------------------------------------------------- showing


def lines(repo: Repo, stored: Stored, *, full: bool = False) -> list[str]:
    if stored.target is not None:
        head = _(
            "#{draft} {target} advancing by {source}",
            draft=stored.id,
            target=stored.target,
            source=stored.source,
        )
    elif stored.kind == "chargen":
        head = (
            _("#{draft} character from {source} (auto)", draft=stored.id, source=stored.source)
            if stored.auto
            else _("#{draft} character from {source}", draft=stored.id, source=stored.source)
        )
    else:
        head = (
            _("#{draft} draft from {source} (auto)", draft=stored.id, source=stored.source)
            if stored.auto
            else _("#{draft} draft from {source}", draft=stored.id, source=stored.source)
        )
    out = [head]
    for entity in stored.draft.entities:
        fields = entity.fields
        if stored.target is not None and entity.key == engine_drafts.MAIN:  # what changes
            fields = {k: v for k, v in fields.items() if stored.base.get(k) != v}
            out.append(
                "- "
                + (
                    ", ".join(
                        f"{k}: {short(stored.base.get(k))} → {short(v)}" for k, v in fields.items()
                    )
                    or _("nothing changes yet")
                )
            )
            continue
        shown = ", ".join(  # rolled traits (a dict) get a line of their own
            f"{k}: {short(v)}"
            for k, v in fields.items()
            if k != "map" and not (k == "traits" and isinstance(v, dict))
        )
        out.append(
            f"- [{entity.key}] {entity.type} {entity.name or _('(no name yet)')}"
            + (f": {shown}" if shown else "")
        )
        traits = entity.fields.get("traits")
        if isinstance(traits, dict) and traits:
            out.append("  " + _("traits: {traits}", traits=tables.traits_line(repo, traits)))
        out += [f"  {link.get('rel')} → {link.get('to')}" for link in entity.links] if full else []
    if stored.draft.map:
        out += ["", *ascii_map(stored), "", "```mermaid", *mermaid(stored), "```"]
    if stored.prompts:
        out += ["", *(_("ask: {prompt}", prompt=p) for p in stored.prompts)]
    choice = stored.draft.open
    if choice is not None:
        verb = "char" if stored.kind == "chargen" else "gen"
        listing = bool(choice.options) and not choice.pick  # a pick's note lists them already
        options = f": {', '.join(choice.options[:24])}" if listing else ""
        note = f" ({shown_phrase(choice.phrase, choice.note)})" if choice.note else ""
        out.append(
            _("waiting for {choice}{note}{options}", choice=choice.name, note=note, options=options)
        )
        out += _described(choice)
        out.append(
            _(
                "answer: `didact {verb} choose {draft} <value>` · let the dice decide: "
                "`didact {verb} roll {draft}`",
                verb=verb,
                draft=stored.id,
            )
            if choice.dice
            else _("answer: `didact {verb} choose {draft} <value>`", verb=verb, draft=stored.id)
        )
    else:
        verb = "char" if stored.kind == "chargen" else "gen"
        out.append(
            _(
                "write it: `didact {verb} commit {draft}` (or edit it first: `{verb} edit`)",
                verb=verb,
                draft=stored.id,
            )
        )
    return out


def _described(choice: engine_drafts.Choice) -> list[str]:
    """What each option means, and the names of options that are ids, a line each; what each
    score costs, when scores are bought."""
    out: list[str] = []
    for option in choice.options[:24]:
        label, said = choice.labels.get(option), choice.about.get(option)
        head = f"{option} ({label})" if label else option
        if said:
            out.append(f"  - {head}: {said}")
        elif label:
            out.append(f"  - {head}")
    costs = choice.form.get("costs") if choice.form.get("kind") == "point_buy" else None
    if isinstance(costs, dict) and costs:
        priced = ", ".join(f"{score} → {cost}" for score, cost in costs.items())
        out.append("  " + _("what each score costs: {costs}", costs=priced))
    return out


def short(value: JSON) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return (
            "[" + ", ".join(short(v) for v in value[:6]) + (", …" if len(value) > 6 else "") + "]"
        )
    if isinstance(value, dict):
        named = value.get("name")  # an item: by its name
        return str(named) if isinstance(named, str) and named else "{…}"
    return str(value)


def _places(stored: Stored, key: str = "places") -> list[DraftEntity]:
    wanted = cast(list[JSON], stored.draft.map.get(key) or [])
    keys = [str(k) for k in wanted]
    return [e for e in stored.draft.entities if e.key in keys]


def _spot(entity: DraftEntity) -> dict[str, JSON]:
    spot = entity.fields.get("map")
    return spot if isinstance(spot, dict) else {}


def ascii_map(stored: Stored, width: int = 48, height: int = 14) -> list[str]:
    """A sketch: each place as a number where the dice dropped it (regions as ^), then paths."""
    places = _places(stored)
    regions = _places(stored, "regions")
    grid = [[" "] * width for _row in range(height)]
    marks: dict[str, str] = {}
    symbols = "123456789abcdefghijklmnopqrstuvwxyz"
    for index, entity in enumerate([*regions, *places]):
        spot = _spot(entity)
        if not spot:
            continue
        x = int(float(cast(float, spot.get("x", 0))) * (width - 1))
        y = int(float(cast(float, spot.get("y", 0))) * (height - 1))
        if entity in regions:
            mark = "^"
        else:
            number = spot.get("n")
            position = (int(number) if isinstance(number, int) else index - len(regions) + 1) - 1
            mark = symbols[position % len(symbols)]
            marks[entity.key] = mark
        grid[y][x] = mark
    border = "+" + "-" * width + "+"
    out = [border, *("|" + "".join(row) + "|" for row in grid), border]
    for place in sorted(places, key=lambda p: marks.get(p.key, "?")):
        spot = _spot(place)
        mark, name, key = marks.get(place.key, "?"), place.name, place.key
        out.append(
            _("{mark} {name} [{key}] (entrance)", mark=mark, name=name, key=key)
            if spot.get("entrance")
            else _("{mark} {name} [{key}] (exit)", mark=mark, name=name, key=key)
            if spot.get("exit")
            else f"{mark} {name} [{key}]"
        )
    for region in regions:
        inside = [marks[p.key] for p in places if p.fields.get("region") == region.key]
        listed = ", ".join(inside) or _("no places")
        out.append(f"^ {region.name} [{region.key}]: {listed}")
    for route in cast(list[JSON], stored.draft.map.get("routes") or []):
        if isinstance(route, dict):
            a, b = marks.get(str(route.get("from")), "?"), marks.get(str(route.get("to")), "?")
            watches = route.get("watches")
            count = (
                watches
                if isinstance(watches, int) and not isinstance(watches, bool)
                else 1
                if watches == 1
                else 2
            )
            extra = (
                ngettext(", {watches} watch", ", {watches} watches", count, watches=watches)
                if watches is not None
                else ""
            )
            kind = f" ({route['type']})" if isinstance(route.get("type"), str) else ""
            details = route.get("details")
            about = f": {'; '.join(str(d) for d in details)}" if isinstance(details, list) else ""
            out.append(f"  {a} — {b}: {route.get('distance')}{extra}{kind}{about}")
    return out


def mermaid(stored: Stored) -> list[str]:
    names = {p.key: p.name for p in _places(stored)}
    out = ["graph LR"]
    for key, name in names.items():
        out.append(f'  {key.replace("-", "_")}["{name}"]')
    for route in cast(list[JSON], stored.draft.map.get("routes") or []):
        if not isinstance(route, dict):
            continue
        a = str(route.get("from")).replace("-", "_")
        b = str(route.get("to")).replace("-", "_")
        label = str(route.get("distance"))
        kind = route.get("type")
        out.append(
            f"  {a} -. {label}, {labels.inline(kind, labels.path_kind(kind))} .- {b}"
            if isinstance(kind, str)
            else f"  {a} -- {label} --- {b}"
        )
    return out
