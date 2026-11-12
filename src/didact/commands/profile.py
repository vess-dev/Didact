"""Session zero and the campaign profile."""

from typing import Annotated

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core.context import Context
from didact.core.errors import InvalidError
from didact.core.i18n import N_, _
from didact.core.output import JSON, Out


@command(
    "session zero",
    summary="The session-zero questions to ask the player, with the answers so far",
    examples=("didact session zero",),
    description=(
        "Ask the player each question (the system pack's own come first), then save the\n"
        "answers: `didact campaign profile role=gm tone='grim but hopeful' lines+=spiders`.\n"
        "Every brief carries the profile afterwards."
    ),
)
def session_zero(ctx: Context) -> Out:
    from didact.services import profile

    repo = open_repo(ctx)
    campaign = repo.active_campaign()
    if campaign is None:
        raise InvalidError(
            _("session zero is for a campaign"), hint=_("`didact campaign new <id>`")
        )
    from didact.services import options

    saved = profile.load(campaign)
    declared = {o.id: o for o in options.declared(repo)}
    values = options.resolved(repo, saved)
    lines = [
        _(
            "Session zero for {name}: ask, then save with `didact campaign profile`",
            name=campaign.name,
        )
    ]
    items: list[JSON] = []
    for question in profile.questions(repo):
        answer = profile.get(saved, question.key)
        shown = (
            ", ".join(str(a) for a in answer)
            if isinstance(answer, list)
            else options.shown(answer)
            if answer is not None
            else None
        )
        choices = f" ({' / '.join(question.choices)})" if question.choices else ""
        lines.append(
            f"- {question.key}: {question.asked}{choices}" + (f" → {shown}" if shown else "")
        )
        item: dict[str, JSON] = {"key": question.key, "ask": question.ask, "answer": answer}
        found = declared.get(question.key)
        if found is not None:  # one of the system's options: what the rules read, and why
            others = {k: v for k, v in saved.items() if k != found.id}
            unset = options.resolved(repo, others)
            setter = options.implied_by(repo, others).get(found.id)
            item |= {
                "option": True,
                "title": found.title,
                "choices": list[JSON](question.choices),
                "value": values.get(found.id),
                "unset": unset.get(found.id),
                "default": found.default,
                "implied_by": {"option": setter[0].id, "title": setter[0].title, "value": setter[1]}
                if setter is not None and unset.get(found.id) != found.default
                else None,
                "meanings": {c: found.meaning(found.parse(c)) for c in question.choices},
                "help": found.help,
                "source": found.source,
            }
        items.append(item)
    return Out(data={"campaign": campaign.id, "questions": items}, md="\n".join(lines))


@command(
    "campaign profile",
    summary="Show or change the campaign profile (role, tone, lines, veils, dice, …)",
    writes=True,
    examples=(
        "didact campaign profile",
        "didact campaign profile role=co-gm dice=physical",
        "didact campaign profile 'lines+=harm to children' veils+=torture tone='grim, hopeful'",
    ),
)
def campaign_profile(
    ctx: Context,
    *changes: Annotated[str, "key=value, key+=item or key-=item", Metavar("key=value")],
) -> Out:
    from didact.services import profile
    from didact.store.repo import campaign_file_text

    repo = open_repo(ctx)
    campaign = repo.active_campaign()
    if campaign is None:
        raise InvalidError(_("no campaign is open"), hint=_("`didact campaign open <id>`"))
    saved = profile.load(campaign)
    if not changes:
        return Out(data={"profile": saved}, md=profile.line(saved))
    done = [profile.change(repo, saved, text) for text in changes]
    campaign.other["profile"] = saved
    cs = changeset(
        ctx,
        repo,
        N_("campaign {campaign} profile: {changes}"),
        campaign=campaign.id,
        changes=", ".join(changes),
    )
    path = repo.layout.campaign_file(campaign.world, campaign.id)
    cs.write(path, campaign_file_text(campaign, repo.read_text(path)))
    return finish(
        ctx, cs, done="; ".join(done), extra={"profile": saved}, notes=[profile.line(saved)]
    )
