"""The overview: where the game stands (the brief), quick play actions, and recent changes."""

import re
from dataclasses import dataclass
from string import Formatter
from typing import Literal

from didact.commands.registry import REGISTRY
from didact.core import labels
from didact.core.i18n import _
from didact.core.output import JSON
from didact.web.app import Request, Response
from didact.web.forms import accepts, typed_entry
from didact.web.html import (
    Html,
    boxed_list,
    button,
    chip,
    entry,
    field,
    form_row,
    group,
    h,
    link_button,
    record_url,
    row,
    select,
    status_page,
)
from didact.web.layout import failure, page, result_panel, run_form, words_form
from didact.web.markdown import inline
from didact.web.pages.common import as_dict, as_list, change_title, record_index
from didact.web.pages.drafts import waiting_note

ODDS = ("very-unlikely", "unlikely", "even", "likely", "very-likely")


def show(req: Request) -> Response:
    flash = req.take_flash()
    brief = req.run("brief", gm=True)
    parts: list[Html | None] = [result_panel(req, flash.ran) if flash else None]
    if not brief.ok:
        parts.append(failure(brief))
    elif not brief.data.get("world"):
        parts.append(start_here(req))
    else:
        playing = bool(brief.data.get("campaign"))
        closed = h(t"{open_campaign(req, str(brief.data.get('world')))}{new_campaign(req)}")
        parts += [
            the_brief(req, brief.data, brief.md),
            waiting_note(req),
            quick_actions(req) if playing else closed,
            recent(req),
        ]
    return page(req, _("Overview"), h(t"{parts}"), nav="overview")


def system_choices(req: Request) -> list[tuple[str, str]]:
    listed = req.run("pack", "list")
    choices = [("", _("(none yet)"))]
    for item in as_list(listed.data.get("packs")):
        pack = as_dict(item)
        if pack.get("kind") == "system" and pack.get("origin") != "shipped":
            choices.append((str(pack.get("id")), f"{pack.get('name')} ({pack.get('id')})"))
    return choices


def start_here(req: Request) -> Html:
    """No world yet: say what a world is, and make one."""
    world_id = typed_entry("id", "w", placeholder=_("e.g. vale"), required=True)
    name = entry("o:--name", placeholder=_("e.g. The Vale"))
    create = button(_("Create world"), kind="suggested pill", icon_name="plus")
    system = select("o:--system", system_choices(req))
    form = run_form(
        req,
        h(
            t'<div class="fields two">{field(_("World id"), world_id, help_=accepts("id"))}'
            t"{field(_('Name'), name)}</div>"
            t'<div class="fields">{field(_("Game system"), system)}'
            t'</div><div class="button-row">{create}</div>'
        ),
        fields={"action": "words", "w": ["world", "new"]},
        cls="card stack",
    )
    about = _("A world holds a setting's canon; a campaign is one playthrough in it.")
    return h(t"{status_page('globe', _('Start a world'), about)}{form}")


def open_campaign(req: Request, world: str) -> Html | None:
    """No campaign is open: the world's, to open one."""
    listed = req.run("campaign", "list")
    rows = [
        row(
            str(c.get("name") or c.get("id")),
            subtitle=_("campaign {campaign}", campaign=c.get("id")),
            suffix=words_form(req, ["campaign", "open", str(c.get("id"))], _("Open")),
        )
        for c in (as_dict(item) for item in as_list(listed.data.get("campaigns")))
        if c.get("world") == world
    ]
    if not rows:
        return None
    return group(
        _("Open a campaign"),
        boxed_list(rows),
        description=_("None is open: open one to play on where it was left."),
    )


def new_campaign(req: Request) -> Html:
    campaign_id = typed_entry("id", "w", placeholder=_("e.g. first-run"), required=True)
    name = entry("o:--name", placeholder=_("e.g. The First Run"))
    start = button(_("Start campaign"), kind="suggested pill", icon_name="plus")
    form = run_form(
        req,
        h(
            t'<div class="fields two">'
            t"{field(_('Campaign id'), campaign_id, help_=accepts('id'))}"
            t"{field(_('Name'), name)}"
            t'</div><div class="button-row">{start}</div>'
        ),
        fields={"action": "words", "w": ["campaign", "new"]},
        cls="card stack",
    )
    return group(
        _("Start a campaign"), form, description=_("Sessions, PCs and the journal live in one.")
    )


def the_brief(req: Request, data: dict[str, JSON], text: str) -> Html:
    facts: list[Html] = []
    for key in ("world", "campaign", "system"):
        value = data.get(key)
        if value:
            facts.append(chip(_fact(key, str(value))))
    for key in ("session", "scene"):
        value = data.get(key)
        if isinstance(value, int) and value:
            facts.append(chip(_numbered(key, value)))
    names = record_index(req).names  # records the brief mentions become links
    location = data.get("location")
    if isinstance(location, str) and location:
        place = names.get(location, location)
        facts.append(chip(place, href=record_url(location), icon_name="map-pin"))
    party = [
        chip(names.get(str(ref), str(ref)), href=record_url(str(ref)), icon_name="user")
        for ref in as_list(data.get("party"))
    ]
    who = (
        h(t'<div class="chips"><span class="dim small">{_("Party:")}</span>{party}</div>')
        if party
        else None
    )
    suffix = link_button("/journal", _("Journal"), icon_name="book-open", kind="flat")
    body = h(
        t'<div class="card stack"><div class="chips">{facts}</div>{brief_rows(text, names)}{who}'
        t"</div>"
    )
    return group(_("Where the game stands"), body, suffix=suffix)


def _fact(key: str, value: str) -> str:
    match key:
        case "world":
            return _("World: {value}", value=value)
        case "campaign":
            return _("Campaign: {value}", value=value)
        case _:
            return _("System: {value}", value=value)


def _numbered(key: str, n: int) -> str:
    return _("Session {n}", n=n) if key == "session" else _("Scene {n}", n=n)


REF = re.compile(r"\[([a-z][a-z0-9-]*:[^\]\s]+)\]")


@dataclass(frozen=True, slots=True)
class Labelled:
    """One kind of the brief's lines, from the message it's written with (in the language in
    use): the line's label, then its value (the `value` placeholder)."""

    parts: list[tuple[str, str | None]]  # literal text, then a placeholder (or None)
    value: str
    kind: Literal["plain", "role", "always"]
    pattern: re.Pattern[str]

    @classmethod
    def of(
        cls, message: str, value: str = "", kind: Literal["plain", "role", "always"] = "plain"
    ) -> Labelled:
        parts = [(text, name) for text, name, _spec, _conv in Formatter().parse(message)]
        regex = "".join(
            re.escape(text)
            + ("" if name is None else f"(?P<{name}>.*)" if name == value else f"(?P<{name}>.+?)")
            for text, name in parts
        )
        try:
            pattern = re.compile(regex)
        except re.error:  # a translation that repeats a placeholder: it matches nothing
            pattern = re.compile(r"(?!)")
        return cls(parts, value, kind, pattern)

    def split(self, line: str) -> tuple[str, str] | None:
        """`line`'s label and value, if it's this kind of line. The label ends at the last
        colon before the value (`Due: summary for …` is labelled `Due`)."""
        found = self.pattern.fullmatch(line)
        if found is None:
            return None
        before: list[str] = []
        after: list[str] = []
        for text, name in self.parts:
            (after if after else before).append(text)
            if name == self.value:
                after.append(found[name])
            elif name is not None:
                (after if after else before).append(found[name])
        head, colon, lead = "".join(before).rpartition(":")
        if not colon:  # no colon: all of it is the label (`PC`)
            head, lead = lead, ""
        return head.strip(), (lead.lstrip() + "".join(after)).strip()


def brief_lines() -> list[Labelled]:
    """The brief's labelled lines (`didact.services.brief`), in the language in use: the same
    messages, so they match the brief whatever language it came in."""
    return [
        Labelled.of(_("Profile: {parts}"), "parts"),
        Labelled.of(_("Time: {when}"), "when"),
        Labelled.of(_("Where: {place}"), "place"),
        Labelled.of(_("Open: {quests}"), "quests"),
        Labelled.of(_("Trackers: {trackers}"), "trackers"),
        Labelled.of(_("Reminders: {reminders}"), "reminders"),
        Labelled.of(_("Scene {n}: {name}"), "name"),
        Labelled.of(_("PC {who}"), "who", "role"),
        Labelled.of(_("Companion {who}"), "who", "role"),
        Labelled.of(_("Hireling {who}"), "who", "role"),
        Labelled.of(_("Due: summary for {refs}"), "refs"),
        Labelled.of(_("Last time (session {n}): {text}"), "text"),
        Labelled.of(_("Story so far: {text}"), "text"),
        Labelled.of(_("Always: {text}"), "text", "always"),
        Labelled.of(_("In play (GM):")),
        Labelled.of(_("Off-screen lately (GM):")),
    ]


def brief_rows(text: str, names: dict[str, str]) -> Html:
    """The brief (`didact brief`) as a list: a label beside each fact, records as links, a
    character's numbers as chips, the standing guidance and the GM's notes as lists. Its first
    line (world, campaign, session) is left out: the chips above say it."""
    kinds = brief_lines()
    hidden = _("(secrets hidden; `--gm` shows them)")
    rows: list[Html] = []
    notes: list[Html] = []
    lines = text.strip().splitlines()[1:]
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        if line == hidden or (line.startswith("(") and line.endswith(")")):
            said = _("secrets hidden: the GM view shows them") if line == hidden else line[1:-1]
            notes.append(h(t'<p class="dim small">{inline(said)}</p>'))
            continue
        kind, found = next(
            ((k.kind, split) for k in kinds if (split := k.split(line)) is not None),
            ("plain", None),
        )
        if found is None:
            rows.append(
                h(t'<div class="brief-row"><span></span><span>{_linked(line, names)}</span></div>')
            )
            continue
        label, value = found
        items: list[str] = []
        while i < len(lines) and lines[i].startswith("- "):  # a list under this label
            items.append(lines[i][2:])
            i += 1
        if kind == "always":  # the standing guidance: one point each
            head, _sep, rest = value.partition(": ")
            points = [p.strip().rstrip(".") for p in (rest or head).split("; ") if p.strip()]
            title = h(t"<strong>{head}</strong>") if rest else None
            listed = [h(t"<li>{inline(point)}</li>") for point in points]
            notes.insert(0, h(t'<div class="brief-always">{title}<ul>{listed}</ul></div>'))
            continue
        if kind == "role" and " · " in value:  # a character: name, then numbers
            who, *stats = value.split(" · ")
            chips = [chip(s) for s in stats]
            shown = h(t'{_linked(who, names)}<span class="chips">{chips}</span>')
        else:
            shown = _linked(value, names)
        listed = [h(t"<li>{_linked(item, names)}</li>") for item in items]
        more = h(t'<ul class="brief-list">{listed}</ul>') if listed else None
        rows.append(
            h(
                t'<div class="brief-row"><span class="brief-label">{label}</span>'
                t"<span>{shown}{more}</span></div>"
            )
        )
    return h(t'<div class="brief">{rows}</div>{notes}')


def _linked(text: str, names: dict[str, str]) -> Html:
    """Markdown for one fact, with `Name [type:slug]` (or a bare `[type:slug]`) as a link."""

    def link(match: re.Match[str]) -> str:
        return f"[{match[1]}]({record_url(match[1])})"

    for ref, name in names.items():
        text = text.replace(f"{name} [{ref}]", f"[{name}]({record_url(ref)})")
    return inline(REF.sub(link, text))


def quick_actions(req: Request) -> Html:
    sessions = as_list(req.run("session", "list", gm=True).data.get("sessions"))
    open_session = bool(sessions) and as_dict(sessions[-1]).get("status") == "open"
    oracle = req.run("oracle", "show")  # the one `ask` asks: its odds, as it names them
    oracles = as_list(req.run("oracle", "list").data.get("oracles")) if oracle.ok else []
    dice = entry("w", placeholder=_("e.g. 2d6+1, 4d6kh3, d20"), label=_("Dice"), required=True)
    roll = run_form(
        req,
        h(t"{dice}{button(_('Roll'), kind='suggested', icon_name='hexagon')}"),
        fields={"action": "words", "w": "roll"},
        panel=True,
        cls="action-row",
    )
    rows = [form_row(_("Roll dice"), roll)]
    if oracles:
        question = entry(
            "w", placeholder=_("a yes/no question"), label=_("Question"), required=True
        )
        named = [str(o) for o in as_list(oracle.data.get("odds"))] or list(ODDS)
        likely = [("", _("(odds: as usual)")), *((o, o.replace("-", " ")) for o in named)]
        odds = select("o:--odds", likely, label=_("Odds"))
        go = button(_("Ask"), kind="suggested", icon_name="help-circle")
        ask = run_form(
            req,
            h(t"{question}{odds}{go}"),
            fields={"action": "words", "w": "ask"},
            panel=True,
            cls="action-row",
        )
        said = str(oracle.data.get("title") or oracle.data.get("oracle") or "")
        rows.append(form_row(_("Ask the oracle"), ask, subtitle=said or None))
    if open_session:
        kinds = select(
            "w", [(k, labels.beat_name(k)) for k in _log_kinds()], "action", label=_("Kind")
        )
        text = entry("w", placeholder=_("what happened, in a line"), label=_("Beat"), required=True)
        beat = run_form(
            req,
            h(t"{kinds}{text}{button(_('Log'), icon_name='edit-3')}"),
            fields={"action": "words", "w": "log"},
            cls="action-row",
        )
        rows.append(form_row(_("Journal beat"), beat))
        title = entry("w", placeholder=_("its title"), label=_("Scene title"))
        scene = run_form(
            req,
            h(t"{title}{button(_('New scene'), icon_name='film')}"),
            fields={"action": "words", "w": ["scene", "new"]},
            cls="action-row",
        )
        rows.append(form_row(_("Next scene"), scene))
        session = words_form(req, ["session", "end"], _("End session"), icon_name="square")
    else:
        session = words_form(
            req, ["session", "start"], _("Start session"), icon_name="play", kind="suggested"
        )
    new = link_button("/records/new", _("New record"), icon_name="plus")
    return group(_("Play"), boxed_list(rows), suffix=h(t"{session}{new}"))


def _log_kinds() -> list[str]:
    spec = REGISTRY.get("log")
    kinds = next((p.choices for p in spec.params if p.name == "kind"), None) if spec else None
    return list(kinds or ("action", "result", "note"))


def recent(req: Request) -> Html:
    history = req.run("history", "--limit", "6")
    names = {} if req.gm else record_index(req).names  # the player view names known records only
    rows: list[Html] = []
    for item in as_list(history.data.get("events")):
        event = as_dict(item)
        undone = chip(_("undone"), kind="dim") if event.get("undone") else None
        when = str(event.get("ts", ""))[:16].replace("T", " ")
        subtitle = f"#e{event.get('seq')} · {when}"
        rows.append(row(change_title(req, event, names), subtitle=subtitle, suffix=undone))
    undo = words_form(req, ["undo"], _("Undo"), icon_name="rotate-ccw", kind="flat")
    more = link_button("/library#history", _("All changes"), kind="flat")
    return group(
        _("Recent changes"),
        boxed_list(rows, empty=_("No changes yet.")),
        suffix=h(t"{undo}{more}"),
    )
