"""The entity record: a system-agnostic core plus per-system mechanics blocks.

Front matter keys (in canonical order; defaults are omitted when writing):
    id, type, name, aliases, tags, status, knowledge, archived, links,
    fields, details, mechanics, extra, created, updated
Any other top-level keys (e.g. added by Obsidian) are preserved untouched.

`details` are short named notes for whoever runs the game: what it looks like, what it wants,
what it's doing and plans next, where it is, its history, the author's own thoughts. Players
see only `looks` (see `services.details`).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.core.ids import EntityId, check_type
from didact.core.output import JSON

type Knowledge = Literal["known", "secret", "rumor"]

KNOWLEDGE: tuple[Knowledge, ...] = ("known", "secret", "rumor")
CORE_ORDER: tuple[str, ...] = (
    "id",
    "type",
    "name",
    "aliases",
    "tags",
    "status",
    "knowledge",
    "archived",
    "links",
    "fields",
    "details",
    "mechanics",
    "extra",
    "created",
    "updated",
)
# Keys a user may set directly with `didact set` (the rest are managed by Didact).
SETTABLE_CORE = frozenset({"name", "aliases", "tags", "status", "knowledge", "archived"})


@dataclass(slots=True)
class Link:
    rel: str
    to: str  # an entity id, optionally `@scope`-qualified

    def to_data(self) -> dict[str, JSON]:
        return {"rel": self.rel, "to": self.to}


@dataclass(slots=True)
class Entity:
    """One stored record: an NPC, place, item, quest, note, PC, …"""

    id: EntityId
    name: str
    aliases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    status: str = "active"
    knowledge: Knowledge = "known"
    archived: bool = False
    links: list[Link] = field(default_factory=list)
    fields: dict[str, JSON] = field(default_factory=dict)
    details: dict[str, str] = field(default_factory=dict)  # name → note (see services.details)
    mechanics: dict[str, JSON] = field(default_factory=dict)  # system id → block
    extra: dict[str, JSON] = field(default_factory=dict)
    created: str = ""
    updated: str = ""
    other: dict[str, JSON] = field(default_factory=dict)  # unknown keys, preserved as-is
    body: str = ""

    @property
    def type(self) -> str:
        return self.id.type

    def meta(self) -> dict[str, JSON]:
        """Front matter in canonical order, without default-valued keys."""
        data: dict[str, JSON] = {"id": str(self.id), "type": self.id.type, "name": self.name}
        if self.aliases:
            data["aliases"] = list(self.aliases)
        if self.tags:
            data["tags"] = list(self.tags)
        if self.status != "active":
            data["status"] = self.status
        if self.knowledge != "known":
            data["knowledge"] = self.knowledge
        if self.archived:
            data["archived"] = True
        if self.links:
            data["links"] = [link.to_data() for link in self.links]
        if self.fields:
            data["fields"] = dict(self.fields)
        if self.details:
            data["details"] = dict[str, JSON](self.details)
        if self.mechanics:
            data["mechanics"] = dict(self.mechanics)
        if self.extra:
            data["extra"] = dict(self.extra)
        if self.created:
            data["created"] = self.created
        if self.updated:
            data["updated"] = self.updated
        data.update(self.other)
        return data

    def to_data(self) -> dict[str, JSON]:
        """Everything, for JSON output and the index."""
        data = self.meta()
        data["body"] = self.body
        return data

    @classmethod
    def from_meta(cls, meta: Mapping[str, JSON], body: str, *, where: str) -> Entity:
        """Validate plain front matter and build an entity."""
        raw_id = meta.get("id")
        if not isinstance(raw_id, str):
            raise InvalidError(
                _("missing `id`"),
                where=where,
                hint=_("add `id: type:slug`, e.g. `id: npc:sweeney`"),
            )
        entity_id = EntityId.parse(raw_id)
        check_type(entity_id.type)
        declared_type = meta.get("type", entity_id.type)
        if declared_type != entity_id.type:
            raise InvalidError(
                _(
                    "`type: {declared}` does not match id {id}",
                    declared=declared_type,
                    id=repr(raw_id),
                ),
                where=where,
                hint=_("set `type: {type}` (or change the id)", type=entity_id.type),
            )
        name = meta.get("name")
        if not isinstance(name, str) or not name.strip():
            raise InvalidError(_("missing `name`"), where=where, hint=_("add `name: …`"))
        knowledge = meta.get("knowledge", "known")
        if knowledge not in KNOWLEDGE:
            raise InvalidError(
                _("invalid knowledge {knowledge}", knowledge=repr(knowledge)),
                where=where,
                hint=_("use known, secret or rumor"),
            )
        archived = meta.get("archived", False)
        if not isinstance(archived, bool):
            raise InvalidError(
                _("`archived` must be true or false"),
                where=where,
                hint=_("archived: true, or false"),
            )
        return cls(
            id=entity_id,
            name=name.strip(),
            aliases=_str_list(meta.get("aliases"), "aliases", where),
            tags=_str_list(meta.get("tags"), "tags", where),
            status=_str(meta.get("status", "active"), "status", where),
            knowledge=knowledge,
            archived=archived,
            links=_links(meta.get("links"), where),
            fields=_map(meta.get("fields"), "fields", where),
            details=_details(meta.get("details"), where),
            mechanics=_map(meta.get("mechanics"), "mechanics", where),
            extra=_map(meta.get("extra"), "extra", where),
            created=_str(meta.get("created", ""), "created", where),
            updated=_str(meta.get("updated", ""), "updated", where),
            other={k: v for k, v in meta.items() if k not in CORE_ORDER},
            body=body,
        )


def _str(value: JSON, key: str, where: str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, int | float) and not isinstance(value, bool):
        return str(value)
    raise InvalidError(
        _("`{key}` must be text", key=key), where=where, hint=_("write it as {key}: '…'", key=key)
    )


def _str_list(value: JSON, key: str, where: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return [str(v) for v in value]
    raise InvalidError(
        _("`{key}` must be a list of text", key=key),
        where=where,
        hint=_("e.g. `{key}: [a, b]`", key=key),
    )


def _map(value: JSON, key: str, where: str) -> dict[str, JSON]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    raise InvalidError(
        _("`{key}` must be a mapping", key=key),
        where=where,
        hint=_("e.g. `{key}: {{hp: 6}}`", key=key),
    )


def _details(value: JSON, where: str) -> dict[str, str]:
    """Named notes as text: a list reads as `a, b`; empty ones are dropped."""
    found: dict[str, str] = {}
    for key, item in _map(value, "details", where).items():
        if isinstance(item, list):
            item = ", ".join(str(i) for i in item)
        if item is not None and str(item).strip():
            found[str(key)] = str(item).strip()
    return found


def _links(value: JSON, where: str) -> list[Link]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise InvalidError(
            _("`links` must be a list"),
            where=where,
            hint=_("e.g. `- {rel: ally, to: npc:tom}`"),
        )
    links: list[Link] = []
    for item in value:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("rel"), str)
            or not isinstance(item.get("to"), str)
        ):
            raise InvalidError(
                _("invalid link {item}", item=repr(item)),
                where=where,
                hint=_("links look like `{rel: ally, to: npc:tom}`"),
            )
        links.append(Link(str(item["rel"]), str(item["to"])))
    return links
