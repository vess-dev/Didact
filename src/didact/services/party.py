"""The party: the campaign's PCs plus the companions and hirelings who travel with them.

Every PC of the campaign is in the party until it leaves (`party remove freya --why died`).
NPCs join with a role: `party add old-gannet --as hireling`. The roster lives in the campaign's
state (`state/party.yaml`), so a world NPC can be a hireling in one campaign and a stranger in
another. The brief shows each member's numbers; `combat start --party` brings everyone.
"""

from dataclasses import dataclass
from typing import Literal, cast

from didact.core.clock import now_iso
from didact.core.errors import ConflictError, DidactError, InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.services import state
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Repo

PARTY = "party"
type Role = Literal["pc", "companion", "hireling"]
ROLES: tuple[Role, ...] = ("pc", "companion", "hireling")


@dataclass(frozen=True, slots=True)
class Member:
    entity: Entity
    role: str


def _load(repo: Repo) -> dict[str, JSON]:
    if repo.active_campaign() is None:
        raise InvalidError(
            _("the party belongs to a campaign"), hint=_("`didact campaign new <id>`")
        )
    return state.load(repo, PARTY)


def _entries(data: dict[str, JSON], key: str) -> list[dict[str, JSON]]:
    raw = data.get(key)
    return [e for e in raw if isinstance(e, dict)] if isinstance(raw, list) else []


def members(repo: Repo, *, gm: bool = False) -> list[Member]:
    """The PCs who haven't left, then the companions and hirelings, in joining order."""
    if repo.active_campaign() is None:
        return []
    data = state.load(repo, PARTY)
    gone = {str(e.get("id")) for e in _entries(data, "left")}
    found: list[Member] = []
    seen: set[str] = set()
    for row in repo.index().rows(repo.chain()[:1], types=["pc"]):
        if row.id in gone or (row.knowledge == "secret" and not gm):
            continue
        found.append(Member(repo.located(row).entity, "pc"))
        seen.add(row.id)
    for entry in _entries(data, "members"):
        ref = str(entry.get("id"))
        if ref in seen or ref in gone:
            continue
        try:
            entity = repo.resolve(ref).entity
        except DidactError:  # the record is gone (deleted or out of scope)
            continue
        found.append(Member(entity, str(entry.get("role", "companion"))))
        seen.add(ref)
    return found


def add(cs: Changeset, entity: Entity, role: Role) -> None:
    data = _load(cs.repo)
    ref = str(entity.id)
    if role == "pc" and entity.type != "pc":
        raise InvalidError(
            _("{ref} isn't a PC", ref=ref), hint=_("NPCs join as companion or hireling")
        )
    if any(m.entity.id == entity.id for m in members(cs.repo, gm=True)):
        raise ConflictError(
            _("{name} is already in the party", name=entity.name),
            hint=_("see `didact party show`"),
        )
    left = [e for e in _entries(data, "left") if e.get("id") != ref]  # coming back
    joined = [e for e in _entries(data, "members") if e.get("id") != ref]
    if entity.type != "pc" or role != "pc":
        joined.append({"id": ref, "role": role, "since": now_iso()[:10]})
    state.plan(cs, PARTY, {**data, "members": cast(JSON, joined), "left": cast(JSON, left)})


def remove(cs: Changeset, entity: Entity, why: str | None) -> str:
    data = _load(cs.repo)
    ref = str(entity.id)
    current = next((m for m in members(cs.repo, gm=True) if m.entity.id == entity.id), None)
    if current is None:
        raise InvalidError(
            _("{name} isn't in the party", name=entity.name), hint=_("see `didact party show`")
        )
    joined = [e for e in _entries(data, "members") if e.get("id") != ref]
    left = [*_entries(data, "left"), {"id": ref, "role": current.role, "why": why or "left"}]
    state.plan(cs, PARTY, {**data, "members": cast(JSON, joined), "left": cast(JSON, left)})
    return current.role


def departed(repo: Repo) -> list[dict[str, JSON]]:
    if repo.active_campaign() is None:
        return []
    return _entries(state.load(repo, PARTY), "left")
