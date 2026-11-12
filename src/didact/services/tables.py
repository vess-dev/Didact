"""Tables in play: finding them in the enabled packs, and logged, replayable table rolls."""

import secrets
from collections.abc import Mapping
from dataclasses import dataclass

from didact.core.errors import DidactError, NotFoundError
from didact.core.i18n import N_, _
from didact.core.output import JSON
from didact.expr import HashStream, RollContext
from didact.expr.model import Value, to_json
from didact.packs.library import PackSet
from didact.services import packs as pack_service
from didact.services import state
from didact.services.dice import Described, logged
from didact.services.values import to_value
from didact.store.events import Event
from didact.store.repo import Repo
from didact.tables.engine import FindTable, TableResult, TableRoller
from didact.tables.model import Table, table_from


def traits_line(repo: Repo, traits: Mapping[str, JSON]) -> str:
    """Rolled traits, each after its table's title. `roll_tables` keeps each under its table's
    id (`last_job` for `last-job`), for the procedure to read: the title says it better."""
    titles: dict[str, str] = {}
    try:
        for item in pack_service.active(repo).all("table"):
            title = item.data.get("title")
            if isinstance(title, str) and title.strip():
                titles.setdefault(item.id.replace("-", "_"), title.strip())
    except DidactError:
        pass  # no packs to ask: the keys will do
    shown = []
    for key, value in traits.items():
        title = titles.get(key, key.replace("_", " "))
        shown.append(f"{title} {value}" if title.endswith("?") else f"{title}: {value}")
    return "; ".join(shown)


def finder(packs: PackSet) -> FindTable:
    """Look tables up by `pack.id`, or by bare id: first in the asking pack, then anywhere."""
    cache: dict[str, Table] = {}

    def find(ref: str, from_pack: str) -> Table:
        text = ref.strip().replace("/", ".")
        candidates = [text] if "." in text or not from_pack else [f"{from_pack}.{text}", text]
        error: DidactError | None = None
        for candidate in candidates:
            try:
                item = packs.find("table", candidate)
            except NotFoundError as exc:
                error = error or exc
                continue
            if item.qualified not in cache:
                cache[item.qualified] = table_from(item.qualified, item.pack, item.data)
            return cache[item.qualified]
        assert error is not None
        raise error

    return find


@dataclass(frozen=True, slots=True)
class TableOutcome:
    table: Table
    results: list[TableResult]
    summary: str
    number: int | None
    event: int | None

    @property
    def label(self) -> str:
        return f"#r{self.number}" if self.number is not None else "#r?"

    def lines(self) -> list[str]:
        if len(self.results) == 1:
            lines = self.results[0].lines()
            return [f"{self.label} {lines[0]}", *lines[1:]]
        lines = [f"{self.label} {self.table.id} ×{len(self.results)}:"]
        for result in self.results:
            first, *rest = result.lines()
            lines += [f"- {first}", *(f"  {line}" for line in rest)]
        return lines

    def to_data(self) -> dict[str, JSON]:
        return {
            "roll": self.number,
            "label": self.label,
            "event": self.event,
            "table": self.table.id,
            "title": self.table.title,
            "results": [r.to_data() for r in self.results],
            "text": [r.text for r in self.results]
            if len(self.results) > 1
            else self.results[0].text,
        }


def roll_table(
    repo: Repo,
    ref: str,
    *,
    inputs: Mapping[str, Value] | None = None,
    times: int = 1,
    seed: str | None = None,
    reason: str | None = None,
    command: str | None = None,
    dry: bool = False,
    packs: PackSet | None = None,
    entry: str | None = None,
) -> TableOutcome:
    """Roll a table (`times` times), logged. `entry`: that entry chosen instead (by its key),
    and what it goes on to rolled."""
    active = packs or pack_service.active(repo)
    registry = active.registry()
    find = finder(active)
    table = find(ref, "")
    given = dict(inputs or {})

    memory = _memory(repo)
    picked: dict[str, str] = {}

    def perform(stream: str | None) -> list[TableResult]:
        ctx = RollContext(registry, HashStream(stream or secrets.token_hex(8)), given)
        roller = TableRoller(find, ctx, memory)
        if entry is not None:
            rolled = [roller.take(table, entry, given)]
        else:
            rolled = [roller.roll(table, given) for _unused in range(times)]
        picked.update(roller.picked)
        return rolled

    def describe(results: list[TableResult], label: str) -> Described:
        if len(results) == 1:
            summary = f"{label} {results[0].lines()[0]}"
        else:
            summary = f"{label} {table.id} ×{len(results)}: " + " | ".join(r.text for r in results)
        if reason:
            summary += f" — {reason}"
        data: dict[str, JSON] = {
            "kind": "table",
            "table": table.id,
            "inputs": {k: to_json(v) for k, v in given.items()},
            "times": times,
            "result": [r.to_data() for r in results],
        }
        if entry is not None:
            data["entry"] = entry  # chosen, not rolled: what it went on to was rolled
        return summary, data

    done = logged(
        repo, perform, describe, seed=seed, physical=False, reason=reason, command=command, dry=dry
    )
    if picked and done.number is not None:  # tables that remember: keep what came up
        from didact.store.changeset import Changeset

        cs = Changeset(repo, summary="", command=command).say(
            N_("remember {table}: {picked}"), table=table.id, picked=", ".join(picked.values())
        )
        state.plan(cs, MEMORY, {**memory, **picked})
        if not cs.is_empty():
            cs.apply()
    return TableOutcome(table, done.value, done.summary, done.number, done.event)


MEMORY = "tables"


def _memory(repo: Repo) -> dict[str, str]:
    if not repo.initialized() or repo.active_world() is None:
        return {}
    return {k: str(v) for k, v in state.load(repo, MEMORY).items()}


def replay_table(repo: Repo, event: Event) -> str | None:
    """Re-roll a logged table roll from its stream; None if it comes out the same."""
    data = event.data
    stream = data.get("stream")
    if not isinstance(stream, str):
        return _("the log entry has no stream")
    raw_inputs = data.get("inputs")
    inputs: dict[str, Value] = {}
    if isinstance(raw_inputs, dict):
        for key, raw in raw_inputs.items():
            converted = to_value(raw)
            if converted is not None:
                inputs[key] = converted
    active = pack_service.active(repo)
    find = finder(active)
    try:
        table = find(str(data.get("table")), "")
        ctx = RollContext(active.registry(), HashStream(stream), inputs)
        roller = TableRoller(find, ctx)
        times = data.get("times", 1)
        chosen = data.get("entry")
        results = (
            [roller.take(table, chosen, inputs)]
            if isinstance(chosen, str)
            else [
                roller.roll(table, inputs)
                for _unused in range(times if isinstance(times, int) else 1)
            ]
        )
    except DidactError as exc:
        return _("no longer rolls: {message}", message=exc.message)
    now = [r.to_data() for r in results]
    import json

    if json.loads(json.dumps(now)) != data.get("result"):
        return _("came out differently: {shown}", shown=" | ".join(r.text for r in results))
    return None
