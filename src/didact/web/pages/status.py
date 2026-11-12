"""Status: where things stand, at a glance, for anyone at the table.

The session and scene, the time and what's coming, the party (their numbers and what they
carry), the fight, open quests and trackers, and where the party is on the map. Numbers can
be nudged right here: every change runs a real command, so it's logged and undoable. Like
every page, it shows what the players know unless the GM view is on.
"""

from didact.core import labels
from didact.core.i18n import _, ngettext, pgettext
from didact.core.output import JSON
from didact.web.app import Request, Response
from didact.web.forms import time_amount
from didact.web.html import (
    Html,
    boxed_list,
    button,
    chip,
    datalist,
    entry,
    form_row,
    group,
    h,
    icon,
    link_button,
    record_url,
    row,
    select,
    status_page,
)
from didact.web.layout import failure, page, result_panel, run_form, words_form
from didact.web.pages.common import Index, as_dict, as_list, record_index
from didact.web.pages.records import NUMERIC_KINDS

NOTES = ("where", "doing", "plan")  # the GM's notes worth seeing in a fight
PEOPLE = ("pc", "npc", "character")  # the records offered to join the party


def show(req: Request) -> Response:
    flash = req.take_flash()
    brief = req.run("brief", gm=True)
    parts: list[Html | None] = [result_panel(req, flash.ran) if flash else None]
    if not brief.ok:
        parts.append(failure(brief))
    elif not brief.data.get("campaign"):
        parts.append(
            status_page(
                "activity",
                _("No campaign in play"),
                _(
                    "Status shows a campaign as it stands: the party, the time, the fight and the "
                    "map. Start or pick one in the Library."
                ),
                link_button("/library", _("Open the Library"), kind="suggested pill"),
            )
        )
    else:
        found = record_index(req)
        names = found.names
        parts += [
            _now(req, as_dict(brief.data), names),
            _party(req, found),
            _fight(req, names),
            _plans(req),
            _nearby(req, names),
        ]
    return page(req, _("Status"), h(t"{parts}"), nav="status")


# ---------------------------------------------------------------------------- now


def _now(req: Request, brief: dict[str, JSON], names: dict[str, str]) -> Html:
    """The session and scene, where the party is, the time and what's coming."""
    rows: list[Html] = []
    session, scene = brief.get("session"), brief.get("scene")  # 0: none yet
    if session:
        title = names.get(f"session:{session}") or _("Session {n}", n=session)
        rows.append(row(title, subtitle=_("the session"), href=f"/journal/{session}"))
    if scene:
        title = names.get(f"scene:{scene}") or _("Scene {n}", n=scene)
        rows.append(row(title, subtitle=_("scene {n}", n=scene)))
    place = brief.get("location")
    if isinstance(place, str) and place in names:
        rows.append(row(names[place], subtitle=_("where the party is"), href=record_url(place)))
    time = req.run("time", "show")
    units = [str(u) for u in as_dict(time.data.get("units"))] if time.ok else []
    if time.ok:
        when = str(time.data.get("text") or "")
        advance = run_form(
            req,
            h(
                t"{time_amount('w', units, amount='1', required=True)}"
                t"{button(_('Advance'), icon_name='clock')}"
            ),
            fields={"action": "words", "w": ["time", "advance"]},
            cls="action-row",
        )
        rows.append(row(when, subtitle=_("the time"), suffix=advance, cls="is-form"))
    reminders = req.run("remind", "--list")
    for item in as_list(reminders.data.get("reminders")):
        reminder = as_dict(item)
        number = str(reminder.get("n"))
        cancel = words_form(
            req,
            ["remind", "--cancel", number],
            "",
            icon_name="x",
            title=_("Cancel this reminder"),
            kind="flat circular",
        )
        when = str(reminder.get("when") or "")
        rows.append(
            row(
                str(reminder.get("text") or ""),
                subtitle=_("reminder · {when}", when=when),
                suffix=cancel,
            )
        )
    if units:  # a reminder: what, and when (once after a while, or every so often)
        text = entry("text", placeholder=_("e.g. Eat a ration"), label=_("Reminder"), required=True)
        how = select(
            "when",
            [("in", pgettext("reminder", "once, after")), ("every", pgettext("reminder", "every"))],
            "in",
            label=_("How often"),
        )
        when = time_amount("amount", units, amount="1", required=True, unit_name="unit")
        remind = run_form(
            req,
            h(t"{text}{how}{when}{button(_('Remind'), icon_name='bell')}"),
            fields={"action": "remind"},
            cls="action-row",
        )
        about = _("it comes due as game time passes")
        rows.append(form_row(_("Set a reminder"), remind, subtitle=about))
    if not rows:
        return group(_("Now"), h(t'<p class="dim">{_("No session yet.")}</p>'))
    return group(_("Now"), boxed_list(rows), id_="now")


# ---------------------------------------------------------------------------- the party


def _party(req: Request, found: Index) -> Html:
    party = req.run("party", "show", gm=True)
    if not party.ok:
        return group(_("Party"), failure(party))
    members = [as_dict(m) for m in as_list(party.data.get("members"))]
    if not members:
        who = entry(
            "w", placeholder=_("a character"), label=_("Who joins"), required=True,
            list_="characters",
        )  # fmt: skip
        people = datalist(
            "characters",
            ((r.id, f"{r.name} ({r.type})") for r in found.records if r.type in PEOPLE),
        )
        add = run_form(
            req,
            h(t"{who}{people}{button(_('Add to the party'), icon_name='user-plus')}"),
            fields={"action": "words", "w": ["party", "add"]},
            cls="action-row",
        )
        empty = _("No one in the party yet.")
        return group(_("Party"), h(t'<p class="dim">{empty}</p>{add}'), id_="party")
    cards = [_member(req, member) for member in members]
    items = datalist(  # what can be added to what they carry: the items here
        "known-items", ((r.name, r.id) for r in found.records if r.type == "item")
    )
    return group(_("Party"), h(t'<div class="cards">{cards}</div>{items}'), id_="party")


def _member(req: Request, member: dict[str, JSON]) -> Html:
    """One member: who, what they look like, their numbers (with − and +), their conditions
    and what they carry."""
    ref = str(member.get("id"))
    shown = req.run("show", ref, gm=True)
    data = as_dict(shown.data) if shown.ok else {}
    looks = as_dict(data.get("details")).get("looks")
    seen = h(t'<p class="dim small">{looks}</p>') if looks else None
    role = chip(labels.party_role(str(member.get("role") or "")), kind="dim")
    tiles = [_stat(req, ref, as_dict(s)) for s in as_list(member.get("stats"))]
    grid = h(t'<div class="tiles">{tiles}</div>') if tiles else None
    conditions = [
        chip(str(c), kind="warning", icon_name="alert-circle")
        for c in as_list(as_dict(data.get("values")).get("conditions"))
    ]
    states = h(t'<div class="chips">{conditions}</div>') if conditions else None
    return h(
        t'<section class="card member"><div class="member-head">'
        t'<a class="member-name" href="{record_url(ref)}">{member.get("name") or ref}</a>{role}'
        t"</div>{seen}{grid}{states}{_carried(req, ref)}</section>"
    )


def _stat(req: Request, ref: str, stat: dict[str, JSON]) -> Html:
    key, kind = str(stat.get("key")), str(stat.get("kind"))
    steps = None
    if kind in NUMERIC_KINDS:  # stored numbers step up and down; derived ones follow
        minus = _step(req, ref, key, "-=", "minus", f"{stat.get('label')} − 1")
        plus = _step(req, ref, key, "+=", "plus", f"{stat.get('label')} + 1")
        steps = h(t'<div class="tile-steps">{minus}{plus}</div>')
    about = stat.get("help")
    said = h(t' title="{about}"') if isinstance(about, str) and about else None  # the sheet's
    return h(
        t'<div class="tile"{said}><span class="tile-label">{stat.get("label")}</span>'
        t'<span class="tile-value">{stat.get("text")}</span>{steps}</div>'
    )


def _step(req: Request, ref: str, key: str, op: str, pic: str, title: str) -> Html:
    return run_form(
        req,
        button("", icon_name=pic, title=title, kind="flat circular"),
        fields={"action": "set", "ref": ref, "key": key, "op": op, "value": "1"},
        cls="inline",
    )


def _carried(req: Request, ref: str) -> Html | None:
    """What a member carries, with use and drop, and a box to add something."""
    inv = req.run("inv", "show", ref, gm=True)
    if not inv.ok:
        return None
    rows: list[Html] = []
    grouped = as_dict(inv.data.get("groups"))
    lists = [(None, as_list(inv.data.get("items"))), *((g, as_list(i)) for g, i in grouped.items())]
    for where, items in lists:
        for raw in items:
            item: dict[str, JSON] = as_dict(raw) if isinstance(raw, dict) else {"name": str(raw)}
            rows.append(_item(req, ref, item, where))
    used, capacity = inv.data.get("used"), inv.data.get("capacity")
    title = (
        _("Carrying · {used} of {capacity}", used=used, capacity=capacity)
        if capacity is not None
        else _("Carrying")
    )
    what = entry(
        "w", placeholder=_("an item"), label=_("Item to add"), required=True, list_="known-items"
    )
    add = run_form(
        req,
        h(t"{what}{button('', icon_name='plus', title=_('Add it'), kind='flat circular')}"),
        fields={"action": "words", "w": ["inv", "add", ref]},
        cls="action-row",
    )
    return h(
        t'<div class="member-carried"><p class="dim small">{title}</p>'
        t"{boxed_list(rows, empty=_('Nothing carried.'))}{add}</div>"
    )


def _item(req: Request, ref: str, item: dict[str, JSON], where: str | None) -> Html:
    name = str(item.get("name") or "")
    uses = as_dict(item.get("uses"))
    count = item.get("count")
    about = [
        f"×{count}" if isinstance(count, int) and count > 1 else None,
        _("{value}/{max} uses", value=uses.get("value"), max=uses.get("max")) if uses else None,
        _("in {where}", where=where) if where else None,
    ]
    subtitle = " · ".join(a for a in about if a) or None
    use = None
    if uses:
        use = words_form(
            req, ["inv", "use", ref, name], "", icon_name="zap", title=_("Use {name}", name=name),
            kind="flat circular",
        )  # fmt: skip
    drop = words_form(
        req, ["inv", "drop", ref, name], "", icon_name="x", title=_("Drop {name}", name=name),
        kind="flat circular",
    )  # fmt: skip
    return row(name, subtitle=subtitle, suffix=h(t"{use}{drop}"))


# ---------------------------------------------------------------------------- the fight


def _fight(req: Request, names: dict[str, str]) -> Html | None:
    ran = req.run("combat", "status", gm=True)
    fight = as_dict(ran.data.get("combat")) if ran.ok else {}
    if not fight.get("active"):
        return None
    order = [as_dict(f) for f in as_list(fight.get("order"))]
    turn, sides = fight.get("turn"), [str(s) for s in as_list(fight.get("sides"))]
    up_side = up_ref = None
    if isinstance(turn, int):
        if fight.get("mode") == "sides" and turn < len(sides):
            up_side = sides[turn]
        elif turn < len(order):
            up_ref = str(order[turn].get("ref"))
    conditions = [as_dict(c) for c in as_list(fight.get("conditions"))]
    rows: list[Html] = []
    for fighter in order:
        ref, side = str(fighter.get("ref")), str(fighter.get("side") or "")
        name = str(fighter.get("name") or names.get(ref) or ref)
        title = h(t'<a href="{record_url(ref)}">{name}</a>') if ref in names else name
        marks = [
            chip(_condition(str(c.get("name")), c.get("rounds")), kind="warning")
            for c in conditions
            if c.get("ref") == ref
        ]
        subtitle = " · ".join(filter(None, [side, _notes(req, ref) if req.gm else None]))
        current = side == up_side or ref == up_ref
        rows.append(
            row(
                title,
                subtitle=subtitle or None,
                suffix=h(t"{marks}"),
                prefix=icon("chevron-right") if current else None,
                cls="is-current" if current else "",
            )
        )
    up = up_side or next((str(f.get("name")) for f in order if f.get("ref") == up_ref), "")
    return group(
        _("The fight · round {n}", n=fight.get("round")),
        boxed_list(rows),
        description=_("Now: {who}", who=up) if up else None,
        id_="fight",
    )


def _condition(name: str, rounds: JSON) -> str:
    if not rounds:
        return name
    if isinstance(rounds, int):
        return ngettext(
            "{name} · {n} rounds", "{name} · {n} rounds", rounds, name=name
        )  # English says "rounds" even for one
    return _("{name} · {rounds} rounds", name=name, rounds=rounds)


def _notes(req: Request, ref: str) -> str | None:
    """Where a fighter is, what they're doing and planning: the GM's notes."""
    shown = req.run("show", ref, gm=True)
    details = as_dict(shown.data.get("details")) if shown.ok else {}
    found = [f"{name}: {details[name]}" for name in NOTES if details.get(name)]
    return " · ".join(found) or None


# ---------------------------------------------------------------------------- quests, trackers


def _plans(req: Request) -> Html | None:
    rows: list[Html] = []
    quests = req.run("quest", "list", gm=True)
    for raw in as_list(quests.data.get("quests")):
        quest = as_dict(raw)
        quest_id = str(quest.get("id"))
        done = words_form(req, ["quest", "done", quest_id], _("Done"), icon_name="check")
        title = h(t'<a href="{record_url(quest_id)}">{quest.get("line") or quest_id}</a>')
        rows.append(row(title, subtitle=str(quest.get("type") or _("quest")), suffix=done))
    tracks = req.run("track", "list", gm=True)
    for raw in as_list(tracks.data.get("tracks")):
        rows.append(_tracker(req, as_dict(raw)))
    if not rows:
        return None
    return group(_("Quests and trackers"), boxed_list(rows), id_="plans")


def _tracker(req: Request, track: dict[str, JSON]) -> Html:
    track_id = str(track.get("id"))
    value = track.get("value")
    meter = None
    if isinstance(value, dict):
        now, size = value.get("value"), value.get("size", value.get("max"))
        if isinstance(now, int | float) and isinstance(size, int | float) and size > 0:
            meter = h(
                t'<progress class="meter" value="{max(0, min(now, size))}" max="{size}">'
                t"{_('{now} of {size}', now=now, size=size)}</progress>"
            )
    back = words_form(
        req, ["track", "tick", track_id, "--by", "-1"], "", icon_name="minus",
        title=_("Take one back"), kind="flat circular",
    )  # fmt: skip
    tick = words_form(
        req, ["track", "tick", track_id], "", icon_name="plus", title=_("Tick it"),
        kind="flat circular",
    )  # fmt: skip
    title = h(t'<a href="{record_url(track_id)}">{track.get("text") or track_id}</a>')
    kind = str(track.get("kind") or _("tracker"))
    return row(title, subtitle=kind, suffix=h(t"{meter}{back}{tick}"))


# ---------------------------------------------------------------------------- the map


def _nearby(req: Request, names: dict[str, str]) -> Html | None:
    """Where the party is, the ways out, and how much of the world it has seen."""
    ran = req.run("map", gm=True)
    places = [as_dict(p) for p in as_list(ran.data.get("places"))] if ran.ok else []
    if not places:
        return None
    by_id = {str(p.get("id")): p for p in places}
    here = by_id.get(str(ran.data.get("here")))
    rows: list[Html] = []
    if here is None:
        rows.append(
            row(_("The party isn't anywhere yet"), subtitle=_("a visit puts it on the map"))
        )
    else:
        place_id = str(here.get("id"))
        region = here.get("region")
        where = (
            _("where the party is · in {region}", region=names.get(region, region))
            if isinstance(region, str)
            else _("where the party is")
        )
        rows.append(
            row(
                h(t'<a href="{record_url(place_id)}">{here.get("name") or place_id}</a>'),
                subtitle=where,
                prefix=icon("map-pin"),
            )
        )
        for raw in as_list(here.get("exits")):
            exit_ = as_dict(raw)
            to = exit_.get("to")
            known = isinstance(to, str) and to in by_id
            target = (
                h(t'<a href="{record_url(str(to))}">{by_id[str(to)].get("name") or to}</a>')
                if known
                else "?"
            )
            rows.append(
                row(
                    h(t"{exit_.get('how') or _('a way')} → {target}"),
                    prefix=icon("corner-down-right"),
                )
            )
    visited = sum(1 for p in places if p.get("state") in ("here", "visited"))
    seen = ngettext(
        "{visited} of {n} known places visited",
        "{visited} of {n} known places visited",
        len(places),
        visited=visited,
    )  # English says "places" even for one
    open_map = link_button("/graph?mode=map", _("Open the map"), icon_name="map")
    return group(
        _("Where the party is"), boxed_list(rows), description=seen, suffix=open_map, id_="map"
    )
