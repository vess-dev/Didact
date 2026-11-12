"""Oracles: ask, meaning, interpret; list and show oracles; the history of answers."""

from typing import TYPE_CHECKING, Annotated

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.errors import DidactError, InvalidError
from didact.core.i18n import N_, _
from didact.core.output import JSON, Out, code
from didact.store.changeset import Changeset

if TYPE_CHECKING:
    from didact.services.oracles import Answer


def _answered(ctx: Context, cs: Changeset, answer: Answer) -> Out:
    head = answer.head()
    label = answer.label.lstrip("#")
    hint = _(
        "interpret it: {command} ({prompt})",
        command=code(f"didact interpret {label} '…'"),
        prompt=answer.prompt,
    )
    data: dict[str, JSON] = {
        "oracle": answer.oracle.qualified,
        "number": answer.number,
        "kind": answer.kind,
        "answer": answer.text,
        "question": answer.question,
        "odds": answer.odds,
        "flags": list[JSON](answer.run.flags if answer.run else []),
        "rolls": list[JSON](answer.rolls),
    }
    if cs.is_empty():
        return Out(data=data, md="\n".join([head, *answer.lines, hint]))
    out = finish(ctx, cs, done=_("kept as {label}", label=answer.label), extra=data)
    return Out(data=out.data, md="\n".join([head, *answer.lines, out.md, hint]), ok=out.ok)


@command(
    "ask",
    summary="Ask the oracle a yes/no question (with odds): the answer is rolled and kept",
    writes=True,
    examples=(
        "didact ask 'Is the door locked?' --odds likely",
        "didact ask 'Does the ferryman know Sweeney?'",
        "didact ask 'Is anyone home?' --oracle my-oracle.chart",
        "didact ask 'Do I climb the wall?' --odds likely --with as_rule=true",
    ),
    description=(
        "Ask what the fiction can't answer yet. The answer is numbered (#o12), logged with its\n"
        "rolls, and during a session written to the journal. Then say what it means:\n"
        "`didact interpret o12 '…'`. The oracle is the campaign's (`campaign set oracle=…`),\n"
        "else the one a pack brings, else Didact's own yes/no oracle."
    ),
)
def ask(
    ctx: Context,
    *question: Annotated[str, "the question", Metavar("question")],
    odds: Annotated[str | None, "how likely: e.g. unlikely, even, likely", Metavar("odds")] = None,
    oracle: Annotated[str | None, "which oracle", Metavar("oracle")] = None,
    with_: Annotated[
        list[str] | None, "more for the oracle's check: name=value", Metavar("name=value")
    ] = None,
) -> Out:
    from didact.services import oracles

    text = " ".join(question).strip()
    if not text:
        raise InvalidError(_("ask a question"), hint=_("e.g. `didact ask 'Is the door locked?'`"))
    repo = open_repo(ctx)
    chosen = oracles.pick(repo, oracle)
    cs = changeset(ctx, repo, N_("ask: {question}"), question=text)
    extra = dict(oracles.parse_with(item) for item in with_ or [])
    answer = oracles.ask(
        cs, chosen, text, odds, dry=ctx.dry_run, command=ctx.command_line, extra=extra
    )
    cs.summary, cs.phrase = answer.head()[:120], None  # the question and the oracle's words
    return _answered(ctx, cs, answer)


@command(
    "meaning",
    summary="Draw meaning words from the oracle (e.g. an action and a theme) to interpret",
    writes=True,
    examples=("didact meaning", "didact meaning --table action --table descriptor"),
)
def meaning(
    ctx: Context,
    *,
    table: Annotated[list[str] | None, "roll these tables instead", Metavar("table")] = None,
    oracle: Annotated[str | None, "which oracle", Metavar("oracle")] = None,
) -> Out:
    from didact.services import oracles

    repo = open_repo(ctx)
    chosen = oracles.pick(repo, oracle)
    cs = changeset(ctx, repo, N_("meaning"))
    answer = oracles.meaning(cs, chosen, table, dry=ctx.dry_run, command=ctx.command_line)
    cs.summary, cs.phrase = answer.head()[:120], None  # the oracle's own words
    return _answered(ctx, cs, answer)


@command(
    "interpret",
    summary="Say what an oracle answer meant; it's kept with the answer (and in the journal)",
    writes=True,
    examples=("didact interpret o12 'The lock is rusted shut, but the hinges are loose.'",),
)
def interpret(
    ctx: Context,
    answer: Annotated[str, "the answer, e.g. o12", Metavar("answer")],
    *text: Annotated[str, "what it means in the fiction", Metavar("text")],
) -> Out:
    from didact.services import oracles

    reading = " ".join(text).strip()
    if not reading:
        raise InvalidError(
            _("say what it means"), hint=_("e.g. `didact interpret o12 'The door gives.'`")
        )
    repo = open_repo(ctx)
    number = oracles.parse_label(answer)
    cs = changeset(ctx, repo, N_("interpret #o{number}"), number=number)
    found = oracles.interpret(cs, number, reading)
    extra: dict[str, JSON] = {
        "number": number,
        "answer": found.get("text"),
        "interpretation": reading,
    }
    return finish(ctx, cs, done=f"#o{number} {found.get('text')}: {reading}", extra=extra)


@command(
    "oracle list",
    summary="The oracles the enabled packs bring",
    examples=("didact oracle list",),
)
def oracle_list(ctx: Context) -> Out:
    from didact.services import oracles

    repo = open_repo(ctx)
    found = oracles.available(repo)
    lines = [f"- {o.qualified}: {o.data.get('title', o.id)}" for o in found]
    items: list[JSON] = [
        {"id": o.qualified, "title": o.data.get("title"), "odds": o.data.get("odds")} for o in found
    ]
    return Out(data={"oracles": items}, md="\n".join([_("oracles:"), *lines]))


@command(
    "oracle show",
    summary="An oracle: how to ask it, its odds, and the state it keeps here",
    examples=("didact oracle show", "didact oracle show core.yes-no"),
)
def oracle_show(
    ctx: Context, oracle: Annotated[str | None, "which oracle", Metavar("oracle")] = None
) -> Out:
    from didact.services import oracles

    repo = open_repo(ctx)
    chosen = oracles.pick(repo, oracle)
    data = chosen.data
    lines = [f"{chosen.qualified}: {data.get('title', chosen.id)}"]
    if data.get("help"):
        lines.append(" ".join(str(data["help"]).split()))
    odds = data.get("odds")
    if isinstance(odds, list):
        lines.append(_("odds: {odds}", odds=", ".join(str(o) for o in odds)))
    meaning = data.get("meaning")
    if isinstance(meaning, list):
        lines.append(_("meaning tables: {tables}", tables=", ".join(str(m) for m in meaning)))
    state: dict[str, JSON] = {}
    if isinstance(data.get("state"), dict):
        entity_id = oracles.state_id(chosen)
        try:
            state = repo.resolve(str(entity_id)).entity.fields
            lines.append(_("state: {state}", state=", ".join(f"{k} {v}" for k, v in state.items())))
        except DidactError:
            lines.append(_("state: not started yet (the first question starts it)"))
    data_out: dict[str, JSON] = {
        "oracle": chosen.qualified,
        "title": data.get("title"),
        "help": data.get("help"),
        "odds": odds if isinstance(odds, list) else [],
        "state": state,
    }
    return Out(data=data_out, md="\n".join(lines))


@command(
    "oracle history",
    summary="The latest oracle answers and what they meant",
    examples=("didact oracle history", "didact oracle history --limit 50"),
)
def oracle_history(ctx: Context, *, limit: Annotated[int, "how many", Metavar("n")] = 20) -> Out:
    from didact.services import oracles

    repo = open_repo(ctx)
    entries = oracles.history(repo, limit=None)
    readings: dict[int, list[str]] = {}
    for entry in entries:
        if entry.get("kind") == "interpretation":
            readings.setdefault(int(str(entry.get("n"))), []).append(str(entry.get("text")))
    answers = [e for e in entries if e.get("kind") != "interpretation"][-limit:]
    if not answers:
        return Out(data={"answers": []}, md=_("no oracle answers yet: `didact ask '…'`"))
    lines: list[str] = []
    for entry in answers:
        number = int(str(entry.get("n")))
        if entry.get("kind") == "meaning":
            lines.append(_("- #o{number} meaning: {text}", number=number, text=entry.get("text")))
        else:
            odds = f" ({entry.get('odds')})" if entry.get("odds") else ""
            lines.append(f"- #o{number} ? {entry.get('question')}{odds} → {entry.get('text')}")
        lines += [f"  → {r}" for r in readings.get(number, [])]
    return Out(data={"answers": list[JSON](answers)}, md="\n".join(lines))
