"""The campaign as a story: a readable book of its sessions, and a timeline by in-game date.

The book puts each session's summary before its transcript (or, with no transcript, its
journal beats). The timeline lists the journal's beats under the in-game day they happened.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.services import play
from didact.store.repo import Repo


def book(repo: Repo) -> str:
    campaign = repo.active_campaign()
    if campaign is None:
        raise InvalidError(
            _("a story belongs to a campaign"), hint=_("`didact campaign open <id>`")
        )
    parts = [f"# {campaign.name}"]
    overall = play.summary_text(repo, "summary:campaign", gm=False)
    if overall:
        parts.append(f"*{overall}*")
    current = play.load(repo)
    for number in range(1, current.session + 1):
        record = play.session_record(repo, number)
        parts.append(f"## {play.title_of(record, _('Session {n}', n=number), gm=False)}")
        summary = play.summary_of(record.body, gm=False) if record is not None else ""
        if summary:
            parts.append(f"*{summary}*")
        path = play.transcript_path(repo, number)
        transcript = path.read_text(encoding="utf-8") if path.is_file() else ""
        body = "\n".join(
            line for line in transcript.splitlines() if not line.startswith("# Session ")
        ).strip()
        if body:
            parts.append(body)
        else:
            beats = [b for b in play.beats(repo, number) if play.visible(b, gm=False)]
            lines = [_beat_line(b) for b in beats]
            parts.append("\n".join(lines) if lines else _("(nothing was written down)"))
    return "\n\n".join(parts) + "\n"


def _beat_line(beat: Mapping[str, object]) -> str:
    mark = play.BEAT_KINDS.get(str(beat.get("kind")), "")
    return f"- {mark + ' ' if mark else ''}{beat.get('text')}"


@dataclass(frozen=True, slots=True)
class Written:
    """A beat on the timeline: its line, and the session and scene it was written in."""

    text: str
    session: int
    scene: int | None

    def where(self, scene: str = "scene") -> str:
        """`S1 scene 2` (the word for a scene given), or `S1`."""
        return f"S{self.session}" + (f" {scene} {self.scene}" if self.scene is not None else "")


def timeline(repo: Repo) -> list[tuple[int, str, list[Written]]]:
    """(in-game day, counted from 1; its date, if the calendar has them; the beats of that day),
    in order."""
    from didact.services import timeline as clock_service

    calendar = clock_service.calendar(repo)
    current = play.load(repo)
    days: dict[int, list[Written]] = {}
    for number in range(1, current.session + 1):
        for beat in play.beats(repo, number):
            if not play.visible(beat, gm=False):
                continue  # the players' timeline
            seconds = beat.get("time")
            day = seconds // calendar.day_seconds if isinstance(seconds, int) else 0
            scene = beat.get("scene")
            written = Written(
                _beat_line(beat)[2:], number, scene if isinstance(scene, int) else None
            )
            days.setdefault(day, []).append(written)
    return [(day + 1, calendar.date(day), days[day]) for day in sorted(days)]
