"""Drafts: what generators and character creation build before anything is written.

A generator or chargen procedure runs in the rules engine with these extra steps. Nothing
touches the library: the steps fill a `Draft`, which `commit` later turns into records.

    - entity: {key: poi, type: loc, name: "The {@noun} {@kind}", fields: {kind: "@kind"}}
    - choose: {from: [fighter, rogue], as: class}          # or table: t / entries: type
    - choose_or_roll: {table: backgrounds, as: background}
    - choose: {from: [brave, quiet, rash], as: not_trait, exclude: "@traits"}  # not those
    - roll: {each: [STR, DEX, WIL], dice: 3d6}            # into the draft's character
    - roll: {hp: 1d6, age: 2d20+10}
    - swap: {among: [STR, DEX, WIL], optional: true}
    - point_buy: {fields: [STR, DEX, CON], budget: 27, costs: {8: 0, 9: 1, …}}
    - apply: "@background.gear"                             # a list → inventory; `field: value` too
    - roll_tables: [physique, skin]                         # traits; entry `gear`/`add` apply
    - name: {from: "@background.names"}                    # or {table: first-names}
    - add: {to: "@forest", field: trails, value: "{@trail}"}  # onto a drafted entity's field
    - add: {field: gold, value: "@bond.gold"}             # numbers add up (the character)
    - map: {places: poi, regions: terrain, paths: {max: 4}} # a pointcrawl among the places

Choices the procedure can't make alone (guided mode) leave the draft **open**: the run stops at
the first one, and `choose` answers it. Every rolled or chosen value is kept on the draft's trail,
so resuming replays the procedure without rolling anything twice.
"""

import math
from dataclasses import dataclass, field
from typing import cast

from didact.core import labels
from didact.core.errors import InvalidError
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON
from didact.core.phrases import Phrase, english, phrase
from didact.expr.model import Value, from_json, to_json
from didact.rules.engine import PATH, Given, Scope, StepHandler
from didact.tables.engine import BOTH_WAYS

MAIN = "character"  # the key of the character a chargen procedure builds


@dataclass(slots=True)
class DraftEntity:
    key: str
    type: str
    name: str
    fields: dict[str, JSON] = field(default_factory=dict)
    body: str = ""
    tags: list[str] = field(default_factory=list)
    links: list[dict[str, JSON]] = field(default_factory=list)  # {rel, to: key or record id}
    scope: str | None = None  # world | campaign (default: by type)
    keyed: bool = True  # its key is one the pack wrote (`key:`): a field or link naming it is it

    def to_data(self) -> dict[str, JSON]:
        data: dict[str, JSON] = {"key": self.key, "type": self.type, "name": self.name}
        if self.fields:
            data["fields"] = self.fields
        if self.body:
            data["body"] = self.body
        if self.tags:
            data["tags"] = list[JSON](self.tags)
        if self.links:
            data["links"] = list[JSON](self.links)
        if self.scope:
            data["scope"] = self.scope
        if not self.keyed:
            data["keyed"] = False
        return data

    @classmethod
    def from_data(cls, data: dict[str, JSON]) -> DraftEntity:
        fields = data.get("fields")
        tags = data.get("tags")
        links = data.get("links")
        scope = data.get("scope")
        return cls(
            str(data["key"]),
            str(data["type"]),
            str(data["name"]),
            dict(fields) if isinstance(fields, dict) else {},
            str(data.get("body") or ""),
            [str(t) for t in tags] if isinstance(tags, list) else [],
            [x for x in links if isinstance(x, dict)] if isinstance(links, list) else [],
            str(scope) if isinstance(scope, str) else None,
            data.get("keyed") is not False,
        )

    @classmethod
    def described(
        cls, key: str, type_: str, values: dict[str, JSON], start: dict[str, JSON]
    ) -> DraftEntity:
        """What an `entity:` step describes (its values filled in), over what `from:` starts it
        with (a compendium entry's type, name and fields)."""
        fields = values.get("fields")
        if isinstance(fields, dict):  # an empty value leaves the field out (an unset parameter)
            fields = {k: v for k, v in fields.items() if v is not None and v != ""}
        inherited = {k: v for k, v in start.items() if k not in ("type", "name", "body", "tags")}
        links = values.get("links")
        return cls(
            key,
            type_,
            str(values.get("name") or start.get("name") or key),
            {**inherited, **(fields if isinstance(fields, dict) else {})},
            str(values.get("body") or start.get("body") or ""),
            [*_texts(start.get("tags")), *_texts(values.get("tags"))],
            [x for x in links if isinstance(x, dict)] if isinstance(links, list) else [],
            str(values["scope"]) if isinstance(values.get("scope"), str) else None,
        )


@dataclass(slots=True)
class Choice:
    """A decision the draft waits for: its name, the options and where they came from.

    What each option means (`about`) and how an option that is an id reads (`labels`) come
    from the packs (`option_notes`, given by the library). `pick` asks for several options at
    once (`a, b`); `form` says how a structured answer is made (`point_buy`, `assign`), so an
    app can ask for it field by field."""

    name: str
    options: list[str]
    note: str = ""  # English (or the pack's own words)
    dice: bool = True  # whether `roll` can make it (a name with nothing to roll from can't)
    free: bool = False  # whether an answer that isn't one of the options will do (a name)
    phrase: Phrase | None = None  # Didact's note as a phrase, to show in any language
    about: dict[str, str] = field(default_factory=dict)  # an option → what it means
    labels: dict[str, str] = field(default_factory=dict)  # an option → its name (an id's)
    pick: int = 0  # how many different options to pick at once (0: one)
    form: dict[str, JSON] = field(default_factory=dict)  # a structured answer: its kind, …

    @classmethod
    def asking(
        cls,
        name: str,
        options: list[str],
        said: Phrase,
        *,
        dice: bool = True,
        free: bool = False,
        pick: int = 0,
        form: dict[str, JSON] | None = None,
    ) -> Choice:
        """A choice whose note is Didact's own words: kept in English, shown in any language."""
        return cls(name, options, english(said), dice, free, said, pick=pick, form=form or {})

    def to_data(self) -> dict[str, JSON]:
        data: dict[str, JSON] = {
            "name": self.name,
            "options": list[JSON](self.options),
            "note": self.note,
        }
        if not self.dice:
            data["dice"] = False
        if self.free or not self.options:  # no options: the answer is typed in
            data["free"] = True
        if self.phrase is not None:
            data["say"] = self.phrase
        if self.about:
            data["about"] = dict[str, JSON](self.about)
        if self.labels:
            data["labels"] = dict[str, JSON](self.labels)
        if self.pick:
            data["pick"] = self.pick
        if self.form:
            data["form"] = self.form
        return data

    @classmethod
    def from_data(cls, data: dict[str, JSON]) -> Choice:
        said = data.get("say")
        about, labels, pick, form = (
            data.get("about"),
            data.get("labels"),
            data.get("pick"),
            data.get("form"),
        )
        return cls(
            str(data.get("name")),
            [str(o) for o in cast(list[JSON], data.get("options") or [])],
            str(data.get("note") or ""),
            data.get("dice") is not False,
            data.get("free") is True,
            said if isinstance(said, dict) else None,
            {str(k): str(v) for k, v in about.items()} if isinstance(about, dict) else {},
            {str(k): str(v) for k, v in labels.items()} if isinstance(labels, dict) else {},
            pick if isinstance(pick, int) and not isinstance(pick, bool) else 0,
            dict(form) if isinstance(form, dict) else {},
        )

    def described(self, scope: Scope, table: str = "") -> Choice:
        """With what each option means, and the names of options that are ids, as the
        library finds them (a table entry's note or its table's `about:`, a compendium
        entry's summary)."""
        notes = scope.run.extra.get("option_notes")
        if callable(notes) and self.options:
            found = cast(tuple[dict[str, str], dict[str, str]], notes(table, self.options))
            self.about, self.labels = found
        return self


@dataclass(slots=True)
class Draft:
    entities: list[DraftEntity] = field(default_factory=list)
    open: Choice | None = None
    map: dict[str, JSON] = field(default_factory=dict)
    auto: bool = False
    counters: dict[str, int] = field(default_factory=dict)
    once: bool = False  # the dice make the next open choice only (`roll --one`)

    def by_dice(self) -> bool:
        """Do the dice make the choice at hand? Always in auto mode; else once, if asked."""
        if self.auto:
            return True
        once, self.once = self.once, False
        return once

    def get(self, key: str) -> DraftEntity:
        for entity in self.entities:
            if entity.key == key:
                return entity
        raise InvalidError(
            _("the draft has no {key}", key=repr(key)),
            hint=_("see `didact gen show` / `char show`"),
        )

    def main(self) -> DraftEntity:
        """The character a chargen draft builds (created on first use)."""
        for entity in self.entities:
            if entity.key == MAIN:
                return entity
        created = DraftEntity(MAIN, "pc", "")
        self.entities.insert(0, created)
        return created

    def next_key(self, base: str) -> str:
        count = self.counters.get(base, 0) + 1
        self.counters[base] = count
        return f"{base}-{count}"


def _wait(scope: Scope, name: str) -> bool:
    """Stop the run at an open choice (guided mode): `choose` answers it and resumes."""
    scope.run.stopped = _("waiting for {name}", name=name)
    return True


def draft_of(scope: Scope) -> Draft:
    found = scope.run.extra.get("draft")
    if not isinstance(found, Draft):
        raise InvalidError(
            _("{rule}: draft steps only run in generators and chargen", rule=scope.rule.id),
            hint=_("move the step into a pack's generators/ or chargen/ procedure"),
        )
    return found


# ---------------------------------------------------------------------------- values


def _value(scope: Scope, raw: JSON) -> JSON:
    """A step value, as `Scope.filled` reads it (`@name` and a lone `{expression}` evaluated,
    other text filled in), but `@entry.key` is a chosen entry's own data."""
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.startswith("@") and "{" not in stripped and " " not in stripped:
            name, _dot, key = stripped[1:].partition(".")
            data = _raw(scope).get(name)
            if key and isinstance(data, dict):
                for part in key.split("."):  # a mapping's keys by their path: `@row.pool.dice`
                    data = data.get(part) if isinstance(data, dict) else None
                return data  # an entry's own data (lists of items and all); None: absent
            bound = scope.run.bound
            if key and name in bound and f"{name}.{key}" not in bound:
                return None  # a choice of one's own, not a table's entry: it brings no data
        return scope.filled(raw)
    if isinstance(raw, list):
        return [_value(scope, item) for item in raw]
    if isinstance(raw, dict):
        return {str(k): _value(scope, v) for k, v in raw.items()}
    return raw


def _options(scope: Scope, spec: dict[str, JSON]) -> tuple[list[str], str]:
    """The options for a choice: a list, a table's entries, or a list expression, less what
    `exclude:` rules out."""
    options, table = _listed(scope, spec)
    excluded = _excluded(scope, spec)
    return [o for o in options if o.casefold() not in excluded], table


def _listed(scope: Scope, spec: dict[str, JSON]) -> tuple[list[str], str]:
    """A list (`from:`), or a table's entries (`table:`); `records:` adds the records of a
    type here (made in play, like a talent made with the GM)."""
    options: list[str] = []
    table = ""
    raw = spec.get("from")
    if isinstance(raw, str) and raw.startswith("@"):
        raw = to_json(scope.eval(raw))
    if isinstance(raw, list):
        options = [str(o) for o in raw]
    elif isinstance(spec.get("table"), str):
        table = str(spec["table"])
        names = scope.run.extra.get("table_options")
        options = [str(o) for o in names(table)] if callable(names) else []
    kind = spec.get("records")
    lister = scope.run.extra.get("records_of")
    if isinstance(kind, str) and callable(lister):
        options += [str(o) for o in lister(kind) if str(o) not in options]
    return options, table


def _excluded(scope: Scope, spec: dict[str, JSON]) -> set[str]:
    """What `exclude:` rules out, casefolded: an earlier pick (`"@traits"`) or a list."""
    if "exclude" not in spec:
        return set()
    found: set[str] = set()

    def add(value: JSON) -> None:
        if isinstance(value, list):  # a list of picks and lists (`["@talents", "@banned"]`)
            for item in value:
                add(item)
        elif value is not None and value != "":
            found.add(str(value).casefold())

    add(_value(scope, spec["exclude"]))
    return found


# ---------------------------------------------------------------------------- steps


def _entity(scope: Scope, step: dict[str, JSON]) -> bool:
    spec = step.get("entity")
    if not isinstance(spec, dict):
        return False
    draft = draft_of(scope)
    values = cast(dict[str, JSON], _value(scope, {k: v for k, v in spec.items() if k != "key"}))
    start = _entry_start(scope, values.get("from"))
    type_ = str(spec.get("type") or start.get("type") or "note")
    base = str(spec.get("key") or type_)
    key = draft.next_key(base)
    entity = DraftEntity.described(key, type_, values, start)
    entity.keyed = bool(spec.get("key")) or "as" in step  # unnamed: no key to swap at commit
    draft.entities.append(entity)
    scope.run.bound[str(step.get("as", base))] = key
    scope.run.lines.append(f"+ {labels.type_inline(type_)} {entity.name} [{key}]")
    return True


def _entry_start(scope: Scope, ref: JSON) -> dict[str, JSON]:
    """What `from:` starts an entity with: a compendium entry's type, name and fields (as
    `spawn` would make it). Nothing when there's no `from:`."""
    if ref is None or ref == "":
        return {}
    lookup = scope.run.extra.get("compendium")
    found = lookup(str(ref)) if callable(lookup) else None
    if not isinstance(found, dict):
        raise InvalidError(
            _("{rule}: there's no compendium entry {entry}", rule=scope.rule.id, entry=repr(ref)),
            hint=_("check the entry: `didact compendium find <words>`"),
        )
    return cast(dict[str, JSON], found)


def _texts(value: JSON) -> list[str]:
    return [str(v) for v in value] if isinstance(value, list) else []


def _choose(scope: Scope, step: dict[str, JSON]) -> bool:
    raw = step.get("choose", step.get("choose_or_roll"))
    if not isinstance(raw, dict):
        return False
    table_ref = raw.get("table")
    if isinstance(table_ref, str) and "{" in table_ref:  # a computed table: `setting-{@kind}`
        raw = {**raw, "table": scope.text(table_ref)}
    rollable = "choose_or_roll" in step
    name = str(raw.get("as") or raw.get("table") or "choice")
    count = raw.get("count")
    many = count if isinstance(count, int) and count > 1 else 0
    prefilled = scope.run.given.prefilled(name)
    if scope.given(name, whole=bool(many)):  # a list: the whole pick
        if many:
            _check_many(scope, name, _options(scope, raw)[0], many)
        else:
            if prefilled:  # one of its options, as written or in another case, or one's own
                scope.settle(name, *_listed(scope, raw))
            if str(scope.run.bound[name]).casefold() in _excluded(scope, raw):
                raise InvalidError(
                    _("{name}: {value} is ruled out here", name=name, value=scope.run.bound[name]),
                    hint=_(
                        "pick another: {options}", options=", ".join(_options(scope, raw)[0][:12])
                    ),
                )
        _after_choice(scope, name, raw)
        return True
    draft = draft_of(scope)
    options, table = _options(scope, raw)
    if many:
        return _choose_many(scope, raw, name, options, many)
    if "answer" in raw:  # already decided (a character's own path): no question, no roll
        said = _value(scope, raw["answer"])
        folded = str(said).casefold() if said is not None and said != "" else None
        match = next((o for o in options if o.casefold() == folded), None)
        if match is not None:
            scope.keep(name, _typed(match))
            _after_choice(scope, name, raw)
            return True
    if (rollable and not options and table) or draft.by_dice():
        if table:
            _roll_table(scope, raw, name, table, options)
        elif options:
            done = scope.roll(f"d{len(options)}", name)
            pick = options[int(done.total) - 1] if isinstance(done.total, int) else options[0]
            scope.keep(name, _typed(pick))
        else:
            raise InvalidError(
                _("{rule}: nothing to choose {name} from", rule=scope.rule.id, name=name),
                hint=_("give the step options (`from: [...]`) or a table (`table: ...`)"),
            )
        _after_choice(scope, name, raw)
        return True
    note = scope.text(str(raw.get("prompt") or ""))  # `{@path}` filled in
    if note or not rollable or not table:
        draft.open = Choice(name, options, note).described(scope, table)
    else:
        said = phrase(N_("or roll on {table}"), table=table)
        draft.open = Choice.asking(name, options, said).described(scope, table)
    return _wait(scope, name)


def _typed(option: str) -> Value:
    """An option as a typed answer would be kept: a whole number as a number (a pool's 6)."""
    return int(option) if option.lstrip("-").isdigit() else option


def _roll_table(
    scope: Scope, spec: dict[str, JSON], name: str, table: str, options: list[str]
) -> None:
    """Let the table decide; a result `exclude:` rules out is rolled again, and left off the
    trail so that a replay takes the one kept."""
    excluded = _excluded(scope, spec)
    for _try in range(20):
        text = _one_reading(scope, name, scope.table({"table": table, "as": name}), options)
        if text.casefold() not in excluded:
            return
        kept = _kept(scope, name)
        if kept is not None and scope.run.trail[kept] == (name, text):
            del scope.run.trail[kept:]  # with its path
        scope.run.lines.append(
            _("{name}: {value} is ruled out; rolling again", name=name, value=text)
        )
    if not options:
        raise InvalidError(
            _(
                "{rule}: every {table} result is ruled out for {name}",
                rule=scope.rule.id,
                table=table,
                name=name,
            ),
            hint=_("loosen its `exclude:`, or give the table results it leaves in"),
        )
    done = scope.roll(f"d{len(options)}", name)  # an unlucky streak: any allowed one
    scope.keep(name, options[int(cast(int, done.total)) - 1])


def _one_reading(scope: Scope, name: str, text: str, options: list[str]) -> str:
    """A choice is one of its options: when the dice make it on a table read both ways (31 or
    13), the straight reading stands (the log line shows both)."""
    if BOTH_WAYS not in text or not options:
        return text
    folded = {o.casefold(): o for o in options}
    chosen = folded.get(text.split(BOTH_WAYS)[0].casefold())
    if chosen is None:
        return text
    scope.run.bound[name] = chosen
    kept = _kept(scope, name)
    if kept is not None and scope.run.trail[kept] == (name, text):
        scope.run.trail[kept] = (name, chosen)
    return chosen


def _kept(scope: Scope, name: str) -> int | None:
    """Where the trail keeps the value of `name` just rolled (its path may follow it)."""
    trail = scope.run.trail
    at = len(trail) - 2 if trail and trail[-1][0] == name + PATH else len(trail) - 1
    return at if at >= 0 else None


def _choose_many(
    scope: Scope, raw: dict[str, JSON], name: str, options: list[str], count: int
) -> bool:
    """Pick `count` different options: `a, b` as the answer, or the dice pick them."""
    draft = draft_of(scope)
    if not options:
        raise InvalidError(
            _("{rule}: nothing to choose {name} from", rule=scope.rule.id, name=name),
            hint=_("give the step options (`from: [...]`) or a table (`table: ...`)"),
        )
    if draft.by_dice():
        pool = list(options)
        picked: list[str] = []
        while len(picked) < count and pool:
            done = scope.roll(f"d{len(pool)}", name)
            picked.append(pool.pop(int(cast(int, done.total)) - 1))
        scope.keep(name, ", ".join(picked))
    else:
        listed = ", ".join(options)
        said = (
            phrase(
                N_("pick {count}, separated by commas, from: {options} ({prompt})"),
                count=count,
                options=listed,
                prompt=scope.text(str(raw["prompt"])),
            )
            if isinstance(raw.get("prompt"), str)
            else phrase(
                N_("pick {count}, separated by commas, from: {options}"),
                count=count,
                options=listed,
            )
        )
        table = str(raw.get("table") or "")
        draft.open = Choice.asking(name, options, said, pick=count).described(scope, table)
        return _wait(scope, name)  # the picks are checked on replay
    _check_many(scope, name, options, count)
    _after_choice(scope, name, raw)
    return True


def _picks(answer: str, folded: dict[str, str]) -> list[str]:
    """The picks in `a, b, c`, longest option first, so one may hold a comma of its own
    ("Wild, ripped hair")."""
    parts = [p.strip() for p in answer.split(",")]
    picked: list[str] = []
    at = 0
    while at < len(parts):
        end = next(
            (j for j in range(len(parts), at, -1) if ", ".join(parts[at:j]).casefold() in folded),
            at + 1,
        )
        picked.append(", ".join(parts[at:end]))
        at = end
    return [p for p in picked if p]


def _check_many(scope: Scope, name: str, options: list[str], count: int) -> None:
    folded = {o.casefold(): o for o in options}
    picked = _picks(str(scope.run.bound[name]), folded)
    wrong = [p for p in picked if p.casefold() not in folded]
    if wrong or len({p.casefold() for p in picked}) != count:
        raise InvalidError(
            _(
                "{name}: pick {count} different ones of {options}",
                name=name,
                count=count,
                options=", ".join(options),
            ),
            hint=_("e.g. `{example}`", example=", ".join(options[:count])),
        )
    scope.run.bound[name] = [folded[p.casefold()] for p in picked]


def _raw(scope: Scope) -> dict[str, JSON]:
    """Table entries' data by the name they were bound to (for `@background.gear`)."""
    found = scope.run.extra.setdefault("raw", {})
    return cast(dict[str, JSON], found)


def _entry(scope: Scope, name: str, table: str) -> dict[str, JSON] | None:
    """Look up the chosen or rolled entry's data and keep it under `name` (a chosen one that
    goes on rolls on first: `Scope.onward`)."""
    lookup = scope.run.extra.get("entry_data")
    if not callable(lookup):
        return None
    scope.onward(name, table)
    data = lookup(table, str(scope.run.bound[name]), scope.run.paths.get(name))
    if not isinstance(data, dict):
        return None
    _raw(scope)[name] = cast(JSON, data)
    scope.bind_data(name, cast(dict[str, JSON], data))
    return cast(dict[str, JSON], data)


def _after_choice(scope: Scope, name: str, spec: dict[str, JSON]) -> None:
    """A chosen table entry brings its data (`@background.gear`); `field:` stores the choice."""
    target = spec.get("field")
    if isinstance(target, str):
        _set_field(scope, target, to_json(scope.run.bound[name]))
    table = spec.get("table")
    if isinstance(table, str):
        _entry(scope, name, table)


def _roll_fields(scope: Scope, step: dict[str, JSON]) -> bool:
    raw = step.get("roll")
    if not isinstance(raw, dict):
        return False
    draft_of(scope).main()  # the character exists from here on
    if "each" in raw:
        names = [str(n) for n in cast(list[JSON], raw.get("each") or [])]
        pairs = [(n, str(raw.get("dice"))) for n in names]
    else:
        pairs = [(str(k), str(v)) for k, v in raw.items()]
    for name, dice in pairs:
        if not scope.given(name):
            done = scope.roll(dice, name)
            scope.keep(name, done.total)
        _set_field(scope, name, to_json(scope.run.bound[name]))
    return True


def _swap(scope: Scope, step: dict[str, JSON]) -> bool:
    raw = step.get("swap")
    if not isinstance(raw, dict):
        return False
    among = [str(n) for n in cast(list[JSON], raw.get("among") or [])]
    name = str(raw.get("as", "swap"))
    draft = draft_of(scope)
    if not scope.given(name):
        if (raw.get("optional") is not True and not among) or draft.by_dice():
            scope.keep(name, "keep")
        else:
            pairs = [f"{a} {b}" for i, a in enumerate(among) for b in among[i + 1 :]]
            said = phrase(N_("swap two scores, or keep them"))
            draft.open = Choice.asking(name, ["keep", *pairs], said)
            return _wait(scope, name)
    choice = str(scope.run.bound[name])
    if choice != "keep":
        first, _space, second = choice.partition(" ")
        character = draft.main()
        if first not in among or second not in among:
            raise InvalidError(
                _(
                    "swap two of {fields} (e.g. '{first} {last}')",
                    fields=", ".join(among),
                    first=among[0],
                    last=among[-1],
                ),
                hint=_("or keep them as they are: `keep`"),
            )
        one, other = character.fields.get(first), character.fields.get(second)
        _set_field(scope, first, other)
        _set_field(scope, second, one)
        scope.run.lines.append(_("swapped {first} and {second}", first=first, second=second))
    return True


def _point_buy(scope: Scope, step: dict[str, JSON]) -> bool:
    raw = step.get("point_buy")
    if not isinstance(raw, dict):
        return False
    names = [str(n) for n in cast(list[JSON], raw.get("fields") or [])]
    budget = int(cast(int, raw.get("budget", 0)))
    costs = {
        int(k): int(cast(int, v)) for k, v in cast(dict[str, JSON], raw.get("costs") or {}).items()
    }
    name = str(raw.get("as", "scores"))
    draft = draft_of(scope)
    if not scope.given(name):
        if draft.by_dice():
            default = raw.get("default")
            if default == "random":  # spend the budget a point at a time, where it still fits
                default = list[JSON](_random_buy(scope, names, budget, costs, name))
            if not isinstance(default, list):
                raise InvalidError(
                    _(
                        "{rule}: point_buy needs a `default` array (or `random`) for --auto",
                        rule=scope.rule.id,
                    ),
                    hint=_("add `default: random` to the step, or answer it: `char choose`"),
                )
            scope.keep(name, " ".join(str(v) for v in default))
        else:
            said = phrase(
                N_("scores for {fields} (budget {budget})"), fields=" ".join(names), budget=budget
            )
            form: dict[str, JSON] = {
                "kind": "point_buy",
                "fields": list[JSON](names),
                "budget": budget,
                "costs": {str(k): v for k, v in sorted(costs.items())},
            }
            draft.open = Choice.asking(name, [], said, form=form)
            return _wait(scope, name)
    values = [int(v) for v in str(scope.run.bound[name]).replace(",", " ").split()]
    if len(values) != len(names):
        example = " ".join(str(min(costs)) for _field in names)
        raise InvalidError(
            ngettext(
                "give {n} score: {names}",
                "give {n} scores: {names}",
                len(names),
                names=" ".join(names),
            ),
            hint=_("e.g. `{example}`", example=example),
        )
    unknown = [v for v in values if v not in costs]
    if unknown:
        raise InvalidError(
            _("{score} isn't on the cost table", score=unknown[0]),
            hint=_("scores: {low}–{high}", low=min(costs), high=max(costs)),
        )
    spent = sum(costs[v] for v in values)
    if spent > budget:
        raise InvalidError(
            _(
                "those scores cost {spent} points; the budget is {budget}",
                spent=spent,
                budget=budget,
            ),
            hint=_("lower some of them until they fit"),
        )
    for field_name, value in zip(names, values, strict=True):
        _set_field(scope, field_name, value)
    scope.run.lines.append(_("point buy: {spent}/{budget} points", spent=spent, budget=budget))
    return True


def _random_buy(
    scope: Scope, names: list[str], budget: int, costs: dict[int, int], name: str
) -> list[int]:
    """Scores bought at random: start at the cheapest; raise a random field while it fits."""
    values = [min(costs)] * len(names)
    spent = 0
    while True:
        open_ = [
            i
            for i, v in enumerate(values)
            if v + 1 in costs and spent - costs[v] + costs[v + 1] <= budget
        ]
        if not open_:
            return values
        done = scope.roll(f"d{len(open_)}", f"{name}: raise")
        pick = open_[int(cast(int, done.total)) - 1]
        spent += costs[values[pick] + 1] - costs[values[pick]]
        values[pick] += 1


def _assign(scope: Scope, step: dict[str, JSON]) -> bool:
    """Spread a fixed array over fields (say 3, 2, 2, 1, 1): `edge=3 heart=2 …`."""
    raw = step.get("assign")
    if not isinstance(raw, dict):
        return False
    names = [str(n) for n in cast(list[JSON], raw.get("fields") or [])]
    values = [int(cast(int, v)) for v in cast(list[JSON], raw.get("values") or [])]
    if len(names) != len(values):
        raise InvalidError(
            _("{rule}: assign needs as many values as fields", rule=scope.rule.id),
            hint=_("give `values:` one number for each name in `fields:`"),
        )
    name = str(raw.get("as", "array"))
    draft = draft_of(scope)
    if not scope.given(name):
        if draft.by_dice():
            pool = list(values)
            picked: list[int] = []
            while pool:
                done = scope.roll(f"d{len(pool)}", name) if len(pool) > 1 else None
                picked.append(pool.pop(int(cast(int, done.total)) - 1 if done else 0))
            scope.keep(name, " ".join(f"{n}={v}" for n, v in zip(names, picked, strict=True)))
        else:
            spread = ", ".join(f"{v:+d}" if min(values) < 0 else str(v) for v in values)
            said = phrase(
                N_("give {spread} to {fields}: e.g. `{example}`"),
                spread=spread,
                fields=", ".join(names),
                example=f"{names[0]}={values[0]} …",
            )
            form: dict[str, JSON] = {
                "kind": "assign",
                "fields": list[JSON](names),
                "values": list[JSON](values),
            }
            draft.open = Choice.asking(name, [], said, form=form)
            return _wait(scope, name)
    given: dict[str, int] = {}
    for part in str(scope.run.bound[name]).replace(",", " ").split():
        key, sep, number = part.partition("=")
        if not sep or key not in names or not number.lstrip("+-").isdigit():
            raise InvalidError(
                _(
                    "{name}: write it as `{field}={value} …`",
                    name=name,
                    field=names[0],
                    value=values[0],
                ),
                hint=_("fields: {fields}", fields=", ".join(names)),
            )
        given[key] = int(number)
    if sorted(given.values()) != sorted(values) or set(given) != set(names):
        raise InvalidError(
            _("{name}: use each of {values} once, one per field", name=name, values=values),
            hint=", ".join(names),
        )
    for key in names:
        _set_field(scope, key, given[key])
    return True


def _apply(scope: Scope, step: dict[str, JSON]) -> bool:
    if "apply" not in step:
        return False
    value = _value(scope, step["apply"])
    if value is None:
        return True  # nothing to apply (e.g. a bond without gear)
    if isinstance(value, list):
        _set_field(scope, "inventory", value)
        scope.run.lines.append(_("gear: {items}", items=", ".join(_item_name(v) for v in value)))
    elif isinstance(value, dict):
        for key, item in value.items():
            if item is not None:  # an entry without it (a power pool only some effects have)
                _set_field(scope, key, item)
    return True


def _set_field(scope: Scope, key: str, value: JSON) -> None:
    """Set a field of the draft's character; a list adds to a list that's already there.
    The value is readable afterwards as `@character.<key>`."""
    character = draft_of(scope).main()
    current = character.fields.get(key)
    if isinstance(current, list) and isinstance(value, list):
        current.extend(value)
    else:
        character.fields[key] = value
    shown = from_json(character.fields[key])
    if shown is not None:
        scope.run.bound[f"character.{key}"] = shown


def _roll_tables(scope: Scope, step: dict[str, JSON]) -> bool:
    if "roll_tables" not in step:
        return False
    raw = step["roll_tables"]
    names = to_json(scope.eval(raw)) if isinstance(raw, str) else raw
    character = draft_of(scope).main()
    traits = character.fields.setdefault("traits", {})
    for table in [str(n) for n in cast(list[JSON], names if isinstance(names, list) else [])]:
        name = table.rpartition(".")[2].replace("-", "_")
        text = scope.table({"table": table, "as": name})
        if isinstance(traits, dict):
            traits[name] = text
        data = _entry(scope, name, table)
        gear = data.get("gear") if data else None
        if isinstance(gear, list) and gear:  # a result that hands out items
            _set_field(scope, "inventory", list(gear))
            scope.run.lines.append(_("gear: {items}", items=", ".join(_item_name(g) for g in gear)))
        extra = data.get("add") if data else None
        if isinstance(extra, dict):  # a result that adds to fields: `add: {gold: 20}`
            for key, amount in extra.items():
                _add_to(scope, character, key, amount)
                scope.run.lines.append(f"{key} +{amount}")
    return True


def _item_name(item: JSON) -> str:
    return str(item.get("name")) if isinstance(item, dict) else str(item)


def _name(scope: Scope, step: dict[str, JSON]) -> bool:
    raw = step.get("name")
    if not isinstance(raw, dict):
        return False
    character = draft_of(scope).main()
    if scope.given("name"):
        character.name = str(scope.run.bound["name"])
        return True
    options, table = _options(scope, raw)
    draft = draft_of(scope)
    if table:
        character.name = scope.table({"table": table, "as": "name"})
    elif options and draft.by_dice():
        done = scope.roll(f"d{len(options)}", "name")
        character.name = options[int(cast(int, done.total)) - 1]
        scope.keep("name", character.name)
    else:  # guided, or nothing to roll a name from (even a random draft waits for one then)
        prompt = raw.get("prompt")
        draft.open = (
            Choice("name", options, scope.text(str(prompt)), dice=bool(options), free=True)
            if prompt
            else Choice.asking(
                "name",
                options,
                phrase(N_("a name: pick one, or give your own")),
                dice=bool(options),
                free=True,
            )
        )
        return _wait(scope, "name")
    return True


def _ask(scope: Scope, step: dict[str, JSON]) -> bool:
    """A question any answer will do (a goal, another record's name): like a name with nothing
    to roll it from, the draft waits for it even in random mode, unless it's prefilled.
    `field:` stores the answer on the character."""
    raw = step.get("ask")
    if not isinstance(raw, dict):
        return False
    name = str(raw.get("as") or "answer")
    if scope.given(name):
        _after_choice(scope, name, raw)
        return True
    prompt = raw.get("prompt")
    note = scope.text(str(prompt)) if prompt else name
    draft_of(scope).open = Choice(name, [], note, dice=False, free=True)
    return _wait(scope, name)


def _add(scope: Scope, step: dict[str, JSON]) -> bool:
    """Add to a field of an entity drafted earlier (`to:`; the character by default): a number
    adds up (a bond's gold), anything else goes onto a list (a forest's trails)."""
    spec = step.get("add")
    if not isinstance(spec, dict):
        return False
    draft = draft_of(scope)
    target = _value(scope, spec.get("to")) if "to" in spec else None
    entity = draft.get(str(target)) if target is not None else draft.main()
    value = _value(scope, spec.get("value"))
    if value is not None:  # nothing to add (a bond without gold)
        _add_to(scope, entity, str(spec.get("field") or "notes"), value)
    return True


def _remove(scope: Scope, step: dict[str, JSON]) -> bool:
    """Take something off a list field of the character (or of a drafted entity, `to:`): a
    talent switched out, a bond resolved. Each value once; nothing there to take is fine."""
    spec = step.get("remove")
    if not isinstance(spec, dict):
        return False
    draft = draft_of(scope)
    target = _value(scope, spec.get("to")) if "to" in spec else None
    entity = draft.get(str(target)) if target is not None else draft.main()
    name = str(spec.get("field") or "notes")
    value = _value(scope, spec.get("value"))
    current = entity.fields.get(name)
    items = list(current) if isinstance(current, list) else []
    for gone in value if isinstance(value, list) else [value]:
        if gone in items:
            items.remove(gone)
    entity.fields[name] = items
    if entity.key == MAIN:
        scope.run.bound[f"character.{name}"] = cast(Value, from_json(items))
    return True


def _add_to(scope: Scope, entity: DraftEntity, name: str, value: JSON) -> None:
    current = entity.fields.get(name)
    if isinstance(value, int | float) and not isinstance(value, bool):
        if isinstance(current, int | float) and not isinstance(current, bool):
            value = current + value
        entity.fields[name] = value
    else:
        items = list(current) if isinstance(current, list) else []
        items.extend(value if isinstance(value, list) else [value])
        entity.fields[name] = items
    if entity.key == MAIN and (shown := from_json(entity.fields[name])) is not None:
        scope.run.bound[f"character.{name}"] = shown


# ---------------------------------------------------------------------------- maps


def _map(scope: Scope, step: dict[str, JSON]) -> bool:
    """The die drop: places (and regions) at random points, joined by paths.

    - `places`: the entities to connect (a key like `poi`, or a type); `regions`: entities
      dropped too, each place going into the nearest one (its `region`).
    - `paths: {max: 4}` per place; `distances` buckets; `watches` per bucket.
    - `hidden: 6` / `conditional: 5`: a d6 per path; at or over the number, that kind.
    - `describe: [table, …]`: rolled for each path (a feature, a condition).
    - `entrance: true`: the place nearest the edge; places are numbered from it along the
      paths (`map.n`), and paths run from the lower number. `exit: true`: a far place near an
      edge is the way out, numbered last. `number: "Room {@n}"` renames the places (and their
      keys) in that order.
    """
    spec = step.get("map")
    if not isinstance(spec, dict):
        return False
    draft = draft_of(scope)
    places = _matching(draft, str(spec.get("places", "loc")))
    regions = _matching(draft, str(spec["regions"])) if isinstance(spec.get("regions"), str) else []
    regions = [r for r in regions if r not in places]
    if len(places) < 2:
        return True
    count = len(places) + len(regions)
    dice = _dice(scope, "positions", f"{count * 2}d100")  # the die drop: one logged roll
    dropped = [*places, *regions]
    points = {p.key: (dice[i] / 100, dice[count + i] / 100) for i, p in enumerate(dropped)}
    paths = cast(dict[str, JSON], spec.get("paths") or {})
    most = int(cast(int, paths.get("max", 3)))
    keys = [p.key for p in places]
    edges = _connect(keys, points, most)
    order = (
        _order(keys, points, edges, exit_=spec.get("exit") is True)
        if spec.get("entrance") is True
        else None
    )
    if order is not None:  # paths lead away from the entrance
        rank = {key: index for index, key in enumerate(order)}
        edges = sorted(
            ((a, b) if rank[a] < rank[b] else (b, a) for a, b in edges),
            key=lambda e: (rank[e[0]], rank[e[1]]),
        )
    kinds = _path_kinds(scope, spec, len(edges))
    distances = [
        str(d) for d in cast(list[JSON], spec.get("distances") or ["short", "medium", "long"])
    ]
    watches = cast(dict[str, JSON], spec.get("watches") or {})
    describe = [str(t) for t in cast(list[JSON], spec.get("describe") or [])]
    routes: list[JSON] = []
    for index, (a, b) in enumerate(edges):
        gap = math.dist(points[a], points[b])
        bucket = (
            distances[min(int(gap / (1.0 / len(distances))), len(distances) - 1)]
            if gap < 1
            else distances[-1]
        )
        kind = kinds[index]
        route: dict[str, JSON] = {
            "from": a,
            "to": b,
            "distance": bucket,
            "hidden": kind == "hidden",
        }
        if kind != "standard":
            route["type"] = kind
        if bucket in watches:
            route["watches"] = watches[bucket]
        details = [
            scope.table({"table": table, "as": table.rpartition(".")[2].replace("-", "_")})
            for table in describe
        ]
        if details:
            route["details"] = list[JSON](details)
        routes.append(route)
        rel = "path" if kind == "standard" else f"{kind} path"
        draft.get(a).links.append({"rel": rel, "to": b})
    for place in dropped:
        x, y = points[place.key]
        place.fields["map"] = {"x": round(x, 2), "y": round(y, 2)}
    for place in places:
        if regions:
            nearest = min(regions, key=lambda r: math.dist(points[place.key], points[r.key]))
            place.fields["region"] = nearest.key
    draft.map = {"places": list[JSON](order or keys), "routes": routes}
    if regions:
        draft.map["regions"] = list[JSON]([r.key for r in regions])
    if order is not None:
        _mark(scope, draft, order, spec)
    scope.run.bound["map.places"] = len(places)
    scope.run.bound["map.paths"] = len(edges)
    scope.run.lines.append(
        _(
            "map: {places} places, {paths} paths, {regions} regions",
            places=len(places),
            paths=len(edges),
            regions=len(regions),
        )
        if regions
        else _("map: {places} places, {paths} paths", places=len(places), paths=len(edges))
    )
    return True


def _dice(scope: Scope, name: str, expression: str) -> list[int]:
    """Roll a pool whose faces matter (positions), kept on the trail so a replay is exact."""
    wanted = int(expression.partition("d")[0])
    if scope.given(name):
        kept = scope.run.bound[name]
        if isinstance(kept, list) and len(kept) == wanted:
            return [int(cast(int, d)) for d in kept]
    done = scope.roll(expression, name)
    faces = [int(d) for d in done.dice]
    scope.keep(name, list[Value](faces))
    return faces


def _matching(draft: Draft, wanted: str) -> list[DraftEntity]:
    return [e for e in draft.entities if e.type == wanted or e.key.startswith(f"{wanted}-")]


def _path_kinds(scope: Scope, spec: dict[str, JSON], count: int) -> list[str]:
    """Standard, hidden or conditional: one d6 per path when the map asks for either."""
    hidden_on, conditional_on = spec.get("hidden"), spec.get("conditional")
    if not count or not (isinstance(hidden_on, int) or isinstance(conditional_on, int)):
        return ["standard"] * count
    name = "hidden paths" if not isinstance(conditional_on, int) else "path kinds"
    found: list[str] = []
    for die in _dice(scope, name, f"{count}d6"):
        if isinstance(hidden_on, int) and die >= hidden_on:
            found.append("hidden")
        elif isinstance(conditional_on, int) and die >= conditional_on:
            found.append("conditional")
        else:
            found.append("standard")
    return found


def _order(
    keys: list[str],
    points: dict[str, tuple[float, float]],
    edges: list[tuple[str, str]],
    *,
    exit_: bool,
) -> list[str]:
    """The entrance is the place nearest the edge; the rest follow along the paths from it,
    nearest first. The exit (if any) is far from the entrance and near an edge: it comes last."""

    def edge_gap(key: str) -> float:
        x, y = points[key]
        return min(x, y, 1 - x, 1 - y)

    entrance = min(keys, key=edge_gap)
    way_out = (
        max(
            (k for k in keys if k != entrance),
            key=lambda k: math.dist(points[entrance], points[k]) - edge_gap(k),
        )
        if exit_ and len(keys) > 1
        else None
    )
    near: dict[str, list[str]] = {k: [] for k in keys}
    for a, b in edges:
        near[a].append(b)
        near[b].append(a)
    order = [entrance]
    frontier = [entrance]
    while frontier:  # breadth first
        current = frontier.pop(0)
        for other in sorted(near[current], key=lambda k: math.dist(points[current], points[k])):
            if other not in order:
                order.append(other)
                frontier.append(other)
    if way_out is not None:
        order.remove(way_out)
        order.append(way_out)
    return order


def _mark(scope: Scope, draft: Draft, order: list[str], spec: dict[str, JSON]) -> None:
    """Number the places (`map.n`), flag the entrance and exit, and rename them if asked."""
    for number, key in enumerate(order, start=1):
        spot = cast(dict[str, JSON], draft.get(key).fields["map"])
        spot["n"] = number
    cast(dict[str, JSON], draft.get(order[0]).fields["map"])["entrance"] = True
    draft.map["entrance"] = order[0]
    if spec.get("exit") is True and len(order) > 1:
        cast(dict[str, JSON], draft.get(order[-1]).fields["map"])["exit"] = True
        draft.map["exit"] = order[-1]
    template = spec.get("number")
    if not isinstance(template, str):
        return
    for number, key in enumerate(order, start=1):
        scope.run.bound["n"] = number
        draft.get(key).name = scope.text(template)
    scope.run.bound.pop("n", None)
    _rekey(scope, draft, {key: f"{key.rpartition('-')[0]}-{n}" for n, key in enumerate(order, 1)})
    placed = {str(k) for k in cast(list[JSON], draft.map["places"])}
    slots = [i for i, e in enumerate(draft.entities) if e.key in placed]  # list them in order
    ranked = sorted((draft.entities[i] for i in slots), key=_number_of)
    for slot, entity in zip(slots, ranked, strict=True):
        draft.entities[slot] = entity


def _number_of(entity: DraftEntity) -> int:
    spot = entity.fields.get("map")
    number = spot.get("n") if isinstance(spot, dict) else None
    return number if isinstance(number, int) else 0


def _rekey(scope: Scope, draft: Draft, mapping: dict[str, str]) -> None:
    """Rename draft keys (room-13 → room-1 once rooms are numbered), everywhere they appear."""

    def swap(value: JSON) -> JSON:
        if isinstance(value, str):
            return mapping.get(value, value)
        if isinstance(value, list):
            return [swap(v) for v in value]
        if isinstance(value, dict):
            return {k: swap(v) for k, v in value.items()}
        return value

    for entity in draft.entities:
        entity.key = mapping.get(entity.key, entity.key)
        entity.fields = cast(dict[str, JSON], swap(entity.fields))
        entity.links = cast(list[dict[str, JSON]], swap(list[JSON](entity.links)))
    draft.map = cast(dict[str, JSON], swap(draft.map))
    for name, value in list(scope.run.bound.items()):
        if isinstance(value, str) and value in mapping:
            scope.run.bound[name] = mapping[value]


def _connect(
    keys: list[str], points: dict[str, tuple[float, float]], most: int
) -> list[tuple[str, str]]:
    """Connect every place: a minimum spanning tree, then nearest neighbours up to `most` each."""
    edges: set[tuple[str, str]] = set()
    degree = dict.fromkeys(keys, 0)
    joined = {keys[0]}
    while len(joined) < len(keys):  # Prim's algorithm: always connected
        best = min(
            ((a, b) for a in joined for b in keys if b not in joined),
            key=lambda pair: math.dist(points[pair[0]], points[pair[1]]),
        )
        edges.add(best)
        degree[best[0]] += 1
        degree[best[1]] += 1
        joined.add(best[1])
    for a in keys:
        near = sorted((b for b in keys if b != a), key=lambda b: math.dist(points[a], points[b]))
        for b in near[:2]:
            pair = (a, b) if (b, a) not in edges else (b, a)
            if pair in edges or degree[a] >= most or degree[b] >= most:
                continue
            edges.add(pair)
            degree[a] += 1
            degree[b] += 1
    return sorted(edges, key=lambda e: (keys.index(e[0]), keys.index(e[1])))


HANDLERS: dict[str, StepHandler] = {
    "entity": _entity,
    "choose": _choose,
    "choose_or_roll": _choose,
    "roll": _roll_fields,  # only dict-valued rolls: `roll: {each: [STR, DEX], dice: 3d6}`
    "swap": _swap,
    "point_buy": _point_buy,
    "assign": _assign,
    "apply": _apply,
    "roll_tables": _roll_tables,
    "name": _name,
    "ask": _ask,
    "add": _add,
    "remove": _remove,
    "map": _map,
}


def given_from(trail: list[tuple[str, Value]], prefill: dict[str, JSON]) -> Given:
    """What to use instead of rolling: the trail (each value once, in order), then the prefill."""
    decided = {
        name: value for name, raw in prefill.items() if (value := from_json(raw)) is not None
    }
    return Given.build(trail, decided)
