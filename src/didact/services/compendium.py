"""The compendium: monsters, items, spells, backgrounds… as pack entries.

An entry is written like `new --data`: `{id: troll, type: monster, name: Troll, hp: 12, …}`.
`spawn` turns an entry into a record in the world; `add` writes homebrew entries into
`systems/<pack>/homebrew/compendium/`, so the pack itself stays untouched, and `remove`
deletes them again. The packs' own entries are never deleted: house rules change them.
"""

import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from didact.core.errors import ConflictError, DidactError, InvalidError, NotFoundError
from didact.core.i18n import _
from didact.core.ids import normalize_name, slugify
from didact.core.output import JSON, code
from didact.packs.library import Item, PackLibrary, PackSet
from didact.packs.source import Problem, Severity
from didact.packs.versions import parse_requirement
from didact.schema.sheet import Sheet
from didact.services import packs as pack_service
from didact.store import frontmatter
from didact.store.changeset import Changeset
from didact.store.repo import Repo

ENTRY_CORE = frozenset(
    {"id", "type", "name", "tags", "aliases", "body", "source", "page", "summary"}
)


@dataclass(frozen=True, slots=True)
class Hit:
    item: Item
    score: int


def entries(packs: PackSet, type_: str | None = None, tags: Sequence[str] = ()) -> list[Item]:
    """The entries in play: of a type, and with every one of `tags`, when they're given."""
    wanted = {normalize_name(t) for t in tags}
    found: list[Item] = []
    for item in packs.all("entry"):
        listed = item.data.get("tags")
        has = {normalize_name(str(t)) for t in listed} if isinstance(listed, list) else set()
        if (type_ is None or item.data.get("type") == type_) and wanted <= has:
            found.append(item)
    return found


def find(packs: PackSet, words: list[str], type_: str | None = None, limit: int = 20) -> list[Hit]:
    """Entries matching every word (name counts most, then tags, then any text)."""
    wanted = [w.casefold() for w in words if w.strip()]
    hits: list[Hit] = []
    for item in entries(packs, type_):
        name = str(item.data.get("name", item.id)).casefold()
        raw_tags = item.data.get("tags")
        listed = raw_tags if isinstance(raw_tags, list) else []
        tags = " ".join(str(t) for t in listed).casefold()
        text = " ".join(str(v) for v in item.data.values()).casefold()
        score = 0
        for word in wanted:
            if word in name:
                score += 3
            elif word in tags:
                score += 2
            elif word in text:
                score += 1
            else:
                score = -1
                break
        if score >= 0:
            hits.append(Hit(item, score))
    hits.sort(key=lambda h: (-h.score, str(h.item.data.get("name", h.item.id))))
    return hits[:limit]


def record_data(item: Item) -> dict[str, JSON]:
    """The entry as `new --data`: everything but its id, plus where it came from."""
    data = {k: v for k, v in item.data.items() if k not in ("id", "type", "source", "page")}
    extra = data.get("extra") if isinstance(data.get("extra"), dict) else {}
    data["extra"] = {**(extra if isinstance(extra, dict) else {}), "compendium": item.qualified}
    return data


def sheet_problems(lib: PackLibrary, bundle: dict[str, JSON], path: Path) -> list[Problem]:
    """A pack's entries against the systems' sheets, for `pack validate`: each
    `mechanics.<system>` block is checked as `spawn` checks it in a world that plays that system,
    and a note counts the blocks of a system the library doesn't have. For each system the blocks
    name that the pack doesn't require, a note counts the top-level keys its sheet and core's
    both have: they go where `set` puts them, into that system's block. A block naming the
    pack itself (a system's own entries) is checked against the pack in `path`, not against
    whatever copy of it the library has."""
    from didact.core.i18n import ngettext
    from didact.schema.sheet import Sheet, check
    from didact.services.records import DATA_KEYS
    from didact.services.sheets import stated

    manifest = cast(dict[str, JSON], bundle.get("manifest") or {})
    requires = cast(dict[str, JSON], manifest.get("requires") or {})
    needs = cast(list[JSON], requires.get("packs") or []) + cast(list[JSON], manifest["extends"])
    own = {str(manifest["id"]), *(parse_requirement(str(n))[0] for n in needs)}
    items = cast(dict[str, JSON], bundle.get("items") or {})
    entries = cast(dict[str, dict[str, JSON]], items.get("entry") or {})
    named = {s for e in entries.values() for s in _blocks(e["data"])}
    known = _Sheets(lib, str(manifest["id"]), _itself(lib, bundle, path, needs))
    problems: list[Problem] = []
    unchecked: dict[str, list[str]] = {}  # a system the library lacks → where its blocks are
    shared: dict[tuple[str, str, str], list[str]] = {}  # (key, system, type) → where
    for entry_id, entry in entries.items():
        data, source = cast(dict[str, JSON], entry["data"]), str(entry["source"])
        type_, blocks = str(data.get("type")), _blocks(data)
        for system, block in blocks.items():
            sh = known.get(system, type_)
            if sh is None:
                unchecked.setdefault(system, []).append(source)
            elif sh.mechanics is not None and isinstance(block, dict):
                given = {k: v for k, v in block.items() if not _rolled(v)}  # rolled at spawn
                lone = Sheet(type_, system, None, sh.mechanics)
                hint = _(
                    "what {system}'s {type} takes: `didact template {type}` in a world that "
                    "plays it",
                    system=system,
                    type=type_,
                )
                for found in check(lone, {}, {system: given}).problems:
                    message = _("{name}: {problem}", name=entry_id, problem=found)
                    problems.append(_at(source, message, hint, "error"))
        for system in sorted(named - own):
            sh = known.get(system, type_)
            if sh is None or sh.core is None or sh.mechanics is None:
                continue
            for key in data:
                if key in DATA_KEYS or key in ENTRY_CORE or stated(sh, key, blocks):
                    continue
                if sh.core.field(key) is not None and sh.mechanics.field(key) is not None:
                    shared.setdefault((key, system, type_), []).append(source)
    for system, where in unchecked.items():
        message = ngettext(
            "{n} entry's `mechanics.{system}` block isn't checked: there's no {system} pack here",
            "{n} entries' `mechanics.{system}` blocks aren't checked: there's no {system} pack "
            "here",
            len(where),
            system=system,
        )
        hint = _("with {system} installed, `didact pack validate` checks them", system=system)
        problems.append(_at(where[0], message, hint, "note"))
    for (key, system, type_), where in shared.items():
        message = ngettext(
            "{n} entry's bare `{key}` goes to {system}'s {type} field (as `set` puts it), not "
            "core's: write it under `fields:` or `mechanics:`",
            "{n} entries' bare `{key}` goes to {system}'s {type} field (as `set` puts it), not "
            "core's: write it under `fields:` or `mechanics:`",
            len(where),
            key=key,
            system=system,
            type=type_,
        )
        problems.append(_at(where[0], message, None, "note"))
    return problems


def _itself(lib: PackLibrary, bundle: dict[str, JSON], path: Path, needs: list[JSON]) -> PackSet:
    """The pack being validated as it is in its folder, with what it needs from the library
    (a copy of it there doesn't count): what a block naming it is checked against."""
    from didact.packs.library import Pack, PackRef

    manifest = cast(dict[str, JSON], bundle["manifest"])
    pack = Pack(PackRef(str(manifest["id"]), str(manifest["version"]), path, "path"), bundle)
    try:
        found = lib.resolve([str(n) for n in needs]).packs if needs else []
    except DidactError:  # what it needs isn't here: its own types, as far as they go
        found = []
    return PackSet([*(p for p in found if p.id != pack.id), pack])


@dataclass(slots=True)
class _Sheets:
    """The sheets of the systems an entry names, each system loaded once (None: not here);
    the pack being validated (`own`, `itself`) as it is in its folder."""

    lib: PackLibrary
    own: str
    itself: PackSet
    loaded: dict[str, PackSet | None] = field(default_factory=dict)
    found: dict[tuple[str, str], Sheet] = field(default_factory=dict)

    def get(self, system: str, type_: str) -> Sheet | None:
        from didact.schema.sheet import sheet_for

        if system == self.own:
            self.loaded[system] = self.itself
        if system not in self.loaded:
            try:
                self.loaded[system] = self.lib.resolve([system])
            except DidactError:
                self.loaded[system] = None
        packs = self.loaded[system]
        if packs is None:
            return None
        if (system, type_) not in self.found:
            try:
                self.found[system, type_] = sheet_for(packs, system, type_)
            except DidactError:  # a type of its that doesn't load: its own validation says why
                self.found[system, type_] = Sheet(type_, system)
        return self.found[system, type_]


def _blocks(data: JSON) -> dict[str, JSON]:
    found = data.get("mechanics") if isinstance(data, dict) else None
    return found if isinstance(found, dict) else {}


def _rolled(value: JSON) -> bool:
    """`"roll 2d8"` (or `"roll"`): a value `spawn` rolls."""
    return isinstance(value, str) and value.strip().lower().split(" ")[0] == "roll"


def _at(source: str, message: str, hint: str | None, severity: Severity) -> Problem:
    """A problem at an entry's `file:line`."""
    file, _sep, line = source.rpartition(":")
    return Problem(file, int(line) if line.isdigit() else None, message, hint, severity)


def add(cs: Changeset, pack_id: str, data: dict[str, JSON]) -> tuple[str, str]:
    """Write a homebrew entry for `pack_id`. Returns (entry id, file path relative to home)."""
    repo = cs.repo
    name, type_ = data.get("name"), data.get("type")
    if not isinstance(name, str) or not name.strip():
        raise InvalidError(
            _("an entry needs a name"),
            hint=_("e.g. {example}", example='{"name": "Bog Hag", "type": "monster"}'),
        )
    if not isinstance(type_, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", type_):
        raise InvalidError(_("an entry needs a type"), hint=_("e.g. monster, item, spell, relic"))
    entry_id = str(data.get("id") or slugify(name))
    root = pack_service.homebrew_dir(repo, pack_id) / "compendium"
    path = root / f"{entry_id}.yaml"
    ordered: dict[str, JSON] = {"id": entry_id, "type": type_, "name": name.strip()}
    ordered.update({k: v for k, v in data.items() if k not in ordered})
    cs.write(path, frontmatter.dump(frontmatter.from_plain(ordered)))
    return entry_id, repo.layout.rel(path)


def locate(packs: PackSet, ref: str, kinds: Collection[str] | None = None) -> Item:
    """An entry by `pack.id`, by bare id (in any letter case: `Shield` is `shield`), or by its
    name, else one of its aliases, when only one entry has it (two that share it: say which,
    `pack.id`); of the types `kinds` only, when they're given (what one carries, `inv add`)."""
    missing: NotFoundError | None = None
    try:
        found = packs.find("entry", ref)
        if kinds is None or found.data.get("type") in kinds:
            return found
    except NotFoundError as exc:
        missing = exc
    wanted = normalize_name(ref)
    pool = [i for i in entries(packs) if kinds is None or i.data.get("type") in kinds]
    by_id = [i for i in pool if i.id.casefold() == ref.strip().casefold()]
    by_name = [i for i in pool if normalize_name(str(i.data.get("name", ""))) == wanted]
    by_alias = [i for i in pool if wanted in {normalize_name(str(a)) for a in _aliases(i)}]
    for named in (by_id, by_name, by_alias):
        if len(named) == 1:
            return named[0]
        if named:
            options = ", ".join(sorted(i.qualified for i in named))
            raise ConflictError(
                _("several entries are called {ref}: {options}", ref=repr(ref), options=options),
                hint=_("use pack.id"),
            )
    raise missing or NotFoundError(
        _("no {kind} {ref} in {packs}", kind="entry", ref=repr(ref), packs=", ".join(packs.ids)),
        hint=_("see `didact pack info <pack>`"),
    )


def _aliases(item: Item) -> list[JSON]:
    listed = item.data.get("aliases")
    return listed if isinstance(listed, list) else []


def homebrew_file(repo: Repo, item: Item) -> Path | None:
    """The homebrew file an entry comes from, or None when it's the pack's own."""
    prefix = f"homebrew:{item.pack}/"
    if not item.source.startswith(prefix):
        return None
    root = pack_service.homebrew_dir(repo, item.pack)
    path = root / item.source.removeprefix(prefix).rpartition(":")[0]
    return path if path.resolve().is_relative_to(root.resolve()) else None


def remove(cs: Changeset, item: Item) -> tuple[str, int]:
    """Delete a homebrew entry. A file that holds other entries too keeps them.

    Returns the file (relative to the data home) and how many entries it still holds.
    """
    from didact.packs.source import read_yaml_items
    from didact.services import overrides

    path = homebrew_file(cs.repo, item)
    if path is None:
        change = code(f"didact override add entry {item.qualified} --data '{{…}}'")
        raise InvalidError(
            _(
                "{entry} is the {pack} pack's own entry ({source}), not homebrew",
                entry=item.qualified,
                pack=item.pack,
                source=item.source,
            ),
            hint=_(
                "pack content can't be deleted, but a house rule can change it: {change}",
                change=change,
            ),
        )
    ruled = [
        o for o in overrides.active(cs.repo, item.pack) if (o.kind, o.id) == ("entry", item.id)
    ]
    if ruled:  # left behind, the house rule would make a partial entry of its own
        take_back = code(f"didact override remove entry {item.qualified} --scope {ruled[0].scope}")
        raise ConflictError(
            _(
                "a house rule still changes {entry} ({scopes})",
                entry=item.qualified,
                scopes=", ".join(o.scope for o in ruled),
            ),
            hint=_("take it back first: {command}", command=take_back),
        )
    rel = cs.repo.layout.rel(path)
    rest = [doc.data for doc in read_yaml_items(path, rel) if doc.data.get("id") != item.id]
    if rest:
        cs.write(path, "---\n".join(frontmatter.dump(frontmatter.from_plain(d)) for d in rest))
    else:
        cs.delete(path)
    return rel, len(rest)
