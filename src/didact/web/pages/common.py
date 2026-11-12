"""Bits several pages share: record types and their colours, the record index, badges."""

import json
import re
import shlex
import zlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, cast

from didact.core import labels
from didact.core.i18n import _, ngettext, pgettext
from didact.core.output import JSON
from didact.core.phrases import shown as shown_phrase
from didact.web.app import Ran, Request, spec_for
from didact.web.html import Html, chip, datalist, h, icon

TYPE_COLORS = {  # the ten colours in style.css (c0…c9): the same type, the same colour
    "npc": 0,
    "pc": 1,
    "item": 2,
    "loc": 3,
    "quest": 4,
    "faction": 5,
    "session": 6,
    "scene": 6,
    "summary": 6,
    "lore": 7,
    "thread": 8,
    "note": 9,
}
COMMON_TYPES = ("npc", "pc", "loc", "item", "faction", "quest", "note")


def type_color(type_: str) -> int:
    known = TYPE_COLORS.get(type_)
    return known if known is not None else zlib.crc32(type_.encode()) % 10


def type_labels() -> dict[str, str]:
    return labels.types_plural()


def type_label(type_: str) -> str:
    return labels.type_plural(type_)


def own_field_labels() -> dict[str, str]:
    """Didact's own fields, by key (a pack's are named by its sheet, in its own words)."""
    return labels.field_names()


def field_label(key: str, names: dict[str, str] | None = None) -> str:
    """A field as a page names it: its sheet's label, else Didact's name for one of its own."""
    return labels.field_name(key, names)


def detail_label(name: str) -> str:
    """One of the GM's details (`didact about`) as a page names it; others as they're called."""
    return labels.detail_name(name)


def knowledge_badge(knowledge: str) -> Html | None:
    match knowledge:
        case "secret":
            return chip(pgettext("knowledge", "secret"), kind="secret", icon_name="eye-off")
        case "rumor":
            return chip(pgettext("knowledge", "rumor"), kind="rumor", icon_name="help-circle")
        case _:
            return None


@dataclass(frozen=True, slots=True)
class Listed:
    """A record as `didact find` lists it."""

    id: str
    name: str
    type: str
    scope: str
    knowledge: str
    snippet: str = ""

    @classmethod
    def from_data(cls, item: JSON) -> Listed:
        data = cast(dict[str, JSON], item)
        return cls(
            str(data.get("id", "")),
            str(data.get("name", "")),
            str(data.get("type", "")),
            str(data.get("scope", "")),
            str(data.get("knowledge", "known")),
            str(data.get("snippet") or ""),
        )


@dataclass(frozen=True, slots=True)
class Index:
    """Every record the viewer may see, from `didact find`."""

    ran: Ran
    records: list[Listed]
    hidden: int

    @property
    def names(self) -> dict[str, str]:
        return {r.id: r.name for r in self.records}

    def refs(self) -> dict[tuple[str, str], str]:
        """How to name each (id, scope) in a link: the id, or `id@scope` if the id repeats."""
        seen: dict[str, int] = {}
        for record in self.records:
            seen[record.id] = seen.get(record.id, 0) + 1
        return {
            (r.id, r.scope): f"{r.id}@{r.scope}" if seen[r.id] > 1 else r.id for r in self.records
        }


def record_index(
    req: Request, *, scope: str | None = None, archived: bool = False, words: Iterable[str] = ()
) -> Index:
    argv = ["find", *words, "--limit", "100000"]
    if scope:
        argv += ["--scope", scope]
    if archived:
        argv.append("--archived")
    ran = req.run(*argv, gm=True)
    raw = ran.data.get("results")
    records = [Listed.from_data(item) for item in raw] if isinstance(raw, list) else []
    hidden = ran.data.get("hidden")
    return Index(ran, records, hidden if isinstance(hidden, int) else 0)


def records_datalist(index: Index, id_: str = "records") -> Html:
    """Suggestions for a record field: ids, labelled with names."""
    return datalist(id_, ((r.id, f"{r.name} ({r.type})") for r in index.records))


def secret_note(
    hidden: int, what: Literal["secret record", "secret beat"] = "secret record"
) -> Html | None:
    if not hidden:
        return None
    if what == "secret beat":
        text = ngettext(
            "{n} secret beat hidden: turn on the GM view to see it.",
            "{n} secret beats hidden: turn on the GM view to see them.",
            hidden,
        )
    else:
        text = ngettext(
            "{n} secret record hidden: turn on the GM view to see it.",
            "{n} secret records hidden: turn on the GM view to see them.",
            hidden,
        )
    return h(t'<p class="dim small note">{icon("eye-off")}<span>{text}</span></p>')


def change_title(req: Request, event: dict[str, JSON], names: dict[str, str]) -> str:
    """A change as this view may name it (`names`: the records the viewer knows, by id).

    The GM view shows the summary in full. The player view shows only which command it was
    and the records the players know: a summary can hold a secret field's value, a secret
    record's name or one of the GM's notes."""
    summary = str(event.get("summary", ""))
    said = shown_phrase(event.get("say"), summary)  # in the reader's language
    if req.gm:
        return said
    if event.get("kind") == "undo":
        undone = re.match(r"undo (#e\d+)", summary)
        return _("undo {event}", event=undone[1]) if undone else pgettext("history", "undo")
    if event.get("kind") == "note":
        return said.partition(":")[0]  # "history cleared"
    try:
        words = shlex.split(str(event.get("command") or ""))
    except ValueError:  # not a command line after all
        words = []
    spec = spec_for(words[1:] if words[:1] == ["didact"] else words)
    parts: list[str] = []
    hidden = 0
    for raw in as_list(event.get("entities")):
        ref = str(raw)
        kind, _sep, slug = ref.partition(":")
        if ref in names:
            parts.append(names[ref])
        elif kind in ("world", "campaign", "session", "scene"):
            parts.append(f"{kind} {slug}")
        else:
            hidden += 1
    if hidden:
        parts.append(
            _("a hidden record")
            if hidden == 1
            else ngettext("{n} hidden record", "{n} hidden records", hidden)
        )
    what = spec.name if spec is not None else _("a change")
    return f"{what} · {', '.join(parts)}" if parts else what


def as_list(value: JSON) -> list[JSON]:
    return value if isinstance(value, list) else []


def as_dict(value: JSON) -> dict[str, JSON]:
    return value if isinstance(value, dict) else {}


def show_value(value: JSON) -> str:
    """A field's value as you'd type it back: text as is, anything else as JSON."""
    if isinstance(value, str):
        try:
            json.loads(value)
        except ValueError:
            return value
        return json.dumps(value, ensure_ascii=False)  # "5" stays text when typed back
    return json.dumps(value, ensure_ascii=False)
