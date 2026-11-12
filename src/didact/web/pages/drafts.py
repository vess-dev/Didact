"""Drafts: character creation and generators, one step at a time.

`char new` and `gen run` build a draft (`c3`, `g7`), and nothing is written until it's
committed. These pages start one, show what it holds (entities and their fields, the map,
the rolls, the book's prompts) and the question it waits for, and run `choose`, `roll`,
`edit`, `discard` and `commit` as real commands, each shown with its command line.

A generator's draft is the GM's material (what waits in each room, hidden paths, secrets), so
the player view shows only that it's there. A character's draft is the player's own.

Most buttons post to `/run`. Four forms post here instead, because what they run or where
they go next depends on what was typed or made: starting a draft (then its page), answering
with parts (picks, scores, an array spread over fields: one `choose`), editing one (only the
fields that changed) and committing one (then the new record, or a list).
"""

import json
import re
import shlex
from dataclasses import dataclass, replace
from urllib.parse import quote, urlencode

from didact.core import labels
from didact.core.errors import DidactError, NotFoundError, UsageError
from didact.core.i18n import _, ngettext, pgettext
from didact.core.output import JSON, flatten
from didact.core.phrases import shown as shown_phrase
from didact.rules.engine import Param as RuleParam
from didact.web.app import Flash, Ran, Request, Response
from didact.web.forms import (
    accepts,
    lines,
    rule_argv,
    rule_fields,
    rule_params,
    text_block,
    typed_entry,
)
from didact.web.html import (
    Html,
    boxed_list,
    button,
    chip,
    datalist,
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
    textarea,
    type_dot,
    url,
)
from didact.web.layout import (
    Confirm,
    command_line,
    csrf,
    failure,
    guarded,
    page,
    result_panel,
    run_form,
    undo_button,
    words_form,
)
from didact.web.markdown import inline, markdown
from didact.web.pages.actions import safe_path
from didact.web.pages.common import (
    COMMON_TYPES,
    Listed,
    as_dict,
    as_list,
    record_index,
    records_datalist,
    secret_note,
    show_value,
    type_color,
    type_label,
)

DRAFT_ID = re.compile(r"#?([a-z]{1,8}\d{1,9})", re.IGNORECASE)  # c3, g7
BUTTONS_UP_TO = 24  # with more options than this, a list to pick from instead of buttons
LONG_VALUE = 24  # a value longer than this gets smaller type in its tile
MAP_W, MAP_H, MAP_PAD = 1000, 600, 44  # the map's drawing area


@dataclass(frozen=True, slots=True)
class Draft:
    """A draft as `gen show` (or `char show`) gives it."""

    id: str
    kind: str  # chargen | generator
    source: str
    data: dict[str, JSON]

    @classmethod
    def of(cls, ran: Ran) -> Draft:
        data = as_dict(ran.data.get("draft"))
        return cls(str(data.get("id")), str(data.get("kind")), str(data.get("source")), data)

    @property
    def character(self) -> bool:
        return self.kind == "chargen"

    @property
    def verb(self) -> str:
        """Its commands: `char …` for a character's draft, `gen …` for a generator's."""
        return "char" if self.character else "gen"

    @property
    def href(self) -> str:
        return draft_url(self.id)

    @property
    def open(self) -> dict[str, JSON] | None:
        """The question it waits for: `name`, `options` and `note`; `dice` is false when the
        dice can't answer it, `free` true when any answer can be typed in."""
        choice = self.data.get("open")
        return choice if isinstance(choice, dict) else None

    @property
    def dice(self) -> bool:
        choice = self.open
        return choice is not None and choice.get("dice") is not False

    @property
    def entities(self) -> list[dict[str, JSON]]:
        return [as_dict(e) for e in as_list(self.data.get("entities"))]

    @property
    def names(self) -> dict[str, str]:
        """Entity keys (`poi-1`) and their names, for the fields and links that name one."""
        return {str(e.get("key")): str(e.get("name") or e.get("key")) for e in self.entities}


def draft_url(draft_id: str) -> str:
    return "/drafts/" + quote(draft_id, safe="")


def _draft_id(raw: str) -> str | None:
    found = DRAFT_ID.fullmatch(raw.strip())
    return found.group(1).lower() if found else None


def _reader(draft_id: str) -> str:
    """The command that reads a draft (either does): `char` for c…, `gen` for the rest."""
    return "char" if draft_id.startswith("c") else "gen"


def _said(name: str) -> str:
    text = name.replace("_", " ").replace("-", " ").strip()
    return text[:1].upper() + text[1:]


# ---------------------------------------------------------------------------- entry points


def start_links(req: Request) -> Html:
    """Buttons that start a character or a generator, and the way to the open drafts."""
    count = len(as_list(req.run("gen", "drafts").data.get("items")))
    drafts = link_button(
        "/drafts",
        _("Drafts ({count})", count=count) if count else _("Drafts"),
        icon_name="edit-3",
        kind="flat",
    )
    return h(t'<div class="button-row draft-links">{_start_buttons()}{drafts}</div>')


def start_group(req: Request) -> Html:
    """The same, for the new-record page."""
    return group(
        _("Or let the system make it"),
        start_links(req),
        description=_(
            "Its own character creation, or a generator: step by step or all at once, "
            "as a draft you look over before anything is written."
        ),
    )


def _start_buttons() -> Html:
    return h(
        t"{link_button('/drafts/new#character', _('Create a character'), icon_name='user-plus')}"
        t"{link_button('/drafts/new#generate', _('Generate…'), icon_name='zap')}"
    )


def advance_button(req: Request, ref: str, type_: str) -> Html | None:
    """The system's way to advance this kind of record (a level-up), as a draft to go through
    step by step; nothing changes until it's committed."""
    listed = req.run("char", "list")
    found = next(
        (
            as_dict(a)
            for a in as_list(listed.data.get("advancements"))
            if as_dict(a).get("advances") == type_
        ),
        None,
    )
    if found is None:
        return None
    label = str(found.get("title") or pgettext("draft", "Advance"))
    go = button(label, icon_name="trending-up", kind="suggested")
    return _post(req, "/drafts/start", go, {"what": "advance", "record": ref})


def waiting_note(req: Request) -> Html | None:
    """A line for the overview while drafts wait to be committed."""
    count = len(as_list(req.run("gen", "drafts").data.get("items")))
    if not count:
        return None
    what = ngettext("{n} draft is waiting", "{n} drafts are waiting", count)
    about = _("Characters and generated material: nothing is written until they're committed.")
    return group(
        _("Drafts"), boxed_list([row(what, subtitle=about, href="/drafts", prefix=icon("edit-3"))])
    )


# ---------------------------------------------------------------------------- the list


def index(req: Request) -> Response:
    flash = req.take_flash()
    listed = req.run("gen", "drafts")
    if not listed.ok:
        body = failure(listed)
    else:
        items = [as_dict(item) for item in as_list(listed.data.get("items"))]
        generated = any(item.get("kind") != "chargen" for item in items)
        titles = _generator_titles(req) if generated else {}
        rows = [_draft_row(req, item, titles) for item in items]
        about = _(
            "Character creation and generators build a draft first: nothing in it is written "
            "until it's committed."
        )
        if rows:
            body = group(
                _("Open drafts"), boxed_list(rows), description=about, suffix=_start_buttons()
            )
        else:
            starts = h(t'<div class="button-row">{_start_buttons()}</div>')
            body = status_page("edit-3", _("No drafts"), about, starts)
    return page(
        req, _("Drafts"), h(t"{_outcome(req, flash)}{body}"), nav="records", back="/records"
    )


def _generator_titles(req: Request) -> dict[str, str]:
    listed = req.run("gen", "list")
    found = (as_dict(g) for g in as_list(listed.data.get("generators")))
    return {str(g.get("id")): str(g.get("title") or g.get("id")) for g in found}


def _draft_row(req: Request, item: dict[str, JSON], titles: dict[str, str]) -> Html:
    draft_id, source = str(item.get("id")), str(item.get("source"))
    waits = item.get("waiting")
    state = (
        chip(_("waiting for {what}", what=waits), kind="dim")
        if waits
        else chip(_("ready"), kind="accent")
    )
    href = draft_url(draft_id)
    if item.get("kind") == "chargen":
        name = str(item.get("name") or "") or _("A new character")
        subtitle = _("#{draft} · character · {source}", draft=draft_id, source=source)
        return row(name, subtitle=subtitle, href=href, prefix=icon("user"), suffix=state)
    title = titles.get(source, source)
    if not req.gm:  # what it made is the GM's: not even its first name
        gm_only = chip(_("GM view only"), kind="secret", icon_name="eye-off")
        subtitle = _("#{draft} · generator", draft=draft_id)
        return row(title, subtitle=subtitle, href=href, prefix=icon("zap"), suffix=gm_only)
    made = str(item.get("name") or "")
    subtitle = f"#{draft_id} · {made or source}"
    return row(title, subtitle=subtitle, href=href, prefix=icon("zap"), suffix=state)


# ---------------------------------------------------------------------------- starting one


def new(req: Request) -> Response:
    flash = req.take_flash()  # only a start that failed comes back here
    values = flash.values if flash is not None else {}
    panel = result_panel(req, flash.ran) if flash is not None else None
    body = h(t"{panel}{_character_start(req, values)}{_generator_start(req, values)}")
    return page(req, _("Create or generate"), body, nav="records", back="/records")


def _character_start(req: Request, values: dict[str, list[str]]) -> Html:
    mine = _first(values, "what") == "character"  # a start that failed: filled in again
    given = _first(values, "prefill") if mine else ""
    decided = textarea(
        "prefill", given, rows=2, placeholder=_("e.g. name=Freya"), label=_("Already decided")
    )
    help_ = _("name=value, one per line: the rest is asked, or rolled")
    guided = button(
        _("Step by step"), icon_name="list", kind="suggested pill", name="mode", value="guided"
    )
    rolled = button(_("At random"), icon_name="shuffle", kind="pill", name="mode", value="random")
    listed = req.run("char", "list")
    chargens = [as_dict(c) for c in as_list(listed.data.get("chargens"))] if listed.ok else []
    which = None
    if len(chargens) > 1:  # the system's PCs, and more: hirelings, followers, …
        chosen = (_first(values, "chargen") if mine else "") or str(
            listed.data.get("default") or ""
        )
        options = [(str(c.get("id")), str(c.get("title") or c.get("id"))) for c in chargens]
        control = select("chargen", options, chosen, label=_("Which character"))
        helps = [
            h(
                t"<li><strong>{c.get('title') or c.get('id')}</strong>: "
                t"{inline(str(c['help']))}</li>"
            )
            for c in chargens
            if c.get("help")
        ]
        about = h(t'<ul class="field-list dim small">{helps}</ul>') if helps else None
        which = h(t"{field(_('Which character'), control)}{about}")
    form = _post(
        req,
        "/drafts/start",
        h(
            t'<div class="fields">{which}'
            t"{field(_('Already decided (optional)'), decided, help_=help_)}"
            t'</div><div class="button-row">{guided}{rolled}</div>'
        ),
        {"what": "character"},
        cls="card stack",
    )
    return group(
        _("Create a character"),
        form,
        description=_(
            "The system's own character creation: answer each question as it comes, "
            "or let the dice roll it all. Nothing is written until you commit."
        ),
        id_="character",
    )


def _generator_start(req: Request, values: dict[str, list[str]]) -> Html:
    about = _("Places, dungeons and more from the packs' generators, made as a draft first.")
    if not req.gm:
        gms = _(
            "What a generator makes is the GM's until it's revealed: secrets, hidden paths, what "
            "waits in each room. Turn on the GM view to run one."
        )
        listed = req.run("gen", "list")  # which there are and what they make: no drafts
        found = [as_dict(g) for g in as_list(listed.data.get("generators"))] if listed.ok else []
        rows = [
            row(str(g.get("title") or g.get("id")), subtitle=inline(str(g.get("help") or "")))
            for g in found
        ]
        which = boxed_list(rows) if rows else None
        notice = h(
            t'<section class="card stack"><p class="note">{icon("eye-off")}<span>{gms}</span></p>'
            t'{which}<div class="button-row">{_gm_button(req)}</div></section>'
        )
        return group(_("Generate"), notice, description=about, id_="generate")
    listed = req.run("gen", "list")
    if not listed.ok:
        return group(_("Generate"), failure(listed), id_="generate")
    generators = [as_dict(g) for g in as_list(listed.data.get("generators"))]
    if not generators:
        empty = h(t'<p class="dim empty">{_("The enabled packs bring no generators.")}</p>')
        return group(_("Generate"), empty, description=about, id_="generate")
    tried = _first(values, "generator")  # the one whose start failed: filled in again
    wanted = req.arg("generator") or tried
    sections: list[Html] = []
    refs = False
    for gen in generators:
        gen_id = str(gen.get("id"))
        params = _params(gen_id, as_dict(gen.get("params")))
        refs = refs or any(p.kind == "ref" for p in params)
        form = _generator_form(req, gen, params, values if tried == gen_id else {})
        name = h(t'{gen.get("title") or gen_id} <span class="dim small">{gen_id}</span>')
        sections.append(expander(name, form, open_=gen_id == wanted))  # the one asked for
    records = records_datalist(record_index(req)) if refs else None
    body = h(t'<div class="stack">{sections}</div>{records}')
    return group(_("Generate"), body, description=about, id_="generate")


def _params(gen_id: str, raw: dict[str, JSON]) -> list[RuleParam]:
    """A generator's `name=value` parameters; an empty default reads as optional."""
    params = rule_params(gen_id, {"params": raw})
    return [replace(p, default=None, optional=True) if p.default == "" else p for p in params]


def _generator_form(
    req: Request, gen: dict[str, JSON], params: list[RuleParam], values: dict[str, list[str]]
) -> Html:
    about = str(gen.get("help") or "")
    help_text = h(t'<p class="dim">{inline(about)}</p>') if about else None
    asked = rule_fields(params, values, records="records") if params else None
    decided = textarea(
        "prefill",
        _first(values, "prefill"),
        rows=2,
        placeholder=_("e.g. terrain=Swamp"),
        label=_("Already decided"),
    )
    help_ = _("name=value, one per line: what it would otherwise roll or ask")
    stepwise = button(
        _("Step by step"), icon_name="list", kind="suggested", name="mode", value="guided"
    )
    at_once = button(_("All at once"), icon_name="shuffle", name="mode", value="auto")
    return _post(
        req,
        "/drafts/start",
        h(
            t"{help_text}{asked}"
            t'<div class="fields">{field(_("Already decided (optional)"), decided, help_=help_)}'
            t'</div><div class="button-row">{stepwise}{at_once}</div>'
        ),
        {"what": "generator", "generator": str(gen.get("id"))},
        cls="stack",
    )


def start(req: Request) -> Response:
    """POST /drafts/start: `char new` or `gen run`, then on to the new draft."""
    what = req.field("what")
    gen_id = req.field("generator").strip()
    if what == "generator":
        back = url("/drafts/new", generator=gen_id) + "#generate"
    elif what == "advance":
        back = record_url(req.field("record").strip())
    else:
        back = "/drafts/new#character"
    try:
        argv = _start_argv(req, what, gen_id)
    except DidactError as err:
        ran = Ran.failed([], err)
    else:
        ran = req.app.run(argv)
    made = as_dict(ran.data.get("draft")).get("id")
    return _go(req, ran, draft_url(made) if ran.ok and isinstance(made, str) else back)


def _start_argv(req: Request, what: str, gen_id: str) -> list[str]:
    given = _prefill(req.field("prefill"))
    prefill = ["--prefill", json.dumps(given, ensure_ascii=False)] if given else []
    mode = req.field("mode")
    if what == "advance":  # a level-up: a draft that changes the record
        random_ = ["--mode", "random"] if mode == "random" else []
        return ["char", "advance", req.field("record").strip(), *random_, *prefill]
    if what == "character":
        chargen = req.field("chargen").strip()
        random_ = ["--mode", "random"] if mode == "random" else []
        return ["char", "new", *([chargen] if chargen else []), *random_, *prefill]
    if what != "generator":
        raise UsageError(_("can't start {what}", what=repr(what)), hint=_("reload the page"))
    if not gen_id:
        raise UsageError(_("pick a generator first"), hint=_("see `didact gen list`"))
    listed = req.run("gen", "list")
    found = [as_dict(g) for g in as_list(listed.data.get("generators"))]
    gen = next((g for g in found if g.get("id") == gen_id), None)
    if gen is None:
        raise NotFoundError(
            _("no generator {generator} here", generator=repr(gen_id)),
            hint=_("see `didact gen list`"),
        )
    params = _params(gen_id, as_dict(gen.get("params")))
    args = rule_argv(gen_id, params, req.form)[2:]  # past `do <rule>`: the name=value pairs
    return ["gen", "run", gen_id, *args, *prefill, *(["--auto"] if mode == "auto" else [])]


def _prefill(text: str) -> dict[str, JSON]:
    """`name=value` lines as `--prefill` JSON. Numbers stay numbers; a name given twice gets
    a list (a value for each time the procedure asks)."""
    found: dict[str, JSON] = {}
    for line in lines(text_block(text)):
        name, sep, raw = line.partition("=")
        if not sep or not name.strip():
            hint = _("one name=value per line, e.g. name=Freya")
            raise UsageError(_("can't read {text}", text=repr(line)), hint=hint)
        key, value = name.strip(), _typed(raw.strip())
        if key not in found:
            found[key] = value
            continue
        before = found[key]
        found[key] = [*before, value] if isinstance(before, list) else [before, value]
    return found


def _typed(text: str) -> JSON:
    """A number or a JSON list as itself; anything else as the text it is."""
    try:
        value: JSON = json.loads(text)
    except ValueError:
        return text
    return text if value is None else value


def _first(values: dict[str, list[str]], name: str) -> str:
    found = values.get(name)
    return found[0] if found else ""


# ---------------------------------------------------------------------------- one draft


def show(req: Request) -> Response:
    flash = req.take_flash()
    draft_id = _draft_id(req.params["draft"])
    if draft_id is None:
        return _missing(req, req.params["draft"], flash)
    shown = req.run(_reader(draft_id), "show", draft_id)
    if not shown.ok:
        return _missing(req, draft_id, flash, shown)
    draft = Draft.of(shown)
    if not draft.character and not req.gm:
        return _gm_only(req, draft)
    target = draft.data.get("target")
    if isinstance(target, str):
        name = next((str(e.get("name") or "") for e in draft.entities), "") or target
        what = str(shown.data.get("title") or pgettext("draft", "Advance"))
        title = _("{what}: {name}", what=what, name=name)
        subtitle = _("draft #{draft} · {source} · changes {record}", draft=draft.id,
                     source=draft.source, record=target)  # fmt: skip
    elif draft.character:
        name = next((str(e.get("name") or "") for e in draft.entities), "")
        title = name or _("New character")
        subtitle = _("character draft #{draft} · {source}", draft=draft.id, source=draft.source)
    else:
        title = _generator_titles(req).get(draft.source, draft.source)
        subtitle = _("draft #{draft} · {source}", draft=draft.id, source=draft.source)
    typed = flash.values if flash is not None and not flash.ran.ok else {}  # to fill in again
    back = _back_button(req, draft) if shown.data.get("back") is not None else None
    body = h(
        t"{_outcome(req, flash)}{_question(req, draft, typed, back)}{_actions(req, draft)}"
        t"{_map(draft)}{_holds(req, draft, typed)}{_prompts(draft)}{_rolls(req, draft)}"
    )
    return page(req, title, body, nav="records", back="/drafts", subtitle=subtitle)


def _missing(req: Request, raw: str, flash: Flash | None, shown: Ran | None = None) -> Response:
    """A draft that isn't there (committed, discarded, or never was): say so, and where to go."""
    drafts = link_button("/drafts", _("Open drafts"), icon_name="edit-3", kind="suggested pill")
    status = 404
    if shown is None:
        about = _(
            "“{draft}” isn't a draft: drafts are numbered like c3 (a character) or g7.", draft=raw
        )
        body = status_page("compass", _("No such draft"), about, drafts)
    else:
        missing = isinstance(shown.error, NotFoundError)
        status = 404 if missing else 200
        title = _("No such draft") if missing else _("Can't show it")
        body = h(t'{failure(shown, title=title)}<div class="button-row">{drafts}</div>')
    body = h(t"{_outcome(req, flash)}{body}")
    return page(req, _("No such draft"), body, nav="records", back="/drafts", status=status)


def _gm_only(req: Request, draft: Draft) -> Response:
    """A generator's draft in the player view: that it's there, and nothing it holds."""
    about = _(
        "What a generator makes is the GM's until it's revealed: secrets, hidden paths, what "
        "waits in each room. Turn on the GM view to see this draft and work on it."
    )
    body = status_page("eye-off", _("This draft is for the GM"), about, _gm_button(req, pill=True))
    return page(req, _("Draft #{draft}", draft=draft.id), body, nav="records", back="/drafts")


def _gm_button(req: Request, *, pill: bool = False) -> Html:
    kind = "suggested pill" if pill else "suggested"
    turn_on = button(_("Turn on the GM view"), icon_name="eye", kind=kind)
    return h(
        t'<form method="post" action="/gm" class="inline">{csrf(req)}{hidden("next", req.here)}'
        t"{hidden('on', '1')}{turn_on}</form>"
    )


def _outcome(req: Request, flash: Flash | None) -> Html | None:
    """What the last step did, in short: its closing line and its command line, with Undo;
    or what went wrong and how to fix it."""
    if flash is None:
        return None
    ran = flash.ran
    if not ran.ok:
        return result_panel(req, ran)
    said = [line for line in ran.md.strip().splitlines() if line.strip()]
    done = inline(said[-1].removeprefix("✔ ")) if said else _("Done")
    return h(
        t'<section class="card result draft-outcome"><div class="result-head is-ok">'
        t"{icon('check-circle')}<span>{done}</span></div>{command_line(ran.line)}"
        t'<div class="result-tools">{undo_button(req, ran)}</div></section>'
    )


def _question(req: Request, draft: Draft, typed: dict[str, list[str]], back: Html | None) -> Html:
    choice = draft.open
    if choice is None:
        commit = _commit_form(req, draft)
        ready = _("Nothing is written yet: look it over, edit what you like, then commit it.")
        return h(
            t'<section class="card draft-question is-ready" id="question">'
            t'<span class="draft-kicker">{_("Ready")}</span><h2>{_("Nothing left to decide")}</h2>'
            t'<p class="dim">{ready}</p><div class="button-row">{back}{commit}</div></section>'
        )
    name = str(choice.get("name") or "")
    note = shown_phrase(
        choice.get("say"), str(choice.get("note") or "")
    )  # in the reader's language
    options = [str(o) for o in as_list(choice.get("options"))]
    meant = {str(k): str(v) for k, v in as_dict(choice.get("about")).items()}
    named = {str(k): str(v) for k, v in as_dict(choice.get("labels")).items()}
    form = as_dict(choice.get("form"))
    several = choice.get("pick")
    about = h(t'<p class="dim">{note}</p>') if note else None
    picks: Html | None = None
    if form.get("kind") == "point_buy":
        picks = _point_buy(req, draft, form, typed)
    elif form.get("kind") == "assign":
        picks = _spread(req, draft, form, typed)
    elif isinstance(several, int) and several > 1 and options:
        picks = _several(req, draft, options, several, meant, named, typed)
    elif len(options) > BUTTONS_UP_TO:
        choices = [("", _("(choose)")), *((o, named.get(o, o)) for o in options)]
        listed = select("a.value", choices, label=_said(name), required=True)
        picks = _choose_form(req, draft, h(t"{listed}{button(_('Choose'), icon_name='check')}"))
        if meant:
            rows = [row(named.get(o, o), subtitle=inline(meant[o])) for o in options if o in meant]
            picks = h(t"{picks}{expander(_('What each one means'), boxed_list(rows))}")
    elif options and (meant or named):
        picks = _described(req, draft, options, meant, named)
    elif options:
        buttons = [_option(req, draft, option) for option in options]
        picks = h(t'<div class="draft-options">{buttons}</div>')
    own: Html | None = None
    if choice.get("free") is True and not form:
        hint = _("or one of your own") if options else _("your answer")
        given = _first(typed, "a.value")  # an answer that failed, to fix
        box = entry(
            "a.value", given, placeholder=hint, label=_("Your {name}", name=name), required=True
        )
        own = _choose_form(req, draft, h(t"{box}{button(_('Answer'), icon_name='check')}"))
    dice = None
    if draft.dice:
        dice = words_form(
            req,
            [draft.verb, "roll", draft.id, "--one"],
            _("Let the dice decide"),
            icon_name="hexagon",
            title=_("Roll for this one; the next question waits for you"),
        )
    return h(
        t'<section class="card draft-question" id="question">'
        t'<span class="draft-kicker">{_("Next")}</span><h2>{_said(name)}</h2>{about}{picks}{own}'
        t'<div class="button-row">{back}{dice}</div></section>'
    )


def _back_button(req: Request, draft: Draft) -> Html:
    """Go back a step: take back the last answer, roll or edit (`char back`), so the question
    before comes again. The history keeps it: Undo, or Redo, brings it back."""
    return words_form(
        req,
        [draft.verb, "back", draft.id],
        pgettext("draft", "Back"),  # a step back (some languages' plain Back is also Undo)
        icon_name="arrow-left",
        title=_("Go back a step: take back the last answer, roll or edit"),
    )


def _option(req: Request, draft: Draft, option: str) -> Html:
    guard = ["--"] if option.startswith("-") else []  # so `-1` isn't read as an option
    return words_form(req, [draft.verb, "choose", draft.id, *guard, option], option)


def _described(
    req: Request, draft: Draft, options: list[str], meant: dict[str, str], named: dict[str, str]
) -> Html:
    """Options that say what they mean (or that are ids with names): a row each, the whole row
    a button that chooses it."""
    forms: list[Html] = []
    for option in options:
        guard = ["--"] if option.startswith("-") else []
        said = (
            h(t'<span class="row-subtitle">{inline(meant[option])}</span>')
            if option in meant
            else None
        )
        pick = h(
            t'<button type="submit" class="option-button"><span class="row-text">'
            t'<span class="row-title">{named.get(option, option)}</span>{said}</span>'
            t"{icon('chevron-right', cls='icon row-arrow')}</button>"
        )
        fields = {"action": "words", "w": [draft.verb, "choose", draft.id, *guard, option]}
        forms.append(run_form(req, pick, fields=fields, cls="option-row"))
    return h(t'<div class="boxed-list draft-choices">{forms}</div>')


def _several(
    req: Request,
    draft: Draft,
    options: list[str],
    count: int,
    meant: dict[str, str],
    named: dict[str, str],
    typed: dict[str, list[str]],
) -> Html:
    """Pick several at once: a box to tick for each option (app.js stops at `count`)."""
    ticked = set(typed.get("pick", []))
    rows: list[Html] = []
    for option in options:
        said = (
            h(t'<span class="row-subtitle">{inline(meant[option])}</span>')
            if option in meant
            else None
        )
        mark = Html(" checked") if option in ticked else Html("")
        rows.append(
            h(
                t'<label class="row option-check"><input type="checkbox" class="check" '
                t'name="pick" value="{option}"{mark}><span class="row-text">'
                t'<span class="row-title">{named.get(option, option)}</span>{said}</span></label>'
            )
        )
    status = _("{n} of {count} chosen", n=len(ticked), count=count)
    words = _("{n} of {count} chosen")  # app.js fills it in as boxes are ticked
    choose = button(_("Choose these"), icon_name="check", kind="suggested")
    body = h(
        t'<div class="boxed-list">{rows}</div><div class="button-row">{choose}<span '
        t'class="dim small" data-pick-count="{words}" aria-live="polite">{status}</span></div>'
    )
    return _post(
        req, f"{draft.href}/answer", body, {"verb": draft.verb, "kind": "pick"}, cls="stack",
        data={"pick": str(count)},
    )  # fmt: skip


def _point_buy(
    req: Request, draft: Draft, form: dict[str, JSON], typed: dict[str, list[str]]
) -> Html:
    """Buy scores with a budget: a number for each field, within what the cost table has;
    app.js keeps the points spent up to date."""
    names = [str(f) for f in as_list(form.get("fields"))]
    costs = {str(k): v for k, v in as_dict(form.get("costs")).items() if isinstance(v, int)}
    scores = sorted(int(k) for k in costs if k.lstrip("-").isdigit())
    budget = form.get("budget")
    if not names or not scores or not isinstance(budget, int):
        return h(t"")
    low, high = scores[0], scores[-1]
    controls: list[Html] = []
    spent = 0
    for name in names:
        given = _first(typed, f"pb.{name}") or str(low)
        spent += costs.get(given, 0) if isinstance(costs.get(given), int) else 0
        box = entry(
            f"pb.{name}", given, type_="number", required=True, label=_said(name),
            attrs={"min": str(low), "max": str(high), "step": "1", "inputmode": "numeric"},
        )  # fmt: skip
        controls.append(field(_said(name), box))
    priced = ", ".join(f"{score} → {costs[str(score)]}" for score in scores)
    left = _("{spent} of {budget} points spent", spent=spent, budget=budget)
    words = {
        "data-spent": _("{spent} of {budget} points spent"),
        "data-over": _("{spent} of {budget} points: over the budget"),
    }
    state = json.dumps({"budget": budget, "costs": costs})
    extra = join(h(t' {k}="{v}"') for k, v in words.items())
    use = button(_("Use these scores"), icon_name="check", kind="suggested")
    body = h(
        t'<div class="fields two">{controls}</div>'
        t'<p class="dim small">{_("What each score costs: {costs}", costs=priced)}</p>'
        t'<div class="button-row">{use}<span class="small budget" data-budget="{state}"{extra}'
        t' aria-live="polite">{left}</span></div>'
    )
    fields = {"verb": draft.verb, "kind": "point_buy", "fields": " ".join(names)}
    return _post(req, f"{draft.href}/answer", body, fields, cls="stack")


def _spread(req: Request, draft: Draft, form: dict[str, JSON], typed: dict[str, list[str]]) -> Html:
    """Spread a fixed array over fields: a list of the values for each field."""
    names = [str(f) for f in as_list(form.get("fields"))]
    values = [v for v in as_list(form.get("values")) if isinstance(v, int)]
    if not names or not values:
        return h(t"")
    signed = min(values) < 0
    shown_values = [f"{v:+d}" if signed else str(v) for v in values]
    distinct = sorted(set(values), reverse=True)
    choices = [("", _("(choose)")), *((str(v), f"{v:+d}" if signed else str(v)) for v in distinct)]
    controls = [
        field(_said(n), select(f"as.{n}", choices, _first(typed, f"as.{n}"), label=_said(n),
                               required=True))
        for n in names
    ]  # fmt: skip
    use = button(_("Use these"), icon_name="check", kind="suggested")
    each = _("Use each of {values} once, one per field.", values=", ".join(shown_values))
    body = h(
        t'<div class="fields two">{controls}</div><p class="dim small">{each}</p>'
        t'<div class="button-row">{use}</div>'
    )
    fields = {"verb": draft.verb, "kind": "assign", "fields": " ".join(names)}
    return _post(req, f"{draft.href}/answer", body, fields, cls="stack")


def _choose_form(req: Request, draft: Draft, body: Html) -> Html:
    """An answer typed or picked: as a command form, which puts `--` before one like `-1`."""
    fields = {"action": "command", "cmd": f"{draft.verb} choose", "a.draft": draft.id}
    return run_form(req, body, fields=fields, cls="action-row")


def _actions(req: Request, draft: Draft) -> Html:
    rest = None
    if draft.dice:
        rest = words_form(
            req,
            [draft.verb, "roll", draft.id],
            _("Roll the rest"),
            icon_name="fast-forward",
            title=_("Let the dice make this choice and every one after it"),
        )
    edit = link_button(url(draft.href, edit="1") + "#holds", _("Edit"), icon_name="edit-3")
    form = words_form(
        req,
        [draft.verb, "discard", draft.id],
        _("Discard"),
        icon_name="trash-2",
        kind="destructive",
        next_ok="/drafts",
        confirm=Confirm(
            _("Discard draft #{draft}?", draft=draft.id),
            _("Nothing from it has been written, and it goes. Undo brings it back."),
            _("Discard"),
        ),
    )
    discard = guarded(
        f"{draft.href}/discard", _("Discard…"), form, icon_name="trash-2", kind="flat"
    )
    return h(t'<div class="button-row draft-actions">{rest}{edit}{discard}</div>')


def _commit_form(req: Request, draft: Draft) -> Html:
    """Commit: in the card that says it's ready (while it waits, `commit` would refuse)."""
    save = button(_("Commit"), icon_name="check", kind="suggested pill")
    return _post(req, f"{draft.href}/commit", save, {"verb": draft.verb})


def _post(
    req: Request,
    action: str,
    body: Html,
    fields: dict[str, str],
    *,
    cls: str = "inline",
    data: dict[str, str] | None = None,
) -> Html:
    """A form for the endpoints here (start, answer, edit, commit); `data` adds `data-*`
    attributes for app.js."""
    parts = [csrf(req), *(hidden(name, value) for name, value in fields.items())]
    extra = join(h(t' data-{key}="{value}"') for key, value in (data or {}).items())
    return h(t'<form method="post" action="{action}" class="{cls}"{extra}>{parts}{body}</form>')


# ---------------------------------------------------------------------------- what it holds


def _holds(req: Request, draft: Draft, typed: dict[str, list[str]]) -> Html:
    if isinstance(draft.data.get("target"), str):
        return _changes(draft)
    entities = draft.entities
    editing = req.arg("edit") == "1"
    items = [
        _entity(req, draft, entity, open_=editing, editing=editing, typed=typed)
        for entity in entities
    ]
    if not items:
        items = [h(t'<p class="dim empty">{_("Nothing yet: answer the question above.")}</p>')]
    added = _add_entity(req, draft) if not draft.character else None
    title = _("The character") if draft.character else _("What it makes")
    return group(title, h(t'<div class="stack">{_given(draft)}{items}{added}</div>'), id_="holds")


def _changes(draft: Draft) -> Html:
    """An advancement: what it changes on the record so far, before → after."""
    base = as_dict(draft.data.get("base"))
    main = next(iter(draft.entities), {})
    fields = as_dict(main.get("fields"))
    rows = [
        row(
            labels.field_name(key),
            subtitle=f"{_text(base.get(key), draft.names)} → {_text(value, draft.names)}",
        )
        for key, value in fields.items()
        if base.get(key) != value
    ]
    listed = boxed_list(rows, empty=_("Nothing changes yet: answer the question above."))
    return group(
        _("What changes"), h(t'<div class="stack">{_given(draft)}{listed}</div>'), id_="holds"
    )


def _given(draft: Draft) -> Html | None:
    """The parameters and what was decided up front, as chips."""
    params = as_dict(draft.data.get("params"))
    prefill = as_dict(draft.data.get("prefill"))
    chips = [chip(f"{k}={show_value(v)}", icon_name="sliders") for k, v in params.items()]
    chips += [chip(f"{k}={show_value(v)}", icon_name="check") for k, v in prefill.items()]
    if draft.data.get("auto") is True:
        chips.append(chip(_("the dice decide"), icon_name="shuffle"))
    if not chips:
        return None
    return h(t'<div class="chips"><span class="dim small">{_("Given:")}</span>{chips}</div>')


def _entity(
    req: Request,
    draft: Draft,
    entity: dict[str, JSON],
    *,
    open_: bool,
    editing: bool,
    typed: dict[str, list[str]],
) -> Html:
    key = str(entity.get("key"))
    type_ = str(entity.get("type"))
    names = draft.names
    fields = as_dict(entity.get("fields"))
    shown = [(k, v) for k, v in flatten(fields) if k != "map" and not k.startswith("map.")]
    tiles = [_tile(k, _text(v, names)) for k, v in shown if v not in ([], {}, None, "")]
    links = [
        chip(f"{link.get('rel') or _('related')} → {_text(link.get('to'), names)}", kind="rel")
        for link in (as_dict(item) for item in as_list(entity.get("links")))
    ]
    tags = [chip(str(tag), icon_name="tag") for tag in as_list(entity.get("tags"))]
    scope = entity.get("scope")
    if isinstance(scope, str):
        tags.append(chip(_("goes to the {scope}", scope=scope), icon_name="layers"))
    marks = h(t'<div class="chips">{tags}{links}</div>') if tags or links else None
    text = str(entity.get("body") or "")
    body = h(t'<div class="card">{markdown(text)}</div>') if text.strip() else None
    grid = h(t'<div class="tiles">{tiles}</div>') if tiles else None
    mine = _first(typed, "key") == key  # its edit failed: open, with what was typed
    form = _edit_form(req, draft, entity, shown, typed if mine else {})
    editor = expander(_("Edit"), form, open_=editing or mine, cls="is-plain")
    drop = None
    if not draft.character:
        drop = words_form(
            req,
            ["gen", "edit", draft.id, "--drop", key],
            _("Leave out"),
            icon_name="x",
            kind="flat",
            title=_("Drop {key} from the draft, and the links to it", key=key),
        )
    name = str(entity.get("name") or "") or h(t'<span class="dim">{_("(no name yet)")}</span>')
    title = h(t'{name} <span class="dim small">{type_} · {key}</span>')
    inside = h(
        t'<div class="stack draft-entity">{grid}{marks}{body}{editor}'
        t'<div class="button-row">{drop}</div></div>'
    )
    dot = type_dot(type_color(type_))
    return h(t'<div id="e-{key}">{expander(title, inside, open_=open_ or mine, prefix=dot)}</div>')


def _tile(key: str, text: str) -> Html:
    label = key.replace(".", " ").replace("_", " ")
    size = "tile-value is-long" if len(text) > LONG_VALUE else "tile-value"
    return h(
        t'<div class="tile"><span class="tile-label">{label}</span>'
        t'<span class="{size}">{text}</span></div>'
    )


def _text(value: JSON, names: dict[str, str]) -> str:
    """A value as it reads: another entity's key as that entity's name, a list joined."""
    if isinstance(value, str):
        return names.get(value, value)
    if isinstance(value, bool):
        return _("yes") if value else _("no")
    if isinstance(value, list):
        return ", ".join(_text(v, names) for v in value) or "—"
    if isinstance(value, dict):
        named = value.get("name")
        return str(named) if named is not None else show_value(value)
    return "—" if value is None else str(value)


def _edit_form(
    req: Request,
    draft: Draft,
    entity: dict[str, JSON],
    shown: list[tuple[str, JSON]],
    typed: dict[str, list[str]],
) -> Html:
    """The name, each field and the description, and a new field: only what changed is sent
    to `edit`, so a change made elsewhere meanwhile stays."""

    def control(path: str, label: str, now: str) -> list[Html]:
        box = entry(f"v:{path}", _first(typed, f"v:{path}") or now, label=label)
        return [field(label, box), hidden(f"was:{path}", now)]

    name = str(entity.get("name") or "")
    controls = control("name", _("Name"), name)
    for path, raw in shown:
        controls += control(f"fields.{path}", path, show_value(raw))
    text = str(entity.get("body") or "")
    about: Html | None = None
    if text:
        box = textarea("v:body", _first(typed, "v:body") or text, rows=5, label=_("Description"))
        about = h(
            t'<div class="fields">{field(_("Description"), box)}{hidden("was:body", text)}</div>'
        )
    new_key = typed_entry(
        "key", "new.key", _first(typed, "new.key"), placeholder=_("e.g. pronouns")
    )
    new_value = entry("new.value", _first(typed, "new.value"))
    save = button(_("Save"), icon_name="check", kind="suggested")
    before, _sep, after = _("Text as it is; numbers and lists ({example}) as JSON.").partition(
        "{example}"
    )  # the example goes in between, as code
    return _post(
        req,
        f"{draft.href}/edit",
        h(
            t'<div class="fields two">{controls}</div>{about}'
            t'<div class="fields two">{field(_("New field"), new_key, help_=accepts("key"))}'
            t'{field(_("Its value"), new_value)}</div><p class="dim small">{before}'
            t'<code>["a", "b"]</code>{after}</p><div class="button-row">{save}</div>'
        ),
        {"verb": draft.verb, "key": str(entity.get("key"))},
        cls="stack",
    )


def _add_entity(req: Request, draft: Draft) -> Html:
    types = datalist("draft-types", ((kind, type_label(kind)) for kind in COMMON_TYPES))
    kind = typed_entry(
        "type", "add.type", placeholder=_("type, e.g. npc"), list_="draft-types", label=_("Type")
    )
    form = _post(
        req,
        f"{draft.href}/edit",
        h(
            t"{kind}"
            t"{entry('add.name', placeholder=_('its name'), label=_('Name'), required=True)}"
            t"{button(_('Add'), icon_name='plus')}{types}"
        ),
        {"verb": draft.verb},
        cls="action-row",
    )
    about = _("a person, place or thing of your own, in the same change")
    return boxed_list([form_row(_("Add one"), form, subtitle=about)])


def answer(req: Request) -> Response:
    """POST /drafts/<id>/answer: an answer made of parts (boxes ticked, scores bought, an array
    spread over fields), as the one `choose` it stands for."""
    draft_id = _draft_id(req.params["draft"]) or ""
    back = draft_url(draft_id) + "#question" if draft_id else "/drafts"
    try:
        verb = _verb(req, draft_id)
        value = _answer_value(req)
    except DidactError as err:
        return _go(req, Ran.failed([], err), back)
    guard = ["--"] if value.startswith("-") else []  # so `-1 2 0` isn't read as an option
    return _go(req, req.app.run([verb, "choose", draft_id, *guard, value]), back)


def _answer_value(req: Request) -> str:
    """The answer a form's parts make: `a, b` for picks, `2 1 0` for scores, `edge=3 …` for
    an array spread over fields."""
    kind = req.field("kind")
    names = req.field("fields").split()
    if kind == "pick":
        picked = [value for value in req.fields("pick") if value]
        if not picked:
            raise UsageError(_("tick the ones you want first"), hint=_("then choose them"))
        return ", ".join(picked)
    if kind == "point_buy":
        scores = [req.field(f"pb.{name}").strip() for name in names]
        wrong = next((s for s in scores if not s.lstrip("-").isdigit()), None)
        if wrong is not None or not names:
            raise UsageError(
                _("a score is a whole number, not {value}", value=repr(wrong or "")),
                hint=_("give each field a number"),
            )
        return " ".join(scores)
    if kind == "assign":
        given = [(name, req.field(f"as.{name}").strip()) for name in names]
        missing = [name for name, value in given if not value]
        if missing or not names:
            raise UsageError(
                _("give {field} a value", field=_said(missing[0]) if missing else "?"),
                hint=_("pick one for each field"),
            )
        return " ".join(f"{name}={value}" for name, value in given)
    raise UsageError(_("that form is out of date"), hint=_("reload the page"))


def edit(req: Request) -> Response:
    """POST /drafts/<id>/edit: `char edit` or `gen edit` with what the form changed."""
    draft_id = _draft_id(req.params["draft"]) or ""
    try:
        argv = _edit_argv(req, draft_id)
    except DidactError as err:
        ran = Ran.failed([], err)
    else:
        ran = req.app.run(argv)
    return _go(req, ran, draft_url(draft_id) if draft_id else "/drafts")


def _edit_argv(req: Request, draft_id: str) -> list[str]:
    verb = _verb(req, draft_id)
    key = req.field("key").strip()
    changes: list[str] = []
    for name, values in req.form.items():
        if key and name.startswith("v:"):
            path = name.removeprefix("v:")
            now = text_block(values[0] if values else "").strip()
            if now != text_block(req.field(f"was:{path}")).strip():
                changes.append(f"{key}.{path}={now}")
    new_key = req.field("new.key").strip()
    if key and new_key:
        changes.append(f"{key}.fields.{new_key}={req.field('new.value').strip()}")
    added: list[str] = []
    kind, name = req.field("add.type").strip(), req.field("add.name").strip()
    if kind or name:
        if not name:
            raise UsageError(_("a new one needs a name"), hint=_("e.g. Old Gannet"))
        added = ["--add", json.dumps({"type": kind or "note", "name": name}, ensure_ascii=False)]
    if not changes and not added:
        raise UsageError(_("nothing changed"), hint=_("change a value, then save"))
    return [verb, "edit", draft_id, *changes, *added]


def _verb(req: Request, draft_id: str) -> str:
    verb = req.field("verb")
    if not draft_id or verb not in ("char", "gen"):
        raise UsageError(_("that form is out of date"), hint=_("reload the page"))
    return verb


# ---------------------------------------------------------------------------- the map


def _map(draft: Draft) -> Html | None:
    """Where the dice dropped each place, and the paths between them."""
    data = as_dict(draft.data.get("map"))
    places = [str(k) for k in as_list(data.get("places"))]
    if not places:
        return None
    fields = {str(e.get("key")): as_dict(e.get("fields")) for e in draft.entities}
    names = draft.names

    def spot(key: str) -> dict[str, JSON]:
        return as_dict(fields.get(key, {}).get("map"))

    def point(key: str) -> tuple[float, float] | None:
        x, y = spot(key).get("x"), spot(key).get("y")
        if not isinstance(x, int | float) or not isinstance(y, int | float):
            return None
        return MAP_PAD + x * (MAP_W - 2 * MAP_PAD), MAP_PAD + y * (MAP_H - 2 * MAP_PAD)

    numbers: dict[str, str] = {}
    for index, key in enumerate(places, start=1):
        number = spot(key).get("n")
        numbers[key] = str(number if isinstance(number, int) else index)
    routes = [as_dict(r) for r in as_list(data.get("routes"))]
    marks: list[Html] = []
    for key in (str(k) for k in as_list(data.get("regions"))):
        at = point(key)
        if at is not None:
            label_y = at[1] + 80 if at[1] < MAP_H / 2 else at[1] - 68
            marks.append(
                h(
                    t'<g class="region"><circle cx="{at[0]:.0f}" cy="{at[1]:.0f}" r="56"></circle>'
                    t'<text x="{at[0]:.0f}" y="{label_y:.0f}">{names.get(key, key)}</text></g>'
                )
            )
    for route in routes:
        a, b = point(str(route.get("from"))), point(str(route.get("to")))
        if a is not None and b is not None:
            about = f"{_path_name(route, numbers)}: {_path_note(route)}"
            marks.append(
                h(
                    t'<line class="route is-{_path_kind(route)}" x1="{a[0]:.0f}" y1="{a[1]:.0f}" '
                    t'x2="{b[0]:.0f}" y2="{b[1]:.0f}"><title>{about}</title></line>'
                )
            )
    for key in places:
        at = point(key)
        if at is None:
            continue
        ends = [role for role in ("entrance", "exit") if spot(key).get(role)]
        cls = " ".join(["place", *(f"is-{role}" for role in ends)])
        marks.append(
            h(
                t'<g class="{cls}"><title>{numbers[key]}. {names.get(key, key)}</title>'
                t'<circle cx="{at[0]:.0f}" cy="{at[1]:.0f}" r="18"></circle>'
                t'<text x="{at[0]:.0f}" y="{at[1]:.0f}">{numbers[key]}</text></g>'
            )
        )
    svg = h(
        t'<svg viewBox="0 0 {MAP_W} {MAP_H}" role="img" '
        t'aria-label="{_("A map of the places and the paths between them")}">{marks}</svg>'
    )
    legend = [
        row(
            names.get(key, key),
            prefix=h(t'<span class="map-number">{numbers[key]}</span>'),
            subtitle=_place_note(spot(key), fields.get(key, {}), names),
            href=f"#e-{key}",
        )
        for key in places
    ]
    paths = [row(_path_name(route, numbers), subtitle=_path_note(route)) for route in routes]
    return group(
        _("Map"),
        h(
            t'<div class="card draft-map">{svg}</div>'
            t"{expander(_('Places'), boxed_list(legend), count=len(legend))}"
            t"{expander(_('Paths'), boxed_list(paths, empty=_('No paths.')), count=len(paths))}"
        ),
        description=_(
            "Where the dice dropped each place. Dashed paths are hidden; dotted ones "
            "need something to pass."
        ),
        id_="map",
    )


def _path_kind(route: dict[str, JSON]) -> str:
    kind = str(route.get("type") or ("hidden" if route.get("hidden") is True else "standard"))
    return re.sub(r"[^a-z0-9]+", "-", kind.lower())


def _path_name(route: dict[str, JSON], numbers: dict[str, str]) -> str:
    start, end = str(route.get("from")), str(route.get("to"))
    return f"{numbers.get(start, start)} — {numbers.get(end, end)}"


def _path_note(route: dict[str, JSON]) -> str:
    parts = [str(route.get("distance") or "")]
    watches = route.get("watches")
    if isinstance(watches, int):
        parts.append(ngettext("{n} watch", "{n} watches", watches))
    kind = route.get("type")
    if isinstance(kind, str):
        parts.append(kind)
    parts += [str(d) for d in as_list(route.get("details"))]
    return " · ".join(part for part in parts if part)


def _place_note(spot: dict[str, JSON], fields: dict[str, JSON], names: dict[str, str]) -> str:
    roles = {"entrance": _("entrance"), "exit": _("exit")}
    parts = [said for role, said in roles.items() if spot.get(role)]
    region = fields.get("region")
    if isinstance(region, str) and region:
        parts.append(_("in {place}", place=names.get(region, region)))
    feature = fields.get("feature")
    if isinstance(feature, str) and feature:
        parts.append(feature)
    return " · ".join(parts)


# ---------------------------------------------------------------------------- prompts, rolls


def _prompts(draft: Draft) -> Html | None:
    asked = [str(p) for p in as_list(draft.data.get("prompts"))]
    if not asked:
        return None
    items = [h(t"<li>{inline(text)}</li>") for text in asked]
    return group(
        _("Prompts"),
        h(t'<div class="card"><ul class="draft-prompts">{items}</ul></div>'),
        description=_("The book's questions: answer them in the descriptions, or in play."),
    )


def _rolls(req: Request, draft: Draft) -> Html | None:
    """Every roll the draft made, as the log has it."""
    labels = [str(r) for r in as_list(draft.data.get("rolls"))]
    if not labels:
        return None
    logged = req.run("rolls", "--limit", str(len(labels) + 100))
    said = {
        f"#r{roll.get('roll')}": str(roll.get("line") or "")
        for roll in (as_dict(item) for item in as_list(logged.data.get("rolls")))
    }
    items = [h(t"<li>{said.get(label) or label}</li>") for label in labels]
    return expander(_("Rolls"), h(t'<ol class="draft-rolls">{items}</ol>'), count=len(labels))


# ---------------------------------------------------------------------------- commit, discard


def commit(req: Request) -> Response:
    """POST /drafts/<id>/commit: then the new character's record, or a list of what was made."""
    draft_id = _draft_id(req.params["draft"]) or ""
    back = draft_url(draft_id) if draft_id else "/drafts"
    try:
        verb = _verb(req, draft_id)
    except DidactError as err:
        return _go(req, Ran.failed([], err), back)
    ran = req.app.run([verb, "commit", draft_id])
    made = [str(r) for r in as_list(ran.data.get("records"))]
    if not ran.ok or not made:
        return _go(req, ran, back)
    if verb == "char":
        return _go(req, ran, record_url(made[0]))  # the character comes first
    return _go(req, ran, "/drafts/made?" + urlencode([("id", ref) for ref in made]))


def made(req: Request) -> Response:
    """What a generator's draft made, once committed: as much of it as this view may see."""
    flash = req.take_flash()
    wanted = [ref for ref in req.query.get("id", []) if ref]
    known: dict[str, Listed] = {}
    for record in record_index(req).records:
        known.setdefault(record.id, record)
    rows = [
        row(
            known[ref].name,
            subtitle=f"{ref} · {known[ref].scope}",
            href=record_url(ref),
            prefix=type_dot(type_color(known[ref].type)),
        )
        for ref in wanted
        if ref in known
    ]
    hidden_ = sum(1 for ref in wanted if ref not in known)
    more = h(
        t"{link_button('/records', _('All records'), icon_name='book', kind='flat')}"
        t"{link_button('/graph', _('Graph'), icon_name='share-2', kind='flat')}"
    )
    listed = boxed_list(rows, empty=_("Nothing to show here."))
    made_ = group(_("Records made"), listed, description=_("Written in one change."), suffix=more)
    body = h(t"{_outcome(req, flash)}{made_}{secret_note(hidden_)}")
    return page(req, _("What it made"), body, nav="records", back="/drafts")


def confirm_discard(req: Request) -> Response:
    """Discarding without JS: ask first, on a page of its own."""
    draft_id = _draft_id(req.params["draft"])
    if draft_id is None:
        return _missing(req, req.params["draft"], None)
    shown = req.run(_reader(draft_id), "show", draft_id)
    if not shown.ok:
        return _missing(req, draft_id, None, shown)
    draft = Draft.of(shown)
    argv = [draft.verb, "discard", draft.id]
    form = words_form(
        req,
        argv,
        _("Discard"),
        icon_name="trash-2",
        kind="destructive pill",
        next_=draft.href,
        next_ok="/drafts",
    )
    cancel = link_button(draft.href, _("Cancel"), kind="pill")
    question = _("Discard draft #{draft}?", draft=draft.id)
    goes = _("Nothing from it has been written, and it goes. Undo brings it back.")
    body = h(
        t'<section class="card dialog-page"><h2>{question}</h2><p class="dim">{goes}</p>'
        t"{command_line(shlex.join(['didact', *argv]))}"
        t'<div class="button-row">{cancel}{form}</div></section>'
    )
    return page(req, _("Discard"), body, nav="records", back=draft.href)


# ---------------------------------------------------------------------------- after a POST


def _go(req: Request, ran: Ran, target: str) -> Response:
    """Keep the outcome for the next page and go there (POST, redirect, GET), as `/run`
    does: reloading never runs a command twice."""
    values = {k: v for k, v in req.form.items() if k != "csrf"}
    key = req.app.remember(Flash(ran, values=values))
    path, _sep, fragment = safe_path(target).partition("#")
    joiner = "&" if "?" in path else "?"
    return Response.redirect(f"{path}{joiner}flash={key}" + (f"#{fragment}" if fragment else ""))
