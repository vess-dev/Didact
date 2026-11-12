"""The Status page (where things stand, at a glance), the map mode of the graph, and the data
they're built from: `party show` with the numbers, `track list` and `quest list`."""

import html
import json
import re
from typing import Any, cast

from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)


def _play(cli: Cli) -> None:
    """A campaign under way: a PC in the party, places and paths, a session and scene, an
    item, a fight, time passing, a reminder, a quest and a tracker."""
    for argv in (
        ("new", "pc", "Freya", "--fill"),  # a new PC joins the party
        ("new", "loc", "The Mill"),
        ("new", "loc", "Old Bridge"),
        ("new", "loc", "Drowned Shrine", "--set", "knowledge=secret"),
        ("link", "The Mill", "road", "Old Bridge"),
        ("link", "Old Bridge", "path", "Drowned Shrine"),
        ("visit", "The Mill"),
        ("visit", "Old Bridge"),
        ("session", "start"),
        ("scene", "new", "The drowned mill"),
        ("inv", "add", "freya", "Rope", "Torch"),
        ("new", "npc", "Goblin"),
        ("about", "goblin", "plan=cut the rope"),
        ("combat", "start", "--party", "goblin"),
        ("time", "advance", "2 hours"),
        ("remind", "Rations run low", "--in", "1 day"),
        ("quest", "new", "Free the spirit"),
        ("track", "new", "Doom", "--kind", "clock", "--size", "6"),
        ("quest", "new", "The heir's claim"),
        ("set", "The heir's claim", "knowledge=secret"),
        ("track", "new", "Coup", "--kind", "clock", "--size", "4"),
        ("set", "coup", "knowledge=secret"),
    ):
        assert cli(*argv).code == 0, argv


def _page(web: Browser, path: str) -> str:  # noqa: F811
    """A page's text, as a reader sees it (no tags)."""
    return html.unescape(re.sub(r"<[^>]+>", "", web.get(path).body))


def _json(cli: Cli, *argv: str) -> Any:
    return json.loads(cli(*argv, "--format", "json").out)


def test_status_shows_where_things_stand(web: Browser, cli: Cli) -> None:  # noqa: F811
    _play(cli)
    page = _page(web, "/status")
    for text in (
        "Now", "Session 1", "The drowned mill", "day 1, 02:00", "Rations run low",
        "Party", "Freya", "hp", "Carrying", "Rope", "Torch", "3/3 uses",
        "The fight · round 1", "Goblin",
        "Quests and trackers", "Free the spirit", "Doom 0/6",
        "Where the party is", "Old Bridge", "road → The Mill", "path → ?", "Open the map",
    ):  # fmt: skip
        assert text in page, text
    assert 'href="/status"' in web.get("/").body  # it's in the navigation


def test_status_is_what_the_players_know(web: Browser, cli: Cli) -> None:  # noqa: F811
    _play(cli)
    page = _page(web, "/status")
    for secret in ("Drowned Shrine", "The heir's claim", "Coup", "cut the rope"):
        assert secret not in page, secret
    web.gm(True)
    gm = _page(web, "/status")
    assert "The heir's claim" in gm and "Coup" in gm and "plan: cut the rope" in gm
    assert "path → Drowned Shrine" in gm


def test_status_adjusts_through_real_commands(web: Browser, cli: Cli) -> None:  # noqa: F811
    _play(cli)
    hp = _json(cli, "show", "freya")["values"]["hp"]
    step = {"action": "set", "ref": "pc:freya", "key": "hp", "op": "-=", "value": "1"}
    assert "didact set pc:freya hp-=1" in _page_after(web, step)
    assert _json(cli, "show", "freya")["values"]["hp"] == hp - 1
    web.run("track", "tick", "track:doom", next_="/status")
    web.run("inv", "drop", "pc:freya", "Rope", next_="/status")
    web.run("quest", "done", "quest:free-the-spirit", next_="/status")
    web.post(
        "/run",
        {"action": "words", "w": ["time", "advance", "1 hour"], "next": "/status"},
    )
    page = _page(web, "/status")
    assert "Doom 1/6" in page and "Rope" not in page and "Free the spirit" not in page
    assert "day 1, 03:00" in page
    for _ in range(5):  # every one of them is a change undo takes back
        assert cli("undo").code == 0
    page = _page(web, "/status")
    assert "Doom 0/6" in page and "Rope" in page and "Free the spirit" in page
    assert _json(cli, "show", "freya")["values"]["hp"] == hp


def _page_after(web: Browser, fields: dict[str, str]) -> str:  # noqa: F811
    return html.unescape(web.post("/run", {**fields, "next": "/status"}).body)


def test_status_before_anything_happens(web: Browser, cli: Cli) -> None:  # noqa: F811
    page = _page(web, "/status")  # the fixture's campaign: no session, party or places yet
    assert "No one in the party yet" in page and "day 1, 00:00" in page
    assert "Session 0" not in page and "Scene 0" not in page
    assert "The party isn't anywhere yet" in page and "The fight" not in page


def test_status_without_a_campaign_points_to_the_library(web: Browser, cli: Cli) -> None:  # noqa: F811
    cli("world", "new", "isles", "--system", "mini-system")
    page = _page(web, "/status")
    assert "No campaign in play" in page and 'href="/library"' in web.get("/status").body


def test_the_map_draws_places_paths_and_where_the_party_is(web: Browser, cli: Cli) -> None:  # noqa: F811
    _play(cli)
    raw = web.get("/api/graph?mode=map").body
    assert "drowned-shrine" not in raw and "Drowned Shrine" not in raw  # not found yet
    data = json.loads(raw)
    states = {node["id"]: node["state"] for node in data["nodes"]}
    assert states["loc:old-bridge"] == "here" and states["loc:the-mill"] == "visited"
    assert data["focus"] == "loc:old-bridge" and data["labels"] is True
    stubs = [node for node in data["nodes"] if node["state"] == "unknown"]
    assert len(stubs) == 1 and stubs[0]["name"] == "?" and stubs[0]["link"] is False
    paths = {(e["source"], e["target"], e["rel"]) for e in data["edges"]}
    assert ("loc:old-bridge", stubs[0]["id"], "path") in paths
    roads = [e for e in data["edges"] if e["rel"] == "road"]
    assert len(roads) == 1  # both ends list it; it's drawn once
    page = web.get("/graph?mode=map").body
    assert 'data-src="/api/graph?mode=map"' in page and "Find a place" in page
    web.gm(True)
    data = json.loads(web.get("/api/graph?mode=map").body)
    states = {node["id"]: node["state"] for node in data["nodes"]}
    assert states["loc:drowned-shrine"] == "secret" and "unknown" not in states.values()


def test_a_region_shows_as_a_dashed_link(web: Browser, cli: Cli) -> None:  # noqa: F811
    cli("new", "loc", "The Vale")
    cli("new", "loc", "Mill Town")
    cli("set", "mill-town", "region=loc:the-vale")
    cli("visit", "Mill Town")
    data = json.loads(web.get("/api/graph?mode=map").body)
    regions = [e for e in data["edges"] if e["kind"] == "region"]
    assert regions == [
        {"source": "loc:mill-town", "target": "loc:the-vale", "rel": "in", "kind": "region"}
    ]


def test_the_lists_carry_names_and_numbers(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    _play(cli)
    party = _json(cli, "party", "show")["members"][0]
    line = cli("party", "show").out.splitlines()[1]
    stats = " · ".join(f"{s['label']} {s['text']}" for s in party["stats"])
    assert stats and line.endswith(stats)  # the same numbers as the stat line
    tracks = _json(cli, "track", "list")["tracks"]
    assert [t["name"] for t in tracks] == ["Doom"]  # the secret one needs --gm
    assert tracks[0]["text"] == "Doom 0/6" and tracks[0]["kind"] == "clock"
    assert {t["name"] for t in _json(cli, "track", "list", "--gm")["tracks"]} == {"Doom", "Coup"}
    quests = _json(cli, "quest", "list")["quests"]
    assert [(q["name"], q["type"]) for q in quests] == [("Free the spirit", "quest")]


def test_the_app_forgets_a_start_up_campaign_that_goes(cli: Cli) -> None:
    from didact.web.app import App

    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "run")
    cli("campaign", "new", "spare")
    app = App(campaign="spare")  # `didact serve --campaign spare`
    assert app.run(["campaign", "delete", "spare"]).ok and app.campaign == "spare"  # a preview
    assert app.run(["campaign", "delete", "spare", "--yes"]).ok
    campaign = cast(str | None, app.campaign)  # the run changed it: mypy can't tell
    assert campaign is None and app.run(["status"]).ok  # the active one takes over


def test_the_chosen_theme_is_in_the_first_bytes(web: Browser) -> None:  # noqa: F811
    """No white flash between pages in the dark theme: the server writes the theme the
    button chose (a cookie) into the page, so the browser's canvas is dark from the start."""
    from didact.web.app import Request
    from didact.web.pages import overview

    for theme, scheme in (("dark", "dark"), ("light", "light"), ("", "light dark")):
        req = Request(web.server.app, "GET", "/", cookies={"didact_theme": theme} if theme else {})
        head = overview.show(req).body.decode().split("</head>")[0]
        assert f'<meta name="color-scheme" content="{scheme}">' in head
        assert (f'<html lang="en" data-theme="{theme}">' if theme else '<html lang="en">') in head
    script = web.get("/static/app.js").body
    assert "didact_theme=" in script  # the theme button sets the cookie
