"""Save points and forks: take a campaign back to an earlier moment, or branch it.

A save point names an event: `didact save 'before the dragon'` keeps the latest event's number.
Every change keeps its files' full before/after text, so the campaign's files as they were at
any event can be rebuilt by walking the log backwards.
- `rewind` writes those files back as one change, so a rewind can be undone too.
- `campaign fork --at` writes them into a new campaign.
Logs stay as they are (transcripts, the oracle log, journals: anything appended), and so do the
save points themselves: history is honest. World canon isn't touched; only the campaign is.

Once the history is cleared (`didact history --clear`), the log can't rebuild anything from
before its cut: `prune` removes the save points that went with it, and `files_at` refuses.
"""

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from didact.core.clock import now_iso
from didact.core.errors import ConflictError, InvalidError, NotFoundError
from didact.core.i18n import _
from didact.core.output import JSON, code
from didact.services import state
from didact.store import frontmatter
from didact.store.changeset import Changeset
from didact.store.events import cleared_before, rebuildable
from didact.store.repo import Repo

SAVES = "saves"


@dataclass(frozen=True, slots=True)
class SavePoint:
    label: str
    event: int
    ts: str

    def to_data(self) -> dict[str, JSON]:
        return {"label": self.label, "event": self.event, "ts": self.ts}


@dataclass(frozen=True, slots=True)
class Placed:
    """A save point, with the campaign (or world) whose saves file keeps it."""

    where: str  # e.g. "campaign withering"
    path: str  # the saves file, relative to the home
    point: SavePoint

    def to_data(self) -> dict[str, JSON]:
        return {**self.point.to_data(), "where": self.where, "path": self.path}


def _points(raw: JSON) -> list[SavePoint]:
    found: list[SavePoint] = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict):
            found.append(
                SavePoint(str(item["label"]), int(cast(int, item["event"])), str(item.get("ts")))
            )
    return found


def listing(repo: Repo) -> list[SavePoint]:
    return _points(state.load(repo, SAVES).get("saves"))


def save(cs: Changeset, label: str) -> SavePoint:
    repo = cs.repo
    name = " ".join(label.split())
    if not name:
        raise InvalidError(
            _("name the save point"), hint=_("e.g. `didact save 'before the dragon'`")
        )
    current = listing(repo)
    if any(s.label.casefold() == name.casefold() for s in current):
        raise ConflictError(
            _("there's already a save point {name}", name=repr(name)), hint=_("pick another name")
        )
    point = SavePoint(name, repo.log.last_seq(), now_iso())
    data: list[JSON] = [s.to_data() for s in [*current, point]]
    state.plan(cs, SAVES, {"saves": data})
    return point


def remove(cs: Changeset, label: str) -> SavePoint:
    """Take a save point off the campaign's list (a change like any other: undo restores it)."""
    current = listing(cs.repo)
    wanted = " ".join(label.split()).casefold()
    found = next((s for s in current if s.label.casefold() == wanted), None)
    if found is None:
        names = ", ".join(repr(s.label) for s in current)
        raise NotFoundError(
            _("no save point {label}", label=repr(label)),
            hint=_("save points: {names}", names=names)
            if names
            else _("there are none here: `didact saves`"),
        )
    data: list[JSON] = [s.to_data() for s in current if s is not found]
    state.plan(cs, SAVES, {"saves": data})
    return found


def everywhere(repo: Repo) -> list[Placed]:
    """Every save point in the home: each campaign's, and any a world keeps on its own."""
    worlds = repo.layout.worlds_dir
    if not worlds.is_dir():
        return []
    files = sorted(
        [*worlds.glob(f"*/state/{SAVES}.yaml"), *worlds.glob(f"*/campaigns/*/state/{SAVES}.yaml")]
    )
    found: list[Placed] = []
    for path in files:
        rel = repo.layout.rel(path)
        parts = rel.split("/")
        where = f"campaign {parts[3]}" if parts[2] == "campaigns" else f"world {parts[1]}"
        found += [Placed(where, rel, p) for p in _points(_load(repo, path).get("saves"))]
    return found


def _load(repo: Repo, path: Path) -> dict[str, JSON]:
    text = repo.read_text(path)
    if not text:
        return {}
    data = frontmatter.to_plain(frontmatter.load(text, where=repo.layout.rel(path)))
    return data if isinstance(data, dict) else {}


def stale(repo: Repo, cut: int) -> list[Placed]:
    """The save points the log can no longer rebuild once history before `cut` is gone."""
    return [p for p in everywhere(repo) if not rebuildable(p.point.event, cut)]


def prune(cs: Changeset, cut: int) -> list[Placed]:
    """Plan taking the save points the log can no longer rebuild off every saves file."""
    repo = cs.repo
    gone = stale(repo, cut)
    for rel in sorted({p.path for p in gone}):
        path = repo.layout.abs(rel)
        data = _load(repo, path)
        kept = [s for s in _points(data.get("saves")) if rebuildable(s.event, cut)]
        data["saves"] = [s.to_data() for s in kept]
        cs.write(path, frontmatter.dump(frontmatter.from_plain(data)))
    return gone


def find(repo: Repo, label: str) -> SavePoint:
    wanted = label.strip().casefold().lstrip("#e")
    for point in reversed(listing(repo)):
        if point.label.casefold() == label.strip().casefold():
            return point
    if wanted.isdigit():  # an event number works too: e42
        return SavePoint(f"#e{wanted}", int(wanted), "")
    names = ", ".join(s.label for s in listing(repo))
    raise NotFoundError(
        _("no save point {label}", label=repr(label)),
        hint=_("save points: {names}", names=names) if names else _("save points: none yet"),
    )


def files_at(
    repo: Repo, prefix: str, event: int, *, label: str | None = None
) -> dict[str, str | None]:
    """Every file under `prefix` (relative to the home) as it was right after `event`.

    Refuses when the history that would take is cleared (`label` names the save point).
    """
    events = repo.log.all()
    cut = cleared_before(events)
    if not rebuildable(event, cut):
        if label is not None and label != f"#e{event}":
            remove = code(shlex.join(["didact", "save", "--remove", label]))
            raise InvalidError(
                _(
                    "can't go back to {label} (#e{event}): the history before #e{cut} was cleared",
                    label=repr(label),
                    event=event,
                    cut=cut,
                ),
                hint=_(
                    "pick a later save point (`didact saves`), or remove this one: {remove}",
                    remove=remove,
                ),
            )
        raise InvalidError(
            _(
                "can't go back to #e{event}: the history before #e{cut} was cleared",
                event=event,
                cut=cut,
            ),
            hint=_("pick an event from #e{first} on (`didact history`)", first=cut - 1),
        )
    root = repo.home / prefix
    current: dict[str, str | None] = {
        repo.layout.rel(p): p.read_text(encoding="utf-8")
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }
    for past in reversed(events):
        if past.seq <= event:
            break
        for change in past.files:
            if not change.path.startswith(prefix):
                continue
            if change.append is not None:
                text = current.get(change.path) or ""
                if text.endswith(change.append):
                    text = text[: len(text) - len(change.append)]
                current[change.path] = None if change.before is None and not text else text
            else:
                current[change.path] = change.before
    return current


def _kept(path: str) -> bool:
    """What a rewind leaves alone: logs and the save points."""
    name = path.rpartition("/")[2]
    return path.endswith(".jsonl") or "/transcripts/" in path or name == f"{SAVES}.yaml"


def campaign_prefix(repo: Repo) -> str:
    campaign = repo.active_campaign()
    if campaign is None:
        raise InvalidError(
            _("save points belong to a campaign"), hint=_("`didact campaign open <id>`")
        )
    folder = repo.layout.campaign_dir(campaign.world, campaign.id)
    return repo.layout.rel(folder) + "/"


def rewind(cs: Changeset, label: str) -> tuple[SavePoint, list[str]]:
    """Put the campaign's records and state back as they were at a save point."""
    repo = cs.repo
    point = find(repo, label)
    prefix = campaign_prefix(repo)
    past = files_at(repo, prefix, point.event, label=point.label)
    changed: list[str] = []
    for path in sorted(past):
        if _kept(path):
            continue
        now = (
            (repo.home / path).read_text(encoding="utf-8") if (repo.home / path).is_file() else None
        )
        then = past[path]
        if now == then:
            continue
        if then is None:
            cs.delete(repo.home / path)
        else:
            cs.write(repo.home / path, then)
        changed.append(path)
    return point, changed


def fork(cs: Changeset, new_id: str, name: str | None, label: str | None) -> tuple[str, int]:
    """A new campaign in the same world: this one as it is, or as it was at a save point."""
    from ruamel.yaml import YAML

    from didact.core.ids import check_name_id
    from didact.core.yamlio import dump_yaml

    repo = cs.repo
    campaign = repo.active_campaign()
    if campaign is None:
        raise InvalidError(_("fork a campaign"), hint=_("`didact campaign open <id>` first"))
    check_name_id(new_id, "campaign")
    if new_id in repo.campaign_index():
        raise ConflictError(
            _("there's already a campaign {id}", id=repr(new_id)), hint=_("pick another id")
        )
    prefix = campaign_prefix(repo)
    point = find(repo, label) if label else None
    at = point.event if point is not None else repo.log.last_seq()
    target = repo.layout.rel(repo.layout.campaign_dir(campaign.world, new_id)) + "/"
    copied = 0
    past = files_at(repo, prefix, at, label=point.label if point is not None else None)
    for path, text in sorted(past.items()):
        if text is None or path.rpartition("/")[2] == f"{SAVES}.yaml":
            continue
        new_path = target + path[len(prefix) :]
        if new_path.endswith("/campaign.yaml"):
            data = cast(dict[str, JSON], YAML(typ="safe", pure=True).load(text) or {})
            data["name"] = name or f"{campaign.name} (fork)"
            data["forked_from"] = {"campaign": campaign.id, "event": at}
            text = dump_yaml(data)
        cs.write(repo.home / Path(new_path), text)
        copied += 1
    return new_id, copied
