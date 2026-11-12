"""House rules: overrides, schema extensions, and world/campaign settings."""

import json
from typing import Annotated, Literal, cast

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.errors import InvalidError, NotFoundError
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON, Out

type Where = Literal["system", "world", "campaign"]


def _patch(data: str) -> dict[str, JSON]:
    try:
        payload = json.loads(data)
    except ValueError as exc:
        raise InvalidError(
            _("--data is not valid JSON: {error}", error=exc), hint=_("e.g. '{\"uses\": 6}'")
        ) from exc
    if not isinstance(payload, dict):
        raise InvalidError(_("--data must be a JSON object"), hint=_("e.g. '{\"uses\": 6}'"))
    return cast(dict[str, JSON], payload)


@command(
    "override add",
    summary="House rule: change a pack's table, rule, type or entry for this world (or scope)",
    writes=True,
    examples=(
        'didact override add table weather --data \'{"entries": {"6": "Ash"}}\'',
        'didact override add type pc --data \'{"fields": {"torch": {"kind": "uses", "max": 6}}}\'',
        'didact override add check save --data \'{"auto": {"1": "success"}}\' --scope campaign',
    ),
    description=(
        "Patch a pack item for a scope: system (every world using the pack), world (the\n"
        "default) or campaign. The patch deep-merges into the item: maps merge, `null`\n"
        "removes a key, lists and values replace. --replace swaps the whole item. The pack\n"
        "itself never changes; `didact override remove` takes the house rule back."
    ),
)
def override_add(
    ctx: Context,
    kind: Annotated[
        str, "table, check, action, procedure, trigger, type, entry, deck, bag", Metavar("kind")
    ],
    ref: Annotated[str, "the item: id or pack.id", Metavar("item")],
    *,
    data: Annotated[str, "the patch as JSON"],
    scope: Annotated[Where, "who it applies to"] = "world",
    replace: Annotated[bool, "replace the whole item instead of merging"] = False,
) -> Out:
    from didact.services import overrides, packs

    patch = _patch(data)
    repo = open_repo(ctx)
    item = packs.active(repo, house_rules=False).find(kind, ref)
    cs = changeset(
        ctx,
        repo,
        N_("override {kind} {item} ({scope})"),
        kind=kind,
        item=item.qualified,
        scope=str(scope),
    )
    merged = patch if replace else overrides.merge(item.data, patch)
    _check(kind, item.id, cast(dict[str, JSON], merged))  # a house rule can't break the game
    path = overrides.write(cs, scope, item.pack, kind, item.id, patch, replace=replace)
    rel = repo.layout.rel(path)
    return finish(
        ctx,
        cs,
        done=_(
            "{kind} {item} overridden for this {scope} ({path})",
            kind=kind,
            item=item.qualified,
            scope=scope,
            path=rel,
        ),
        extra={"path": rel},
    )


def _check(kind: str, item_id: str, data: dict[str, JSON]) -> None:
    """Validate the patched item like a pack item, so a house rule can't break the game."""
    from didact.packs.kinds import validator_for
    from didact.packs.source import Doc
    from didact.store import frontmatter

    validate = validator_for(kind)
    if validate is None:
        return
    text = frontmatter.dump(frontmatter.from_plain(data))
    doc = Doc(data, frontmatter.load(text, where="override"), "override", 1)
    errors = [p for p in validate(doc) if p.severity == "error"]
    if errors:
        raise InvalidError(
            _(
                "the patched {kind} {item} isn't valid: {problems}",
                kind=kind,
                item=item_id,
                problems="; ".join(p.message for p in errors),
            ),
            hint=errors[0].hint or _("fix the patch"),
        )


@command(
    "override list",
    summary="List the house rules in effect here",
    examples=("didact override list",),
)
def override_list(ctx: Context) -> Out:
    from didact.services import overrides, packs

    repo = open_repo(ctx)
    found = [
        o for p in packs.active(repo, house_rules=False).packs for o in overrides.active(repo, p.id)
    ]
    if not found:
        return Out(data={"overrides": []}, md=_("no house rules here"))
    lines = [ngettext("{n} house rule:", "{n} house rules:", len(found))]
    rows: list[JSON] = []
    for o in found:
        why = f" — {o.reason}" if o.reason else ""
        item = f"{o.kind} {o.pack}.{o.id}"
        if o.replace:
            item = _("{item} (replaces it)", item=item)
        lines.append(f"- {o.scope}: {item}{why}")
        rows.append(
            {
                "scope": o.scope,
                "kind": o.kind,
                "id": f"{o.pack}.{o.id}",
                "reason": o.reason,
                "patch": o.patch,
            }
        )
    return Out(data={"overrides": rows}, md="\n".join(lines))


@command(
    "override diff",
    summary="Show how house rules change a pack item (book → effective)",
    examples=("didact override diff table weather",),
)
def override_diff(
    ctx: Context,
    kind: Annotated[str, "the kind", Metavar("kind")],
    ref: Annotated[str, "the item", Metavar("item")],
) -> Out:
    from didact.core.output import flatten
    from didact.services import packs

    repo = open_repo(ctx)
    book = packs.active(repo, house_rules=False).find(kind, ref)
    now = packs.active(repo).find(kind, ref)
    before, after = dict(flatten(book.data)), dict(flatten(now.data))
    lines = [_("{kind} {item}: book → here", kind=kind, item=book.qualified)]
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            old = json.dumps(before[key], ensure_ascii=False) if key in before else _("(none)")
            new = json.dumps(after[key], ensure_ascii=False) if key in after else _("(removed)")
            lines.append(f"- {key}: {old} → {new}")
    if len(lines) == 1:
        lines.append(_("no house rules change it here"))
    return Out(data={"book": book.data, "effective": now.data}, md="\n".join(lines))


@command(
    "override remove",
    summary="Take a house rule back",
    writes=True,
    examples=(
        "didact override remove table weather",
        "didact override remove check save --scope campaign",
    ),
)
def override_remove(
    ctx: Context,
    kind: Annotated[str, "the kind", Metavar("kind")],
    ref: Annotated[str, "the item", Metavar("item")],
    *,
    scope: Annotated[Where, "which scope's rule"] = "world",
) -> Out:
    from didact.services import overrides, packs

    repo = open_repo(ctx)
    item = packs.active(repo, house_rules=False).find(kind, ref)
    base = overrides.root(repo, scope, item.pack)
    path = base / kind / f"{item.id}.yaml" if base else None
    if path is None or not path.is_file():
        raise NotFoundError(
            _(
                "no {scope} house rule for {kind} {item}",
                scope=scope,
                kind=kind,
                item=item.qualified,
            ),
            hint=_("see `didact override list`"),
        )
    cs = changeset(
        ctx,
        repo,
        N_("override {kind} {item} removed ({scope})"),
        kind=kind,
        item=item.qualified,
        scope=str(scope),
    )
    cs.delete(path)
    done = _(
        "removed the {scope} house rule for {kind} {item}",
        scope=scope,
        kind=kind,
        item=item.qualified,
    )
    return finish(ctx, cs, done=done)


@command(
    "schema extend",
    summary="Add your own fields to a record type (reputation, sanity, …) for this world",
    writes=True,
    examples=(
        "didact schema extend pc --field reputation=counter",
        'didact schema extend pc --field \'sanity={"kind": "resource"}\' --scope campaign',
    ),
)
def schema_extend(
    ctx: Context,
    type_: Annotated[str, "the record type", Metavar("type")],
    *,
    field: Annotated[list[str], "name=kind or name={json spec} (repeatable)", Metavar("name=kind")],
    scope: Annotated[Where, "who it applies to"] = "world",
) -> Out:
    from didact.services import overrides, packs, sheets

    repo = open_repo(ctx)
    system = sheets.active_system(repo)
    pack = system or "core"
    fields: dict[str, JSON] = {}
    for text in field:
        name, sep, spec = text.partition("=")
        if not sep or not name.strip():
            raise InvalidError(
                _("can't read --field {text}", text=repr(text)),
                hint=_("write name=kind, e.g. reputation=counter"),
            )
        fields[name.strip()] = (
            json.loads(spec) if spec.strip().startswith("{") else {"kind": spec.strip()}
        )
    active = packs.active(repo, house_rules=False)
    try:
        item = active.find("type", f"{pack}.{type_}")
        patch_base = item.data
        item_pack, item_id = item.pack, item.id
    except NotFoundError:
        patch_base, item_pack, item_id = {"type": type_}, pack, type_
    patch: dict[str, JSON] = {"fields": fields}
    if not patch_base.get("fields") and "type" not in patch_base:
        patch["type"] = type_
    merged = overrides.merge(patch_base, patch)
    _check("type", item_id, cast(dict[str, JSON], merged))
    cs = changeset(
        ctx,
        repo,
        N_("schema extend {type} ({scope}): {fields}"),
        type=type_,
        scope=str(scope),
        fields=", ".join(fields),
    )
    existing = [
        o
        for o in overrides.active(repo, item_pack)
        if o.kind == "type" and o.id == item_id and o.scope == scope
    ]
    combined = overrides.merge(existing[0].patch, patch) if existing else patch
    path = overrides.write(
        cs, scope, item_pack, "type", item_id, cast(dict[str, JSON], combined), replace=False
    )
    done = _(
        "{type} gains {fields} in this {scope} (`didact template {type}`)",
        type=type_,
        fields=", ".join(fields),
        scope=scope,
    )
    return finish(ctx, cs, done=done, extra={"path": repo.layout.rel(path), "fields": fields})


SETTINGS = {"name", "description", "system", "strictness"}


def _settings(
    ctx: Context, target: Literal["world", "campaign"], assignments: tuple[str, ...]
) -> Out:
    from didact.services import packs
    from didact.services.sheets import STRICTNESS
    from didact.store.repo import campaign_file_text, world_file_text

    repo = open_repo(ctx)
    changes: dict[str, str] = {}
    for text in assignments:
        key, sep, value = text.partition("=")
        if not sep or key.strip() not in SETTINGS:
            raise InvalidError(
                _("can't set {text}", text=repr(text)),
                hint=_("settable: {keys} (key=value)", keys=", ".join(sorted(SETTINGS))),
            )
        changes[key.strip()] = value.strip()
    if "strictness" in changes and changes["strictness"] not in STRICTNESS:
        raise InvalidError(
            _("strictness must be strict, lenient or freeform"), hint=_("e.g. strictness=lenient")
        )
    system = changes.pop("system", None)
    if system is not None and target == "campaign":
        raise InvalidError(
            _("a campaign plays its world's game system"),
            hint=_(
                "a world keeps the system it was made with; another system plays in a world "
                "of its own: `didact world new <id> --system <pack>`"
            ),
        )
    if target == "campaign":
        campaign = repo.active_campaign()
        if campaign is None:
            raise InvalidError(_("no campaign is open"), hint=_("`didact campaign open <id>`"))
        cs = changeset(
            ctx,
            repo,
            N_("campaign {campaign}: {changes}"),
            campaign=campaign.id,
            changes=", ".join(assignments),
        )
        for key, value in changes.items():
            if key in ("name", "description"):
                setattr(campaign, key, value)
            else:
                campaign.other[key] = value
        path = repo.layout.campaign_file(campaign.world, campaign.id)
        cs.write(path, campaign_file_text(campaign, repo.read_text(path)))
        done = _("campaign {id}: {changes}", id=campaign.id, changes=", ".join(assignments))
        return finish(ctx, cs, done=done)
    world = repo.require_world()
    if system is not None and system != (world.system or ""):
        if world.system:
            raise InvalidError(
                _(
                    "world {world} plays {system}: a world keeps the system it was made with",
                    world=world.id,
                    system=world.system,
                ),
                hint=_(
                    "another system plays in a world of its own: "
                    "`didact world new <id> --system <pack>`"
                ),
            )
        if not system:
            system = None  # none yet, and still none
    cs = changeset(
        ctx, repo, N_("world {world}: {changes}"), world=world.id, changes=", ".join(assignments)
    )
    notes: list[str] = []
    if system and system != world.system:  # a world without one takes its system, for good
        dropped = packs.tie_system(cs, world, system)
        notes = packs.dropped_lines(dropped)
    for key, value in changes.items():
        if key in ("name", "description"):
            setattr(world, key, value)
        else:
            world.other[key] = value
    path = repo.layout.world_file(world.id)
    cs.write(path, world_file_text(world, cs.planned_text(path)))
    done = _("world {id}: {changes}", id=world.id, changes=", ".join(assignments))
    return finish(ctx, cs, done=done, notes=notes)


@command(
    "campaign set",
    summary="Change campaign settings: name, description, strictness",
    writes=True,
    examples=("didact campaign set strictness=lenient", "didact campaign set name='The Withering'"),
)
def campaign_set(
    ctx: Context, *assignments: Annotated[str, "key=value", Metavar("key=value")]
) -> Out:
    return _settings(ctx, "campaign", assignments)


@command(
    "world set",
    summary="Change world settings: name, description, strictness; a system if it has none yet",
    writes=True,
    examples=(
        "didact world set description='Fog and frog knights'",
        "didact world set system=my-system     # only a world without a system yet: for good",
    ),
)
def world_set(ctx: Context, *assignments: Annotated[str, "key=value", Metavar("key=value")]) -> Out:
    return _settings(ctx, "world", assignments)
