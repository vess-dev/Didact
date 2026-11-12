"""Trigger keys: which words make a record come up in a lore scan.

Pure functions shared by the index (which stores every key's first word, so a scan is one
query) and the lore service (which checks whole phrases and the rules around them).

- Text is case-folded and split into words (`Sweeney's` → `sweeney`, `s`).
- A key is a word or phrase matched on whole words, or `/regex/` (case-insensitive).
- Plurals match: `wolf` also fires on `wolves`, `key` on `keys`, `berry` on `berries`.
- Single-word keys need at least MIN_KEY letters, so names like "Al" don't fire everywhere.
"""

import re

from didact.store.entity import Entity

WORD = re.compile(r"\w+")
MIN_KEY = 3
# Records that track play rather than the world don't turn into cards.
NOT_CARDS = frozenset({"session", "scene", "summary", "note", "track", "lore", "ruling"})


def words(text: str) -> list[str]:
    return WORD.findall(text.casefold())


def is_regex(key: str) -> bool:
    return len(key) > 2 and key.startswith("/") and key.endswith("/")


def forms(word: str) -> set[str]:
    """A word and its plural forms: wolf → wolves, key → keys, berry → berries."""
    found = {word, word + "s"}
    if word.endswith(("s", "x", "z", "ch", "sh")):
        found.add(word + "es")
    if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
        found.add(word[:-1] + "ies")
    if word.endswith("f"):
        found.add(word[:-1] + "ves")
    if word.endswith("fe"):
        found.add(word[:-2] + "ves")
    return found


def phrases(key: str) -> list[tuple[str, ...]]:
    """The word sequences a plain key matches (its last word in every plural form)."""
    parts = words(key)
    if not parts or (len(parts) == 1 and len(parts[0]) < MIN_KEY):
        return []
    return [(*parts[:-1], last) for last in sorted(forms(parts[-1]))]


def keys_of(entity: Entity) -> tuple[list[str], str] | None:
    """(keys, source) for a record that can come up in a scan, or None.

    Lore entries use their `keys`; rulings their `keys`, else their rule and tags; every
    world record (NPC, place, item, faction, …) is a card keyed by its name and aliases.
    """
    fields = entity.fields
    listed = fields.get("keys")
    given = [str(k) for k in listed] if isinstance(listed, list) else []
    if entity.type == "lore":
        return given, "lore"
    if entity.type == "ruling":
        rule = fields.get("rule")
        fallback = [str(rule).rpartition(".")[2]] if isinstance(rule, str) else []
        return (given or [*fallback, *entity.tags]), "ruling"
    if entity.type in NOT_CARDS:
        return None
    return [entity.name, *entity.aliases, *given], "card"


def rows_for(entity: Entity) -> list[tuple[str, str, str, str]]:
    """Index rows: (first word, phrase, kind, source). Kind: key | regex | constant."""
    found = keys_of(entity)
    if found is None:
        return []
    keys, source = found
    rows: set[tuple[str, str, str, str]] = set()
    for key in keys:
        if is_regex(key):
            rows.add(("", key, "regex", source))
            continue
        for phrase in phrases(key):
            rows.add((phrase[0], " ".join(phrase), "key", source))
    if source == "lore" and entity.fields.get("constant") is True:
        rows.add(("", "", "constant", source))
    return sorted(rows)


def find(phrase: tuple[str, ...], tokens: list[str], at: dict[str, list[int]]) -> int | None:
    """Where a phrase first occurs among the text's words, or None."""
    for start in at.get(phrase[0], ()):
        if tuple(tokens[start : start + len(phrase)]) == phrase:
            return start
    return None


def positions(tokens: list[str]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for index, token in enumerate(tokens):
        found.setdefault(token, []).append(index)
    return found
