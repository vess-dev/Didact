"""The page chrome (header bar, sidebar, GM banner, toasts) and the widgets that show results."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from didact.core import i18n
from didact.core.i18n import _
from didact.web.app import Flash, Ran, Request, Response
from didact.web.html import Html, button, h, hidden, icon, join
from didact.web.markdown import inline, markdown
from didact.web.static import asset_url

NAV = (
    ("overview", "/", "home"),
    ("status", "/status", "activity"),
    ("records", "/records", "book"),
    ("graph", "/graph", "share-2"),
    ("journal", "/journal", "book-open"),
    ("reference", "/reference", "bookmark"),
    ("library", "/library", "layers"),
    ("commands", "/commands", "terminal"),
    ("settings", "/settings", "settings"),
)


def nav_labels() -> dict[str, str]:
    return {
        "overview": _("Overview"),
        "status": _("Status"),
        "records": _("Records"),
        "graph": _("Graph"),
        "journal": _("Journal"),
        "reference": _("Reference"),
        "library": _("Library"),
        "commands": _("Commands"),
        "settings": _("Settings"),
    }


THEME_COOKIE = "didact_theme"  # light or dark, as the theme button chose; unset: the system's
LANGUAGE_COOKIE = "didact_lang"  # the app's language, as Settings chose; unset: the browser's


def page(
    req: Request,
    title: str,
    body: Html,
    *,
    nav: str,
    back: str | None = None,
    subtitle: str | None = None,
    wide: bool = False,
    scripts: Sequence[str] = (),
    status: int = 200,
) -> Response:
    """A whole page: the chrome around `body`, and the last action's toast unless the page
    showed it already."""
    flash = req.take_flash()
    toasts = toast(req, flash) if flash is not None else None
    extra = [h(t'<script src="{asset_url(name)}" defer></script>') for name in scripts]
    content = "content is-wide" if wide else "content"
    theme = req.cookies.get(THEME_COOKIE)
    chosen = theme if theme in ("light", "dark") else None  # else the system's
    root = h(t' data-theme="{chosen}"') if chosen else None
    markup = h(
        t'<!doctype html>\n<html lang="{i18n.current().tag}"{root}><head><meta charset="utf-8">'
        t'<meta name="viewport" content="width=device-width, initial-scale=1">'
        t'<meta name="color-scheme" content="{chosen or "light dark"}">'
        t"<title>{title} · Didact</title>"
        t'<link rel="icon" href="{asset_url("favicon.svg")}">'
        t'<link rel="stylesheet" href="{asset_url("style.css")}">'
        t'<script src="{asset_url("app.js")}"></script>{extra}</head>'
        t'<body class="{"is-gm" if req.gm else "is-player"}"{_script_words()}>'
        t'<input type="checkbox" id="nav-toggle" class="nav-toggle" aria-hidden="true">'
        t'<div class="window">{_sidebar(req, nav)}'
        t'<label for="nav-toggle" class="scrim" aria-hidden="true"></label>'
        t'<div class="main">{_headerbar(req, title, subtitle, back)}{gm_banner(req)}'
        t'<main class="{content}" id="content">{body}</main></div></div>'
        t'<div class="toasts" aria-live="polite">{toasts}</div></body></html>'
    )
    return Response.html(markup, status)


def _script_words() -> Html:
    """What app.js says, in the page's language (data attributes: the CSP allows no inline
    script)."""
    words = {
        "sure": _("Are you sure?"),
        "ok": _("OK"),
        "cancel": _("Cancel"),
        "copied": _("Copied"),
    }
    return join(h(t' data-t-{key}="{text}"') for key, text in words.items())


def _sidebar(req: Request, nav: str) -> Html:
    labels = nav_labels()
    rows = [
        h(
            t'<a class="nav-row{" is-active" if key == nav else ""}" href="{href}">'
            t"{icon(pic)}<span>{labels[key]}</span></a>"
        )
        for key, href, pic in NAV
    ]
    world, campaign = req.app.context()
    where = " · ".join(name for name in (world, campaign) if name) or _("no world yet")
    return h(
        t'<aside class="sidebar" aria-label="{_("Sections")}">'
        t'<a class="brand" href="/">{icon("hexagon")}<span>Didact</span></a>'
        t'<nav class="nav">{rows}</nav><div class="sidebar-foot">'
        t'<a href="/library" title="{_("The active world and campaign")}">{icon("globe")}'
        t'<span>{where}</span></a><a href="/about">{_("Fonts & icons")}</a></div></aside>'
    )


def _headerbar(req: Request, title: str, subtitle: str | None, back: str | None) -> Html:
    menu = h(
        t'<label for="nav-toggle" class="icon-button menu-button" title="{_("Menu")}">'
        t"{icon('menu')}</label>"
    )
    back_button = (
        h(
            t'<a class="icon-button" href="{back}" title="{_("Back")}" aria-label="{_("Back")}">'
            t"{icon('arrow-left')}</a>"
        )
        if back
        else None
    )
    sub = h(t'<span class="subtitle">{subtitle}</span>') if subtitle else None
    search = h(
        t'<a class="icon-button" href="/search" title="{_("Search")}" '
        t'aria-label="{_("Search")}">{icon("search")}</a>'
    )
    docs = h(
        t'<a class="icon-button" href="/docs/" title="{_("Code documentation")}" '
        t'aria-label="{_("Code documentation")}">{icon("code")}</a>'
    )
    style = _("Dark or light style")
    theme = h(
        t'<button type="button" class="icon-button js-only" data-theme-toggle '
        t'title="{style}" aria-label="{style}">'
        t"{icon('moon', cls='icon when-light')}{icon('sun', cls='icon when-dark')}</button>"
    )
    return h(
        t'<header class="headerbar"><div class="hb-start">{menu}{back_button}</div>'
        t'<div class="hb-title"><h1>{title}</h1>{sub}</div>'
        t'<div class="hb-end">{search}{docs}{gm_toggle(req)}{theme}</div></header>'
    )


def gm_toggle(req: Request) -> Html:
    on = req.gm
    title = _("GM view is on: spoilers shown") if on else _("GM view is off: what the players know")
    return h(
        t'<form method="post" action="/gm" class="gm-form">{csrf(req)}{hidden("next", req.here)}'
        t"{hidden('on', '0' if on else '1')}"
        t'<button class="icon-button gm-toggle{" is-on" if on else ""}" '
        t'aria-pressed="{"true" if on else "false"}" title="{title}">'
        t"{icon('eye' if on else 'eye-off')}<span>GM</span></button></form>"
    )


def gm_banner(req: Request) -> Html | None:
    if not req.gm:
        return None
    return h(
        t'<div class="banner" role="status">{icon("eye")}<span>{_("GM view: spoilers shown")}'
        t'</span><form method="post" action="/gm">{csrf(req)}{hidden("next", req.here)}'
        t"{hidden('on', '0')}{button(_('Hide them'), kind='flat')}</form></div>"
    )


def csrf(req: Request) -> Html:
    return hidden("csrf", req.app.secret)


# ---------------------------------------------------------------------------- forms


@dataclass(frozen=True, slots=True)
class Confirm:
    """Ask before submitting: a dialog's title, text and action button."""

    title: str
    body: str
    action: str
    kind: str = "destructive"


def run_form(
    req: Request,
    body: Html,
    *,
    fields: Mapping[str, str | Sequence[str]] | None = None,
    next_: str | None = None,
    next_ok: str | None = None,
    panel: bool = False,
    cls: str = "",
    confirm: Confirm | None = None,
    data: Mapping[str, str] | None = None,
) -> Html:
    """A form that runs a command through `/run`, then comes back to `next_` (default: here),
    or goes on to `next_ok` when it worked. `data` adds `data-*` attributes for app.js."""
    parts = [csrf(req), hidden("next", next_ or req.here)]
    if next_ok:
        parts.append(hidden("next_ok", next_ok))
    if panel:
        parts.append(hidden("show", "panel"))
    for name, value in (fields or {}).items():
        values = [value] if isinstance(value, str) else list(value)
        parts.extend(hidden(name, v) for v in values)
    attrs: dict[str, str] = {}
    if confirm is not None:
        attrs = {
            "data-confirm": confirm.title,
            "data-confirm-body": confirm.body,
            "data-confirm-action": confirm.action,
            "data-confirm-kind": confirm.kind,
        }
    attrs.update({f"data-{k}": v for k, v in (data or {}).items()})
    extra = join(h(t' {k}="{v}"') for k, v in attrs.items())
    return h(t'<form method="post" action="/run" class="{cls}"{extra}>{parts}{body}</form>')


def words_form(
    req: Request,
    argv: Sequence[str],
    label: str,
    *,
    icon_name: str | None = None,
    kind: str = "",
    title: str | None = None,
    next_: str | None = None,
    next_ok: str | None = None,
    panel: bool = False,
    confirm: Confirm | None = None,
    cls: str = "inline",
) -> Html:
    """A one-button form that runs a fixed command line."""
    return run_form(
        req,
        button(label, icon_name=icon_name, kind=kind, title=title),
        fields={"action": "words", "w": list(argv)},
        next_=next_,
        next_ok=next_ok,
        panel=panel,
        confirm=confirm,
        cls=cls,
    )


def guarded(href: str, label: str, form: Html, *, icon_name: str, kind: str = "") -> Html:
    """A button that asks first. With JS it opens a dialog from the hidden `form` (which has
    a `Confirm`); without JS it goes to `href`, a page that asks the same question."""
    cls = " ".join(["button", *(f"is-{k}" for k in kind.split())])
    return h(
        t'<a class="{cls}" href="{href}" data-confirm-form>{icon(icon_name)}<span>{label}</span>'
        t"</a><div hidden>{form}</div>"
    )


# ---------------------------------------------------------------------------- results


def command_line(line: str) -> Html:
    label = _("Copy the command")
    copy = h(
        t'<button type="button" class="icon-button js-only" data-copy="{line}" '
        t'title="{label}" aria-label="{label}">{icon("copy")}</button>'
    )
    return h(t'<div class="command-line"><code>$ {line}</code>{copy}</div>')


def undo_button(req: Request, ran: Ran) -> Html | None:
    target = ran.undo_target
    if target is None:
        return None
    return words_form(req, ["undo", "--event", target], _("Undo"), icon_name="rotate-ccw")


def output(req: Request, ran: Ran) -> str:
    """What a command said, as this view may show it. Undo quotes the change it took back,
    which can hold a secret: the player view names the changes, not what they were."""
    if req.gm or not ran.ok or ran.argv[:1] not in (("undo",), ("redo",)):
        return ran.md
    if ran.data.get("dry_run"):  # what it would take back, by number only
        steps = ran.data.get("steps")
        found = ran.data.get("events")
        numbers = (
            [s.get("seq") for s in steps if isinstance(s, dict)]
            if isinstance(steps, list)
            else found
            if isinstance(found, list)
            else [ran.data.get("event")]
        )
        listed = ", ".join(f"#e{n}" for n in numbers if isinstance(n, int))
        if not listed:
            return _("dry run: {done}", done=_("nothing changed"))
        return _("dry run: would undo {events}", events=listed)
    if ran.argv[0] == "redo":
        redone, event = ran.data.get("redone"), ran.data.get("event")
        return _("✔ redid #e{event} ({undo})", event=redone, undo=f"#e{event}")
    undone = ran.data.get("undone")
    if not isinstance(undone, list):
        return _("✔ undid a change")
    return _("✔ undid {changes}", changes=", ".join(f"#e{n}" for n in undone))


def result_panel(req: Request, ran: Ran) -> Html:
    """A command's outcome in full: its command line, then its output or its error and fix."""
    if ran.ok:
        head = h(
            t'<div class="result-head is-ok">{icon("check-circle")}<span>{_("Done")}</span></div>'
        )
        body = markdown(output(req, ran)) or h(t'<p class="dim">{_("(no output)")}</p>')
    else:
        failed = h(t"{icon('alert-circle')}<span>{_('Failed')}</span>")
        head = h(t'<div class="result-head is-error">{failed}</div>')
        body = error_body(ran)
    return h(
        t'<section class="card result" id="result">{head}{command_line(ran.line)}{body}'
        t'<div class="result-tools">{undo_button(req, ran)}</div></section>'
    )


def error_body(ran: Ran) -> Html:
    err = ran.error
    if err is None:  # the command ran but reported a problem (exit code 1)
        return markdown(ran.md)
    where = (
        h(t'<p class="dim small">{_("where: {where}", where=err.where)}</p>') if err.where else None
    )
    fix = (
        h(t'<p class="hint">{icon("info")}<span>{inline(err.hint)}</span></p>')
        if err.hint
        else None
    )
    return h(t'<div class="error"><p class="error-message">{err.message}</p>{fix}{where}</div>')


def toast(req: Request, flash: Flash) -> Html:
    """A short note of what just happened, with its command line (and Undo)."""
    ran = flash.ran
    if ran.ok:
        text_lines = output(req, ran).strip().splitlines()
        lines = [line.removeprefix("✔ ") for line in text_lines if line.strip()]
        text = join(h(t"<div>{inline(line)}</div>") for line in lines[:3])
        if len(lines) > 3:
            text = h(t'{text}<div class="dim">…</div>')
        kind, pic = "is-ok", "check-circle"
    else:
        err = ran.error
        said = ran.md.strip().splitlines() or [_("it didn't work")]
        message = err.message if err is not None else said[0]
        hint = h(t'<div class="dim">{inline(err.hint)}</div>') if err and err.hint else None
        text = h(t"<div>{message}</div>{hint}")
        kind, pic = "is-error", "alert-circle"
    close_label = _("Close")
    close = h(
        t'<a class="icon-button" href="{req.here}" data-dismiss title="{close_label}" '
        t'aria-label="{close_label}">{icon("x")}</a>'
    )
    line = h(t'<code class="toast-command">$ {ran.line}</code>')
    return h(
        t'<div class="toast {kind}" role="status">{icon(pic)}'
        t'<div class="toast-text">{text}{line}</div>{undo_button(req, ran)}{close}</div>'
    )


def failure(ran: Ran, *, title: str | None = None) -> Html:
    """A read that failed: its error and fix, as the page's content."""
    title = title if title is not None else _("Can't show this")
    return h(
        t'<section class="card failure"><h2>{title}</h2>{error_body(ran)}'
        t"{command_line(ran.line)}</section>"
    )
