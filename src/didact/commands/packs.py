"""Pack commands: list, info, validate, enable, disable."""

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, cast

from didact.commands._common import changeset, finish, made_pack, open_repo
from didact.commands.registry import Metavar, command
from didact.core import labels
from didact.core.context import Context
from didact.core.errors import InvalidError, NotFoundError
from didact.core.i18n import N_, _, ngettext, pgettext
from didact.core.output import JSON, Out, code
from didact.store.repo import Repo

if TYPE_CHECKING:
    from didact.packs.library import PackLibrary
    from didact.packs.source import Problem


@command(
    "pack list",
    summary="List the packs Didact can see (systems, oracles, settings, supplements), and the "
    "ones that ship with it, ready to install",
    examples=("didact pack list",),
)
def pack_list(ctx: Context) -> Out:
    from didact.services import packs

    repo = open_repo(ctx)
    lib = packs.library(repo)
    enabled = set(packs.enabled(repo)) if repo.initialized() else {packs.CORE}
    from didact.packs.library import version_key
    from didact.packs.share import shipped

    ready_versions = {s.id: s.version for s in shipped()}
    rows: list[JSON] = []
    lines = []
    for pack_id, versions in lib.available().items():
        best = versions[0]
        head = _peek(best.path)
        others = ", ".join(v.version for v in versions[1:])
        mark = "  " + _("← enabled") if pack_id in enabled else ""
        more = " " + _("(also {versions})", versions=others) if others else ""
        newer = ready_versions.get(pack_id)
        installed = [v.version for v in versions if v.origin == "installed"]
        if not installed or newer is None or version_key(newer) <= version_key(installed[0]):
            newer = None  # an update is only offered for an installed pack
        update = (
            " "
            + _("(update: {version}, {command})", version=newer, command=code("didact pack update"))
            if newer
            else ""
        )
        kind, name = head.get("kind", "?"), head.get("name", pack_id)
        shown_kind, origin = labels.pack_kind(str(kind)), labels.pack_origin(best.origin)
        lines.append(
            f"- {pack_id} {best.version} · {shown_kind} · {name} [{origin}]{more}{update}{mark}"
        )
        rows.append(
            {
                "id": pack_id,
                "version": best.version,
                "versions": [v.version for v in versions],
                "installed": list[JSON](installed),
                "update": newer,
                "origin": best.origin,
                "kind": head.get("kind"),
                "name": head.get("name"),
                "description": head.get("description"),
                "enabled": pack_id in enabled,
                "path": str(best.path),
            }
        )
    for ready in shipped():  # ships with Didact, not installed here yet
        if ready.id in lib.available():
            continue
        how = code(f"didact pack install {ready.id}")
        lines.append(
            f"- {ready.id} {ready.version} · "
            f"{labels.pack_kind(ready.kind) if ready.kind else '?'} · "
            f"{ready.name} " + _("[ships with Didact, install: {command}]", command=how)
        )
        rows.append(
            {
                "id": ready.id,
                "version": ready.version,
                "versions": [ready.version],
                "installed": [],
                "origin": "shipped",
                "kind": ready.kind or None,
                "name": ready.name,
                "description": ready.description or None,
                "enabled": False,
                "path": str(ready.path),
            }
        )
    if not rows:
        return Out(data={"packs": []}, md=_("no packs found"))
    return Out(
        data={"packs": rows}, md="\n".join([ngettext("{n} pack:", "{n} packs:", len(rows)), *lines])
    )


def _peek(path: Path) -> dict[str, str]:
    from didact.packs.share import head_of

    return head_of((path / "pack.yaml").read_text(encoding="utf-8"))


@command(
    "pack info",
    summary="Show what a pack is and holds: manifest, license, contents, guide",
    examples=("didact pack info my-system", "didact pack info my-system --detail full"),
)
def pack_info(ctx: Context, pack_id: Annotated[str, "the pack", Metavar("pack")]) -> Out:
    from didact.packs.kinds import ALL_KINDS
    from didact.services import packs

    repo = open_repo(ctx)
    lib = packs.library(repo)
    pack = lib.load(lib.find(pack_id))
    manifest = pack.manifest
    license_ = manifest.get("license") if isinstance(manifest.get("license"), dict) else {}
    assert isinstance(license_, dict)
    counts: dict[str, int] = {}
    for kind in ALL_KINDS:
        if kind == "reference":
            counts[kind] = len(pack.section("reference"))
        elif kind == "term":
            counts[kind] = len(pack.section("glossary"))
        else:
            counts[kind] = sum(1 for _item in pack.items(kind))
    dice = pack.section("dice")
    for section in ("dice", "macros", "chains"):
        block = dice.get(section)
        counts[f"dice {section}" if section != "dice" else "named dice"] = (
            len(block) if isinstance(block, dict) else 0
        )
    held = [labels.inline(f"{n} {k}", labels.item_count(k, n)) for k, n in counts.items() if n]
    where = f"{labels.pack_origin(pack.ref.origin)}: {pack.ref.path}"
    lines = [f"{pack.id} {pack.version} · {labels.pack_kind(pack.kind)} · {pack.name} [{where}]"]
    if manifest.get("description"):
        lines.append(str(manifest["description"]).strip())
    lines.append(
        _("license: {license}", license=license_.get("spdx") or _("unspecified"))
        + (
            ""
            if license_.get("redistributable", True)
            else " · " + _("personal use only, never exported")
        )
        + (f" · {license_['attribution']}" if license_.get("attribution") else "")
    )
    if pack.extends or pack.requires:
        deps = [f"{i} {s}".strip() for i, s in pack.requires]
        lines.append(
            _(
                "requires: {requires} · extends: {extends}",
                requires=", ".join(deps) or "—",
                extends=", ".join(pack.extends) or "—",
            )
        )
    if pack.hidden:
        patterns = "; ".join(f"{kind}: {', '.join(p)}" for kind, p in pack.hidden.items())
        lines.append(_("hides: {patterns}", patterns=patterns))
    lines.append(_("expressions: {prefix}", prefix=code(pack.alias + ".…")))
    lines.append(
        _("contains: {items}", items=", ".join(held)) if held else _("contains: nothing yet")
    )
    if pack.plugins:
        state = (
            pgettext("plugins", "trusted")
            if pack.trusted
            else _("off until trusted (`didact pack trust {pack}`)", pack=pack.id)
        )
        lines.append(
            _("plugins: {plugins} ({state})", plugins=", ".join(pack.plugins), state=state)
        )
    guide = str(pack.bundle.get("guide") or "").strip()
    full = [*lines, "", guide] if guide else lines
    if guide:
        lines.append(
            _("guide: {command}", command=code("didact pack info " + pack.id + " --detail full"))
        )
    data: dict[str, JSON] = {
        "id": pack.id,
        "version": pack.version,
        "kind": pack.kind,
        "name": pack.name,
        "origin": pack.ref.origin,
        "path": str(pack.ref.path),
        "manifest": manifest,
        "contents": dict(counts),
        "trusted": pack.trusted,
        "guide": guide,
    }
    return Out(data=data, md="\n".join(lines), md_full="\n".join(full))


@command(
    "pack validate",
    summary="Check packs for problems (file:line and a fix for each)",
    examples=(
        "didact pack validate",
        "didact pack validate my-system",
        "didact pack validate ./my-hack",
    ),
)
def pack_validate(
    ctx: Context,
    target: Annotated[
        str | None, "a pack id or folder (default: every pack)", Metavar("pack")
    ] = None,
) -> Out:
    from didact.packs.build import build
    from didact.services import clock, compendium, packs

    repo = open_repo(ctx)
    lib = packs.library(repo)
    if target is None:
        paths = [versions[0].path for versions in lib.available().values()]
    elif Path(target).expanduser().is_dir():
        paths = [Path(target).expanduser()]
    else:
        paths = [lib.find(target).path]
    reports: list[JSON] = []
    lines: list[str] = []
    failed = False
    for path in paths:
        result = build(path)
        problems = [*result.problems, *_idle_hides(lib, path, result.bundle)]
        if result.bundle is not None:  # its entries against the sheets of the systems they name
            problems += compendium.sheet_problems(lib, result.bundle, path)
            declared = cast(dict[str, JSON], result.bundle["manifest"])
            problems += clock.problems(declared.get("settings"))  # its calendar
        errors = [p for p in problems if p.severity == "error"]
        warnings = [p for p in problems if p.severity == "warning"]
        failed = failed or bool(errors)
        name = path.name
        if result.bundle is not None:
            manifest = result.bundle["manifest"]
            assert isinstance(manifest, dict)
            name = f"{manifest['id']} {manifest['version']}"
        verdict = _("✔ ok") if not errors else ngettext("✘ {n} error", "✘ {n} errors", len(errors))
        if warnings:
            verdict += ", " + ngettext("{n} warning", "{n} warnings", len(warnings))
        lines.append(f"{verdict}: {name} ({path})")
        lines += [f"  - {_listed(p)}" for p in problems]
        reports.append(
            {
                "path": str(path),
                "ok": not errors,
                "problems": [p.to_data() for p in problems],
            }
        )
    if not paths:
        raise NotFoundError(_("no packs to validate"), hint=_("see `didact pack list`"))
    return Out(data={"packs": reports}, md="\n".join(lines), ok=not failed)


def _idle_hides(lib: PackLibrary, path: Path, bundle: dict[str, JSON] | None) -> list[Problem]:
    """A warning for each `hides` pattern of a hack that matches nothing in the packs it extends
    (when they're here to check against)."""
    from didact.core.errors import DidactError
    from didact.packs.build import MANIFEST
    from didact.packs.library import Pack, PackRef
    from didact.packs.source import Problem

    if bundle is None:
        return []
    hack = Pack(PackRef("", "", path, "path"), bundle)
    if not hack.hidden:
        return []
    try:
        bases = lib.resolve(hack.extends)
    except DidactError:
        return []
    return [
        Problem(
            MANIFEST,
            None,
            _(
                "`hides` {kind} pattern {pattern} matches nothing in {packs}",
                kind=kind,
                pattern=repr(pattern),
                packs=", ".join(hack.extends),
            ),
            _("remove it or check the spelling"),
            "warning",
        )
        for kind, pattern in bases.idle_hides(hack)
    ]


def _listed(problem: Problem) -> str:
    """A problem as `pack validate` and `pack lint` list it: error, warning or note, in the
    language in use, then where and what (the data keeps the severity as it is)."""
    if problem.severity == "error":
        return _("error: {problem}", problem=problem.text())
    if problem.severity == "warning":
        return _("warning: {problem}", problem=problem.text())
    return _("note: {note}", note=problem.text())


def _toggle(ctx: Context, pack_id: str, *, on: bool, scope: str | None) -> Out:
    from didact.services import packs, sheets

    repo = open_repo(ctx)
    system = sheets.active_system(repo)
    if on:
        lib = packs.library(repo)
        lib.find(pack_id)  # it must exist
        if packs.kind_of(lib, pack_id) == "system":
            return _use_system(ctx, repo, pack_id, system)
        clash = packs.conflicts(lib, system, [pack_id])
        if clash:
            world = repo.require_world()
            other = clash[pack_id]
            raise InvalidError(
                _(
                    "{pack} needs {other}, but world {world} plays {system}: one system at a time",
                    pack=pack_id,
                    other=other,
                    world=world.id,
                    system=system,
                )
                if system
                else _(
                    "{pack} needs {other}, and world {world} has no game system yet",
                    pack=pack_id,
                    other=other,
                    world=world.id,
                ),
                hint=_system_hint(repo, other)
                if system
                else _("give it {system} first: `didact pack enable {system}`", system=other),
            )
    elif pack_id == packs.CORE:
        raise InvalidError(
            _("core is always in use: every system builds on it"),
            hint=_("there's nothing to disable"),
        )
    elif pack_id == system:
        raise InvalidError(
            _("{pack} is this world's game system, for good", pack=pack_id),
            hint=_(
                "a world keeps the system it was made with; another system plays in a world "
                "of its own: `didact world new <id> --system <pack>`"
            ),
        )
    where = scope or ("campaign" if repo.active_campaign() is not None else "world")
    said = N_("enable pack {pack}") if on else N_("disable pack {pack}")
    cs = changeset(ctx, repo, said, pack=pack_id)
    target, listed = packs.set_enabled(
        cs, pack_id, on=on, where="world" if where == "world" else "campaign"
    )
    names = ", ".join(listed) or pgettext("packs", "none")
    done = (
        _("enabled {pack} in {scope} (packs: {packs})", pack=pack_id, scope=target, packs=names)
        if on
        else _(
            "disabled {pack} in {scope} (packs: {packs})", pack=pack_id, scope=target, packs=names
        )
    )
    return finish(
        ctx,
        cs,
        done=done,
        extra={"scope": target, "packs": list[JSON](listed)},
    )


def _use_system(ctx: Context, repo: Repo, pack_id: str, system: str | None) -> Out:
    """Enabling a system: it's the world's for good, so only a world without one yet takes
    it. Anywhere else, another system plays in a world of its own."""
    from didact.services import packs

    world = repo.require_world()
    if pack_id == system:
        return Out(
            data={"world": world.id, "system": pack_id, "changed": False},
            md=_("{pack} is already this world's game system", pack=pack_id),
        )
    if system is not None:
        raise InvalidError(
            _(
                "world {world} plays {system}: a world keeps the system it was made with",
                world=world.id,
                system=system,
            ),
            hint=_system_hint(repo, pack_id),
        )
    cs = changeset(ctx, repo, N_("world {world} plays {system}"), world=world.id, system=pack_id)
    dropped = packs.tie_system(cs, world, pack_id)
    notes = packs.dropped_lines(dropped)
    done = _("world {world} plays {system} now, for good", world=world.id, system=pack_id)
    extra: dict[str, JSON] = {"world": world.id, "system": pack_id, "dropped": list[JSON](dropped)}
    return finish(ctx, cs, done=done, extra=extra, notes=notes)


def _system_hint(repo: Repo, pack_id: str) -> str:
    """Where a system plays: the worlds made with it, or a new one."""
    from didact.services import packs

    worlds = packs.played_in(repo, pack_id)
    if worlds:
        return _(
            "{system} plays in world {worlds}: `didact world use {world}`",
            system=pack_id,
            worlds=", ".join(worlds),
            world=worlds[0],
        )
    return _("make a world for it: `didact world new <id> --system {system}`", system=pack_id)


@command(
    "pack enable",
    summary="Use a pack in the current campaign (or the whole world with --scope world)",
    writes=True,
    examples=(
        "didact pack enable my-oracle",
        "didact pack enable my-setting --scope world",
        "didact pack enable my-system          # a world without a system yet: its system",
    ),
    description=(
        "One game system is in use at a time: the open world's. A world keeps the system it\n"
        "was made with, so enabling a system only gives one to a world that has none yet;\n"
        "another system plays in a world of its own (`didact world new <id> --system <pack>`).\n"
        "A pack that needs another system (a setting written for it) can't be added either."
    ),
)
def pack_enable(
    ctx: Context,
    pack_id: Annotated[str, "the pack", Metavar("pack")],
    *,
    scope: Annotated[Literal["campaign", "world"] | None, "where (default: the campaign)"] = None,
) -> Out:
    return _toggle(ctx, pack_id, on=True, scope=scope)


@command(
    "pack disable",
    summary="Stop using a pack in the current campaign (or the world with --scope world)",
    writes=True,
    examples=("didact pack disable my-oracle",),
)
def pack_disable(
    ctx: Context,
    pack_id: Annotated[str, "the pack", Metavar("pack")],
    *,
    scope: Annotated[Literal["campaign", "world"] | None, "where (default: the campaign)"] = None,
) -> Out:
    return _toggle(ctx, pack_id, on=False, scope=scope)


# ---------------------------------------------------------------------------- authoring


def _pack_dir(ctx: Context, ref: str) -> tuple[Path, str]:
    """A pack folder by path or id → (folder, pack id)."""
    from didact.packs.library import _peek_manifest
    from didact.services import packs

    path = Path(ref).expanduser()
    if (path / "pack.yaml").is_file():
        head = _peek_manifest(path / "pack.yaml")
        return path, head[0] if head else path.name
    found = packs.library(open_repo(ctx)).find(ref)
    return found.path, found.id


@command(
    "pack new",
    summary="Start a new pack: a scaffold with a manifest, guide and example content",
    writes=True,
    examples=(
        "didact pack new my-hack --name 'My Hack'",
        "didact pack new vale-setting --kind setting",
        "didact pack new my-hack --dir ./my-hack",
        "didact pack new vale-homebrew --from-overlay my-system   # your homebrew, as a pack",
    ),
    description=(
        "--from-overlay <system> makes a supplement for that system from your homebrew for it:\n"
        "the compendium entries, tables, lore and the rest in the library's homebrew for it\n"
        "(`compendium add`), and the records kept for every world of that system (`new …\n"
        "--scope system`) as compendium entries. Secrets and the GM's notes stay out unless\n"
        "--secrets. House rules (`override`) patch the system itself, so they aren't carried.\n"
        "The pack isn't marked as shareable: set its licence in pack.yaml before `pack export`."
    ),
)
def pack_new(
    ctx: Context,
    pack_id: Annotated[str, "the new pack's id (lowercase, dashes)", Metavar("id")],
    *,
    name: Annotated[str | None, "its display name", Metavar("name")] = None,
    kind: Annotated[
        Literal["system", "oracle", "supplement", "setting", "adventure"], "what it is"
    ] = "system",
    dir_: Annotated[
        str | None, "where (default: the library's packs folder)", Metavar("path")
    ] = None,
    from_overlay: Annotated[
        str | None, "make it from your homebrew for this system", Metavar("system")
    ] = None,
    secrets: Annotated[bool, "with --from-overlay: secrets and the GM's notes too"] = False,
) -> Out:
    from didact.core.ids import check_name_id
    from didact.packs.author import scaffold
    from didact.services import packs

    check_name_id(pack_id, "pack")
    repo = open_repo(ctx)
    root = (
        Path(dir_).expanduser() if dir_ else packs.library(repo).installed_dir / pack_id / "0.1.0"
    )
    if from_overlay is not None:
        return _from_overlay(ctx, repo, pack_id, name, from_overlay, root, secrets=secrets)
    if ctx.dry_run:
        return Out(
            data={"dry_run": True, "path": str(root)},
            md=_("dry run: would create {pack} in {path}", pack=pack_id, path=root),
        )
    written = scaffold(root, pack_id, name or pack_id.replace("-", " ").title(), kind)
    lines = [
        _("✔ created pack {pack} in {path}", pack=pack_id, path=root),
        *(f"- {f}" for f in written if not f.endswith(".keep")),
    ]
    lines.append(
        _(
            "next: edit GUIDE.md, add content (`didact pack add {pack} table --data …`), "
            "then `didact pack test {pack}`",
            pack=pack_id,
        )
    )
    return Out(
        data={"id": pack_id, "path": str(root), "files": list[JSON](written)}, md="\n".join(lines)
    )


def _from_overlay(
    ctx: Context,
    repo: Repo,
    pack_id: str,
    name: str | None,
    system: str,
    root: Path,
    *,
    secrets: bool,
) -> Out:
    """`pack new --from-overlay`: a supplement made of the library's homebrew for a system."""
    from didact.core.ids import Scope
    from didact.services import overrides, packing, packs

    base = packs.library(repo).find(system)  # it must be a pack Didact knows
    homebrew = packs.homebrew_dir(repo, base.id)
    entities = packing.records(repo, [Scope("system", base.id)], secrets=secrets)
    packing.need_content(entities, homebrew, base.id)
    packing.check_folder(root)
    title = name or _("{system} homebrew", system=base.id)
    if ctx.dry_run:
        return Out(
            data={"dry_run": True, "path": str(root), "records": len(entities)},
            md=_("dry run: would create {pack} in {path}", pack=pack_id, path=root),
        )
    manifest: dict[str, JSON] = {
        "id": pack_id,
        "name": title,
        "kind": "supplement",
        "version": "0.1.0",
        "description": f"Homebrew for {base.id}, made from a Didact library.",
        "requires": {"didact": ">=0.1", "packs": ["core", base.id]},
        "license": {"spdx": "", "redistributable": False, "attribution": ""},
    }
    guide = packing.guide(
        title,
        f"Homebrew for {base.id}: monsters, items, tables and lore made in play.",
        [
            f"`didact pack enable {pack_id}` in a world that plays {base.id}.",
            f"`didact compendium import {pack_id}` brings its records into the world.",
            "Its lore comes up in play by itself.",
        ],
    )
    made = packing.write(root, manifest, guide, repo, entities, secrets=secrets, copies=homebrew)
    house = len(overrides.active(repo, base.id))
    if house:
        made.notes.append(
            ngettext(
                "{n} house rule not carried: it patches {system} itself (`didact override list`)",
                "{n} house rules not carried: they patch {system} itself (`didact override list`)",
                house,
                system=base.id,
            )
        )
    return made_pack(pack_id, made)


@command(
    "pack add",
    summary="Add content to a pack from JSON (validated, written as YAML)",
    writes=True,
    examples=(
        'didact pack add my-hack table --data \'{"table": "fog", "entries": {"1-6": "Fog"}}\'',
        'didact pack add my-hack check --data \'{"check": "save", "roll": "d20", "success": "…"}\'',
    ),
)
def pack_add(
    ctx: Context,
    pack: Annotated[str, "the pack (id or folder)", Metavar("pack")],
    kind: Annotated[
        str,
        "table, check, action, procedure, trigger, type, entry, deck, bag, test",
        Metavar("kind"),
    ],
    *,
    data: Annotated[str, "the item as JSON"],
    replace: Annotated[bool, "overwrite an item with the same id"] = False,
) -> Out:
    import json

    from didact.packs.author import add_item

    try:
        payload = json.loads(data)
    except ValueError as exc:
        raise InvalidError(
            _("--data is not valid JSON: {error}", error=exc), hint=_("e.g. --data '{\"hp\": 6}'")
        ) from exc
    if not isinstance(payload, dict):
        raise InvalidError(_("--data must be a JSON object"), hint=_("e.g. --data '{\"hp\": 6}'"))
    root, pack_id = _pack_dir(ctx, pack)
    if ctx.dry_run:
        return Out(
            data={"dry_run": True},
            md=_("dry run: would add a {kind} to {pack}", kind=kind, pack=pack_id),
        )
    rel, problems = add_item(root, kind, payload, replace=replace)
    lines = [
        _("✔ wrote {pack}/{file}", pack=pack_id, file=rel),
        *(_("warning: {message}", message=p.message) for p in problems),
    ]
    return Out(data={"pack": pack_id, "file": rel}, md="\n".join(lines))


@command(
    "pack lint",
    summary="Validate a pack and point out what's missing (help, sources, guide)",
    examples=("didact pack lint my-hack",),
)
def pack_lint(
    ctx: Context, pack: Annotated[str, "the pack (id or folder)", Metavar("pack")]
) -> Out:
    from didact.packs.author import lint
    from didact.packs.build import build

    root, pack_id = _pack_dir(ctx, pack)
    result = build(root)
    lines = [_listed(p) for p in result.problems]
    warnings = lint(result.bundle) if result.bundle is not None else []
    lines += [_("style: {note}", note=w) for w in warnings]
    head = _("✔ ok") if result.ok else ngettext("✘ {n} error", "✘ {n} errors", len(result.errors))
    notes = ngettext("{n} style note", "{n} style notes", len(warnings))
    text = "\n".join([f"{head}: {pack_id} ({notes})", *lines])
    data: dict[str, JSON] = {
        "ok": result.ok,
        "problems": [p.to_data() for p in result.problems],
        "style": list[JSON](warnings),
    }
    return Out(data=data, md=text, ok=result.ok)


@command(
    "pack build",
    summary="Compile a pack into its JSON bundle (what Didact loads)",
    examples=("didact pack build my-hack", "didact pack build my-hack --out bundle.json"),
)
def pack_build(
    ctx: Context,
    pack: Annotated[str, "the pack (id or folder)", Metavar("pack")],
    *,
    out: Annotated[
        str | None, "where to write it (default: <pack>/.build/)", Metavar("path")
    ] = None,
) -> Out:
    import json

    from didact.packs.build import build
    from didact.store.fsutil import atomic_write

    root, pack_id = _pack_dir(ctx, pack)
    result = build(root)
    if result.bundle is None:
        first = result.errors[0].text() if result.errors else _("unknown problem")
        raise InvalidError(
            _("{pack} doesn't build: {problem}", pack=pack_id, problem=first),
            hint=_("run `didact pack validate {pack}`", pack=pack),
        )
    manifest = result.bundle["manifest"]
    assert isinstance(manifest, dict)
    target = Path(out) if out else root / ".build" / f"{pack_id}-{manifest['version']}.json"
    atomic_write(target, json.dumps(result.bundle, ensure_ascii=False, indent=1))
    return Out(
        data={"path": str(target)}, md=_("✔ built {pack} → {path}", pack=pack_id, path=target)
    )


@command(
    "pack test",
    summary="Run a pack's tests: table rolls, expressions, odds and smoke-play scripts",
    examples=("didact pack test my-hack",),
)
def pack_test(
    ctx: Context, pack: Annotated[str, "the pack (id or folder)", Metavar("pack")]
) -> Out:
    from didact.packs.build import build
    from didact.packs.testing import run_tests

    root, pack_id = _pack_dir(ctx, pack)
    result = build(root)
    if result.bundle is None:
        first = result.errors[0].text() if result.errors else _("unknown problem")
        raise InvalidError(
            _("{pack} doesn't build: {problem}", pack=pack_id, problem=first),
            hint=_("run `didact pack validate {pack}`", pack=pack),
        )
    items = result.bundle.get("items")
    tests = items.get("test", {}) if isinstance(items, dict) else {}
    if not isinstance(tests, dict) or not tests:
        return Out(
            data={"tests": []},
            md=_("{pack} has no tests yet (add them in tests/*.yaml)", pack=pack_id),
        )
    outcomes = run_tests(root, pack_id, tests)
    failed = [o for o in outcomes if not o.ok]
    lines = [f"{'✔' if o.ok else '✘'} {o.test}: {o.detail}" for o in outcomes]
    head = ngettext(
        "{pack}: {passed}/{n} tests passed",
        "{pack}: {passed}/{n} tests passed",
        len(outcomes),
        pack=pack_id,
        passed=len(outcomes) - len(failed),
    )
    data: dict[str, JSON] = {
        "tests": [{"test": o.test, "ok": o.ok, "detail": o.detail} for o in outcomes]
    }
    return Out(data=data, md="\n".join([head, *lines]), ok=not failed)


@command(
    "pack import",
    summary="Turn a Markdown table into a Didact table (print it, or add it to a pack)",
    examples=(
        "didact pack import weather.md --id weather",
        "didact pack import culture.md --id culture --columns --into my-hack",
    ),
)
def pack_import(
    ctx: Context,
    file: Annotated[str, "a Markdown file with a pipe table (- for stdin)", Metavar("file")],
    *,
    id_: Annotated[str, "the table's id", Metavar("id")],
    dice: Annotated[
        str | None, "its dice (default: from the header, e.g. d6)", Metavar("dice")
    ] = None,
    columns: Annotated[bool, "roll each column separately"] = False,
    into: Annotated[str | None, "add it to this pack", Metavar("pack")] = None,
) -> Out:
    import sys

    from didact.packs.author import add_item, md_table
    from didact.store import frontmatter

    text = sys.stdin.read() if file == "-" else Path(file).expanduser().read_text(encoding="utf-8")
    table = md_table(text, id_, dice, columns=columns)
    if into:
        root, pack_id = _pack_dir(ctx, into)
        rel, _problems = add_item(root, "table", table, replace=False)
        return Out(
            data={"pack": pack_id, "file": rel, "table": table},
            md=_("✔ wrote {pack}/{file}", pack=pack_id, file=rel),
        )
    yaml_text = frontmatter.dump(frontmatter.from_plain(table))
    return Out(data={"table": table}, md="```yaml\n" + yaml_text + "```")


# ---------------------------------------------------------------------------- sharing


@command(
    "pack export",
    summary="Package a pack as a .didactpack file anyone can install",
    examples=("didact pack export my-hack", "didact pack export my-system --to ~/Desktop"),
)
def pack_export(
    ctx: Context,
    pack: Annotated[str, "the pack (id or folder)", Metavar("pack")],
    *,
    to: Annotated[str | None, "a folder or file name (default: here)", Metavar("path")] = None,
) -> Out:
    from didact.packs.share import export

    root, pack_id = _pack_dir(ctx, pack)
    done = export(root, Path(to).expanduser() if to else None)
    lines = [
        ngettext(
            "✔ exported {pack} → {path} ({n} file)",
            "✔ exported {pack} → {path} ({n} files)",
            done.files,
            pack=pack_id,
            path=done.path,
        ),
        *(_("note: {note}", note=n) for n in done.notes),
    ]
    return Out(data={"path": str(done.path), "files": done.files}, md="\n".join(lines))


@command(
    "pack install",
    summary="Install a pack from a .didactpack file, a folder or an https URL, or one that "
    "ships with Didact by its id",
    examples=(
        "didact pack install my-system",
        "didact pack install ~/Downloads/my-hack-0.1.0.didactpack",
        "didact pack install ./my-hack",
        "didact pack install https://example.org/packs/my-hack-0.1.0.didactpack",
    ),
)
def pack_install(
    ctx: Context,
    source: Annotated[
        str, "file, folder, URL, or the id of a pack that ships with Didact", Metavar("source")
    ],
    *,
    force: Annotated[bool, "replace the same version if it's installed"] = False,
) -> Out:
    from didact.packs.share import install
    from didact.services import packs

    repo = open_repo(ctx)
    repo.require_init()
    done = install(packs.library(repo), source, force=force)
    lines = [
        _(
            "✔ installed {pack} {version} → {path}",
            pack=done.id,
            version=done.version,
            path=done.path,
        ),
        *(_("note: {note}", note=n) for n in done.notes),
    ]
    lines.append(_use_it(repo, done.id))
    return Out(
        data={"id": done.id, "version": done.version, "path": str(done.path)}, md="\n".join(lines)
    )


def _use_it(repo: Repo, pack_id: str) -> str:
    """How to use a pack just installed: enable it, or, one system at a time, play it (or the
    system it's written for) in a world of its own."""
    from didact.core.errors import DidactError
    from didact.services import packs, sheets

    enable = _("use it: {command}", command=code(f"didact pack enable {pack_id}"))
    world = repo.active_world() if repo.initialized() else None
    lib = packs.library(repo)
    try:
        kind = packs.kind_of(lib, pack_id)
        system = sheets.active_system(repo) if world is not None else None
        clash = packs.conflicts(lib, system, [pack_id]).get(pack_id) if kind != "system" else None
    except DidactError:
        return enable
    if kind == "system":
        if world is not None and system == pack_id:
            return _("{pack} is already this world's game system", pack=pack_id)
        if world is not None and system is None:
            return enable  # a world without a system takes it
        return _("make a world for it: `didact world new <id> --system {system}`", system=pack_id)
    if clash is not None and world is not None:  # a setting for another system: its world
        return _("make a world for it: `didact world new <id> --system {system}`", system=clash)
    return enable


@command(
    "pack trust",
    summary="Let an installed pack's Python plugins run (shows the code's hashes first)",
    examples=("didact pack trust my-dice", "didact pack trust my-dice --yes"),
)
def pack_trust(
    ctx: Context,
    pack: Annotated[str, "the pack", Metavar("pack")],
    *,
    yes: Annotated[bool, "trust it (without this, only show what would run)"] = False,
) -> Out:
    from didact.packs.share import trust
    from didact.services import packs

    lib = packs.library(open_repo(ctx))
    loaded = lib.load(lib.find(pack))
    if not loaded.plugins:
        return Out(
            data={"id": loaded.id, "plugins": []},
            md=_("{pack} has no plugins: nothing to trust", pack=loaded.id),
        )
    lines = [_("{pack} {version} runs this Python code:", pack=loaded.id, version=loaded.version)]
    for rel, digest in loaded.plugin_hashes().items():
        source = (loaded.ref.path / rel).read_text(encoding="utf-8")
        lines += [
            ngettext(
                "- {file} (sha256 {digest}…, {n} lines)",
                "- {file} (sha256 {digest}…, {n} lines)",
                len(source.splitlines()),
                file=rel,
                digest=digest[:16],
            ),
            "```python",
            source.rstrip(),
            "```",
        ]
    if not yes:
        lines.append(
            _(
                "read it, then trust it with {command}",
                command=code(f"didact pack trust {loaded.id} --yes"),
            )
        )
        return Out(data={"id": loaded.id, "trusted": loaded.trusted}, md="\n".join(lines))
    hashes = trust(lib, loaded)
    lines.append(
        _(
            "✔ trusted {pack} {version}; any change to its code revokes this",
            pack=loaded.id,
            version=loaded.version,
        )
    )
    return Out(
        data={"id": loaded.id, "trusted": True, "plugins": dict[str, JSON](hashes)},
        md="\n".join(lines),
    )


@command(
    "pack untrust",
    summary="Switch an installed pack's plugins off again",
    examples=("didact pack untrust my-dice",),
)
def pack_untrust(ctx: Context, pack: Annotated[str, "the pack", Metavar("pack")]) -> Out:
    from didact.packs.share import untrust
    from didact.services import packs

    lib = packs.library(open_repo(ctx))
    loaded = lib.load(lib.find(pack))
    removed = untrust(lib, loaded)
    text = (
        _("✔ {pack}'s plugins are off", pack=loaded.id)
        if removed
        else _("{pack} wasn't trusted", pack=loaded.id)
    )
    return Out(data={"id": loaded.id, "untrusted": removed}, md=text)


@command(
    "pack uninstall",
    summary="Remove an installed pack version from the library (shows what uses it first)",
    examples=(
        "didact pack uninstall my-hack",
        "didact pack uninstall my-hack --yes",
        "didact pack uninstall my-hack 0.1.0 --yes",
    ),
    description=(
        "Without --yes it says what would go and which worlds and campaigns use the pack. It\n"
        "refuses while something uses the only copy (unless --force), and it can't be undone:\n"
        "install the .didactpack again to get it back. The core pack can't be removed."
    ),
)
def pack_uninstall(
    ctx: Context,
    pack: Annotated[str, "the pack", Metavar("pack")],
    pack_version: Annotated[
        str | None, "which version (default: the newest)", Metavar("version")
    ] = None,
    *,
    yes: Annotated[bool, "really remove it"] = False,
    force: Annotated[bool, "remove it even though worlds or campaigns use it"] = False,
) -> Out:
    import shutil

    from didact.services import packs

    repo = open_repo(ctx)
    if pack == packs.CORE:
        raise InvalidError(
            _("core ships with Didact and can't be removed"), hint=_("every system builds on it")
        )
    lib = packs.library(repo)
    versions = lib.available().get(pack, [])
    installed = [r for r in versions if r.origin == "installed"]
    chosen = next((r for r in installed if pack_version is None or r.version == pack_version), None)
    if chosen is None:
        if versions:
            where = ", ".join(f"{r.version} ({r.origin}: {r.path})" for r in versions)
            raise InvalidError(
                _(
                    "{pack} isn't installed in this library: it comes from {where}",
                    pack=pack,
                    where=where,
                ),
                hint=_("only packs added with `didact pack install` can be uninstalled here"),
            )
        raise NotFoundError(
            _("no installed version of {pack} {version}", pack=pack, version=pack_version)
            if pack_version
            else _("no installed version of {pack}", pack=pack),
            hint=_("`didact pack list` shows the installed versions"),
        )
    used = packs.used_by(repo, pack)
    others = [r for r in versions if r.path != chosen.path]
    lines = [
        _("removes {pack} {version} ({path})", pack=pack, version=chosen.version, path=chosen.path)
    ]
    if used:
        lines.append(
            _(
                "in use by: {used}: they'll use {version} ({origin}) instead",
                used="; ".join(used),
                version=others[0].version,
                origin=others[0].origin,
            )
            if others
            else _(
                "in use by: {used}: they won't load until it's installed again or disabled there",
                used="; ".join(used),
            )
        )
    lines.append(_("this can't be undone: install it again from its .didactpack to get it back"))
    data: dict[str, JSON] = {
        "id": pack, "version": chosen.version, "path": str(chosen.path),
        "used_by": list[JSON](used),
    }  # fmt: skip
    if not yes:
        return Out(data=data, md="\n".join([*lines, _("add --yes to remove it")]))
    if used and not others and not force:
        raise InvalidError(
            _("{pack} is in use: {used}", pack=pack, used="; ".join(used)),
            hint=_(
                "disable it there first (`didact pack disable {pack}`), or add --force", pack=pack
            ),
        )
    shutil.rmtree(chosen.path)
    return Out(data=data, md=_("✔ removed {pack} {version}", pack=pack, version=chosen.version))


@command(
    "pack update",
    summary="Look for newer versions of the installed packs, and install them (shows them first)",
    examples=("didact pack update", "didact pack update --yes", "didact pack update my-hack --yes"),
    description=(
        "Looks in Didact's packs folder and on GitHub (vess-dev/Didact; set "
        "DIDACT_PACK_UPDATES to look elsewhere, or to nothing not to look). The new version "
        "installs beside the old one: campaigns keep the version they're pinned to until "
        "`didact campaign upgrade`."
    ),
)
def pack_update(
    ctx: Context,
    pack: Annotated[str | None, "only this pack", Metavar("pack")] = None,
    *,
    yes: Annotated[bool, "install the updates"] = False,
) -> Out:
    from didact.packs.share import update, updates
    from didact.services import packs

    repo = open_repo(ctx)
    lib = packs.library(repo)
    offers, notes = updates(lib)
    if pack is not None:
        offers = [o for o in offers if o.id == pack]
    rows: list[JSON] = [
        {"id": o.id, "installed": o.installed, "version": o.version, "from": o.where}
        for o in offers
    ]
    lines = [
        _(
            "- {pack}: {installed} → {version} (from {where})",
            pack=o.id,
            installed=o.installed,
            version=o.version,
            where=labels.pack_origin(o.where),
        )
        for o in offers
    ]
    notes_md = [_("note: {note}", note=n) for n in notes]
    if not offers:
        current = (
            _("{pack} is up to date", pack=pack)
            if pack
            else _("the installed packs are up to date")
        )
        return Out(
            data={"updates": [], "notes": list[JSON](notes)},
            md="\n".join([current, *notes_md]),
        )
    if not yes:
        return Out(
            data={"updates": rows, "notes": list[JSON](notes)},
            md="\n".join(
                [
                    ngettext("{n} update:", "{n} updates:", len(offers)),
                    *lines,
                    *notes_md,
                    _("install: {command}", command=code("didact pack update --yes")),
                ]
            ),
        )
    repo.require_init()
    done = [update(lib, o) for o in offers]
    return Out(
        data={"updates": rows, "installed": [f"{d.id} {d.version}" for d in done]},
        md="\n".join(
            [
                *(_("✔ installed {pack} {version}", pack=d.id, version=d.version) for d in done),
                *(_("note: {note}", note=n) for d in done for n in d.notes),
                _("campaigns move to them with {command}", command=code("didact campaign upgrade")),
            ]
        ),
    )


@command(
    "campaign upgrade",
    summary="Move the campaign to the pack versions installed now (shows what changes)",
    writes=True,
    examples=("didact campaign upgrade", "didact campaign upgrade --dry-run"),
)
def campaign_upgrade(ctx: Context) -> Out:
    from didact.services import packs
    from didact.store.repo import campaign_file_text

    repo = open_repo(ctx)
    campaign = repo.active_campaign()
    if campaign is None:
        raise InvalidError(_("no campaign is open"), hint="`didact campaign open <id>`")
    before = packs.pins(repo)
    system = campaign.system or repo.load_world(campaign.world).system
    extra = [str(p) for p in campaign.other.get("packs") or []]  # type: ignore[union-attr]
    new = packs.pin_set(
        packs.library(repo), [packs.CORE, *([system] if system else []), *extra], {}
    )
    changes = []
    for pack_id, entry in new.items():
        version = entry["version"] if isinstance(entry, dict) else entry
        if before.get(pack_id) != version:
            changes.append(
                f"{pack_id}: {before[pack_id]} → {version}"
                if pack_id in before
                else _("{pack}: new → {version}", pack=pack_id, version=version)
            )
    campaign.other["pins"] = new
    cs = changeset(ctx, repo, N_("upgrade campaign {campaign} packs"), campaign=campaign.id)
    path = repo.layout.campaign_file(campaign.world, campaign.id)
    cs.write(path, campaign_file_text(campaign, repo.read_text(path)))
    out = finish(
        ctx,
        cs,
        done=_("pinned {campaign} to the installed packs", campaign=campaign.id),
        extra={"pins": new},
    )
    lines = [*(f"- {c}" for c in changes)] or [_("versions unchanged (content hashes refreshed)")]
    return Out(data=out.data, md="\n".join([out.md, *lines]), ok=out.ok)


# ---------------------------------------------------------------------------- rulebooks


@command(
    "pack ingest",
    summary="Start a pack from a rulebook: page-marked text plus draft tables to review",
    examples=(
        "didact pack ingest ~/Books/my-rpg.pdf --out ./my-rpg-work",
        "didact pack ingest notes.md",
    ),
)
def pack_ingest(
    ctx: Context,
    source: Annotated[str, "a PDF (needs pdftotext) or a Markdown/text file", Metavar("file")],
    *,
    out: Annotated[
        str | None, "the workspace (default: <library>/workspace/<name>)", Metavar("dir")
    ] = None,
) -> Out:
    from didact.packs.ingest import ingest

    path = Path(source).expanduser()
    if not path.is_file():
        raise NotFoundError(
            _("no file {file}", file=source), hint=_("give the path to a PDF or a text file")
        )
    repo = open_repo(ctx)
    workspace = (
        Path(out).expanduser()
        if out
        else repo.home / "workspace" / path.stem.lower().replace(" ", "-")
    )
    count, found = ingest(path, workspace)
    drafts = workspace / "candidates"
    lines = [
        ngettext("✔ {n} page → {path}", "✔ {n} pages → {path}", count, path=workspace / "text.md"),
        ngettext(
            "{n} candidate table in {path}: drafts to check",
            "{n} candidate tables in {path}: drafts to check",
            len(found),
            path=drafts,
        ),
        *(
            ngettext(
                "- p. {page}: {n} rows from “{text}”",
                "- p. {page}: {n} rows from “{text}”",
                len(c.rows),
                page=c.page,
                text=c.rows[0][1][:40],
            )
            for c in found[:12]
        ),
        _(
            "next: `didact pack new <id>`, then `didact pack add` or `didact pack import`;\n"
            "walk the checklist in `didact guide packs` and cite pages with `source:`."
        ),
    ]
    data: dict[str, JSON] = {"pages": count, "workspace": str(workspace), "candidates": len(found)}
    return Out(data=data, md="\n".join(lines))


def _section_coverage(pack_id: str, bundle: dict[str, JSON], sections: list[str]) -> Out:
    from didact.packs.ingest import cited_sections

    cited = cited_sections(bundle)
    missing = [s for s in sections if s not in cited]
    share = (len(sections) - len(missing)) / len(sections)
    lines = [
        ngettext(
            "{pack} cites {n} section of {total} ({share})",
            "{pack} cites {n} sections of {total} ({share})",
            len(sections) - len(missing),
            pack=pack_id,
            total=len(sections),
            share=f"{share:.0%}",
        )
    ]
    lines.append(
        _("not yet: {sections}", sections=", ".join(missing))
        if missing
        else _("every section of the book is converted")
    )
    extra = sorted(cited - set(sections))
    if extra:
        lines.append(_("cited but not listed in pack.yaml: {sections}", sections=", ".join(extra)))
    data: dict[str, JSON] = {
        "sections": list[JSON](sections),
        "missing": list[JSON](missing),
        "share": share,
    }
    return Out(data=data, md="\n".join(lines))


@command(
    "pack coverage",
    summary="Which pages of the book a pack cites (and which it doesn't yet)",
    examples=("didact pack coverage my-system",),
)
def pack_coverage(
    ctx: Context, pack: Annotated[str, "the pack (id or folder)", Metavar("pack")]
) -> Out:
    from didact.packs.build import build
    from didact.packs.ingest import cited_pages, ranges

    root, pack_id = _pack_dir(ctx, pack)
    result = build(root)
    if result.bundle is None:
        raise InvalidError(
            _("{pack} doesn't build", pack=pack_id),
            hint=_("run `didact pack validate {pack}`", pack=pack),
        )
    manifest = result.bundle["manifest"]
    source = manifest.get("source") if isinstance(manifest, dict) else None
    sections = source.get("sections") if isinstance(source, dict) else None
    if isinstance(sections, list) and sections:  # an unpaginated book: coverage by section
        return _section_coverage(pack_id, result.bundle, [str(s) for s in sections])
    cited = sorted(cited_pages(result.bundle))
    total = source.get("pages") if isinstance(source, dict) else None
    lines = [
        ngettext(
            "{pack} cites {n} page: {pages}",
            "{pack} cites {n} pages: {pages}",
            len(cited),
            pack=pack_id,
            pages=ranges(cited),
        )
    ]
    data: dict[str, JSON] = {"cited": list[JSON](cited)}
    if isinstance(total, int) and total > 0:
        missing = [p for p in range(1, total + 1) if p not in set(cited)]
        share = (total - len(missing)) / total
        lines.append(
            ngettext(
                "{share} of {n} pages; not yet: {missing}",
                "{share} of {n} pages; not yet: {missing}",
                total,
                share=f"{share:.0%}",
                missing=ranges(missing),
            )
        )
        data |= {"pages": total, "missing": list[JSON](missing), "share": share}
    else:
        lines.append(_("add `source: {title: …, pages: N}` to pack.yaml to see what's missing"))
    return Out(data=data, md="\n".join(lines))
