"""The library: worlds and campaigns (switch, create, delete), packs (enable, disable, install,
uninstall), the history (undo, clear), save points and backups."""

import shlex
from urllib.parse import quote

from didact.core.i18n import _, ngettext, pgettext
from didact.core.output import JSON
from didact.services.care import AUTO_KEEP, human
from didact.web.app import Request, Response
from didact.web.forms import accepts, typed_entry
from didact.web.html import (
    Html,
    boxed_list,
    button,
    chip,
    entry,
    expander,
    field,
    form_row,
    group,
    h,
    icon,
    link_button,
    row,
    select,
    url,
)
from didact.web.layout import (
    Confirm,
    command_line,
    failure,
    guarded,
    page,
    result_panel,
    run_form,
    words_form,
)
from didact.web.markdown import markdown
from didact.web.pages.common import as_dict, as_list, change_title, record_index
from didact.web.pages.overview import system_choices

PACK_KINDS = ("system", "oracle", "setting", "adventure", "supplement")
HISTORY = 30  # the changes the history shows at first
HISTORY_MOST = 2000  # and at most, after "Show older changes"
JUMP_LISTED = 100  # the steps a jump's preview lists, at most


def index(req: Request) -> Response:
    flash = req.take_flash()
    parts: list[Html | None] = [
        result_panel(req, flash.ran) if flash else None,
        _worlds(req),
        _packs(req),
        _history(req),
        _saves(req),
        _backups(req),
        _start_over(req),
    ]
    return page(req, _("Library"), h(t"{parts}"), nav="library")


def _pack_kind(kind: str) -> str:
    """A kind of pack, as a heading."""
    labels = {
        "system": pgettext("pack kind", "Systems"),
        "oracle": pgettext("pack kind", "Oracles"),
        "setting": pgettext("pack kind", "Settings"),
        "adventure": pgettext("pack kind", "Adventures"),
        "supplement": pgettext("pack kind", "Supplements"),
        "base": pgettext("pack kind", "Bases"),  # core: what every system builds on
    }
    return labels.get(kind, f"{kind.capitalize()}s")


def _worlds(req: Request) -> Html:
    worlds = req.run("world", "list")
    if not worlds.ok:
        return group(_("Worlds and campaigns"), failure(worlds))
    campaigns = req.run("campaign", "list")
    active_world = worlds.data.get("active")
    active_campaign = campaigns.data.get("active")
    by_world: dict[str, list[dict[str, JSON]]] = {}
    for item in as_list(campaigns.data.get("campaigns")):
        campaign = as_dict(item)
        by_world.setdefault(str(campaign.get("world")), []).append(campaign)
    sections: list[Html] = []
    for item in as_list(worlds.data.get("worlds")):
        world = as_dict(item)
        world_id = str(world.get("id"))
        system = f" · {world['system']}" if world.get("system") else ""
        world_name = str(world.get("name") or world_id)
        rows = [
            row(
                world_name,
                subtitle=_("world {world}", world=world_id) + system,
                suffix=h(
                    t"{_open(req, 'world', world_id, world_id == active_world)}"
                    t"{_delete(req, 'world', world_id, world_name)}"
                ),
            )
        ]
        for campaign in by_world.get(world_id, []):
            campaign_id = str(campaign.get("id"))
            campaign_name = str(campaign.get("name") or campaign_id)
            rows.append(
                row(
                    campaign_name,
                    subtitle=_("campaign {campaign}", campaign=campaign_id),
                    prefix=h(t'<span class="indent"></span>'),
                    suffix=h(
                        t"{_open(req, 'campaign', campaign_id, campaign_id == active_campaign)}"
                        t"{_delete(req, 'campaign', campaign_id, campaign_name)}"
                    ),
                )
            )
        start = run_form(
            req,
            h(
                t"{
                    typed_entry(
                        'id',
                        'w',
                        placeholder=_('new campaign id'),
                        label=_('Campaign id'),
                        required=True,
                    )
                }"
                t"{entry('o:--name', placeholder=_('name (optional)'), label=_('Campaign name'))}"
                t"{button(_('Start'), icon_name='plus')}"
            ),
            fields={"action": "words", "w": ["campaign", "new"], "o:--world": world_id},
            cls="action-row",
        )
        rows.append(form_row(_("New campaign here"), start, subtitle=accepts("id")))
        title = h(t'{world.get("name") or world_id} <span class="dim small">{world_id}</span>')
        count = len(by_world.get(world_id, []))
        sections.append(expander(title, boxed_list(rows), count=count))
    world_id = field(
        _("World id"),
        typed_entry("id", "w", placeholder=_("e.g. vale"), required=True),
        help_=accepts("id"),
    )
    name = field(_("Name"), entry("o:--name", placeholder=_("optional")))
    wanted = req.arg("system")  # a system's New world button
    system_field = field(
        _("Game system"),
        select("o:--system", system_choices(req), wanted),
        help_=_("For good: a world keeps its system, and its campaigns play it."),
    )
    create = button(_("Create world"), icon_name="plus", kind="suggested")
    new_world = run_form(
        req,
        h(
            t'<div class="fields two">{world_id}{name}</div><div class="fields">{system_field}'
            t'</div><div class="button-row">{create}</div>'
        ),
        fields={"action": "words", "w": ["world", "new"]},
        cls="stack",
    )
    making = expander(
        _("New world"), new_world, cls="is-plain", open_=bool(wanted), attrs={"id": "new-world"}
    )
    sections.append(making)
    return group(
        _("Worlds and campaigns"),
        h(t'<div class="stack">{sections}</div>'),
        description=_("A world holds the canon; each campaign is one playthrough in it."),
        id_="worlds",
    )


def _open(req: Request, kind: str, key: str, active: bool) -> Html:
    """Open a world or a campaign; the open campaign can be closed (its world stays open)."""
    if not active:
        verb = "use" if kind == "world" else "open"
        return words_form(req, [kind, verb, key], _("Open"), next_="/library#worlds")
    if kind == "world":
        return chip(pgettext("world", "open"), kind="accent")
    close = words_form(req, ["campaign", "close"], _("Close"), next_="/library#worlds")
    return h(t"{chip(pgettext('campaign', 'open'), kind='accent')}{close}")


def _goes(kind: str) -> str:
    """What deleting a world or a campaign takes with it."""
    if kind == "world":
        return _("Its records, maps, lore and every campaign in it go.")
    return _("Its PCs, sessions, journal and oracle state go; the world stays.")


def _delete_question(kind: str, name: str) -> str:
    if kind == "world":
        return _("Delete the world “{name}”?", name=name)
    return _("Delete the campaign “{name}”?", name=name)


def _delete_form(req: Request, kind: str, key: str, name: str, *, pill: bool = False) -> Html:
    return words_form(
        req,
        [kind, "delete", key, "--yes"],
        _("Delete"),
        icon_name="trash-2",
        kind="destructive pill" if pill else "destructive",
        next_="/library#worlds",
        confirm=Confirm(
            _delete_question(kind, name),
            _goes(kind) + " " + _("Undo (in the history below) brings it all back."),
            _("Delete"),
        ),
    )


def _delete(req: Request, kind: str, key: str, name: str) -> Html:
    form = _delete_form(req, kind, key, name)
    href = f"/library/delete?{kind}=" + quote(key)
    return guarded(href, _("Delete…"), form, icon_name="trash-2", kind="flat destructive")


def _packs(req: Request) -> Html:
    listed = req.run("pack", "list")
    if not listed.ok:
        return group(_("Packs"), failure(listed), id_="packs")
    worlds = req.run("world", "list")
    open_world = worlds.data.get("active")
    playing: dict[str, list[str]] = {}  # system → the worlds that play it
    bare = False  # the open world has no system yet
    for item in as_list(worlds.data.get("worlds")):
        world = as_dict(item)
        if world.get("system"):
            playing.setdefault(str(world.get("system")), []).append(str(world.get("id")))
        elif world.get("id") == open_world:
            bare = True
    by_kind: dict[str, list[Html]] = {}
    for item in as_list(listed.data.get("packs")):
        pack = as_dict(item)
        pack_id = str(pack.get("id"))
        enabled = bool(pack.get("enabled"))
        toggle: Html
        if pack.get("origin") == "shipped":  # ships with Didact, not installed here yet
            toggle = words_form(
                req,
                ["pack", "install", pack_id],
                _("Install"),
                icon_name="download",
                kind="suggested",
            )
        elif pack_id == "core":
            toggle = chip(_("always on"))  # every system builds on it
        elif pack.get("kind") == "system":
            toggle = _system(req, pack_id, enabled, bare=bare, worlds=playing.get(pack_id, []))
        else:
            toggle = words_form(
                req,
                ["pack", "disable" if enabled else "enable", pack_id],
                _("Disable") if enabled else _("Enable"),
                kind="" if enabled else "suggested",
            )
        installed = [str(v) for v in as_list(pack.get("installed"))] if pack_id != "core" else []
        if installed:  # only copies installed in this library can be uninstalled
            toggle = h(t"{toggle}{[_uninstall(req, pack_id, v) for v in installed]}")
        if pack.get("update"):
            update = words_form(
                req,
                ["pack", "update", pack_id, "--yes"],
                _("Update to {version}", version=pack.get("update")),
                icon_name="download",
                kind="suggested",
            )
            toggle = h(t"{update}{toggle}")
        info = words_form(
            req,
            ["pack", "info", pack_id],
            "",
            icon_name="info",
            title=_("About this pack"),
            kind="flat circular",
            panel=True,
        )
        badge = (
            chip(_("enabled"), kind="accent") if enabled and pack.get("kind") != "system" else None
        )
        meta = f"{pack_id} {pack.get('version') or ''} · {_origin(pack)}"
        about = str(pack.get("description") or "")
        said = h(t'{about}<span class="row-meta">{meta}</span>') if about else meta
        by_kind.setdefault(str(pack.get("kind") or "other"), []).append(
            row(
                h(t"{pack.get('name') or pack_id} {badge}"),
                subtitle=said,
                suffix=h(t"{info}{toggle}"),
            )
        )
    order = {kind: i for i, kind in enumerate(PACK_KINDS)}
    kinds = sorted(by_kind.items(), key=lambda item: (order.get(item[0], 99), item[0]))
    sections = [
        expander(_pack_kind(kind), boxed_list(rows), count=len(rows)) for kind, rows in kinds
    ]
    source = entry(
        "w", placeholder=_("a .didactpack file, a pack folder or an https URL"), required=True,
        label=_("Pack to install"),
    )  # fmt: skip
    install = run_form(
        req,
        h(t"{source}{button(_('Install'), icon_name='download')}"),
        fields={"action": "words", "w": ["pack", "install"]},
        cls="action-row",
    )
    check = link_button(
        "/library/updates", _("Check for updates…"), icon_name="refresh-cw", kind="pill"
    )
    return group(
        _("Packs"),
        h(
            t'<div class="stack">{sections}'
            t"{boxed_list([form_row(_('Install a pack'), install)])}"
            t'<div class="button-row">{check}</div></div>'
        ),
        description=_(
            "Enabling a pack adds it to the open campaign. The core pack is always on, and one "
            "game system is in use at a time: the open world's, which it keeps for good."
        ),
        id_="packs",
    )


def _system(req: Request, pack_id: str, in_use: bool, *, bare: bool, worlds: list[str]) -> Html:
    """A system is in use while a world that plays it is open. Another one plays in a world of
    its own: open one, or make one; an open world without a system can take it."""
    if in_use:
        return chip(_("in use"), kind="accent")
    if bare:
        return words_form(
            req, ["pack", "enable", pack_id], _("Use in this world"), kind="suggested"
        )
    if worlds:
        opens = [
            words_form(req, ["world", "use", w], _("Open {world}", world=w), next_="/library#packs")
            for w in worlds[:3]
        ]
        return h(t"{opens}")
    return link_button(
        f"/library?system={quote(pack_id)}#new-world", _("New world"), icon_name="plus"
    )


def confirm_updates(req: Request) -> Response:
    """Newer versions of the installed packs, from the command's own preview; then install
    them, or leave it."""
    preview = req.run("pack", "update")
    back = "/library#packs"
    if not preview.ok:
        body: Html = h(t'<section class="card dialog-page">{failure(preview)}</section>')
    else:
        found = bool(as_list(preview.data.get("updates")))
        done = link_button(back, _("Cancel") if found else _("Back"), kind="pill")
        install = (
            words_form(
                req,
                ["pack", "update", "--yes"],
                _("Install the updates"),
                icon_name="download",
                kind="suggested pill",
                next_=back,
            )
            if found
            else None
        )
        body = h(
            t'<section class="card dialog-page is-wide"><h2>{_("Pack updates")}</h2>'
            t'<div class="dialog-text">{markdown(preview.md)}</div>'
            t'<div class="button-row">{done}{install}</div></section>'
        )
    return page(req, _("Pack updates"), body, nav="library", back=back)


def _origin(pack: dict[str, JSON]) -> str:
    origin = str(pack.get("origin") or "")
    return _("ships with Didact") if origin == "shipped" else origin


def _uninstall(req: Request, pack_id: str, version: str) -> Html:
    form = words_form(
        req,
        ["pack", "uninstall", pack_id, *([version] if version else []), "--yes"],
        _("Uninstall"),
        icon_name="trash-2",
        kind="destructive",
        next_="/library#packs",
        confirm=Confirm(
            _("Uninstall {pack} {version}?", pack=pack_id, version=version),
            _(
                "It leaves your library, and this can't be undone: install its .didactpack "
                "again to get it back. If a world or campaign still uses it, Didact refuses "
                "and says where."
            ),
            _("Uninstall"),
        ),
    )
    href = "/library/uninstall?pack=" + quote(pack_id) + "&version=" + quote(version)
    return guarded(href, _("Uninstall…"), form, icon_name="trash-2", kind="flat destructive")


def confirm_uninstall(req: Request) -> Response:
    """Uninstalling without JS: say what it does first."""
    pack_id, version = req.arg("pack"), req.arg("version")
    argv = ["pack", "uninstall", pack_id, *([version] if version else []), "--yes"]
    form = words_form(
        req, argv, _("Uninstall"), icon_name="trash-2", kind="destructive pill",
        next_="/library#packs",
    )  # fmt: skip
    cancel = link_button("/library#packs", _("Cancel"), kind="pill")
    question = _("Uninstall {pack} {version}?", pack=pack_id, version=version)
    leaves = _(
        "It leaves your library, and this can't be undone: install its .didactpack again to get "
        "it back."
    )
    body = h(
        t'<section class="card dialog-page"><h2>{question}</h2>'
        t'<p class="dim">{leaves}</p>{command_line(shlex.join(["didact", *argv]))}'
        t'<div class="button-row">{cancel}{form}</div></section>'
    )
    return page(req, _("Uninstall"), body, nav="library", back="/library#packs")


def _history(req: Request) -> Html:
    wanted = req.arg("history")
    limit = int(wanted) if wanted.isdigit() and 0 < int(wanted) <= HISTORY_MOST else HISTORY
    history = req.run("history", "--limit", str(limit))
    names = {} if req.gm else record_index(req).names  # the player view names known records only
    events = [as_dict(item) for item in as_list(history.data.get("events"))]
    rows: list[Html] = []
    for position, event in enumerate(events):
        seq = event.get("seq")
        when = str(event.get("ts", ""))[:16].replace("T", " ")
        undone = bool(event.get("undone"))
        if event.get("kind") == "note":  # the mark a cleared history leaves: nothing to undo
            tail = chip(pgettext("history", "note"), kind="dim")
        elif event.get("kind") == "undo":
            tail = chip(pgettext("history", "undo"), kind="dim")
        elif undone:
            tail = chip(_("undone"), kind="dim")
        else:
            tail = words_form(
                req,
                ["undo", "--event", f"e{seq}"],
                "",
                icon_name="rotate-ccw",
                title=_("Undo #e{seq}", seq=seq),
                kind="flat circular",
            )
        jump = (  # the newest is where things stand: there's nothing after it to take back
            link_button(
                url("/library/jump", to=f"e{seq}"),
                "",
                icon_name="skip-back",
                title=_("Jump back to here: take back everything after #e{seq}", seq=seq),
                kind="flat circular",
            )
            if position
            else None
        )
        why = (
            " · " + _("why: {reason}", reason=event["reason"])
            if event.get("reason") and req.gm
            else ""
        )
        rows.append(
            row(
                change_title(req, event, names),
                subtitle=f"#e{seq} · {when}{why}",
                suffix=h(t"{tail}{jump}"),
                cls="is-undone" if undone else "",
            )
        )
    more = None
    if len(events) >= limit and limit < HISTORY_MOST:
        older = url("/library", history=str(min(limit * 4, HISTORY_MOST))) + "#history"
        shown = link_button(older, _("Show older changes"), icon_name="chevrons-down", kind="flat")
        more = h(t'<div class="button-row">{shown}</div>')
    undo = words_form(req, ["undo"], _("Undo"), icon_name="rotate-ccw", kind="suggested")
    redo = words_form(req, ["redo"], _("Redo"), icon_name="rotate-cw")
    clear = link_button("/library/clear-history", _("Clear…"), icon_name="trash-2", kind="flat")
    return group(
        _("History"),
        h(t"{boxed_list(rows, empty=_('No changes yet.'))}{more}"),
        description=_(
            "Every change, newest first. Undo takes the last one back, or pick one; jump back "
            "to a change to take back everything after it."
        ),
        suffix=h(t"{undo}{redo}{clear}"),
        id_="history",
    )


def confirm_jump(req: Request) -> Response:
    """Jumping back to a change: the command's own preview of what goes (named as this view may
    name it), then jump, or leave it."""
    back = "/library#history"
    cancel = link_button(back, _("Cancel"), kind="pill")
    preview = req.run("undo", "--to", req.arg("to").strip() or "e0", "--dry-run")
    if not preview.ok:
        failed = failure(preview, title=_("Can't jump back there"))
        body = h(
            t'<section class="card dialog-page">{failed}<div class="button-row">{cancel}</div>'
            t"</section>"
        )
        return page(req, _("Jump back"), body, nav="library", back=back)
    names = {} if req.gm else record_index(req).names
    point = as_dict(preview.data.get("point"))
    seq = point.get("seq")
    steps = [as_dict(step) for step in as_list(preview.data.get("steps"))]
    question = _("Jump back to #e{seq}?", seq=seq)
    at = boxed_list([_step_row(req, point, names)])
    if not steps:
        done = link_button(back, _("Back"), kind="pill")
        nothing = _("Nothing after it is still in effect: the library is as it was then.")
        body = h(
            t'<section class="card dialog-page"><h2>{question}</h2>{at}'
            t'<p class="dim">{nothing}</p><div class="button-row">{done}</div></section>'
        )
        return page(req, _("Jump back"), body, nav="library", back=back)
    about = _(
        "Everything after it is taken back, newest first: each change is undone, and each roll "
        "is marked undone. Nothing is deleted: Redo, or jumping back to a later change, brings "
        "it back."
    )
    listed = [_step_row(req, step, names) for step in steps[:JUMP_LISTED]]
    if len(steps) > JUMP_LISTED:
        more = ngettext("… and {n} more", "… and {n} more", len(steps) - JUMP_LISTED)
        listed.append(row(h(t'<span class="dim">{more}</span>')))
    goes = ngettext("{n} step is taken back", "{n} steps are taken back", len(steps))
    argv = ["undo", "--to", f"e{seq}"]
    jump = words_form(
        req, argv, _("Jump back"), icon_name="skip-back", kind="destructive pill", next_=back
    )
    body = h(
        t'<section class="card dialog-page is-wide"><h2>{question}</h2>{at}'
        t'<p class="dim">{about}</p><h3 class="subhead">{goes}</h3>{boxed_list(listed)}'
        t"{command_line(shlex.join(['didact', *argv]))}"
        t'<div class="button-row">{cancel}{jump}</div></section>'
    )
    return page(req, _("Jump back"), body, nav="library", back=back)


def _step_row(req: Request, event: dict[str, JSON], names: dict[str, str]) -> Html:
    """One event in a jump's preview: a roll with a die, an undo with its arrow."""
    when = str(event.get("ts", ""))[:16].replace("T", " ")
    kind = event.get("kind")
    pic = "hexagon" if kind == "roll" else "rotate-ccw" if kind == "undo" else "edit-3"
    return row(
        change_title(req, event, names), subtitle=f"#e{event.get('seq')} · {when}", prefix=icon(pic)
    )


def confirm_clear_history(req: Request) -> Response:
    """What clearing the history drops and breaks, from the command's own preview; then the
    choice: back up first, clear, or leave it."""
    rolls = req.arg("rolls") == "1"
    argv = ["history", "--clear", *(["--rolls"] if rolls else [])]
    preview = req.run(*argv)
    back = "/library#history"
    cancel = link_button(back, _("Cancel"), kind="pill")
    toggle: Html | None = None  # the dice record (rolls and notes): kept unless asked for
    if rolls or preview.data.get("kept"):
        href = "/library/clear-history" if rolls else "/library/clear-history?rolls=1"
        dice = link_button(
            href, _("Also clear the dice record (rolls and notes)"),
            icon_name="check-square" if rolls else "square", kind="flat",
        )  # fmt: skip
        toggle = h(t'<div class="button-row">{dice}</div>')
    if not preview.ok:
        body: Html = h(t'<section class="card dialog-page">{failure(preview)}</section>')
    elif not preview.data.get("preview"):
        body = h(
            t'<section class="card dialog-page"><h2>{_("Nothing to clear")}</h2>'
            t'{markdown(preview.md)}{toggle}<div class="button-row">{cancel}</div></section>'
        )
    else:
        save = words_form(req, ["snapshot"], _("Back up first"), icon_name="archive", kind="pill")
        clear = words_form(
            req, [*argv, "--yes"], _("Clear the history"), icon_name="trash-2",
            kind="destructive pill", next_=back,
        )  # fmt: skip
        body = h(
            t'<section class="card dialog-page is-wide"><h2>{_("Clear the history?")}</h2>'
            t'<div class="dialog-text">{markdown(preview.md)}</div>{toggle}'
            t'<div class="button-row">{cancel}{save}{clear}</div></section>'
        )
    return page(req, _("Clear the history"), body, nav="library", back=back)


def _start_over(req: Request) -> Html:
    """Resetting the library: a page of its own asks first and shows what goes."""
    reset = link_button(
        "/library/reset", _("Reset…"), icon_name="alert-triangle", kind="destructive"
    )
    about = _(
        "Empty the library, as if Didact were newly installed: every world, campaign and change "
        "goes, and numbering starts again at #e1. A backup is made first, and backups stay."
    )
    return group(
        _("Start over"),
        boxed_list([row(_("Reset the library"), subtitle=about, suffix=reset)]),
        id_="reset",
    )


def confirm_reset(req: Request) -> Response:
    """What a reset empties, from the command's own preview; then reset, or leave it."""
    packs = req.arg("packs") == "1"
    argv = ["reset", *(["--packs"] if packs else [])]
    preview = req.run(*argv)
    back = "/library#reset"
    cancel = link_button(back, _("Cancel"), kind="pill")
    toggle: Html | None = None  # installed packs: kept unless asked for
    if packs or preview.data.get("packs"):
        href = "/library/reset" if packs else "/library/reset?packs=1"
        also = link_button(
            href, _("Also remove the installed packs"),
            icon_name="check-square" if packs else "square", kind="flat",
        )  # fmt: skip
        toggle = h(t'<div class="button-row">{also}</div>')
    if not preview.ok:
        body: Html = h(t'<section class="card dialog-page">{failure(preview)}</section>')
    else:
        reset = words_form(
            req, [*argv, "--yes"], _("Reset the library"), icon_name="alert-triangle",
            kind="destructive pill", next_="/",
        )  # fmt: skip
        body = h(
            t'<section class="card dialog-page is-wide"><h2>{_("Reset the library?")}</h2>'
            t'<div class="dialog-text">{markdown(preview.md)}</div>{toggle}'
            t'<div class="button-row">{cancel}{reset}</div></section>'
        )
    return page(req, _("Reset the library"), body, nav="library", back=back)


def _saves(req: Request) -> Html:
    saves = req.run("saves")
    rows: list[Html] = []
    for item in as_list(saves.data.get("saves")):
        save = as_dict(item)
        label = str(save.get("label", ""))
        form = words_form(
            req,
            ["rewind", label],
            _("Rewind"),
            icon_name="rewind",
            kind="destructive",
            confirm=Confirm(
                _("Rewind to “{label}”?", label=label),
                _(
                    "The campaign's records and state go back to that point, as one change "
                    "that undo can take back. Logs and the world's canon stay as they are."
                ),
                _("Rewind"),
            ),
        )
        rewind = guarded(
            "/library/rewind?save=" + quote(label), _("Rewind…"), form, icon_name="rewind"
        )
        remove = words_form(
            req, ["save", "--remove", label], "", icon_name="x",
            title=_("Remove “{label}”", label=label), kind="flat circular",
        )  # fmt: skip
        when = str(save.get("ts", ""))[:16].replace("T", " ")
        rows.append(
            row(label, subtitle=f"#e{save.get('event')} · {when}", suffix=h(t"{rewind}{remove}"))
        )
    body = boxed_list(rows, empty=_("No save points yet.")) if saves.ok else failure(saves)
    name = entry("w", placeholder=_("e.g. before the dragon"), label=_("Save point"), required=True)
    make = run_form(
        req,
        h(t"{name}{button(_('Save'), icon_name='save')}"),
        fields={"action": "words", "w": "save"},
        cls="action-row",
    )
    return group(
        _("Save points"),
        h(t"{body}{boxed_list([form_row(_('Make a save point'), make)])}"),
        id_="saves",
    )


def confirm_delete(req: Request) -> Response:
    """Deleting a world or campaign without JS: say what goes first."""
    kind = "world" if req.arg("world") else "campaign"
    key = req.arg(kind)
    form = _delete_form(req, kind, key, key, pill=True)
    cancel = link_button("/library#worlds", _("Cancel"), kind="pill")
    goes = _goes(kind) + " " + _("Undo brings it all back.")
    body = h(
        t'<section class="card dialog-page"><h2>{_delete_question(kind, key)}</h2>'
        t'<p class="dim">{goes}</p>'
        t"{command_line(shlex.join(['didact', kind, 'delete', key, '--yes']))}"
        t'<div class="button-row">{cancel}{form}</div></section>'
    )
    return page(req, _("Delete"), body, nav="library", back="/library#worlds")


def _backup_chip(kind: str) -> str | None:
    """How a backup was made, as a badge (none for one made by hand)."""
    chips = {
        "auto": pgettext("backup", "auto"),
        "before-restore": _("before restore"),
        "before-reset": _("before reset"),
    }
    return chips.get(kind)


def _backups(req: Request) -> Html:
    listed = req.run("snapshot", "--list")
    rows: list[Html] = []
    folder = ""
    for item in reversed(as_list(listed.data.get("snapshots"))):  # newest first
        backup = as_dict(item)
        folder = str(backup.get("path", "")).rpartition("/")[0]
        name = str(backup.get("name", ""))
        size = backup.get("bytes")
        made = _backup_chip(str(backup.get("kind")))
        badge = chip(made, kind="dim") if made else None
        form = words_form(
            req,
            ["snapshot", "--remove", name],
            _("Delete"),
            icon_name="trash-2",
            kind="destructive",
            next_="/library#backups",
            confirm=Confirm(
                _("Delete the backup {name}?", name=name),
                _("The zip file goes for good: this can't be undone."),
                _("Delete"),
            ),
        )
        href = "/library/remove-backup?name=" + quote(name)
        remove = guarded(href, _("Delete…"), form, icon_name="trash-2", kind="flat destructive")
        rows.append(
            row(
                h(t"{name} {badge}"),
                subtitle=human(size) if isinstance(size, int) else None,
                suffix=h(t"{_restore(req, name)}{remove}"),
            )
        )
    body = boxed_list(rows, empty=_("No backups yet.")) if listed.ok else failure(listed)
    where = h(t'<p class="hint">{icon("folder")}<span>{folder}</span></p>') if folder else None
    count = entry(
        "o:--keep", placeholder=_("how many"), type_="number", required=True,
        label=_("Backups to keep"), attrs={"min": "0"},
    )  # fmt: skip
    keep = run_form(
        req,
        h(t"{count}{button(_('Keep the newest'), icon_name='scissors', kind='destructive')}"),
        fields={"action": "words", "w": ["snapshot"]},
        cls="action-row",
        confirm=Confirm(
            _("Delete the older backups?"),
            _("Everything but the newest ones you keep goes for good: this can't be undone."),
            _("Delete"),
        ),
    )
    now = words_form(req, ["snapshot"], _("Back up now"), icon_name="archive", kind="suggested")
    return group(
        _("Backups"),
        h(t"{body}{where}{boxed_list([form_row(_('Prune the backups'), keep)])}"),
        description=_(
            "Zips of the whole library. Ending a session makes one too (auto): the newest "
            "{count} of those stay.",
            count=AUTO_KEEP,
        ),
        suffix=now,
        id_="backups",
    )


def _restores() -> str:
    return _(
        "Everything in the library but its backups is replaced by the backup's. The library as "
        "it is now is backed up first: undo can't take a restore back, but restoring that backup "
        "can."
    )


def _restore(req: Request, name: str) -> Html:
    form = words_form(
        req,
        ["snapshot", "--restore", name, "--yes"],
        _("Restore"),
        icon_name="refresh-ccw",
        kind="destructive",
        next_="/library#backups",
        confirm=Confirm(_("Restore the backup {name}?", name=name), _restores(), _("Restore")),
    )
    href = "/library/restore-backup?name=" + quote(name)
    return guarded(href, _("Restore…"), form, icon_name="refresh-ccw", kind="flat")


def confirm_restore_backup(req: Request) -> Response:
    """Restoring a backup without JS: the command's own preview first (what the backup holds
    next to the library now, and what happens), then the choice."""
    name = req.arg("name")
    argv = ["snapshot", "--restore", name]
    preview = req.run(*argv)
    back = "/library#backups"
    cancel = link_button(back, _("Cancel"), kind="pill")
    if not preview.ok:
        failed = failure(preview, title=_("Can't restore this"))
        body = h(
            t'<section class="card dialog-page">{failed}<div class="button-row">{cancel}</div>'
            t"</section>"
        )
    else:
        restore = words_form(
            req, [*argv, "--yes"], _("Restore"), icon_name="refresh-ccw", kind="destructive pill",
            next_=back,
        )  # fmt: skip
        question = _("Restore the backup {name}?", name=name)
        body = h(
            t'<section class="card dialog-page is-wide"><h2>{question}</h2>'
            t'<div class="dialog-text">{markdown(preview.md)}</div>'
            t'<div class="button-row">{cancel}{restore}</div></section>'
        )
    return page(req, _("Restore a backup"), body, nav="library", back=back)


def confirm_remove_backup(req: Request) -> Response:
    """Deleting a backup without JS: say it's for good first."""
    name = req.arg("name")
    form = words_form(
        req, ["snapshot", "--remove", name], _("Delete"), icon_name="trash-2",
        kind="destructive pill", next_="/library#backups",
    )  # fmt: skip
    cancel = link_button("/library#backups", _("Cancel"), kind="pill")
    question = _("Delete the backup {name}?", name=name)
    goes = _("The zip file goes for good: this can't be undone.")
    body = h(
        t'<section class="card dialog-page"><h2>{question}</h2>'
        t'<p class="dim">{goes}</p>'
        t"{command_line(shlex.join(['didact', 'snapshot', '--remove', name]))}"
        t'<div class="button-row">{cancel}{form}</div></section>'
    )
    return page(req, _("Delete a backup"), body, nav="library", back="/library#backups")


def confirm_rewind(req: Request) -> Response:
    """Rewinding without JS: say what it does first."""
    label = req.arg("save")
    form = words_form(
        req,
        ["rewind", label],
        _("Rewind"),
        icon_name="rewind",
        kind="destructive pill",
        next_="/library#saves",
    )
    cancel = link_button("/library#saves", _("Cancel"), kind="pill")
    question = _("Rewind to “{label}”?", label=label)
    goes = _("The campaign goes back to that point, as one change that undo can take back.")
    body = h(
        t'<section class="card dialog-page"><h2>{question}</h2>'
        t'<p class="dim">{goes}</p>{command_line(shlex.join(["didact", "rewind", label]))}'
        t'<div class="button-row">{cancel}{form}</div></section>'
    )
    return page(req, _("Rewind"), body, nav="library", back="/library#saves")
