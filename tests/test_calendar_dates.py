"""A calendar's leap years (`leap:` on a month), the day of the week its start is
(`start.weekday`) and how it writes its year (`year: "3A {year}"`), and a campaign's own first
day: a date of the calendar, before its start or after, it opens on (`campaign new --date`) or
is set to before its first session (`time set`). Calendars without them read as before (the
`leap-setting` and `era-setting` fixtures)."""

import datetime
import json
from pathlib import Path
from typing import cast

import pytest

from didact.commands import load_all
from didact.commands.registry import REGISTRY
from didact.core.errors import InvalidError
from didact.core.output import JSON
from didact.services.clock import calendar_from
from didact.web.forms import command_argv
from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)
from tests.test_web_inputs import _box

MONTHS = [
    ("January", 31), ("February", 28), ("March", 31), ("April", 30), ("May", 31), ("June", 30),
    ("July", 31), ("August", 31), ("September", 30), ("October", 31), ("November", 30),
    ("December", 31),
]  # fmt: skip
WEEK = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
REAL: dict[str, JSON] = {
    "week": list[JSON](WEEK),
    "months": [
        {"name": name, "days": days, **({"leap": [4, 100, 400]} if days == 28 else {})}
        for name, days in MONTHS
    ],
    "start": {"year": 2277, "month": 10, "day": 23, "weekday": "Tuesday"},
}
ERA: dict[str, JSON] = {
    "week": ["Moonday", "Tidesday", "Rootday"],
    "months": [{"name": n, "days": 20} for n in ("Frost", "High Sun", "Ember")],
    "start": {"year": 201, "month": 2, "day": 17},
    "year": "3A {year}",
}


def _real(day: datetime.date) -> str:
    return f"{WEEK[day.isoweekday() % 7]}, {day.day} {MONTHS[day.month - 1][0]} {day.year}"


def test_leap_years_and_the_starts_weekday_keep_the_real_calendar() -> None:
    real = calendar_from({}, {"calendar": REAL})
    start = datetime.date(2277, 10, 23)
    for days in range(-200_000, 200_000, 4_999):  # five centuries and more, either side
        assert real.date(days) == _real(start + datetime.timedelta(days=days))
    assert real.read_date("Sunday, 29 February 2280") == (2280, 2, 29)
    assert real.read_date("29 february 2400") == (2400, 2, 29)  # every 400th year after all
    with pytest.raises(InvalidError, match="February has no day 29"):
        real.read_date("29 February 2100")  # but not every 100th
    assert real.day_of(2280, 2, 29) == (datetime.date(2280, 2, 29) - start).days


def test_a_campaign_opens_on_any_date_and_the_week_follows() -> None:
    early = calendar_from({}, {"calendar": REAL}, {"year": 2102, "month": 10, "day": 23})
    assert early.date(0) == "Monday, 23 October 2102" and early.values(0)["time.year"] == 2102
    early.start_at(2281, 10, 19, gone=2)  # two days have gone by: the first day was the 17th
    assert early.first_day() == {"year": 2281, "month": 10, "day": 17}
    assert early.date(2) == "Wednesday, 19 October 2281"
    plain = calendar_from({}, {"calendar": {**REAL, "start": {"year": 2277, "month": 10}}})
    assert plain.date(0) == "Sunday, 1 October 2277"  # no weekday said: the week's first
    with pytest.raises(InvalidError, match="can't read the date 'Octobre 19'"):
        early.read_date("Octobre 19")


def test_a_calendar_writes_its_year_its_own_way_and_reads_it_back() -> None:
    era = calendar_from({}, {"calendar": ERA})
    assert era.describe(0) == "day 1, 00:00 · Moonday, 17 High Sun 3A 201"
    assert era.values(0)["time.year"] == 201  # rules read the number
    assert era.read_date("Tidesday, 3 Ember 3A 202") == (202, 3, 3) == era.read_date("3 ember 202")
    after = calendar_from({}, {"calendar": {**ERA, "year": "{year} AF"}})
    assert after.date(0) == "Moonday, 17 High Sun 201 AF"
    assert after.read_date("1 Frost 202 AF") == (202, 1, 1)
    yearless = calendar_from({}, {"calendar": {"months": [{"name": "Frost", "days": 24}]}})
    assert yearless.read_date("3 Frost") == (None, 1, 3)
    with pytest.raises(InvalidError, match="can't read the date '3 Frost 7728'"):
        yearless.read_date("3 Frost 7728")  # it numbers no years
    with pytest.raises(InvalidError, match="no months to date by"):
        calendar_from({}, {}).read_date("3 Frost")


def setup(cli: Cli, setting: str) -> None:
    assert cli("world", "new", "w", "--system", "mini-system", "--seed", "dates").code == 0
    assert cli("pack", "enable", setting).code == 0


def test_a_campaign_opens_before_the_calendars_start_or_after_it(cli: Cli) -> None:
    setup(cli, "leap-setting")
    made = cli("campaign", "new", "early", "--date", "23 October 2102")
    assert made.code == 0, made.err
    assert "note: it's day 1, 00:00 (morning watch) · Monday, 23 October 2102 (fall)" in made.out
    assert (
        "→ day 2, 00:00 (morning watch) · Tuesday, 24 October 2102"
        in cli("time", "advance", "1 day").out
    )
    assert cli("campaign", "new", "late", "--date", "Wednesday, 19 October 2281").code == 0
    assert "Wednesday, 19 October 2281 (fall)" in cli("time", "show").out
    assert cli("campaign", "new", "plain").code == 0  # no date: the calendar's start
    assert "Tuesday, 23 October 2277 (fall)" in cli("time", "show").out
    refused = cli("campaign", "new", "never", "--date", "29 February 2100")
    assert refused.code == 1 and "February has no day 29" in refused.err
    assert "write it as the calendar does, e.g. 23 October 2277" in refused.err
    assert cli("campaign", "open", "never").code == 1  # refused whole: nothing made


def test_a_new_campaign_reads_its_date_with_the_calendar_it_will_have(cli: Cli) -> None:
    assert cli("world", "new", "w", "--system", "mini-system").code == 0
    assert cli("campaign", "new", "first").code == 0
    assert cli("pack", "enable", "leap-setting").code == 0  # the open campaign's calendar only
    refused = cli("campaign", "new", "second", "--date", "19 October 2281")
    assert refused.code == 1 and "the calendar here has no months to date by" in refused.err
    assert cli("pack", "enable", "era-setting", "--scope", "world").code == 0
    made = cli("campaign", "new", "third", "--date", "3 Ember 3A 202")  # "first" is still open
    assert made.code == 0, made.err
    assert "Moonday, 3 Ember 3A 202" in cli("time", "show").out


def test_the_date_is_set_until_the_first_session(cli: Cli) -> None:
    setup(cli, "leap-setting")
    assert cli("campaign", "new", "c").code == 0
    assert cli("remind", "Check the traps", "--in", "3 days").code == 0
    assert cli("time", "advance", "2 days").code == 0
    done = cli("time", "set", "19 October 2281")  # now is that date: the first day, the 17th
    assert done.code == 0, done.err
    assert "day 3, 00:00 (morning watch) · Wednesday, 19 October 2281 (fall)" in done.out
    campaign = json.loads(cli("campaign", "list", "--format", "json").out)["campaigns"][0]
    assert campaign["start"] == {"year": 2281, "month": 10, "day": 17}
    due = "Check the traps · day 4, 00:00 (morning watch) · Thursday, 20 October 2281"
    assert due in cli("remind", "--list").out  # what hangs on the clock moves with it
    assert cli("undo").code == 0 and "Thursday, 25 October 2277" in cli("time", "show").out
    assert cli("session", "start").code == 0
    refused = cli("time", "set", "1 January 2300")
    assert refused.code == 1 and "play has begun (session 1)" in refused.err
    assert "a campaign's date is set before its first session" in refused.err


def test_the_year_as_the_calendar_writes_it_wherever_a_date_shows(cli: Cli) -> None:
    setup(cli, "era-setting")
    assert cli("campaign", "new", "c", "--date", "Tidesday, 3 Ember 3A 202").code == 0
    assert "3 Ember 3A 202" in cli("time", "show").out
    assert cli("remind", "The ferry leaves", "--in", "1 day").code == 0
    due = "The ferry leaves · day 2, 00:00 (morning watch) · Tidesday, 4 Ember 3A 202"
    assert due in cli("remind", "--list").out
    assert cli("session", "start").code == 0
    assert "Time: day 1, 00:00 (morning watch) · Moonday, 3 Ember 3A 202" in cli("brief").out
    assert cli("log", "action", "We set out").code == 0
    assert "## day 1 · Moonday, 3 Ember 3A 202" in cli("timeline").out  # the journal's days


def test_the_status_page_dates_the_time_as_the_calendar_does(web: Browser, cli: Cli) -> None:  # noqa: F811
    assert cli("pack", "enable", "era-setting", "--scope", "world").code == 0
    page = web.get("/status")
    assert page.status == 200 and "Moonday, 17 High Sun 3A 201" in page.body
    for path in ("/commands/time/set", "/commands/campaign/new"):  # a date, not an amount of time
        form = web.get(path).body
        assert 'name="a.date"' in form and 'name="a.date.unit"' not in form
    assert 'type="text"' in _box(web.get("/commands/campaign/new").body, "a.date")
    load_all()
    dated = command_argv(REGISTRY["time set"], {"a.date": ["3 Ember 3A 202"]})
    assert dated == ["time", "set", "3 Ember 3A 202"]


def test_a_leap_rule_of_one_number_and_a_calendar_pack_validate_reads(
    cli: Cli, tmp_path: Path
) -> None:
    every_fourth = [
        {**month, "leap": 4} if month["days"] == 28 else month
        for month in cast(list[dict[str, JSON]], REAL["months"])
    ]
    julian = calendar_from({}, {"calendar": {**REAL, "months": list[JSON](every_fourth)}})
    assert julian.read_date("29 February 2100") == (2100, 2, 29)  # every 4th year, no exception
    pack = tmp_path / "bad-calendar"
    pack.mkdir()
    (pack / "GUIDE.md").write_text("# A calendar with mistakes\n")
    (pack / "pack.yaml").write_text(
        "id: bad-calendar\nname: B\nkind: setting\nversion: 0.1.0\nrequires: {packs: [core]}\n"
        "settings:\n  calendar:\n    week: [Sun, Mon]\n"
        "    months: [{name: Feb, days: 28, leap: [4, x]}, {name: Mar, days: 31, leap: 0}]\n"
        "    start: {year: 1, month: 1, day: 1, weekday: Tus}\n    year: 4E\n"
    )
    said = cli("pack", "validate", str(pack))
    assert said.code == 1 and "✘ 4 errors" in said.out
    assert "Feb: `leap:` takes a number of years or a list of them, not [4, 'x']" in said.out
    assert "Mar: `leap:` takes a number of years or a list of them, not 0" in said.out
    assert "the start's weekday 'Tus' isn't a day of the week (fix: one of: Sun, Mon)" in said.out
    assert "`year:` needs {year} where the number goes, not '4E'" in said.out


def test_a_weekday_that_isnt_the_dates_says_so(cli: Cli) -> None:
    setup(cli, "leap-setting")
    made = cli("campaign", "new", "c", "--date", "Monday, 23 October 2103")
    assert made.code == 0 and "note: 23 October 2103 is a Tuesday, not a Monday" in made.out
    assert "Tuesday, 23 October 2103" in cli("time", "show").out  # the date decides
    reset = cli("time", "set", "tuesday 23 October 2102")
    assert "note: 23 October 2102 is a Monday, not a Tuesday" in reset.out
    right = cli("time", "set", "Monday, 23 October 2102")
    assert right.code == 0 and "not a" not in right.out
