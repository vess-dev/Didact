"""The journal: sessions, each opening to its scenes, beats and rolls."""

from urllib.parse import quote

from didact.core import labels
from didact.core.i18n import _, ngettext, pgettext
from didact.core.output import JSON
from didact.web.app import Request, Response
from didact.web.html import (
    Html,
    chip,
    command_url,
    expander,
    h,
    icon,
    link_button,
    status_page,
)
from didact.web.layout import failure, page, words_form
from didact.web.markdown import inline, markdown
from didact.web.pages.common import as_dict, as_list, secret_note

INLINE = 3  # the newest sessions shown at once; older ones load when opened


def index(req: Request) -> Response:
    listing = req.run("session", "list", gm=True)
    if not listing.ok:
        return page(req, _("Journal"), failure(listing), nav="journal")
    sessions = [as_dict(s) for s in as_list(listing.data.get("sessions"))]
    if not sessions:
        playing = req.app.context()[1] is not None  # sessions belong to a campaign
        start = (
            words_form(
                req,
                ["session", "start"],
                _("Start session 1"),
                icon_name="play",
                kind="suggested pill",
            )
            if playing
            else link_button("/library#worlds", _("Start a campaign"), kind="suggested pill")
        )
        about = _("Each session keeps its scenes, beats and rolls.")
        empty = status_page("book-open", _("No sessions yet"), about, start)
        return page(req, _("Journal"), empty, nav="journal")
    parts: list[Html] = []
    for position, session in enumerate(reversed(sessions)):
        number = session.get("session")
        if not isinstance(number, int):
            continue
        title = str(session.get("name") or _("Session {n}", n=number))
        status = str(session.get("status") or "")
        summary = str(session.get("summary") or "")
        badge = chip(pgettext("session", "open"), kind="accent") if status == "open" else None
        label = _("Session {n}", n=number)
        head = h(t'<span>{label}</span><span class="dim"> · {title}</span> {badge}')
        teaser = h(t'<p class="dim small">{inline(summary[:160])}</p>') if summary else None
        if position < INLINE:
            body = session_body(req, number)
            attrs: dict[str, str] = {}
        else:
            open_link = link_button(
                f"/journal/{number}", _("Open session {n}", n=number), kind="flat"
            )
            body = h(t'<div class="fragment">{teaser}{open_link}</div>')
            attrs = {"data-fragment": f"/journal/{number}?fragment=1"}
        parts.append(expander(head, body, attrs=attrs))
    body = h(t'<div class="stack">{parts}</div>')
    count = ngettext("{n} sessions", "{n} sessions", len(sessions))  # English: "1 sessions" too
    return page(req, _("Journal"), body, nav="journal", subtitle=count)


def session(req: Request) -> Response:
    number = int(req.params["n"])
    body = session_body(req, number)
    if req.arg("fragment"):
        return Response.html(body)
    return page(req, _("Session {n}", n=number), body, nav="journal", back="/journal")


def session_body(req: Request, number: int) -> Html:
    shown = req.run("session", "show", str(number), gm=True)
    if not shown.ok:
        return failure(shown)
    data = shown.data
    titles, summaries = _scene_notes(data)
    entries = [as_dict(e) for e in as_list(data.get("entries"))]
    scenes = [s for s in as_list(data.get("scenes")) if isinstance(s, int)]
    parts: list[Html | None] = []
    summary = str(data.get("summary") or "")
    if summary:
        parts.append(h(t'<div class="summary">{markdown(summary)}</div>'))
    loose = [e for e in entries if not isinstance(e.get("scene"), int)]
    if loose:
        parts.append(_timeline(loose))
    for scene in scenes:
        name = titles.get(scene) or _("Scene {n}", n=scene)
        own = [e for e in entries if e.get("scene") == scene]
        note = summaries.get(scene)
        about = h(t'<div class="summary dim">{markdown(note)}</div>') if note else None
        timeline = _timeline(own) if own else h(t'<p class="dim small">{_("Nothing logged.")}</p>')
        heading = _("Scene {n} · {name}", n=scene, name=name)
        parts.append(h(t'<h3 class="subhead">{heading}</h3>{about}{timeline}'))
    if not entries and not summary:
        parts.append(h(t'<p class="dim">{_("Nothing logged yet.")}</p>'))
    hidden = data.get("hidden")
    parts.append(secret_note(hidden if isinstance(hidden, int) else 0, "secret beat"))
    said = link_button(f"/journal/{number}/transcript", _("Transcript"), icon_name="file-text")
    alone = link_button(f"/journal/{number}", _("Open on its own"), icon_name="external-link")
    tools = h(t'<div class="button-row">{said}{alone}</div>')
    return h(t'<div class="session">{parts}{tools}</div>')


def _scene_notes(data: dict[str, JSON]) -> tuple[dict[int, str], dict[int, str]]:
    """Scene titles and summaries, from `session show`'s `scene_info`."""
    titles: dict[int, str] = {}
    summaries: dict[int, str] = {}
    for item in (as_dict(i) for i in as_list(data.get("scene_info"))):
        number = item.get("scene")
        if isinstance(number, int):
            titles[number] = str(item.get("title") or _("Scene {n}", n=number))
            if item.get("summary"):
                summaries[number] = str(item["summary"])
    return titles, summaries


def _timeline(entries: list[dict[str, JSON]]) -> Html:
    items: list[Html] = []
    for entry in entries:
        text = str(entry.get("text") or "")
        label, _sep, rest = text.partition(" ")
        roll = label.startswith("#r")
        pic = icon("hexagon" if roll else "chevron-right", cls="icon beat-icon")
        secret = (
            h(t'<span class="gm-mark" title="{_("GM only")}">{icon("eye-off")}</span>')
            if entry.get("secret")
            else None
        )
        kind = entry.get("kind")
        tag = h(t'<span class="beat-kind">{labels.beat_name(str(kind))}</span> ') if kind else None
        tools = None if roll else _beat_tools(label)
        items.append(
            h(
                t'<li class="beat{" is-roll" if roll else ""}">{pic}'
                t'<span class="beat-where">{label}</span>'
                t'<div class="beat-text">{secret}{tag}{rest}</div>{tools}</li>'
            )
        )
    return h(t'<ol class="timeline">{items}</ol>')


def _beat_tools(beat_id: str) -> Html:
    """Edit a beat (its text, who it's about, secrecy) or remove it: the command forms."""
    edit = command_url("beat edit") + "?a.beat-id=" + quote(beat_id)
    remove = command_url("beat rm") + "?a.beat-id=" + quote(beat_id)
    return h(
        t'<span class="beat-tools">'
        t'<a class="icon-button" href="{edit}" title="{_("Edit {beat}", beat=beat_id)}">'
        t"{icon('edit-2')}</a>"
        t'<a class="icon-button" href="{remove}" title="{_("Remove {beat}", beat=beat_id)}">'
        t"{icon('x')}</a>"
        t"</span>"
    )


def transcript(req: Request) -> Response:
    number = int(req.params["n"])
    shown = req.run("transcript", str(number))
    body = markdown(shown.md) if shown.ok else failure(shown)
    back = f"/journal/{number}"
    return page(
        req,
        _("Transcript {n}", n=number),
        h(t'<div class="card">{body}</div>'),
        nav="journal",
        back=back,
    )
