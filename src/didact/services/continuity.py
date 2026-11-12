"""`continuity`: what doesn't add up in the library here, each with the command that fixes it.

- dangling links (to records that don't exist);
- near-duplicate names of the same type (merge them?);
- the dead or gone still in play: in the party, a fight, or on the oracle's lists;
- open quests and threads that have gone quiet;
- sheets the rules would reject (stats out of range, unknown fields);
- summaries still to write, or stale after a retcon.
"""

import difflib
import re
from dataclasses import dataclass

from didact.core.i18n import _, ngettext
from didact.core.output import JSON
from didact.schema.sheet import Sheet
from didact.store.index import Row
from didact.store.repo import Repo

GONE = frozenset({"dead", "destroyed", "gone", "retired", "departed"})
DONE = frozenset({"done", "failed", "closed", "abandoned", "resolved", "complete", "completed"})
QUIET_SESSIONS = 2
MOST_PER_TYPE = 600  # name comparisons grow fast; bigger types are skipped


@dataclass(frozen=True, slots=True)
class Issue:
    kind: str
    ref: str
    text: str
    fix: str

    def to_data(self) -> dict[str, JSON]:
        return {"kind": self.kind, "ref": self.ref, "text": self.text, "fix": self.fix}


def check(repo: Repo) -> list[Issue]:
    index = repo.index()
    rows = index.rows(repo.chain())
    issues = [*_dangling(repo, rows), *_duplicates(rows), *_gone_in_play(repo, rows)]
    issues += [*_quiet(repo, rows), *_sheets(repo, rows), *_summaries(repo)]
    return issues


def _dangling(repo: Repo, rows: list[Row]) -> list[Issue]:
    here = {r.path: r for r in rows}
    return [
        Issue(
            "dangling link",
            here[path].id,
            _("{name} links to {target}, which isn't here", name=here[path].name, target=target),
            _(
                "didact link {id} --remove {target} (or create {target})",
                id=here[path].id,
                target=target,
            ),
        )
        for path, target in repo.index().broken()
        if path in here
    ]


def _fold(name: str) -> str:
    text = re.sub(r"[^a-z0-9 ]+", " ", name.casefold())
    return " ".join(w for w in text.split() if w not in ("the", "a", "an", "of"))


def _duplicates(rows: list[Row]) -> list[Issue]:
    issues: list[Issue] = []
    by_type: dict[str, list[Row]] = {}
    for row in rows:
        if row.type not in ("session", "scene", "summary", "track", "oracle"):
            by_type.setdefault(row.type, []).append(row)
    for type_, group in by_type.items():
        if len(group) > MOST_PER_TYPE:
            continue
        folded = [(_fold(r.name), r) for r in group]
        for i, (name, row) in enumerate(folded):
            for other_name, other in folded[i + 1 :]:
                if not name or not other_name:
                    continue
                same = name == other_name
                close = difflib.SequenceMatcher(None, name, other_name).ratio() >= 0.9
                if same or close:
                    issues.append(
                        Issue(
                            "near duplicate",
                            row.id,
                            _(
                                "{name} and {other} ({other_id}) may be the same {type}",
                                name=row.name,
                                other=other.name,
                                other_id=other.id,
                                type=type_,
                            ),
                            f"didact merge {other.id} {row.id}",
                        )
                    )
    return issues


def _gone_in_play(repo: Repo, rows: list[Row]) -> list[Issue]:
    from didact.services import combat, party

    gone = {r.id: r for r in rows if r.status in GONE}
    if not gone:
        return []
    issues: list[Issue] = []
    for member in party.members(repo, gm=True):
        if str(member.entity.id) in gone:
            row = gone[str(member.entity.id)]
            issues.append(
                Issue(
                    "gone but in play",
                    row.id,
                    _(
                        "{name} is {status} but still in the party",
                        name=row.name,
                        status=row.status,
                    ),
                    f"didact party remove {row.id}",
                )
            )
    fight = combat.load(repo) if repo.active_campaign() is not None else None
    for fighter in fight.order if fight is not None else []:
        if fighter.ref in gone:
            issues.append(
                Issue(
                    "gone but in play",
                    fighter.ref,
                    _(
                        "{name} is {status} but still in the fight",
                        name=fighter.name,
                        status=gone[fighter.ref].status,
                    ),
                    _("didact combat end (or take them out of the order)"),
                )
            )
    names = {row.name.casefold(): row for row in gone.values()}
    for state in (r for r in rows if r.type == "oracle"):
        fields = state.data.get("fields")
        for list_name, entries in fields.items() if isinstance(fields, dict) else []:
            for entry in entries if isinstance(entries, list) else []:
                listed = names.get(str(entry).casefold())
                if listed is not None:
                    issues.append(
                        Issue(
                            "gone but in play",
                            listed.id,
                            _(
                                "{name} is {status} but still on the {list} list",
                                name=listed.name,
                                status=listed.status,
                                list=list_name,
                            ),
                            f"didact lists drop {list_name} '{listed.name}' --all",
                        )
                    )
    return issues


def _quiet(repo: Repo, rows: list[Row]) -> list[Issue]:
    from didact.services import play

    if repo.active_campaign() is None:
        return []
    current = play.load(repo)
    if current.session <= QUIET_SESSIONS:
        return []
    since = play.session_record(repo, current.session - QUIET_SESSIONS + 1)
    started = str(since.fields.get("started") or since.created) if since is not None else ""
    issues: list[Issue] = []
    for row in rows:
        if row.type not in ("quest", "thread", "task") or row.status in DONE or not started:
            continue
        updated = str(row.data.get("updated") or "")
        if updated and updated < started:
            issues.append(
                Issue(
                    "gone quiet",
                    row.id,
                    ngettext(
                        "{name} hasn't moved in {n} session",
                        "{name} hasn't moved in {n} sessions",
                        QUIET_SESSIONS,
                        name=row.name,
                    ),
                    _("bring it back into play, or close it: didact quest done {id}", id=row.id),
                )
            )
    return issues


def _sheets(repo: Repo, rows: list[Row]) -> list[Issue]:
    from didact.services import sheets

    issues: list[Issue] = []
    cache: dict[str, Sheet] = {}
    for row in rows:
        if row.type not in cache:
            cache[row.type] = sheets.sheet(repo, row.type)
        sheet = cache[row.type]
        if sheet.empty:
            continue
        for problem in sheets.problems(row.entity(), sheet):
            issues.append(
                Issue(
                    "sheet",
                    row.id,
                    f"{row.name}: {problem}",
                    _("didact set {id} … (see `didact template {type}`)", id=row.id, type=row.type),
                )
            )
    return issues


def _summaries(repo: Repo) -> list[Issue]:
    from didact.services import play

    if repo.active_campaign() is None:
        return []
    return [
        Issue(
            "summary",
            target,
            _("summary to write: {item}", item=_("{target} ({why})", target=target, why=why))
            if why
            else _("summary to write: {item}", item=target),
            "didact summary due",
        )
        for target, why in play.due_items(repo, play.load(repo))
    ]
