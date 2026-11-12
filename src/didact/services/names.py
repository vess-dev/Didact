"""Names: roll them from the packs' name tables, and never hand out the same one twice.

Packs point at their name tables in settings (a list rolls each table and joins the results):

    settings:
      names: {npc: [first-names, surnames], place: place-names}

`name npc` rolls until it finds a name the world doesn't use yet. Used means a record's name or
alias, a name registered with `names use` (said in play but never made a record), or a name
offered before. Names LLMs overuse (Elara, Kael, …) are skipped too. `names forget` frees a
registered or offered name again. The registry is per world: `worlds/<id>/state/names.yaml`.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from didact.core.clock import now_iso
from didact.core.errors import DidactError, InvalidError, NotFoundError
from didact.core.i18n import _
from didact.core.ids import normalize_name
from didact.core.output import JSON
from didact.services import packs, tables
from didact.store import frontmatter
from didact.store.changeset import Changeset
from didact.store.repo import Repo

BATCH = 8  # candidates rolled per name wanted
CLICHES = frozenset({
    # people
    "aelar", "aldric", "alaric", "aria", "caelum", "cassian", "eldrin", "elara", "elowen",
    "evander", "kael", "kaelen", "lirael", "lyra", "mira", "nyx", "orion", "rowan", "seraphina",
    "sylas", "talia", "thorne", "vesper", "zephyr",
    # places
    "eldoria", "ravenshollow", "shadowfen", "silverbrook", "whispering woods", "brightwater",
})  # fmt: skip


def registry_path(repo: Repo) -> Path:
    world = repo.active_world()
    if world is None:
        raise InvalidError(_("names are kept per world"), hint=_("`didact world new <id>` first"))
    return repo.layout.world_dir(world.id) / "state" / "names.yaml"


def load(repo: Repo) -> dict[str, JSON]:
    path = registry_path(repo)
    text = repo.read_text(path)
    if not text:
        return {"used": [], "offered": []}
    data = frontmatter.to_plain(frontmatter.load(text, where=repo.layout.rel(path)))
    return data if isinstance(data, dict) else {"used": [], "offered": []}


def _save(cs: Changeset, data: dict[str, JSON]) -> None:
    cs.write(registry_path(cs.repo), frontmatter.dump(frontmatter.from_plain(data)))


def cliche(name: str) -> bool:
    folded = normalize_name(name)
    return folded in CLICHES or any(part in CLICHES for part in folded.split())


def taken(repo: Repo) -> dict[str, str]:
    """Every name in use here (normalized) → who or what uses it."""
    found: dict[str, str] = {}
    for row in repo.index().rows(repo.chain(), include_archived=True):
        found.setdefault(normalize_name(row.name), row.id)
        for alias in cast(list[JSON], row.data.get("aliases") or []):
            found.setdefault(normalize_name(str(alias)), _("{id} (alias)", id=row.id))
    registry = load(repo)
    for entry in cast(list[JSON], registry.get("used") or []):
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            what = entry.get("for")
            found.setdefault(
                normalize_name(str(entry["name"])),
                _("registered: {what}", what=what) if what else _("registered"),
            )
    for name in cast(list[JSON], registry.get("offered") or []):
        found.setdefault(normalize_name(str(name)), _("offered earlier by `didact name`"))
    return found


def check(repo: Repo, name: str) -> str | None:
    """Why a name isn't fresh here, or None if it is."""
    owner = taken(repo).get(normalize_name(name))
    if owner is not None:
        return _("taken: {owner}", owner=owner)
    if cliche(name):
        return _("a name LLMs overuse; roll one with `didact name <kind>`")
    return None


def tables_for(repo: Repo, kind: str) -> list[str]:
    """The name tables the enabled packs give for a kind (npc, place, …)."""
    try:
        active = packs.active(repo)
    except DidactError:
        return []
    kinds: list[str] = []
    for pack_id in active.ids:
        spec = active.get(pack_id).settings.get("names")
        heirs = [active.get(heir).settings.get("names") for heir in active.descendants(pack_id)[1:]]
        if not isinstance(spec, dict) or any(isinstance(theirs, dict) for theirs in heirs):
            continue  # a hack's name tables stand in for its base's
        kinds += [str(k) for k in spec]
        wanted = spec.get(kind)
        if isinstance(wanted, str):
            return [f"{pack_id}.{wanted}" if "." not in wanted else wanted]
        if isinstance(wanted, list):
            return [f"{pack_id}.{t}" if "." not in str(t) else str(t) for t in wanted]
    known = ", ".join(sorted(set(kinds)))
    raise NotFoundError(
        _(
            "no name tables for {kind} in the enabled packs (kinds: {known})",
            kind=repr(kind),
            known=known,
        )
        if known
        else _("no name tables for {kind} in the enabled packs (kinds: none)", kind=repr(kind)),
        hint=_("invent a name, then check it: `didact names check '<name>'`"),
    )


@dataclass(slots=True)
class Drawn:
    names: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # "Kael (overused)", "Mira (taken: npc:mira)"
    rolls: list[str] = field(default_factory=list)  # roll labels, e.g. #r12


def draw(cs: Changeset, kind: str, count: int, *, command: str | None) -> Drawn:
    """Roll fresh names and mark them offered, so they aren't offered again."""
    repo = cs.repo
    refs = tables_for(repo, kind)
    used = taken(repo)
    done = Drawn()
    wanted = max(count, 1)
    columns: list[list[str]] = []
    for ref in refs:
        outcome = tables.roll_table(
            repo, ref, times=wanted * BATCH, reason=f"name: {kind}", command=command
        )
        done.rolls.append(outcome.label)
        columns.append([r.text for r in outcome.results])
    for parts in zip(*columns, strict=True):
        name = " ".join(p.strip() for p in parts if p.strip())
        key = normalize_name(name)
        if key in used or name in done.names:
            why = used.get(key) or _("just offered")
            done.skipped.append(f"{name} ({why})")
            continue
        if cliche(name):
            done.skipped.append(_("{name} (overused)", name=name))
            continue
        done.names.append(name)
        used[key] = _("offered")
        if len(done.names) == wanted:
            break
    if not done.names:
        raise InvalidError(
            _("every {kind} name rolled is taken", kind=kind),
            hint=_("the tables may be too small; add entries"),
        )
    registry = load(repo)
    offered = [*cast(list[JSON], registry.get("offered") or []), *done.names]
    _save(cs, {**registry, "offered": offered})
    return done


def use(cs: Changeset, name: str, what: str | None) -> str | None:
    """Register a name said in play (no record yet). Returns why it isn't fresh, if it isn't."""
    repo = cs.repo
    problem = check(repo, name)
    registry = load(repo)
    entry: dict[str, JSON] = {"name": name.strip(), "at": now_iso()[:10]}
    if what:
        entry["for"] = what
    used = [*cast(list[JSON], registry.get("used") or []), entry]
    _save(cs, {**registry, "used": used})
    return problem


@dataclass(frozen=True, slots=True)
class Forgotten:
    name: str  # as it was registered or offered
    registered: list[str]  # what had it ("the ferryman"), one per registration
    offered: bool


def forget(cs: Changeset, name: str) -> Forgotten:
    """Take a name out of the registry: its registrations and any offer of it."""
    repo = cs.repo
    registry = load(repo)
    key = normalize_name(name)
    used = cast(list[JSON], registry.get("used") or [])
    offered = [str(n) for n in cast(list[JSON], registry.get("offered") or [])]

    def matches(entry: JSON) -> bool:
        return isinstance(entry, dict) and normalize_name(str(entry.get("name", ""))) == key

    gone = [e for e in used if isinstance(e, dict) and matches(e)]
    kept = [n for n in offered if normalize_name(n) != key]
    if not gone and len(kept) == len(offered):
        registered = [str(e.get("name")) for e in used if isinstance(e, dict)]
        shown = ", ".join(registered[:20]) + (", …" if len(registered) > 20 else "")
        owner = taken(repo).get(key)
        if registered and owner is not None:
            hint = _(
                "it's the name of {owner}, not a registered one; registered names: {names}",
                owner=owner,
                names=shown,
            )
        elif owner is not None:
            hint = _(
                "it's the name of {owner}, not a registered one; no names are registered yet",
                owner=owner,
            )
        elif registered:
            hint = _("registered names: {names}", names=shown)
        else:
            hint = _("no names are registered yet")
        raise NotFoundError(_("{name} isn't a registered name", name=name), hint=hint)
    left = [e for e in used if not matches(e)]
    _save(cs, {**registry, "used": left, "offered": list[JSON](kept)})
    if gone:
        spelled = str(gone[0].get("name"))
    else:
        spelled = next(n for n in offered if normalize_name(n) == key)
    return Forgotten(spelled, [str(e.get("for") or "") for e in gone], len(kept) != len(offered))


def listing(repo: Repo) -> list[str]:
    registry = load(repo)
    lines: list[str] = []
    for entry in cast(list[JSON], registry.get("used") or []):
        if isinstance(entry, dict):
            what = f" — {entry['for']}" if entry.get("for") else ""
            lines.append(f"- {entry.get('name')}{what}")
    offered = [str(n) for n in cast(list[JSON], registry.get("offered") or [])]
    return lines + ([_("offered: {names}", names=", ".join(offered))] if offered else [])
