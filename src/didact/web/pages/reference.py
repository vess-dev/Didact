"""Reference and play: search everything, run the enabled packs' rules from forms, roll their
tables, and read their rules text, glossary and guides."""

from dataclasses import dataclass
from urllib.parse import quote

from didact.core import i18n
from didact.core.errors import DidactError
from didact.core.i18n import _, ngettext, pgettext
from didact.core.output import JSON
from didact.web.app import Request, Response
from didact.web.forms import rule_fields, rule_params
from didact.web.html import (
    Html,
    boxed_list,
    button,
    chip,
    command_url,
    entry,
    expander,
    form_row,
    group,
    h,
    hidden,
    link_button,
    record_url,
    row,
    status_page,
    switch,
    switch_row,
)
from didact.web.layout import failure, page, result_panel, run_form, words_form
from didact.web.markdown import inline, markdown
from didact.web.pages.common import as_dict, as_list, record_index, records_datalist

RULE_KINDS = ("check", "action", "procedure", "trigger")


def _rule_kind(kind: str) -> str:
    """A kind of rule, as a heading."""
    labels = {
        "check": _("Checks"),
        "action": _("Actions"),
        "procedure": _("Procedures"),
        "trigger": _("Triggers"),
    }
    return labels.get(kind, f"{kind.capitalize()}s")


def _source_label(source: str) -> str:
    """Where a search hit came from, as a badge."""
    labels = {
        "rules": pgettext("search source", "rules"),
        "terms": pgettext("search source", "terms"),
        "mechanics": pgettext("search source", "mechanics"),
        "tables": pgettext("search source", "tables"),
        "compendium": pgettext("search source", "compendium"),
        "records": pgettext("search source", "records"),
        "transcript": pgettext("search source", "transcript"),
        "docs": pgettext("search source", "docs"),
    }
    return labels.get(source, source)


def rule_url(rule_id: str) -> str:
    return "/rules/" + quote(rule_id, safe="")


def table_url(table_id: str) -> str:
    return "/tables/" + quote(table_id, safe="")


def section_url(section_id: str) -> str:
    return "/reference/" + quote(section_id, safe="")


def guide_url(topic: str) -> str:
    return "/guide/" + quote(topic, safe="")


@dataclass(frozen=True, slots=True)
class Texts:
    """The enabled packs' rules text and glossary (read through the services)."""

    sections: list[tuple[str, str, str, str]]  # (id, pack, title, body)
    terms: list[tuple[str, str, str]]  # (term, pack, definition)


def pack_texts(req: Request) -> Texts:
    from didact.services import packs, reference

    try:
        with req.app.repo() as repo:
            active = packs.active(repo)
            sections = [(s.qualified, s.pack, s.title, s.body) for s in reference.sections(active)]
            terms = [(term.term, term.pack, term.definition) for term in reference.terms(active)]
    except DidactError:
        return Texts([], [])
    return Texts(sections, terms)


# ---------------------------------------------------------------------------- the page


def index(req: Request) -> Response:
    flash = req.take_flash()
    texts = pack_texts(req)
    parts: list[Html | None] = [
        result_panel(req, flash.ran) if flash else None,
        _search_box(req.arg("q")),
        h(t'<div id="{RESULTS}" aria-live="polite"></div>'),  # live results, as you type
        _rules(req),
        _tables(req),
        _rules_text(req, req.arg("lookup").strip(), texts),
        _glossary(req, texts),
        _guides(req),
    ]
    return page(req, _("Reference"), h(t"{parts}"), nav="reference")


RESULTS = "search-results"  # where the search page's results go, and live ones as you type


def _search_box(query: str) -> Html:
    box = entry(
        "q",
        query,
        type_="search",
        placeholder=_("Search rules, tables, records, docs…"),
        label=_("Search everything"),
        attrs={"data-live": RESULTS},
    )
    go = button(_("Search"), icon_name="search", kind="suggested")
    return h(
        t'<form class="toolbar search-bar" method="get" action="/search" role="search">{box}{go}'
        t"</form>"
    )


def _rules(req: Request) -> Html:
    listed = req.run("rules", "list")
    by_kind: dict[str, list[Html]] = {}
    for item in as_list(listed.data.get("rules")):
        rule = as_dict(item)
        rule_id = str(rule.get("id", ""))
        by_kind.setdefault(str(rule.get("kind", "rule")), []).append(
            row(
                str(rule.get("title") or rule_id),
                subtitle=h(t"<code>{rule.get('usage') or rule_id}</code>"),
                href=rule_url(rule_id),
            )
        )
    if not by_kind:
        none = h(t'<p class="dim">{_("No rules in the enabled packs.")}</p>')
        return group(_("Rules"), none if listed.ok else failure(listed))
    kinds = sorted(
        by_kind.items(),
        key=lambda item: (RULE_KINDS.index(item[0]) if item[0] in RULE_KINDS else 9, item[0]),
    )
    sections = [
        expander(_rule_kind(kind), boxed_list(rows), count=len(rows)) for kind, rows in kinds
    ]
    return group(
        _("Rules"),
        h(t'<div class="stack">{sections}</div>'),
        description=_("The enabled packs' checks, actions, procedures and triggers: open one."),
    )


def _tables(req: Request) -> Html:
    listed = req.run("table", "list")
    by_pack: dict[str, list[Html]] = {}
    for item in as_list(listed.data.get("tables")):
        table = as_dict(item)
        table_id = str(table.get("id", ""))
        roll = words_form(
            req, ["table", "roll", table_id], _("Roll"), icon_name="hexagon", panel=True
        )
        entries = link_button(
            table_url(table_id), "", icon_name="list", title=_("Its entries"), kind="flat circular"
        )
        about = str(table.get("description") or "")
        meta = f"{table_id} · {table.get('dice') or ''}"
        said = h(t'{inline(about)}<span class="row-meta">{meta}</span>') if about else meta
        by_pack.setdefault(table_id.partition(".")[0], []).append(
            row(str(table.get("title") or table_id), subtitle=said, suffix=h(t"{entries}{roll}"))
        )
    if not by_pack:
        return group(_("Tables"), h(t'<p class="dim">{_("No tables in the enabled packs.")}</p>'))
    sections = [
        expander(pack, boxed_list(rows), count=len(rows)) for pack, rows in sorted(by_pack.items())
    ]
    return group(_("Tables"), h(t'<div class="stack">{sections}</div>'), id_="tables")


def _rules_text(req: Request, words: str, texts: Texts) -> Html:
    box = entry(
        "lookup",
        words,
        type_="search",
        placeholder=_("Look a rule up, e.g. damage"),
        label=_("Look a rule up"),
    )
    form = h(
        t'<form class="toolbar" method="get" action="/reference#rules-text">{box}'
        t"{button(_('Look up'), icon_name='search')}</form>"
    )
    found = None
    if words:
        looked = req.run("rules", "lookup", *words.split())
        shown = markdown(looked.md) if looked.ok else failure(looked)
        found = h(t'<div class="card">{shown}</div>')
    by_pack: dict[str, list[Html]] = {}
    for section_id, pack, title, _body in texts.sections:
        by_pack.setdefault(pack, []).append(
            row(title, subtitle=section_id, href=section_url(section_id))
        )
    sections = [
        expander(_("{pack}: every section", pack=pack), boxed_list(rows), count=len(rows))
        for pack, rows in sorted(by_pack.items())
    ]
    body = h(t'{form}{found}<div class="stack">{sections}</div>')
    return group(_("Rules text"), body, id_="rules-text")


def _glossary(req: Request, texts: Texts) -> Html:
    if not texts.terms:
        none = h(t'<p class="dim">{_("No glossary in the enabled packs.")}</p>')
        return group(_("Glossary"), none, id_="glossary")
    term = entry("w", placeholder=_("a term, e.g. fatigue"), label=_("Term"), required=True)
    define = run_form(
        req,
        h(t"{term}{button(_('Define'), icon_name='book')}"),
        fields={"action": "words", "w": "define"},
        panel=True,
        cls="action-row",
    )
    items = [
        h(
            t'<div class="term" data-filter-item="{term} {definition}"><dt>{term} '
            t'<span class="dim small">{pack}</span></dt><dd>{inline(definition)}</dd></div>'
        )
        for term, pack, definition in sorted(texts.terms, key=lambda t_: t_[0].casefold())
    ]
    box = entry(
        "",
        type_="search",
        placeholder=_("Filter terms"),
        label=_("Filter terms"),
        attrs={"data-filter": "glossary-terms"},
    )
    body = h(
        t'<div class="toolbar">{box}</div><dl class="glossary" id="glossary-terms">{items}</dl>'
    )
    every = expander(_("All terms"), body, count=len(items))
    return group(
        _("Glossary"),
        h(t"{boxed_list([form_row(_('Define'), define)])}{every}"),
        id_="glossary",
    )


def _in_language() -> list[str]:
    """`--lang` for `didact guide`, when the app speaks something other than English."""
    speaking = i18n.current()
    return [] if speaking.code == i18n.DEFAULT else ["--lang", speaking.tag]


def _guides(req: Request) -> Html:
    topics = as_dict(req.run("guide", *_in_language()).data.get("topics"))
    rows = [
        row(
            topic,
            subtitle=inline(str(summary)) if summary else _("how to run this pack"),
            href=guide_url(topic),
        )
        for topic, summary in topics.items()
    ]
    return group(_("Guides"), boxed_list(rows, empty=_("No guides.")), id_="guides")


# ---------------------------------------------------------------------------- search


def search(req: Request) -> Response:
    flash = req.take_flash()
    query = req.arg("q").strip()
    parts: list[Html | None] = []
    if not query:
        about = _(
            "Rules, terms, tables, the compendium, records, the transcript and Didact's docs."
        )
        parts.append(status_page("search", _("Search everything"), about))
    else:
        found = req.run("search", *query.split(), "--limit", "40", gm=True)
        if not found.ok:
            parts.append(failure(found))
        else:
            rows = [_hit(req, as_dict(hit)) for hit in as_list(found.data.get("hits"))]
            parts.append(boxed_list(rows, empty=_("Nothing matches {query}.", query=repr(query))))
            hidden_count = found.data.get("hidden")
            if isinstance(hidden_count, int) and hidden_count:
                said = ngettext(
                    "{n} secret matches hidden: the GM view shows them.",
                    "{n} secret matches hidden: the GM view shows them.",
                    hidden_count,
                )
                parts.append(h(t'<p class="dim small note">{said}</p>'))
    head = [result_panel(req, flash.ran) if flash else None, _search_box(query)]
    body = h(t'{head}<div id="{RESULTS}" aria-live="polite">{parts}</div>')
    return page(req, _("Search"), body, nav="reference", subtitle=query or None)


def hit_page(source: str, hit_id: str) -> str | None:
    """Where a search hit has a page of its own."""
    kind, _sep, rest = hit_id.partition(":")
    match source:
        case "records":
            return record_url(hit_id)
        case "mechanics":
            return rule_url(hit_id)
        case "rules":
            return section_url(hit_id)
        case "tables":
            return table_url(hit_id)
        case "docs" if kind == "command" and rest:
            return command_url(rest)
        case "docs" if kind == "guide" and rest:
            return guide_url(rest)
        case _:
            return None


def _hit(req: Request, hit: dict[str, JSON]) -> Html:
    source = str(hit.get("source", ""))
    hit_id = str(hit.get("id", ""))
    title = str(hit.get("title", hit_id))
    snippet = str(hit.get("snippet") or "")
    next_ = str(hit.get("next") or "")
    badge = chip(_source_label(source), kind="dim")
    target = hit_page(source, hit_id)
    if target:
        return row(title, subtitle=snippet, href=target, prefix=badge)
    line = next_.removeprefix("didact ").strip()
    show = None
    if line:
        show = run_form(
            req,
            h(t"{hidden('line', line)}{button(_('Show'), icon_name='play', title=next_)}"),
            fields={"action": "line"},
            panel=True,
            cls="inline",
        )
    subtitle = h(t'{snippet} <code class="dim">{next_}</code>')
    return row(title, subtitle=subtitle, prefix=badge, suffix=show)


# ---------------------------------------------------------------------------- one of each


def rule(req: Request) -> Response:
    rule_id = req.params["rule"]
    flash = req.take_flash()
    shown = req.run("rules", "show", rule_id)
    if not shown.ok:
        return page(req, rule_id, failure(shown), nav="reference", back="/reference", status=404)
    full_id = str(shown.data.get("id") or rule_id)
    params = rule_params(full_id, as_dict(shown.data.get("data")))
    values = flash.values if flash is not None else {}
    found = record_index(req)
    dry = switch_row(_("Dry run: roll, but keep nothing"), switch("dry_run"))
    run = button(_("Run"), kind="suggested pill", icon_name="play")
    form = run_form(
        req,
        h(
            t"{hidden('rule', full_id)}{rule_fields(params, values, records='records')}"
            t'{records_datalist(found)}<div class="switches">{dry}</div>'
            t'<div class="button-row">{run}</div>'
        ),
        fields={"action": "do"},
        panel=True,
        cls="card stack",
    )
    about = h(t'<div class="card">{markdown(shown.md)}</div>')
    body = h(
        t"{result_panel(req, flash.ran) if flash else None}{group(_('Run it'), form)}"
        t"{group(_('What it does'), about)}"
    )
    title = str(shown.data.get("title") or full_id)
    return page(req, title, body, nav="reference", back="/reference", subtitle=full_id)


def table(req: Request) -> Response:
    table_id = req.params["table"]
    flash = req.take_flash()
    shown = req.run("table", "show", table_id)
    if not shown.ok:
        return page(req, table_id, failure(shown), nav="reference", back="/reference", status=404)
    full_id = str(shown.data.get("id") or table_id)
    roll = words_form(
        req,
        ["table", "roll", full_id],
        _("Roll"),
        icon_name="hexagon",
        kind="suggested",
        panel=True,
    )
    body = h(
        t"{result_panel(req, flash.ran) if flash else None}"
        t'<div class="button-row">{roll}</div><div class="card">{markdown(shown.md)}</div>'
    )
    title = str(shown.data.get("title") or full_id)
    return page(req, title, body, nav="reference", back="/reference#tables", subtitle=full_id)


def section(req: Request) -> Response:
    wanted = req.params["section"]
    for section_id, pack, title, text in pack_texts(req).sections:
        if section_id == wanted:
            body = h(t'<div class="card">{markdown(text)}</div>')
            subtitle = f"{pack} · {section_id}"
            back = "/reference#rules-text"
            return page(req, title, body, nav="reference", back=back, subtitle=subtitle)
    missing = status_page(
        "bookmark", _("No such section"), _("It may belong to a pack that isn't enabled here.")
    )
    return page(req, _("Not found"), missing, nav="reference", back="/reference", status=404)


def guide(req: Request) -> Response:
    topic = req.params["topic"]
    english = req.arg("english") == "1"
    shown = req.run("guide", topic, *([] if english else _in_language()))
    if not shown.ok:
        return page(req, topic, failure(shown), nav="reference", back="/reference", status=404)
    text = str(shown.data.get("text") or shown.md)
    note: Html | None = None
    if shown.data.get("language", "en") != "en" and shown.data.get("current") is False:
        older = _("This translation was made from an older version of the guide.")
        link = link_button(f"{guide_url(topic)}?english=1", _("Read the English"), kind="flat")
        note = h(t'<p class="dim small note">{older} {link}</p>')
    body = h(t'{note}<div class="card">{markdown(text)}</div>')
    return page(
        req, _("Guide: {topic}", topic=topic), body, nav="reference", back="/reference#guides"
    )
