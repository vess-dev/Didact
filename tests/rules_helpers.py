"""Test helpers for rules: fixture-pack rules and an engine with scripted dice."""

from dataclasses import dataclass, field
from typing import cast

from didact.core.errors import InvalidError, NotFoundError
from didact.core.output import JSON
from didact.expr import DieSpec, Face, PhysicalFaces, Registry, RollContext, default_registry, run
from didact.expr.engine import PoolResult
from didact.expr.model import Value
from didact.expr.render import collect_flags, line, parts, symbol_counts, walk
from didact.packs.build import build
from didact.rules.engine import (
    Engine,
    EntityDone,
    FieldSet,
    ItemDone,
    PoolDone,
    Resolver,
    RollDone,
    Rule,
    TableDone,
    UseDone,
)
from tests.conftest import FIXTURE_PACKS


def pack_rules(pack: str) -> dict[str, Rule]:
    """Every rule of a fixture pack, by bare id."""
    bundle = build(FIXTURE_PACKS / pack).bundle
    assert bundle is not None
    items = cast(dict[str, dict[str, dict[str, JSON]]], bundle["items"])
    found: dict[str, Rule] = {}
    for kind in ("check", "action", "procedure", "trigger"):
        for rule_id, entry in items.get(kind, {}).items():
            data = cast(dict[str, JSON], entry["data"])
            source = str(entry["source"])
            found[rule_id] = Rule(kind, f"{pack}.{rule_id}", pack, data, source)
    return found


type Records = dict[str, dict[str, Value]]


@dataclass
class Scripted:
    """Kept faces first (a reroll), then scripted ones."""

    keep: list[int]
    physical: PhysicalFaces
    index: int = 0

    def draw(self, die: DieSpec) -> Face:
        position, self.index = self.index, self.index + 1
        if position < len(self.keep) and self.keep[position]:
            return Face(self.keep[position])
        return self.physical.draw(die)


@dataclass
class FakeHost:
    """Scripted dice and in-memory records: the engine without a library."""

    faces: list[str]
    records: dict[str, dict[str, Value]]
    registry: Registry = field(default_factory=default_registry)
    changes: list[str] = field(default_factory=list)
    count: int = 0
    rules: dict[str, Rule] = field(default_factory=dict)
    fires: dict[str, tuple[str, ...]] = field(default_factory=dict)  # field → hook triggers

    def roll(
        self, expression: str, reason: str, resolve: Resolver, faces: list[int] | None = None
    ) -> RollDone:
        self.count += 1
        source = Scripted(faces or [], PhysicalFaces(self.faces))
        rolled = run(expression, RollContext(self.registry, source, {}, resolve))
        self.faces = self.faces[source.physical.used :]
        result = rolled.result
        kept: list[int] = []
        faces_rolled: list[int] = []
        for node in walk(result):
            if isinstance(node, PoolResult):
                faces_rolled += [d.face for d in node.pool.dice]
                kept += [d.value for d in node.pool.dice if d.kept]
        tagged = {k: v for k, v in parts(result).items() if isinstance(v, int | float | str | bool)}
        return RollDone(
            f"#r{self.count}",
            line(f"#r{self.count}", rolled.canonical, result),
            result.value,
            kept,
            faces_rolled,
            collect_flags(result),
            cast(dict[str, Value], tagged),
            symbol_counts(result),
        )

    def record(self, ref: str, of: str | None = None) -> str:
        found = next((k for k in self.records if k == ref or k.endswith(f":{ref}")), None)
        if found is None:
            raise InvalidError(f"nothing called {ref!r}")
        return found

    def values(self, record_id: str) -> dict[str, Value]:
        return {"armor": 0, **self.records[record_id]}

    def set_field(self, record_id: str, key: str, op: str, value: Value) -> FieldSet:
        current = self.records[record_id].get(key, 0)
        assert isinstance(current, int) and isinstance(value, int)
        new = value if op == "=" else current + value if op == "+=" else current - value
        self.records[record_id][key] = max(new, 0)
        self.changes.append(f"{record_id}.{key} {op} {value}")
        return FieldSet(triggers=self.fires.get(key, ()))

    def unset_field(self, record_id: str, key: str) -> FieldSet:
        self.records[record_id].pop(key, None)
        self.changes.append(f"{record_id}.{key} unset")
        return FieldSet()

    def make(self, spec: dict[str, JSON], rule: Rule) -> EntityDone:
        name = str(spec.get("name") or spec.get("key") or "")
        record = f"{spec.get('type') or 'note'}:{name.lower().replace(' ', '-')}"
        new = record not in self.records
        self.records.setdefault(record, {"name": name})
        self.changes.append(f"make {record}" if new else f"keep {record}")
        return EntityDone(record, name, new)

    def give(self, record_id: str, item: str, data: dict[str, JSON]) -> ItemDone:
        self.changes.append(f"{record_id} gets {item}")
        return ItemDone(item)

    def take(self, record_id: str, item: str, count: int | None) -> ItemDone:
        self.changes.append(f"{record_id} drops {item}")
        return ItemDone(item)

    def use(self, record_id: str, item: str, spend: int) -> UseDone:
        self.changes.append(f"{record_id} uses {item}")
        return UseDone(
            item, values={"out": False, "gone": False, "left": 1, "die": "", "rolled": 0}
        )

    def item(
        self, record_id: str, field: str, path: str
    ) -> tuple[dict[str, JSON], tuple[str, ...]] | None:
        return None

    def table(self, ref: str, inputs: dict[str, Value], reason: str) -> TableDone:
        return TableDone("#rT", f"a roll on {ref}", {})

    def rule(self, ref: str, from_pack: str) -> Rule:
        found = self.rules.get(ref.rpartition(".")[2])
        if found is None:
            raise NotFoundError(f"no rule {ref!r}")
        return found

    def settings(self, pack: str) -> dict[str, JSON]:
        return {}

    def option(self, name: str) -> JSON:
        return None

    def now(self) -> dict[str, Value]:
        return {}

    def party(self, pcs: bool) -> list[str]:
        return [k for k in self.records if k.startswith("pc:")]  # every PC, and nobody else

    def pool(self, record_id: str, *, roll: bool, drop: int, extra: int, reason: str) -> PoolDone:
        """A pool as a record's `value`: scripted faces drop 1-3s (or `drop` dice alone)."""
        size = self.records[record_id].get("value", 0)
        assert isinstance(size, int)
        left = max(0, size - drop)
        faces = [int(self.faces.pop(0)) for _ in range(left)] if roll else []
        dropped = sum(1 for f in faces if f <= 3)
        left -= dropped
        self.records[record_id]["value"] = left
        self.changes.append(f"{record_id} pool {size} → {left}")
        values: dict[str, Value] = {
            "highest": max(faces, default=0), "dropped": dropped, "left": left,
            "empty": left == 0, "faces": list[Value](faces),
        }  # fmt: skip
        return PoolDone([f"{record_id}: {size}d → {left}d"], [], values)

    def oracle_state(self, rule: Rule) -> str | None:
        return None

    def remind(self, text: str, after: str | None, every: str | None) -> str:
        self.changes.append(f"remind in {after or every}: {text}")
        return f"reminder: {text}"


def pack_registry(pack: str) -> Registry:
    """The dice registry a pack brings (its named dice, macros and chains)."""
    from didact.expr.modifiers import default_registry as fresh
    from didact.packs import dice

    bundle = build(FIXTURE_PACKS / pack).bundle
    assert bundle is not None
    registry = fresh()
    dice.register(
        registry, [(pack.replace("-", "_"), cast(dict[str, JSON], bundle.get("dice") or {}))]
    )
    return registry


def make_engine(
    faces: str, records: Records | None, rules: dict[str, Rule]
) -> tuple[Engine, FakeHost]:
    """An engine with scripted dice (faces in order) and in-memory records."""
    pack = next(iter(rules.values())).pack if rules else ""
    registry = pack_registry(pack) if pack else default_registry()
    host = FakeHost(faces.split(",") if faces else [], dict(records or {}), registry, rules=rules)
    return Engine(host), host
