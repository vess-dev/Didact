"""The pages, and the routes that reach them."""

import re
from collections.abc import Callable
from dataclasses import dataclass

from didact.core.i18n import _
from didact.web.app import Request, Response
from didact.web.html import boxed_list, group, h, link_button, row, status_page
from didact.web.layout import page
from didact.web.pages import (
    actions,
    commands,
    drafts,
    graph,
    journal,
    library,
    overview,
    records,
    reference,
    settings,
    status,
)
from didact.web.static import asset_url

type Handler = Callable[[Request], Response]


@dataclass(frozen=True, slots=True)
class Route:
    method: str
    pattern: re.Pattern[str]
    handler: Handler


def _route(method: str, pattern: str, handler: Handler) -> Route:
    return Route(method, re.compile(pattern), handler)


def not_found(req: Request) -> Response:
    home = link_button("/", _("Overview"), icon_name="home", kind="suggested pill")
    body = status_page("compass", _("Nothing here"), _("That page doesn't exist."), home)
    return page(req, _("Not found"), body, nav="", status=404)


def about(req: Request) -> Response:
    rows = [
        row(
            _("Ubuntu font family"),
            subtitle=_("Ubuntu Font Licence 1.0 · Dalton Maag, for Canonical"),
            href=asset_url("fonts/UFL-LICENCE.txt"),
        ),
        row(
            _("Feather icons"),
            subtitle=_("MIT License · Cole Bemis"),
            href=asset_url("feather-LICENSE.txt"),
        ),
    ]
    fonts = group(
        _("Fonts and icons"),
        boxed_list(rows),
        description=_("Shipped with Didact: no network needed."),
    )
    guide = link_button("/guide/web", _("How this app works"), icon_name="book-open", kind="pill")
    return page(req, _("About"), h(t'{fonts}<div class="button-row">{guide}</div>'), nav="")


ROUTES: tuple[Route, ...] = (
    _route("GET", r"/", overview.show),
    _route("GET", r"/status", status.show),
    _route("GET", r"/records", records.index),
    _route("GET", r"/records/new", records.new_form),
    _route("GET", r"/record/(?P<ref>[^/]+)", records.show),
    _route("GET", r"/record/(?P<ref>[^/]+)/delete", records.confirm_delete),
    _route("GET", r"/drafts", drafts.index),
    _route("GET", r"/drafts/new", drafts.new),
    _route("GET", r"/drafts/made", drafts.made),
    _route("POST", r"/drafts/start", drafts.start),
    _route("GET", r"/drafts/(?P<draft>[^/]+)", drafts.show),
    _route("GET", r"/drafts/(?P<draft>[^/]+)/discard", drafts.confirm_discard),
    _route("POST", r"/drafts/(?P<draft>[^/]+)/answer", drafts.answer),
    _route("POST", r"/drafts/(?P<draft>[^/]+)/edit", drafts.edit),
    _route("POST", r"/drafts/(?P<draft>[^/]+)/commit", drafts.commit),
    _route("GET", r"/graph", graph.show),
    _route("GET", r"/api/graph", graph.api),
    _route("GET", r"/journal", journal.index),
    _route("GET", r"/journal/(?P<n>\d{1,6})", journal.session),
    _route("GET", r"/journal/(?P<n>\d{1,6})/transcript", journal.transcript),
    _route("GET", r"/reference", reference.index),
    _route("GET", r"/search", reference.search),
    _route("GET", r"/rules/(?P<rule>[^/]+)", reference.rule),
    _route("GET", r"/tables/(?P<table>[^/]+)", reference.table),
    _route("GET", r"/reference/(?P<section>[^/]+)", reference.section),
    _route("GET", r"/guide/(?P<topic>[^/]+)", reference.guide),
    _route("GET", r"/library", library.index),
    _route("GET", r"/library/rewind", library.confirm_rewind),
    _route("GET", r"/library/jump", library.confirm_jump),
    _route("GET", r"/library/delete", library.confirm_delete),
    _route("GET", r"/library/uninstall", library.confirm_uninstall),
    _route("GET", r"/library/clear-history", library.confirm_clear_history),
    _route("GET", r"/library/remove-backup", library.confirm_remove_backup),
    _route("GET", r"/library/reset", library.confirm_reset),
    _route("GET", r"/library/updates", library.confirm_updates),
    _route("GET", r"/library/restore-backup", library.confirm_restore_backup),
    _route("GET", r"/commands", commands.index),
    _route("GET", r"/commands/(?P<name>.+)", commands.form),
    _route("GET", r"/about", about),
    _route("POST", r"/run", actions.run),
    _route("POST", r"/gm", actions.gm),
    _route("GET", r"/settings", settings.show),
    _route("POST", r"/language", settings.language),
    _route("GET", r"/settings/thesaurus/progress", settings.progress),
    _route("POST", r"/settings/thesaurus/download", settings.download),
    _route("GET", r"/docs", lambda req: Response.redirect("/docs/")),
    _route("GET", r"/docs/(?P<path>[^?#]*)", settings.docs),
)
