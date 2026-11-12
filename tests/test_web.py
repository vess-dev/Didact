"""The browser app (`didact serve`): pages, forms, the graph, the guards and player safety.

Each test starts the real server on a free port in a thread, against the test's own library,
and talks to it with urllib like a small browser (cookies, redirects, the form token).
"""

import html
import http.client
import json
import os
import re
import signal
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, cast

import pytest

from didact.commands import load_all
from didact.commands.registry import REGISTRY
from didact.web.app import App, Request
from didact.web.forms import command_argv
from didact.web.html import h, record_url
from didact.web.markdown import markdown
from didact.web.pages import records
from didact.web.server import WebServer, host_allowed, is_loopback, split_host, startup_lines
from tests.conftest import Cli

SECRET_BODY = "Champion of the Wood.\n\n## Secrets\nHe is the rightful heir."


@dataclass(frozen=True, slots=True)
class Page:
    status: int
    url: str
    body: str
    headers: dict[str, str]

    def json(self) -> Any:
        return json.loads(self.body)


class Browser:
    """Just enough browser: a cookie jar, redirects, and forms that carry the token."""

    def __init__(self, server: WebServer) -> None:
        self.server = server
        self.port = server.app.port
        self.base = f"http://127.0.0.1:{self.port}"
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    @property
    def token(self) -> str:
        return self.server.app.secret

    def _open(self, request: urllib.request.Request) -> Page:
        try:
            with self.opener.open(request, timeout=30) as response:
                body = response.read().decode("utf-8", errors="replace")
                return Page(response.status, response.url, body, dict(response.headers))
        except urllib.error.HTTPError as err:
            return Page(
                err.code, request.full_url, err.read().decode("utf-8", "replace"), dict(err.headers)
            )

    def get(self, path: str) -> Page:
        return self._open(urllib.request.Request(self.base + path))

    def post(
        self, path: str, fields: dict[str, str | list[str]], *, token: str | None = None
    ) -> Page:
        pairs: list[tuple[str, str]] = [("csrf", self.token if token is None else token)]
        for name, value in fields.items():
            for item in [value] if isinstance(value, str) else value:
                pairs.append((name, item))
        data = urllib.parse.urlencode(pairs).encode()
        return self._open(urllib.request.Request(self.base + path, data=data, method="POST"))

    def run(self, *argv: str, next_: str = "/", **fields: str) -> Page:
        """Submit a one-button form that runs `argv`."""
        return self.post("/run", {"action": "words", "w": list(argv), "next": next_, **fields})

    def gm(self, on: bool) -> Page:
        return self.post("/gm", {"on": "1" if on else "0", "next": "/"})


def raw(
    port: int, path: str, headers: dict[str, str], *, method: str = "GET", body: bytes = b""
) -> int:
    """A request with exactly these headers (urllib would fix the Host up)."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    try:
        connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        for name, value in headers.items():
            connection.putheader(name, value)
        if method == "POST":
            connection.putheader("Content-Length", str(len(body)))
        connection.endheaders(body or None)
        return connection.getresponse().status
    finally:
        connection.close()


@pytest.fixture
def web(cli: Cli) -> Iterator[Browser]:
    """A library with a world, a campaign and a few records, and the app serving it."""
    assert cli("world", "new", "vale", "--system", "mini-system").code == 0
    assert cli("campaign", "new", "run").code == 0
    cli("new", "npc", "Sweeney", "--tag", "wood", "--body", SECRET_BODY)
    cli("new", "loc", "Amber Grave", "--body", "A pool of bubbling sap.")
    cli("link", "sweeney", "lives-at", "Amber Grave")
    cli("new", "npc", "Hidden Heir", "--set", "knowledge=secret")
    server = WebServer(App(), "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        browser = Browser(server)
        assert browser.get("/").status == 200  # sets the form token's cookie
        yield browser
    finally:
        server.shutdown()
        server.server_close()


def shown(cli: Cli, ref: str) -> dict[str, Any]:
    result = cli("show", ref, "--gm", "--format", "json")
    assert result.code == 0, result.err
    return cast(dict[str, Any], json.loads(result.out))


def field_names(html: str) -> set[str]:
    return set(re.findall(r'name="([^"]+)"', html))


# ---------------------------------------------------------------------------- pages


def test_every_page_renders_with_its_content(web: Browser) -> None:
    pages = {
        "/": ["Where the game stands", "Roll dice", "Recent changes", "Sweeney"],
        "/records": ["Sweeney", "Amber Grave", "NPCs", "Places", "New record"],
        "/records/new": ['name="type"', 'name="name"', 'name="body"'],
        "/record/npc:sweeney": ["Champion of the Wood", "lives-at", "Amber Grave", "History"],
        "/record/loc:amber-grave": ["Linked from", "Sweeney"],
        "/graph": ['id="graph"', "graph.js"],
        "/journal": ["No sessions yet", "Start session 1"],
        "/reference": ["Rules", "Save", "Tables", "Glossary", "Guides"],
        "/search?q=sap": ["Amber Grave"],
        "/rules/save": ['name="r.who"', 'name="r.attr"', "STR"],
        "/tables/weather": ["Summer weather", "Roll"],
        "/reference/mini-system.saves": ["Saves", "d20"],
        "/guide/dice": ["Guide: dice"],
        "/library": ["Worlds and campaigns", "mini-system", "History", "Save points"],
        "/commands": ["Command line", "roll", "world new"],
        "/commands/world/new": ['name="a.world-id"', 'name="a.system"'],
        "/about": ["Ubuntu", "Feather"],
    }
    for path, wanted in pages.items():
        page = web.get(path)
        assert page.status == 200, f"{path}: {page.status}"
        assert page.headers["Content-Type"].startswith("text/html"), path
        for text in wanted:
            assert text in page.body, f"{path} lacks {text!r}"
    assert web.get("/api/graph").headers["Content-Type"].startswith("application/json")


def test_unknown_routes_are_404_and_wrong_methods_405(web: Browser) -> None:
    assert web.get("/nope").status == 404
    assert "Nothing here" in web.get("/nope").body
    assert web.get("/record/npc:nobody").status == 404
    assert web.get("/commands/no/such/command").status == 404
    assert web.get("/journal/zero").status == 404
    assert web.post("/records", {}).status == 405
    assert web.get("/run").status == 405


def test_static_files_have_their_types_and_no_way_out(web: Browser) -> None:
    types = {
        "style.css": "text/css",
        "app.js": "text/javascript",
        "graph.js": "text/javascript",
        "feather-sprite.svg": "image/svg+xml",
        "favicon.svg": "image/svg+xml",
        "fonts/ubuntu-latin-400-normal.woff2": "font/woff2",
        "fonts/ubuntu-mono-latin-400-normal.woff2": "font/woff2",
        "fonts/UFL-LICENCE.txt": "text/plain",
        "feather-LICENSE.txt": "text/plain",
    }
    for name, kind in types.items():
        page = web.get(f"/static/{name}")
        assert page.status == 200, name
        assert page.headers["Content-Type"].startswith(kind), name
    sprite = web.get("/static/feather-sprite.svg").body
    assert 'id="eye-off"' in sprite and 'id="share-2"' in sprite
    for sneaky in (
        "/static/../app.py",
        "/static/%2e%2e/app.py",
        "/static/..%2fapp.py",
        "/static/fonts/../../server.py",
        "/static//etc/passwd",
        "/static/%2Fetc%2Fpasswd",
        "/static/",
    ):
        assert raw(web.port, sneaky, {"Host": f"127.0.0.1:{web.port}"}) == 404, sneaky


def test_the_host_header_must_name_this_server(web: Browser) -> None:
    port = web.port
    for good in (f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}", f"LOCALHOST:{port}"):
        assert raw(port, "/", {"Host": good}) == 200, good
    for bad in ("evil.example", f"evil.example:{port}", f"localhost:{port + 1}", "", "[::1"):
        assert raw(port, "/", {"Host": bad}) == 403, bad
    assert raw(port, "/", {}) == 403


def test_host_rules() -> None:
    assert split_host("localhost:8765") == ("localhost", 8765)
    assert split_host("[::1]:80") == ("::1", 80)
    assert split_host("::1") is None and split_host("a:b") is None
    assert host_allowed("192.168.1.5:8765", "192.168.1.5", 8765)
    assert not host_allowed("192.168.1.6:8765", "192.168.1.5", 8765)
    assert host_allowed("192.168.1.9:8765", "0.0.0.0", 8765)  # any address when bound to all
    assert not host_allowed("rebind.example:8765", "0.0.0.0", 8765)  # but never a name
    assert host_allowed("localhost", "127.0.0.1", 80)
    assert is_loopback("127.0.0.1") and is_loopback("::1") and is_loopback("localhost")
    assert not is_loopback("0.0.0.0") and not is_loopback("192.168.1.5")
    assert any("warning" in line for line in startup_lines("http://0.0.0.0:1/", "0.0.0.0"))
    assert not any("warning" in line for line in startup_lines("http://127.0.0.1:1/", "127.0.0.1"))


def test_posts_need_this_sites_form_token(web: Browser, cli: Cli) -> None:
    form: dict[str, str | list[str]] = {"action": "words", "w": ["new", "npc", "Intruder"]}
    assert web.post("/run", form, token="").status == 403
    assert web.post("/run", form, token="not-the-token").status == 403
    stranger = Browser(web.server)  # the right token, but no cookie
    assert stranger.post("/run", form).status == 403
    pairs = [("csrf", web.token), ("action", "words"), ("next", "/")]
    body = urllib.parse.urlencode([*pairs, ("w", "new"), ("w", "npc"), ("w", "Intruder")])
    headers = {
        "Host": f"127.0.0.1:{web.port}",
        "Cookie": f"{web.server.app.csrf_cookie}={web.token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    assert raw(web.port, "/run", headers, method="POST", body=b"csrf=x") == 403
    for extra in ({"Origin": "http://evil.example"}, {"Sec-Fetch-Site": "cross-site"}):
        sent = {**headers, **extra}
        assert raw(web.port, "/run", sent, method="POST", body=body.encode()) == 403, extra
    assert cli("show", "Intruder").code != 0
    same = {**headers, "Origin": f"http://127.0.0.1:{web.port}", "Sec-Fetch-Site": "same-origin"}
    assert raw(web.port, "/run", same, method="POST", body=body.encode()) == 303
    assert cli("show", "Intruder").code == 0  # the same request from our own page runs


def test_responses_are_locked_down(web: Browser) -> None:
    page = web.get("/")
    assert "default-src 'self'" in page.headers["Content-Security-Policy"]
    assert page.headers["X-Frame-Options"] == "DENY"
    assert page.headers["X-Content-Type-Options"] == "nosniff"
    assert "Access-Control-Allow-Origin" not in page.headers
    cookie = next(c for c in web.jar if c.name == web.server.app.csrf_cookie)
    assert cookie.has_nonstandard_attr("HttpOnly")
    sent = urllib.request.urlopen(web.base + "/", timeout=30).headers["Set-Cookie"]
    assert "SameSite=Strict" in sent and "HttpOnly" in sent


# ---------------------------------------------------------------------------- writing through forms


def test_records_are_made_changed_linked_and_deleted_through_forms(web: Browser, cli: Cli) -> None:
    made = web.post(
        "/run",
        {
            "action": "new",
            "type": "npc",
            "name": "Old Tom",
            "tags": "smuggler, tall",
            "body": "- Limps.\r\n- Hums old songs.",
            "fields": "role=ferryman",
            "next": "/records/new",
            "next_ok": "@record",
        },
    )
    assert made.status == 200 and made.url.startswith(web.base + "/record/npc:old-tom")
    assert "didact new npc &#x27;Old Tom&#x27; --tag smuggler --tag tall" in made.body
    tom = shown(cli, "npc:old-tom")
    assert tom["tags"] == ["smuggler", "tall"] and tom["fields"]["role"] == "ferryman"
    assert tom["body"].startswith("- Limps.\n- Hums")

    changed = web.post(
        "/run",
        {"action": "set", "ref": "npc:old-tom", "key": "role", "value": "innkeeper"},
    )
    assert "didact set npc:old-tom role=innkeeper" in changed.body
    assert shown(cli, "npc:old-tom")["fields"]["role"] == "innkeeper"

    web.post(
        "/run",
        {
            "action": "set",
            "ref": "npc:old-tom",
            "assignment": "hp=4",
            "next": "/record/npc:old-tom",
        },
    )
    stepped = web.post(
        "/run",
        {"action": "set", "ref": "npc:old-tom", "key": "hp", "op": "-=", "value": "1"},
    )
    assert "didact set npc:old-tom hp-=1" in stepped.body
    assert shown(cli, "npc:old-tom")["values"]["hp"] == 3

    edited = web.post(
        "/run",
        {
            "action": "edit",
            "ref": "npc:old-tom",
            "body": "A tall man.\r\n\r\n## Secrets\r\nHe smuggles for the heir.",
            "was.body": tom["body"],
            "next": "/record/npc:old-tom",
        },
    )
    assert "didact edit npc:old-tom --data" in edited.body
    assert (
        shown(cli, "npc:old-tom")["body"]
        == "A tall man.\n\n## Secrets\nHe smuggles for the heir.\n"
    )
    renamed = web.post(
        "/run",
        {
            "action": "edit",
            "ref": "npc:old-tom",
            "name": "Tomas",
            "was.name": "Old Tom",
            "tags": "smuggler, tall",
            "was.tags": "smuggler, tall",
        },
    )
    assert renamed.status == 200
    assert shown(cli, "npc:old-tom")["name"] == "Tomas"

    linked = web.run("link", "npc:old-tom", "ally", "npc:sweeney", next_="/record/npc:old-tom")
    assert "didact link npc:old-tom ally npc:sweeney" in linked.body
    assert {"rel": "ally", "to": "npc:sweeney"} in shown(cli, "npc:old-tom")["links"]
    assert "Linked from" in web.get("/record/npc:sweeney").body

    web.run("note", "npc:old-tom", "Owes Sweeney a boat.", next_="/record/npc:old-tom")
    assert "Owes Sweeney a boat." in shown(cli, "npc:old-tom")["body"]

    delete = records.delete_command()  # `rm`, or `delete` once it's called that
    refused = web.run(delete, "npc:sweeney", next_="/record/npc:sweeney", next_ok="/records")
    assert refused.url.startswith(web.base + "/record/npc:sweeney")
    assert "still referenced" in refused.body and "--unlink" in refused.body
    assert "Delete and remove those links" in refused.body
    assert cli("show", "npc:sweeney").code == 0

    gone = web.run(
        *records.delete_argv("npc:sweeney", unlink=True),
        next_="/record/npc:sweeney",
        next_ok="/records",
    )
    assert gone.url.startswith(web.base + "/records")
    assert cli("show", "npc:sweeney").code != 0
    assert "ally" not in json.dumps(shown(cli, "npc:old-tom").get("links", []))

    undone = web.run("undo", next_="/records")
    assert "didact undo" in undone.body
    assert cli("show", "npc:sweeney").code == 0


def test_the_toast_undo_takes_back_that_change(web: Browser, cli: Cli) -> None:
    page = web.post(
        "/run",
        {
            "action": "set",
            "ref": "npc:sweeney",
            "key": "mood",
            "value": "grim",
            "next": "/record/npc:sweeney",
        },
    )
    target = re.search(r'name="w" value="(e\d+)"', page.body)
    assert target is not None, "the result offers an Undo"
    assert shown(cli, "sweeney")["fields"]["mood"] == "grim"
    web.run("undo", "--event", target.group(1), next_="/record/npc:sweeney")
    assert "mood" not in shown(cli, "sweeney").get("fields", {})


def test_a_failed_form_says_why_and_keeps_what_was_typed(web: Browser, cli: Cli) -> None:
    page = web.post(
        "/run",
        {
            "action": "new",
            "type": "Not A Type",
            "name": "Ghost",
            "body": "kept text",
            "next": "/records/new",
            "next_ok": "@record",
        },
    )
    assert page.url.startswith(web.base + "/records/new")
    assert "invalid entity type" in page.body and "kept text" in page.body
    assert cli("find", "Ghost").out.startswith("0 results")
    nothing = web.post(
        "/run", {"action": "edit", "ref": "npc:sweeney", "name": "Sweeney", "was.name": "Sweeney"}
    )
    assert "nothing changed" in nothing.body


def test_dry_runs_change_nothing(web: Browser, cli: Cli) -> None:
    page = web.post(
        "/run",
        {"action": "new", "type": "npc", "name": "Maybe", "dry_run": "1", "next": "/records/new"},
    )
    assert "dry run" in page.body
    assert cli("show", "Maybe").code != 0


# ---------------------------------------------------------------------------- command forms


def test_command_forms_follow_the_parameters(web: Browser) -> None:
    show = field_names(web.get("/commands/show").body)
    assert {"a.ref", "a.gm", "detail"} <= show and "dry_run" not in show  # positional, flag
    log = web.get("/commands/log").body
    assert '<select class="entry" name="a.kind"' in log  # a choice
    assert '<option value="consequence">consequence</option>' in log
    new = web.get("/commands/new").body
    assert '<textarea class="entry" name="a.tag"' in new  # a repeated option
    assert {"a.type", "a.name", "a.set", "a.fill", "dry_run", "reason"} <= field_names(new)
    roll = web.get("/commands/roll").body
    assert '<textarea class="entry" name="a.expression"' in roll  # *args
    filled = web.get("/commands/show?a.ref=npc:sweeney").body
    assert 'name="a.ref" value="npc:sweeney"' in filled


def test_command_forms_build_argument_lists() -> None:
    load_all()
    new = REGISTRY["new"]
    form = {
        "a.type": ["npc"],
        "a.name": ["Old Tom"],
        "a.tag": ["smuggler\r\n\r\ntall"],
        "a.body": ["- limps"],
        "a.fill": ["1"],
        "dry_run": ["1"],
        "reason": ["testing"],
    }
    assert command_argv(new, form) == [
        "new", "npc", "Old Tom", "--tag", "smuggler", "--tag", "tall", "--body=- limps",
        "--fill", "--dry-run", "--reason", "testing",
    ]  # fmt: skip
    roll = REGISTRY["roll"]
    assert command_argv(roll, {"a.expression": ["-1+d6"]}) == ["roll", "--", "-1+d6"]
    assert command_argv(roll, {"a.expression": ["d20 <= 12"], "detail": ["1"]}) == [
        "roll", "d20 <= 12", "--detail", "full",
    ]  # fmt: skip


def test_a_command_form_runs_and_shows_its_result(web: Browser, cli: Cli) -> None:
    page = web.post(
        "/run",
        {
            "action": "command",
            "cmd": "roll",
            "a.expression": "2d6",
            "next": "/commands/roll",
            "show": "panel",
        },
    )
    assert page.url.startswith(web.base + "/commands/roll")
    assert "$ didact roll 2d6" in page.body and "#r" in page.body
    assert "Undo" in page.body  # a roll can be taken back
    listed = web.post(
        "/run", {"action": "command", "cmd": "find", "a.type": "loc", "next": "/commands/find"}
    )
    assert "didact find --type loc" in listed.body and "Amber Grave" in listed.body
    assert cli("rolls").out.count("2d6") >= 1


def test_the_command_line_box(web: Browser) -> None:
    rolled = web.post(
        "/run",
        {"action": "line", "line": "didact roll '2d6+1'", "show": "panel", "next": "/commands"},
    )
    assert "$ didact roll 2d6+1" in rolled.body
    helped = web.post("/run", {"action": "line", "line": "roll --help", "next": "/commands"})
    assert "didact help roll" in helped.body and "Quote the expression" in helped.body
    refused = web.post("/run", {"action": "line", "line": "batch --file x", "next": "/commands"})
    assert "doesn&#x27;t run in the browser" in refused.body
    garbled = web.post("/run", {"action": "line", "line": "log note 'open", "next": "/commands"})
    assert "check its quotes" in garbled.body
    served = web.post("/run", {"action": "line", "line": "serve", "next": "/commands"})
    assert "already running" in served.body


def test_rules_run_from_their_form(web: Browser) -> None:
    page = web.post(
        "/run",
        {
            "action": "do",
            "rule": "save",
            "r.who": "sweeney",
            "r.attr": "STR",
            "next": "/rules/save",
            "show": "panel",
        },
    )
    assert "$ didact do mini-system.save who=sweeney attr=STR" in page.body
    rolled = web.run("table", "roll", "weather", next_="/reference", show="panel")
    assert "didact table roll weather" in rolled.body and "#r" in rolled.body


# ---------------------------------------------------------------------------- the graph


def test_the_graph_json_is_player_safe(web: Browser, cli: Cli) -> None:
    data = web.get("/api/graph").json()
    ids = {node["id"] for node in data["nodes"]}
    assert {"npc:sweeney", "loc:amber-grave"} <= ids and "npc:hidden-heir" not in ids
    edge = {"source": "npc:sweeney", "target": "loc:amber-grave", "rel": "lives-at"}
    assert edge in data["edges"]
    assert {"npc", "loc"} <= {t["type"] for t in data["types"]}
    around = web.get("/api/graph?focus=loc:amber-grave&depth=1").json()
    assert {n["id"] for n in around["nodes"]} == {"loc:amber-grave", "npc:sweeney"}
    assert around["focus"] == "loc:amber-grave"
    assert "error" in web.get("/api/graph?focus=npc:hidden-heir").json()
    cli("link", "npc:hidden-heir", "hides-in", "loc:amber-grave")
    assert "npc:hidden-heir" not in {n["id"] for n in web.get("/api/graph").json()["nodes"]}
    web.gm(True)
    seen = web.get("/api/graph").json()
    assert "npc:hidden-heir" in {n["id"] for n in seen["nodes"]}
    secret = next(n for n in seen["nodes"] if n["id"] == "npc:hidden-heir")
    assert secret["knowledge"] == "secret"
    focused = web.get("/graph?focus=npc:sweeney&depth=2").body
    assert "/api/graph?focus=npc%3Asweeney&amp;depth=2" in focused
    cli("new", "item", "Chest")
    cli("inv", "add", "loc:amber-grave", "item:chest")
    holds = {"source": "loc:amber-grave", "target": "item:chest", "rel": "holds"}
    assert holds in web.get("/api/graph").json()["edges"]  # what holds what, as edges


# ---------------------------------------------------------------------------- player safety


def test_secrets_stay_hidden_until_the_gm_view_is_on(web: Browser) -> None:
    listed = web.get("/records").body
    assert "Hidden Heir" not in listed and "1 secret record hidden" in listed
    secret = web.get("/record/npc:hidden-heir").body
    assert "This record is secret" in secret and "Hidden Heir" not in secret
    sweeney = web.get("/record/npc:sweeney").body
    assert "rightful heir" not in sweeney and "1 secret line hidden" in sweeney
    assert 'name="body"' not in sweeney  # no editor that would lose the secret lines
    assert "GM view: spoilers shown" not in sweeney
    assert "rightful heir" not in web.get("/search?q=heir").body

    turned = web.gm(True)
    assert "GM view: spoilers shown" in turned.body
    assert "Hidden Heir" in web.get("/records").body
    assert "rightful heir" in web.get("/record/npc:sweeney").body
    assert 'name="body"' in web.get("/record/npc:sweeney").body
    assert "Hidden Heir" in web.get("/record/npc:hidden-heir").body

    web.gm(False)
    assert "Hidden Heir" not in web.get("/records").body


def test_gm_view_can_start_on(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    cli("new", "npc", "Hidden Heir", "--set", "knowledge=secret")
    server = WebServer(App(gm=True), "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        page = Browser(server).get("/records")
        assert "Hidden Heir" in page.body and "GM view: spoilers shown" in page.body
    finally:
        server.shutdown()
        server.server_close()


def test_text_from_the_library_is_escaped(web: Browser, cli: Cli) -> None:
    cli("new", "npc", "<script>alert(1)</script>", "--id", "xss",
        "--body", "<img src=x onerror=alert(1)> **bold**")  # fmt: skip
    page = web.get("/record/npc:xss").body
    assert "<script>alert(1)" not in page and "&lt;script&gt;alert(1)" in page
    assert "<img src=x" not in page and "<strong>bold</strong>" in page
    assert "<a href" not in str(markdown("[x](javascript:alert(1))"))


# ---------------------------------------------------------------------------- journal, library


def test_the_journal_shows_sessions_scenes_and_beats(web: Browser, cli: Cli) -> None:
    web.run("session", "start")
    web.run("scene", "new", "The Mill")
    web.run("log", "result", "The sap holds her fast")
    page = web.get("/journal").body
    assert "Session 1" in page and "Scene 1 · The Mill" in page
    assert "The sap holds her fast" in page
    alone = web.get("/journal/1?fragment=1").body
    assert "The sap holds her fast" in alone and "<html" not in alone
    assert web.get("/journal/1").status == 200


def test_the_library_switches_and_creates_worlds(web: Browser, cli: Cli) -> None:
    made = web.post(
        "/run",
        {
            "action": "words",
            "w": ["world", "new", "isles"],
            "o:--system": "mini-system",
            "o:--name": "",
            "next": "/library",
        },
    )
    assert "didact world new isles --system mini-system" in made.body
    assert json.loads(cli("world", "list", "--format", "json").out)["active"] == "isles"
    web.run("campaign", "open", "run", next_="/library")
    assert json.loads(cli("campaign", "list", "--format", "json").out)["active"] == "run"
    saved = web.run("save", "before the mill", next_="/library")
    assert "before the mill" in saved.body
    assert "before the mill" in web.get("/library").body


def test_the_library_deletes_campaigns_and_worlds(web: Browser, cli: Cli) -> None:
    cli("world", "new", "isles")
    cli("campaign", "new", "spare", "--world", "isles")
    library = web.get("/library").body
    assert "/library/delete?campaign=spare" in library and "/library/delete?world=isles" in library
    asked = web.get("/library/delete?campaign=spare").body
    assert "Delete the campaign “spare”?" in asked and "didact campaign delete spare --yes" in asked
    gone = web.run("campaign", "delete", "spare", "--yes", next_="/library")
    assert "deleted campaign spare" in gone.body
    assert "spare" not in cli("campaign", "list").out
    web.run("world", "delete", "isles", "--yes", next_="/library")
    assert "isles" not in cli("world", "list").out
    assert cli("undo").code == 0 and "isles" in cli("world", "list").out  # it comes back


def test_the_library_installs_and_uninstalls_packs(
    web: Browser, cli: Cli, lucky: Path, tmp_path: Path
) -> None:
    library = web.get("/library").body
    assert "always on" in library and "in use" in library  # core and the system stay
    assert "/library/uninstall?pack=core" not in library
    assert cli("pack", "export", "lucky", "--to", str(tmp_path)).code == 0
    installed = web.run(
        "pack", "install", str(tmp_path / "lucky-0.1.0.didactpack"), next_="/library"
    )
    assert "installed lucky 0.1.0" in installed.body
    assert "/library/uninstall?pack=lucky&amp;version=0.1.0" in web.get("/library").body
    asked = html.unescape(web.get("/library/uninstall?pack=lucky&version=0.1.0").body)
    assert "Uninstall lucky 0.1.0?" in asked and "can't be undone" in asked
    removed = web.run("pack", "uninstall", "lucky", "0.1.0", "--yes", next_="/library")
    assert "removed lucky 0.1.0" in removed.body


def test_the_library_clears_the_history_and_keeps_backups(web: Browser, cli: Cli) -> None:
    web.run("save", "before", next_="/library")
    library = web.get("/library").body
    assert "/library/clear-history" in library and "No backups yet." in library
    assert "Remove “before”" in library  # a save point can go (and come back with undo)
    asked = web.get("/library/clear-history").body
    assert "Clear the history?" in asked and "Clearing would drop" in asked
    assert "didact history --clear --yes" in asked and "Back up first" in asked
    assert "save points removed" in asked
    rolls = web.get("/library/clear-history?rolls=1").body
    assert "didact history --clear --rolls --yes" in rolls and "#check-square" in rolls

    web.run("snapshot", next_="/library")
    web.run("snapshot", next_="/library")
    names = [
        b["name"]
        for b in json.loads(cli("snapshot", "--list", "--format", "json").out)["snapshots"]
    ]
    library = web.get("/library").body
    assert all(f"/library/remove-backup?name={name}" in library for name in names)
    asked = html.unescape(web.get(f"/library/remove-backup?name={names[0]}").body)
    assert f"Delete the backup {names[0]}?" in asked and "can't be undone" in asked
    kept = web.post(
        "/run", {"action": "words", "w": ["snapshot"], "o:--keep": "1", "next": "/library"}
    )
    assert "didact snapshot --keep 1" in kept.body and "deleted 1 backup" in kept.body
    gone = web.run("snapshot", "--remove", names[1], next_="/library")
    assert f"deleted backup {names[1]}" in gone.body and "No backups yet." in gone.body

    cleared = web.run("history", "--clear", "--yes", next_="/library#history")
    assert "cleared" in cleared.body and "Remove “before”" not in cleared.body
    history = json.loads(cli("history", "--format", "json").out)["events"]
    marker = next(e for e in history if e["kind"] == "note")
    assert f'"e{marker["seq"]}"' not in web.get("/library").body  # the mark has no Undo
    web.run("history", "--clear", "--yes")  # the save point's removal was a change too
    assert "Nothing to clear" in web.get("/library/clear-history").body


def test_the_serve_command_hands_over_to_the_web_app(
    cli: Cli, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import didact.web

    seen: dict[str, object] = {}
    monkeypatch.setattr(didact.web, "serve", lambda **kwargs: seen.update(kwargs))
    home = tmp_path / "elsewhere"
    result = cli("--home", str(home), "serve", "--port", "9000", "--gm", "--campaign", "run")
    assert result.code == 0 and "stopped" in result.out
    assert seen["port"] == 9000 and seen["gm"] is True and seen["host"] == "127.0.0.1"
    assert seen["home"] == str(home) and seen["campaign"] == "run"
    assert seen["open_browser"] is False
    assert "--open" in cli("help", "serve").out


def test_the_app_passes_on_its_global_options(cli: Cli, tmp_path: Path) -> None:
    other = tmp_path / "other-home"
    cli("--home", str(other), "world", "new", "far", "--system", "mini-system")
    cli("--home", str(other), "new", "npc", "Distant Dan")
    app = App(home=str(other))
    ran = app.run(["show", "Distant Dan"])
    assert ran.ok and ran.line == "didact show 'Distant Dan'"
    assert app.globals()[:2] == ["--home", str(other)]


# ---------------------------------------------------------------------------- hidden info


def test_hidden_info_renders_when_show_has_it(home: Path) -> None:
    app = App(gm=True)
    req = Request(app, "GET", "/record/item:silver-key")
    data: dict[str, Any] = {
        "details": {"looks": "tarnished, warm to the touch", "history": "forged for the king"},
        "suggested": ["plan", "secret"],
        "where": [
            {"id": "item:chest", "name": "Chest"},
            {"id": "loc:my-house", "name": "My House"},
        ],
        "contents": [
            {"name": "Pouch", "ref": "item:pouch", "contents": [{"name": "coin", "count": 3}]},
            {"name": "rope"},
        ],
        "chronicle": [
            {"id": "S2.3", "session": 2, "scene": 3, "kind": "consequence",
             "text": "Freya pockets the key", "importance": 8, "secret": True,
             "about": ["pc:freya"]},
        ],
    }  # fmt: skip
    where = str(records._where(data))
    assert "in " in where and "Chest</a> › <a" in where and record_url("loc:my-house") in where
    details = str(records._details(req, "item:silver-key", data))
    assert "tarnished, warm to the touch" in details and "forged for the king" in details
    assert details.count('class="gm-mark"') == 1  # history is GM only; looks isn't
    assert "detail=plan" in details and "Not filled in yet" in details
    tree = str(records._contents(data, {}))
    assert tree.count('class="tree"') == 2 and "×3" in tree and record_url("item:pouch") in tree
    story = str(records._chronicle(data, {"pc:freya": "Freya"}))
    assert "S2.3" in story and "Freya pockets the key" in story and ">Freya</a>" in story
    assert 'class="gm-mark"' in story
    assert records._chronicle({}, {}) is None and records._where({}) is None
    assert str(h(t"{records._contents({}, {})}")) == ""


def test_destructive_actions_ask_first_even_without_js(web: Browser, cli: Cli) -> None:
    page = web.get("/record/npc:sweeney")
    assert 'href="/record/npc:sweeney/delete" data-confirm-form' in page.body
    assert 'data-confirm="Delete Sweeney?"' in page.body  # the dialog, with JS
    asked = web.get("/record/npc:sweeney/delete").body  # the page, without
    delete = records.delete_command()
    assert "Delete Sweeney?" in asked and f"$ didact {delete} npc:sweeney" in asked
    assert f'name="w" value="{delete}"' in asked
    unlinking = web.get("/record/npc:sweeney/delete?unlink=1").body
    assert f"didact {delete} npc:sweeney --unlink" in unlinking
    cli("save", "start")
    saves = web.get("/library").body
    assert "/library/rewind?save=start" in saves and "Rewind to “start”?" in saves
    assert "didact rewind start" in web.get("/library/rewind?save=start").body


def test_details_are_edited_with_about(web: Browser, cli: Cli) -> None:
    if "about" not in REGISTRY:
        pytest.skip("`didact about` isn't there yet")
    page = web.post(
        "/run",
        {
            "action": "about",
            "ref": "npc:sweeney",
            "name": "looks",
            "text": "tall, sap on his hands",
            "next": "/record/npc:sweeney",
        },
    )
    assert "didact about npc:sweeney &#x27;looks=tall, sap on his hands&#x27;" in page.body
    assert shown(cli, "sweeney")["details"]["looks"] == "tall, sap on his hands"
    web.post(
        "/run", {"action": "about", "ref": "npc:sweeney", "name": "wants", "text": "the crown"}
    )
    player = web.get("/record/npc:sweeney").body
    assert "tall, sap on his hands" in player and "the crown" not in player
    web.gm(True)
    assert "the crown" in web.get("/record/npc:sweeney").body


def test_older_sessions_load_when_opened(web: Browser, cli: Cli) -> None:
    for number in range(1, 6):
        cli("session", "start")
        cli("log", "note", f"Beat of session {number}")
        cli("session", "end", "--summary", f"Session {number} went well.")
    page = web.get("/journal").body
    assert 'data-fragment="/journal/1?fragment=1"' in page  # the oldest waits to be opened
    assert "Beat of session 5" in page and "Beat of session 1" not in page
    assert "Session 1 went well." in page  # its summary shows anyway
    assert "Beat of session 1" in web.get("/journal/1?fragment=1").body


def test_head_requests_and_asset_versions(web: Browser) -> None:
    assert raw(web.port, "/records", {"Host": f"127.0.0.1:{web.port}"}, method="HEAD") == 200
    page = web.get("/").body
    version = re.search(r'/static/style\.css\?v=(\w+)"', page)
    assert version is not None
    fresh = web.get(f"/static/style.css?v={version.group(1)}")
    assert "immutable" in fresh.headers["Cache-Control"]
    assert web.get("/static/style.css").headers["Cache-Control"] == "no-cache"


@pytest.mark.slow
def test_didact_serve_runs_until_interrupted(cli: Cli) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    process = subprocess.Popen(
        [sys.executable, "-m", "didact", "serve", "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        assert process.stdout is not None
        first = process.stdout.readline()
        found = re.search(r"http://127\.0\.0\.1:\d+/", first)
        assert found, first
        with urllib.request.urlopen(found.group(0), timeout=30) as response:
            assert response.status == 200
        process.send_signal(signal.SIGINT)
        rest, _ = process.communicate(timeout=30)
        assert process.returncode == 0 and "stopped" in rest
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_the_command_line_box_keeps_the_format_asked_for(web: Browser) -> None:
    page = web.post(
        "/run", {"action": "line", "line": "find --type loc --format json", "next": "/commands"}
    )
    assert "<pre><code>{" in page.body and "&quot;loc:amber-grave&quot;" in page.body
