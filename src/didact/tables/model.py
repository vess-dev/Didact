"""Tables as packs write them.

    table: weather
    title: Summer weather
    dice: d6                     # any expression: 2d6, d66, d100, d20 + @corruption
    clamp: true                  # a total past the ends uses the first/last entry
    entries:
      1-2: Clear
      3-4: {text: Rain, data: {travel: slow}}
      5: {text: Storm, then: [{table: lightning}]}
      6: {text: Roll twice, roll: 2}
    refs: {noun: nouns}          # `{noun}` in a text rolls on table `nouns`
    source: "Warden's Guide p. 12"

Other shapes: `entries` as a list (uniform, or `weight:` per entry), `columns` (roll each
column of a row separately), and `lookup: key` (or `[key1, key2]`) for tables you read
instead of roll, such as a chart indexed by odds and chaos.

`about:` says what each entry means when a choice offers it, from the entry's data
(`about: "Knows: {skills}."`); an entry's own `note:` says it instead.
"""

import re
from dataclasses import dataclass
from typing import cast

from didact.core.i18n import _
from didact.core.output import JSON

_RANGE = re.compile(r"^\s*(\d+)\s*[-–]\s*(\d+)\s*$")  # 2-3, 96-00
_SPAN = re.compile(r"^\s*(-?\d+)\s*\.\.\s*(-?\d+)\s*$")  # -4..-2
_AT_LEAST = re.compile(r"^\s*(-?\d+)\s*\+\s*$")  # 12+
_AT_MOST = re.compile(r"^\s*\.\.\s*(-?\d+)\s*$")  # ..2
_FIELD = re.compile(r"\{\{|\}\}|\{(\w+)\}")  # an entry's data named in an `about:` template
UNBOUNDED = 10**9


@dataclass(frozen=True, slots=True)
class Band:
    """The rolls an entry covers."""

    low: int
    high: int
    label: str

    def covers(self, value: int) -> bool:
        return self.low <= value <= self.high


def parse_key(raw: str | int, *, percentile: bool = False) -> Band:
    """`3`, `2-3`, `96-00` (00 is 100 on a d100), `-4..-2`, `12+`, `..2`."""
    label = str(raw)
    if isinstance(raw, int) and not isinstance(raw, bool):
        return Band(raw, raw, label)
    text = label.strip()
    if re.fullmatch(r"-?\d+", text):
        value = int(text)
        if percentile and text == "00":
            value = 100
        return Band(value, value, label)
    if match := _RANGE.match(text):
        low, high = int(match.group(1)), int(match.group(2))
        if percentile and match.group(2) == "00":
            high = 100
        if high < low:
            raise ValueError(_("range {text} runs backwards", text=repr(text)))
        return Band(low, high, label)
    if match := _SPAN.match(text):
        low, high = int(match.group(1)), int(match.group(2))
        if high < low:
            raise ValueError(_("range {text} runs backwards", text=repr(text)))
        return Band(low, high, label)
    if match := _AT_LEAST.match(text):
        return Band(int(match.group(1)), UNBOUNDED, label)
    if match := _AT_MOST.match(text):
        return Band(-UNBOUNDED, int(match.group(1)), label)
    raise ValueError(
        _("can't read entry key {text}: use 3, 2-3, 12+, ..2 or -4..-2", text=repr(text))
    )


@dataclass(frozen=True, slots=True)
class Entry:
    band: Band | None  # None for weighted/list entries
    weight: int
    text: str
    data: dict[str, JSON]
    then: list[JSON]
    table: str | None  # roll this table instead
    times: int  # "roll N times" entries (N > 0), else 0
    raw: JSON

    @property
    def label(self) -> str:
        return self.band.label if self.band else self.text


def entry_from(raw: JSON, band: Band | None) -> Entry:
    if isinstance(raw, dict):
        text = raw.get("text", raw.get("name", ""))
        then = raw.get("then", [])
        times = raw.get("roll", 0)
        data = raw.get("data", {})
        weight = raw.get("weight", 1)
        return Entry(
            band,
            weight if isinstance(weight, int) else 1,
            str(text) if text is not None else "",
            data if isinstance(data, dict) else {},
            cast(list[JSON], then if isinstance(then, list) else [then]),
            str(raw["table"]) if isinstance(raw.get("table"), str) else None,
            times if isinstance(times, int) and not isinstance(times, bool) else 0,
            raw,
        )
    if isinstance(raw, list):  # a row of columns
        return Entry(band, 1, " / ".join(str(r) for r in raw), {}, [], None, 0, raw)
    return Entry(band, 1, "" if raw is None else str(raw), {}, [], None, 0, raw)


@dataclass(frozen=True, slots=True)
class Table:
    id: str  # qualified: pack.id
    pack: str
    title: str
    dice: str | None
    entries: tuple[Entry, ...]
    columns: tuple[str, ...]
    lookup: tuple[str, ...]
    refs: dict[str, str]
    clamp: bool
    duplicates: str  # reroll | keep | make_it_worse
    source: str
    data: dict[str, JSON]
    remember: bool = False  # keep the last result per campaign, for `repeat:` entries

    @property
    def weighted(self) -> bool:
        return all(e.band is None for e in self.entries)

    def entry_for(self, value: int) -> Entry | None:
        for entry in self.entries:
            if entry.band is not None and entry.band.covers(value):
                return entry
        return None

    def landing(self, value: int) -> Entry | None:
        """The entry a roll of `value` lands on: by the weights of a weighted list, else the
        one whose key covers it (past the ends, the first or last with `clamp`); None: none."""
        if self.weighted:
            running = 0
            for weighted in self.entries:
                running += weighted.weight
                if value <= running:
                    return weighted
            return None
        found = self.entry_for(value)
        if found is None and self.clamp and self.entries:
            low, high = self.span()
            found = self.entry_for(low if value < low else high)
        return found

    def span(self) -> tuple[int, int]:
        bands = [e.band for e in self.entries if e.band is not None]
        return min(b.low for b in bands), max(b.high for b in bands)


def table_from(qualified: str, pack: str, data: dict[str, JSON]) -> Table:
    """Build a Table from pack data (already validated)."""
    dice = data.get("dice")
    percentile = isinstance(dice, str) and dice.replace(" ", "") in ("d100", "1d100", "d%", "1d%")
    raw_entries = data.get("entries", {})
    lookup = data.get("lookup")
    keys = tuple(lookup) if isinstance(lookup, list) else ((str(lookup),) if lookup else ())
    entries: list[Entry] = []
    if isinstance(raw_entries, list):
        entries = [entry_from(item, None) for item in raw_entries]
    elif isinstance(raw_entries, dict) and not keys:
        entries = [
            entry_from(v, parse_key(k, percentile=percentile)) for k, v in raw_entries.items()
        ]
    columns = data.get("columns", [])
    refs = data.get("refs", {})
    return Table(
        id=qualified,
        pack=pack,
        title=str(data.get("title") or qualified.rpartition(".")[2].replace("-", " ").capitalize()),
        dice=str(dice) if isinstance(dice, str | int) else None,
        entries=tuple(entries),
        columns=tuple(str(c) for c in columns) if isinstance(columns, list) else (),
        lookup=tuple(str(k) for k in keys),
        refs={str(k): str(v) for k, v in refs.items()} if isinstance(refs, dict) else {},
        clamp=bool(data.get("clamp", False)),
        duplicates=str(data.get("duplicates", "reroll")),
        source=str(data.get("source") or ""),
        data=data,
        remember=bool(data.get("remember"))
        or any(isinstance(e.raw, dict) and "repeat" in e.raw for e in entries),
    )


def about(table: Table, entry: Entry) -> str:
    """What an entry means when a choice offers it: its `note:`, else the table's `about:`
    filled in from its data (a list reads `a, b`; `{text}` is the entry itself)."""
    note = entry.raw.get("note") if isinstance(entry.raw, dict) else None
    if isinstance(note, str) and note.strip():
        return note.strip()
    template = table.data.get("about")
    if not isinstance(template, str):
        return ""

    def value(match: re.Match[str]) -> str:
        key = match.group(1)
        if key is None:  # `{{` or `}}`: a brace itself
            return match.group()[0]
        found = entry.text if key == "text" else entry.data.get(key)
        if isinstance(found, list):
            return ", ".join(str(item) for item in found)
        return "" if found is None or isinstance(found, dict) else str(found)

    return _FIELD.sub(value, template).strip()


def infer_dice(table: Table) -> str:
    """A die for a table that doesn't name one: from its keys (1–6 → d6, 11–66 → d66)."""
    if table.weighted:
        return f"d{sum(e.weight for e in table.entries)}"
    low, high = table.span()
    if low == 11 and high == 66:
        return "d66"
    if low == 1 and high < UNBOUNDED:
        return f"d{high}"
    raise ValueError(_("can't tell which dice to roll: add `dice:`"))
