"""The campaign in Lonelog notation (lonelog.itch.io, CC BY-SA 4.0), the solo-play journal format.

Each session's beats in order, with their marks (`@` action, `?` oracle, `d:` roll, `->`
result, `=>` consequence), scenes as `S1`, `S2`, and the records a beat is about as tags:
`[N:Old Tom]`, `[L:The Mill]`, `[PC:Freya]`, `[Thread:…]`, `[Clock:…]`. Rolls sit where they
were made, a roll a beat names just before it (an oracle's answer stands for its dice). It's
what the players know: no secret beats, scenes, records, or the rolls only a secret beat names.
"""

from collections.abc import Mapping

from didact.core.errors import DidactError, InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.services import knowledge, play
from didact.store.events import Event, undone_seqs
from didact.store.repo import Repo

TAGS = {"npc": "N", "loc": "L", "pc": "PC", "thread": "Thread", "quest": "Thread", "track": "Clock"}


def document(repo: Repo) -> str:
    """The active campaign's journal as one Lonelog document."""
    from didact.services import dice

    campaign = repo.active_campaign()
    if campaign is None:
        raise InvalidError(
            _("a journal belongs to a campaign"), hint=_("`didact campaign open <id>`")
        )
    hidden = knowledge.unknown(repo)
    scope, _unused = dice.roll_scope(repo)
    undone = undone_seqs(repo.log.all())
    rolls = [e for e in dice.roll_events(repo, scope=scope) if e.seq not in undone]
    parts = [
        f"# {campaign.name}",
        _(
            "Lonelog: @ action, ? oracle, d: roll, -> result, => consequence; tags: [N:] "
            "people, [L:] places, [PC:] characters, [Thread:] threads, [Clock:] clocks."
        ),
    ]
    current = play.load(repo)
    for number in range(1, current.session + 1):
        record = play.session_record(repo, number)
        title = play.title_of(record, _("Session {n}", n=number), gm=False)
        parts.append(f"## {title}")
        lines = _session(repo, number, rolls, hidden)
        parts.append("\n".join(lines) if lines else _("(nothing was written down)"))
    return "\n\n".join(parts) + "\n"


def _session(repo: Repo, number: int, rolls: list[Event], hidden: knowledge.Unknown) -> list[str]:
    beats = play.beats(repo, number)
    named = {_label(r) for b in beats for r in _listed(b.get("rolls"))}
    kept = {_label(r) for b in beats if play.visible(b, gm=False) for r in _listed(b.get("rolls"))}
    by_label = {f"#r{_number(e)}": e for e in rolls}
    entries: list[tuple[int, int | None, list[str]]] = []  # (order, scene, lines)
    for event in rolls:
        if event.data.get("session") != number or f"#r{_number(event)}" in named:
            continue  # another session's, or it goes with the beat that names it
        entries.append((event.seq, _scene(event.data), [_roll_line(event)]))
    for beat in beats:
        if not play.visible(beat, gm=False):
            continue
        shown = (
            [] if beat.get("kind") == "oracle" else _listed(beat.get("rolls"))
        )  # the answer says it
        lines = [
            _roll_line(by_label[_label(r)])
            for r in shown
            if _label(r) in kept
            and _label(r) in by_label
            and by_label[_label(r)].data.get("kind") != "report"
        ]
        lines.append(play.beat_line(beat) + _tags(repo, beat, hidden))
        seq = beat.get("seq")
        entries.append((seq if isinstance(seq, int) else 0, _scene(beat), lines))
    entries.sort(key=lambda e: e[0])
    out: list[str] = []
    scene: int | None = None
    for _order, at, lines in entries:
        if at is not None and at != scene:
            scene = at
            record = play.scene_record(repo, at)
            name = play.title_of(record, "", gm=False)
            out += ["", f"S{at} *{name}*" if name else f"S{at}"]
        out += lines
    return out[1:] if out[:1] == [""] else out


def _roll_line(event: Event) -> str:
    label, _space, rest = event.summary.partition(" ")
    return f"d: {rest} ({label})" if label.startswith("#r") and rest else f"d: {event.summary}"


def _tags(repo: Repo, beat: Mapping[str, JSON], hidden: knowledge.Unknown) -> str:
    tags: list[str] = []
    for ref in _listed(beat.get("about")):
        if str(ref) in hidden.ids:
            continue
        try:
            entity = repo.resolve(str(ref)).entity
        except DidactError:
            continue  # gone since
        prefix = TAGS.get(entity.id.type)
        if prefix is not None:
            tags.append(f"[{prefix}:{entity.name}]")
    return (" " + " ".join(tags)) if tags else ""


def _label(raw: JSON) -> str:
    """A beat's roll as `#r12` (older beats may say `r12`)."""
    return "#" + str(raw).lstrip("#")


def _scene(data: Mapping[str, JSON]) -> int | None:
    scene = data.get("scene")
    return scene if isinstance(scene, int) else None


def _number(event: Event) -> int:
    value = event.data.get("roll")
    return value if isinstance(value, int) else 0


def _listed(raw: JSON) -> list[JSON]:
    return raw if isinstance(raw, list) else []
