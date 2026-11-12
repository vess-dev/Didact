"""`didact export --as site`: a player-safe website of the campaign, in a folder of its own."""

import html
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from didact.services.site import page_name
from tests.conftest import Cli, Run

PAGE = re.compile(r"[a-z0-9-]+_[a-z0-9-]+\.html")


def export(cli: Cli, folder: Path) -> Run:
    return cli("export", "--as", "site", "--to", str(folder))


def export_data(cli: Cli, folder: Path) -> Any:  # parsed JSON, read freely in tests
    done = cli("export", "--as", "site", "--to", str(folder), "--format", "json")
    assert done.code == 0, done.err
    return json.loads(done.out)


def site_files(folder: Path) -> dict[str, str]:
    """Every file the folder holds (path in it → text)."""
    return {
        path.relative_to(folder).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def play(cli: Cli) -> None:
    """A little of everything the site shows: the party, people, places, things, a session."""
    for argv in (
        ("world", "new", "vale", "--system", "mini-system", "--description", "A drowned vale."),
        ("campaign", "new", "withering", "--name", "The Withering"),
        ("new", "pc", "Freya", "--set", "STR=12", "--set", "hp=4"),
        ("about", "freya", "looks=red cloak"),
        ("inv", "add", "freya", "Rope"),
        ("new", "npc", "Tom", "--body", "Runs the *mill*."),
        ("about", "tom", "looks=tall, floury"),
        ("link", "freya", "rival", "tom"),
        ("new", "loc", "The Mill"),
        ("new", "loc", "The Wood"),
        ("new", "loc", "Amber Grave", "--set", "region=loc:the-wood"),
        ("link", "The Mill", "road", "The Wood"),
        ("visit", "The Mill"),
        ("new", "item", "Chest"),
        ("new", "item", "Ring"),
        ("inv", "add", "the mill", "item:chest"),
        ("inv", "add", "chest", "item:ring"),
        ("session", "start", "Arrival"),
        ("scene", "new", "Opening"),
        ("log", "consequence", "Tom lied about the flour", "--about", "tom", "--about", "freya"),
        ("scene", "end", "--summary", "They met Tom."),
        ("session", "end", "--summary", "Freya reached the mill."),
    ):
        done = cli(*argv)
        assert done.code == 0, (argv, done.err)


def test_the_site_shows_what_the_players_know(cli: Cli, tmp_path: Path) -> None:
    play(cli)
    folder = tmp_path / "site"
    done = export(cli, folder)
    where = folder.resolve()
    assert done.code == 0, done.err
    assert done.out.startswith(f"✔ exported the site to {where}: 10 pages\nopen {where}/index.html")
    data = export_data(cli, folder)
    assert data["pages"] == 10 and data["records"] == 7 and data["folder"] == str(where)
    files = site_files(folder)
    assert set(files) == {
        ".didact-site", "favicon.svg", "index.html", "journal.html", "map.html", "style.css",
        *(f"records/{page_name(i)}" for i in (
            "pc:freya", "npc:tom", "loc:the-mill", "loc:the-wood", "loc:amber-grave",
            "item:chest", "item:ring",
        )),
    }  # fmt: skip
    index = files["index.html"]
    assert "<h1>The Withering</h1>" in index and '<p class="eyebrow">Vale</p>' in index
    assert "A drowned vale." in index and "Freya reached the mill." in index
    assert "red cloak" in index and '<span class="tile-label">STR</span>' in index
    assert '<span class="tile-value">12</span>' in index and "4/4" in index
    assert '<h2>NPCs <span class="count">1</span></h2>' in index
    assert '<a class="row" href="records/npc_tom.html">' in index
    tom = files["records/npc_tom.html"]
    assert "<p>Runs the <em>mill</em>.</p>" in tom and "tall, floury" in tom
    assert '<a href="pc_freya.html">Freya</a>' in tom.split("Linked from")[1]
    assert "Tom lied about the flour" in tom.split("Chronicle")[1]
    assert '<a class="beat-where" href="../journal.html#beat-s1-1">S1.1</a>' in tom
    freya = files["records/pc_freya.html"]
    assert "<h2>Carrying</h2>" in freya and "<li>Rope</li>" in freya
    ring = files["records/item_ring.html"]
    assert (
        '<p class="where">In <a href="item_chest.html">Chest</a> › '
        'at <a href="loc_the-mill.html">The Mill</a></p>'
    ) in ring
    grave = files["records/loc_amber-grave.html"]
    assert '<p class="where">In <a href="loc_the-wood.html">The Wood</a></p>' in grave
    journal = files["journal.html"]
    assert '<section class="card session" id="session-1"><h2>Session 1 · Arrival' in journal
    assert '<h3 id="scene-1">Scene 1 · Opening</h3>' in journal and "They met Tom." in journal
    atlas = files["map.html"]
    assert 'The party is at <a href="records/loc_the-mill.html">The Mill</a>' in atlas
    assert 'road → <a href="records/loc_the-wood.html">The Wood</a>' in atlas
    assert "stylesheet" in index and "<script" not in "".join(files.values())


# ---------------------------------------------------------------------------- the sweep

MARKER = re.compile(r"qx\d+", re.IGNORECASE)
HIDING_PLACES = {
    "QX1": "a secret record's name, id and text",
    "QX2": "a `## Secrets` section",
    "QX3": "a `## GM notes` section",
    "QX4": "a field kept secret by `extra.secret_keys`",
    "QX5": "a `secret: true` sheet field",
    "QX6": "a GM detail",
    "QX7": "a secret beat",
    "QX8": "the transcript",
    "QX9": "a secret place",
    "QX10": "bookkeeping in `extra`",
    "QX11": "a secret item in a public inventory",
    "QX12": "a secret holder in a `where` chain",
    "QX13": "a secret quest",
    "QX14": "a secret section of a session's summary",
    "QX15": "a secret scene's title",
    "QX16": "a secret section of the world's description",
    "QX17": "a hidden path",
    "QX18": "a secret record named in public fields, by id and by name",
}
VEILED = """\
type: npc
extends: character
fields:
  omen: {kind: text, secret: true}
---
type: pc
extends: character
fields:
  omen: {kind: text, secret: true}
"""


def plant(cli: Cli, home: Path) -> None:
    """A marker in every place a secret can hide, each beside something the players know."""
    world = "A drowned vale.\n\n## Secrets\nQX16 the vale was drowned on purpose."
    body = "Runs the mill.\n\n## Secrets\nQX2 he poisoned the well.\n\n## GM notes\nQX3 pay it off"
    cli("world", "new", "vale", "--system", "mini-system", "--description", world)
    homebrew = home / "systems" / "mini-system" / "homebrew" / "schemas"
    homebrew.mkdir(parents=True)
    (homebrew / "veiled.yaml").write_text(VEILED, encoding="utf-8")  # a secret sheet field
    summary = "Freya reached the mill.\n\n### Secrets\nQX14 she was followed."
    for argv in (
        ("campaign", "new", "withering"),
        ("new", "pc", "Freya", "--fill"),
        ("set", "freya", "omen=QX5 doom"),
        ("new", "npc", "Tom", "--body", body),
        ("set", "tom", "true_name=QX4", 'extra.secret_keys=["fields.true_name"]'),
        ("set", "tom", "omen=QX5 flood", "extra.ledger=QX10"),
        ("about", "tom", "looks=tall", "plan=QX6 flee", "doing=QX6 whittling"),
        ("new", "npc", "QX1 Heir", "--set", "knowledge=secret", "--body", "QX1 body"),
        ("link", "tom", "serves", "QX1 Heir"),
        ("link", "QX1 Heir", "watches", "tom"),
        ("new", "npc", "QX18 Spy", "--set", "knowledge=secret"),
        ("set", "tom", "patron=npc:qx18-spy", "contact=QX18 Spy"),
        ("new", "loc", "The Mill"),
        ("new", "loc", "The Wood"),
        ("new", "loc", "QX9 Shrine", "--set", "knowledge=secret"),
        ("link", "The Mill", "path", "QX9 Shrine"),
        ("link", "The Mill", "hidden-qx17", "The Wood"),
        ("visit", "The Mill"),
        ("new", "item", "QX11 Relic", "--set", "knowledge=secret"),
        ("inv", "add", "tom", "item:qx11-relic"),
        ("new", "item", "QX12 Coffer", "--set", "knowledge=secret"),
        ("new", "item", "Ring"),
        ("inv", "add", "the mill", "item:qx12-coffer"),
        ("inv", "add", "QX12 Coffer", "item:ring"),
        ("quest", "new", "QX13 plot"),
        ("set", "QX13 plot", "knowledge=secret"),
        ("session", "start"),
        ("scene", "new", "Opening"),
        ("log", "consequence", "Tom lied", "--about", "tom", "--about", "npc:qx1-heir"),
        ("log", "note", "QX7 raiders gather", "--secret", "--about", "tom"),
        ("capture", "--role", "gm", "--text", "QX8 the transcript"),
        ("scene", "new", "QX15 Ambush"),
        ("set", "scene:2", "knowledge=secret"),
        ("session", "end", "--summary", summary),
    ):
        done = cli(*argv)
        assert done.code == 0, (argv, done.err)


def test_no_secret_reaches_the_site(cli: Cli, home: Path, tmp_path: Path) -> None:
    plant(cli, home)
    folder = tmp_path / "site"
    assert export(cli, folder).code == 0
    files = site_files(folder)
    leaks = [
        f"{path}: {marker} ({HIDING_PLACES.get(marker, '?')})"
        for path, text in files.items()  # a file's name too: a page's name holds an id
        for marker in sorted({m.upper() for m in MARKER.findall(path + html.unescape(text))})
    ]
    assert not leaks, "\n".join(leaks)
    tom = files["records/npc_tom.html"]  # what the players know of it is all there
    assert "Runs the mill." in tom and "tall" in tom and "Tom lied" in tom
    assert "path → ?" in files["map.html"] and "path → ?" in files["records/loc_the-mill.html"]
    index = files["index.html"]
    assert "Freya reached the mill." in index and "A drowned vale." in index
    assert "records/item_ring.html" in files and "Opening" in files["journal.html"]
    gm = "".join(
        cli(*argv).out
        for argv in (
            ("show", "tom", "--gm"),
            ("show", "freya", "--gm"),
            ("show", "the mill", "--gm"),
            ("map", "--gm"),
            ("session", "show", "1", "--gm", "--detail", "full"),
            ("world", "show", "--gm"),
            ("quest", "list", "--gm"),
        )
    )
    missing = [m for m in HIDING_PLACES if m not in gm.upper()]
    assert not missing, missing  # the sweep isn't vacuous: each marker is really there


# ---------------------------------------------------------------------------- links, HTML


def test_every_link_leads_to_a_page_of_the_site(cli: Cli, tmp_path: Path) -> None:
    play(cli)
    cli("new", "npc", "Wren", "--body", "See [Tom](https://example.org/tom) and [the mill](#).")
    folder = tmp_path / "site"
    assert export(cli, folder).code == 0
    files = site_files(folder)
    checked = 0
    for path, text in files.items():
        if not path.endswith(".html"):
            continue
        for target in re.findall(r'(?:href|src)="([^"]*)"', text):
            target = html.unescape(target)
            if target.startswith("https://"):
                continue  # a link someone wrote into a record's text
            parts = urlsplit(target)
            assert not parts.scheme and not parts.netloc and not target.startswith("/"), target
            page = (folder / path).parent / unquote(parts.path) if parts.path else folder / path
            page = page.resolve()
            assert page.is_relative_to(folder.resolve()), (path, target)
            rel = page.relative_to(folder.resolve()).as_posix()
            assert rel in files, (path, target)
            if parts.fragment:
                assert f'id="{parts.fragment}"' in files[rel], (path, target)
            checked += 1
    assert checked > 50


def test_html_in_the_library_stays_text(cli: Cli, tmp_path: Path) -> None:
    tom = "npc:b-bold-b-tom"
    body = (
        "<script>alert(1)</script>\n\n[click me](javascript:alert(1)) "
        '<img src=x onerror="alert(2)"> ![pic](https://example.org/p.png)\n\n'
        "## Secrets\n<script>alert(3)</script>"
    )
    for argv in (
        ("world", "new", "vale", "--system", "mini-system"),
        ("campaign", "new", "run"),
        ("new", "npc", "<b>Bold</b> Tom", "--body", body, "--tag", '"><script>'),
        ("about", tom, "looks=<i onmouseover=alert(4)>tall</i>"),
        ("session", "start", "<script>alert(5)</script>"),
        ("log", "note", "<script>alert(6)</script> [x](javascript:alert(7))", "--about", tom),
        ("session", "end", "--summary", "<iframe src=javascript:alert(8)></iframe>"),
    ):
        done = cli(*argv)
        assert done.code == 0, (argv, done.err)
    folder = tmp_path / "site"
    assert export(cli, folder).code == 0
    files = site_files(folder)
    pages = {path: text for path, text in files.items() if path.endswith(".html")}
    for path, text in pages.items():
        tags = re.findall(r"<[^>]*>", text)  # escaped text can't hold a `<`: these are all tags
        names = {re.split(r"[\s/>]", tag[1:], maxsplit=1)[0].lower() for tag in tags}
        assert not names & {"script", "img", "iframe", "i", "b"}, (path, names)
        for tag in tags:
            assert not re.search(r"\son[a-z]+\s*=", re.sub(r'"[^"]*"', '""', tag)), (path, tag)
        for target in re.findall(r'href="([^"]*)"', text):
            clean = re.sub(r"[\x00-\x20]", "", html.unescape(target)).lower()
            assert not clean.startswith(("javascript:", "data:", "vbscript:")), (path, target)
    page = pages["records/npc_b-bold-b-tom.html"]
    assert "<title>&lt;b&gt;Bold&lt;/b&gt; Tom · Run</title>" in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page and "alert(3)" not in page
    assert "[click me](javascript:alert(1))" in page  # shown as text, not a link
    assert '!<a href="https://example.org/p.png">pic</a>' in page  # a link, not a download
    assert "&lt;i onmouseover=alert(4)&gt;tall&lt;/i&gt;" in page
    assert "&lt;script&gt;alert(6)&lt;/script&gt;" in pages["journal.html"]
    assert "Content-Security-Policy" in page and "script-src &#x27;none&#x27;" in page


# ---------------------------------------------------------------------------- the folder


def test_the_folder_belongs_to_the_site(cli: Cli, tmp_path: Path) -> None:
    play(cli)
    missing = cli("export", "--as", "site")
    assert missing.code == 2 and "--to" in missing.err
    assert cli("export", "--as", "site", "--scope", "all", "--to", str(tmp_path / "x")).code == 2
    assert not (tmp_path / "x").exists()
    foreign = tmp_path / "notes"
    foreign.mkdir()
    (foreign / "notes.txt").write_text("mine", encoding="utf-8")
    refused = export(cli, foreign)
    assert refused.code == 1 and "isn't empty, and no site was exported there" in refused.err
    assert [p.name for p in foreign.iterdir()] == ["notes.txt"]
    assert export(cli, foreign / "notes.txt").code == 1  # a file, not a folder
    finder = tmp_path / "finder"
    finder.mkdir()
    (finder / ".DS_Store").write_bytes(b"\0")  # what a file manager leaves: still empty
    assert export(cli, finder).code == 0 and (finder / ".DS_Store").read_bytes() == b"\0"

    site = tmp_path / "site"
    assert export(cli, site).code == 0
    first = site_files(site)
    (site / "mine.txt").write_text("a stranger's", encoding="utf-8")
    (site / "records" / "mine.txt").write_text("a stranger's", encoding="utf-8")
    (site / "extra").mkdir()
    (site / "extra" / "notes.md").write_text("a stranger's", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("never touched", encoding="utf-8")
    listed = json.loads(first[".didact-site"])
    listed["files"] += ["../outside.txt", str(outside), "records/../../outside.txt"]
    (site / ".didact-site").write_text(json.dumps(listed), encoding="utf-8")
    assert cli("rm", "item:ring").code == 0
    cli("set", "tom", "mood=grim")
    again = export(cli, site)
    assert again.code == 0 and "note: removed 1 file the last export wrote" in again.out
    now = site_files(site)
    assert "records/item_ring.html" not in now and "grim" in now["records/npc_tom.html"]
    assert now["mine.txt"] == now["records/mine.txt"] == now["extra/notes.md"] == "a stranger's"
    assert outside.read_text(encoding="utf-8") == "never touched"
    written = set(json.loads(now[".didact-site"])["files"])
    assert written == set(now) - {".didact-site", "mine.txt", "records/mine.txt", "extra/notes.md"}

    (site / "records" / "npc_wren.html").write_text("a stranger's", encoding="utf-8")
    cli("new", "npc", "Wren")
    blocked = export(cli, site)  # a new page would overwrite a file the site didn't write
    assert blocked.code == 1 and "npc_wren.html is in the way" in blocked.err
    assert (site / "records" / "npc_wren.html").read_text(encoding="utf-8") == "a stranger's"
    assert site_files(site)[".didact-site"] == now[".didact-site"]  # nothing was written

    (site / "records" / "npc_wren.html").unlink()
    (site / "records" / "mine.txt").unlink()
    (site / "records" / "npc_tom.html").unlink()  # already gone: nothing to remove
    assert cli("world", "new", "empty", "--system", "mini-system").code == 0
    emptied = export(cli, site)
    assert emptied.code == 0 and "removed 5 files" in emptied.out
    assert not (site / "records").exists()  # no pages left: the folder they were in goes
    assert (site / "mine.txt").exists() and (site / "extra" / "notes.md").exists()


def test_the_site_never_writes_through_a_link(cli: Cli, tmp_path: Path) -> None:
    play(cli)
    site = tmp_path / "site"
    assert export(cli, site).code == 0
    victim = tmp_path / "victim.txt"
    victim.write_text("never touched", encoding="utf-8")
    (site / "index.html").unlink()
    (site / "index.html").symlink_to(victim)  # a page swapped for a link: replaced, not followed
    assert export(cli, site).code == 0
    assert victim.read_text(encoding="utf-8") == "never touched"
    assert (
        not (site / "index.html").is_symlink() and "The Withering" in site_files(site)["index.html"]
    )

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "keep.txt").write_text("never touched", encoding="utf-8")
    for page in (site / "records").iterdir():
        page.unlink()
    (site / "records").rmdir()
    (site / "records").symlink_to(elsewhere, target_is_directory=True)
    refused = export(cli, site)  # its pages would land outside the folder
    assert refused.code == 1 and "records is in the way" in refused.err
    assert [p.name for p in elsewhere.iterdir()] == ["keep.txt"]

    (tmp_path / "dangling").symlink_to(tmp_path / "nowhere")
    dangling = export(cli, tmp_path / "dangling")
    assert dangling.code == 1 and "is a link to nothing" in dangling.err
    assert not (tmp_path / "nowhere").exists()
    odd = tmp_path / "odd"
    odd.mkdir()
    (odd / ".didact-site").write_text('{"files": ["notes.txt"]}', encoding="utf-8")
    (odd / "notes.txt").write_text("mine", encoding="utf-8")
    unclear = export(cli, odd)  # a list that doesn't say it's a site's: nothing is replaced
    assert unclear.code == 1 and "doesn't list the files of a site" in unclear.err
    assert (odd / "notes.txt").read_text(encoding="utf-8") == "mine"


def test_an_empty_campaign(cli: Cli, tmp_path: Path) -> None:
    nowhere = export(cli, tmp_path / "none")
    assert nowhere.code == 1 and "no active world" in nowhere.err
    cli("world", "new", "vale", "--system", "mini-system")
    cli("campaign", "new", "quiet")
    folder = tmp_path / "site"
    done = export(cli, folder)
    assert done.code == 0 and ": 3 pages" in done.out
    files = site_files(folder)
    assert set(files) == {
        ".didact-site", "favicon.svg", "index.html", "journal.html", "map.html", "style.css"
    }  # fmt: skip
    assert "0 records · 0 sessions · 0 places" in files["index.html"]
    assert "Nothing yet." in files["index.html"] and "The party" not in files["index.html"]
    assert "No sessions yet." in files["journal.html"]
    assert "No places known yet." in files["map.html"]


def test_record_ids_with_odd_characters(cli: Cli, tmp_path: Path) -> None:
    cli("world", "new", "vale", "--system", "mini-system")
    for argv in (
        ("new", "a-b", "First", "--id", "c"),  # a-b:c
        ("new", "a", "Second", "--id", "b-c"),  # a:b-c: the same letters, another record
        ("new", "x--y", "Third", "--id", "z"),
        ("new", "npc", "One", "--id", "1"),
        ("new", "npc", "Évil ../../..\\name/.."),
        ("new", "npc", "CON"),
    ):
        done = cli(*argv)
        assert done.code == 0, (argv, done.err)
    folder = tmp_path / "site"
    assert export(cli, folder).code == 0
    pages = sorted(p.name for p in (folder / "records").iterdir())
    assert pages == [
        "a-b_c.html", "a_b-c.html", "npc_1.html", "npc_con.html", "npc_evil-name.html",
        "x--y_z.html",
    ]  # fmt: skip
    assert all(PAGE.fullmatch(name) for name in pages)
    assert all(p.resolve().is_relative_to(folder.resolve()) for p in folder.rglob("*"))
    evil = (folder / "records" / "npc_evil-name.html").read_text(encoding="utf-8")
    assert "<h1>Évil ../../..\\name/..</h1>" in evil
    assert export(cli, folder).code == 0  # stable: the same names again
    assert sorted(p.name for p in (folder / "records").iterdir()) == pages
    for odd in ("npc:../../etc", "a/b:c", "npc:x y", "npc:", "NPC:Tom", "npc:x\\y"):
        name = page_name(odd)
        assert re.fullmatch(r"record-[0-9a-f]{16}\.html", name), odd
        assert name == page_name(odd) and name != page_name(odd + "x")
    assert page_name("a-b:c") != page_name("a:b-c")


def test_the_site_speaks_the_language_asked_for(cli: Cli, tmp_path: Path) -> None:
    from didact.core import i18n
    from didact.core.i18n import _

    play(cli)
    assert export(cli, tmp_path / "en").code == 0
    english = site_files(tmp_path / "en")
    assert '<html lang="en"' in english["index.html"]
    assert "<h1>Journal</h1>" in english["journal.html"]
    assert "Player characters" in english["index.html"]

    done = cli("export", "--as", "site", "--lang", "fr", "--to", str(tmp_path / "fr"))
    assert done.code == 0, done.err
    assert done.out.startswith("✔ exported the site to")  # the command's own output stays English
    french = site_files(tmp_path / "fr")
    assert all('<html lang="fr"' in text for rel, text in french.items() if rel.endswith(".html"))
    with i18n.use("fr"):
        journal, players = _("Journal"), _("Player characters")
    if journal != "Journal":  # translated (the catalog may not have every new message yet)
        assert f"<h1>{html.escape(journal)}</h1>" in french["journal.html"]
        assert "<h1>Journal</h1>" not in french["journal.html"]
    if players != "Player characters":
        assert html.escape(players) in french["index.html"]
        assert "Player characters" not in french["index.html"]

    tagged = cli("export", "--as", "site", "--lang", "pt-BR", "--to", str(tmp_path / "pt"))
    assert tagged.code == 0, tagged.err
    assert '<html lang="pt-BR"' in site_files(tmp_path / "pt")["index.html"]


def test_an_unknown_export_language_is_refused(cli: Cli, tmp_path: Path) -> None:
    play(cli)
    done = cli("export", "--as", "story", "--lang", "xx")
    assert done.code != 0
    assert "unknown language 'xx'" in done.err and "pt-BR" in done.err
    story = cli("export", "--as", "story", "--lang", "fr")
    assert story.code == 0, story.err
    assert story.out.startswith("# The Withering")
