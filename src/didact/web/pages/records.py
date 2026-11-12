"""Records: the list (by type), the new-record form, and one record's page with its actions."""

import shlex

from didact.commands.registry import REGISTRY
from didact.core import labels
from didact.core.errors import DidactError, NotFoundError
from didact.core.i18n import _, ngettext, pgettext
from didact.core.output import JSON, flatten
from didact.web.app import Flash, Request, Response
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
    hidden,
    icon,
    join,
    link_button,
    record_url,
    row,
    select,
    status_page,
    switch,
    switch_row,
    textarea,
    type_dot,
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
from didact.web.markdown import inline, markdown
from didact.web.pages.common import (
    COMMON_TYPES,
    Index,
    as_dict,
    as_list,
    change_title,
    detail_label,
    field_label,
    knowledge_badge,
    record_index,
    records_datalist,
    secret_note,
    show_value,
    type_color,
    type_label,
)
from didact.web.pages.drafts import advance_button, start_group, start_links
from didact.web.safe import WAS_DETAILS, WAS_FIELDS, WAS_VALUES, StaleForm, flat_fields, snapshot

NUMERIC_KINDS = frozenset(
    {"int", "number", "stat", "resource", "uses", "pool", "counter", "track", "clock"}
)
LOOKS = "looks"  # the one detail the players see
SLOT_PARTS = ("used", "capacity", "free")  # how a slots field sums up


def delete_command() -> str:
    """`didact delete`, or `rm` where that is still its name."""
    return "delete" if "delete" in REGISTRY else "rm"


def _has_param(command: str, name: str) -> bool:
    spec = REGISTRY.get(command)
    return spec is not None and any(p.name == name for p in spec.params)


def gm_mark() -> Html:
    return h(t'<span class="gm-mark" title="{_("GM only")}">{icon("eye-off")}</span>')


# ---------------------------------------------------------------------------- the list


def index(req: Request) -> Response:
    choice = req.arg("scope", "all")
    archived = req.arg("archived") == "1"
    query = req.arg("q").strip()
    status = req.run("status").data
    active = {key: status.get(key) for key in ("world", "campaign")}
    scope = f"{choice}:{active[choice]}" if active.get(choice) else None
    found = record_index(req, scope=scope, archived=archived)
    if not found.ran.ok:
        return page(req, _("Records"), failure(found.ran), nav="records")
    wanted = query.casefold()
    records = [
        r
        for r in found.records
        if not wanted or any(wanted in text.casefold() for text in (r.name, r.id, r.type))
    ]
    refs = found.refs()
    by_type: dict[str, list[Html]] = {}
    for record in records:
        by_type.setdefault(record.type, []).append(
            row(
                record.name,
                subtitle=f"{record.id} · {record.scope}",
                href=record_url(refs[(record.id, record.scope)]),
                suffix=knowledge_badge(record.knowledge),
                filter_text=f"{record.name} {record.id} {record.type}",
            )
        )
    chips = [
        chip(
            label,
            href=url("/records", scope=None if key == "all" else key),
            kind=_on(key == choice),
        )
        for key, label in (("all", _("All")), ("world", _("World")), ("campaign", _("Campaign")))
        if key == "all" or active.get(key)
    ]
    chips.append(
        chip(
            _("Archived"),
            href=url(
                "/records",
                scope=None if choice == "all" else choice,
                archived=None if archived else "1",
            ),
            kind=_on(archived),
            icon_name="archive",
        )
    )
    keep = hidden("scope", choice) if choice != "all" else None
    box = entry(
        "q",
        query,
        type_="search",
        placeholder=_("Filter records"),
        label=_("Filter records"),
        attrs={"data-filter": "record-groups"},
    )
    new = link_button("/records/new", _("New record"), icon_name="plus", kind="suggested")
    toolbar = h(
        t'<div class="toolbar"><form class="filter" method="get" action="/records" role="search">'
        t'{keep}{box}</form><div class="chips">{chips}</div>{new}</div>'
    )
    sections = [
        expander(
            type_label(type_),
            boxed_list(rows),
            count=len(rows),
            prefix=type_dot(type_color(type_)),
            attrs={"data-filter-group": ""},
        )
        for type_, rows in sorted(by_type.items(), key=lambda item: type_label(item[0]))
    ]
    if not records:
        action = link_button(
            "/records/new", _("New record"), icon_name="plus", kind="suggested pill"
        )
        about = (
            _("Nothing matches that filter.")
            if query
            else _("Records are the people, places and things of the game.")
        )
        sections = [status_page("book", _("No records here"), about, action)]
    body = h(
        t"{toolbar}{start_links(req)}{secret_note(found.hidden)}"
        t'<div id="record-groups" class="stack">{sections}'
        t'</div><p class="dim empty filter-empty" hidden>{_("Nothing matches the filter.")}</p>'
    )
    shown = ngettext("{n} shown", "{n} shown", len(records))
    return page(req, _("Records"), body, nav="records", subtitle=shown)


def _on(active: bool) -> str:
    return "active" if active else ""


# ---------------------------------------------------------------------------- new record


def new_form(req: Request) -> Response:
    flash = req.take_flash()
    values = flash.values if flash is not None else {}
    panel = result_panel(req, flash.ran) if flash is not None else None
    found = record_index(req)
    types = sorted({*COMMON_TYPES, *(r.type for r in found.records)})
    status = req.run("status").data

    def value(name: str, default: str = "") -> str:
        given = values.get(name)
        return given[0] if given else default

    scopes = [("", _("the usual place for its type"))]
    for key in ("campaign", "world"):
        if status.get(key):
            label = (
                _("campaign {campaign}", campaign=status[key])
                if key == "campaign"
                else _("world {world}", world=status[key])
            )
            scopes.append((f"{key}:{status[key]}", label))
    scopes.append(("global", _("every world (global)")))
    type_options = join(h(t'<option value="{kind}">{type_label(kind)}</option>') for kind in types)
    kind = typed_entry(
        "type",
        "type",
        value("type", req.arg("type", "npc")),
        list_="types",
        required=True,
        placeholder="npc, loc, item…",
    )
    name = entry("name", value("name"), required=True, placeholder=_("e.g. Old Tom"))
    tags = entry("tags", value("tags"), placeholder=_("comma, separated"))
    text = textarea(
        "body",
        value("body"),
        rows=6,
        placeholder=_("Markdown. GM-only lines go under a ## Secrets heading."),
    )
    extra = textarea("fields", value("fields"), rows=3, placeholder=_("e.g. role=innkeeper"))
    where = select("scope", scopes, value("scope"))
    switches = [
        switch_row(
            _("Roll what the sheet rolls (--fill)"), switch("fill", checked=bool(value("fill")))
        ),
        switch_row(
            _("Secret: the players don't know it exists"),
            switch("secret", checked=bool(value("secret"))),
        )
        if req.gm
        else None,
        switch_row(
            _("Dry run: show what would change"), switch("dry_run", checked=bool(value("dry_run")))
        ),
    ]
    buttons = h(
        t'<div class="button-row">{button(_("Create"), kind="suggested pill", icon_name="plus")}'
        t"{link_button('/records', _('Cancel'), kind='flat')}</div>"
    )
    body = run_form(
        req,
        h(
            t'<div class="fields two">{field(_("Type"), kind, help_=accepts("type"))}'
            t"{field(_('Name'), name)}</div>"
            t'<datalist id="types">{type_options}</datalist>'
            t'<div class="fields">{field(_("Tags"), tags)}{field(_("Description"), text)}'
            t"{field(_('Fields'), extra, help_=_('key=value, one per line'))}"
            t"{field(_('Where it lives'), where)}</div>"
            t'<div class="switches">{switches}</div>{buttons}'
        ),
        fields={"action": "new"},
        next_="/records/new",
        next_ok="@record",
        panel=True,
        cls="card stack",
    )
    body = h(t"{panel}{body}{start_group(req)}")
    return page(req, _("New record"), body, nav="records", back="/records")


# ---------------------------------------------------------------------------- one record


def show(req: Request) -> Response:
    ref = req.params["ref"]
    flash = req.take_flash()
    shown = req.run("show", ref, gm=True)
    panel = _flash_panel(req, flash, ref)
    if not shown.ok:
        missing = isinstance(shown.error, NotFoundError)
        title = _("No such record") if missing else _("Can't show it")
        body = h(t"{panel}{failure(shown, title=title)}")
        return page(req, ref, body, nav="records", back="/records", status=404 if missing else 200)
    data = shown.data
    if data.get("hidden") is True:
        secret = status_page(
            "eye-off",
            _("This record is secret"),
            _("The players don't know about it yet. Turn on the GM view to see it."),
        )
        return page(req, _("Secret"), h(t"{panel}{secret}"), nav="records", back="/records")
    record_id = str(data.get("id", ref))
    name = str(data.get("name", record_id))
    type_ = str(data.get("type", record_id.partition(":")[0]))
    found = record_index(req)
    names = found.names
    stale = flash is not None and isinstance(flash.ran.error, StaleForm)
    typed = flash.values if flash is not None and stale else {}  # to merge with the new version
    body = h(
        t"{panel}{_head(req, ref, data, name, type_, typed)}{_problems(data)}{_hidden(data)}"
        t"{_sheet(req, ref, data, type_)}{_body(req, ref, data, typed)}{_details(req, ref, data)}"
        t"{_fields(req, ref, data)}{_contents(data, names)}{_links(req, ref, data, names, found)}"
        t"{_chronicle(data, names)}{_note(req, ref)}{_lore(data, names)}"
        t"{_history(req, record_id, names)}"
    )
    subtitle = f"{type_} · {data.get('scope', '')}"
    return page(req, name, body, nav="records", back="/records", subtitle=subtitle)


def _flash_panel(req: Request, flash: Flash | None, ref: str) -> Html | None:
    """The last action's outcome. A refused delete offers to remove the links as well."""
    if flash is None:
        return None
    panel = result_panel(req, flash.ran)
    command = delete_command()
    error = flash.ran.error
    refused = (
        flash.ran.argv[:1] == (command,)
        and error is not None
        and error.code == "conflict"
        and _has_param(command, "unlink")
    )
    if not refused:
        return panel
    form = words_form(
        req,
        delete_argv(ref, unlink=True),
        _("Delete"),
        icon_name="trash-2",
        kind="destructive",
        next_ok="/records",
        confirm=Confirm(
            _("Delete it and the links to it?"),
            _("The links other records have to it go too. The history can undo it."),
            _("Delete"),
        ),
    )
    again = guarded(
        f"{record_url(ref)}/delete?unlink=1",
        _("Delete and remove those links"),
        form,
        icon_name="trash-2",
        kind="destructive",
    )
    return h(t'{panel}<div class="button-row">{again}</div>')


def _head(
    req: Request,
    ref: str,
    data: dict[str, JSON],
    name: str,
    type_: str,
    typed: dict[str, list[str]],
) -> Html:
    archived = bool(data.get("archived"))
    record_id = str(data.get("id", ref))
    tags = [chip(str(tag), icon_name="tag") for tag in as_list(data.get("tags"))]
    aliases = ", ".join(str(a) for a in as_list(data.get("aliases")))
    also = (
        h(t'<p class="dim small">{_("also known as {aliases}", aliases=aliases)}</p>')
        if aliases
        else None
    )
    status = str(data.get("status", "active"))
    badges = [
        knowledge_badge(str(data.get("knowledge", "known"))),
        chip(_("archived"), kind="dim", icon_name="archive") if archived else None,
        chip(status, kind="dim") if status != "active" else None,
    ]
    graph = link_button(url("/graph", focus=record_id, depth="2"), _("Graph"), icon_name="share-2")
    toggle = words_form(
        req,
        ["restore" if archived else "archive", ref],
        _("Restore") if archived else _("Archive"),
        icon_name="archive",
    )
    delete_form = words_form(
        req,
        delete_argv(ref),
        _("Delete"),
        icon_name="trash-2",
        kind="destructive",
        next_ok="/records",
        confirm=Confirm(
            _("Delete {name}?", name=name),
            _("The history can undo it. If other records link to it, it stays until you say."),
            _("Delete"),
        ),
    )
    delete = guarded(
        f"{record_url(ref)}/delete",
        _("Delete…"),
        delete_form,
        icon_name="trash-2",
        kind="destructive",
    )
    kind_chip = chip(type_, icon_name="box")
    scope_chip = chip(str(data.get("scope", "")), icon_name="layers")
    return h(
        t'<section class="card record-head"><div class="record-title">{type_dot(type_color(type_))}'
        t"<h2>{name}</h2>{badges}</div>"
        t'<div class="chips">{kind_chip}{scope_chip}{tags}</div>{also}{_where(data)}'
        t'<div class="button-row">{advance_button(req, ref, type_)}{graph}{toggle}{delete}</div>'
        t"{_edit(req, ref, data, name, typed)}"
        t"</section>"
    )


def _where(data: dict[str, JSON]) -> Html | None:
    """Where it is: one breadcrumb per place it's held (`where` is a list of chains, nearest
    holder first; a single flat chain works too)."""
    raw = as_list(data.get("where"))
    chains = [as_list(c) for c in raw] if raw and isinstance(raw[0], list) else [raw]
    lines: list[Html] = []
    before, _sep, after = _("in {place}").partition("{place}")  # the links go in between
    for chain in chains:
        steps = [
            h(t'<a href="{record_url(str(s.get("id")))}">{s.get("name") or s.get("id")}</a>')
            for s in (as_dict(item) for item in chain)
        ]
        if steps:
            lines.append(
                h(
                    t'<p class="where">{icon("map-pin")}<span>{before}{join(steps, " › ")}'
                    t"{after}</span></p>"
                )
            )
    return join(lines, "") if lines else None


def _edit(
    req: Request, ref: str, data: dict[str, JSON], name: str, typed: dict[str, list[str]]
) -> Html:
    """The name, tags and aliases. After a refused save the form holds what was typed, and
    the `was.*` values are the new ones: saving again replaces them knowingly."""
    tags = ", ".join(str(tag) for tag in as_list(data.get("tags")))
    aliases = ", ".join(str(a) for a in as_list(data.get("aliases")))
    mine = {k: typed[k][0] for k in ("name", "tags", "aliases") if typed.get(k)}
    save = button(_("Save"), kind="suggested", icon_name="check")
    listed = _("comma, separated")
    also = entry("aliases", mine.get("aliases", aliases), placeholder=listed)
    form = run_form(
        req,
        h(
            t'<div class="fields">'
            t"{field(_('Name'), entry('name', mine.get('name', name), required=True))}"
            t"{field(_('Tags'), entry('tags', mine.get('tags', tags), placeholder=listed))}"
            t"{field(_('Also known as'), also)}"
            t"</div>{hidden('was.name', name)}{hidden('was.tags', tags)}"
            t"{hidden('was.aliases', aliases)}"
            t'<div class="button-row">{save}</div>'
        ),
        fields={"action": "edit", "ref": ref},
        cls="stack",
    )
    return expander(_("Edit name, tags and aliases"), form, open_=bool(mine), cls="is-plain")


def _problems(data: dict[str, JSON]) -> Html | None:
    found = as_list(data.get("problems"))
    if not found:
        return None
    items = [h(t"<li>{problem}</li>") for problem in found]
    return h(t'<section class="card warning">{icon("alert-triangle")}<ul>{items}</ul></section>')


def _hidden(data: dict[str, JSON]) -> Html | None:
    """What the player view left out (so the GM knows there's more)."""
    info = as_dict(data.get("hidden"))
    lines = info.get("lines")
    n_lines = lines if isinstance(lines, int) else 0
    n_fields = len(as_list(info.get("fields")))
    n_details = len(as_list(info.get("details")))
    parts = [
        ngettext("{n} secret line", "{n} secret lines", n_lines) if n_lines else None,
        ngettext("{n} secret field", "{n} secret fields", n_fields) if n_fields else None,
        ngettext("{n} GM detail", "{n} GM details", n_details) if n_details else None,
    ]
    things = ""
    for part in parts:
        if part:
            things = _("{first} and {second}", first=things, second=part) if things else part
    if not things:
        return None
    said = _("{things} hidden: the GM view shows them.", things=things)
    return h(t'<p class="dim small note">{icon("eye-off")}<span>{said}</span></p>')


def _sheet(req: Request, ref: str, data: dict[str, JSON], type_: str) -> Html | None:
    """The sheet's values as tiles; stored numbers get − and + buttons."""
    values = as_dict(data.get("values"))
    own = set(as_dict(data.get("fields")))
    shown = {k: v for k, v in values.items() if k.split(".")[0] not in own}
    numbers, labels, helps = _sheet_specs(req, type_, list(shown)) if shown else (set(), {}, {})
    tiles: list[Html] = []
    meant: list[Html] = []  # what each value shown means, as the sheet says
    done: set[str] = set()
    for key, value in shown.items():
        if key in done:
            continue
        base, _sep, part = key.rpartition(".")
        if part in SLOT_PARTS and f"{base}.capacity" in shown:  # slots: "used / capacity"
            done |= {base, *(f"{base}.{p}" for p in SLOT_PARTS)}
            used, capacity = shown.get(f"{base}.used"), shown.get(f"{base}.capacity")
            items = _value_text(shown.get(base)) if shown.get(base) else None
            label = field_label(base, labels)
            tiles.append(_tile(label, f"{used} / {capacity}", detail=items, about=helps.get(base)))
            if helps.get(base):
                meant.append(row(label, subtitle=inline(helps[base])))
            continue
        if value in ([], {}, None, ""):
            continue
        steps = None
        label = field_label(key, labels)
        if key in numbers:
            minus = _step_form(req, ref, key, "-=", "minus", f"{label} − 1")
            plus = _step_form(req, ref, key, "+=", "plus", f"{label} + 1")
            steps = h(t'<div class="tile-steps">{minus}{plus}</div>')
        tiles.append(_tile(label, _value_text(value), steps=steps, about=helps.get(key)))
        if helps.get(key):
            meant.append(row(label, subtitle=inline(helps[key])))
    if not tiles:
        return None
    explained = (
        expander(_("What each one means"), boxed_list(meant), cls="is-plain") if meant else None
    )
    change = run_form(
        req,
        h(
            t"{
                entry('assignment', placeholder=_('e.g. hp=4, hp-=2, weapon=d8'), label=_('Change'))
            }"
            t"{button(_('Change'), icon_name='check')}"
        ),
        fields={
            "action": "set",
            "ref": ref,
            WAS_VALUES: snapshot(values),
            WAS_FIELDS: snapshot(flat_fields(data)),
        },
        cls="action-row",
    )
    how = _("key=value, key+=n or key-=n")
    rows = [form_row(_("Change a value"), change, subtitle=how)]
    return group(_("Sheet"), h(t'<div class="tiles">{tiles}</div>{explained}{boxed_list(rows)}'))


def _tile(
    label: str,
    text: str,
    *,
    detail: str | None = None,
    steps: Html | None = None,
    about: str | None = None,
) -> Html:
    more = h(t'<span class="tile-detail">{detail}</span>') if detail else None
    said = h(t' title="{about}"') if about else None  # what it is, as the sheet says
    return h(
        t'<div class="tile"{said}><span class="tile-label">{label}</span>'
        t'<span class="tile-value">{text}</span>{more}{steps}</div>'
    )


def _step_form(req: Request, ref: str, key: str, op: str, pic: str, title: str) -> Html:
    return run_form(
        req,
        button("", icon_name=pic, title=title, kind="flat circular"),
        fields={"action": "set", "ref": ref, "key": key, "op": op, "value": "1"},
        cls="inline",
    )


def _sheet_specs(
    req: Request, type_: str, keys: list[str]
) -> tuple[set[str], dict[str, str], dict[str, str]]:
    """Which sheet values are stored numbers (so that −/+ can change them), and the labels
    and help the sheet gives its fields."""
    from didact.services import sheets

    numbers: set[str] = set()
    labels: dict[str, str] = {}
    helps: dict[str, str] = {}
    try:
        with req.app.repo() as repo:
            sheet = sheets.sheet(repo, type_)
            for key in keys:
                path = sheet.route(key)
                spec = sheet.spec_at(path) if path else None
                if spec is None:
                    continue
                if spec.stored and spec.kind in NUMERIC_KINDS:
                    numbers.add(key)
                if spec.opt("label"):
                    labels[key] = spec.label
                about = spec.opt("help")
                if isinstance(about, str) and about.strip():
                    helps[key] = about.strip()
    except DidactError:
        return set(), {}, {}
    return numbers, labels, helps


def _value_text(value: JSON) -> str:
    if isinstance(value, list):
        return ", ".join(_value_text(v) for v in value) or "—"
    if isinstance(value, dict):
        named = value.get("name")
        return str(named) if named is not None else show_value(value)
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return _("yes") if value else _("no")
    return str(value)


def _body(req: Request, ref: str, data: dict[str, JSON], typed: dict[str, list[str]]) -> Html:
    text = str(data.get("body") or "")
    mine = typed["body"][0] if typed.get("body") else None  # a refused save: merge, then save
    held_back = bool(as_dict(data.get("hidden")).get("lines"))
    if held_back and not req.gm:
        locked = _("Some of this text is for the GM only: turn on the GM view to edit it.")
        editor = h(t'<p class="dim small note">{icon("lock")}<span>{locked}</span></p>')
    else:
        save = button(_("Save"), kind="suggested", icon_name="check")
        unsaved = _(
            "Your version, not saved: the description above changed since you opened the page."
        )
        merge = (
            h(t'<p class="dim small note">{icon("git-merge")}<span>{unsaved}</span></p>')
            if mine is not None
            else None
        )
        box = textarea("body", text if mine is None else mine, rows=12, label=_("Description"))
        before, _sep, after = _(
            "Markdown. Lines under a {heading} heading are for the GM only."
        ).partition("{heading}")  # the heading goes in between, as code
        form = run_form(
            req,
            h(
                t"{merge}{box}{hidden('was.body', text)}"
                t'<p class="dim small">{before}<code>## Secrets</code>{after}</p>'
                t'<div class="button-row">{save}</div>'
            ),
            fields={"action": "edit", "ref": ref},
            cls="stack",
        )
        editor = expander(_("Edit the description"), form, open_=mine is not None, cls="is-plain")
    shown = markdown(text) if text.strip() else h(t'<p class="dim">{_("No description yet.")}</p>')
    return group(_("Description"), h(t'<div class="card">{shown}</div>{editor}'))


def _details(req: Request, ref: str, data: dict[str, JSON]) -> Html | None:
    """Named details (`didact about`): the players see looks, the GM sees them all."""
    details = as_dict(data.get("details"))
    suggested = [str(s) for s in as_list(data.get("suggested"))]
    editable = "about" in REGISTRY
    if not details and not suggested and not editable:
        return None
    clearable = _has_param("about", "clear")
    shown = snapshot(details)
    rows: list[Html] = []
    for name, text in details.items():
        label = detail_label(name)
        title = h(t"{gm_mark() if name != LOOKS else None}<span>{label}</span>")
        if not editable:
            rows.append(row(title, subtitle=str(text)))
            continue
        save = button(
            "", icon_name="check", title=_("Save {name}", name=label), kind="flat circular"
        )
        form = run_form(
            req,
            h(t"{entry('text', str(text), label=label)}{hidden('name', name)}{save}"),
            fields={"action": "about", "ref": ref, WAS_DETAILS: shown},
            cls="action-row",
        )
        clear = (
            words_form(
                req,
                ["about", ref, "--clear", name],
                "",
                icon_name="x",
                title=_("Remove {name}", name=label),
                kind="flat circular",
            )
            if clearable
            else None
        )
        rows.append(form_row(title, h(t"{form}{clear}")))
    if editable:
        wanted = req.arg("detail") or ("" if details or req.gm else LOOKS)
        name = typed_entry(
            "word", "name", wanted, placeholder=_("e.g. looks"), label=_("Name"), required=True
        )
        text = entry("text", placeholder=_("what it is"), label=_("Text"), required=True)
        add = run_form(
            req,
            h(t"{name}{text}{button(_('Add'), icon_name='plus')}"),
            fields={"action": "about", "ref": ref, WAS_DETAILS: shown},
            cls="action-row",
        )
        rows.append(form_row(_("Add a detail"), add, subtitle=accepts("word")))
    chips = [
        chip(
            detail_label(name),
            href=url(record_url(ref), detail=name) + "#details",
            icon_name="plus",
            kind="add",
        )
        for name in suggested
    ]
    open_ = h(t'<span class="dim small">{_("Not filled in yet:")}</span>{chips}') if chips else None
    about = (
        _("Looks are what the players see; the rest is for the GM.")
        if req.gm
        else _("What the players know it looks like.")
    )
    body = h(t'{boxed_list(rows)}<div class="chips">{open_}</div>')
    return group(_("Details"), body, description=about, id_="details")


def _fields(req: Request, ref: str, data: dict[str, JSON]) -> Html:
    rows: list[Html] = []
    shown = snapshot(flat_fields(data))
    held = "contents" in data  # the Contents section shows the inventory as a tree
    for key, value in flatten(as_dict(data.get("fields"))):
        if value == {} or value == []:
            continue
        if held and (key == "inventory" or key.startswith("inventory.")):
            continue
        label = field_label(key)
        form = run_form(
            req,
            h(
                t"{entry('value', show_value(value), label=label)}"
                t"{
                    button(
                        '',
                        icon_name='check',
                        title=_('Save {name}', name=label),
                        kind='flat circular',
                    )
                }"
            ),
            fields={"action": "set", "ref": ref, "key": key, WAS_FIELDS: shown},
            cls="action-row",
        )
        remove = run_form(
            req,
            button("", icon_name="x", title=_("Remove {name}", name=label), kind="flat circular"),
            fields={"action": "set", "ref": ref, "key": key, "unset": "1", WAS_FIELDS: shown},
            cls="inline",
        )
        rows.append(form_row(label, h(t"{form}{remove}")))
    key = typed_entry("key", "key", placeholder=_("name"), label=_("Field name"), required=True)
    add = run_form(
        req,
        h(
            t"{key}"
            t"{entry('value', placeholder=_('value'), label=_('Field value'))}"
            t"{button(_('Add'), icon_name='plus')}"
        ),
        fields={"action": "set", "ref": ref, WAS_FIELDS: shown},
        cls="action-row",
    )
    rows.append(form_row(_("Add a field"), add, subtitle=accepts("key")))
    return group(_("Fields"), boxed_list(rows), description=_("Open fields: any name, any value."))


def _contents(data: dict[str, JSON], names: dict[str, str]) -> Html | None:
    items = as_list(data.get("contents"))
    if not items:
        return None
    return group(
        pgettext("what a record holds: its inventory", "Contents"),
        h(t'<div class="card">{_tree(items, names)}</div>'),
    )


def _tree(items: list[JSON], names: dict[str, str]) -> Html:
    entries: list[Html] = []
    for raw in items:
        item = as_dict(raw)
        ref = item.get("ref")
        name = str(item.get("name") or (names.get(str(ref)) if ref else None) or ref or "?")
        count = item.get("count")
        times = (
            h(t' <span class="dim">×{count}</span>')
            if isinstance(count, int) and count != 1
            else None
        )
        label = (
            h(t'<a href="{record_url(str(ref))}">{name}</a>{times}') if ref else h(t"{name}{times}")
        )
        inner = as_list(item.get("contents"))
        if inner:
            nested = _tree(inner, names)
            entries.append(h(t"<li><details><summary>{label}</summary>{nested}</details></li>"))
        else:
            entries.append(h(t"<li>{label}</li>"))
    return h(t'<ul class="tree">{entries}</ul>')


def _links(
    req: Request, ref: str, data: dict[str, JSON], names: dict[str, str], found: Index
) -> Html:
    rows: list[Html] = []
    for item in as_list(data.get("links")):
        link = as_dict(item)
        rel, target = str(link.get("rel", "")), str(link.get("to", ""))
        bare = target.partition("@")[0]
        remove = words_form(
            req,
            ["link", ref, rel, target, "--remove"],
            "",
            icon_name="x",
            title=_("Remove the {rel} link", rel=rel),
            kind="flat circular",
        )
        rows.append(
            row(
                h(t'<a href="{record_url(target)}">{names.get(bare, bare)}</a>'),
                prefix=chip(rel, kind="rel"),
                subtitle=bare,
                suffix=remove,
            )
        )
    back: list[Html] = []
    for item in as_list(data.get("backlinks")):
        link = as_dict(item)
        source = str(link.get("id", ""))
        back.append(
            row(
                names.get(source, source),
                prefix=chip(str(link.get("rel", "")), kind="rel"),
                subtitle=_("{record} links here", record=source),
                href=record_url(source),
            )
        )
    add = run_form(
        req,
        h(
            t"{
                entry('w', placeholder=_('relation, e.g. ally'), label=_('Relation'), required=True)
            }"
            t"{
                entry(
                    'w',
                    placeholder=_('record'),
                    list_='records',
                    label=_('Links to'),
                    required=True,
                )
            }"
            t"{button(_('Link'), icon_name='link')}{records_datalist(found)}"
        ),
        fields={"action": "words", "w": ["link", ref]},
        cls="action-row",
    )
    rows.append(form_row(_("Add a link"), add))
    body = boxed_list(rows)
    if back:
        body = h(t'{body}<h3 class="subhead">{_("Linked from")}</h3>{boxed_list(back)}')
    return group(_("Links"), body, id_="links")


def _chronicle(data: dict[str, JSON], names: dict[str, str]) -> Html | None:
    """The journal beats about this record, as a timeline."""
    beats = [as_dict(b) for b in as_list(data.get("chronicle"))]
    if not beats:
        return None
    items: list[Html] = []
    for beat in beats:
        where = str(beat.get("id") or "")
        session, scene = beat.get("session"), beat.get("scene")
        if not where and session:
            where = f"S{session}" + (f".{scene}" if scene else "")
        others = [
            h(t'<a href="{record_url(str(other))}">{names.get(str(other), str(other))}</a>')
            for other in as_list(beat.get("about"))
        ]
        with_ = h(t'<span class="dim small"> · {join(others, ", ")}</span>') if others else None
        importance = beat.get("importance")
        marks = [
            gm_mark() if beat.get("secret") else None,
            icon("star", cls="icon important")
            if isinstance(importance, int) and importance >= 7
            else None,
        ]
        kind = labels.beat_name(str(beat.get("kind") or ""))
        items.append(
            h(
                t'<li class="beat"><span class="beat-where">{where}</span><div class="beat-text">'
                t'{marks}<span class="beat-kind">{kind}</span> '
                t"{beat.get('text') or ''}{with_}</div></li>"
            )
        )
    return group(_("Chronicle"), h(t'<ol class="timeline card">{items}</ol>'))


def _note(req: Request, ref: str) -> Html:
    form = run_form(
        req,
        h(
            t"{
                entry(
                    'w', placeholder=_('e.g. Agreed to guide them'), label=_('Note'), required=True
                )
            }"
            t"{button(_('Add note'), icon_name='edit-3')}"
        ),
        fields={"action": "words", "w": ["note", ref]},
        cls="action-row",
    )
    return group(_("Notes"), boxed_list([form_row(_("Add a dated note"), form)]))


def _lore(data: dict[str, JSON], names: dict[str, str]) -> Html | None:
    ids = [str(i) for i in as_list(data.get("lore"))]
    if not ids:
        return None
    chips = [chip(names.get(i, i), href=record_url(i), icon_name="bookmark") for i in ids]
    return group(_("Lore it brings up"), h(t'<div class="chips">{chips}</div>'))


def _history(req: Request, record_id: str, names: dict[str, str]) -> Html:
    history = req.run("history", record_id, "--limit", "10")
    rows: list[Html] = []
    for item in as_list(history.data.get("events")):
        event = as_dict(item)
        when = str(event.get("ts", ""))[:16].replace("T", " ")
        undone = chip(_("undone"), kind="dim") if event.get("undone") else None
        subtitle = f"#e{event.get('seq')} · {when}"
        rows.append(row(change_title(req, event, names), subtitle=subtitle, suffix=undone))
    return group(_("History"), boxed_list(rows, empty=_("No changes yet.")))


# ---------------------------------------------------------------------------- delete, without JS


def delete_argv(ref: str, *, unlink: bool = False) -> list[str]:
    """The delete command for a record; with `unlink`, also for the links to it."""
    command = delete_command()
    if not unlink or not _has_param(command, "unlink"):
        return [command, ref]
    return [command, ref, "--unlink", *(["--yes"] if _has_param(command, "yes") else [])]


def confirm_delete(req: Request) -> Response:
    """Deleting without JS: ask first, on a page of its own."""
    ref = req.params["ref"]
    unlink = req.arg("unlink") == "1"
    shown = req.run("show", ref, gm=True)
    name = str(shown.data.get("name") or ref)
    argv = delete_argv(ref, unlink=unlink)
    form = words_form(
        req,
        argv,
        _("Delete"),
        icon_name="trash-2",
        kind="destructive pill",
        next_=record_url(ref),
        next_ok="/records",
    )
    cancel = link_button(record_url(ref), _("Cancel"), kind="pill")
    about = (
        _("The links other records have to it go too. The history can undo it.")
        if unlink
        else _(
            "The history can undo it. If other records link to it, Didact says so and "
            "offers to remove those links too."
        )
    )
    question = _("Delete {name}?", name=name)
    body = h(
        t'<section class="card dialog-page"><h2>{question}</h2><p class="dim">{about}</p>'
        t"{command_line(shlex.join(['didact', *argv]))}"
        t'<div class="button-row">{cancel}{form}</div></section>'
    )
    return page(req, _("Delete"), body, nav="records", back=record_url(ref))
