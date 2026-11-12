"""Maps: places, how they connect, and what the party has found.

A place is a `loc` record. Its `region` field nests it in another place, and links connect it
(`didact link loc:mill road loc:bridge`; either direction counts). Where the party is lives in
the campaign's play state. On the players' map a place is one of:

- here: where the party is (`didact visit <place>`);
- visited: `discovered: true` (visiting sets it); its exits show;
- known: the party knows of it but hasn't been;
- rumored: `knowledge: rumor`;
- hidden: `knowledge: secret`; not shown at all, and an exit leading there shows as `?`.

A path linked as `hidden path` (generators make some) only shows in the GM view until it's
found: link the places again as a plain `path` (`didact link a path b`).
"""

import re
from dataclasses import dataclass, field
from typing import cast

from didact.core.i18n import _, ngettext, pgettext
from didact.core.output import JSON
from didact.services import play, records
from didact.services.knowledge import secret_path
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Located, Repo

PLACE_TYPES = ("loc",)


def natural(name: str) -> tuple[tuple[int, int | str], ...]:
    """A sort key that puts `room 2` before `room 10`."""
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in re.split(r"(\d+)", name.casefold())
        if part
    )


@dataclass(slots=True)
class Place:
    id: str
    name: str
    knowledge: str
    visited: bool
    region: str | None
    exits: list[tuple[str, str]] = field(default_factory=list)  # (how, place id)

    def state(self, here: str | None) -> str:
        if self.id == here:
            return "here"
        if self.visited:
            return "visited"
        return {"rumor": "rumored", "secret": "secret"}.get(self.knowledge, "not visited")


def places(repo: Repo) -> dict[str, Place]:
    found: dict[str, Place] = {}
    links: list[tuple[str, str, str]] = []
    for row in repo.index().rows(repo.chain(), types=list(PLACE_TYPES)):
        fields = row.data.get("fields")
        values = fields if isinstance(fields, dict) else {}
        region = values.get("region")
        found[row.id] = Place(
            row.id,
            row.name,
            row.knowledge,
            values.get("discovered") is True,
            region if isinstance(region, str) else None,
        )
        for link in cast(list[JSON], row.data.get("links") or []):
            if isinstance(link, dict):
                target = str(link.get("to", "")).partition("@")[0]
                links.append((row.id, str(link.get("rel", "")), target))
    for source, how, target in links:
        if target in found and source in found and target != source:
            found[source].exits.append((how, target))
            found[target].exits.append((how, source))
    return found


def here(repo: Repo) -> str | None:
    if repo.active_campaign() is None:
        return None
    return play.load(repo).location


def lines(repo: Repo, *, gm: bool, within: str | None = None) -> tuple[list[str], dict[str, JSON]]:
    """The map as Markdown lines (players' view unless `gm`), plus JSON data."""
    everywhere = places(repo)
    at = here(repo)
    shown = {k: p for k, p in everywhere.items() if gm or p.knowledge != "secret"}
    hidden = len(everywhere) - len(shown)
    if at and at in everywhere:
        name = everywhere[at].name
        head = (
            _("Map · GM view · here: {name}", name=name)
            if gm
            else _("Map · what the party knows · here: {name}", name=name)
        )
    else:
        head = _("Map · GM view") if gm else _("Map · what the party knows")
    out = [head]
    children: dict[str | None, list[Place]] = {}
    for place in shown.values():
        parent = place.region if place.region in shown and place.region != place.id else None
        children.setdefault(parent, []).append(place)

    def walk(parent: str | None, depth: int) -> None:
        for place in sorted(children.get(parent, []), key=lambda p: natural(p.name)):
            out.append("  " * depth + "- " + _describe(place, at, shown, gm))
            walk(place.id, depth + 1)

    if within is not None:
        root = everywhere.get(within)
        if root is not None and root.id in shown:
            out.append("- " + _describe(root, at, shown, gm))
            walk(root.id, 1)
    else:
        walk(None, 0)
    if len(out) == 1:
        out.append(_("- no places yet: `didact new loc <name>`, then `didact visit <place>`"))
    if hidden:
        out.append(
            ngettext(
                "({n} secret place hidden; `--gm` shows them)",
                "({n} secret places hidden; `--gm` shows them)",
                hidden,
            )
        )
    data: dict[str, JSON] = {
        "here": at,
        "places": [
            {
                "id": p.id,
                "name": p.name,
                "state": p.state(at),
                "region": p.region,
                "exits": [
                    {"how": how, "to": to if to in shown else None}
                    for how, to in p.exits
                    if gm or ((p.visited or p.id == at) and not secret_path(how))
                ],
            }
            for p in shown.values()
        ],
        "hidden": hidden,
    }
    return out, data


def _describe(place: Place, at: str | None, shown: dict[str, Place], gm: bool) -> str:
    text = f"{place.name} [{place.id}] ({_state(place.state(at))})"
    if not (gm or place.visited or place.id == at):
        return text  # the party hasn't been there: its exits are unknown
    exits = [
        f"{how or pgettext('map exit', 'way')} → {shown[to].name if to in shown else '?'}"
        for how, to in place.exits
        if gm or not secret_path(how)
    ]
    if not exits:
        return text
    return _("{place} · exits: {exits}", place=text, exits=" · ".join(exits))


def _state(state: str) -> str:
    """A place's state (`Place.state`), in the reader's language."""
    shown = {
        "here": pgettext("place state", "here"),
        "visited": pgettext("place state", "visited"),
        "rumored": pgettext("place state", "rumored"),
        "secret": pgettext("place state", "secret"),
        "not visited": pgettext("place state", "not visited"),
    }
    return shown.get(state, state)


def visit(cs: Changeset, located: Located) -> list[str]:
    """The party is here now: the place (and the regions it's in) is known and visited."""
    notes: list[str] = []

    def arrive(entity: Entity) -> None:
        if entity.knowledge != "known":
            notes.append(
                _(
                    "{name} was {knowledge}; now the party knows it",
                    name=entity.name,
                    knowledge=entity.knowledge,
                )
            )
            entity.knowledge = "known"
        entity.fields["discovered"] = True

    records.edit(cs, located.path, arrive)
    everywhere = places(cs.repo)
    seen = {str(located.entity.id)}
    region = (
        everywhere[str(located.entity.id)].region if str(located.entity.id) in everywhere else None
    )
    while region is not None and region in everywhere and region not in seen:
        seen.add(region)
        if not everywhere[region].visited or everywhere[region].knowledge != "known":
            records.edit(cs, cs.repo.resolve(region).path, arrive)
        region = everywhere[region].region
    if cs.repo.active_campaign() is not None:  # where the party is belongs to a campaign
        current = play.load(cs.repo)
        current.location = str(located.entity.id)
        play.save(cs, current)
    return notes
