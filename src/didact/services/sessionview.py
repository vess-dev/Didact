"""A session rendered for reading: scenes in order, each with its beats and rolls interleaved."""

from dataclasses import dataclass

from didact.core import labels
from didact.core.i18n import _, ngettext
from didact.core.output import JSON
from didact.services import play
from didact.store.events import undone_seqs
from didact.store.repo import Repo


@dataclass(frozen=True, slots=True)
class Entry:
    order: int  # the event that wrote it: beats and rolls sort into the order they happened
    ts: str
    scene: int | None
    text: str
    kind: str = "roll"  # a beat's kind, or "roll"
    secret: bool = False  # a beat out of the players' sight (GM views only)


def hidden_beats(repo: Repo, number: int) -> int:
    """How many of a session's beats a player view leaves out."""
    return sum(1 for beat in play.beats(repo, number) if not play.visible(beat, gm=False))


def entries(repo: Repo, number: int, *, gm: bool = False) -> list[Entry]:
    found: list[Entry] = []
    for beat in play.beats(repo, number):
        if not play.visible(beat, gm):
            continue
        where, order = beat.get("scene"), beat.get("seq")
        found.append(
            Entry(
                order if isinstance(order, int) else 0,
                str(beat.get("ts")),
                where if isinstance(where, int) else None,
                f"{beat.get('id')} {play.beat_line(beat)}",
                str(beat.get("kind") or "note"),
                bool(beat.get("secret")),
            )
        )
    events = repo.log.all()
    undone = undone_seqs(events)
    for event in events:
        if event.kind != "roll" or event.data.get("session") != number:
            continue
        if (event.reason or "").startswith("name:"):
            continue  # name candidates on offer: rolled and logged, but not part of the story
        where = event.data.get("scene")
        text = _("{line} (undone)", line=event.summary) if event.seq in undone else event.summary
        found.append(Entry(event.seq, event.ts, where if isinstance(where, int) else None, text))
    found.sort(key=lambda e: (e.order, e.ts))
    return found


def render(
    repo: Repo, number: int, *, full: bool, gm: bool = False
) -> tuple[list[str], dict[str, JSON]]:
    record = play.session_record(repo, number)
    title = play.title_of(record, f"Session {number}", gm=gm)  # English in the data
    shown = play.title_of(record, _("Session {n}", n=number), gm=gm)
    status = str(record.fields.get("status", "")) if record is not None else "unknown"
    said = labels.inline(status, labels.session_status(status))
    lines = [_("# Session {n} · {title} ({status})", n=number, title=shown, status=said)]
    summary = play.summary_of(record.body, gm=gm) if record is not None else ""
    if summary:
        lines += ["", _("Summary: {summary}", summary=summary)]
    items = entries(repo, number, gm=gm)
    listed = record.fields.get("scenes") if record is not None else None
    scenes = [s for s in listed if isinstance(s, int)] if isinstance(listed, list) else []
    loose = [e for e in items if e.scene is None]
    if loose:
        lines += ["", *(_line(e) for e in loose)]
    about_scenes: list[JSON] = []
    for scene_number in scenes:
        scene = play.scene_record(repo, scene_number)
        name = play.title_of(scene, f"Scene {scene_number}", gm=gm)  # English in the data
        shown_name = play.title_of(scene, _("Scene {n}", n=scene_number), gm=gm)
        lines += ["", _("## Scene {n} · {name}", n=scene_number, name=shown_name)]
        scene_summary = play.summary_of(scene.body, gm=gm) if scene is not None else ""
        if scene_summary:
            lines.append(_("Summary: {summary}", summary=scene_summary))
        lines += [_line(e) for e in items if e.scene == scene_number]
        about_scenes.append({"scene": scene_number, "title": name, "summary": scene_summary})
    if full:
        transcript = repo.read_text(play.transcript_path(repo, number))
        if transcript:
            lines += ["", transcript.rstrip()]
    data: dict[str, JSON] = {
        "session": number,
        "title": title,
        "status": status,
        "summary": summary,
        "scenes": list[JSON](scenes),
        "scene_info": about_scenes,
        "entries": [_entry_data(e) for e in items],
    }
    if not gm:
        hidden = hidden_beats(repo, number)
        if hidden:
            data["hidden"] = hidden
            lines.append(
                ngettext(
                    "({n} secret beat hidden; --gm)", "({n} secret beats hidden; --gm)", hidden
                )
            )
    return lines, data


def _line(entry: Entry) -> str:
    return _("- {text} (GM)", text=entry.text) if entry.secret else f"- {entry.text}"


def _entry_data(entry: Entry) -> JSON:
    data: dict[str, JSON] = {
        "ts": entry.ts,
        "scene": entry.scene,
        "text": entry.text,
        "kind": entry.kind,
    }
    if entry.secret:
        data["secret"] = True
    return data
