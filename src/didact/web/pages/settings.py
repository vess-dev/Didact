"""Settings: the campaign's options (its system's variant and optional rules), the app's language,
the thesaurus searches use for synonyms, and the code's API documentation (served at /docs/,
rebuilt when the code changed)."""

import json
import mimetypes
import subprocess
import sys
from pathlib import Path

from didact.core import i18n, labels, words
from didact.core.i18n import _, pgettext
from didact.core.output import JSON
from didact.web.app import Request, Response
from didact.web.html import (
    Html,
    boxed_list,
    button,
    chip,
    choice_row,
    expander,
    form_row,
    group,
    h,
    hidden,
    join,
    link_button,
    row,
    select,
)
from didact.web.layout import LANGUAGE_COOKIE, csrf, failure, page, run_form, words_form
from didact.web.markdown import inline
from didact.web.pages.actions import safe_path
from didact.web.pages.common import as_dict, as_list

YEAR = 60 * 60 * 24 * 365


def show(req: Request) -> Response:
    body = h(t"{_options(req)}{_language(req)}{_thesaurus(req)}{_docs(req)}")
    return page(req, _("Settings"), body, nav="settings")


def _options(req: Request) -> Html | None:
    """The campaign's options: its system's variant and optional rules, as session zero asks
    them. Each can stay at its default ("default: …", which follows what another option
    implies), or be set; saving runs `campaign profile` with what changed. Each says what it
    does: a flag what turning it on changes, a choice what each of its values means."""
    asked = req.run("session", "zero")
    if not asked.ok:
        return None  # no campaign yet
    found = [as_dict(q) for q in as_list(asked.data.get("questions"))]
    rows: list[Html] = []
    for question in (q for q in found if q.get("option") is True):
        key = str(question.get("key"))
        title = str(question.get("title") or key)
        answer = question.get("answer")
        was = "" if answer is None else _shown(answer)  # what the profile says: "" is unset
        unset = labels.on_off(_shown(question.get("unset")))
        setter = as_dict(question.get("implied_by"))
        default = (
            _(
                "(default: {value}, as {option} is {choice})",
                value=unset,
                option=str(setter.get("title")),
                choice=labels.on_off(_shown(setter.get("value"))),
            )
            if setter
            else _("(default: {value})", value=unset)
        )
        choices = [("", default)]
        choices += [(str(c), labels.on_off(str(c))) for c in as_list(question.get("choices"))]
        meanings = {str(k): str(v) for k, v in as_dict(question.get("meanings")).items() if v}
        value = _shown(question.get("value"))
        source = str(question.get("source") or "").replace(" ", "\u00a0")  # "p. 173" stays whole
        flag = [str(c) for c in as_list(question.get("choices"))] == ["on", "off"]
        if flag:  # what turning it on does, whether it's on or not
            text = str(question.get("help") or meanings.get("on") or "")
            said = _("When on: {what}", what=text) if text else ""
            more = None
        else:  # what the value in play means, and what each of the others would
            said = meanings.get(value, "")
            every = [
                row(
                    labels.on_off(choice),
                    subtitle=inline(meaning),
                    suffix=chip(pgettext("an option's value", "in play"), kind="accent")
                    if choice == value
                    else None,
                )
                for choice, meaning in meanings.items()
            ]
            more = (
                expander(_("What each choice means"), boxed_list(every), cls="is-plain")
                if len(every) > 1
                else None
            )
        about = (
            f"{said} ({source})" if said and source else said or (f"({source})" if source else "")
        )
        picker = select(f"opt.{key}", choices, was, label=title)
        control = h(t"{picker}{hidden(f'was.{key}', was)}")
        rows.append(choice_row(title, control, about=inline(about) if about else None, more=more))
    if not rows:
        return None
    save = button(_("Save"), icon_name="check", kind="suggested")
    form = run_form(
        req,
        h(t'{boxed_list(rows)}<div class="button-row">{save}</div>'),
        fields={"action": "options"},
        next_="/settings#options",
    )
    return group(
        _("Options"),
        form,
        description=_(
            "The variant and optional rules this campaign plays with, as its system describes "
            "them: its rules, character creation and generators follow them, and the brief "
            "tells the GM what they can't enforce. Each says what it does; leave one at its "
            "default to follow the system, or what another option implies."
        ),
        id_="options",
    )


def _shown(value: JSON) -> str:
    """An option's value as the profile writes it: a flag as on or off."""
    if isinstance(value, bool):
        return "on" if value else "off"
    return str(value)


def _language(req: Request) -> Html:
    chosen = req.cookies.get(LANGUAGE_COOKIE, "")
    options = [("", _("The browser's language"))]
    options += [
        (lang.code, lang.name if lang.code == "en" else f"{lang.name} · {lang.english}")
        for lang in i18n.LANGUAGES.values()
    ]
    control = select(
        "lang", options, chosen if chosen in i18n.LANGUAGES else "", label=_("Language")
    )
    form = h(
        t'<form method="post" action="/language" class="action-row">{csrf(req)}'
        t"{hidden('next', '/settings')}{control}{button(_('Use it'), kind='suggested')}</form>"
    )
    return group(
        _("Language"),
        boxed_list([form_row(_("The app's language"), form)]),
        description=_(
            "The app, its guides and what commands show here. The command line and the LLMs "
            "that use it stay in English: the language chosen here is only the app's."
        ),
        id_="language",
    )


def language(req: Request) -> Response:
    """Choose the app's language (a cookie; empty: the browser's), then go back."""
    code = req.field("lang")
    if code in i18n.LANGUAGES:
        cookie = f"{LANGUAGE_COOKIE}={code}; Path=/; Max-Age={YEAR}; SameSite=Strict"
    else:
        cookie = f"{LANGUAGE_COOKIE}=; Path=/; Max-Age=0; SameSite=Strict"
    response = Response.redirect(safe_path(req.field("next")))
    response.headers.append(("Set-Cookie", cookie))
    return response


def _thesaurus(req: Request) -> Html:
    have = req.run("setup", "thesaurus", "--check")
    if not have.ok:
        return group(_("Thesaurus"), failure(have), id_="thesaurus")
    back = "/settings#thesaurus"
    rows: list[Html] = []
    installed: set[str] = set()
    for item in as_list(have.data.get("lexicons")):
        if not isinstance(item, dict):
            continue
        code = str(item.get("language") or "")
        installed.add(code)
        remove = words_form(
            req, ["setup", "thesaurus", "--remove", "--lang", code], _("Remove"),
            icon_name="trash-2", kind="flat destructive", next_=back,
        )  # fmt: skip
        choose = (
            chip(_("In use"), kind="accent")
            if item.get("active")
            else words_form(req, ["setup", "thesaurus", "--lang", code], _("Use"), next_=back)
        )
        name = str(item.get("name") or code)
        rows.append(row(name, subtitle=code, suffix=h(t"{choose}{remove}")))
    offered = req.run("setup", "thesaurus", "--available")
    choices = [
        (str(o.get("language")), f"{o.get('language')} · {o.get('name')}")
        for o in as_list(offered.data.get("available"))
        if isinstance(o, dict) and o.get("language") not in installed
    ]
    if choices:
        download = h(
            t'<form method="post" action="/settings/thesaurus/download" class="action-row">'
            t"{csrf(req)}{select('lang', choices, 'en', label=_('Language'))}"
            t"{button(_('Download and use'), icon_name='download', kind='suggested')}</form>"
        )
        rows.append(form_row(_("Add a language"), download))
    return group(
        _("Thesaurus"),
        h(t"{_progress(req)}{boxed_list(rows)}"),
        description=_(
            "Searches also find synonyms from WordNet in the language in use. "
            "English is about 110 MB once downloaded."
        ),
        id_="thesaurus",
    )


def _progress(req: Request) -> Html:
    """A download's progress: shown while one runs, and kept current by app.js."""
    now = words.progress()
    say = {
        "download": _("Downloading {language}…"),
        "add": _("Adding {language} to the thesaurus…"),
        "failed": _("The download failed: {error}"),
        "size": _("{done} of {total} MB"),
    }
    data = {f"data-t-{key}": text for key, text in say.items()}
    text = ""
    if now is not None:
        stage = now.stage if now.stage in say else "download"
        text = say[stage].format(language=now.language, error=now.error)
    state = json.dumps(now.to_data() if now is not None else None)
    extra = join(h(t' {k}="{v}"') for k, v in data.items())
    return h(
        t'<div class="card progress-card" id="thesaurus-progress" '
        t'data-url="/settings/thesaurus/progress" data-state="{state}"{extra}'
        t'{Html(" hidden") if now is None else Html("")} aria-live="polite">'
        t'<p class="progress-text">{text}</p><progress max="1"></progress></div>'
    )


def progress(req: Request) -> Response:
    """How far a thesaurus download is, for app.js (read directly: the download runs in a
    process of its own, and the app's commands wait for each other)."""
    now = words.progress()
    return Response.json(now.to_data() if now is not None else None)


def download(req: Request) -> Response:
    """Start `didact setup thesaurus --lang <code>` in a process of its own, then show its
    progress on the Settings page (one download at a time)."""
    code = req.field("lang").strip()
    offered = {c for c, _name in words.available()}
    running = words.progress()
    if code in offered and (running is None or running.stage == "failed"):
        words.starting(code)
        command = [
            sys.executable, "-c", "from didact.cli.main import main; raise SystemExit(main())",
            "setup", "thesaurus", "--lang", code,
        ]  # fmt: skip
        subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )  # fmt: skip
    return Response.redirect("/settings#thesaurus")


def _docs(req: Request) -> Html:
    status = req.run("docs", "status")
    state = str(status.data.get("state") or "missing")
    said = {
        "current": _("Up to date"),
        "stale": _("Older than the code: opening them rebuilds them"),
        "missing": _("Not built yet: opening them builds them (a few seconds)"),
    }[state]
    rebuild = words_form(
        req, ["docs", "build", "--force"], _("Rebuild"), icon_name="refresh-cw",
        next_="/settings#docs",
    )  # fmt: skip
    actions = h(t"{link_button('/docs/', _('Open'), icon_name='code', kind='suggested')}{rebuild}")
    return group(
        _("Code documentation"),
        boxed_list([row(said, prefix=chip(state), suffix=actions)]),
        description=_("Every module's documentation, from its docstrings and types."),
        id_="docs",
    )


# ---------------------------------------------------------------------------- the docs


DOCS_POLICY = (  # pdoc's pages carry their own styles and scripts
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; object-src 'none'; base-uri 'none'; "
    "form-action 'self'; frame-ancestors 'none'"
)


def docs(req: Request) -> Response:
    """The API documentation's files, built first when the code changed."""
    built = req.run("docs", "build")
    if not built.ok:
        return page(req, _("Code documentation"), failure(built), nav="settings", status=500)
    root = Path(str(built.data.get("path"))).resolve()
    wanted = req.params.get("path", "") or "index.html"
    target = (root / wanted).resolve()
    if target.is_dir():
        target = target / "index.html"
    if not target.is_relative_to(root) or not target.is_file():
        return Response.text(_("That page isn't in the documentation."), 404)
    kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    if kind.startswith("text/") or kind in ("application/javascript",):
        kind += "; charset=utf-8"
    response = Response(target.read_bytes(), 200, kind)
    response.headers.append(("Content-Security-Policy", DOCS_POLICY))
    return response
