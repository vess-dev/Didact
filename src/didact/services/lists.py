"""The oracle's lists (threads, characters, features), kept on its state record.

The campaign's oracle names its lists and how to roll them:
`lists: {names: [threads, characters], method: sections, most: 3}`. Any other name makes a
list too (one per PC, region or theme). Entries are text; an entry listed again is weighted
(up to `most` lines). Rules roll them with `pick: "@oracle.threads"`.
"""

from dataclasses import dataclass
from typing import cast

from didact.core.errors import InvalidError, NotFoundError
from didact.core.i18n import _, ngettext
from didact.core.output import JSON
from didact.packs.library import Item
from didact.services import dice, oracles, records
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Repo
from didact.tables import lists

NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-_")


@dataclass(frozen=True, slots=True)
class Config:
    names: tuple[str, ...]
    method: str
    most: int


@dataclass(frozen=True, slots=True)
class Rolled:
    pick: lists.Pick
    rolls: list[str]
    lines: list[str]


def config(oracle: Item) -> Config:
    raw = oracle.data.get("lists")
    spec = raw if isinstance(raw, dict) else {}
    names = spec.get("names")
    method = str(spec.get("method") or "uniform")
    most = spec.get("most")
    return Config(
        tuple(str(n) for n in names) if isinstance(names, list) else (),
        method if method in lists.METHODS else "uniform",
        most if isinstance(most, int) else 3,
    )


def state(repo: Repo, oracle: Item, *, dry: bool, command: str | None) -> Entity:
    found = oracles.ensure_state(repo, oracle, dry=dry, command=command, force=True)
    assert found is not None  # forced
    return repo.resolve(found).entity


def entries(entity: Entity, name: str) -> list[str]:
    raw = entity.fields.get(name)
    return [str(e) for e in raw] if isinstance(raw, list) else []


def names(entity: Entity, cfg: Config) -> list[str]:
    """The declared lists, then any other list the state record holds."""
    extra = [k for k, v in entity.fields.items() if isinstance(v, list) and k not in cfg.names]
    return [*cfg.names, *sorted(extra)]


def check_name(name: str) -> str:
    cleaned = name.strip().lower()
    if not cleaned or set(cleaned) - NAME_CHARS:
        raise InvalidError(
            _("{name} can't name a list", name=repr(name)),
            hint=_("use letters, digits and dashes: e.g. characters-wood"),
        )
    return cleaned


def change(
    cs: Changeset, oracle: Item, name: str, entry: str, *, times: int, remove: bool, every: bool
) -> tuple[list[str], str]:
    """Add (or remove) an entry. Returns the new list and a note."""
    repo = cs.repo
    cfg = config(oracle)
    entity = state(repo, oracle, dry=False, command=cs.command)
    located = repo.resolve(str(entity.id))
    text = " ".join(entry.split())
    if not text:
        raise InvalidError(
            _("give the entry's text"),
            hint=_("e.g. `didact lists add threads 'Find the killer'`"),
        )
    note = ""
    updated: list[str] = []

    def edit(target: Entity) -> None:
        nonlocal note, updated
        current = entries(target, name)
        if remove:
            updated, gone = lists.drop(current, text, every=every)
            if not gone:
                raise NotFoundError(
                    _("{text} isn't on {name}", text=repr(text), name=name),
                    hint=_("see `didact lists show {name}`", name=name),
                )
            note = ngettext(
                "took {n} line of {text} off {name}",
                "took {n} lines of {text} off {name}",
                gone,
                text=repr(text),
                name=name,
            )
        else:
            try:
                updated = lists.add(current, text, times, cfg.most, lists.capacity(cfg.method))
            except ValueError as exc:
                raise InvalidError(str(exc), hint=_("weight it at most that many times")) from exc
            weight = sum(1 for e in updated if e.casefold() == text.casefold())
            note = (
                ngettext(
                    "{text} is on {name} ({n} line)",
                    "{text} is on {name} ({n} lines)",
                    weight,
                    text=repr(text),
                    name=name,
                )
                if weight > 1
                else _("{text} is on {name}", text=repr(text), name=name)
            )
        target.fields[name] = list[JSON](updated)

    records.edit(cs, located.path, edit)
    return updated, note


def roll(cs: Changeset, oracle: Item, name: str, *, dry: bool, command: str | None) -> Rolled:
    repo = cs.repo
    cfg = config(oracle)
    entity = state(repo, oracle, dry=dry, command=command)
    current = entries(entity, name)
    faces: list[int] = []
    labels: list[str] = []
    shown: list[str] = []
    for die in lists.dice_for(len(current), cfg.method):
        outcome = dice.roll(repo, die, reason=f"list {name}", command=command, dry=dry)
        faces.append(int(cast(int, outcome.rolled.result.value)))
        labels.append(outcome.label)
        shown.append(outcome.line)
    picked = lists.pick(current, cfg.method, faces)
    return Rolled(picked, labels, shown)
