"""Retcons: change a fact after the fact, and keep what it used to be.

    didact retcon "Sweeney is Anglwyst's son" --set sweeney.parent=npc:anglwyst --secret

1. The changes apply like `set` (checked against the sheet).
2. Old values aren't lost: each record's `extra.superseded` keeps {key, was, now, until, why},
   where `until` is the in-game time (seconds) when the old fact stopped being true.
3. The fact goes into each record's body, under `## Facts` (or `## Secrets` with `--secret`).
4. Summaries that mention a changed record are marked stale; `summary due` asks for rewrites.
5. The event says "retcon:" and carries the fact as its reason, so `audit` lists it.

The event log and the transcripts are never rewritten: a retcon is appended like any change.
"""

import re
from dataclasses import dataclass, field
from typing import cast

from didact.core.clock import now_iso
from didact.core.i18n import _
from didact.core.output import JSON
from didact.schema.sheet import Sheet
from didact.services import assign, play, records, sheets
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Located

SECRETS = "## Secrets"
FACTS = "## Facts"


@dataclass(slots=True)
class Retconned:
    record: str
    changes: list[str] = field(default_factory=list)  # "parent: (none) → npc:anglwyst"
    keys: list[str] = field(default_factory=list)  # the paths changed: fields.parent, …


def read(entity: Entity, path: tuple[str, ...]) -> JSON:
    """The value at a key path, or None."""
    head = path[0]
    if head in ("fields", "mechanics", "extra"):
        value: JSON = cast(JSON, getattr(entity, head))
        for part in path[1:]:
            value = value.get(part) if isinstance(value, dict) else None
        return value
    if head in ("name", "status", "knowledge", "archived", "body"):
        return cast(JSON, getattr(entity, head))
    if head in ("aliases", "tags"):
        return list[JSON](getattr(entity, head))
    return None


def _routed(sh: Sheet, assignment: assign.Assignment) -> tuple[str, ...]:
    if assignment.bare and not sh.empty:
        found = sh.route(assignment.key.removeprefix("fields."))
        if found is not None:
            return found
    return assignment.path


def apply(
    cs: Changeset,
    located: Located,
    assignments: list[assign.Assignment],
    fact: str,
    *,
    secret: bool,
    mode: sheets.Strictness,
) -> Retconned:
    """Change a record for a retcon: new values, the superseded old ones, and the fact."""
    sh = sheets.sheet(cs.repo, located.entity.type)
    done = Retconned(str(located.entity.id))
    until = play.load(cs.repo).seconds if cs.repo.active_campaign() is not None else None

    def change(entity: Entity) -> None:
        kept = entity.extra.get("superseded")
        superseded: list[JSON] = list(kept) if isinstance(kept, list) else []
        for assignment in assignments:
            path = _routed(sh, assignment)
            was = read(entity, path)
            note = sheets.apply(entity, assignment, sh, mode)
            now = read(entity, path)
            if was == now:
                key = ".".join(path[2:] if path[0] == "mechanics" else path[1:] or path)
                done.changes.append(
                    _("{key}: unchanged ({note})", key=key, note=note)
                    if note
                    else _("{key}: unchanged", key=key)
                )
                continue
            key = ".".join(path[2:] if path[0] == "mechanics" else path[1:] or path)
            entry: dict[str, JSON] = {"key": key, "was": was, "now": now, "why": fact}
            entry |= {"until": until} if until is not None else {"at": now_iso()[:10]}
            superseded.append(entry)
            done.keys.append(".".join(path))
            shown = f"{key}: {_show(was)} → {_show(now)}"
            done.changes.append(shown + (f" ({note})" if note else ""))
        if superseded:
            entity.extra["superseded"] = superseded
        if secret and done.keys:
            hidden = entity.extra.get("secret_keys")
            known = [str(k) for k in hidden] if isinstance(hidden, list) else []
            entity.extra["secret_keys"] = list[JSON](
                [*known, *(k for k in done.keys if k not in known)]
            )
        entity.body = add_fact(entity.body, fact, secret=secret)

    records.edit(cs, located.path, change)
    return done


def _show(value: JSON) -> str:
    if value is None or value == "":
        return _("(none)")
    if isinstance(value, dict) and "value" in value:
        return str(value["value"])
    return str(value)


def add_fact(body: str, fact: str, *, secret: bool) -> str:
    """Add `- fact` under `## Facts` (or `## Secrets`), creating the section at the end."""
    heading = SECRETS if secret else FACTS
    line = f"- {fact.strip()}"
    lines = body.rstrip("\n").splitlines()
    if heading in [x.strip() for x in lines]:
        at = [x.strip() for x in lines].index(heading)
        end = next((i for i in range(at + 1, len(lines)) if lines[i].startswith("#")), len(lines))
        while end > at + 1 and not lines[end - 1].strip():
            end -= 1
        lines.insert(end, line)
    else:
        lines += (["", heading] if lines else [heading]) + [line]
    return "\n".join(lines).strip() + "\n"


def mark_stale(cs: Changeset, names: list[str], why: str) -> list[str]:
    """Mark summaries that mention any of `names` stale. Returns the records marked."""
    repo = cs.repo
    campaign = repo.active_campaign()
    wanted = [n for n in dict.fromkeys(names) if n.strip()]
    if campaign is None or not wanted:
        return []
    pattern = re.compile(
        r"(?<![\w])(" + "|".join(re.escape(n) for n in wanted) + r")(?![\w])", re.IGNORECASE
    )
    marked: list[str] = []
    rows = repo.index().rows(repo.chain()[:1], types=["scene", "session", "summary"])
    for row in rows:
        located = repo.located(row)
        entity = located.entity
        text = play.get_summary(entity.body) or (entity.body if entity.type == "summary" else "")
        if not text or not pattern.search(text):
            continue

        def stale(target: Entity) -> None:
            target.fields["stale"] = why

        records.edit(cs, located.path, stale)
        marked.append(str(entity.id))
    return marked
