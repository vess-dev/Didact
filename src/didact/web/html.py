"""Safe HTML from Python, and the small widgets every page is built from.

`h(t'<a href="{url}">{name}</a>')` escapes `url` and `name`. Values that are already `Html`
(what `h`, `icon`, `markdown`, … return) pass through untouched, lists and other iterables
are joined, and None or False render as nothing. Attributes are always double-quoted.
"""

import html
from collections.abc import Iterable, Mapping, Sequence
from string.templatelib import Template
from urllib.parse import quote, urlencode

from didact.web.static import asset_url


class Html(str):
    """Markup that is safe to send as is."""

    __slots__ = ()

    def __add__(self, other: str) -> Html:
        return Html(str.__add__(self, esc(other)))  # plain text added to markup is escaped


def esc(value: object) -> Html:
    return value if isinstance(value, Html) else Html(html.escape(str(value), quote=True))


def h(template: Template) -> Html:
    """Render a t-string as HTML, escaping every interpolated value that isn't `Html`."""
    parts: list[str] = []
    for part in template:
        if isinstance(part, str):
            parts.append(part)
            continue
        value = part.value
        match part.conversion:
            case "r":
                value = repr(value)
            case "s":
                value = str(value)
            case "a":
                value = ascii(value)
        if part.format_spec:
            value = format(value, part.format_spec)
        parts.append(_render(value))
    return Html("".join(parts))


def _render(value: object) -> str:
    if isinstance(value, Html):
        return value
    if value is None or value is False:
        return ""
    if isinstance(value, str):
        return html.escape(value, quote=True)
    if isinstance(value, Iterable):
        return "".join(_render(item) for item in value)
    return html.escape(str(value), quote=True)


def join(items: Iterable[object], sep: str = "") -> Html:
    """The items (escaped unless `Html`) joined by `sep`, which is markup."""
    return Html(sep.join(_render(item) for item in items))


# ---------------------------------------------------------------------------- urls


def url(path: str, **params: str | int | None) -> str:
    """A path with the query parameters that have a value."""
    given = {k.rstrip("_"): str(v) for k, v in params.items() if v not in (None, "")}
    return f"{path}?{urlencode(given)}" if given else path


def record_url(ref: str) -> str:
    return "/record/" + quote(ref, safe=":@")


def command_url(name: str) -> str:
    return "/commands/" + "/".join(quote(word, safe="") for word in name.split())


# ---------------------------------------------------------------------------- widgets


def icon(name: str, *, cls: str = "icon") -> Html:
    """A Feather icon from the sprite."""
    href = f"{asset_url('feather-sprite.svg')}#{name}"
    return h(t'<svg class="{cls}" aria-hidden="true"><use href="{href}"></use></svg>')


def button(
    label: str | Html,
    *,
    icon_name: str | None = None,
    kind: str = "",
    name: str | None = None,
    value: str | None = None,
    title: str | None = None,
    type_: str = "submit",
    attrs: Mapping[str, str] | None = None,
) -> Html:
    """A button: kind is "", "suggested", "destructive", "flat", "pill" or a mix."""
    pic = icon(icon_name) if icon_name else None
    text = h(t"<span>{label}</span>") if label else None
    named = {"aria-label": None if label else title}  # an icon-only button needs a name
    extra = _attrs(attrs, name=name, value=value, title=title, **named)
    cls = " ".join(["button", *(f"is-{k}" for k in kind.split())])
    return h(t'<button type="{type_}" class="{cls}"{extra}>{pic}{text}</button>')


def link_button(
    href: str,
    label: str | Html,
    *,
    icon_name: str | None = None,
    kind: str = "",
    title: str | None = None,
    attrs: Mapping[str, str] | None = None,
) -> Html:
    pic = icon(icon_name) if icon_name else None
    text = h(t"<span>{label}</span>") if label else None
    cls = " ".join(["button", *(f"is-{k}" for k in kind.split())])
    extra = _attrs(attrs, title=title, **{"aria-label": None if label else title})
    return h(t'<a class="{cls}" href="{href}"{extra}>{pic}{text}</a>')


def _attrs(given: Mapping[str, str] | None = None, /, **named: str | None) -> Html:
    items = {**{k: v for k, v in named.items() if v is not None}, **(given or {})}
    return join(h(t' {key}="{value}"') for key, value in items.items())


def hidden(name: str, value: str) -> Html:
    return h(t'<input type="hidden" name="{name}" value="{value}">')


def chip(
    text: str | Html, *, kind: str = "", href: str | None = None, icon_name: str | None = None
) -> Html:
    pic = icon(icon_name) if icon_name else None
    cls = " ".join(["chip", *(f"is-{k}" for k in kind.split())])
    if href:
        return h(t'<a class="{cls}" href="{href}">{pic}<span>{text}</span></a>')
    return h(t'<span class="{cls}">{pic}<span>{text}</span></span>')


def type_dot(color: int) -> Html:
    return h(t'<span class="dot c{color}" aria-hidden="true"></span>')


def row(
    title: str | Html,
    *,
    subtitle: str | Html | None = None,
    href: str | None = None,
    prefix: Html | None = None,
    suffix: Html | None = None,
    filter_text: str | None = None,
    cls: str = "",
) -> Html:
    """One row of a boxed list: an optional prefix, a title and subtitle, and a suffix."""
    sub = h(t'<span class="row-subtitle">{subtitle}</span>') if subtitle else None
    text = h(t'<span class="row-text"><span class="row-title">{title}</span>{sub}</span>')
    tail = h(t'<span class="row-suffix">{suffix}</span>') if suffix else None
    lead = h(t'<span class="row-prefix">{prefix}</span>') if prefix else None
    item = _attrs(**{"data-filter-item": filter_text}) if filter_text is not None else Html("")
    classes = f"row {cls}".strip()
    if href:
        arrow = icon("chevron-right", cls="icon row-arrow")
        return h(t'<a class="{classes} is-link" href="{href}"{item}>{lead}{text}{tail}{arrow}</a>')
    return h(t'<div class="{classes}"{item}>{lead}{text}{tail}</div>')


def form_row(title: str | Html, form: Html, *, subtitle: str | Html | None = None) -> Html:
    """A boxed-list row whose content is a small form (a title above it)."""
    sub = h(t'<span class="row-subtitle">{subtitle}</span>') if subtitle else None
    return h(
        t'<div class="row is-form"><div class="row-text"><span class="row-title">{title}</span>'
        t"{sub}</div>{form}</div>"
    )


def choice_row(
    title: str | Html,
    control: Html,
    *,
    about: str | Html | None = None,
    more: Html | None = None,
) -> Html:
    """A boxed-list row with a control beside its title and, across the row below, what the
    choice means (a long text wraps under both instead of squeezing beside the control), then
    `more` (what each value means, say)."""
    text = h(t'<p class="row-about">{about}</p>') if about else None
    extra = h(t'<div class="row-more">{more}</div>') if more else None
    return h(
        t'<div class="row is-choice"><div class="row-text"><span class="row-title">{title}</span>'
        t"</div>{control}{text}{extra}</div>"
    )


def boxed_list(rows: Iterable[Html], *, empty: str | None = None, cls: str = "") -> Html:
    items = list(rows)
    if not items:
        return h(t'<p class="dim empty">{empty}</p>') if empty else Html("")
    return h(t'<div class="boxed-list {cls}">{items}</div>')


def group(
    title: str | Html,
    body: Html,
    *,
    description: str | Html | None = None,
    suffix: Html | None = None,
    id_: str | None = None,
) -> Html:
    """A titled section (a libadwaita preferences group)."""
    about = h(t'<p class="group-description">{description}</p>') if description else None
    tail = h(t'<div class="group-suffix">{suffix}</div>') if suffix else None
    anchor = _attrs(id=id_)
    head = h(t'<div class="group-head"><div><h2>{title}</h2>{about}</div>{tail}</div>')
    return h(t'<section class="group"{anchor}>{head}{body}</section>')


def expander(
    summary: str | Html,
    body: Html,
    *,
    count: int | None = None,
    open_: bool = False,
    prefix: Html | None = None,
    cls: str = "",
    attrs: Mapping[str, str] | None = None,
) -> Html:
    """A collapsible section (`<details>`) with a count badge."""
    badge = h(t'<span class="count">{count}</span>') if count is not None else None
    flag = Html(" open") if open_ else Html("")
    extra = _attrs(attrs)
    chevron = icon("chevron-right", cls="icon chevron")
    return h(
        t'<details class="expander {cls}"{flag}{extra}><summary>{chevron}{prefix}'
        t'<span class="expander-title">{summary}</span>{badge}</summary>'
        t'<div class="expander-body">{body}</div></details>'
    )


def status_page(
    icon_name: str, title: str, description: str | Html = "", action: Html | None = None
) -> Html:
    """An empty state: a big icon, a title, a line of help and maybe a button."""
    pic = icon(icon_name, cls="icon status-icon")
    text = h(t'<p class="dim">{description}</p>') if description else None
    return h(t'<div class="status-page">{pic}<h2>{title}</h2>{text}{action}</div>')


# ---------------------------------------------------------------------------- form controls


def entry(
    name: str,
    value: str = "",
    *,
    placeholder: str = "",
    type_: str = "text",
    required: bool = False,
    list_: str | None = None,
    label: str | None = None,
    attrs: Mapping[str, str] | None = None,
    cls: str = "",
) -> Html:
    extra = _attrs(
        attrs,
        placeholder=placeholder or None,
        list=list_,
        required="required" if required else None,
        **{"aria-label": label},
    )
    classes = f"entry {cls}".strip()
    return h(t'<input class="{classes}" type="{type_}" name="{name}" value="{value}"{extra}>')


def textarea(
    name: str,
    value: str = "",
    *,
    rows: int = 3,
    placeholder: str = "",
    label: str | None = None,
    required: bool = False,
    cls: str = "",
) -> Html:
    extra = _attrs(
        placeholder=placeholder or None,
        required="required" if required else None,
        **{"aria-label": label},
    )
    classes = f"entry {cls}".strip()
    return h(t'<textarea class="{classes}" name="{name}" rows="{rows}"{extra}>{value}</textarea>')


def select(
    name: str,
    options: Sequence[tuple[str, str]],
    selected: str = "",
    *,
    label: str | None = None,
    required: bool = False,
) -> Html:
    items = [
        h(t'<option value="{value}"{_selected(value == selected)}>{text}</option>')
        for value, text in options
    ]
    extra = _attrs(required="required" if required else None, **{"aria-label": label})
    return h(t'<select class="entry" name="{name}"{extra}>{items}</select>')


def _selected(on: bool) -> Html:
    return Html(" selected") if on else Html("")


def switch(name: str, *, checked: bool = False, label: str | None = None) -> Html:
    """A GNOME-style switch (a checkbox underneath)."""
    flag = Html(" checked") if checked else Html("")
    extra = _attrs(**{"aria-label": label})
    return h(t'<input class="switch" type="checkbox" name="{name}" value="1"{flag}{extra}>')


def field(label: str | Html, control: Html, *, help_: str | Html | None = None) -> Html:
    """A labelled control, stacked."""
    about = h(t'<span class="field-help">{help_}</span>') if help_ else None
    return h(
        t'<label class="field"><span class="field-label">{label}</span>{control}{about}</label>'
    )


def switch_row(label: str | Html, control: Html, *, help_: str | Html | None = None) -> Html:
    """A labelled switch on one line."""
    about = h(t'<span class="field-help">{help_}</span>') if help_ else None
    return h(
        t'<label class="switch-row"><span class="row-text"><span>{label}</span>{about}</span>'
        t"{control}</label>"
    )


def datalist(id_: str, options: Iterable[tuple[str, str]]) -> Html:
    items = [h(t'<option value="{value}">{text}</option>') for value, text in options]
    return h(t'<datalist id="{id_}">{items}</datalist>')
