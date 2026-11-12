"""Rolling on tables: dice or weights, lookups, columns, templates, follow-ups, with a trace.

`TableRoller` gets tables through a `find(ref, from_pack)` callback, so it never touches packs.
Every die it rolls comes from the RollContext's source: a table roll is one replayable roll.
"""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from didact.core.errors import DidactError, InvalidError, UnknownName
from didact.core.i18n import N_, _, pgettext
from didact.core.output import JSON
from didact.core.phrases import Phrase, english, phrase, translated
from didact.expr import RollContext, parse
from didact.expr.engine import evaluate, scalar, show
from didact.expr.model import Value
from didact.expr.render import detail
from didact.tables.model import Band, Entry, Table, entry_from, infer_dice, parse_key

MAX_DEPTH = 10
MAX_REROLLS = 20
_PLACEHOLDER = re.compile(r"\{\{|\}\}|\{([^{}]+)\}")  # `{{` and `}}` write a brace itself
_COLUMN = re.compile(r"\{\{|\}\}|\{(\w+)\}")  # a column named in a `read:` template

type FindTable = Callable[[str, str], Table]


@dataclass(slots=True)
class TableResult:
    table: str
    title: str
    text: str
    value: int | None = None  # the roll (None for lookups)
    dice: str = ""  # how it was rolled: "d6 → [4]"
    entry: str = ""  # the entry's key: "3-4"
    data: dict[str, JSON] = field(default_factory=dict)
    columns: dict[str, TableResult] = field(default_factory=dict)
    parts: list[TableResult] = field(default_factory=list)  # "roll twice": the rolls combined
    follow: list[TableResult] = field(default_factory=list)  # `then:` follow-ups
    subs: list[TableResult] = field(default_factory=list)  # tables rolled for `{placeholders}`
    notes: list[str | Phrase] = field(default_factory=list)  # a phrase: shown in any language
    source: str = ""
    onward: list[TableResult] = field(default_factory=list)  # rolled next: instead, then

    def copy_head(self) -> TableResult:
        """This result without its parts: one reading of a crucible."""
        return TableResult(
            self.table, self.title, self.text, self.value, self.dice, self.entry, dict(self.data)
        )

    def carried(self) -> dict[str, JSON]:
        """The entry's data, with what the tables it went on to roll add (the table it rolls
        instead, then its `then:` follow-ups, each down the line): a key keeps its first value."""
        found = dict(self.data)
        for result in self.onward:
            for key, value in result.carried().items():
                found.setdefault(key, value)
        return found

    def path(self) -> list[list[str]]:
        """The entries the roll took, as [table, entry]: this one, then those it went on to."""
        own = [[self.table, self.entry]] if self.entry else []
        return own + [step for result in self.onward for step in result.path()]

    @property
    def note_lines(self) -> list[str]:
        """The notes in English, as the data and the log keep them."""
        return [english(n) if isinstance(n, dict) else n for n in self.notes]

    def to_data(self) -> dict[str, JSON]:
        data: dict[str, JSON] = {"table": self.table, "title": self.title, "text": self.text}
        if self.value is not None:
            data["roll"] = self.value
        if self.dice:
            data["dice"] = self.dice
        if self.entry:
            data["entry"] = self.entry
        if self.data:
            data["data"] = self.data
        for name in ("parts", "follow", "subs"):
            items = getattr(self, name)
            if items:
                data[name] = [i.to_data() for i in items]
        if self.columns:
            data["columns"] = {k: v.to_data() for k, v in self.columns.items()}
        if self.notes:
            data["notes"] = list[JSON](self.note_lines)
        if self.source:
            data["source"] = self.source
        return data

    def lines(self, indent: str = "") -> list[str]:
        """`weather (d6 → [4]): Rain` then indented follow-ups."""
        how = f" ({_how(self.dice)})" if self.dice else ""
        lines = [f"{indent}{self.table}{how}: {self.text}"]
        pad = " " * len(indent)
        for part in self.parts:
            lines.extend(part.lines(pad + "  + "))
        for sub in self.subs:
            lines.extend(sub.lines(pad + "  ↳ "))
        for follow in self.follow:
            lines.extend(follow.lines(pad + "  then "))
        lines.extend(
            f"{pad}  " + _("note: {note}", note=translated(n) if isinstance(n, dict) else n)
            for n in self.notes
        )
        return lines


BOTH_WAYS = " · or "  # joins the two readings of a table read both ways (31 or 13)
ONE_ENTRY = "one entry"  # how a table with a single entry was "rolled"
CHOSEN = "chosen"  # how an entry chosen, not rolled, came about (what it goes on to is rolled)
OTHER_WAY = "read the other way: "  # how the other reading of a crucible came about


def _how(text: str) -> str:
    """How a result was rolled, in the reader's language (the data keeps it in English)."""
    if text == ONE_ENTRY:
        return _("one entry")
    if text == CHOSEN:
        return pgettext("table entry", "chosen")
    if text.startswith(OTHER_WAY):
        return _("read the other way: {value}", value=text.removeprefix(OTHER_WAY))
    return text


class TableRoller:
    def __init__(
        self, find: FindTable, ctx: RollContext, memory: Mapping[str, str] | None = None
    ) -> None:
        self.find = find
        self.ctx = ctx
        self.memory = dict(memory or {})  # table → the entry it landed on last time
        self.picked: dict[str, str] = {}  # what to remember after this roll

    def roll(
        self,
        table: Table,
        inputs: Mapping[str, Value] | None = None,
        *,
        depth: int = 0,
        skip_repeats: bool = False,
    ) -> TableResult:
        if depth > MAX_DEPTH:
            raise InvalidError(
                _(
                    "tables nest more than {depth} deep at {table}",
                    depth=MAX_DEPTH,
                    table=table.id,
                ),
                hint=_("a table may be rolling itself through its references"),
            )
        given = dict(inputs or {})
        if any(self.ctx.vars.get(k) != v for k, v in given.items()):
            self.ctx.vars = {
                **self.ctx.vars,
                **given,
            }  # table dice can read them: `d20 + @corruption`
        if table.lookup:
            return self._lookup(table, given, depth)
        if table.columns:
            return self._columns(table, given, depth)
        value, how = self._pick(table)
        entry = self._entry(table, value)
        if skip_repeats:  # rolling again for "roll twice": skip entries that say to roll more
            tries = 0
            while entry.times and tries < MAX_REROLLS:
                value, how = self._pick(table)
                entry = self._entry(table, value)
                tries += 1
        result = self._resolve(table, entry, value, how, given, depth)
        if table.data.get("both_ways") is True:
            self._other_way(table, value, result, given, depth)
        return result

    def take(
        self, table: Table, label: str, inputs: Mapping[str, Value] | None = None
    ) -> TableResult:
        """The entry `label`, chosen rather than rolled: what it goes on to (`then:`, a table
        instead) is rolled, as when a roll lands on it."""
        entry = next((e for e in table.entries if e.label == label), None)
        if entry is None:
            raise InvalidError(  # (a draft's path or a logged roll from an older table)
                _("table {table} has no entry for {value}", table=table.id, value=repr(label)),
                hint=_("check the pack: `didact pack validate {pack}`", pack=table.pack),
            )
        return self._resolve(table, entry, None, CHOSEN, dict(inputs or {}), 0)

    def _other_way(
        self, table: Table, value: int, result: TableResult, given: dict[str, Value], depth: int
    ) -> None:
        """A crucible read both ways (31 or 13): the other reading rides along; pick one."""
        tens, units = divmod(value, 10)
        swapped = units * 10 + tens
        if swapped == value or not (1 <= units <= 9 and 1 <= tens <= 9):
            return
        found = table.entry_for(swapped)
        if found is None:
            return
        other = self._resolve(table, found, swapped, f"{OTHER_WAY}{swapped}", given, depth)
        result.parts = [result.copy_head(), other]
        result.text = f"{result.text}{BOTH_WAYS}{other.text}"
        result.notes.append(
            phrase(
                N_("read both ways: {value} or {other}; pick the one that fits"),
                value=value,
                other=swapped,
            )
        )

    # ------------------------------------------------------------------ picking an entry

    def _pick(self, table: Table) -> tuple[int, str]:
        if table.weighted:
            expression = f"d{sum(e.weight for e in table.entries)}"
        else:
            expression = table.dice or _infer(table)
        value, how = self._dice(expression, table)
        if not table.dice and len(table.entries) == 1:  # a template joining other tables
            how = ONE_ENTRY  # (still drawn, so seeded rolls stay the same)
        return value, how

    def _dice(self, expression: str, table: Table) -> tuple[int, str]:
        try:
            node = parse(expression, self.ctx.registry)
            result = evaluate(node, self.ctx)
            number = scalar(result)
        except DidactError as exc:
            raise InvalidError(
                _(
                    "table {table}: dice `{expression}`: {problem}",
                    table=table.id,
                    expression=expression,
                    problem=exc.message,
                ),
                hint=exc.hint,
            ) from exc
        if not float(number).is_integer():
            raise InvalidError(
                _(
                    "table {table}: `{expression}` rolled {number}, not a whole number",
                    table=table.id,
                    expression=expression,
                    number=number,
                ),
                hint=_("check the pack: `didact pack validate {pack}`", pack=table.pack),
            )
        return int(number), f"{expression} → {detail(result)}"

    def _entry(self, table: Table, value: int) -> Entry:
        entry = table.landing(value)
        if entry is not None:
            return entry
        low, high = table.span()
        raise InvalidError(
            _(
                "table {table} has no entry for {value} (entries cover {low}–{high})",
                table=table.id,
                value=value,
                low=low,
                high=high,
            ),
            hint=_("add `clamp: true` to the table, or cover every roll"),
        )

    # ------------------------------------------------------------------ resolving an entry

    def _resolve(
        self,
        table: Table,
        entry: Entry,
        value: int | None,
        how: str,
        given: dict[str, Value],
        depth: int,
    ) -> TableResult:
        if table.remember and entry.band is not None:
            again = self.memory.get(table.id) == entry.label
            self.memory[table.id] = self.picked[table.id] = entry.label
            repeat = entry.raw.get("repeat") if isinstance(entry.raw, dict) else None
            if again and repeat is not None:  # e.g. Extreme weather twice in a row
                replaced = entry_from(repeat, None)
                result = self._resolve(table, replaced, value, how, given, depth)
                result.entry = entry.label
                result.notes.append(
                    phrase(
                        N_("{entry} twice in a row: {result}"), entry=entry.text, result=result.text
                    )
                )
                return result
        result = TableResult(table.id, table.title, "", value, how, entry.label, dict(entry.data))
        result.source = (
            str(entry.raw.get("source", table.source))
            if isinstance(entry.raw, dict)
            else table.source
        )
        if entry.table:
            target = self.find(entry.table, table.pack)
            inner = self.roll(target, given, depth=depth + 1)
            result.subs.append(inner)
            result.onward.append(inner)
            result.text = entry.text or inner.text
        elif entry.times:
            result.parts = self._repeat(table, entry.times, given, depth)
            result.text = " + ".join(p.text for p in result.parts)
            result.notes.extend(n for p in result.parts for n in p.notes)
        else:
            result.text = self._render(entry.text, table, given, depth, result)
        for step in entry.then:
            result.follow.append(self._then(step, table, given, depth))
        result.onward += result.follow
        return result

    def _repeat(
        self, table: Table, times: int, given: dict[str, Value], depth: int
    ) -> list[TableResult]:
        results: list[TableResult] = []
        seen: set[str] = set()
        for _time in range(times):
            attempt = self.roll(table, given, depth=depth + 1, skip_repeats=True)
            tries = 0
            while attempt.entry in seen and table.duplicates == "reroll" and tries < MAX_REROLLS:
                attempt = self.roll(table, given, depth=depth + 1, skip_repeats=True)
                tries += 1
            if attempt.entry in seen and table.duplicates == "make_it_worse":
                attempt.notes.append(
                    phrase(N_("{result} came up again: make it worse"), result=attempt.text)
                )
            seen.add(attempt.entry)
            results.append(attempt)
        return results

    def _then(self, step: JSON, table: Table, given: dict[str, Value], depth: int) -> TableResult:
        """A follow-up: `{table: x}`, `x` (a table id), `{roll: 2d6, text: …}` or `{text: …}`."""
        if isinstance(step, str):
            step = {"table": step}
        if not isinstance(step, dict):
            raise InvalidError(
                _("table {table}: can't follow up with {step}", table=table.id, step=repr(step)),
                hint=_("check the pack: `didact pack validate {pack}`", pack=table.pack),
            )
        if isinstance(step.get("table"), str):
            target = self.find(str(step["table"]), table.pack)
            times = step.get("times", 1)
            rolled = [
                self.roll(target, given, depth=depth + 1)
                for _time in range(times if isinstance(times, int) else 1)
            ]
            if len(rolled) == 1:
                return rolled[0]
            merged = TableResult(target.id, target.title, " + ".join(r.text for r in rolled))
            merged.parts = merged.onward = rolled
            return merged
        if isinstance(step.get("roll"), str):
            value, how = self._dice(str(step["roll"]), table)
            label = str(step.get("text", "roll"))
            return TableResult(table.id, label, f"{label}: {value}", value, how)
        text = self._render(str(step.get("text", "")), table, given, depth, None)
        return TableResult(table.id, table.title, text)

    def _render(
        self, text: str, table: Table, given: dict[str, Value], depth: int, into: TableResult | None
    ) -> str:
        """Fill `{name}` placeholders: inputs, then refs (tables), then dice, then table ids.
        `{{` and `}}` write a brace itself."""

        def replace(match: re.Match[str]) -> str:
            if match.group(1) is None:
                return match.group()[0]
            key = match.group(1).strip()
            if key in given:
                return _text(given[key])
            found = self.ctx.vars.get(key)
            if found is not None:
                return _text(found)
            ref = table.refs.get(key)
            if ref is not None:
                return self._sub(ref, table, given, depth, into)
            try:
                node = parse(key, self.ctx.registry)
            except DidactError:
                node = None
            if node is not None:
                try:
                    return _text(evaluate(node, self.ctx).value)
                except UnknownName as exc:
                    if exc.what != "variable":
                        raise
            try:
                return self._sub(key, table, given, depth, into)
            except DidactError as exc:
                hint = _(
                    "add it to `refs:`, pass `--with {key}=…`, or fix the name ({problem})",
                    key=key,
                    problem=exc.message,
                )
                message = _("table {table}: nothing fills {{{key}}}", table=table.id, key=key)
                raise InvalidError(message, hint=hint) from exc

        return _PLACEHOLDER.sub(replace, text)

    def _sub(
        self, ref: str, table: Table, given: dict[str, Value], depth: int, into: TableResult | None
    ) -> str:
        target = self.find(ref, table.pack)
        inner = self.roll(target, given, depth=depth + 1)
        if into is not None:
            into.subs.append(inner)
        return inner.text

    # ------------------------------------------------------------------ lookups and columns

    def _lookup(self, table: Table, given: dict[str, Value], depth: int) -> TableResult:
        node: JSON = table.data.get("entries", {})
        used: list[str] = []
        for key in table.lookup:
            wanted = given.get(key, self.ctx.vars.get(key))
            if wanted is None:
                raise InvalidError(
                    _(
                        "table {table} is read by {keys}; {key} is missing",
                        table=table.id,
                        keys=", ".join(table.lookup),
                        key=key,
                    ),
                    hint=_("pass it: `--with {key}=…`", key=key),
                )
            if not isinstance(node, dict):
                raise InvalidError(
                    _(
                        "table {table}: too few levels for {keys}",
                        table=table.id,
                        keys=", ".join(table.lookup),
                    ),
                    hint=_("check the pack: `didact pack validate {pack}`", pack=table.pack),
                )
            node = _match(node, wanted, table)
            used.append(f"{key}={_text(wanted)}")
        entry = entry_from(node, Band(0, 0, ", ".join(used)))
        result = self._resolve(table, entry, None, "lookup " + ", ".join(used), given, depth)
        if not isinstance(node, dict):
            result.data = {"value": node, **result.data}  # the raw cell, for rules to read
        return result

    def _columns(self, table: Table, given: dict[str, Value], depth: int) -> TableResult:
        result = TableResult(table.id, table.title, "")
        rolls: list[str] = []
        texts: list[str] = []
        for index, name in enumerate(table.columns):
            value, how = self._pick(table)
            row = self._entry(table, value)
            cells = row.raw if isinstance(row.raw, list) else [row.raw]
            if len(cells) == 1:
                index = 0  # a plain entry fills every column: "roll twice on the same list"
            elif index >= len(cells):
                raise InvalidError(
                    _(
                        "table {table}: row {row} has no `{name}` column",
                        table=table.id,
                        row=row.label,
                        name=name,
                    ),
                    hint=_("check the pack: `didact pack validate {pack}`", pack=table.pack),
                )
            cell = entry_from(cells[index], row.band)
            column = self._resolve(table, cell, value, how, given, depth)
            column.title = name
            result.columns[name] = column
            rolls.append(str(value))
            texts.append(f"{name}: {column.text}")
        result.dice = f"{table.dice or _infer(table)} → {', '.join(rolls)}"
        if table.data.get("labels") is False:  # meaning pairs: "Abandon · Advantage"
            texts = [c.text for c in result.columns.values()]
        result.text = " · ".join(texts)
        read = table.data.get("read")
        if isinstance(read, str):  # the book's reading: "It's a {first} {second} with …"
            words = {name: column.text for name, column in result.columns.items()}
            result.text = _COLUMN.sub(
                lambda m: words.get(m.group(1), m.group(0)) if m.group(1) else m.group()[0], read
            )
        return result


def _match(node: dict[str, JSON], wanted: Value, table: Table) -> JSON:
    """Pick the entry a lookup value falls in: the same key (ignoring case, and spaces against
    dashes: "Exceptional Yes" finds `exceptional-yes`), or a numeric range key."""
    text = _loose(_text(wanted))
    for key, value in node.items():
        if _loose(str(key)) == text:
            return value
    if isinstance(wanted, int | float) and not isinstance(wanted, bool):
        for key, value in node.items():
            try:
                band = parse_key(key)
            except ValueError:
                continue
            if band.covers(int(wanted)):
                return value
    options = ", ".join(str(k) for k in node)
    raise InvalidError(
        _("table {table} has no entry for {value}", table=table.id, value=repr(_text(wanted))),
        hint=_("entries: {options}", options=options),
    )


def _infer(table: Table) -> str:
    try:
        return infer_dice(table)
    except ValueError as exc:
        raise InvalidError(
            _("table {table}: {problem}", table=table.id, problem=str(exc)),
            hint=_("check the pack: `didact pack validate {pack}`", pack=table.pack),
        ) from exc


def _loose(text: str) -> str:
    return re.sub(r"[\s_-]+", "-", text.strip().casefold())


def _text(value: Value) -> str:
    return value if isinstance(value, str) else show(value)
