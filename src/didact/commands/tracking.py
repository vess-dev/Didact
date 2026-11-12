"""Time, trackers, reminders, quests and accomplishments."""

from typing import TYPE_CHECKING, Annotated, Literal

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core import labels
from didact.core.context import Context
from didact.core.errors import ConflictError, InvalidError, UsageError
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON, Out

if TYPE_CHECKING:
    from didact.services.clock import Calendar
    from didact.services.trackers import Reminder
    from didact.store.repo import Repo


@command("time show", summary="What time it is in the game", examples=("didact time show",))
def time_show(ctx: Context) -> Out:
    from didact.services import play, timeline

    repo = open_repo(ctx)
    seconds = play.load(repo).seconds
    cal = timeline.calendar(repo)
    units = dict(sorted(cal.units.items(), key=lambda unit: (unit[1], unit[0])))  # shortest first
    return Out(
        data={"seconds": seconds, "text": cal.describe(seconds), "units": dict[str, JSON](units)},
        md=_("it's {time}", time=cal.describe(seconds)),
    )


@command(
    "time advance",
    summary="Move game time forward: timers expire, reminders come due, time triggers run",
    writes=True,
    examples=(
        "didact time advance 1 watch",
        "didact time advance 3 turns",
        "didact time advance 2 days",
    ),
)
def time_advance(
    ctx: Context, *amount: Annotated[str, "how long, e.g. 1 watch", Metavar("amount")]
) -> Out:
    from didact.services import timeline

    repo = open_repo(ctx)
    cal = timeline.calendar(repo)
    seconds = cal.parse(" ".join(amount) or "1 turn")
    cs = changeset(ctx, repo, N_("time advances {amount}"), amount=" ".join(amount))
    done = timeline.advance(repo, cs, seconds, command=ctx.command_line)
    notes = [
        *(
            _("timer: {timer} ran out: {note}", timer=name, note=note)
            if note
            else _("timer: {timer} ran out", timer=name)
            for name, note in done.expired
        ),
        *(_("reminder: {reminder}", reminder=r) for r in done.reminders),
    ]
    notes += [_("holiday: {holiday}", holiday=h) for h in done.holidays]
    notes += [_("trigger {trigger}", trigger=t) for t in done.triggers]
    text = _(
        "time: {before} → {after}",
        before=cal.describe(done.before),
        after=cal.describe(done.after),
    )
    data: dict[str, JSON] = {
        "before": done.before,
        "after": done.after,
        "timers": list[JSON](done.timers),
    }
    data |= {"reminders": list[JSON](done.reminders), "triggers": list[JSON](done.triggers)}
    return finish(ctx, cs, done=text, extra=data, notes=notes)


@command(
    "time set",
    summary="Set the campaign's date, before its first session (then `time advance` moves it on)",
    writes=True,
    examples=("didact time set '14 March 1890'",),
    description=(
        "A date of the calendar in play, written as it writes dates (a weekday before it is left\n"
        "to the date), before the calendar's start or after it: today becomes that date, and the\n"
        "campaign's first day moves with it. Once a session has begun, the journal is dated by\n"
        "the clock, which only moves on."
    ),
)
def time_set(
    ctx: Context, *date: Annotated[str, "the date, as the calendar writes one", Metavar("date")]
) -> Out:
    from didact.services import play, timeline
    from didact.store.repo import campaign_file_text

    repo = open_repo(ctx)
    campaign = repo.active_campaign()
    if campaign is None:
        raise InvalidError(_("no campaign is open"), hint=_("`didact campaign open <id>`"))
    current = play.load(repo)
    if current.session:
        raise ConflictError(
            _("play has begun (session {n})", n=current.session),
            hint=_(
                "a campaign's date is set before its first session; "
                "`didact time advance <amount>` moves it on"
            ),
        )
    cal = timeline.calendar(repo)
    gone = current.seconds // cal.day_seconds  # time advanced already: now is that date
    text = " ".join(date)
    cal.start_at(*cal.read_date(text), gone=gone)
    campaign.other["start"] = cal.first_day()
    path = repo.layout.campaign_file(campaign.world, campaign.id)
    cs = changeset(ctx, repo, N_("time set to {date}"), date=text)
    cs.write(path, campaign_file_text(campaign, repo.read_text(path)))
    weekday = cal.weekday_note(text, gone)  # the date decides; a day of the week that isn't its
    return finish(
        ctx,
        cs,
        done=_("it's {time}", time=cal.describe(current.seconds)),
        notes=[weekday] if weekday else [],
    )


@command(
    "remind",
    summary="Set a reminder for a game time (once, or every so often); --list, --cancel",
    writes=True,
    examples=(
        "didact remind 'Eat a ration' --every '1 day'",
        "didact remind 'The ferry leaves' --in '2 watches'",
        "didact remind --list",
        "didact remind --cancel 2",
        "didact remind --cancel 'ferry'",
    ),
    description=(
        "Reminders come due as game time passes (`didact time advance`). --list numbers\n"
        "the pending ones, soonest first; --cancel drops one, by that number or by words\n"
        "from its text (the first that has them all)."
    ),
)
def remind(
    ctx: Context,
    *text: Annotated[str, "the reminder", Metavar("text")],
    in_: Annotated[
        str | None, "after how long (default: at the next --every)", Metavar("time")
    ] = None,
    every: Annotated[str | None, "repeat this often", Metavar("time")] = None,
    list_: Annotated[bool, "show the pending reminders, numbered, and when they're due"] = False,
    cancel: Annotated[
        str | None, "drop one: its number in --list, or words from its text", Metavar("which")
    ] = None,
) -> Out:
    from didact.services import play, timeline, trackers

    if list_ or cancel is not None:
        if text or in_ or every:
            raise UsageError(
                _("--list and --cancel take no reminder text, --in or --every"),
                hint=_("quote the words to cancel: `didact remind --cancel 'the ferry'`"),
            )
        if list_ and cancel is not None:
            raise UsageError(
                _("--list or --cancel, not both"), hint=_("`didact remind --list` first")
            )
    repo = open_repo(ctx)
    cal = timeline.calendar(repo)
    now = play.load(repo).seconds
    if list_:
        return _reminders(repo, cal, now)
    if cancel is not None:
        items = trackers.pending(repo)
        gone = trackers.find_reminder(items, cancel)
        cs = changeset(ctx, repo, N_("reminder cancelled: {text}"), text=gone.text)
        trackers.save_reminders(cs, [r for r in items if r is not gone])
        done = _(
            "cancelled the reminder for {time}: {text}", time=cal.describe(gone.at), text=gone.text
        )
        return finish(ctx, cs, done=done, extra={"cancelled": _reminder_data(gone)})
    period = cal.parse(every) if every else None
    delay = cal.parse(in_) if in_ else period
    if delay is None:
        raise InvalidError(
            _("when?"),
            hint=_("give --in '<time>' and/or --every '<time>' (`--list` shows the pending ones)"),
        )
    words = " ".join(text).strip()
    items = [*trackers.reminders(repo), trackers.Reminder(words, now + delay, period)]
    cs = changeset(ctx, repo, N_("remind: {text}"), text=words)
    trackers.save_reminders(cs, items)
    return finish(
        ctx,
        cs,
        done=_("reminder set for {time}: {text}", time=cal.describe(now + delay), text=words),
    )


def _reminder_data(reminder: Reminder) -> dict[str, JSON]:
    return {"text": reminder.text, "at": reminder.at, "every": reminder.every}


def _reminders(repo: Repo, cal: Calendar, now: int) -> Out:
    """The pending reminders, numbered for `remind --cancel <n>`."""
    from didact.services import trackers

    items = trackers.pending(repo)
    if not items:
        return Out(data={"now": now, "reminders": []}, md=_("no reminders are pending"))
    lines = [
        ngettext(
            "{n} reminder (it's {time}):",
            "{n} reminders (it's {time}):",
            len(items),
            time=cal.describe(now),
        )
    ]
    rows: list[JSON] = []
    for number, item in enumerate(items, 1):
        when = cal.describe(item.at)
        if item.every:
            period = trackers.period(item.every, cal.units)
            line = _(
                "{number}. {text} · {time} · every {period}",
                number=number,
                text=item.text,
                time=when,
                period=period,
            )
        else:
            line = _("{number}. {text} · {time}", number=number, text=item.text, time=when)
        lines.append(line)
        rows.append({"n": number, **_reminder_data(item), "when": cal.describe(item.at)})
    return Out(data={"now": now, "reminders": rows}, md="\n".join(lines))


@command(
    "track new",
    summary="Make a tracker: clock, track, counter, resource, uses or timer",
    writes=True,
    examples=(
        "didact track new 'Spider infestation' --kind clock --size 6",
        "didact track new 'Torch' --kind timer --lasts '6 turns' --note 'the torch gutters out'",
        "didact track new 'Doom' --kind counter",
        "didact track new 'The Order seizes the ford' --size 6 --for faction:the-order",
        "didact track new 'Poisoned' --kind pool --size 4 --note 'harm'   # a diminishing pool",
        "didact track new 'Troll' --kind pool --linked 4+4 --pool task",
    ),
)
def track_new(
    ctx: Context,
    name: Annotated[str, "its name", Metavar("name")],
    *,
    kind: Annotated[
        Literal["clock", "track", "counter", "resource", "uses", "timer", "pool"],
        "what it counts",
    ] = "clock",
    size: Annotated[int | None, "segments or boxes (clock, track)", Metavar("n")] = None,
    max_: Annotated[int | None, "a ceiling (counter, resource, uses)", Metavar("n")] = None,
    start: Annotated[int, "the starting value"] = 0,
    lasts: Annotated[str | None, "how long a timer runs, e.g. '6 turns'", Metavar("time")] = None,
    note: Annotated[str, "what it means when it fills or runs out", Metavar("text")] = "",
    for_: Annotated[
        str | None, "whose it is: a faction's plan, a PC's doom", Metavar("record")
    ] = None,
    pool: Annotated[
        Literal["task", "pressure", "timer", "resource", "power", "campaign"] | None,
        "a pool's type (default task)",
    ] = None,
    linked: Annotated[
        str | None, "a linked pool's phases, e.g. 4+4 or 8+4", Metavar("sizes")
    ] = None,
) -> Out:
    from didact.services import play, timeline, trackers

    repo = open_repo(ctx)
    phases = None
    if linked:
        try:
            phases = [int(part.strip().removesuffix("d")) for part in linked.split("+")]
        except ValueError as exc:
            raise UsageError(
                _("can't read {value}", value=repr(linked)), hint=_("e.g. --linked 4+4")
            ) from exc
    expires = None
    if lasts:
        expires = play.load(repo).seconds + timeline.calendar(repo).parse(lasts)
    owner = str(repo.resolve(for_).entity.id) if for_ else None
    cs = changeset(ctx, repo, N_("track {name}"), name=name)
    entity = trackers.new_track(
        cs,
        name,
        kind,
        size=size,
        maximum=max_,
        start=start,
        expires=expires,
        note=note,
        owner=owner,
        pool=pool,
        phases=phases,
    )
    shown = trackers.show(entity, play.load(repo).seconds)
    return finish(ctx, cs, done=_("tracking {tracker} ({id})", tracker=shown, id=entity.id))


@command(
    "track roll",
    summary="Roll a diminishing pool: dice showing 1-3 drop; at 0d its event happens",
    writes=True,
    examples=(
        "didact track roll poisoned",
        "didact track roll troll --drop 1        # greater effect or potency: drop 1d first",
        "didact track roll blasting-wand --extra 1   # a power pool with spark",
    ),
    description=(
        "Rolls every die in the pool and drops each 1-3. A linked pool moves to its next phase\n"
        "when one empties; the last one empty means its event happens. The highest die is\n"
        "the result when a power pool stands in for an action roll."
    ),
)
def track_roll(
    ctx: Context,
    ref: Annotated[str, "the pool", Metavar("pool")],
    *,
    drop: Annotated[int, "dice to drop before rolling", Metavar("n")] = 0,
    extra: Annotated[int, "extra dice that roll along but never drop", Metavar("n")] = 0,
) -> Out:
    from didact.services import trackers

    repo = open_repo(ctx)
    cs = changeset(ctx, repo, N_("roll pool {pool}"), pool=ref)
    rolled = trackers.roll_pool(
        cs,
        repo.resolve(ref, of="track"),  # a name a foe shares is its pool here
        drop=drop,
        extra=extra,
        command=ctx.command_line,
        dry=ctx.dry_run,
    )
    if rolled.highest is not None:
        result = _(
            "{pool}: {dropped} dropped, {left}d left (highest {highest})",
            pool=rolled.entity.name,
            dropped=rolled.dropped,
            left=rolled.left,
            highest=rolled.highest,
        )
    else:
        result = _(
            "{pool}: {dropped} dropped, {left}d left",
            pool=rolled.entity.name,
            dropped=rolled.dropped,
            left=rolled.left,
        )
    data: dict[str, JSON] = {
        "pool": str(rolled.entity.id),
        "faces": list[JSON](rolled.faces),
        "extra": list[JSON](rolled.extra),
        "dropped": rolled.dropped,
        "left": rolled.left,
        "highest": rolled.highest,
        "empty": rolled.empty,
    }
    if cs.is_empty():  # nothing dropped: the roll still counts (it's logged)
        return Out(
            data=data, md="\n".join([*rolled.lines, _("{result}: nothing dropped", result=result)])
        )
    return finish(ctx, cs, done=result, extra=data, notes=rolled.lines)


@command(
    "track tick",
    summary="Advance a tracker (or `--by -1` to take it back)",
    writes=True,
    examples=("didact track tick spider-infestation", "didact track tick doom --by 2"),
)
def track_tick(
    ctx: Context,
    ref: Annotated[str, "the tracker", Metavar("track")],
    *,
    by: Annotated[int, "how much"] = 1,
) -> Out:
    from didact.services import trackers

    repo = open_repo(ctx)
    cs = changeset(ctx, repo, N_("tick {track}"), track=ref)
    entity, note = trackers.tick(cs, ref, "+=" if by >= 0 else "-=", abs(by))
    notes = [note] if note else []
    return finish(ctx, cs, done=trackers.show(entity), notes=notes)


@command(
    "track list",
    summary="The trackers in play",
    examples=("didact track list", "didact track list --gm"),
)
def track_list(ctx: Context, *, gm: Annotated[bool, "include secret ones"] = False) -> Out:
    from didact.services import play, trackers

    repo = open_repo(ctx)
    now = play.load(repo).seconds if repo.active_campaign() else 0
    found = trackers.active(repo, ("track",), gm=gm)
    if not found:
        return Out(data={"tracks": []}, md=_("no trackers"))
    lines = [f"- {trackers.show(e, now)} ({e.id})" for e in found]
    data: list[JSON] = [
        {
            "id": str(e.id),
            "name": e.name,
            "kind": str(e.fields.get("kind", "counter")),
            "text": trackers.show(e, now),
            "value": e.fields.get("value"),
        }
        for e in found
    ]
    return Out(data={"tracks": data}, md="\n".join(lines))


@command(
    "quest new",
    summary="Start a quest, thread or task (with milestones)",
    writes=True,
    examples=(
        "didact quest new 'Purify the forest' --goal 'Free the spirit' --milestone 'Find it'",
        "didact quest new 'Find the hut' --type thread",
    ),
)
def quest_new(
    ctx: Context,
    name: Annotated[str, "its name", Metavar("name")],
    *,
    type_: Annotated[Literal["quest", "thread", "task"], "which kind"] = "quest",
    goal: Annotated[str, "what finishing it means", Metavar("text")] = "",
    milestone: Annotated[
        list[str] | None, "a step on the way (repeatable)", Metavar("text")
    ] = None,
) -> Out:
    from didact.services import trackers

    repo = open_repo(ctx)
    cs = changeset(ctx, repo, N_("{type} {name}"), type=type_, name=name)
    entity = trackers.new_quest(cs, type_, name, goal, milestone or [])
    return finish(
        ctx,
        cs,
        done=_("{kind} {id}: {quest}", kind=type_, id=entity.id, quest=trackers.quest_line(entity)),
    )


@command(
    "quest done",
    summary="Finish a quest (or one milestone with --milestone)",
    writes=True,
    examples=(
        "didact quest done purify-the-forest",
        "didact quest done purify-the-forest --milestone 1",
    ),
)
def quest_done(
    ctx: Context,
    ref: Annotated[str, "the quest, thread or task", Metavar("quest")],
    *,
    milestone: Annotated[str | None, "a milestone's number or text", Metavar("milestone")] = None,
    status: Annotated[Literal["done", "failed", "abandoned"], "how it ended"] = "done",
) -> Out:
    from didact.services import trackers

    repo = open_repo(ctx)
    cs = (
        changeset(ctx, repo, N_("{quest}: milestone"), quest=ref)
        if milestone
        else changeset(ctx, repo, N_("{quest}: {status}"), quest=ref, status=status)
    )
    entity = trackers.progress(cs, ref, milestone=milestone, status=None if milestone else status)
    line = trackers.quest_line(entity)
    if milestone:
        done = _(
            "{id} milestone {milestone}: {quest}", id=entity.id, milestone=milestone, quest=line
        )
    else:
        done = _("{id} {status}: {quest}", id=entity.id, status=status, quest=line)
    return finish(ctx, cs, done=done)


@command("quest list", summary="Open quests, threads and tasks", examples=("didact quest list",))
def quest_list(ctx: Context, *, gm: Annotated[bool, "include secret ones"] = False) -> Out:
    from didact.services import trackers

    repo = open_repo(ctx)
    found = trackers.active(repo, trackers.QUEST_TYPES, gm=gm)
    if not found:
        return Out(data={"quests": []}, md=_("no open quests, threads or tasks"))
    lines = [ngettext("{n} open item:", "{n} open items:", len(found))] + [
        f"- {labels.type_inline(e.type)} {trackers.quest_line(e)} ({e.id})" for e in found
    ]
    data: list[JSON] = [
        {
            "id": str(e.id),
            "name": e.name,
            "type": e.type,
            "line": trackers.quest_line(e),
        }
        for e in found
    ]
    return Out(data={"quests": data}, md="\n".join(lines))


@command(
    "accomplish",
    summary="Record an accomplishment (growth, XP, a milestone for advancement)",
    writes=True,
    examples=("didact accomplish 'Freed the spirit of the Wood' --pc freya --xp 1",),
)
def accomplish(
    ctx: Context,
    *text: Annotated[str, "what was accomplished", Metavar("text")],
    pc: Annotated[str | None, "who did it", Metavar("pc")] = None,
    xp: Annotated[int | None, "experience earned", Metavar("n")] = None,
) -> Out:
    from didact.core.clock import now_iso
    from didact.services import play, records

    repo = open_repo(ctx)
    words = " ".join(text).strip()
    if not words:
        raise InvalidError(
            _("what was accomplished?"),
            hint=_("e.g. `didact accomplish 'Freed the spirit' --pc freya`"),
        )
    fields: dict[str, JSON] = {"session": play.load(repo).session, "when": now_iso()}
    if xp is not None:
        fields["xp"] = xp
    entity = records.build_entity(
        records.new_id("accomplishment", words[:48]), words, {"fields": fields}
    )
    if pc:
        who = repo.resolve(pc).entity
        records.add_link(entity, "by", str(who.id))
    cs = changeset(ctx, repo, N_("accomplishment: {text}"), text=words)
    records.create(cs, repo.default_scope("pc"), entity)
    return finish(ctx, cs, done=_("accomplished: {text}", text=words))


@command(
    "faction turn",
    summary="The factions act: each rolls (or runs the pack's rule) and advances its clocks",
    writes=True,
    examples=("didact faction turn", "didact faction turn --gm"),
    description=(
        "Every faction that isn't gone takes a turn: the system's `settings.factions.turn`\n"
        "rule, or a roll (d6; 4+ ticks each of its clocks: `track new … --for faction:x`).\n"
        "Narrate the moves from their agendas. Secret factions act too; `--gm` shows them."
    ),
)
def faction_turn(
    ctx: Context, *, gm: Annotated[bool, "show secret factions' moves"] = False
) -> Out:
    from didact.services import factions

    repo = open_repo(ctx)
    every, _unused = factions.active(repo, gm=True)
    if not every:
        return Out(data={"moves": []}, md=_("no factions yet: `didact new faction <name>`"))
    cs = changeset(ctx, repo, N_("faction turn"))
    moves = factions.turn(repo, cs, every, dry=ctx.dry_run, command=ctx.command_line)
    lines: list[str] = []
    hidden = 0
    items: list[JSON] = []
    for move in moves:
        if move.faction.knowledge == "secret" and not gm:
            hidden += 1
            continue
        lines.append(f"## {move.faction.name} [{move.faction.id}]")
        lines += move.lines
        lines.append(factions.prompt(move))
        lines += [_("filled: {name}: it happens now", name=name) for name in move.filled]
        items.append(
            {
                "id": str(move.faction.id),
                "advanced": move.advanced,
                "filled": list[JSON](move.filled),
                "lines": list[JSON](move.lines),
            }
        )
    if hidden:
        lines.append(
            ngettext(
                "({n} secret faction acted; `--gm` shows them)",
                "({n} secret factions acted; `--gm` shows them)",
                hidden,
            )
        )
    data: dict[str, JSON] = {"moves": items, "hidden": hidden}
    if cs.is_empty():
        return Out(data=data, md="\n".join(lines))
    out = finish(ctx, cs, done=_("the factions moved"), extra=data)
    return Out(data=out.data, md="\n".join([*lines, out.md]), ok=out.ok)
