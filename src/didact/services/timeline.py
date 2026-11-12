"""Moving time forward: timers expire, reminders come due, `on: time` triggers run."""

from dataclasses import dataclass, field

from didact.core.errors import DidactError
from didact.core.output import JSON
from didact.expr.model import Value
from didact.services import events, packs, play, sheets, trackers
from didact.services.clock import Calendar, calendar_from
from didact.store.changeset import Changeset
from didact.store.repo import Repo


def calendar(repo: Repo) -> Calendar:
    """The calendar here: the world's own, else an enabled setting pack's, else the system's.
    A campaign that opened on a date of its own (`start` in its `campaign.yaml`) begins there."""
    system = sheets.active_system(repo)
    settings: dict[str, JSON] = {}
    try:
        active = packs.active(repo)
    except DidactError:
        active = None
    if active is not None:
        if system and system in active.ids:
            settings = active.settings(system)
        for pack_id in active.ids:
            pack = active.get(pack_id)
            if pack.kind == "setting" and isinstance(pack.settings.get("calendar"), dict):
                settings = {**settings, **pack.settings}  # a setting's calendar wins
    world, campaign = repo.active_world(), repo.active_campaign()
    begun = campaign.other.get("start") if campaign is not None else None
    return calendar_from(settings, world.other if world is not None else {}, begun)


@dataclass(slots=True)
class Advanced:
    before: int
    after: int
    timers: list[str] = field(default_factory=list)  # in English, for the data
    expired: list[tuple[str, str]] = field(default_factory=list)  # (timer, its note), to show
    reminders: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    holidays: list[str] = field(default_factory=list)


def advance(repo: Repo, cs: Changeset, seconds: int, *, command: str | None) -> Advanced:
    current = play.load(repo)
    before, after = current.seconds, current.seconds + seconds
    current.seconds = after
    play.save(cs, current)
    done = Advanced(before, after)
    now = calendar(repo)
    for timer in trackers.expired_timers(repo, before, after):
        note = str(timer.fields.get("note") or "")
        done.timers.append(f"{timer.name} ran out" + (f": {note}" if note else ""))
        done.expired.append((timer.name, note))
    done.holidays = now.holidays_between(before // now.day_seconds, after // now.day_seconds)
    due, keep = trackers.fire_reminders(trackers.reminders(repo), after)
    if due or len(keep) != len(trackers.reminders(repo)):
        trackers.save_reminders(cs, keep)
    done.reminders = [r.text for r in due]
    preset: dict[str, Value] = now.values(after) | {"time.passed": seconds}
    done.triggers = events.fire(repo, cs, "time", preset, command=command)
    return done
