"""The brief: a compact picture of the game right now, for (re)starting play.

Vale / "The Withering" (my-system) · session 4 · scene 12 (open)
Scene 12: Amber Grave: a sap pool with a trapped spirit
PC Freya [pc:freya] · STR 11/13 · DEX 14 · hp 2/4 · armor 1
Due: summary for scene:11
Last time: …
"""

from dataclasses import dataclass, field

from didact.core import labels
from didact.core.errors import DidactError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.services import play, sheets
from didact.store.entity import Entity
from didact.store.repo import Repo

EXCERPT = 400


@dataclass(slots=True)
class Brief:
    lines: list[str] = field(default_factory=list)
    data: dict[str, JSON] = field(default_factory=dict)


def build(repo: Repo, *, gm: bool) -> Brief:
    out = Brief()
    world = repo.active_world()
    campaign = repo.active_campaign()
    if world is None:
        out.lines.append(_("no world yet: `didact world new <id>`"))
        return out
    system = sheets.active_system(repo)
    head = (
        world.name
        + (f' / "{campaign.name}"' if campaign else "")
        + (f" ({system})" if system else "")
    )
    current = play.load(repo)
    if campaign is not None and current.session:
        if current.session_open:
            head = _("{head} · session {n} (open)", head=head, n=current.session)
        else:
            head = _("{head} · session {n} (closed)", head=head, n=current.session)
        if current.scene and current.scene_open:
            head = _("{head} · scene {n} (open)", head=head, n=current.scene)
        elif current.scene:
            head = _("{head} · scene {n}", head=head, n=current.scene)
    out.lines.append(head)
    out.data |= {"world": world.id, "campaign": campaign.id if campaign else None, "system": system}
    if campaign is not None:
        from didact.services import options, profile

        saved = profile.load(campaign)
        declared = frozenset(o.id for o in options.declared(repo))
        out.lines.append(
            profile.line(saved, skip=declared)
            if saved
            else _("Profile: not set yet (`didact session zero`)")
        )
        out.data["profile"] = saved
        changed = options.changed(repo)  # the system's rules as this campaign plays them
        for option, value in changed:
            meaning = option.meaning(value)
            said = options.shown(value)
            out.lines.append(
                _("Option {key}={value}: {meaning}", key=option.id, value=said, meaning=meaning)
                if meaning
                else _("Option {key}={value}", key=option.id, value=said)
            )
        out.data["options"] = {option.id: value for option, value in changed}
    out.data |= {"session": current.session, "scene": current.scene}
    if campaign is not None:
        from didact.services import timeline, trackers

        cal = timeline.calendar(repo)
        out.lines.append(_("Time: {when}", when=cal.describe(current.seconds)))
        if current.location:
            try:
                place = repo.resolve(current.location).entity
                out.lines.append(_("Where: {place}", place=f"{place.name} [{place.id}]"))
            except DidactError:
                out.lines.append(
                    _("Where: {ref} (missing; `didact visit <place>`)", ref=current.location)
                )
        out.data["location"] = current.location
        quests = trackers.active(repo, trackers.QUEST_TYPES, gm=gm)
        if quests:
            listed = " · ".join(
                f"{labels.type_inline(q.type)} {trackers.quest_line(q)}" for q in quests[:8]
            )
            out.lines.append(_("Open: {quests}", quests=listed))
        tracks = trackers.active(repo, ("track",), gm=gm)
        if tracks:
            listed = " · ".join(trackers.show(t, current.seconds) for t in tracks[:8])
            out.lines.append(_("Trackers: {trackers}", trackers=listed))
        soon = [r for r in trackers.reminders(repo) if r.at <= current.seconds + cal.units["day"]]
        if soon:
            listed = " · ".join(f"{r.text} ({cal.describe(r.at)})" for r in soon[:5])
            out.lines.append(_("Reminders: {reminders}", reminders=listed))
    if campaign is not None and current.scene_open:
        scene = play.scene_record(repo, current.scene)
        if scene is not None:
            expected = scene.fields.get("expected")
            name = play.title_of(scene, _("(a scene the players haven't seen)"), gm=gm)
            if expected:
                line = _(
                    "Scene {n}: {name} ({expected})", n=current.scene, name=name, expected=expected
                )
            else:
                line = _("Scene {n}: {name}", n=current.scene, name=name)
            out.lines.append(line)
    from didact.services import party

    roster = party.members(repo, gm=gm) if campaign is not None else []
    if campaign is None:
        roster = [party.Member(pc, "pc") for pc in _records(repo, "pc", gm)]
    from didact.services import knowledge

    hid = knowledge.NOTHING if gm else knowledge.unknown(repo)
    for member in roster:
        entity = member.entity
        sh = sheets.sheet(repo, entity.type)
        shown = entity if gm else knowledge.player_copy(entity, sh, hid)[0]
        stats = sheets.stat_line(shown, sh)
        who = f"{entity.name} [{entity.id}]" + (f" · {stats}" if stats else "")
        out.lines.append(member_line(member.role, who))
    out.data["party"] = [str(m.entity.id) for m in roster]
    if campaign is not None:
        missing = play.due(repo, current)
        if missing:
            out.lines.append(_("Due: summary for {refs}", refs=", ".join(missing)))
        out.data["due"] = list[JSON](missing)
        last = current.session - (1 if current.session_open else 0)
        if last >= 1:
            text = play.summary_text(repo, f"session:{last}", gm=gm)
            if text:
                out.lines.append(_("Last time (session {n}): {text}", n=last, text=_excerpt(text)))
        story = play.summary_text(repo, "summary:campaign", gm=gm)
        if story:
            out.lines.append(_("Story so far: {text}", text=_excerpt(story)))
    if campaign is not None:
        from didact.services import lore

        always = lore.constants(repo, gm=gm)
        out.lines += [_("Always: {text}", text=hit.text) for hit in always]
        out.data["constant"] = [str(h.entity.id) for h in always]
    if gm and campaign is not None:
        noted, offstage = _in_play(repo, current, [str(m.entity.id) for m in roster])
        if noted:
            out.lines += [_("In play (GM):"), *noted]
        if offstage:
            out.lines += [_("Off-screen lately (GM):"), *offstage]
        out.data["in_play"] = list[JSON](noted)
    if not gm:
        out.lines.append(_("(secrets hidden; `--gm` shows them)"))
    return out


def member_line(role: str, who: str) -> str:
    """A party member's line: its role, then `who` (name, reference and numbers)."""
    match role:
        case "pc":
            return _("PC {who}", who=who)
        case "companion":
            return _("Companion {who}", who=who)
        case "hireling":
            return _("Hireling {who}", who=who)
        case _:
            return f"{role.capitalize()} {who}"


def _in_play(repo: Repo, current: play.PlayState, party: list[str]) -> tuple[list[str], list[str]]:
    """The GM's notes on what's in play: the place, the fighters, whoever this scene's beats are
    about, and the party (where, doing, plan, state); and the latest secret beats."""
    from didact.services import combat, details

    refs: list[str] = [current.location] if current.location else []
    fight = combat.load(repo)
    if fight is not None:
        refs += [f.ref for f in fight.order]
    beats = play.beats(repo, current.session) if current.session else []
    for beat in beats:
        about = beat.get("about")
        if isinstance(about, list) and (
            not current.scene_open or beat.get("scene") == current.scene
        ):
            refs += [str(a) for a in about]
    refs += party
    noted: list[str] = []
    for ref in dict.fromkeys(refs):
        try:
            entity = repo.resolve(ref).entity
        except DidactError:
            continue
        found = [
            f"{labels.inline(k, labels.detail_name(k))}: {_clip(entity.details[k])}"
            for k in (*details.IN_SCENE, "state")
            if k in entity.details
        ]
        if found:
            noted.append(f"- {entity.name} [{entity.id}]: " + " · ".join(found))
    offstage = [f"- {play.beat_line(b)}" for b in beats if b.get("secret")][-3:]
    return noted[:10], offstage


def _clip(text: str, width: int = 140) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= width else flat[:width].rsplit(" ", 1)[0] + "…"


def _records(repo: Repo, type_: str, gm: bool) -> list[Entity]:
    rows = repo.index().rows(repo.chain(), types=[type_])
    found: list[Entity] = []
    for row in rows:
        if row.knowledge == "secret" and not gm:
            continue
        found.append(repo.located(row).entity)
    return found


def _excerpt(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= EXCERPT else flat[:EXCERPT].rsplit(" ", 1)[0] + "…"
