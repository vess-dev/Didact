"""Rulings: record how an unclear rule was settled, and find it again."""

from typing import Annotated

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON, Out


@command(
    "ruling add",
    summary="Record how an unclear rule was settled (campaign, world or system scope)",
    writes=True,
    examples=(
        "didact ruling add 'Can you push a save twice?' 'No: one push per roll.' --rule scramble",
        "didact ruling add 'Do petty items stack?' 'Up to 3 per slot.' --scope system",
    ),
    description=(
        "Rulings show up in `rules lookup` for their topic and in the output of `do` for\n"
        "their rule, so the same question gets the same answer next time. Campaign scope\n"
        "is the default; `world` shares it with every campaign here, `system` with every game."
    ),
)
def ruling_add(
    ctx: Context,
    question: Annotated[str, "the question that came up", Metavar("question")],
    answer: Annotated[str, "how it was settled", Metavar("ruling")],
    *,
    rule: Annotated[str | None, "the rule it's about", Metavar("rule")] = None,
    scope: Annotated[str | None, "campaign (default), world, system", Metavar("scope")] = None,
    tag: Annotated[list[str] | None, "a tag"] = None,
    keys: Annotated[
        list[str] | None, "words that bring it up in lore scans (comma-separated)"
    ] = None,
) -> Out:
    from didact.services import lore, rulings

    repo = open_repo(ctx)
    where = rulings.scope_for(repo, scope)
    rule_id = None
    if rule:
        from didact.services import packs, rules

        rule_id = rules.find_rule(packs.active(repo), rule).id
    cs = changeset(ctx, repo, N_("ruling: {question}"), question=question)
    entity = rulings.add(
        cs, question, answer, scope=where, rule=rule_id, tags=tag, keys=lore.split_keys(keys)
    )
    extra: dict[str, JSON] = {"id": str(entity.id), "scope": str(where)}
    return finish(
        ctx, cs, done=_("{ruling} ({scope})", ruling=rulings.line(entity), scope=where), extra=extra
    )


@command(
    "ruling find",
    summary="Find rulings about a topic (or list them all)",
    examples=("didact ruling find push", "didact ruling find"),
)
def ruling_find(ctx: Context, *words: Annotated[str, "what it's about", Metavar("topic")]) -> Out:
    from didact.services import rulings

    repo = open_repo(ctx)
    if words:
        found = rulings.matching(repo, list(words))
    else:
        found = [
            repo.located(row).entity for row in repo.index().rows(repo.chain(), types=["ruling"])
        ]
    lines = [
        ngettext("{n} ruling:", "{n} rulings:", len(found)),
        *(f"- {rulings.line(e)}" for e in found),
    ]
    items: list[JSON] = [
        {"id": str(e.id), "question": e.fields.get("question"), "ruling": e.fields.get("ruling")}
        for e in found
    ]
    return Out(data={"rulings": items}, md="\n".join(lines))
