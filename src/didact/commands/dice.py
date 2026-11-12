"""Dice commands: roll, rolls, replay, odds."""

from typing import Annotated

from didact.commands._common import changeset, open_repo
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.errors import InvalidError, UsageError
from didact.core.i18n import N_, _, ngettext, pgettext
from didact.core.output import JSON, Out, code, table
from didact.expr.model import Value
from didact.store.events import undone_seqs


def _expression(words: tuple[str, ...]) -> str:
    text = " ".join(words).strip()
    if not text:
        raise InvalidError(_("what should I roll?"), hint=_("e.g. `didact roll 4d6kh3`"))
    return text


def _variables(texts: list[str] | None) -> dict[str, Value]:
    from didact.services.dice import parse_var

    return dict(parse_var(t) for t in texts or [])


@command(
    "roll",
    summary="Roll any dice expression; every roll is logged with an id (#r12)",
    writes=True,
    examples=(
        "didact roll 4d6kh3",
        "didact roll 'd20 <= @STR' --as sweeney --reason 'STR save vs the trap'",
        "didact roll '6d10>=8f1'",
        "didact roll '{d8, d6}kh1'          # two weapons: keep the better",
        "didact roll 2d6 --got 6,3          # you rolled real dice: record them",
        "didact roll 'd6!' --dry-run        # how Didact reads it, without rolling",
    ),
    description=(
        "Roll dice. Quote the expression (single quotes are safest: `>`, `<`, `!`, `(`\n"
        "and spaces mean something to the shell). Modifiers attach to the dice without\n"
        "spaces (`4d6kh3`, `6d10>=8`, `d6!`); with spaces, a comparison checks the total\n"
        "(`d20 <= @STR`). The canonical form is echoed back. Variables come from\n"
        "`--as <record>`, `--var name=value` or `@record.field`. Full notation:\n"
        "`didact guide dice`."
    ),
)
def roll(
    ctx: Context,
    *expression: Annotated[str, "the dice expression; quote it", Metavar("expression")],
    as_: Annotated[str | None, "read @variables from this record", Metavar("record")] = None,
    var: Annotated[list[str] | None, "set a variable, e.g. DEX=12", Metavar("name=value")] = None,
    got: Annotated[str | None, "real dice faces in order, e.g. 6,3,4", Metavar("faces")] = None,
    seed: Annotated[str | None, "a fixed stream: same seed, same dice", Metavar("text")] = None,
) -> Out:
    from didact.expr import parse
    from didact.expr.parser import canonical
    from didact.services import dice

    text = _expression(expression)
    repo = open_repo(ctx)
    if ctx.dry_run:
        registry, _unused = dice.registry_for(repo)
        shown = canonical(parse(text, registry), registry)
        return Out(
            data={"dry_run": True, "expr": text, "canonical": shown},
            md=_("dry run: would roll {expr}", expr=code(shown)),
        )
    outcome = dice.roll(
        repo,
        text,
        variables=_variables(var),
        as_record=as_,
        got=got,
        seed=seed,
        reason=ctx.reason,
        command=ctx.command_line,
    )
    lines = [outcome.line, *(_("note: {note}", note=n) for n in outcome.notes)]
    if got is None and repo.initialized():
        from didact.services import profile

        if profile.physical_dice(repo):
            lines.append(
                _("note: this campaign uses physical dice: ask the player, then pass --got")
            )
    return Out(data=outcome.to_data(), md="\n".join(lines))


@command(
    "report",
    summary="Record an outcome that wasn't rolled here (a card, a block tower), logged like a roll",
    writes=True,
    examples=(
        "didact report 'the tower stands' --of 'the tower'",
        "didact report 'the Queen of Spades' --of 'the deck' --about freya",
        "didact report 'heads' --of 'a coin' --reason 'who goes first'",
    ),
    description=(
        "For results Didact didn't produce: a card the player drew, a block tower that fell,\n"
        "a coin flipped at the table. It gets a roll number (#r12) and goes in the roll log\n"
        "(`rolls`), undoable like a roll, but `replay` passes over it: there's nothing to\n"
        "roll again. During a session it's also a result beat in the journal (->), on the\n"
        "chronicle of each record --about names."
    ),
)
def report(
    ctx: Context,
    *outcome: Annotated[str, "what happened", Metavar("outcome")],
    of: Annotated[str | None, "what gave it: the tower, the deck, a coin", Metavar("what")] = None,
    about: Annotated[
        list[str] | None, "a record it concerns (repeatable)", Metavar("record")
    ] = None,
    secret: Annotated[bool, "out of the players' sight: GM views only"] = False,
) -> Out:
    from didact.services import dice, play

    text = " ".join(outcome).strip()
    if not text:
        raise UsageError(
            _("say what happened"), hint=_("e.g. `didact report 'the tower falls' --of tower`")
        )
    repo = open_repo(ctx)
    refs = [str(repo.resolve(r).entity.id) for r in about or []]
    if ctx.dry_run:
        return Out(
            data={"dry_run": True, "outcome": text},
            md=_("dry run: would report {outcome}", outcome=text),
        )
    done = dice.report(
        repo, text, of=of, reason=ctx.reason, command=ctx.command_line, entities=tuple(refs)
    )
    data: dict[str, JSON] = {"roll": done.number, "event": done.event, "outcome": text, "of": of}
    lines = [f"✔ {done.summary}"]
    current = play.load(repo) if repo.active_campaign() is not None else None
    if current is not None and current.session_open and done.number is not None:
        cs = changeset(ctx, repo, N_("log the report #r{roll}"), roll=done.number)
        beat = play.add_beat(
            cs, current, "result", f"{of}: {text}" if of else text,
            rolls=[f"r{done.number}"], about=refs, secret=secret,
        )  # fmt: skip
        cs.apply()
        data["beat"] = beat
        lines.append(_("{beat} {line}", beat=beat["id"], line=play.beat_line(beat)))
    return Out(data=data, md="\n".join(lines))


@command(
    "rolls",
    summary="List recent rolls in this campaign (or everywhere with --all)",
    examples=("didact rolls", "didact rolls --limit 50", "didact rolls --all"),
)
def rolls(
    ctx: Context,
    *,
    limit: Annotated[int, "how many"] = 20,
    all_: Annotated[bool, "include rolls from every campaign and world"] = False,
) -> Out:
    from didact.services import dice

    repo = open_repo(ctx)
    if not repo.initialized():
        return Out(data={"rolls": []}, md=_("no rolls yet"))
    scope, _unused = dice.roll_scope(repo)
    events = dice.roll_events(repo, scope=None if all_ else scope)
    undone = undone_seqs(repo.log.all())
    chosen = list(reversed(events))[:limit]
    where = "everywhere" if all_ else scope
    shown = _("everywhere") if all_ else scope
    if not chosen:
        return Out(data={"rolls": [], "scope": where}, md=_("no rolls yet ({where})", where=shown))
    items: list[JSON] = []
    lines = [
        ngettext(
            "{n} roll ({where}), newest first:",
            "{n} rolls ({where}), newest first:",
            len(chosen),
            where=shown,
        )
    ]
    for event in chosen:
        if event.seq in undone:
            lines.append(_("- {line} (undone)", line=event.summary))
        else:
            lines.append(f"- {event.summary}")
        items.append(
            {
                "roll": event.data.get("roll"),
                "event": event.seq,
                "ts": event.ts,
                "line": event.summary,
                "value": event.data.get("value"),
                "scope": event.data.get("scope"),
                "undone": event.seq in undone,
            }
        )
    return Out(data={"rolls": items, "scope": where}, md="\n".join(lines))


@command(
    "replay",
    summary="Re-run logged rolls and check each comes out exactly the same",
    examples=("didact replay", "didact replay --all"),
)
def replay(
    ctx: Context,
    *,
    all_: Annotated[bool, "check rolls from every campaign and world"] = False,
) -> Out:
    from didact.services import dice

    repo = open_repo(ctx)
    if not repo.initialized():
        return Out(data={"checked": 0, "problems": []}, md=_("no rolls to replay"))
    scope, _unused = dice.roll_scope(repo)
    checks = dice.replay(repo, dice.roll_events(repo, scope=None if all_ else scope))
    where = "everywhere" if all_ else scope
    shown = _("everywhere") if all_ else scope
    problems = [c for c in checks if c.problem]
    data: dict[str, JSON] = {
        "checked": len(checks),
        "scope": where,
        "problems": [
            {"roll": c.number, "event": c.event.seq, "problem": c.problem} for c in problems
        ],
    }
    if not checks:
        return Out(data=data, md=_("no rolls to replay ({where})", where=shown))
    if not problems:
        md = ngettext(
            "✔ {n} roll reproduced exactly ({where})",
            "✔ {n} rolls reproduced exactly ({where})",
            len(checks),
            where=shown,
        )
        return Out(data=data, md=md)
    lines = [
        ngettext(
            "✘ {problems} of {n} roll did not reproduce ({where}):",
            "✘ {problems} of {n} rolls did not reproduce ({where}):",
            len(checks),
            problems=len(problems),
            where=shown,
        )
    ]
    lines += [f"- #r{c.number}: {c.problem}" for c in problems]
    return Out(data=data, md="\n".join(lines), ok=False)


@command(
    "odds",
    summary="Probabilities for a roll: exact when possible, else simulated",
    examples=(
        "didact odds '2d6 >= 8'",
        "didact odds 4d6kh3",
        "didact odds 'd20 <= @STR' --as sweeney",
        "didact odds '6d10>=8f1'",
    ),
)
def odds(
    ctx: Context,
    *expression: Annotated[str, "the dice expression; quote it", Metavar("expression")],
    as_: Annotated[str | None, "read @variables from this record", Metavar("record")] = None,
    var: Annotated[list[str] | None, "set a variable, e.g. DEX=12", Metavar("name=value")] = None,
    simulate: Annotated[bool, "estimate by rolling many times, even if exact odds work"] = False,
    samples: Annotated[int, "rolls to simulate", Metavar("n")] = 20_000,
) -> Out:
    from didact.expr.odds import odds as compute
    from didact.expr.render import number
    from didact.services import dice
    from didact.services.values import record_values

    text = _expression(expression)
    repo = open_repo(ctx)
    variables: dict[str, Value] = {}
    if as_:
        variables |= record_values(repo.resolve(as_).entity)
    variables |= _variables(var)
    if not 100 <= samples <= 1_000_000:
        raise InvalidError(_("--samples must be 100–1,000,000"), hint=_("e.g. `--samples 50000`"))
    registry, _unused = dice.registry_for(repo)
    result = compute(text, registry, variables, samples=samples, exact=not simulate)
    how = (
        _("exact")
        if result.method == "exact"
        else ngettext(
            "simulated, {count} roll",
            "simulated, {count} rolls",
            result.samples or 0,
            count=f"{result.samples:,}",
        )
    )
    data: dict[str, JSON] = {
        "canonical": result.canonical,
        "method": result.method,
        "samples": result.samples,
        "distribution": [{"outcome": o, "chance": p} for o, p in result.distribution.items()],
    }
    note = (
        [_("note: simulated because {why}", why=result.why_simulated)]
        if result.why_simulated
        else []
    )
    if result.is_check:
        chance = result.chance
        data["chance"] = chance
        spread = f" ±{result.margin(chance):.1%}" if result.samples else ""
        md = _(
            "{expr}: {chance}{spread} chance of true ({how})",
            expr=code(result.canonical),
            chance=_percent(chance),
            spread=spread,
            how=how,
        )
        return Out(data=data, md="\n".join([md, *note]))
    outcomes = list(result.distribution)
    data |= {"mean": result.mean, "sd": result.sd, "min": outcomes[0], "max": outcomes[-1]}
    head = _(
        "{expr} ({how}): mean {mean}, sd {sd}, from {low} to {high}",
        expr=code(result.canonical),
        how=how,
        mean=f"{result.mean:.2f}",
        sd=f"{result.sd:.2f}",
        low=number(outcomes[0]),
        high=number(outcomes[-1]),
    )
    rows: list[list[str]] = []
    if len(outcomes) <= 30:
        rows = [
            [number(o), _percent(p), _percent(result.at_least(o))]
            for o, p in result.distribution.items()
        ]
        body = table([pgettext("column", "roll"), _("chance"), _("this or more")], rows)
    else:
        marks = [0.05, 0.25, 0.5, 0.75, 0.95]
        cumulative, found, index = 0.0, [], 0
        for outcome, p in result.distribution.items():
            cumulative += p
            while index < len(marks) and cumulative >= marks[index] - 1e-12:
                found.append([f"{marks[index]:.0%}", number(outcome)])
                index += 1
        body = table([_("percentile"), pgettext("column", "roll")], found)
    return Out(data=data, md="\n".join([head, "", body, *note]))


def _percent(p: float) -> str:
    if 0 < p < 0.0001:
        return "<0.01%"
    if 0.9999 < p < 1:
        return ">99.99%"
    return f"{p:.2%}"
