"""Loose matching for searches. A query word finds itself, its near spellings (a typo within
`NEAR_CUTOFF`, when it isn't there as typed) and its synonyms: one step away in the thesaurus,
never a synonym's synonyms. Exact matches count most, then near spellings, then synonyms.

The thesaurus is WordNet, through the `wn` library: the Open English WordNet, plus any other
languages added with `didact setup thesaurus`. Its data lives in Didact's cache folder
(`wordnet/`); without it, searches still match exact words and near spellings.
"""

import difflib
import json
import os
import re
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from types import ModuleType

from didact.core.config import ENV_CACHE, default_cache_dir
from didact.core.i18n import _
from didact.core.output import JSON

NEAR_CUTOFF = 0.8  # how alike a near spelling must be (difflib's ratio, 0 to 1)
EXACT, NEAR, SYNONYM = 1.0, 0.75, 0.6  # what each kind of match is worth
SYNONYMS_MAX = 15  # the most common senses' words first

_WORD = re.compile(r"\w+")


def tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.casefold()))


def stem(word: str) -> str:
    """Plurals fold into the singular: `goblins` finds `goblin`."""
    return word.rstrip("s") if len(word) > 3 else word


def wordnet_dir() -> Path:
    """Where the thesaurus's data lives (Didact's cache folder; `cache clear` leaves it)."""
    return Path(os.environ.get(ENV_CACHE) or default_cache_dir()).expanduser() / "wordnet"


def thesaurus_ready() -> bool:
    return (wordnet_dir() / "wn.db").is_file()


def synonyms(word: str) -> list[str]:
    """The words one step away from `word` in the thesaurus language in use (any form:
    `wolves` too)."""
    database = wordnet_dir() / "wn.db"
    if not database.is_file():
        return []
    lexicon = active()
    if lexicon is None:
        return []
    stamp = database.stat().st_mtime_ns
    return list(_synonyms(str(database.parent), stamp, lexicon, word.casefold()))


@cache
def _synonyms(folder: str, stamp: int, lexicon: tuple[str, str], word: str) -> tuple[str, ...]:
    wn = _wordnet(Path(folder))
    from wn.morphy import Morphy

    english = lexicon[1] == "en"  # Morphy knows English word forms only
    found: list[str] = []
    try:
        reader = wn.Wordnet(lexicon[0], lemmatizer=Morphy() if english else None)
        senses = reader.synsets(word)  # `wolves` finds `wolf`'s
    except wn.Error:
        return ()
    for synset in senses:
        for lemma in synset.lemmas():
            text = str(lemma).replace("_", " ").casefold()
            if text != word and text not in found:
                found.append(text)
    return tuple(found[:SYNONYMS_MAX])


def _wordnet(folder: Path) -> ModuleType:
    """The `wn` library, reading and writing the thesaurus in `folder`."""
    import warnings

    import wn

    warnings.filterwarnings("ignore", category=wn.WnWarning)  # its notes aren't for players
    wn.config.data_directory = folder  # type: ignore[attr-defined]  # documented, not exported
    return wn


def near(word: str, vocabulary: Iterable[str]) -> list[str]:
    """Words spelled nearly like `word`."""
    folded = word.casefold()
    options = [v for v in vocabulary if v != folded and abs(len(v) - len(folded)) <= 2]
    return difflib.get_close_matches(folded, options, n=3, cutoff=NEAR_CUTOFF)


def _has(text: str, form: str) -> bool:
    """`form` starts a word in `text` (both casefolded)."""
    return re.search(rf"(?<!\w){re.escape(form)}", text) is not None


def phrase_words(given: Sequence[str]) -> list[str] | None:
    """The words of the arguments when one of them is a phrase (quoted: `"fallout 3 clocks"`),
    for a search to try when the phrase finds nothing; None when there's no phrase to split."""
    split = [word for text in given for word in text.split()]
    return split if len(split) > len([t for t in given if t.strip()]) else None


@dataclass(slots=True)
class Matcher:
    """The words of a query, and how well a text matches them. A near spelling counts only for
    a word no text searched has as typed: a first pass with `typed` set to every word notes in
    `seen` the words that are there, and a second, with `typed=seen`, lets the others (typos,
    perhaps) find their near spellings. So `scroll` finds the scrolls, not every `roll`."""

    words: list[str]
    typed: frozenset[str] | None = None  # no near spellings for these (None: for none of them)
    seen: set[str] = field(default_factory=set)  # the words the texts so far have as typed
    whole: bool = False  # each word only as a word of the text (`ward` isn't in `warden`)
    _near: dict[tuple[str, str], bool] = field(default_factory=dict)

    def see(self, *folded: str) -> None:
        """Note which words these casefolded texts have as typed."""
        for word in self.words:
            if word not in self.seen and any(stem(word) in text for text in folded):
                self.seen.add(word)

    def unseen(self) -> bool:
        """Some word no text had as typed: a second pass would try its near spellings."""
        return any(word not in self.seen for word in self.words)

    def weight(self, word: str, folded: str, words_in: set[str] | None = None) -> tuple[float, str]:
        """How `word` matches the casefolded `folded`, and the form found (0 and "" if not)."""
        exact = stem(word)
        if self.whole:  # a word of the text, as typed (a plural too), and nothing looser
            present = words_in if words_in is not None else tokens(folded)
            return (EXACT, exact) if any(stem(t) == exact for t in present) else (0.0, "")
        if exact in folded:
            return EXACT, exact
        if self.typed is None or word not in self.typed:
            for token in sorted(words_in if words_in is not None else tokens(folded)):
                key = (word, token)
                if key not in self._near:
                    self._near[key] = bool(near(word, [token]))
                if self._near[key]:
                    return NEAR, token
        for other in synonyms(word):
            if _has(folded, stem(other)):
                return SYNONYM, stem(other)
        return 0.0, ""

    def found(self, text: str) -> bool:
        """Every word matches, one way or another."""
        folded = text.casefold()
        self.see(folded)
        present = tokens(folded)
        return all(self.weight(w, folded, present)[0] for w in self.words)

    def forms(self, text: str) -> list[str]:
        """The forms of the words found in `text`: what a snippet should show."""
        folded = text.casefold()
        present = tokens(folded)
        return [form for w in self.words if (form := self.weight(w, folded, present)[1])]


# ---------------------------------------------------------------------------- the thesaurus

LEXICONS = {"en": "oewn", "de": "odenet"}  # other languages: the Open Multilingual Wordnet's


@dataclass(frozen=True, slots=True)
class Lexicon:
    id: str
    language: str
    name: str
    active: bool


def installed() -> list[Lexicon]:
    """The thesaurus's lexicons; the one in use is marked."""
    if not thesaurus_ready():
        return []
    wn = _wordnet(wordnet_dir())
    lexicons = [(lex.id, lex.language, lex.label) for lex in wn.lexicons()]
    chosen = _chosen({i for i, _lg, _n in lexicons})
    return [Lexicon(i, lg, n, i == chosen) for i, lg, n in lexicons]


def active() -> tuple[str, str] | None:
    """The lexicon searches use, as (id, language): the one chosen, else the first installed."""
    database = wordnet_dir() / "wn.db"
    if not database.is_file():
        return None
    marker = wordnet_dir() / ACTIVE
    stamp = (database.stat().st_mtime_ns, marker.stat().st_mtime_ns if marker.is_file() else 0)
    return _active(str(wordnet_dir()), stamp)


@cache
def _active(folder: str, stamp: tuple[int, int]) -> tuple[str, str] | None:
    chosen = next((lex for lex in installed() if lex.active), None)
    return (chosen.id, chosen.language) if chosen else None


def _chosen(ids: set[str]) -> str | None:
    marker = wordnet_dir() / ACTIVE
    chosen = marker.read_text(encoding="utf-8").strip() if marker.is_file() else ""
    return chosen if chosen in ids else (sorted(ids)[0] if ids else None)


def use(code: str) -> Lexicon | None:
    """Make one installed language the thesaurus's (only one is used at a time)."""
    for lexicon in installed():
        if lexicon.language == code or lexicon.id == project_for(code):
            (wordnet_dir() / ACTIVE).write_text(lexicon.id + "\n", encoding="utf-8")
            return Lexicon(lexicon.id, lexicon.language, lexicon.name, True)
    return None


def project_for(language: str) -> str:
    """The WordNet project for a language code (`en`, `fr`, …)."""
    return LEXICONS.get(language, f"omw-{language}")


def known_projects() -> set[str]:
    import wn

    return {str(p["id"]) for p in wn.projects()}


def available() -> list[tuple[str, str]]:
    """The languages a thesaurus can be downloaded for: (code, the wordnet's name)."""
    import wn

    found: dict[str, str] = {}
    for project in wn.projects():
        pid, label = str(project["id"]), str(project["label"])
        if pid in LEXICONS.values():
            code = next(c for c, p in LEXICONS.items() if p == pid)
        elif pid.startswith("omw-") and not pid.startswith("omw-en"):
            code = pid.removeprefix("omw-")
        else:
            continue
        found.setdefault(code, label)
    return sorted(found.items())


def remove_language(code: str) -> bool:
    """Take one language's wordnet out of the thesaurus."""
    if not thesaurus_ready():
        return False
    wn = _wordnet(wordnet_dir())
    gone = False
    for lexicon in wn.lexicons():
        if lexicon.id == project_for(code) or lexicon.language == code:
            wn.remove(f"{lexicon.id}:{lexicon.version}", progress_handler=None)
            gone = True
            marker = wordnet_dir() / ACTIVE
            if marker.is_file() and marker.read_text(encoding="utf-8").strip() == lexicon.id:
                marker.unlink()
    return gone


# ---------------------------------------------------------------------------- downloading

ACTIVE = "active"  # the id of the lexicon in use
PROGRESS = "progress.json"  # a download under way, for anyone watching
STALE = 30 * 60  # a progress file untouched this long is from a download that died


@dataclass(frozen=True, slots=True)
class Progress:
    language: str
    stage: str  # "download" (count and total in bytes), "add" (entries) or "failed"
    count: int
    total: int
    error: str = ""

    def to_data(self) -> dict[str, JSON]:
        return {
            "language": self.language, "stage": self.stage, "count": self.count,
            "total": self.total, "error": self.error,
        }  # fmt: skip


def progress() -> Progress | None:
    """The download under way (or the last one, if it failed), else None."""
    path = wordnet_dir() / PROGRESS
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        age = time.time() - path.stat().st_mtime
    except OSError, ValueError:
        return None
    if not isinstance(data, dict) or age > STALE:
        return None
    return Progress(
        str(data.get("language") or ""), str(data.get("stage") or ""),
        int(data.get("count") or 0), int(data.get("total") or 0), str(data.get("error") or ""),
    )  # fmt: skip


def _report(value: Progress) -> None:
    folder = wordnet_dir()
    folder.mkdir(parents=True, exist_ok=True)
    scratch = folder / f"{PROGRESS}.{os.getpid()}"
    scratch.write_text(json.dumps(value.to_data()), encoding="utf-8")
    scratch.replace(folder / PROGRESS)


def _reporter(language: str) -> type:
    """A `wn` progress handler that keeps `progress.json` current (a few times a second)."""
    from wn.util import ProgressHandler

    class Reporter(ProgressHandler):
        last = 0.0

        def update(self, n: int = 1, force: bool = False) -> None:
            super().update(n, force)
            now = time.monotonic()
            if not force and now - Reporter.last < 0.25:
                return
            Reporter.last = now
            unit = str(self.kwargs.get("unit") or "")
            stage = (
                "download"
                if unit.startswith("b")
                or "download" in str(self.kwargs.get("message") or "").casefold()
                else "add"
            )
            _report(Progress(
                language, stage, _whole(self.kwargs.get("count")),
                _whole(self.kwargs.get("total")),
            ))  # fmt: skip

    return Reporter


def starting(language: str) -> None:
    """Say a download of `language` is about to begin (before its process takes over)."""
    _report(Progress(language, "download", 0, 0))


def settled(language: str) -> None:
    """Clear a "starting" mark for `language` that no download took over."""
    running = progress()
    if running is not None and running.language == language and not running.count:
        (wordnet_dir() / PROGRESS).unlink(missing_ok=True)


def _whole(value: object) -> int:
    return value if isinstance(value, int) else 0


def add(source: str, *, file: bool, language: str = "") -> None:
    """Download a WordNet project into the thesaurus (or add a WN-LMF file), reporting how
    far it is in `progress.json`, and make it the language in use. One at a time."""
    import shutil

    running = progress()
    if running is not None and running.stage != "failed" and running.count:
        raise RuntimeError(_("a download is already under way ({lang})", lang=running.language))
    folder = wordnet_dir()
    folder.mkdir(parents=True, exist_ok=True)
    wn = _wordnet(folder)
    code = language or source
    _report(Progress(code, "download", 0, 0))
    try:
        if file:
            wn.add(source, progress_handler=_reporter(code))
        else:
            wn.download(source, progress_handler=_reporter(code))
    except Exception as err:
        _report(Progress(code, "failed", 0, 0, str(err)))
        raise
    finally:
        shutil.rmtree(folder / "downloads", ignore_errors=True)  # the compressed copies
    (folder / PROGRESS).unlink(missing_ok=True)
    lexicons = [lex for lex in installed() if lex.id == source or lex.language == code]
    newest = lexicons[-1] if lexicons else (installed()[-1] if installed() else None)
    if newest is not None:
        (folder / ACTIVE).write_text(newest.id + "\n", encoding="utf-8")


def remove() -> bool:
    import shutil

    folder = wordnet_dir()
    if not folder.exists():
        return False
    shutil.rmtree(folder)
    return True
