"""Finding packs, loading their bundles, and the set of packs active in a campaign.

Packs come from three places (highest version wins; on a tie, the earlier place):
1. folders on `$DIDACT_PACK_PATH` (development, test fixtures);
2. packs installed in the data home: `packs/<id>/<version>/`;
3. the core pack, part of Didact itself.

The other packs that ship with Didact are `.didactpack` files beside it, installed on request
(`shipped()` in `didact.packs.share`).
"""

import json
import os
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Literal, cast

from didact.core.config import Config
from didact.core.errors import ConflictError, InvalidError, NotFoundError
from didact.core.i18n import _, ngettext
from didact.core.output import JSON
from didact.expr import Registry
from didact.packs.build import BUNDLE_FORMAT, MANIFEST, build, fingerprint
from didact.packs.versions import Version, parse_requirement, satisfies

type Origin = Literal["path", "installed", "bundled"]
ORIGIN_RANK: dict[Origin, int] = {"path": 0, "installed": 1, "bundled": 2}
TRUST_FILE = "trust.json"
# The kinds a bundle keeps in a section of their own instead of under `items`.
SECTIONS = {"reference": "reference", "term": "glossary"}


def _hidden_by(patterns: Sequence[str], item_id: str) -> bool:
    """Whether `hides` patterns drop an id: `*` matches any run of characters, the last pattern
    that matches decides, and one that starts with `!` keeps the item."""
    hidden = False
    for pattern in patterns:
        keep = pattern.startswith("!")
        if fnmatchcase(item_id, pattern[1:] if keep else pattern):
            hidden = not keep
    return hidden


@dataclass(frozen=True, slots=True)
class PackRef:
    """A pack found on disk (not loaded yet)."""

    id: str
    version: str
    path: Path
    origin: Origin

    @property
    def label(self) -> str:
        return f"{self.id} {self.version} ({self.origin})"


@dataclass(frozen=True, slots=True)
class Item:
    """One piece of pack content: a table, check, schema type, compendium entry, …"""

    kind: str
    pack: str
    id: str
    data: dict[str, JSON]
    source: str  # "tables/weather.yaml:3"

    @property
    def qualified(self) -> str:
        return f"{self.pack}.{self.id}"


@dataclass(slots=True)
class Pack:
    ref: PackRef
    bundle: dict[str, JSON]
    trusted: bool = False

    @property
    def id(self) -> str:
        return self.ref.id

    @property
    def version(self) -> str:
        return self.ref.version

    @property
    def manifest(self) -> dict[str, JSON]:
        return cast(dict[str, JSON], self.bundle["manifest"])

    @property
    def name(self) -> str:
        return str(self.manifest.get("name", self.id))

    @property
    def kind(self) -> str:
        return str(self.manifest.get("kind", ""))

    @property
    def alias(self) -> str:
        return str(self.bundle.get("alias", self.id))

    @property
    def extends(self) -> list[str]:
        return [str(e) for e in cast(list[JSON], self.manifest.get("extends") or [])]

    @property
    def hidden(self) -> dict[str, list[str]]:
        """The patterns of the items this pack drops from the packs it extends, by kind."""
        raw = cast(dict[str, JSON], self.manifest.get("hides") or {})
        return {k: [str(p) for p in cast(list[JSON], v or [])] for k, v in raw.items()}

    def hides(self, kind: str, item_id: str) -> bool:
        """Whether this pack drops an item of a pack it extends: the last pattern that matches
        decides, and one that starts with `!` keeps the item."""
        return _hidden_by(self.hidden.get(kind, ()), item_id)

    @property
    def requires(self) -> list[tuple[str, str]]:
        requires = cast(dict[str, JSON], self.manifest.get("requires") or {})
        return [parse_requirement(str(r)) for r in cast(list[JSON], requires.get("packs") or [])]

    @property
    def settings(self) -> dict[str, JSON]:
        return cast(dict[str, JSON], self.manifest.get("settings") or {})

    @property
    def plugins(self) -> list[str]:
        return [str(p) for p in cast(list[JSON], self.manifest.get("plugins") or [])]

    @property
    def files(self) -> dict[str, str]:
        return cast(dict[str, str], self.bundle.get("files") or {})

    def section(self, name: str) -> dict[str, JSON]:
        return cast(dict[str, JSON], self.bundle.get(name) or {})

    def _entries(self, kind: str) -> dict[str, JSON]:
        """What this pack holds of a kind, by id (reference sections and glossary terms have
        sections of their own)."""
        if kind in SECTIONS:
            return self.section(SECTIONS[kind])
        items = cast(dict[str, JSON], self.bundle.get("items") or {})
        return cast(dict[str, JSON], items.get(kind) or {})

    def has(self, kind: str, item_id: str) -> bool:
        return item_id in self._entries(kind)

    def ids(self, kind: str) -> list[str]:
        return list(self._entries(kind))

    def items(self, kind: str) -> Iterator[Item]:
        entries = self._entries(kind) if kind not in SECTIONS else {}
        for item_id, entry in entries.items():
            record = cast(dict[str, JSON], entry)
            yield Item(
                kind, self.id, item_id, cast(dict[str, JSON], record["data"]), str(record["source"])
            )

    def plugin_hashes(self) -> dict[str, str]:
        return {p: self.files.get(p, "") for p in self.plugins}

    def with_overlay(self, overlay: dict[str, JSON], label: str) -> Pack:
        """This pack plus homebrew items (same ids replace the pack's; sources say `homebrew`)."""
        items = {
            k: dict(cast(dict[str, JSON], v))
            for k, v in cast(dict[str, JSON], self.bundle.get("items") or {}).items()
        }
        for kind, entries in cast(dict[str, JSON], overlay.get("items") or {}).items():
            merged = items.setdefault(kind, {})
            for item_id, entry in cast(dict[str, JSON], entries).items():
                record = dict(cast(dict[str, JSON], entry))
                record["source"] = f"{label}/{record['source']}"
                merged[item_id] = record
        return Pack(self.ref, {**self.bundle, "items": cast(dict[str, JSON], items)}, self.trusted)


# ---------------------------------------------------------------------------- discovery


CORE = "core"


def bundled_dir() -> Path | None:
    """Where the core pack and the `.didactpack` files of the packs that ship with Didact are:
    the repository's `packs/` folder in a checkout, `didact/shipped` in an installed copy."""
    package = Path(__file__).resolve().parents[1]
    root = package.parents[1]
    checkout = root / "packs"
    if (root / "pyproject.toml").is_file() and checkout.is_dir():
        return checkout
    installed = package / "shipped"
    return installed if installed.is_dir() else None


def _pack_dirs(directory: Path) -> Iterator[Path]:
    if (directory / MANIFEST).is_file():
        yield directory
        return
    if directory.is_dir():
        for child in sorted(directory.iterdir()):
            if (child / MANIFEST).is_file():
                yield child


class PackLibrary:
    """Every pack Didact can see, and a cache of their compiled bundles."""

    def __init__(self, config: Config, *, extra: Sequence[Path] = ()) -> None:
        self.config = config
        self.extra = list(extra)
        self._refs: list[PackRef] | None = None
        self._loaded: dict[tuple[str, str, str], Pack] = {}

    @property
    def installed_dir(self) -> Path:
        return self.config.home / "packs"

    def search(self) -> list[tuple[Path, Origin]]:
        found: list[tuple[Path, Origin]] = []
        for raw in os.environ.get("DIDACT_PACK_PATH", "").split(os.pathsep):
            if raw.strip():
                found.append((Path(raw).expanduser(), "path"))
        found.extend((p, "path") for p in self.extra)
        if self.installed_dir.is_dir():
            for pack_dir in sorted(self.installed_dir.iterdir()):
                if pack_dir.is_dir():
                    found.extend((v, "installed") for v in sorted(pack_dir.iterdir()) if v.is_dir())
        bundled = bundled_dir()
        if bundled is not None and (bundled / CORE).is_dir():
            found.append((bundled / CORE, "bundled"))
        return found

    def refresh(self) -> None:
        """Look again: after a pack is installed or removed."""
        self._refs = None

    def refs(self) -> list[PackRef]:
        if self._refs is None:
            refs: list[PackRef] = []
            for directory, origin in self.search():
                for pack_dir in _pack_dirs(directory):
                    head = _peek_manifest(pack_dir / MANIFEST)
                    if head is not None:
                        refs.append(PackRef(head[0], head[1], pack_dir, origin))
            self._refs = refs
        return self._refs

    def available(self) -> dict[str, list[PackRef]]:
        """pack id → every version found, best first."""
        grouped: dict[str, list[PackRef]] = {}
        for ref in self.refs():
            grouped.setdefault(ref.id, []).append(ref)
        for versions in grouped.values():
            versions.sort(
                key=lambda r: (version_key(r.version), -ORIGIN_RANK[r.origin]), reverse=True
            )
        return dict(sorted(grouped.items()))

    def find(self, pack_id: str, spec: str = "") -> PackRef:
        versions = self.available().get(pack_id)
        if not versions:
            import difflib

            close = difflib.get_close_matches(pack_id, list(self.available()), n=3)
            hint = (
                _("did you mean {names}?", names=", ".join(close))
                if close
                else _("see `didact pack list`")
            )
            raise NotFoundError(_("no pack {pack}", pack=repr(pack_id)), hint=hint)
        for ref in versions:
            if satisfies(ref.version, spec):
                return ref
        have = ", ".join(r.version for r in versions)
        raise NotFoundError(
            _(
                "no version of pack {pack} matches {spec} (have {have})",
                pack=repr(pack_id),
                spec=repr(spec),
                have=have,
            ),
            hint=_("install a matching version with `didact pack install`"),
        )

    def load(self, ref: PackRef) -> Pack:
        key = (ref.id, ref.version, str(ref.path))
        if key in self._loaded:
            return self._loaded[key]
        bundle = self._bundle(ref)
        pack = Pack(ref, bundle, trusted=self._trusted(ref, bundle))
        self._loaded[key] = pack
        return pack

    def _bundle(self, ref: PackRef) -> dict[str, JSON]:
        cache_dir = self.config.cache / "packs"
        stamp = fingerprint(ref.path)
        cached = cache_dir / f"{ref.origin}-{ref.id}-{ref.version}-{stamp}.json"
        if cached.is_file():
            try:
                bundle = json.loads(cached.read_text(encoding="utf-8"))
                if isinstance(bundle, dict) and bundle.get("format") == BUNDLE_FORMAT:
                    return bundle
            except ValueError:
                pass
        result = build(ref.path)
        if result.bundle is None:
            count = len(result.errors)
            if result.errors:
                message = ngettext(
                    "pack {pack} {version} has {n} problem(s); first: {first}",
                    "pack {pack} {version} has {n} problem(s); first: {first}",
                    count,
                    pack=ref.id,
                    version=ref.version,
                    first=result.errors[0].text(),
                )
            else:
                message = ngettext(
                    "pack {pack} {version} has {n} problem(s)",
                    "pack {pack} {version} has {n} problem(s)",
                    count,
                    pack=ref.id,
                    version=ref.version,
                )
            raise InvalidError(
                message,
                where=str(ref.path),
                hint=_("run `didact pack validate {path}`", path=ref.path),
            )
        cache_dir.mkdir(parents=True, exist_ok=True)
        for old in cache_dir.glob(f"{ref.origin}-{ref.id}-{ref.version}-*.json"):
            old.unlink(missing_ok=True)
        cached.write_text(json.dumps(result.bundle, ensure_ascii=False), encoding="utf-8")
        return result.bundle

    # ------------------------------------------------------------------ trust

    def trust_store(self) -> dict[str, JSON]:
        path = self.installed_dir / TRUST_FILE
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def _trusted(self, ref: PackRef, bundle: dict[str, JSON]) -> bool:
        """Plugins of bundled and development packs run; installed ones need `pack trust`."""
        if ref.origin != "installed":
            return True
        manifest = cast(dict[str, JSON], bundle["manifest"])
        plugins = [str(p) for p in cast(list[JSON], manifest.get("plugins") or [])]
        if not plugins:
            return True
        entry = self.trust_store().get(f"{ref.id}@{ref.version}")
        files = cast(dict[str, str], bundle.get("files") or {})
        wanted = {p: files.get(p, "") for p in plugins}
        return isinstance(entry, dict) and entry.get("plugins") == wanted

    # ------------------------------------------------------------------ resolving a set

    def resolve(self, wanted: Sequence[str], pins: dict[str, str] | None = None) -> PackSet:
        """The packs to load for `wanted` (plus everything they require or extend), deps first."""
        order: list[Pack] = []
        state: dict[str, str] = {}  # id → "visiting" | "done"
        pins = pins or {}

        def visit(pack_id: str, spec: str, chain: tuple[str, ...]) -> None:
            if state.get(pack_id) == "done":
                existing = next(p for p in order if p.id == pack_id)
                if spec and not satisfies(existing.version, spec):
                    values = {"pack": pack_id, "spec": spec, "version": existing.version}
                    message = (
                        _(
                            "{needer} needs {pack} {spec}, but {version} is in use",
                            needer=chain[-1],
                            **values,
                        )
                        if chain
                        else _(
                            "the campaign needs {pack} {spec}, but {version} is in use", **values
                        )
                    )
                    raise ConflictError(
                        message, hint=_("install a version that satisfies every pack")
                    )
                return
            if state.get(pack_id) == "visiting":
                cycle = " → ".join([*chain, pack_id])
                raise InvalidError(
                    _("packs depend on each other in a circle: {cycle}", cycle=cycle),
                    hint=_("break the cycle"),
                )
            state[pack_id] = "visiting"
            pinned = pins.get(pack_id)
            ref = self.find(pack_id, f"=={pinned}" if pinned else spec)
            pack = self.load(ref)
            for dep_id, dep_spec in pack.requires:
                visit(dep_id, dep_spec, (*chain, pack_id))
            for base in pack.extends:
                base_id, base_spec = parse_requirement(base)
                visit(base_id, base_spec, (*chain, pack_id))
            state[pack_id] = "done"
            order.append(pack)

        for raw in wanted:
            pack_id, spec = parse_requirement(raw)
            visit(pack_id, spec, ())
        return PackSet(order)


def _peek_manifest(path: Path) -> tuple[str, str] | None:
    """(id, version) from a pack.yaml without full validation."""
    import re

    text = path.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for key in ("id", "version"):
        match = re.search(rf"^{key}:\s*['\"]?([^'\"#\s]+)", text, re.MULTILINE)
        if match:
            found[key] = match.group(1)
    if "id" not in found:
        return None
    return found["id"], found.get("version", "0.0.0")


def version_key(text: str) -> Version:
    try:
        return Version.parse(text)
    except InvalidError:
        return Version(0)


# ---------------------------------------------------------------------------- the active set


@dataclass(slots=True)
class PackSet:
    """The packs in play, dependencies first. Later packs override earlier ones they extend."""

    packs: list[Pack]
    _items: dict[str, list[Item]] = field(default_factory=dict)

    @property
    def ids(self) -> list[str]:
        return [p.id for p in self.packs]

    def get(self, pack_id: str) -> Pack:
        for pack in self.packs:
            if pack.id == pack_id:
                return pack
        raise NotFoundError(
            _("pack {pack} isn't enabled here", pack=repr(pack_id)),
            hint=_(
                "enable it with `didact pack enable {pack}` (enabled: {enabled})",
                pack=pack_id,
                enabled=", ".join(self.ids),
            ),
        )

    def descendants(self, pack_id: str) -> list[str]:
        """`pack_id` and every enabled pack that extends it, most derived last."""
        found = [pack_id]
        for pack in self.packs:
            bases = [parse_requirement(e)[0] for e in pack.extends]
            if any(b in found for b in bases) and pack.id not in found:
                found.append(pack.id)
        return found

    def all(self, kind: str) -> list[Item]:
        """The effective items of a kind: an extending pack's item replaces its base's, and the
        base's items it hides are left out."""
        if kind not in self._items:
            effective: dict[tuple[str, str], Item] = {}
            for pack in self.packs:
                for item in pack.items(kind):
                    effective[self._base_of(pack.id, item), item.id] = item
            hiders = {p.id: self._hiders(p.id, kind) for p in self.packs}
            shown = [
                i
                for i in effective.values()
                if not any(_hidden_by(h, i.id) for h in hiders[i.pack])
            ]
            self._items[kind] = sorted(shown, key=lambda i: (i.pack, i.id))
        return self._items[kind]

    def superseded(self, pack_id: str, kind: str, item_id: str) -> bool:
        """Whether a pack in play that extends `pack_id` replaces its item (the same id) or
        hides it. For what `all` doesn't list: reference sections and glossary terms."""
        heirs = [self.get(heir) for heir in self.descendants(pack_id)[1:]]
        return any(heir.has(kind, item_id) or heir.hides(kind, item_id) for heir in heirs)

    def idle_hides(self, hack: Pack) -> list[tuple[str, str]]:
        """The `hides` patterns of a pack, as (kind, pattern), that match nothing in the packs
        it extends. This set holds those packs; the hack itself needn't be in it."""
        lineage: list[str] = []
        for raw in hack.extends:
            base = parse_requirement(raw)[0]
            lineage += [*self._ancestors(base), base]
        idle: list[tuple[str, str]] = []
        for kind, patterns in hack.hidden.items():
            ids = [i for pack_id in lineage for i in self.get(pack_id).ids(kind)]
            idle += [
                (kind, pattern)
                for pattern in patterns
                if not any(fnmatchcase(i, pattern.removeprefix("!")) for i in ids)
            ]
        return idle

    def _hiders(self, pack_id: str, kind: str) -> list[list[str]]:
        """The `hides` patterns for a kind of each pack in play that extends `pack_id`."""
        heirs = [self.get(heir).hidden.get(kind) for heir in self.descendants(pack_id)[1:]]
        return [patterns for patterns in heirs if patterns]

    def _base_of(self, pack_id: str, item: Item) -> str:
        """The earliest pack in `pack_id`'s ancestry that defines the same item."""
        for ancestor in self._ancestors(pack_id):
            if self.get(ancestor).has(item.kind, item.id):
                return ancestor
        return pack_id

    def _ancestors(self, pack_id: str) -> list[str]:
        pack = self.get(pack_id)
        found: list[str] = []
        for raw in pack.extends:
            base = parse_requirement(raw)[0]
            found.extend(self._ancestors(base))
            found.append(base)
        return found

    def find(self, kind: str, ref: str) -> Item:
        """An item by `pack.id` (or `pack/id`) or by bare `id` when only one pack has it."""
        text = ref.strip().replace("/", ".")
        pack_id, dot, item_id = text.rpartition(".")
        items = self.all(kind)
        if dot:
            lineage = self.descendants(pack_id) if pack_id in self.ids else [pack_id]
            matches = [i for i in items if i.id == item_id and i.pack in lineage]
            if not matches:
                matches = [
                    i for i in items if i.id == item_id and self._base_of(i.pack, i) == pack_id
                ]
            if not matches and pack_id in self.ids:  # inherited: the nearest ancestor's item
                ancestors = self._ancestors(pack_id)
                inherited = [i for i in items if i.id == item_id and i.pack in ancestors]
                if inherited:
                    matches = [max(inherited, key=lambda i: ancestors.index(i.pack))]
        else:
            matches = [i for i in items if i.id == item_id]
        if len(matches) == 1:
            return matches[0]
        if matches:
            options = ", ".join(sorted(i.qualified for i in matches))
            raise ConflictError(
                _("{ref} is in several packs: {options}", ref=repr(ref), options=options),
                hint=_("use pack.id"),
            )
        import difflib

        names = sorted({i.id for i in items} | {i.qualified for i in items})
        close = difflib.get_close_matches(item_id if dot else text, names, n=3)
        hint = (
            _("did you mean {names}?", names=", ".join(close))
            if close
            else _("see `didact pack info <pack>`")
        )
        message = (
            _("no {kind} {ref} in {packs}", kind=kind, ref=repr(ref), packs=", ".join(self.ids))
            if self.ids
            else _("no {kind} {ref} in the enabled packs", kind=kind, ref=repr(ref))
        )
        raise NotFoundError(message, hint=hint)

    def settings(self, pack_id: str) -> dict[str, JSON]:
        """A pack's settings as played: those of the packs it extends, its own on top of them,
        and on top of those the settings of the packs in play that extend it (the hack is the
        game being played), key by key. A pack that only requires another keeps its own."""
        lineage = [*self._ancestors(pack_id), *self.descendants(pack_id)]
        merged: dict[str, JSON] = {}
        for each in dict.fromkeys(lineage):
            merged |= self.get(each).settings
        return merged

    def setting(self, pack_id: str, key: str, default: JSON = None) -> JSON:
        return self.settings(pack_id).get(key, default)

    def registry(self) -> Registry:
        """The dice registry: built-ins, pack dice/macros/chains, and trusted plugins."""
        from didact.expr import default_registry, load_plugin
        from didact.packs import dice

        registry = default_registry()
        dice.register(registry, [(p.alias, p.section("dice")) for p in self.packs])
        for pack in self.packs:
            if not pack.trusted:
                continue
            for plugin in pack.plugins:
                load_plugin(pack.ref.path / plugin, registry, namespace=pack.id)
        return registry
