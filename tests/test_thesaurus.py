"""The thesaurus: one language in use at a time (switching back needs no download), and a
download that reports how far it is, on the command line and on the Settings page."""

import json
from pathlib import Path
from typing import Any

import pytest

from didact.core import words
from tests.conftest import Cli
from tests.test_web import Browser, web  # noqa: F401  (the fixture)

FRENCH = Path(__file__).parent / "fixtures" / "wordnet-mini-fr.xml"


def _json(cli: Cli, *argv: str) -> Any:
    return json.loads(cli(*argv, "--format", "json").out)


@pytest.mark.usefixtures("thesaurus")
def test_one_language_is_in_use(cli: Cli) -> None:
    assert "blade" in words.synonyms("sword")
    assert cli("setup", "thesaurus", "--from", str(FRENCH)).code == 0  # added, and now in use
    lexicons = {
        x["language"]: x["active"] for x in _json(cli, "setup", "thesaurus", "--check")["lexicons"]
    }
    assert lexicons == {"en": False, "fr": True}
    assert words.synonyms("épée") == ["lame"] and words.synonyms("sword") == []
    assert cli("setup", "thesaurus", "--lang", "en").code == 0  # back, without a download
    assert "blade" in words.synonyms("sword") and words.synonyms("épée") == []
    assert "English" not in cli("setup", "thesaurus", "--check").out.split("← in use")[0][-40:]
    assert cli("setup", "thesaurus", "--remove", "--lang", "en").code == 0
    assert words.active() == ("mini-fr", "fr")  # what's left is used


def test_a_download_reports_how_far_it_is(web: Browser, cli: Cli) -> None:  # noqa: F811
    assert "no download under way" in cli("setup", "thesaurus", "--progress").out
    assert web.get("/settings/thesaurus/progress").json() is None
    assert 'id="thesaurus-progress"' in web.get("/settings").body
    words._report(words.Progress("fr", "download", 5 * 1048576, 20 * 1048576))
    shown = _json(cli, "setup", "thesaurus", "--progress")["progress"]
    assert shown == {"language": "fr", "stage": "download", "count": 5242880,
                     "total": 20971520, "error": ""}  # fmt: skip
    assert web.get("/settings/thesaurus/progress").json()["count"] == 5242880
    page = web.get("/settings").body
    assert "Downloading fr…" in page and 'data-t-size="{done} of {total} MB"' in page
    words._report(words.Progress("fr", "failed", 0, 0, "no network"))
    assert "The download failed: no network" in web.get("/settings").body


def test_the_settings_page_starts_a_download_in_its_own_process(
    web: Browser,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started: list[list[str]] = []
    monkeypatch.setattr("subprocess.Popen", lambda argv, **_kw: started.append(argv))
    web.post("/settings/thesaurus/download", {"lang": "klingon"})
    assert started == []  # not a wordnet language
    web.post("/settings/thesaurus/download", {"lang": "fr"})
    assert started and started[0][-4:] == ["setup", "thesaurus", "--lang", "fr"]
    assert words.progress() == words.Progress("fr", "download", 0, 0)
    web.post("/settings/thesaurus/download", {"lang": "de"})
    assert len(started) == 1  # one download at a time
