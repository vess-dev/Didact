"""Every command as a form, and a command-line box: the whole CLI, point and click."""

from urllib.parse import unquote

from didact.commands.registry import REGISTRY, CommandSpec
from didact.core.i18n import _, ngettext, pgettext, translate
from didact.core.output import JSON
from didact.web.app import Request, Response
from didact.web.forms import TIMES, command_fields, offered, value_name
from didact.web.html import (
    Html,
    boxed_list,
    button,
    chip,
    command_url,
    datalist,
    entry,
    expander,
    group,
    h,
    hidden,
    row,
    status_page,
    url,
)
from didact.web.layout import page, result_panel, run_form
from didact.web.markdown import markdown
from didact.web.pages.common import as_dict, as_list, record_index


def line_box(req: Request, line: str = "", *, next_: str | None = None) -> Html:
    box = entry(
        "line",
        line,
        placeholder="roll 2d6   ·   show sweeney   ·   help set",
        label=_("A didact command"),
        required=True,
        attrs={"autocomplete": "off", "spellcheck": "false", "autocapitalize": "off"},
    )
    run = button(_("Run"), kind="suggested", icon_name="corner-down-left")
    return run_form(
        req,
        h(t'<span class="prompt">didact</span>{box}{run}'),
        fields={"action": "line"},
        next_=next_ or "/commands",
        panel=True,
        cls="command-box",
    )


def index(req: Request) -> Response:
    flash = req.take_flash()
    panel = result_panel(req, flash.ran) if flash else None
    typed = flash.values.get("line", [""])[0] if flash else req.arg("line")
    groups: dict[str, list[CommandSpec]] = {}
    for spec in sorted(REGISTRY.values(), key=lambda s: s.name):
        groups.setdefault(spec.words[0], []).append(spec)
    alone = [specs[0] for word, specs in groups.items() if [s.name for s in specs] == [word]]
    sections = [
        expander(
            word,
            boxed_list(_row(spec) for spec in specs),
            count=len(specs),
            attrs={"data-filter-group": ""},
        )
        for word, specs in groups.items()
        if [s.name for s in specs] != [word]
    ]
    first = expander(
        _("Commands"),
        boxed_list(_row(spec) for spec in alone),
        count=len(alone),
        attrs={"data-filter-group": ""},
    )
    box = entry(
        "",
        type_="search",
        placeholder=_("Filter commands"),
        label=_("Filter commands"),
        attrs={"data-filter": "command-list"},
    )
    about = _("Any command, as you'd type it in a terminal (without the word didact).")
    body = h(
        t"{panel}{group(_('Command line'), line_box(req, typed), description=about)}"
        t'<div class="toolbar">{box}</div><div id="command-list" class="stack">{first}{sections}'
        t'</div><p class="dim empty filter-empty" hidden>{_("No command matches.")}</p>'
    )
    count = ngettext("{n} command", "{n} commands", len(REGISTRY))
    return page(req, _("Commands"), body, nav="commands", subtitle=count)


def _row(spec: CommandSpec) -> Html:
    return row(
        spec.name,
        subtitle=translate(spec.summary),
        href=command_url(spec.name),
        suffix=chip(_("writes"), kind="dim") if spec.writes else None,
        filter_text=f"{spec.name} {spec.summary} {translate(spec.summary)}",
    )


def form(req: Request) -> Response:
    name = " ".join(unquote(part) for part in req.params["name"].split("/") if part)
    spec = REGISTRY.get(name)
    if spec is None:
        missing = status_page(
            "terminal", _("No such command"), _("There is no didact {name}.", name=name)
        )
        return page(req, name, missing, nav="commands", back="/commands", status=404)
    flash = req.take_flash()
    values = flash.values if flash is not None else _prefill(req, spec)
    go = button(_("Run"), kind="suggested pill", icon_name="play")
    lists, offers, units = _offers(req, spec)
    fields = command_fields(spec, values, gm=req.gm, lists=lists, units=units)
    run = run_form(
        req,
        h(t'{hidden("cmd", spec.name)}{fields}{offers}<div class="button-row">{go}</div>'),
        fields={"action": "command"},
        next_=command_url(spec.name),
        panel=True,
        cls="card stack",
    )
    examples = [
        row(h(t"<code>{example}</code>"), href=url("/commands", line=_example_line(example)))
        for example in spec.examples
        if "\n" not in example
    ]
    usage = h(t'<p><code class="usage">{spec.usage()}</code></p>')
    about = h(t'<div class="card">{usage}{markdown(translate(spec.description))}</div>')
    shown = group(
        _("Examples"), boxed_list(examples), description=_("Open one in the command line.")
    )
    parts: list[Html | None] = [
        result_panel(req, flash.ran) if flash else None,
        group(_("Run it"), run),
        group(pgettext("a command's page: its usage and description", "About"), about),
        shown if examples else None,
    ]
    subtitle = _("changes the library (undoable)") if spec.writes else _("reads only")
    title = f"didact {spec.name}"
    return page(req, title, h(t"{parts}"), nav="commands", back="/commands", subtitle=subtitle)


def _offers(req: Request, spec: CommandSpec) -> tuple[dict[str, str], Html, list[str]]:
    """What a command's form can offer to choose from (`forms.OFFERED`): the records, drafts,
    packs, save points, oracles, tables, rules and creations here, as datalists (as this view
    may name them); and the calendar's units, when it takes an amount of game time."""
    wanted = offered(spec)
    lists: dict[str, str] = {}
    markup: list[Html] = []

    def add(name: str, options: list[tuple[str, str]]) -> None:
        lists[name] = f"offer-{name}"
        markup.append(datalist(f"offer-{name}", options))

    def listed(argv: list[str], key: str) -> list[dict[str, JSON]]:
        return [as_dict(item) for item in as_list(req.run(*argv).data.get(key))]

    def titled(items: list[dict[str, JSON]], key: str = "id") -> list[tuple[str, str]]:
        return [(str(i.get(key)), str(i.get("title") or i.get(key))) for i in items]

    if "records" in wanted:
        add("records", [(r.id, f"{r.name} ({r.type})") for r in record_index(req).records])
    if "drafts" in wanted:  # a generator's draft is the GM's: the player view names its source
        drafts = listed(["gen", "drafts"], "items")
        add("drafts", [
            (str(d.get("id")), str(
                (d.get("name") if req.gm or d.get("kind") == "chargen" else None)
                or d.get("source")
            ))
            for d in drafts
        ])  # fmt: skip
    if "packs" in wanted:
        add("packs", [(str(p.get("id")), str(p.get("name") or p.get("id")))
                      for p in listed(["pack", "list"], "packs")])  # fmt: skip
    if "saves" in wanted:
        add("saves", [(str(x.get("label")), f"#e{x.get('event')}")
                      for x in listed(["saves"], "saves")])  # fmt: skip
    for name, argv, key in (
        ("oracles", ["oracle", "list"], "oracles"),
        ("tables", ["table", "list"], "tables"),
        ("rules", ["rules", "list"], "rules"),
        ("generators", ["gen", "list"], "generators"),
        ("chargens", ["char", "list"], "chargens"),
    ):
        if name in wanted:
            add(name, titled(listed(argv, key)))
    units: list[str] = []
    if any(value_name(p) in TIMES for p in spec.params):
        shown = req.run("time", "show")
        units = [str(u) for u in as_dict(shown.data.get("units"))] if shown.ok else []
    return lists, h(t"{markup}"), units


def _example_line(example: str) -> str:
    """An example without `didact` and its trailing comment."""
    return example.removeprefix("didact ").split("  #")[0].strip()


def _prefill(req: Request, spec: CommandSpec) -> dict[str, list[str]]:
    """`/commands/show?a.ref=npc:tom` fills the form in."""
    wanted = {f"a.{p.cli_name}" for p in spec.params}
    return {key: values for key, values in req.query.items() if key in wanted}
