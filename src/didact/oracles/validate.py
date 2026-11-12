"""Checking `oracles/*.yaml` when a pack is built.

oracle: yes-no
title: Yes/no oracle
help: Ask a yes/no question; the answer may come with "and" or "but".
ask: yes-no                      # the check that answers (params: question, odds, oracle)
odds: [very unlikely, unlikely, even, likely, very likely]
meaning: [action, theme]         # tables rolled for `didact meaning` (one word from each)
state: {chaos: {start: 5, min: 1, max: 9}}   # kept per campaign, readable as @oracle.chaos
lists: {names: [threads, characters], method: sections, most: 3}   # `didact lists …`
prompt: "Interpret the answer in the fiction."
"""

from didact.core.i18n import _
from didact.core.output import JSON
from didact.packs.kinds import register_validator
from didact.packs.source import Doc, Problem

ORACLE_KEYS = frozenset({
    "oracle", "title", "help", "ask", "odds", "meaning", "state", "lists", "prompt", "source",
    "tags",
})  # fmt: skip
LIST_KEYS = frozenset({"names", "method", "most"})


def check_oracle(doc: Doc) -> list[Problem]:
    data = doc.data
    problems = [
        doc.problem(
            (key,),
            _("unknown key `{key}`", key=key),
            _("an oracle takes: {keys}", keys=", ".join(sorted(ORACLE_KEYS))),
        )
        for key in sorted(set(data) - ORACLE_KEYS)
    ]
    if not isinstance(data.get("ask"), str):
        problems.append(
            doc.problem(
                ("ask",),
                _("an oracle needs `ask`: the check that answers"),
                _("e.g. ask: yes-no"),
            )
        )
    for key in ("odds", "meaning"):
        value = data.get(key)
        if value is not None and not (
            isinstance(value, list) and all(isinstance(v, str) for v in value)
        ):
            problems.append(doc.problem((key,), _("`{key}` is a list of names", key=key)))
    state = data.get("state")
    if state is not None:
        problems += _check_state(doc, state)
    lists = data.get("lists")
    if lists is not None:
        problems += _check_lists(doc, lists)
    return problems


def _check_lists(doc: Doc, lists: JSON) -> list[Problem]:
    from didact.tables.lists import METHODS

    if not isinstance(lists, dict):
        return [
            doc.problem(
                ("lists",), _("`lists` is {example}", example="{names: […], method: …, most: 3}")
            )
        ]
    problems = [
        doc.problem(
            ("lists", key), _("unknown key `{key}`", key=key), _("lists take: names, method, most")
        )
        for key in sorted(set(lists) - LIST_KEYS)
    ]
    method = lists.get("method", "uniform")
    if method not in METHODS:
        problems.append(
            doc.problem(
                ("lists", "method"), _("method is one of: {methods}", methods=", ".join(METHODS))
            )
        )
    names = lists.get("names")
    if names is not None and not (
        isinstance(names, list) and all(isinstance(n, str) for n in names)
    ):
        problems.append(doc.problem(("lists", "names"), _("`names` is a list of list names")))
    return problems


def _check_state(doc: Doc, state: JSON) -> list[Problem]:
    if not isinstance(state, dict):
        return [
            doc.problem(
                ("state",),
                _("`state` maps names to {shape}", shape="{start, min, max}"),
                _("e.g. {example}", example="{chaos: {start: 5}}"),
            )
        ]
    problems: list[Problem] = []
    for name, spec in state.items():
        start = spec.get("start") if isinstance(spec, dict) else spec
        if not isinstance(start, int | str | list):
            problems.append(
                doc.problem(("state", name), _("state `{name}` needs a start value", name=name))
            )
    return problems


register_validator("oracle", check_oracle)
