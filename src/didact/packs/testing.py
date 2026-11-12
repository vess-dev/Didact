"""`pack test`: run the examples a pack declares in `tests/*.yaml`.

    test: weather-covers            test: save-math              test: smoke
    table: weather                  expr: "d20 <= @STR"          script:
    times: 50                       vars: {STR: 10}                - world new t --system {pack}
                                    got: "7"                       - new pc Hero --fill
    test: fair-save                 expect: true                   - run: show hero
    odds: "d20 <= 10"                                                expect: "HP"
    chance: 0.5                     test: every-table
                                    table: all

`table: all` rolls every table of the pack (a lookup table once per key). Scripts run real
`didact` commands in a throwaway library where the pack is available; a step may be
`{run: …, expect: text}` (or a list of texts) to check what it printed, `expect_not` for text
it mustn't print, and `fails: true` for a command that must fail (its error is printed too).
"""

import contextlib
import io
import os
import shlex
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from didact.core.config import resolve_config
from didact.core.errors import DidactError
from didact.core.i18n import _, ngettext
from didact.core.output import JSON
from didact.expr import HashStream, PhysicalFaces, RollContext, run
from didact.expr.engine import show
from didact.expr.model import Value, from_json, values_from
from didact.packs.kinds import register_validator
from didact.packs.library import PackLibrary, PackSet
from didact.packs.source import Doc, Problem

TEST_KEYS = frozenset({
    "test", "help", "table", "times", "with", "expr", "vars", "got", "expect", "odds", "chance",
    "tolerance", "script",
})  # fmt: skip


STEP = frozenset({"run", "expect", "expect_not", "fails"})  # a step that checks what it printed


@dataclass(frozen=True, slots=True)
class Outcome:
    test: str
    ok: bool
    detail: str


def check_test(doc: Doc) -> list[Problem]:
    data = doc.data
    problems = [
        doc.problem((k,), _("unknown test key `{key}`", key=k))
        for k in sorted(set(data) - TEST_KEYS)
    ]
    if not any(k in data for k in ("table", "expr", "odds", "script")):
        problems.append(doc.problem((), _("a test needs `table`, `expr`, `odds` or `script`")))
    script = data.get("script")
    for index, step in enumerate(script if isinstance(script, list) else []):
        if isinstance(step, dict) and (
            not isinstance(step.get("run"), str)
            or set(step) - STEP
            or _texts(step.get("expect")) is None
            or _texts(step.get("expect_not")) is None
            or not isinstance(step.get("fails", False), bool)
        ):
            problems.append(
                doc.problem(
                    ("script", index),
                    _("a step is a command, or {run: …, expect: …, expect_not: …, fails: true}"),
                )
            )
    return problems


def _texts(value: JSON) -> list[str] | None:
    """A step's `expect` or `expect_not`: one text or a list of them (None: something else)."""
    items = value if isinstance(value, list) else [] if value is None else [value]
    return [str(i) for i in items] if all(isinstance(i, str) for i in items) else None


register_validator("test", check_test)


def run_tests(pack_dir: Path, pack_id: str, tests: dict[str, JSON]) -> list[Outcome]:
    with _library(pack_dir) as lib:
        packs = lib.resolve([pack_id])
        outcomes = []
        for name, entry in tests.items():
            data = entry.get("data") if isinstance(entry, dict) else None
            if not isinstance(data, dict):
                continue
            try:
                outcomes.append(_one(name, data, packs, pack_dir, pack_id))
            except DidactError as exc:
                outcomes.append(Outcome(name, False, exc.message))
        return outcomes


@contextlib.contextmanager
def _library(pack_dir: Path) -> Iterator[PackLibrary]:
    with tempfile.TemporaryDirectory(prefix="didact-test-") as scratch:
        config = resolve_config(
            home=str(Path(scratch) / "home"), cache=str(Path(scratch) / "cache")
        )
        yield PackLibrary(config, extra=[pack_dir.parent])


def _one(name: str, data: dict[str, JSON], packs: PackSet, pack_dir: Path, pack_id: str) -> Outcome:
    from didact.services.tables import finder
    from didact.tables.engine import TableRoller

    registry = packs.registry()
    inputs = values_from(data.get("with"))
    if data.get("table") == "all":
        return _every_table(name, data, packs, pack_id)
    if isinstance(data.get("table"), str):
        find = finder(packs)
        table = find(str(data["table"]), pack_id)
        times = data.get("times", 20)
        count = times if isinstance(times, int) else 20
        for i in range(count):
            ctx = RollContext(registry, HashStream(f"test:{name}:{i}"), inputs)
            TableRoller(find, ctx).roll(table, inputs)
        return Outcome(
            name,
            True,
            ngettext("{n} roll on {table}", "{n} rolls on {table}", count, table=table.id),
        )
    if isinstance(data.get("expr"), str):
        got = data.get("got")
        source = PhysicalFaces.parse(str(got)) if got is not None else HashStream(f"test:{name}")
        ctx = RollContext(registry, source, values_from(data.get("vars")))
        value = run(str(data["expr"]), ctx).result.value
        expected = from_json(data.get("expect"))
        if "expect" in data and value != expected:
            if expected is None:
                return Outcome(name, False, _("expected nothing, got {got}", got=show(value)))
            detail = _("expected {expected}, got {got}", expected=show(expected), got=show(value))
            return Outcome(name, False, detail)
        return Outcome(name, True, f"{data['expr']} = {show(value)}")
    if isinstance(data.get("odds"), str):
        from didact.expr.odds import odds

        found = odds(str(data["odds"]), registry, inputs)
        wanted, tolerance = data.get("chance"), data.get("tolerance", 0.02)
        off = isinstance(wanted, int | float) and isinstance(tolerance, int | float)
        if off and abs(found.chance - float(wanted)) > float(tolerance):  # type: ignore[arg-type]
            return Outcome(
                name,
                False,
                _(
                    "chance {chance}, expected {wanted} ± {tolerance}",
                    chance=f"{found.chance:.3f}",
                    wanted=wanted,
                    tolerance=tolerance,
                ),
            )
        return Outcome(
            name,
            True,
            _("chance {chance} ({method})", chance=f"{found.chance:.3f}", method=found.method),
        )
    script = data.get("script")
    if isinstance(script, list):
        return _script(name, script, pack_dir, pack_id)
    return Outcome(name, False, _("nothing to test"))


def _every_table(name: str, data: dict[str, JSON], packs: PackSet, pack_id: str) -> Outcome:
    """Roll each of the pack's tables (`times` each); a lookup table once for each key."""
    from didact.services.tables import finder
    from didact.tables.engine import TableRoller

    find = finder(packs)
    registry = packs.registry()
    times = data.get("times", 5)
    count = times if isinstance(times, int) else 5
    rolled = 0
    for item in packs.get(pack_id).items("table"):
        table = find(item.qualified, pack_id)
        cases = _lookup_cases(list(table.lookup), table.data.get("entries")) if table.lookup else []
        for i, inputs in enumerate(cases or [{} for _unused in range(count)]):
            ctx = RollContext(registry, HashStream(f"test:{name}:{table.id}:{i}"), inputs)
            try:
                TableRoller(find, ctx).roll(table, inputs)
            except DidactError as exc:
                return Outcome(name, False, f"{table.id}: {exc.message}")
            rolled += 1
    return Outcome(name, True, ngettext("{n} roll", "{n} rolls", rolled))


def _lookup_cases(keys: list[str], entries: JSON) -> list[dict[str, Value]]:
    """One input per cell of a lookup table, level by level (`3`, `4-5`, `Fair`, `25+`)."""
    if not keys or not isinstance(entries, dict):
        return [{}]
    cases: list[dict[str, Value]] = []
    for raw, inner in entries.items():
        text = str(raw)
        first = text.partition("-")[0].rstrip("+") if text[:1].isdigit() else text
        value: Value = int(first) if first.isdigit() else text
        cases += [{keys[0]: value, **rest} for rest in _lookup_cases(keys[1:], inner)]
    return cases


def _script(name: str, steps: list[JSON], pack_dir: Path, pack_id: str) -> Outcome:
    from didact.cli.main import main

    with tempfile.TemporaryDirectory(prefix="didact-smoke-") as scratch:
        saved = {k: os.environ.get(k) for k in ("DIDACT_HOME", "DIDACT_CACHE", "DIDACT_PACK_PATH")}
        extra = os.pathsep.join(filter(None, [str(pack_dir.parent), saved["DIDACT_PACK_PATH"]]))
        os.environ.update(
            DIDACT_HOME=str(Path(scratch) / "home"),
            DIDACT_CACHE=str(Path(scratch) / "cache"),
            DIDACT_PACK_PATH=extra,
        )
        try:
            for number, step in enumerate(steps, 1):
                text = str(step.get("run") if isinstance(step, dict) else step)
                try:
                    args = shlex.split(text.replace("{pack}", pack_id))
                except ValueError as exc:  # unbalanced quotes: the step, not the runner, is wrong
                    return Outcome(
                        name,
                        False,
                        _(
                            "step {number} `{command}` can't be read: {error}",
                            number=number,
                            command=text,
                            error=str(exc),
                        ),
                    )
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = main(args)
                checks = step if isinstance(step, dict) else {}
                fails = checks.get("fails") is True
                if code != 0 and not fails:
                    message = (err.getvalue() or out.getvalue()).strip().splitlines()
                    return Outcome(
                        name,
                        False,
                        _(
                            "step {number} `{command}` failed: {error}",
                            number=number,
                            command=text,
                            error=message[0] if message else code,
                        ),
                    )
                if code == 0 and fails:
                    return Outcome(
                        name,
                        False,
                        _("step {number} `{command}` didn't fail", number=number, command=text),
                    )
                printed = out.getvalue() + err.getvalue()  # an expected failure's error too
                for expected in _texts(checks.get("expect")) or []:
                    if expected not in printed:
                        return Outcome(
                            name,
                            False,
                            _(
                                "step {number} `{command}` didn't print {expected}",
                                number=number,
                                command=text,
                                expected=repr(expected),
                            ),
                        )
                for unwanted in _texts(checks.get("expect_not")) or []:
                    if unwanted in printed:
                        return Outcome(
                            name,
                            False,
                            _(
                                "step {number} `{command}` printed {unwanted}",
                                number=number,
                                command=text,
                                unwanted=repr(unwanted),
                            ),
                        )
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    return Outcome(name, True, ngettext("{n} command ran", "{n} commands ran", len(steps)))
