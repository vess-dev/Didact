"""Translations of what people read: the browser app's words and the guides. Commands and
their output stay English (they're for the LLM).

The words are gettext catalogs: `didact/locale/<code>/LC_MESSAGES/didact.po`, compiled to
`didact.mo` beside it (`make i18n` extracts, merges and compiles). In code, mark a message with
`_()`, name its values instead of joining pieces (`_("Uninstall {pack}?", pack=pack_id)`), use
`ngettext` for counts and `pgettext` where one English word means two things. The language in
use is per request (`use()`); untranslated messages fall back to English.
"""

import gettext
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from pathlib import Path

DOMAIN = "didact"
DEFAULT = "en"


@dataclass(frozen=True, slots=True)
class Language:
    code: str  # the catalog's folder (gettext style: `pt_BR`)
    tag: str  # BCP 47, for `<html lang>` and Accept-Language (`pt-BR`)
    name: str  # in its own language
    english: str


# Steam's fully supported languages that the app's font (Ubuntu: Latin, Cyrillic, Greek) can show.
LANGUAGES: dict[str, Language] = {
    lang.code: lang
    for lang in (
        Language("en", "en", "English", "English"),
        Language("bg", "bg", "Български", "Bulgarian"),
        Language("cs", "cs", "Čeština", "Czech"),
        Language("da", "da", "Dansk", "Danish"),
        Language("de", "de", "Deutsch", "German"),
        Language("el", "el", "Ελληνικά", "Greek"),
        Language("es", "es", "Español (España)", "Spanish (Spain)"),
        Language("es_419", "es-419", "Español (Latinoamérica)", "Spanish (Latin America)"),
        Language("fi", "fi", "Suomi", "Finnish"),
        Language("fr", "fr", "Français", "French"),
        Language("hu", "hu", "Magyar", "Hungarian"),
        Language("id", "id", "Bahasa Indonesia", "Indonesian"),
        Language("it", "it", "Italiano", "Italian"),
        Language("ms", "ms", "Bahasa Melayu", "Malay"),
        Language("nb", "nb", "Norsk", "Norwegian"),
        Language("nl", "nl", "Nederlands", "Dutch"),
        Language("pl", "pl", "Polski", "Polish"),
        Language("pt", "pt", "Português (Portugal)", "Portuguese (Portugal)"),
        Language("pt_BR", "pt-BR", "Português (Brasil)", "Portuguese (Brazil)"),
        Language("ro", "ro", "Română", "Romanian"),
        Language("ru", "ru", "Русский", "Russian"),
        Language("sv", "sv", "Svenska", "Swedish"),
        Language("tr", "tr", "Türkçe", "Turkish"),
        Language("uk", "uk", "Українська", "Ukrainian"),
    )
}

_current: ContextVar[str] = ContextVar("didact_language", default=DEFAULT)


def locale_dir() -> Path:
    return Path(str(files("didact") / "locale"))


def current() -> Language:
    return LANGUAGES.get(_current.get(), LANGUAGES[DEFAULT])


@contextmanager
def use(code: str) -> Iterator[Language]:
    """Speak `code` (a known language, else English) until the block ends."""
    token = _current.set(code if code in LANGUAGES else DEFAULT)
    try:
        yield current()
    finally:
        _current.reset(token)


@cache
def catalog(code: str) -> gettext.NullTranslations:
    if code == DEFAULT:
        return gettext.NullTranslations()
    return gettext.translation(DOMAIN, locale_dir(), languages=[code], fallback=True)


def _(message: str, /, **values: object) -> str:
    """`message` in the current language, with `{name}` values filled in."""
    text = catalog(_current.get()).gettext(message)
    return text.format(**values) if values else text


def N_(message: str) -> str:
    """Mark text for translation that's translated later, elsewhere (extraction finds it)."""
    return message


def N_plural(singular: str, plural: str) -> tuple[str, str]:
    """Mark a message's plural forms for translation later, elsewhere (extraction finds them)."""
    return singular, plural


def translate(message: str) -> str:
    """Text written elsewhere (a command's help, extracted from the registry), in the
    current language; nothing is filled in."""
    return catalog(_current.get()).gettext(message) if message else message


def translate_plural(singular: str, plural: str, n: int) -> str:
    """Plural forms written elsewhere (argparse's), in the current language; nothing filled in."""
    return catalog(_current.get()).ngettext(singular, plural, n)


def ngettext(singular: str, plural: str, n: int, /, **values: object) -> str:
    """The right form for `n` (`{n}` is filled in too): languages have up to four."""
    text = catalog(_current.get()).ngettext(singular, plural, n)
    return text.format(n=n, **values)


def pgettext(context: str, message: str, /, **values: object) -> str:
    """`message` where the same English means different things (`context` tells them apart)."""
    text = catalog(_current.get()).pgettext(context, message)
    return text.format(**values) if values else text


LANGUAGE_ENV = "DIDACT_LANG"  # another language for the command line, for the call it's given to


def command_line_language() -> str:
    """The command line's language: English, what LLMs read best and are told to use, unless
    the call itself asks for another (`DIDACT_LANG=fr didact brief`). Nothing makes a language
    stick, so an LLM running `didact` always reads English, whatever language the browser app
    shows its people. The MCP server never asks: it's always English."""
    import os

    return chosen(os.environ.get(LANGUAGE_ENV, ""))


def chosen(value: str) -> str:
    """A language code from a code or tag (`pt_BR`, `pt-BR`, `fr`); unknown: English."""
    if value in LANGUAGES:
        return value
    by_tag = {lang.tag.casefold(): lang.code for lang in LANGUAGES.values()}
    return by_tag.get(value.strip().casefold().replace("_", "-"), DEFAULT)


def negotiate(accept_language: str) -> str:
    """The best known language for an Accept-Language header (`fr-CA,fr;q=0.9,en;q=0.8`)."""
    by_tag = {lang.tag.casefold(): lang.code for lang in LANGUAGES.values()}
    wanted: list[tuple[float, int, str]] = []
    for position, part in enumerate(accept_language.split(",")):
        tag, _sep, params = part.strip().partition(";")
        quality = 1.0
        if params.strip().startswith("q="):
            try:
                quality = float(params.strip()[2:])
            except ValueError:
                quality = 0.0
        if tag and quality > 0:
            wanted.append((-quality, position, tag.strip().casefold()))
    for _q, _p, tag in sorted(wanted):
        if tag in by_tag:
            return by_tag[tag]
        if tag.startswith("es-") and tag != "es-es":
            return "es_419"  # any Latin American Spanish
        if tag.split("-")[0] in by_tag:
            return by_tag[tag.split("-")[0]]
        if tag.split("-")[0] == "no":
            return "nb"
    return DEFAULT
