"""Oracles: ask yes/no questions, draw meaning words, and keep what the answers meant.

An oracle is a pack item (`oracles/*.yaml`) that names:
- the check that answers (`ask`);
- the tables for meaning words (`meaning`);
- the odds it knows;
- any state it keeps per campaign (a chaos factor, say).

That state lives in a record (`oracle:<pack>-<id>`) that its rules read as `@oracle.chaos`
and change with `set` steps.

Every answer gets a number (`#o12`) and is kept in `oracles.jsonl`: the campaign's, or the
world's when there is no campaign. `didact interpret o12 '…'` stores what it meant. During a
session, both answers and interpretations also go into the journal.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from didact.core.clock import now_iso
from didact.core.errors import InvalidError, NotFoundError
from didact.core.i18n import N_, _
from didact.core.ids import EntityId, Scope
from didact.core.output import JSON
from didact.packs.library import Item
from didact.rules.engine import Engine, Run
from didact.services import counters, packs, play, records, rules, tables
from didact.store.changeset import Changeset
from didact.store.repo import Repo

DEFAULT = "core.yes-no"


@dataclass(slots=True)
class Answer:
    number: int | None  # None in a dry run
    oracle: Item
    kind: str  # ask | meaning
    text: str  # "Yes, but…" or "betray · oath"
    question: str = ""
    odds: str = ""
    run: Run | None = None
    rolls: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"#o{self.number}" if self.number is not None else "#o?"

    def head(self) -> str:
        if self.kind == "meaning":
            return f"{self.label} meaning: {self.text}"
        odds = f" ({self.odds})" if self.odds else ""
        return f"{self.label} ? {self.question or '(a question)'}{odds} → {self.text}"

    @property
    def prompt(self) -> str:
        raw = self.oracle.data.get("prompt")
        return str(raw).strip() if isinstance(raw, str) else _("Interpret it in the fiction.")


def available(repo: Repo) -> list[Item]:
    return list(packs.active(repo).all("oracle"))


def pick(repo: Repo, ref: str | None) -> Item:
    """The oracle named, else the campaign's (`campaign set oracle=…`), else a pack's, else core."""
    active = packs.active(repo)
    if ref:
        return active.find("oracle", ref)
    campaign = repo.active_campaign()
    chosen = campaign.other.get("oracle") if campaign is not None else None
    if isinstance(chosen, str):
        return active.find("oracle", chosen)
    found = [o for o in active.all("oracle") if o.pack != "core"]
    if len(found) == 1:
        return found[0]
    if found:
        options = ", ".join(o.qualified for o in found)
        raise InvalidError(
            _("several oracles are enabled: {options}", options=options),
            hint=_("pick one with --oracle, or `didact campaign set oracle=<id>`"),
        )
    return active.find("oracle", DEFAULT)


# ---------------------------------------------------------------------------- state


def state_id(oracle: Item) -> EntityId:
    return EntityId("oracle", f"{oracle.pack}-{oracle.id}")


def ensure_state(
    repo: Repo, oracle: Item, *, dry: bool, command: str | None, force: bool = False
) -> str | None:
    """The oracle's state record, if it keeps state (or `force`: lists need one); started with
    its values on first use.

    Starting it is its own change, applied before the question, so the question's rules can
    read and change it like any record.
    """
    spec = oracle.data.get("state")
    if not isinstance(spec, dict) or not spec:
        if not force:
            return None
        spec = {}
    entity_id = state_id(oracle)
    scope = _home_scope(repo)
    if repo.exists(scope, entity_id):
        return str(entity_id)
    if dry:
        raise InvalidError(
            _("{oracle} hasn't started its state here yet", oracle=oracle.qualified),
            hint=_("ask once without --dry-run to start it"),
        )
    fields: dict[str, JSON] = {}
    for name, raw in spec.items():
        fields[name] = raw.get("start") if isinstance(raw, dict) else raw
    title = str(oracle.data.get("title") or oracle.id)
    entity = records.build_entity(entity_id, f"{title} state", {"fields": fields})
    cs = Changeset(repo, summary="", command=command).say(
        N_("start {oracle}'s state"), oracle=oracle.qualified
    )
    records.create(cs, scope, entity)
    cs.apply()
    return str(entity_id)


def _home_scope(repo: Repo) -> Scope:
    campaign = repo.active_campaign()
    if campaign is not None:
        return Scope("campaign", campaign.id)
    return Scope("world", repo.require_world().id)


# ---------------------------------------------------------------------------- the log


def log_path(repo: Repo) -> Path:
    campaign = repo.active_campaign()
    if campaign is not None:
        return play.campaign_dir(repo) / "oracles.jsonl"
    return repo.layout.world_dir(repo.require_world().id) / "oracles.jsonl"


def _next_number(repo: Repo) -> int:
    """The next oracle number: like roll numbers, never reused, even after an undo."""
    return counters.next_number(repo, "oracles", floor=lambda: _highest(repo))


def _highest(repo: Repo) -> int:
    try:
        return max((int(cast(int, e.get("n", 0))) for e in history(repo, limit=None)), default=0)
    except InvalidError:
        return 0


def history(repo: Repo, *, limit: int | None = 20) -> list[dict[str, JSON]]:
    text = repo.read_text(log_path(repo)) or ""
    found = [json.loads(line) for line in text.splitlines() if line.strip()]
    items = [f for f in found if isinstance(f, dict)]
    return items[-limit:] if limit else items


def _record(cs: Changeset, answer: Answer, dry: bool) -> None:
    if dry:
        return
    repo = cs.repo
    answer.number = _next_number(repo)
    entry: dict[str, JSON] = {
        "n": answer.number,
        "ts": now_iso(),
        "oracle": answer.oracle.qualified,
        "kind": answer.kind,
        "text": answer.text,
        "rolls": list[JSON](answer.rolls),
    }
    if answer.question:
        entry["question"] = answer.question
    if answer.odds:
        entry["odds"] = answer.odds
    if answer.run is not None and answer.run.flags:
        entry["flags"] = list[JSON](answer.run.flags)
    entry |= play.marks(repo)
    cs.append(log_path(repo), json.dumps(entry, ensure_ascii=False) + "\n")
    current = play.load(repo)
    if current.session_open:
        beat = answer.head().split(" ", 1)[1].removeprefix("? ").removeprefix("meaning: ")
        text = (
            f"{beat} ({answer.label})"
            if answer.kind == "ask"
            else f"meaning: {beat} ({answer.label})"
        )
        play.add_beat(cs, current, "oracle", text, rolls=[r.lstrip("#") for r in answer.rolls])


# ---------------------------------------------------------------------------- asking


def ask(
    cs: Changeset,
    oracle: Item,
    question: str,
    odds: str | None,
    *,
    dry: bool,
    command: str | None,
    extra: dict[str, str] | None = None,
) -> Answer:
    repo = cs.repo
    active = packs.active(repo)
    rule = rules.find_rule(active, str(oracle.data.get("ask")), oracle.pack)
    params = rule.params
    unknown = sorted(set(extra or {}) - set(params))
    if unknown:
        raise InvalidError(
            _("{rule} takes no {name}", rule=rule.id, name=repr(unknown[0])),
            hint=_("it takes: {params}", params=", ".join(params)),
        )
    known = [str(o) for o in cast(list[JSON], oracle.data.get("odds") or [])]
    if odds is not None and known and odds not in known:
        raise InvalidError(
            _("odds are one of: {odds}", odds=", ".join(known)),
            hint=_("not {odds}", odds=repr(odds)),
        )
    args: dict[str, str] = {}
    if "question" in params and question:
        args["question"] = question
    if "odds" in params and odds:
        args["odds"] = odds
    state = ensure_state(repo, oracle, dry=dry, command=command) if "oracle" in params else None
    if state is not None:
        args["oracle"] = state
    args |= extra or {}
    host = rules.LibraryHost(repo, cs, active, dry, command)
    result = Engine(host).run(rule, args)
    shown = odds or str(result.params.get("odds", "")) if "odds" in params else ""
    answer = Answer(
        None, oracle, "ask", result.outcome or "(no answer)", question, shown, result,
        list(result.rolls), list(result.lines),
    )  # fmt: skip
    _record(cs, answer, dry)
    return answer


def meaning(
    cs: Changeset, oracle: Item, wanted: list[str] | None, *, dry: bool, command: str | None
) -> Answer:
    repo = cs.repo
    names = wanted or [str(t) for t in cast(list[JSON], oracle.data.get("meaning") or [])]
    if not names:
        raise NotFoundError(
            _("{oracle} has no meaning tables", oracle=oracle.qualified),
            hint=_("name some with --table"),
        )
    words: list[str] = []
    rolls: list[str] = []
    lines: list[str] = []
    for name in names:
        ref = name if "." in name else f"{oracle.pack}.{name}"
        outcome = tables.roll_table(
            repo, ref, reason=f"meaning: {oracle.qualified}", command=command
        )
        first = outcome.results[0]
        columns = [c.text for c in first.columns.values()]  # a pair: "Abandon · Advantage"
        words.append(" · ".join(columns) if columns else first.text)
        rolls.append(outcome.label)
        lines += outcome.lines()
    answer = Answer(None, oracle, "meaning", " · ".join(words), rolls=rolls, lines=lines)
    _record(cs, answer, dry)
    return answer


def interpret(cs: Changeset, number: int, text: str) -> dict[str, JSON]:
    """Store what an answer meant: in the oracle log, and the journal during a session."""
    repo = cs.repo
    found = next((e for e in history(repo, limit=None) if e.get("n") == number), None)
    if found is None:
        raise NotFoundError(
            _("no oracle answer #o{number} here", number=number),
            hint=_("see `didact oracle history`"),
        )
    entry: dict[str, JSON] = {
        "n": number,
        "ts": now_iso(),
        "kind": "interpretation",
        "text": text.strip(),
    }
    entry |= play.marks(repo)
    cs.append(log_path(repo), json.dumps(entry, ensure_ascii=False) + "\n")
    current = play.load(repo)
    if current.session_open:
        play.add_beat(cs, current, "result", f"{text.strip()} (#o{number})")
    return found


def parse_with(text: str) -> tuple[str, str]:
    name, sep, value = text.partition("=")
    if not sep or not name.strip():
        raise InvalidError(
            _("write it as name=value, not {text}", text=repr(text)),
            hint=_("e.g. --with as_rule=true"),
        )
    return name.strip(), value.strip()


def parse_label(text: str) -> int:
    cleaned = text.strip().lstrip("#").lower().removeprefix("o")
    if not cleaned.isdigit():
        raise InvalidError(
            _("not an oracle answer: {text}", text=repr(text)),
            hint=_("answers look like o12 or #o12"),
        )
    return int(cleaned)
