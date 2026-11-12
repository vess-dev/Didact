"""Didact's own words as the reader sees them: record types, fields and details, journal kinds,
knowledge, what a pack is and holds, where it comes from, and the profile's words.

The keys stay English wherever they're stored or typed (`didact log roll`, `knowledge=secret`,
`campaign profile role=gm`); only what's shown is translated, and only Didact's own vocabulary:
a pack's words (its types, fields and tables) are the pack's, in its own language. A line of the
command line's output shows a key as it's typed when it speaks English (for the LLMs that read
it: `inline`), and its label in any other language; the web app always shows labels.
"""

from didact.core import i18n
from didact.core.i18n import _, ngettext, pgettext


def inline(key: str, label: str) -> str:
    """A key in a line of text: as it's typed, in English (the command line's own language),
    else its label in the reader's language."""
    return key if i18n.current().code == i18n.DEFAULT else label


def type_inline(type_: str) -> str:
    """A record's type in a line of the command line's output (`npc Sweeney`)."""
    return inline(type_, type_name(type_))


def types_plural() -> dict[str, str]:
    """Didact's record types, as a list heading names them."""
    return {
        "npc": _("NPCs"),
        "pc": _("Player characters"),
        "loc": _("Places"),
        "item": _("Items"),
        "faction": _("Factions"),
        "quest": _("Quests"),
        "character": _("Characters"),
        "note": _("Notes"),
        "session": _("Sessions"),
        "scene": _("Scenes"),
        "summary": _("Summaries"),
        "lore": _("Lore"),
        "ruling": _("Rulings"),
        "thread": _("Threads"),
        "task": _("Tasks"),
        "track": _("Trackers"),
        "oracle": _("Oracles"),
    }


def type_plural(type_: str) -> str:
    """A list heading for a type: Didact's in the reader's language, a pack's as it's called."""
    return types_plural().get(type_, type_.replace("-", " ").capitalize())


def type_name(type_: str) -> str:
    """One record's type in a line of text (`NPC Sweeney`); a pack's type as it's called."""
    return {
        "npc": pgettext("type", "NPC"),
        "pc": pgettext("type", "PC"),
        "loc": pgettext("type", "place"),
        "item": pgettext("type", "item"),
        "faction": pgettext("type", "faction"),
        "quest": pgettext("type", "quest"),
        "character": pgettext("type", "character"),
        "note": pgettext("type", "note"),
        "session": pgettext("type", "session"),
        "scene": pgettext("type", "scene"),
        "summary": pgettext("type", "summary"),
        "lore": pgettext("type", "lore"),
        "ruling": pgettext("type", "ruling"),
        "thread": pgettext("type", "thread"),
        "task": pgettext("type", "task"),
        "track": pgettext("type", "tracker"),
        "oracle": pgettext("type", "oracle"),
    }.get(type_, type_)


def field_names() -> dict[str, str]:
    """Didact's own fields, by key: every system's `fields`, and what drafts set there. A pack's
    fields are named by its sheet (`label`), in its own words."""
    return {
        "description": _("Description"),
        "goal": _("Goal"),
        "pronouns": _("Pronouns"),
        "player": _("Player"),
        "role": _("Role"),
        "region": _("Region"),
        "discovered": _("Discovered"),
        "agenda": _("Agenda"),
        "obstacle": _("Obstacle"),
        "status_note": _("Status note"),
        "inventory": _("Inventory"),
        "traits": _("Traits"),
        "notes": _("Notes"),
        "routes": _("Routes"),
        "map": _("Map"),
        "map.x": _("Map: x"),
        "map.y": _("Map: y"),
        "map.n": _("Map: number"),
        "map.entrance": _("Map: entrance"),
        "map.exit": _("Map: exit"),
    }


def field_name(key: str, labels: dict[str, str] | None = None) -> str:
    """A field as it's shown: its sheet's label, else Didact's name for one of its own fields,
    else the key. A key inside a group of Didact's (a rolled trait) is named after the group."""
    if labels and key in labels:
        return labels[key]
    own = field_names()
    if key in own:
        return own[key]
    head, dot, rest = key.partition(".")
    if dot and head in own:
        return _("{group} · {name}", group=own[head], name=rest.replace("_", " "))
    return key.replace(".", " ").replace("_", " ")


def detail_name(name: str) -> str:
    """One of the GM's details (`didact about`); others as they're called."""
    return {
        "looks": pgettext("detail", "Looks"),
        "personality": pgettext("detail", "Personality"),
        "wants": pgettext("detail", "Wants"),
        "fears": pgettext("detail", "Fears"),
        "attitude": pgettext("detail", "Attitude"),
        "doing": pgettext("detail", "Doing"),
        "plan": pgettext("detail", "Plan"),
        "where": pgettext("detail", "Where"),
        "history": pgettext("detail", "History"),
        "powers": pgettext("detail", "Powers"),
        "state": pgettext("detail", "State"),
        "secret": pgettext("detail", "Secret"),
        "thoughts": pgettext("detail", "Thoughts"),
    }.get(name, name)


def beat_name(kind: str) -> str:
    """A journal entry's kind (`didact log <kind>`)."""
    return {
        "action": pgettext("beat", "action"),
        "oracle": pgettext("beat", "oracle"),
        "roll": pgettext("beat", "roll"),
        "result": pgettext("beat", "result"),
        "consequence": pgettext("beat", "consequence"),
        "narration": pgettext("beat", "narration"),
        "dialogue": pgettext("beat", "dialogue"),
        "note": pgettext("beat", "note"),
        "ooc": pgettext("beat", "out of character"),
    }.get(kind, kind)


def party_role(role: str) -> str:
    """A party member's role (`party add … --as <role>`)."""
    return {
        "pc": pgettext("party", "PC"),
        "companion": pgettext("party", "companion"),
        "hireling": pgettext("party", "hireling"),
    }.get(role, role)


def session_status(status: str) -> str:
    """Whether a session or scene is under way."""
    return {
        "open": pgettext("session", "open"),
        "closed": pgettext("session", "closed"),
        "unknown": pgettext("session", "unknown"),
    }.get(status, status)


def lore_kind(kind: str) -> str:
    """What a lore hit is: an entry's kind (`lore add --kind`), a record's card or a ruling."""
    return {
        "lore": pgettext("lore", "lore"),
        "memory": pgettext("lore", "memory"),
        "rule-reminder": pgettext("lore", "rule reminder"),
        "preference": pgettext("lore", "preference"),
        "secret": pgettext("lore", "secret"),
        "card": pgettext("lore", "card"),
        "ruling": pgettext("lore", "ruling"),
    }.get(kind, kind)


def initiative_mode(mode: str) -> str:
    """How a fight takes turns (`combat start --mode`)."""
    return {
        "sides": pgettext("initiative", "sides"),
        "individual": pgettext("initiative", "individual"),
        "popcorn": pgettext("initiative", "popcorn"),
    }.get(mode, mode)


def knowledge_name(knowledge: str) -> str:
    """Who knows a record: known, secret (the GM's) or rumor."""
    return {
        "known": pgettext("knowledge", "known"),
        "secret": pgettext("knowledge", "secret"),
        "rumor": pgettext("knowledge", "rumor"),
    }.get(knowledge, knowledge)


def record_key(key: str) -> str:
    """The keys every record has, as `show` names them."""
    return {
        "aliases": pgettext("record", "aliases"),
        "tags": pgettext("record", "tags"),
        "status": pgettext("record", "status"),
        "knowledge": pgettext("record", "knowledge"),
        "archived": pgettext("record", "archived"),
        "links": pgettext("record", "links"),
        "updated": pgettext("record", "updated"),
    }.get(key, key)


def scope_name(kind: str) -> str:
    """A scope's kind: global, a system, a world, a campaign."""
    return {
        "global": pgettext("scope", "global"),
        "system": pgettext("scope", "system"),
        "world": pgettext("scope", "world"),
        "campaign": pgettext("scope", "campaign"),
    }.get(kind, kind)


def library_part(what: str) -> str:
    """A part of the data home (`didact library`): a world or campaign by name, or one of these."""
    head, _space, name = what.strip().partition(" ")
    if head in ("world", "campaign") and name:
        return f"{inline(head, scope_name(head))} {name}"
    return inline(
        what.strip(),
        {
            "installed packs": _("installed packs"),
            "systems (homebrew)": _("systems (homebrew)"),
            "global": scope_name("global"),
            "event log": _("event log"),
            "backups": _("backups"),
        }.get(what.strip(), what.strip()),
    )


def cache_part(kind: str) -> str:
    """A kind of cached file (`didact cache show`)."""
    return inline(
        kind,
        {"search indexes": _("search indexes"), "compiled packs": _("compiled packs")}.get(
            kind, kind
        ),
    )


def on_off(value: str) -> str:
    """A flag's value as a switch says it (the value typed stays `on` or `off`)."""
    return {"on": pgettext("switch", "on"), "off": pgettext("switch", "off")}.get(value, value)


def time_unit(unit: str) -> str:
    """A unit of game time, as a list to pick it from names it (advance 3 [hours]); a pack's
    own units are the pack's words."""
    return {
        "second": pgettext("units of time", "seconds"),
        "minute": pgettext("units of time", "minutes"),
        "round": pgettext("units of time", "rounds"),
        "turn": pgettext("units of time", "turns"),
        "hour": pgettext("units of time", "hours"),
        "watch": pgettext("units of time", "watches"),
        "day": pgettext("units of time", "days"),
        "week": pgettext("units of time", "weeks"),
    }.get(unit, unit)


def path_kind(kind: str) -> str:
    """A path of a map that isn't plain."""
    return {
        "hidden": pgettext("path", "hidden"),
        "conditional": pgettext("path", "conditional"),
    }.get(kind, kind)


def yes_no(value: bool) -> str:
    return pgettext("answer", "yes") if value else pgettext("answer", "no")


def pack_kind(kind: str) -> str:
    """What a pack is."""
    return {
        "system": pgettext("pack", "system"),
        "oracle": pgettext("pack", "oracle"),
        "setting": pgettext("pack", "setting"),
        "supplement": pgettext("pack", "supplement"),
        "adventure": pgettext("pack", "adventure"),
        "base": pgettext("pack", "base"),
    }.get(kind, kind)


def pack_origin(origin: str) -> str:
    """Where a pack comes from."""
    return {
        "installed": pgettext("pack", "installed"),
        "bundled": pgettext("pack", "bundled"),
        "shipped": pgettext("pack", "shipped"),
        "path": pgettext("pack", "path"),
        "library": pgettext("pack", "library"),
        "shipped folder": _("Didact's packs folder"),
    }.get(origin, origin)


def item_kind(kind: str) -> str:
    """One kind of pack content, alone (`check save`)."""
    return {
        "type": pgettext("content", "sheet type"),
        "table": pgettext("content", "table"),
        "deck": pgettext("content", "deck"),
        "bag": pgettext("content", "bag"),
        "check": pgettext("content", "check"),
        "action": pgettext("content", "action"),
        "procedure": pgettext("content", "procedure"),
        "trigger": pgettext("content", "trigger"),
        "option": pgettext("content", "option"),
        "entry": pgettext("content", "compendium entry"),
        "test": pgettext("content", "test"),
        "generator": pgettext("content", "generator"),
        "chargen": pgettext("content", "character creation"),
        "oracle": pgettext("content", "oracle"),
        "lore": pgettext("content", "lore entry"),
        "reference": pgettext("content", "reference section"),
        "term": pgettext("content", "glossary term"),
    }.get(kind, kind)


def item_count(kind: str, n: int) -> str:
    """So many of one kind of pack content: `201 tables`."""
    match kind:
        case "type":
            return ngettext("{n} sheet type", "{n} sheet types", n)
        case "table":
            return ngettext("{n} table", "{n} tables", n)
        case "deck":
            return ngettext("{n} deck", "{n} decks", n)
        case "bag":
            return ngettext("{n} bag", "{n} bags", n)
        case "check":
            return ngettext("{n} check", "{n} checks", n)
        case "action":
            return ngettext("{n} action", "{n} actions", n)
        case "procedure":
            return ngettext("{n} procedure", "{n} procedures", n)
        case "trigger":
            return ngettext("{n} trigger", "{n} triggers", n)
        case "option":
            return ngettext("{n} option", "{n} options", n)
        case "entry":
            return ngettext("{n} compendium entry", "{n} compendium entries", n)
        case "test":
            return ngettext("{n} test", "{n} tests", n)
        case "generator":
            return ngettext("{n} generator", "{n} generators", n)
        case "chargen":
            return ngettext("{n} character creation", "{n} character creations", n)
        case "oracle":
            return ngettext("{n} oracle", "{n} oracles", n)
        case "lore":
            return ngettext("{n} lore entry", "{n} lore entries", n)
        case "reference":
            return ngettext("{n} reference section", "{n} reference sections", n)
        case "term":
            return ngettext("{n} glossary term", "{n} glossary terms", n)
        case "named dice":
            return ngettext("{n} named die", "{n} named dice", n)
        case "dice macros":
            return ngettext("{n} dice macro", "{n} dice macros", n)
        case "dice chains":
            return ngettext("{n} dice chain", "{n} dice chains", n)
    return f"{n} {kind}"


def check_state(state: str) -> str:
    """How one of `doctor`'s checks came out."""
    return {
        "ok": pgettext("check", "ok"),
        "warn": pgettext("check", "warn"),
        "fail": pgettext("check", "fail"),
    }.get(state, state)


def search_source(source: str) -> str:
    """Where a search hit comes from."""
    return {
        "rules": pgettext("search", "rules"),
        "terms": pgettext("search", "glossary"),
        "mechanics": pgettext("search", "mechanics"),
        "tables": pgettext("search", "tables"),
        "compendium": pgettext("search", "compendium"),
        "records": pgettext("search", "records"),
        "transcript": pgettext("search", "transcript"),
        "docs": pgettext("search", "docs"),
        "guides": pgettext("search", "guides"),
        "generators": pgettext("search", "generators"),
    }.get(source, source)


def profile_key(key: str) -> str:
    """One of the campaign profile's keys, as the brief shows it."""
    return {
        "role": pgettext("profile", "role"),
        "tone": pgettext("profile", "tone"),
        "themes": pgettext("profile", "themes"),
        "lines": pgettext("profile", "lines"),
        "veils": pgettext("profile", "veils"),
        "lethality": pgettext("profile", "lethality"),
        "fudging": pgettext("profile", "fudging"),
        "invention": pgettext("profile", "invention"),
        "narration": pgettext("profile", "narration"),
        "dice": pgettext("profile", "dice"),
    }.get(key, key)


def profile_value(value: str) -> str:
    """One of the profile's own choices, as the brief shows it (free answers as given)."""
    return {
        "gm": pgettext("profile", "GM"),
        "co-gm": pgettext("profile", "co-GM"),
        "oracle": pgettext("profile", "oracle only"),
        "scribe": pgettext("profile", "scribe"),
        "gentle": pgettext("profile", "gentle"),
        "standard": pgettext("profile", "standard"),
        "deadly": pgettext("profile", "deadly"),
        "never": pgettext("profile", "never"),
        "peril-points": pgettext("profile", "peril points"),
        "book-first": pgettext("profile", "book first"),
        "balanced": pgettext("profile", "balanced"),
        "freeform": pgettext("profile", "freeform"),
        "short": pgettext("profile", "short"),
        "medium": pgettext("profile", "medium"),
        "long": pgettext("profile", "long"),
        "second": pgettext("profile", "second person"),
        "third": pgettext("profile", "third person"),
        "present": pgettext("profile", "present tense"),
        "past": pgettext("profile", "past tense"),
        "didact": pgettext("profile", "Didact rolls"),
        "physical": pgettext("profile", "physical dice"),
    }.get(value, value)
