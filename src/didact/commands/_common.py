"""Helpers shared by command modules: opening the repo, finishing changesets, showing records."""

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from didact.core import labels
from didact.core.context import Context
from didact.core.errors import InvalidError
from didact.core.i18n import _, ngettext
from didact.core.ids import Scope
from didact.core.output import JSON, Out, code, flatten
from didact.core.phrases import Phrase
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Repo

if TYPE_CHECKING:
    from didact.services.packing import Made

BODY_PREVIEW = 700


def open_repo(ctx: Context) -> Repo:
    return Repo.open(ctx)


def changeset(ctx: Context, repo: Repo, summary: str | Phrase, /, **values: JSON) -> Changeset:
    """A changeset for a command, tagged with the open turn group (for `undo --turn`). The
    summary is a message marked with `N_` and the values it names, or a phrase
    (`Changeset.say`)."""
    from didact.services import turns

    return Changeset(
        repo,
        summary="",
        command=ctx.command_line,
        reason=ctx.reason,
        turn=turns.current(repo),
    ).say(summary, **values)


def finish(
    ctx: Context,
    cs: Changeset,
    *,
    done: str,
    review: bool = False,
    yes: bool = False,
    extra: dict[str, JSON] | None = None,
    notes: list[str] | None = None,
) -> Out:
    """Apply a changeset, or preview it (--dry-run), or stage it for `didact apply` (review)."""
    data: dict[str, JSON] = dict(extra or {})
    tail = [_("note: {note}", note=n) for n in notes or []]
    if cs.is_empty():
        return Out(
            data={**data, "changed": False},
            md="\n".join([_("no changes: it already looks like that"), *tail]),
        )
    preview = cs.preview(full=ctx.detail == "full")
    files: list[JSON] = [{"path": f.path, "action": f.action} for f in cs.files]
    if ctx.dry_run:
        data |= {"dry_run": True, "summary": cs.summary, "files": files}
        return Out(data=data, md="\n".join([_("dry run: {done}", done=done), preview, *tail]))
    if review and not yes:
        change_id = cs.stage()
        data |= {"staged": change_id, "summary": cs.summary, "files": files}
        lines = [
            preview,
            _(
                "staged as {change}: apply with {apply} (or discard with {discard})",
                change=code(change_id),
                apply=code(f"didact apply {change_id}"),
                discard=code(f"didact discard {change_id}"),
            ),
        ]
        return Out(data=data, md="\n".join([*lines, *tail]))
    event = cs.apply()
    data |= {"event": event.seq, "summary": event.summary, "files": files}
    return Out(
        data=data, md="\n".join([_("✔ {done} ({event})", done=done, event=event.label), *tail])
    )


def parse_data(raw: str | None, flag: str = "--data") -> dict[str, JSON] | None:
    """A JSON object from an option such as `--data`, with a clear error if it isn't one."""
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise InvalidError(
            _("{flag} is not valid JSON: {error}", flag=flag, error=exc),
            hint=_("pass a JSON object, e.g. '{example}'", example='{"hp": 6}'),
        ) from exc
    if not isinstance(data, dict):
        raise InvalidError(
            _("{flag} must be a JSON object", flag=flag),
            hint=_("e.g. '{example}'", example='{"name": "Old Tom"}'),
        )
    return cast(dict[str, JSON], data)


def show_value(value: JSON) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def headline(entity_id: str, name: str, scope: Scope | str) -> str:
    return f"{entity_id} · {name} ({scope})"


def render_record(
    entity: Entity,
    scope: Scope,
    *,
    full: bool,
    backlinks: list[tuple[str, str]] | None = None,
    sheet: list[str] | None = None,
    handled: set[str] | None = None,
) -> str:
    """Markdown for one record: headline, sheet lines, other key: value lines, links, body.

    `handled` lists flattened keys (or key prefixes) the sheet lines already show.
    """
    lines = [headline(str(entity.id), entity.name, scope)]
    if entity.aliases:
        lines.append(f"{labels.record_key('aliases')}: " + ", ".join(entity.aliases))
    if entity.tags:
        lines.append(f"{labels.record_key('tags')}: " + ", ".join(entity.tags))
    if entity.status != "active":
        lines.append(f"{labels.record_key('status')}: {entity.status}")
    if entity.knowledge != "known":
        lines.append(f"{labels.record_key('knowledge')}: {labels.knowledge_name(entity.knowledge)}")
    if entity.archived:
        lines.append(
            f"{labels.record_key('archived')}: {labels.inline('true', labels.yes_no(True))}"
        )
    lines.extend(sheet or [])
    skip = handled or set()
    for container in ("fields", "mechanics", "extra"):
        prefix = "" if container == "fields" else f"{container}."
        for key, value in flatten(getattr(entity, container), prefix):
            if key in skip or any(key.startswith(f"{h}.") for h in skip):
                continue
            if value == {} or value == []:
                continue  # an empty block says nothing
            shown = labels.inline(key, labels.field_name(key)) if container == "fields" else key
            lines.append(f"{shown}: {show_value(value)}")
    for name, text in entity.details.items():  # a player copy holds only what they may see
        said = labels.inline(name, labels.detail_name(name))
        lines.append(
            f"{said}: {text}" if name == "looks" else _("{name}: {text} (GM)", name=said, text=text)
        )
    if entity.links:
        joined = "; ".join(f"{link.rel} → {link.to}" for link in entity.links)
        lines.append(f"{labels.record_key('links')}: {joined}")
    if backlinks:
        refs = "; ".join(f"{src} ({rel})" for src, rel in backlinks)
        lines.append(_("referenced by: {records}", records=refs))
    if full:
        lines.append(f"{labels.record_key('updated')}: {entity.updated}")
    body = entity.body.strip()
    if body:
        if not full and len(body) > BODY_PREVIEW:
            body = _("{text}… (`--detail full` shows the rest)", text=body[:BODY_PREVIEW].rstrip())
        lines += ["", body]
    return "\n".join(lines)


def scope_list(scopes: list[Scope]) -> str:
    return ", ".join(str(s) for s in scopes)


def roller(ctx: Context, repo: Repo, name: str) -> Callable[[str, str], int]:
    """Roll a field's dice through the roll log, so a rolled stat is a logged #r roll."""
    from didact.services import dice

    def roll(expression: str, field: str) -> int:
        reason = f"{name}: {field}"
        return dice.roll_number(
            repo, expression, reason=reason, command=ctx.command_line, log=not ctx.dry_run
        )

    return roll


def made_pack(pack_id: str, made: Made) -> Out:
    """What a made pack's command says: where it went, what's in it, what to look at."""
    lines = [
        _("✔ created pack {pack} in {path}", pack=pack_id, path=made.root),
        ", ".join(
            [
                ngettext("{n} compendium entry", "{n} compendium entries", made.entries),
                ngettext("{n} lore entry", "{n} lore entries", made.lore),
                ngettext("{n} file", "{n} files", len(made.files)),
            ]
        ),
        *(_("note: {note}", note=n) for n in made.notes),
        *(_("problem: {problem}", problem=p) for p in made.problems),
        _("next: read GUIDE.md and set the licence in pack.yaml before sharing it"),
    ]
    data: dict[str, JSON] = {
        "id": pack_id,
        "path": str(made.root),
        "files": list[JSON](made.files),
        "entries": made.entries,
        "lore": made.lore,
        "problems": list[JSON](made.problems),
    }
    return Out(data=data, md="\n".join(lines), ok=not made.problems)
