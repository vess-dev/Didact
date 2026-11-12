"""Words kept to be read later, in any language: a message and its values, as data.

What's persisted stays English (the log's summaries, a draft's questions), since anything may
read it back. Beside the English, keep the phrase that made it: its message (marked with `N_`,
so extraction finds it) and its values. `shown()` reads it in the current language.

    said = phrase(N_("the party goes to {place}"), place="The Ford")
    english(said)            # "the party goes to The Ford": what the log keeps
    shown(said, summary)     # the same, in the reader's language

A value can be a phrase itself (`undo #e12: <what #e12 did>`), and `counted()` makes one with
plural forms (`{n} save points`).
"""

from didact.core.i18n import DEFAULT, catalog, current
from didact.core.output import JSON

type Phrase = dict[str, JSON]


def phrase(message: str, /, **values: JSON) -> Phrase:
    """Keep `message` (a literal marked with `N_`) and the values it names."""
    said: Phrase = {"msg": message}
    if values:
        said["values"] = dict(values)
    return said


def counted(singular: str, plural: str, n: int, /, **values: JSON) -> Phrase:
    """A phrase with plural forms, like `ngettext`; `{n}` is filled in too."""
    return phrase(singular, **values) | {"plural": plural, "n": n}


def english(said: Phrase) -> str:
    """The phrase in English, as persisted."""
    return _render(said, DEFAULT)


def translated(said: Phrase) -> str:
    """The phrase in the current language."""
    return shown(said, english(said))


def shown(said: JSON, fallback: str) -> str:
    """A kept phrase in the current language. `fallback` is its English as it was kept: shown
    in English, or when there's no phrase (older data) or it can't be read."""
    code = current().code
    if code == DEFAULT or not isinstance(said, dict):
        return fallback
    try:
        return _render(said, code)
    except KeyError, IndexError, ValueError, TypeError:
        return fallback


def _render(said: Phrase, code: str) -> str:
    message = said.get("msg")
    if not isinstance(message, str):
        raise ValueError("not a phrase")
    raw = said.get("values")
    values = {k: _value(v, code) for k, v in raw.items()} if isinstance(raw, dict) else {}
    words = catalog(code)
    plural, n = said.get("plural"), said.get("n")
    if isinstance(plural, str) and isinstance(n, int) and not isinstance(n, bool):
        return words.ngettext(message, plural, n).format(n=n, **values)
    text = words.gettext(message)
    return text.format(**values) if values else text


def _value(value: JSON, code: str) -> object:
    """A value to fill in: a phrase is read in the same language; anything else as it is."""
    if isinstance(value, dict) and isinstance(value.get("msg"), str):
        return _render(value, code)
    return value
