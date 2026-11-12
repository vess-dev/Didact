"""The repository: one data home, its worlds and campaigns, scopes, entities and index."""

import copy
import difflib
from collections.abc import Collection, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from didact.core.clock import now_iso
from didact.core.config import Config
from didact.core.context import Context
from didact.core.errors import ConflictError, InvalidError, NotFoundError
from didact.core.i18n import _
from didact.core.ids import (
    GLOBAL,
    NAME_RE,
    RESERVED_TYPES,
    TYPE_RE,
    EntityId,
    Ref,
    Scope,
    check_name_id,
    normalize_name,
)
from didact.core.output import JSON
from didact.store import frontmatter, recovery
from didact.store.entity import Entity
from didact.store.events import EventLog
from didact.store.fsutil import atomic_write, exclusive_lock
from didact.store.index import Index, Row
from didact.store.layout import SCHEMA_VERSION, Layout, entity_location

WORLD_ORDER = ("id", "name", "system", "description", "created")
# Record types that belong to one playthrough rather than to the world's canon.
# Records that track play rather than the world: a bare name prefers the world's records.
BOOKKEEPING = frozenset({"session", "scene", "summary", "ruling", "note", "lore"})
CAMPAIGN_TYPES = frozenset({
    "pc", "note", "session", "scene", "summary", "quest", "thread", "task", "track", "ruling",
    "lore",
})  # fmt: skip
CAMPAIGN_ORDER = ("id", "world", "name", "system", "description", "created")


@dataclass(slots=True)
class WorldInfo:
    id: str
    name: str
    system: str | None = None
    description: str = ""
    created: str = ""
    other: dict[str, JSON] = field(default_factory=dict)

    def meta(self) -> dict[str, JSON]:
        data: dict[str, JSON] = {"id": self.id, "name": self.name}
        if self.system:
            data["system"] = self.system
        if self.description:
            data["description"] = self.description
        data["created"] = self.created
        data.update(self.other)
        return data


@dataclass(slots=True)
class CampaignInfo:
    id: str
    world: str
    name: str
    system: str | None = None
    description: str = ""
    created: str = ""
    other: dict[str, JSON] = field(default_factory=dict)

    def meta(self) -> dict[str, JSON]:
        data: dict[str, JSON] = {"id": self.id, "world": self.world, "name": self.name}
        if self.system:
            data["system"] = self.system
        if self.description:
            data["description"] = self.description
        data["created"] = self.created
        data.update(self.other)
        return data


@dataclass(slots=True)
class State:
    schema: int = SCHEMA_VERSION
    world: str | None = None
    campaign: str | None = None

    def meta(self) -> dict[str, JSON]:
        return {"schema": self.schema, "world": self.world, "campaign": self.campaign}


@dataclass(frozen=True, slots=True)
class Located:
    """An entity together with where it lives."""

    entity: Entity
    scope: Scope
    path: Path


def parse_entity(text: str, where: str) -> Entity:
    yaml_text, body = frontmatter.split(text, where=where)
    meta = frontmatter.to_plain(frontmatter.load(yaml_text, where=where), where=where)
    if not isinstance(meta, dict):
        raise InvalidError(
            _("front matter must be a mapping"),
            where=where,
            hint=_("start the file with ---, then key: value lines, then ---"),
        )
    entity = Entity.from_meta(meta, body, where=where)
    location = entity_location(where)
    if location is not None and location[1] != entity.id:
        raise InvalidError(
            _("id {id} does not match the file name", id=entity.id),
            where=where,
            hint=_(
                "rename the file to {type}/{slug}.md or fix the id",
                type=entity.id.type,
                slug=entity.id.slug,
            ),
        )
    return entity


def render_entity(entity: Entity, previous: str | None = None) -> str:
    from didact.store.entity import CORE_ORDER

    return frontmatter.render(entity.meta(), entity.body, previous=previous, order=CORE_ORDER)


class Repo:
    """Access to one data home. Cheap to create; opens the index lazily."""

    def __init__(
        self,
        config: Config,
        *,
        world: str | None = None,
        campaign: str | None = None,
        no_campaign: bool = False,
    ) -> None:
        self.config = config
        self.layout = Layout(config.home)
        self.log = EventLog(self.layout.log_file)
        self._world_override = world
        self._campaign_override = campaign
        self._no_campaign = no_campaign  # the world as a campaign new to it sees it
        self._index: Index | None = None
        self._state: State | None = None

    @classmethod
    def open(cls, ctx: Context) -> Repo:
        repo = cls(ctx.config, world=ctx.world, campaign=ctx.campaign)
        if repo.layout.applying_file.exists():  # being written (the lock waits) or cut short
            with exclusive_lock(repo.layout.lock_file):
                gone = repo._recover()
            if gone is not None:
                ctx.notices.extend(gone.notices())
        return repo

    def close(self) -> None:
        if self._index is not None:
            self._index.close()
            self._index = None

    # ------------------------------------------------------------------ setup & state

    @property
    def home(self) -> Path:
        return self.layout.home

    def initialized(self) -> bool:
        return self.layout.state_file.exists()

    def init(self) -> bool:
        """Create the data-home layout. Returns False if it already existed."""
        created = not self.initialized()
        for directory in (
            self.layout.global_root,
            self.layout.systems_dir,
            self.layout.worlds_dir,
            self.layout.packs_dir,
            self.layout.log_file.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        if created:
            self.save_state(State())
        return created

    def require_init(self) -> None:
        if not self.initialized():
            self.init()

    @contextmanager
    def writing(self) -> Iterator[None]:
        """Hold the data-home lock (one writer at a time), having cleared up after any change a
        crash cut short."""
        with exclusive_lock(self.layout.lock_file):
            self._recover()
            yield

    def _recover(self) -> recovery.TakenBack | None:
        gone = recovery.recover(self.layout, self.log)
        if gone is not None:
            self.refresh_index([c.path for c in gone.event.files])
        return gone

    def state(self) -> State:
        if self._state is None:
            if not self.layout.state_file.exists():
                self._state = State()
            else:
                data = _load_yaml_mapping(self.layout.state_file)
                self._state = State(
                    schema=int(_int(data.get("schema", SCHEMA_VERSION))),
                    world=_opt_str(data.get("world")),
                    campaign=_opt_str(data.get("campaign")),
                )
        return self._state

    def save_state(self, state: State) -> None:
        """The active world/campaign is a preference, not game data: it isn't event-logged."""
        text = frontmatter.dump(frontmatter.from_plain(state.meta()))
        atomic_write(self.layout.state_file, text)
        self._state = state

    # ------------------------------------------------------------------ worlds & campaigns

    def world_ids(self) -> list[str]:
        if not self.layout.worlds_dir.exists():
            return []
        return sorted(
            p.name
            for p in self.layout.worlds_dir.iterdir()
            if (p / "world.yaml").is_file() and NAME_RE.match(p.name)
        )

    def load_world(self, world_id: str) -> WorldInfo:
        path = self.layout.world_file(world_id)
        if not path.is_file():
            raise NotFoundError(
                _("no world {world}", world=repr(world_id)),
                hint=_suggest(world_id, self.world_ids(), "didact world list"),
            )
        data = _load_yaml_mapping(path)
        return WorldInfo(
            id=world_id,
            name=str(data.get("name") or world_id),
            system=_opt_str(data.get("system")),
            description=str(data.get("description") or ""),
            created=str(data.get("created") or ""),
            other={k: v for k, v in data.items() if k not in WORLD_ORDER},
        )

    def campaign_index(self) -> dict[str, str]:
        """campaign id → world id, for every campaign in the home."""
        found: dict[str, str] = {}
        for world_id in self.world_ids():
            campaigns_dir = self.layout.world_dir(world_id) / "campaigns"
            if not campaigns_dir.is_dir():
                continue
            for path in campaigns_dir.iterdir():
                if (path / "campaign.yaml").is_file() and NAME_RE.match(path.name):
                    found[path.name] = world_id
        return found

    def load_campaign(self, campaign_id: str) -> CampaignInfo:
        campaigns = self.campaign_index()
        world_id = campaigns.get(campaign_id)
        if world_id is None:
            raise NotFoundError(
                _("no campaign {campaign}", campaign=repr(campaign_id)),
                hint=_suggest(campaign_id, list(campaigns), "didact campaign list"),
            )
        data = _load_yaml_mapping(self.layout.campaign_file(world_id, campaign_id))
        return CampaignInfo(
            id=campaign_id,
            world=world_id,
            name=str(data.get("name") or campaign_id),
            system=_opt_str(data.get("system")),
            description=str(data.get("description") or ""),
            created=str(data.get("created") or ""),
            other={k: v for k, v in data.items() if k not in CAMPAIGN_ORDER},
        )

    def active_campaign(self) -> CampaignInfo | None:
        if self._no_campaign:
            return None  # none open in this view, whatever the state says
        if self._campaign_override:
            return self.load_campaign(self._campaign_override)
        state = self.state()
        if state.campaign is None or state.campaign not in self.campaign_index():
            return None  # none active, or it was deleted: nothing is active
        campaign = self.load_campaign(state.campaign)
        if self._world_override and campaign.world != self._world_override:
            return None  # --world points elsewhere; the active campaign doesn't apply
        return campaign

    def active_world(self) -> WorldInfo | None:
        if self._world_override:
            return self.load_world(self._world_override)
        campaign = self.active_campaign()
        if campaign is not None:
            return self.load_world(campaign.world)
        state = self.state()
        if not state.world or state.world not in self.world_ids():
            return None  # none active, or it was deleted
        return self.load_world(state.world)

    def require_world(self) -> WorldInfo:
        world = self.active_world()
        if world is None:
            raise InvalidError(
                _("no active world"),
                hint=_(
                    "create one with `didact world new <id>` "
                    "or pick one with `didact world use <id>`"
                ),
            )
        return world

    # ------------------------------------------------------------------ scopes

    def chain(self) -> list[Scope]:
        """The scopes visible right now, narrowest first."""
        scopes: list[Scope] = []
        campaign = self.active_campaign()
        world = self.active_world()
        if campaign is not None:
            scopes.append(Scope("campaign", campaign.id))
        if world is not None:
            scopes.append(Scope("world", world.id))
        system = (campaign.system if campaign and campaign.system else None) or (
            world.system if world else None
        )
        if system:
            scopes.append(Scope("system", system))
        scopes.append(GLOBAL)
        return scopes

    def all_scopes(self) -> list[Scope]:
        scopes = [GLOBAL]
        if self.layout.systems_dir.is_dir():
            scopes += [
                Scope("system", p.name)
                for p in sorted(self.layout.systems_dir.iterdir())
                if p.is_dir() and NAME_RE.match(p.name)
            ]
        for world_id in self.world_ids():
            scopes.append(Scope("world", world_id))
        scopes += [Scope("campaign", c) for c in sorted(self.campaign_index())]
        return scopes

    def world_family(self, world_id: str) -> list[Scope]:
        """A world plus all of its campaigns."""
        campaigns = sorted(c for c, w in self.campaign_index().items() if w == world_id)
        return [Scope("world", world_id), *(Scope("campaign", c) for c in campaigns)]

    def scope_root(self, scope: Scope) -> Path:
        match scope.kind:
            case "global":
                return self.layout.global_root
            case "system":
                return self.layout.systems_dir / str(scope.name)
            case "world":
                return self.layout.world_dir(str(scope.name))
            case "campaign":
                world_id = self.campaign_index().get(str(scope.name))
                if world_id is None:
                    raise NotFoundError(
                        _("no campaign {campaign}", campaign=repr(scope.name)),
                        hint=_("see `didact campaign list`"),
                    )
                return self.layout.campaign_dir(world_id, str(scope.name))

    def check_scope(self, scope: Scope) -> Scope:
        """Make sure a scope can hold records (systems are created on demand)."""
        match scope.kind:
            case "world":
                self.load_world(str(scope.name))
            case "campaign":
                self.load_campaign(str(scope.name))
            case _:
                pass
        return scope

    def default_scope(self, entity_type: str) -> Scope:
        """Where `new` puts a record when no --scope is given."""
        campaign = self.active_campaign()
        if entity_type in CAMPAIGN_TYPES and campaign is not None:
            return Scope("campaign", campaign.id)
        world = self.active_world()
        if world is not None:
            return Scope("world", world.id)
        raise InvalidError(
            _("no active world to put this in"),
            hint=_(
                "create one with `didact world new <id>`, pick one with `didact world use <id>`, "
                "or pass --scope global"
            ),
        )

    # ------------------------------------------------------------------ entity files

    def entity_path(self, scope: Scope, entity_id: EntityId) -> Path:
        return self.scope_root(scope) / entity_id.type / f"{entity_id.slug}.md"

    def entity_files(self, scopes: Sequence[Scope] | None = None) -> Iterator[tuple[Scope, str]]:
        """(scope, home-relative path) for every entity file in the given scopes (default: all)."""
        for scope in self.all_scopes() if scopes is None else scopes:
            try:
                root = self.scope_root(scope)
            except NotFoundError:
                continue
            if not root.is_dir():
                continue
            for type_dir in sorted(root.iterdir()):
                if (
                    not type_dir.is_dir()
                    or not TYPE_RE.match(type_dir.name)
                    or type_dir.name in RESERVED_TYPES
                ):
                    continue
                for path in sorted(type_dir.glob("*.md")):
                    rel = self.layout.rel(path)
                    if entity_location(rel) is not None:
                        yield scope, rel

    def read_text(self, path: Path) -> str | None:
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def load_entity(self, path: Path) -> Entity:
        text = self.read_text(path)
        if text is None:
            raise NotFoundError(
                _("no file {path}", path=self.layout.rel(path)),
                hint=_("it was moved or deleted: `didact reindex` catches up"),
            )
        return parse_entity(text, self.layout.rel(path))

    # ------------------------------------------------------------------ index & lookup

    def index(self) -> Index:
        if self._index is None:
            self._index = Index(self.config.index_path, self.home)
            self._index.sync(self.entity_files(), parse_entity)
        return self._index

    def refresh_index(self, rel_paths: Sequence[str]) -> None:
        if self._index is None:
            return  # the next open() syncs anyway
        changes: list[tuple[str, Scope | None]] = []
        for rel in rel_paths:
            location = entity_location(rel)
            changes.append((rel, location[0] if location else None))
        self._index.refresh(changes, parse_entity)

    def located(self, row: Row) -> Located:
        path = self.layout.abs(row.path)
        return Located(self.load_entity(path), row.scope, path)

    def resolve(
        self,
        text: str,
        *,
        scopes: Sequence[Scope] | None = None,
        of: str | Collection[str] | None = None,
    ) -> Located:
        """Find one entity by id (`npc:tom`, `npc:tom@world:vale`), name or alias.

        Searches the given scopes (default: the active chain), narrowest first. `of`: a name
        finds only a record of that type, or those types, when one has it (a foe's card, not the
        pool named after it; `track roll` the pool); a name none of them has, as before.
        """
        chain = list(self.chain() if scopes is None else scopes)
        index = self.index()
        text = text.strip()
        if EntityId.looks_like(text.partition("@")[0]):
            ref = Ref.parse(text)
            search = [ref.scope] if ref.scope else chain
            rows = index.by_id(str(ref.id), search)
            if rows:
                return self.located(_narrowest(rows, search))
            # fall through: an old id kept as an alias still resolves
        rows = index.by_name(text, chain)
        if of is not None:  # the type asked for, if any has the name (a `ref` parameter's `to:`)
            types = {of} if isinstance(of, str) else set(of)
            rows = [r for r in rows if r.type in types] or rows
        if len({r.id for r in rows}) > 1:  # a scene titled "Wolf" doesn't shadow the wolf
            story = [r for r in rows if r.type not in BOOKKEEPING]
            rows = story or rows
        if rows:
            distinct = {r.id for r in rows}
            if len(distinct) == 1:
                return self.located(_narrowest(rows, chain))
            options = ", ".join(sorted(f"{r.id} ({r.name}, {r.scope})" for r in rows))
            raise ConflictError(
                _("{text} matches several records: {options}", text=repr(text), options=options),
                hint=_("use the id instead"),
            )
        raise NotFoundError(
            _(
                "nothing called {text} in {scopes}",
                text=repr(text),
                scopes=", ".join(map(str, chain)),
            ),
            hint=self._hint_for(text, chain),
        )

    def _hint_for(self, text: str, chain: Sequence[Scope]) -> str:
        index = self.index()
        candidates = index.similar_names(text, chain)
        if not candidates:
            names = {normalize_name(r.name): r for r in index.rows(chain)}
            close = difflib.get_close_matches(normalize_name(text), list(names), n=3, cutoff=0.6)
            candidates = [names[c] for c in close]
        if candidates:
            return _(
                "did you mean {options}?",
                options=_either([f"`{r.id}` ({r.name})" for r in candidates[:3]]),
            )
        return _("check the spelling, or search with `didact find <words>`")

    def exists(self, scope: Scope, entity_id: EntityId) -> bool:
        return self.entity_path(scope, entity_id).is_file()

    def ensure_new(self, scope: Scope, entity_id: EntityId) -> None:
        if self.exists(scope, entity_id):
            raise ConflictError(
                _("{id} already exists in {scope}", id=entity_id, scope=scope),
                hint=_(
                    "see it with `didact show {id}`, or choose another id with --id", id=entity_id
                ),
            )

    def touch(self, entity: Entity, *, created: bool = False) -> Entity:
        stamp = now_iso()
        if created or not entity.created:
            entity.created = entity.created or stamp
        entity.updated = stamp
        return entity


def _narrowest(rows: Sequence[Row], chain: Sequence[Scope]) -> Row:
    order = {scope: i for i, scope in enumerate(chain)}
    return min(rows, key=lambda r: order.get(r.scope, len(order)))


def _suggest(value: str, options: Sequence[str], command: str) -> str:
    close = difflib.get_close_matches(value, list(options), n=3)
    if close:
        return _("did you mean {options}?", options=_either([f"`{c}`" for c in close]))
    return _("see `{command}`", command=command)


def _either(options: Sequence[str]) -> str:
    """`a`, `a or b`, `a or b or c` (at most three)."""
    match options:
        case [one]:
            return one
        case [first, second]:
            return _("{first} or {second}", first=first, second=second)
        case _:
            return _(
                "{first} or {second} or {third}",
                first=options[0],
                second=options[1],
                third=options[2],
            )


_YAML_CACHE: dict[Path, tuple[tuple[int, int, int], dict[str, JSON]]] = {}


def _load_yaml_mapping(path: Path) -> dict[str, JSON]:
    """A world's or campaign's YAML, parsed once per version of the file (a copy each time)."""
    info = path.stat()
    stamp = (info.st_mtime_ns, info.st_size, info.st_ino)
    cached = _YAML_CACHE.get(path)
    if cached is not None and cached[0] == stamp:
        return copy.deepcopy(cached[1])
    rel = path.name
    node = frontmatter.load(path.read_text(encoding="utf-8"), where=rel)
    data = frontmatter.to_plain(node, where=rel)
    assert isinstance(data, dict)
    _YAML_CACHE[path] = (stamp, copy.deepcopy(data))
    return data


def _opt_str(value: JSON) -> str | None:
    return value if isinstance(value, str) and value else None


def _int(value: JSON) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise InvalidError(
        _("expected a number, got {value}", value=repr(value)),
        hint=_("fix that value in the world's or campaign's file"),
    )


def world_file_text(info: WorldInfo, previous: str | None = None) -> str:
    return _yaml_doc(info.meta(), WORLD_ORDER, previous)


def campaign_file_text(info: CampaignInfo, previous: str | None = None) -> str:
    return _yaml_doc(info.meta(), CAMPAIGN_ORDER, previous)


def _yaml_doc(data: dict[str, JSON], order: Sequence[str], previous: str | None) -> str:
    if previous is not None:
        node = frontmatter.load(previous, where="(previous)")
        frontmatter.sync(node, data, order)
        return frontmatter.dump(node)
    return frontmatter.dump(frontmatter.from_plain(data))


def check_world_id(value: str) -> str:
    return check_name_id(value, "world")
