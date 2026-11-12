"""Pack dice (`dice.yaml`): named dice, macros and dice chains.

dice:
  boost: [blank, blank, success, success+advantage, advantage+advantage, advantage]
  marvel: [1, 2, 3, 4, 5, {value: 6, symbols: [marvel]}]
macros:
  attack: {params: [a, b], expr: "{$a, $b}kh1", summary: "Two weapons: keep the higher"}
chains:
  odd: [3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 20, 24, 30]
"""

import re
from collections import Counter
from collections.abc import Iterable

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.expr import DieSpec, Face, Macro, Registry
from didact.packs.source import Doc, Problem

_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_PARAM = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_KEYS = {"dice", "macros", "chains"}


def parse_face(raw: JSON) -> Face:
    match raw:
        case bool():
            raise ValueError(_("invalid face {face}", face=repr(raw)))
        case int():
            return Face(raw)
        case str() if raw.strip() in ("", "-", "blank"):
            return Face()
        case str() if re.fullmatch(r"-?\d+", raw.strip()):
            return Face(int(raw))
        case str():
            symbols = tuple(s.strip() for s in raw.split("+"))
            if not all(_SYMBOL.match(s) for s in symbols):
                raise ValueError(
                    _(
                        "invalid face {face}: use numbers or symbol names like `success+advantage`",
                        face=repr(raw),
                    )
                )
            return Face(0, symbols)
        case {"value": int() as value, **rest}:
            symbols_raw = rest.get("symbols", [])
            if not isinstance(symbols_raw, list) or not all(
                isinstance(s, str) and _SYMBOL.match(s) for s in symbols_raw
            ):
                raise ValueError(_("`symbols` must be a list of names"))
            return Face(value, tuple(str(s) for s in symbols_raw))
    raise ValueError(_("invalid face {face}", face=repr(raw)))


def die_from(raw: JSON) -> DieSpec:
    if not isinstance(raw, list) or len(raw) < 2:
        raise ValueError(_("a die needs a list of at least two faces"))
    faces = tuple(parse_face(f) for f in raw)
    return DieSpec("custom", len(faces), faces=faces)


def check_dice(doc: Doc) -> list[Problem]:
    problems: list[Problem] = []
    for key in sorted(set(doc.data) - _KEYS):
        problems.append(
            doc.problem((key,), _("unknown key `{key}`", key=key), _("use dice, macros or chains"))
        )
    dice = doc.data.get("dice", {})
    for name, faces in dice.items() if isinstance(dice, dict) else []:
        if not _NAME.match(name):
            problems.append(
                doc.problem(
                    ("dice", name),
                    _("invalid die name {name}", name=repr(name)),
                    _("e.g. `boost`"),
                )
            )
            continue
        try:
            die_from(faces)
        except ValueError as exc:
            problems.append(
                doc.problem(("dice", name), _("die `{name}`: {error}", name=name, error=exc))
            )
    macros = doc.data.get("macros", {})
    for name, spec in macros.items() if isinstance(macros, dict) else []:
        where = ("macros", name)
        if not _PARAM.match(name):
            problems.append(
                doc.problem(
                    where, _("invalid macro name {name}", name=repr(name)), _("e.g. `attack`")
                )
            )
            continue
        if not isinstance(spec, dict) or not isinstance(spec.get("expr"), str):
            problems.append(
                doc.problem(
                    where,
                    _("macro `{name}` needs `expr`", name=name),
                    _('e.g. expr: "{$a, $b}kh1"'),
                )
            )
            continue
        params = spec.get("params", [])
        if not isinstance(params, list) or not all(
            isinstance(p, str) and _PARAM.match(p) for p in params
        ):
            problems.append(doc.problem((*where, "params"), _("`params` must be a list of names")))
    chains = doc.data.get("chains", {})
    for name, sizes in chains.items() if isinstance(chains, dict) else []:
        numbers = (
            [s for s in sizes if isinstance(s, int) and s > 0] if isinstance(sizes, list) else []
        )
        if not numbers or numbers != sizes or numbers != sorted(set(numbers)):
            problems.append(
                doc.problem(
                    ("chains", name),
                    _("chain `{name}` must list die sizes, smallest first", name=name),
                )
            )
    return problems


def register(registry: Registry, packs: Iterable[tuple[str, dict[str, JSON]]]) -> None:
    """Add every pack's dice to `registry`: always as `alias.name`, and as `name` when unique."""
    entries = [(alias, dice) for alias, dice in packs if dice]
    counts: Counter[tuple[str, str]] = Counter()
    for _alias, dice in entries:
        for section in ("dice", "macros", "chains"):
            block = dice.get(section)
            for name in block if isinstance(block, dict) else ():
                counts[section, name] += 1
    for alias, dice in entries:
        for section in ("dice", "macros", "chains"):
            block = dice.get(section)
            if not isinstance(block, dict):
                continue
            for name, raw in block.items():
                names = [f"{alias}.{name}"]
                if counts[section, name] == 1:
                    names.append(name)
                for full in names:
                    try:
                        _add(registry, section, full, raw)
                    except ValueError as exc:
                        if full == name:
                            continue  # a short name clashing with a built-in: keep the long one
                        raise InvalidError(
                            _("pack dice `{name}`: {error}", name=full, error=exc),
                            hint=_("rename it"),
                        ) from exc


def _add(registry: Registry, section: str, name: str, raw: JSON) -> None:
    match section:
        case "dice":
            registry.add_die(name, die_from(raw))
        case "macros":
            assert isinstance(raw, dict)
            params = raw.get("params", [])
            registry.add_macro(
                Macro(
                    name,
                    tuple(str(p) for p in params) if isinstance(params, list) else (),
                    str(raw["expr"]),
                    str(raw.get("summary", "")),
                )
            )
        case _:
            assert isinstance(raw, list)
            registry.add_chain(
                name, tuple(int(s) for s in raw if isinstance(s, int))
            )  # step.<name>
