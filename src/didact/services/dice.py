"""Rolling for real: seeds, roll numbers, variables from records, the roll log and replay.

Each roll draws from its own stream, `<seed>:<roll number>`. The seed belongs to the active
campaign (else the world, else the library), so one roll's internals never shift another's,
and `didact replay` can re-run every logged roll and check that it comes out the same.
"""

import hashlib
import json
import re
import secrets
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from didact import __version__
from didact.core import i18n
from didact.core.errors import DidactError, InvalidError, NotFoundError
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON
from didact.core.phrases import english, phrase
from didact.expr import (
    DieSpec,
    Face,
    HashStream,
    PhysicalFaces,
    Registry,
    RollContext,
    Rolled,
    Source,
    default_registry,
    run,
)
from didact.expr.model import Scalar, Value, to_json
from didact.expr.render import collect_flags, collect_notes, line, parts, symbol_counts, to_data
from didact.services.values import record_resolver, record_values, to_value
from didact.store.events import SAY, Cleared, Event, said, undone_seqs
from didact.store.fsutil import atomic_write
from didact.store.repo import Repo

LIBRARY_SCOPE = "global"


def registry_for(repo: Repo) -> tuple[Registry, list[str]]:
    """The dice registry here: built-ins plus the enabled packs' dice, macros and plugins.

    Plain dice never fail over a pack problem: without the packs, the built-ins roll, and the
    returned notes say why.
    """
    from didact.services import packs

    if not repo.initialized():
        return default_registry(), []
    try:
        return packs.active(repo).registry(), []
    except NotFoundError as exc:
        return default_registry(), [
            _("pack dice unavailable ({message}); built-in dice only", message=exc.message)
        ]


# ---------------------------------------------------------------------------- seeds & numbers


def roll_scope(repo: Repo) -> tuple[str, str]:
    """(scope, seed) for rolls right now: the campaign's, else the world's, else the library's."""
    campaign = repo.active_campaign()
    if campaign is not None:
        scope = f"campaign:{campaign.id}"
        return scope, _seed(campaign.other.get("seed"), scope)
    world = repo.active_world()
    if world is not None:
        scope = f"world:{world.id}"
        return scope, _seed(world.other.get("seed"), scope)
    return LIBRARY_SCOPE, _seed(None, LIBRARY_SCOPE)


def _seed(stored: JSON, scope: str) -> str:
    if isinstance(stored, str | int) and str(stored):
        return str(stored)
    return hashlib.sha256(f"didact-seed:{scope}".encode()).hexdigest()[:16]


def _read_counters(repo: Repo) -> dict[str, JSON]:
    path = repo.layout.counters_file
    data: dict[str, JSON] = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            data = loaded if isinstance(loaded, dict) else {}
        except ValueError:
            data = {}
    if not isinstance(data.get("rolls"), int):
        # lost or damaged: rebuild from the log, so numbers (and dice streams) never repeat;
        # other counters (oracle answers, drafts) are kept as they are
        data["rolls"] = highest_logged(repo.log)
    return data


def _roll_number(event: Event) -> int:
    number = event.data.get("roll")
    return number if isinstance(number, int) else 0


def highest_logged(events: Iterable[Event]) -> int:
    """The highest roll number the log knows of: its rolls, and those a history clear
    dropped (its marker keeps the highest number used by then)."""
    highest = 0
    for event in events:
        if event.kind == "roll":
            highest = max(highest, _roll_number(event))
        elif (mark := Cleared.of(event)) is not None:
            highest = max(highest, mark.rolls)
    return highest


def highest_roll(repo: Repo) -> int:
    """The highest roll number used so far, by the counter or the log: the next is above it."""
    counted = _read_counters(repo).get("rolls")
    return max(counted if isinstance(counted, int) else 0, highest_logged(repo.log))


# ---------------------------------------------------------------------------- variables


def parse_var(text: str) -> tuple[str, Scalar]:
    name, sep, raw = text.partition("=")
    name, raw = name.strip().lstrip("@"), raw.strip()
    if not sep or not name:
        raise InvalidError(
            _("invalid --var {text}", text=repr(text)),
            hint=_("write `--var name=value`, e.g. `--var DEX=12`"),
        )
    try:
        value: Scalar = int(raw)
    except ValueError:
        try:
            value = float(raw)
        except ValueError:
            raise InvalidError(
                _("--var {name} must be a number, not {raw}", name=name, raw=repr(raw)),
                hint=_("e.g. `--var DEX=12`"),
            ) from None
    return name, value


# ---------------------------------------------------------------------------- rolling


@dataclass(slots=True)
class KeptFaces:
    """A reroll: keep some faces (non-zero), draw fresh ones for the rest (zeros), in order."""

    keep: list[int]
    fresh: HashStream
    index: int = 0

    def draw(self, die: DieSpec) -> Face:
        position = self.index
        self.index += 1
        if position < len(self.keep) and self.keep[position]:
            return Face(self.keep[position])
        return self.fresh.draw(die)


@dataclass(frozen=True, slots=True)
class RollOutcome:
    rolled: Rolled
    line: str
    number: int | None  # None: not logged (no data home yet)
    event: int | None
    scope: str | None
    stream: str | None
    got: list[str] | None
    used: dict[str, Value] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"#r{self.number}" if self.number is not None else "#r?"

    @property
    def notes(self) -> list[str]:
        notes = collect_notes(self.rolled.result)
        if _squash(self.rolled.text) != _squash(self.rolled.canonical):
            notes.insert(
                0,
                _(
                    "read `{text}` as `{canonical}`",
                    text=self.rolled.text.strip(),
                    canonical=self.rolled.canonical,
                ),
            )
        if self.number is None:
            notes.append(_("not logged: there is no data home yet (`didact init`)"))
        return notes + self.warnings

    def to_data(self) -> dict[str, JSON]:
        result = self.rolled.result
        data: dict[str, JSON] = {
            "roll": self.number,
            "label": self.label,
            "event": self.event,
            "expr": self.rolled.text,
            "canonical": self.rolled.canonical,
            "value": to_json(result.value),
            "line": self.line,
            "flags": list(collect_flags(result)),
            "parts": parts(result),
            "symbols": dict(symbol_counts(result)),
            "notes": list(self.notes),
            "vars": {k: to_json(v) for k, v in self.used.items()},
            "scope": self.scope,
            "result": to_data(result),
        }
        if self.got is not None:
            data["got"] = list(self.got)
        return data


def _squash(text: str) -> str:
    """For spotting a real difference between what was typed and the canonical form."""
    compact = re.sub(r"\s+", "", text).replace("==", "=")
    return re.sub(r"(?<![\w)\]}@.])1d", "d", compact)


def roll(
    repo: Repo,
    expression: str,
    *,
    variables: Mapping[str, Value] | None = None,
    as_record: str | None = None,
    got: str | None = None,
    seed: str | None = None,
    reason: str | None = None,
    command: str | None = None,
    resolver: Callable[[str], Value | None] | None = None,
    keep: list[int] | None = None,
    dry: bool = False,
    registry: Registry | None = None,
) -> RollOutcome:
    """Roll an expression and log it (#r number, stream, faces, variables, result).

    `resolver` reads `@name.field` values (rules pass their own); `keep` rerolls a pool keeping
    some faces (0 = draw fresh); `dry` rolls without logging.
    """
    warnings: list[str] = []
    if registry is None:
        registry, warnings = registry_for(repo)
    base: dict[str, Value] = {}
    entities: tuple[str, ...] = ()
    if as_record:
        located = repo.resolve(as_record)
        base |= record_values(located.entity)
        entities = (str(located.entity.id),)
    base |= dict(variables or {})
    if resolver is None and repo.initialized():
        resolver = record_resolver(repo)

    def attempt(stream: str | None) -> tuple[Rolled, dict[str, Value], list[str] | None]:
        physical = PhysicalFaces.parse(got) if got is not None else None
        fresh = HashStream(stream or secrets.token_hex(8))
        source: Source = physical or (KeptFaces(keep, fresh) if keep is not None else fresh)
        ctx = RollContext(registry, source, base, resolver)
        rolled = run(expression, ctx)
        if physical is not None:
            extra = physical.leftover()
            if extra:
                raise InvalidError(
                    ngettext(
                        "--got has {n} face(s) this roll didn't use: {faces}",
                        "--got has {n} face(s) this roll didn't use: {faces}",
                        len(extra),
                        faces=", ".join(extra),
                    ),
                    hint=_("give exactly the faces rolled, in order"),
                )
            return rolled, ctx.used, physical.record
        return rolled, ctx.used, None

    def describe(done: tuple[Rolled, dict[str, Value], list[str] | None], label: str) -> Described:
        rolled, used, faces = done
        data: dict[str, JSON] = {
            "expr": expression,
            "canonical": rolled.canonical,
            "value": to_json(rolled.result.value),
            "vars": {k: to_json(v) for k, v in used.items()},
            "result": to_data(rolled.result),
        }
        if faces is not None:
            data["got"] = list[JSON](faces)
        if keep is not None:
            data["keep"] = list[JSON](keep)
        return line(label, rolled.canonical, rolled.result, reason), data

    done = logged(
        repo,
        attempt,
        describe,
        seed=seed,
        physical=got is not None,
        reason=reason,
        command=command,
        entities=entities,
        dry=dry,
    )
    rolled, used, faces = done.value
    return RollOutcome(
        rolled,
        done.summary,
        done.number,
        done.event,
        done.scope,
        done.stream,
        faces,
        used,
        warnings,
    )


type Described = tuple[str, dict[str, JSON]]


@dataclass(frozen=True, slots=True)
class Logged[T]:
    value: T
    summary: str
    number: int | None
    event: int | None
    stream: str | None
    scope: str | None


def logged[T](
    repo: Repo,
    perform: Callable[[str | None], T],
    describe: Callable[[T, str], Described],
    *,
    seed: str | None,
    physical: bool,
    reason: str | None,
    command: str | None,
    entities: tuple[str, ...] = (),
    dry: bool = False,
) -> Logged[T]:
    """Take the next roll number, draw from its stream, and log the roll as one event.

    `perform(stream)` does the rolling; `describe(value, label)` gives the one-line summary and
    the data to log (to which the roll number, scope, stream and version are added).
    """
    if dry or not repo.initialized():
        stream = None if physical else (seed or secrets.token_hex(8))
        value = perform(stream)
        summary, _unused = describe(value, "#r?")
        return Logged(value, summary, None, None, stream, None)
    scope, scope_seed = roll_scope(repo)
    with repo.writing():
        counters = _read_counters(repo)
        number = int(counters["rolls"]) + 1  # type: ignore[arg-type]
        stream = None if physical else (seed if seed is not None else f"{scope_seed}:{number}")
        value = perform(stream)
        shown, data = describe(value, f"#r{number}")  # in the reader's language
        with i18n.use(i18n.DEFAULT):  # the log keeps English
            summary, data = describe(value, f"#r{number}")
        data = {"roll": number, **data, "scope": scope, "version": __version__}
        from didact.services.play import marks

        data |= marks(repo)  # the open session, scene and turn
        if stream is not None:
            data["stream"] = stream
        counters["rolls"] = number
        # the counter first: a crash in between skips a number rather than reusing one
        atomic_write(repo.layout.counters_file, json.dumps(counters))
        event = repo.log.append(
            kind="roll",
            summary=summary,
            command=command,
            reason=reason,
            entities=entities,
            data=data,
        )
    return Logged(value, shown, number, event.seq, stream, scope)


def report(
    repo: Repo,
    outcome: str,
    *,
    of: str | None,
    reason: str | None,
    command: str | None,
    entities: tuple[str, ...] = (),
    dry: bool = False,
) -> Logged[str]:
    """Log an outcome that wasn't rolled here (a card drawn, a block tower that fell) as a
    roll: numbered, in the roll log and undoable, but with nothing to replay."""

    def describe(text: str, label: str) -> Described:
        summary = (
            _("{label} reported {what}: {outcome}", label=label, what=of, outcome=text)
            if of
            else _("{label} reported: {outcome}", label=label, outcome=text)
        )
        if reason:
            summary += f" — {reason}"
        data: dict[str, JSON] = {"kind": REPORT, "outcome": text}
        if of:
            data["of"] = of
        return summary, data

    return logged(
        repo,
        lambda _stream: outcome,
        describe,
        seed=None,
        physical=True,
        reason=reason,
        command=command,
        entities=entities,
        dry=dry,
    )


REPORT = "report"  # the kind of a logged roll that was a reported outcome


def roll_number(
    repo: Repo, expression: str, *, reason: str, command: str | None, log: bool = True
) -> int:
    """Roll for a sheet field: logged like any roll (unless `log` is off, e.g. a dry run)."""
    if log and repo.initialized():
        result = roll(repo, expression, reason=reason, command=command).rolled.result.value
    else:
        registry, _unused = registry_for(repo)
        ctx = RollContext(registry, HashStream(secrets.token_hex(8)))
        result = run(expression, ctx).result.value
    if isinstance(result, bool) or not isinstance(result, int):
        raise InvalidError(
            _(
                "{reason}: `{expression}` didn't roll a whole number",
                reason=reason,
                expression=expression,
            ),
            hint=_("use dice that total a number, e.g. `2d6`"),
        )
    return result


# ---------------------------------------------------------------------------- the roll log


def roll_events(repo: Repo, *, scope: str | None) -> list[Event]:
    """Logged rolls, oldest first; only those made in `scope` unless it is None."""
    return [
        e for e in repo.log if e.kind == "roll" and (scope is None or e.data.get("scope") == scope)
    ]


def find_roll(repo: Repo, number: int) -> Event:
    cleared = 0  # the highest roll number a clear of the dice record may have dropped
    for event in repo.log:
        if event.kind == "roll" and _roll_number(event) == number:
            return event
        mark = Cleared.of(event)
        if mark is not None and mark.dice:
            cleared = max(cleared, mark.rolls)
    if number <= cleared:
        raise NotFoundError(
            _("no roll #r{number}: rolls went when the history was cleared", number=number),
            hint=_("see `didact rolls` for what's left"),
        )
    raise NotFoundError(_("no roll #r{number}", number=number), hint=_("see `didact rolls`"))


def void_roll(repo: Repo, event: Event, *, reason: str | None, command: str | None) -> Event:
    """Mark a roll as undone. It stays in the log (marked), and the roll counter never rewinds."""
    if event.kind != "roll":
        raise InvalidError(
            _("{label} is not a roll", label=event.label), hint=_("`didact rolls` lists the rolls")
        )
    if event.seq in undone_seqs(repo.log.all()):
        raise InvalidError(
            _("#r{number} is already undone", number=_roll_number(event)),
            hint=_("`didact rolls` shows which are"),
        )
    words = phrase(N_("undo roll {roll}"), roll=event.summary)
    with repo.writing():
        return repo.log.append(
            kind="undo",
            summary=english(words),
            command=command,
            reason=reason,
            entities=event.entities,
            undoes=event.seq,
            data={SAY: words},
        )


def unmark(repo: Repo, mark: Event, *, reason: str | None, command: str | None) -> Event:
    """Take back a mark on a roll (an undo without files, as `void_roll` logs): an undone undo
    is a redo, so the roll it marked undone stands again."""
    if mark.kind != "undo" or mark.files:
        raise InvalidError(
            _("{label} doesn't mark a roll", label=mark.label),
            hint=_("`didact undo --event {event}` takes a change back", event=f"e{mark.seq}"),
        )
    words = phrase(N_("undo {event}: {what}"), event=mark.label, what=said(mark))
    with repo.writing():
        return repo.log.append(
            kind="undo",
            summary=english(words),
            command=command,
            reason=reason,
            entities=mark.entities,
            undoes=mark.seq,
            data={SAY: words},
        )


@dataclass(frozen=True, slots=True)
class ReplayCheck:
    event: Event
    problem: str | None  # None: reproduced exactly

    @property
    def number(self) -> int:
        return _roll_number(self.event)


def replay(repo: Repo, events: Sequence[Event]) -> list[ReplayCheck]:
    """Re-run logged rolls from their streams (or recorded faces) and compare the results."""
    registry, _unused = registry_for(repo)
    checks: list[ReplayCheck] = []
    for event in events:
        data = event.data
        if data.get("kind") == REPORT:
            continue  # reported, not rolled: nothing to replay
        if data.get("kind") == "table":
            from didact.services.tables import replay_table

            checks.append(ReplayCheck(event, replay_table(repo, event)))
            continue
        if data.get("kind") == "shuffle":
            from didact.services.decks import replay_shuffle

            checks.append(ReplayCheck(event, replay_shuffle(data)))
            continue
        stored_vars = data.get("vars")
        variables: dict[str, Value] = {}
        if isinstance(stored_vars, dict):
            for key, raw in stored_vars.items():
                converted = to_value(raw)
                if converted is not None:
                    variables[key] = converted
        got, stream, kept = data.get("got"), data.get("stream"), data.get("keep")
        source: Source
        if isinstance(got, list):
            source = PhysicalFaces([str(g) for g in got])
        elif isinstance(stream, str) and isinstance(kept, list):
            source = KeptFaces([int(k) for k in kept if isinstance(k, int)], HashStream(stream))
        elif isinstance(stream, str):
            source = HashStream(stream)
        else:
            checks.append(ReplayCheck(event, _("the log entry has no stream or faces")))
            continue
        try:
            rolled = run(str(data.get("expr", "")), RollContext(registry, source, variables))
        except DidactError as exc:
            checks.append(ReplayCheck(event, _("no longer rolls: {message}", message=exc.message)))
            continue
        now = json.loads(json.dumps(to_data(rolled.result)))
        if now != data.get("result"):
            shown = line(f"#r{_roll_number(event)}", rolled.canonical, rolled.result)
            checks.append(ReplayCheck(event, _("came out differently: {shown}", shown=shown)))
        else:
            checks.append(ReplayCheck(event, None))
    return checks
