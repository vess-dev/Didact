"""Rules: list, show, do, resolve, pending."""

import json
from typing import Annotated, cast

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core import labels
from didact.core.context import Context
from didact.core.errors import InvalidError
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON, Out, code
from didact.core.phrases import phrase


def _args(texts: tuple[str, ...], flags: set[str] | None = None) -> dict[str, str]:
    """`name=value` pairs; a flag parameter can stand alone (`protect` is `protect=true`)."""
    found: dict[str, str] = {}
    for text in texts:
        key, sep, value = text.partition("=")
        if not sep and flags and key.strip() in flags:
            found[key.strip()] = "true"
            continue
        if not sep or not key.strip():
            hint = (
                _(
                    "give parameters as name=value, e.g. who=freya; flags can stand alone: {flags}",
                    flags=", ".join(sorted(flags)),
                )
                if flags
                else _("give parameters as name=value, e.g. who=freya")
            )
            raise InvalidError(_("can't read {text}", text=repr(text)), hint=hint)
        found[key.strip()] = value.strip()
    return found


@command(
    "rules list",
    summary="List the rules in the enabled packs (checks, actions, procedures, triggers)",
    examples=("didact rules list", "didact rules list --kind check"),
)
def rules_list(
    ctx: Context,
    *,
    kind: Annotated[
        str | None, "only this kind: check, action, procedure, trigger", Metavar("kind")
    ] = None,
) -> Out:
    from didact.services import packs, rules

    repo = open_repo(ctx)
    found = [r for r in rules.all_rules(packs.active(repo)) if kind is None or r.kind == kind]
    if not found:
        return Out(data={"rules": []}, md=_("no rules in the enabled packs"))
    lines = [ngettext("{n} rule:", "{n} rules:", len(found))]
    rows: list[JSON] = []
    for rule in found:
        about = str(rule.data.get("help") or "").strip().split("\n")[0]
        kind_ = labels.inline(rule.kind, labels.item_kind(rule.kind))
        lines.append(f"- {kind_} {rule.id} · {rule.title}" + (f": {about}" if about else ""))
        rows.append({"id": rule.id, "kind": rule.kind, "title": rule.title, "usage": rule.usage()})
    return Out(data={"rules": rows}, md="\n".join(lines))


@command(
    "rules show",
    summary="Explain a rule: what it does, its parameters, and how to run it",
    examples=("didact rules show save", "didact rules show my-system.attack --detail full"),
)
def rules_show(ctx: Context, ref: Annotated[str, "the rule", Metavar("rule")]) -> Out:
    from didact.services import packs, rules

    repo = open_repo(ctx)
    rule = rules.find_rule(packs.active(repo), ref)
    data = rule.data
    kind = labels.inline(rule.kind, labels.item_kind(rule.kind))
    lines = [f"{kind} {rule.id} · {rule.title}", _("run: {usage}", usage=code(rule.usage()))]
    if data.get("help"):
        lines.append(str(data["help"]).strip())
    for param in rule.params.values():
        extra = " " + _("(one of {values})", values=", ".join(param.values)) if param.values else ""
        default = (
            ", " + _("default {value}", value=param.default) if param.default is not None else ""
        )
        lines.append(
            f"- `{param.name}`: {param.kind}{extra}{default}"
            + (f" · {param.help}" if param.help else "")
        )
    for key in ("prompt", "roll", "success"):
        value = data.get(key)
        if value is not None:
            shown = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            lines.append(f"{key}: {shown}")
    bands = data.get("bands")
    if isinstance(bands, dict):
        lines.append(
            _("outcomes: {bands}", bands=" · ".join(f"{k}: {v}" for k, v in bands.items()))
        )
    options = data.get("options")
    if isinstance(options, dict):
        lines.append(
            _(
                "after the roll: {options} (`didact resolve`)",
                options=", ".join([*options, "accept"]),
            )
        )
    lines.append(_("source: {source}", source=rule.source))
    full = [*lines, "", "```json", json.dumps(data, indent=2, ensure_ascii=False), "```"]
    out: dict[str, JSON] = {
        "id": rule.id,
        "kind": rule.kind,
        "title": rule.title,
        "usage": rule.usage(),
        "data": data,
    }
    return Out(data=out, md="\n".join(lines), md_full="\n".join(full))


def _show_run(result: object, head: str) -> list[str]:
    from didact.rules.engine import Run, option_label

    assert isinstance(result, Run)
    lines = [head, *result.lines]
    if result.options:
        lines.append(
            _(
                "pending: {options}",
                options=" · ".join(
                    f"{k} ({option_label(k, v)})" for k, v in result.options.items()
                ),
            )
        )
    return lines


@command(
    "do",
    summary="Run a rule: a check, action, procedure or trigger (rules as function calls)",
    writes=True,
    examples=(
        "didact do save who=freya attr=STR",
        "didact do my-system.attack attacker=freya target=troll weapon=d8",
        "didact do watch action=travel --dry-run",
    ),
    description=(
        "Run a rule from the enabled packs with name=value parameters (a flag can stand alone:\n"
        "`protect` is `protect=true`). Dice are rolled and logged, changes are applied as one\n"
        "undoable change, and prompts tell you what to\n"
        "narrate or decide. A roll that allows push/burn/reroll comes back pending: finish it\n"
        "with `didact resolve <roll> <option>`."
    ),
)
def do(
    ctx: Context,
    ref: Annotated[str, "the rule", Metavar("rule")],
    *args: Annotated[str, "parameters: name=value", Metavar("name=value")],
) -> Out:
    from didact.services import packs, rules

    repo = open_repo(ctx)
    found = rules.find_rule(packs.active(repo), ref)
    params = _args(args, {p.name for p in found.params.values() if p.kind == "flag"})
    cs = changeset(ctx, repo, N_("do {rule}"), rule=ref)
    rule, result = rules.run(repo, cs, ref, params, dry=ctx.dry_run, command=ctx.command_line)
    shown = ", ".join(f"{k}={v}" for k, v in params.items())
    verdict: JSON = phrase(N_("pending")) if result.options else result.outcome
    if shown and verdict:
        cs.say(N_("do {rule} ({params}): {verdict}"), rule=rule.id, params=shown, verdict=verdict)
    elif shown:
        cs.say(N_("do {rule} ({params})"), rule=rule.id, params=shown)
    elif verdict:
        cs.say(N_("do {rule}: {verdict}"), rule=rule.id, verdict=verdict)
    else:
        cs.say(N_("do {rule}"), rule=rule.id)
    lines = _show_run(result, f"{rule.kind} {rule.id}" + (f" ({shown})" if shown else ""))
    if repo.active_world() is not None:
        from didact.services import rulings

        lines += [rulings.line(e) for e in rulings.for_rule(repo, rule.id)]
    if result.options:
        key = result.rolls[0] if result.rolls else rule.id
        lines.append(_("finish with {command}", command=code(f"didact resolve {key} <option>")))
    data = result.to_data()
    if cs.is_empty():
        if ctx.dry_run:
            lines.insert(0, _("dry run (nothing kept):"))
        return Out(data=data, md="\n".join(lines))
    if result.options:
        done = _("{rule}: pending", rule=rule.id)
    else:
        done = f"{rule.id}: {result.outcome}" if result.outcome else rule.id
    out = finish(ctx, cs, done=done, extra=data)
    return Out(data=out.data, md="\n".join([*lines, out.md]), ok=out.ok)


@command(
    "resolve",
    summary="Finish a pending roll with one of its options (push, burn, reroll, accept, …)",
    writes=True,
    examples=("didact resolve r12 push", "didact resolve r12 accept"),
)
def resolve(
    ctx: Context,
    roll: Annotated[str, "the pending roll, e.g. r12", Metavar("roll")],
    option: Annotated[str, "the option to take", Metavar("option")],
) -> Out:
    from didact.services import rules

    repo = open_repo(ctx)
    cs = changeset(ctx, repo, N_("resolve {roll}: {option}"), roll=roll, option=option)
    rule, result = rules.resolve(repo, cs, roll, option, command=ctx.command_line)
    cs.say(
        N_("resolve {roll} ({rule}): {option} → {outcome}"),
        roll=roll,
        rule=rule.id,
        option=option,
        outcome=result.outcome,
    )
    lines = _show_run(result, f"{rule.id} {roll}: {option}")
    out = finish(ctx, cs, done=f"{rule.id}: {result.outcome}", extra=result.to_data())
    return Out(data=out.data, md="\n".join([*lines, out.md]), ok=out.ok)


@command(
    "pending",
    summary="List rolls waiting for a decision (push, burn, accept, …)",
    examples=("didact pending",),
)
def pending(ctx: Context) -> Out:
    from didact.services import rules

    repo = open_repo(ctx)
    waiting = rules.pending(repo)
    if not waiting:
        return Out(data={"pending": {}}, md=_("no pending rolls"))
    from didact.rules.engine import option_label

    lines = [ngettext("{n} pending roll:", "{n} pending rolls:", len(waiting))]
    for key, entry in waiting.items():
        info = cast(dict[str, JSON], entry)
        options = cast(dict[str, JSON], info.get("options") or {})
        listed = " · ".join(f"{k} ({option_label(k, str(v))})" for k, v in options.items())
        lines.append(f"- #{key} {info.get('rule')}: {listed}")
    return Out(data={"pending": waiting}, md="\n".join(lines))
