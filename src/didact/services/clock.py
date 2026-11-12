"""In-game time: units, calendars, and what time advancing fires.

Time is kept in seconds since the campaign began (`play.yaml` → `seconds`). Packs name their
units and calendar in `settings`; a world can set its own calendar in `world.yaml`:

    settings:
      time_units: {round: 6, turn: 600, watch: 28800}     # seconds
      watches: [morning, afternoon, night]                 # names for the day's watches
      calendar:
        hours: 24
        week: [Moonday, Tidesday, …]
        months: [{name: Frost, days: 24}, {name: Thaw, days: 28, leap: [4, 100, 400]}, …]
        start: {year: 7728, month: 1, day: 1, weekday: Tidesday}  # the start's day of the week
        year: "{year} AV"                                  # how a date writes its year
        seasons: [{name: Dead, month: 1, day: 4}, …]      # each from its first day
        holidays: [{name: First Light, month: 1, day: 24, text: "…"}, …]

`leap: 4` makes a month a day longer every 4th year; `leap: [4, 100, 400]` every 4th, but not
every 100th, but every 400th: each number overrules the one before. A campaign can open on
another date of the calendar, before its start or after (`campaign new --date`, kept as `start`
in `campaign.yaml`): its first day is then that date, and its weekday follows from the start's.
A date written with another day of the week is still that date (a note says which day it is).
"""

import re
from dataclasses import dataclass, field
from typing import cast

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.expr.model import Value
from didact.packs.source import Problem

BASE_UNITS: dict[str, int] = {
    "second": 1,
    "minute": 60,
    "round": 6,
    "turn": 600,
    "hour": 3600,
    "watch": 4 * 3600,
    "day": 24 * 3600,
    "week": 7 * 24 * 3600,
}
_AMOUNT = re.compile(r"^\s*(\d+(?:\.\d+)?)?\s*([a-z]+)\s*$")


@dataclass(frozen=True, slots=True)
class Month:
    name: str
    days: int
    leap: tuple[int, ...] = ()  # a day longer in the years these divide (`[4, 100, 400]`)

    def length(self, year: int | None) -> int:
        """Its days in a year: a day more in a leap year (of a calendar that numbers them)."""
        longer = False
        for number, every in enumerate(self.leap):
            if year is not None and every and year % every == 0:  # each overrules the last
                longer = number % 2 == 0
        return self.days + (1 if longer else 0)


@dataclass(frozen=True, slots=True)
class Marker:
    """A season's start or a holiday: a month and day in the year."""

    name: str
    month: int
    day: int
    text: str = ""


@dataclass(slots=True)
class Calendar:
    hours: int = 24
    units: dict[str, int] = field(default_factory=lambda: dict(BASE_UNITS))
    watches: list[str] = field(default_factory=list)
    week: list[str] = field(default_factory=list)
    months: list[Month] = field(default_factory=list)
    start_year: int | None = None
    start_month: int = 1
    start_day: int = 1
    weekday: int = 0  # the first day's day of the week (its index in `week`)
    year_text: str = ""  # how a date writes its year: "3A {year}" ("": the number alone)
    seasons: list[Marker] = field(default_factory=list)
    holidays: list[Marker] = field(default_factory=list)

    @property
    def day_seconds(self) -> int:
        return self.hours * 3600

    def parse(self, text: str) -> int:
        """`2 watches`, `1 day`, `turn`, `90 minutes` → seconds."""
        match = _AMOUNT.match(text.strip().lower())
        if not match:
            raise InvalidError(
                _("can't read the time {text}", text=repr(text)),
                hint=_("e.g. `1 watch`, `3 turns`, `2 days`"),
            )
        amount = float(match.group(1) or 1)
        unit = match.group(2)
        forms = [unit, unit.removesuffix("es"), unit.removesuffix("s")]  # watches, turns
        seconds = next((self.units[f] for f in forms if f in self.units), None)
        if seconds is None:
            known = ", ".join(sorted(self.units))
            raise InvalidError(
                _("unknown unit {unit}", unit=repr(unit)),
                hint=_("units here: {units}", units=known),
            )
        return round(amount * seconds)

    def describe(self, seconds: int) -> str:
        """`day 3, 14:00 (afternoon watch) · 14 Bright 7728`"""
        day_index, rest = divmod(max(seconds, 0), self.day_seconds)
        hours, rest = divmod(rest, 3600)
        minutes = rest // 60
        clock = f"{hours:02d}:{minutes:02d}"
        if self.watches:
            watch = min(int(hours * len(self.watches) / self.hours), len(self.watches) - 1)
            text = _(
                "day {day}, {time} ({watch} watch)",
                day=day_index + 1,
                time=clock,
                watch=self.watches[watch],  # the pack's name for it: not translated
            )
        else:
            text = _("day {day}, {time}", day=day_index + 1, time=clock)
        date = self.date(day_index)
        return f"{text} · {date}" if date else text

    def month_day(self, day_index: int) -> tuple[int, int, int] | None:
        """(year offset, month number, day of month) for a day since the campaign began; a day
        before it counts back."""
        if not any(m.days for m in self.months):
            return None
        year_offset, in_year = 0, self._before(self.start_month, self.start_day, 0) + day_index
        while in_year < 0:
            year_offset -= 1
            in_year += self._year_days(year_offset)
        while in_year >= self._year_days(year_offset):
            in_year -= self._year_days(year_offset)
            year_offset += 1
        for number, month in enumerate(self.months, 1):
            days = month.length(self._year(year_offset))
            if in_year < days:
                return year_offset, number, in_year + 1
            in_year -= days
        return None

    def day_of(self, year: int | None, month: int, day: int) -> int:
        """The day since the campaign began that a date is (`month_day` the other way; before
        it, negative). Without numbered years, a date is in the first day's year."""
        offset = year - self.start_year if year is not None and self.start_year is not None else 0
        found = self._before(month, day, offset) - self._before(self.start_month, self.start_day, 0)
        for each in range(min(offset, 0), max(offset, 0)):  # the whole years between
            found += self._year_days(each) if offset > 0 else -self._year_days(each)
        return found

    def start_at(self, year: int | None, month: int, day: int, *, gone: int = 0) -> None:
        """Make the campaign's first day another date, or the day `gone` days before it (when
        that many have passed since the first day): the week runs on from the start's."""
        if self.week:
            shift = self.day_of(year, month, day) - gone
            self.weekday = (self.weekday + shift) % len(self.week)
        if self.start_year is not None and year is not None:
            self.start_year = year
        self.start_month, self.start_day = month, day
        found = self.month_day(-gone) if gone else None
        if found is not None:
            offset, self.start_month, self.start_day = found
            self.start_year = self._year(offset)

    def first_day(self) -> dict[str, JSON]:
        """The campaign's first day as its `campaign.yaml` keeps it (`start`)."""
        year: dict[str, JSON] = {"year": self.start_year} if self.start_year is not None else {}
        return {**year, "month": self.start_month, "day": self.start_day}

    def _year(self, offset: int) -> int | None:
        """The number of the year `offset` years from the first day's (None: years have none)."""
        return None if self.start_year is None else self.start_year + offset

    def _year_days(self, offset: int) -> int:
        year = self._year(offset)
        return sum(m.length(year) for m in self.months)

    def _before(self, month: int, day: int, offset: int) -> int:
        """The days of a year (`offset` years from the first day's) before a day of a month."""
        year = self._year(offset)
        return sum(m.length(year) for m in self.months[: month - 1]) + day - 1

    def written(self, year_offset: int, month: int, day: int) -> str:
        """A date as the calendar writes it, without its weekday: `17 Frost 3A 201`."""
        text = f"{day} {self.months[month - 1].name}"
        year = self._year(year_offset)
        if year is None:
            return text
        return f"{text} {self.year_text.replace('{year}', str(year)) if self.year_text else year}"

    def date(self, day_index: int) -> str:
        found = self.month_day(day_index)
        if found is None:
            return ""
        year_offset, month, day = found
        named = self.weekday_name(day_index)
        weekday = f"{named}, " if named else ""
        extra = [m.name for m in self.holidays if (m.month, m.day) == (month, day)]
        season = self.season(day_index)
        text = weekday + self.written(year_offset, month, day)
        text += f" ({season})" if season else ""
        return text + (" · " + ", ".join(extra) if extra else "")

    def read_date(self, text: str) -> tuple[int | None, int, int]:
        """A date as the calendar writes one (`23 October 2277`; a weekday before it is left to
        the date, a year read as dates write it or as its number) → (year, month, day)."""
        first = self.month_day(0)
        if first is None:
            raise InvalidError(
                _("the calendar here has no months to date by"),
                hint=_(
                    "a setting's or a system's calendar has them: "
                    "`didact pack enable <pack> --scope world`"
                ),  # the world's: what a new campaign plays with
            )
        example = _("write it as the calendar does, e.g. {example}", example=self.written(*first))
        unread = _("can't read the date {text}", text=repr(text))
        words = self._weekday_said(text)[1]
        found = re.fullmatch(r"(\d+)\s+(.+)", words)
        rest = found.group(2) if found else ""
        named = [
            (number, month)
            for number, month in enumerate(self.months, 1)
            if re.match(rf"{re.escape(month.name)}(\s|$)", rest, re.IGNORECASE)
        ]
        if found is None or not named:
            raise InvalidError(unread, hint=example)
        number, month = max(named, key=lambda m: len(m[1].name))  # the longest name that fits
        given = rest[len(month.name) :].strip()
        year = self._read_year(given)
        if (year is None) != (self.start_year is None) or (year is None and given):
            raise InvalidError(unread, hint=example)  # no year, or one a calendar has none of
        day = int(found.group(1))
        if not 1 <= day <= month.length(year):
            raise InvalidError(
                _("{month} has no day {day}", month=month.name, day=day), hint=example
            )
        return year, number, day

    def _weekday_said(self, text: str) -> tuple[str | None, str]:
        """The day of the week written before a date (as the week names it), and the rest."""
        words = text.strip()
        for name in self.week:
            said = re.match(rf"{re.escape(name)}\s*,?\s+", words, re.IGNORECASE)
            if said:
                return name, words[said.end() :]
        return None, words

    def weekday_name(self, day_index: int) -> str:
        """The day of the week a day since the campaign began is ("" when there's no week)."""
        return self.week[(self.weekday + day_index) % len(self.week)] if self.week else ""

    def weekday_note(self, text: str, day_index: int) -> str | None:
        """When a date was written with a day of the week that isn't the one it falls on (the
        likeliest sign of a wrong date): a note saying so. The date decides either way."""
        said = self._weekday_said(text)[0]
        found = self.month_day(day_index)
        actual = self.weekday_name(day_index)
        if said is None or found is None or said.casefold() == actual.casefold():
            return None
        return _(
            "{date} is a {weekday}, not a {written}",
            date=self.written(*found),
            weekday=actual,
            written=said,
        )

    def _read_year(self, text: str) -> int | None:
        """A year as dates write it (`3A 201`) or as its number; None when it's neither."""
        form = re.escape(self.year_text or "{year}").replace(re.escape("{year}"), r"(-?\d+)")
        found = re.fullmatch(form.replace(r"\ ", r"\s*"), text, re.IGNORECASE)
        found = found or re.fullmatch(r"(-?\d+)", text)
        return int(found.group(1)) if found else None

    def season(self, day_index: int) -> str:
        """The season a day falls in: the last one that began on or before it."""
        found = self.month_day(day_index)
        if found is None or not self.seasons:
            return ""
        _unused, month, day = found
        started = [s for s in self.seasons if (s.month, s.day) <= (month, day)]
        ordered = sorted(started or self.seasons, key=lambda s: (s.month, s.day))
        return ordered[-1].name  # before the first start: the year's last season

    def holidays_between(self, first_day: int, last_day: int) -> list[str]:
        """Holidays on the days after `first_day`, up to and including `last_day`."""
        found: list[str] = []
        for index in range(first_day + 1, min(last_day, first_day + 400) + 1):
            date = self.month_day(index)
            if date is None:
                break
            for marker in self.holidays:
                if (marker.month, marker.day) == date[1:]:
                    when = f"{date[2]} {self.months[date[1] - 1].name}"
                    found.append(
                        f"{marker.name} ({when})" + (f": {marker.text}" if marker.text else "")
                    )
        return found

    def values(self, seconds: int) -> dict[str, Value]:
        """What time rules can read: `@time.day`, `@time.hour`, `@time.watch`, `@time.is_night`;
        with months, `@time.month` (its number), `@time.month_name`, `@time.day_of_month` and
        `@time.year`; with seasons, `@time.season`."""
        day_index, rest = divmod(max(seconds, 0), self.day_seconds)
        hour = rest // 3600
        found: dict[str, Value] = {
            "time.seconds": seconds,
            "time.day": day_index + 1,
            "time.hour": hour,
            "time.is_night": hour < 6 or hour >= 18,
        }
        if self.watches:
            found["time.watch"] = self.watches[
                min(int(hour * len(self.watches) / self.hours), len(self.watches) - 1)
            ]
        dated = self.month_day(day_index)
        if dated is not None:
            year_offset, month, day = dated
            found["time.month"] = month
            found["time.month_name"] = self.months[month - 1].name
            found["time.day_of_month"] = day
            if self.start_year is not None:
                found["time.year"] = self.start_year + year_offset
        if self.seasons:
            found["time.season"] = self.season(day_index)
        return found


def calendar_from(
    settings: dict[str, JSON], world: dict[str, JSON], begun: JSON = None
) -> Calendar:
    """The calendar here: the world's own if it has one, else the system pack's settings.
    `begun` is a campaign's own first day (`{year, month, day}`), when it isn't the start."""
    cal = Calendar()
    units = settings.get("time_units")
    if isinstance(units, dict):
        cal.units |= {str(k): int(v) for k, v in units.items() if isinstance(v, int | float)}
    watches = settings.get("watches")
    if isinstance(watches, list):
        cal.watches = [str(w) for w in watches]
    spec = (
        world.get("calendar")
        if isinstance(world.get("calendar"), dict)
        else settings.get("calendar")
    )
    if isinstance(spec, dict):
        hours = spec.get("hours")
        if isinstance(hours, int) and hours > 0:
            cal.hours = hours
            cal.units["day"] = hours * 3600
        week = spec.get("week")
        if isinstance(week, list):
            cal.week = [str(w) for w in week]
            cal.units["week"] = len(cal.week) * cal.units["day"]
        months = spec.get("months")
        if isinstance(months, list):
            cal.months = [
                Month(str(m.get("name")), int(cast(int, m.get("days", 30))), _every(m.get("leap")))
                for m in months
                if isinstance(m, dict) and m.get("name")
            ]
        start = spec.get("start")
        if isinstance(start, dict):
            year, month, day = start.get("year"), start.get("month", 1), start.get("day", 1)
            cal.start_year = year if isinstance(year, int) else None
            cal.start_month = month if isinstance(month, int) else 1
            cal.start_day = day if isinstance(day, int) else 1
            named = [w.casefold() for w in cal.week]
            weekday = str(start.get("weekday", "")).casefold()
            cal.weekday = named.index(weekday) if weekday in named else 0
        written = spec.get("year")
        if isinstance(written, str) and "{year}" in written:
            cal.year_text = written
        cal.seasons = _markers(spec.get("seasons"))
        cal.holidays = _markers(spec.get("holidays"))
    if cal.watches and "watch" not in (units if isinstance(units, dict) else {}):
        cal.units["watch"] = cal.day_seconds // len(cal.watches)
    if isinstance(begun, dict) and cal.months:
        year, month, day = begun.get("year"), begun.get("month"), begun.get("day")
        if isinstance(month, int) and 1 <= month <= len(cal.months) and isinstance(day, int):
            cal.start_at(year if isinstance(year, int) else None, month, day)
    return cal


def _every(raw: JSON) -> tuple[int, ...]:
    """A month's `leap: 4` or `leap: [4, 100, 400]`: the years it's a day longer in, each
    number overruling the one before (what isn't a positive whole number: `problems` says)."""
    listed = raw if isinstance(raw, list) else [raw]
    return tuple(n for n in listed if isinstance(n, int) and _positive(n))


def _positive(raw: JSON) -> bool:
    return isinstance(raw, int) and not isinstance(raw, bool) and raw > 0


def problems(settings: JSON) -> list[Problem]:
    """What `pack validate` says of a pack's calendar (`settings.calendar`), which would
    otherwise be read past without a word: a month's `leap:` that isn't a positive whole number
    or a list of them, a start's `weekday` that isn't a day of its week, a `year:` with no
    `{year}` for the number to go in."""
    from didact.packs.build import MANIFEST

    spec = settings.get("calendar") if isinstance(settings, dict) else None
    if not isinstance(spec, dict):
        return []
    found: list[Problem] = []
    months = spec.get("months")
    for month in months if isinstance(months, list) else []:
        if not isinstance(month, dict) or "leap" not in month:
            continue
        raw = month["leap"]
        listed = raw if isinstance(raw, list) else [raw]
        if not listed or not all(_positive(n) for n in listed):
            message = _(
                "{month}: `leap:` takes a number of years or a list of them, not {value}",
                month=str(month.get("name") or "?"),
                value=repr(raw),
            )
            found.append(
                Problem(MANIFEST, None, message, _("e.g. `leap: 4`, or `leap: [4, 100, 400]`"))
            )
    week = [str(w) for w in cast(list[JSON], spec.get("week") or [])]
    start = spec.get("start")
    if isinstance(start, dict) and "weekday" in start:
        said = str(start["weekday"])
        if said.casefold() not in {w.casefold() for w in week}:
            found.append(
                Problem(
                    MANIFEST,
                    None,
                    _("the start's weekday {day} isn't a day of the week", day=repr(said)),
                    _("one of: {values}", values=", ".join(week))
                    if week
                    else _("give the calendar a `week:` to name its days"),
                )
            )
    written = spec.get("year")
    if written is not None and not (isinstance(written, str) and "{year}" in written):
        found.append(
            Problem(
                MANIFEST,
                None,
                _("`year:` needs {{year}} where the number goes, not {value}", value=repr(written)),
                _("e.g. {example}", example='`year: "4E {year}"`'),
            )
        )
    return found


def _markers(raw: JSON) -> list[Marker]:
    found: list[Marker] = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            month, day = item.get("month", 1), item.get("day", 1)
            found.append(
                Marker(
                    str(item["name"]),
                    month if isinstance(month, int) else 1,
                    day if isinstance(day, int) else 1,
                    str(item.get("text") or ""),
                )
            )
    return found
