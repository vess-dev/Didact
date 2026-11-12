"""Play: sessions, scenes, the journal, transcripts, summaries and the brief."""

import sys
from typing import TYPE_CHECKING, Annotated, Literal

from didact.commands._common import changeset, finish, open_repo
from didact.commands.registry import Metavar, command
from didact.core import labels
from didact.core.context import Context
from didact.core.errors import DidactError, InvalidError
from didact.core.i18n import N_, _, ngettext
from didact.core.output import JSON, Out, code
from didact.core.phrases import english, phrase
from didact.store.changeset import Changeset
from didact.store.repo import Repo

if TYPE_CHECKING:
    from didact.expr.model import Value
    from didact.services.play import PlayState


def _said_beat(cs: Changeset, said: str, secret: str, beat: dict[str, JSON]) -> None:
    """A journal change's summary: the beat's line, cut to 120 characters in all. History is
    seen by everyone, so a secret beat's summary says only that it is one."""
    from didact.services import play

    number = str(beat["id"])
    if beat.get("secret"):
        cs.say(secret, beat=number)
        return
    room = 120 - len(english(phrase(said, beat=number, line="")))
    cs.say(said, beat=number, line=play.beat_line(beat)[: max(room, 0)])


def _fire(
    ctx: Context, cs: Changeset, current: PlayState, event: str, *, scene: int | None = None
) -> list[str]:
    """Run the packs' `on: <event>` triggers inside this changeset; notes for the output."""
    from didact.services import events

    preset: dict[str, Value] = {"session": current.session, "scene": scene or current.scene}
    ran = events.fire(cs.repo, cs, event, preset, dry=ctx.dry_run, command=ctx.command_line)
    return [_("trigger {trigger}", trigger=line) for line in ran]


@command(
    "brief",
    summary="Where the game stands: session, scene, party, what's due, the story so far",
    examples=("didact brief", "didact brief --gm"),
)
def brief(ctx: Context, *, gm: Annotated[bool, "include secrets (GM eyes only)"] = False) -> Out:
    from didact.services import brief as briefing

    found = briefing.build(open_repo(ctx), gm=gm)
    return Out(data=found.data, md="\n".join(found.lines))


@command(
    "session start",
    summary="Start the next session (and show the brief)",
    writes=True,
    examples=("didact session start", "didact session start 'Into the Wood'"),
)
def session_start(
    ctx: Context, title: Annotated[str | None, "a title", Metavar("title")] = None
) -> Out:
    from didact.services import brief as briefing
    from didact.services import play

    repo = open_repo(ctx)
    current = play.load(repo)
    cs = changeset(ctx, repo, N_("start session {number}"), number=current.session + 1)
    number = play.start_session(cs, current, title)
    notes = _fire(ctx, cs, current, "session_start")
    done = _("session {number} started", number=number)
    out = finish(ctx, cs, done=done, extra={"session": number}, notes=notes)
    lines = [out.md]
    if not ctx.dry_run:
        lines += ["", *briefing.build(repo, gm=False).lines]
    return Out(data=out.data, md="\n".join(lines), ok=out.ok)


@command(
    "session end",
    summary="End the session (give its summary now, or later with `summary write session`)",
    writes=True,
    examples=(
        "didact session end --summary 'Freya found the grave and bargained with the spirit.'",
    ),
)
def session_end(
    ctx: Context, *, summary: Annotated[str | None, "the session's summary", Metavar("text")] = None
) -> Out:
    from didact.services import play

    repo = open_repo(ctx)
    current = play.load(repo)
    cs = changeset(ctx, repo, N_("end session {number}"), number=current.session)
    scene_was_open = current.scene_open
    number = play.end_session(cs, current, summary)
    notes = _fire(ctx, cs, current, "scene_end") if scene_was_open else []
    notes += _fire(ctx, cs, current, "session_end")
    if not summary:
        notes.append(_("summary due: `didact summary write session:{number} '…'`", number=number))
    done = _("session {number} ended", number=number)
    out = finish(ctx, cs, done=done, extra={"session": number}, notes=notes)
    if "event" not in out.data:  # a dry run: nothing ended, nothing to back up
        return out
    from didact.services import care

    backup = care.auto_backup(repo)  # never raises: the session has ended either way
    data: dict[str, JSON] = {**out.data, "backup": backup.to_data()}
    return Out(data=data, md="\n".join([out.md, _("note: {note}", note=backup.note)]), ok=out.ok)


@command(
    "scene new",
    summary="Start the next scene (closing the current one)",
    writes=True,
    examples=("didact scene new 'Amber Grave' --expected 'a quiet pool of sap'",),
)
def scene_new(
    ctx: Context,
    title: Annotated[str | None, "a title", Metavar("title")] = None,
    *,
    expected: Annotated[str | None, "what the scene is expected to be", Metavar("text")] = None,
) -> Out:
    from didact.services import play

    repo = open_repo(ctx)
    current = play.load(repo)
    cs = changeset(ctx, repo, N_("scene {number}"), number=current.scene + 1)
    previous = current.scene if current.scene_open else None
    number = play.new_scene(cs, current, title, expected)
    notes = _fire(ctx, cs, current, "scene_end", scene=previous) if previous else []
    notes += _fire(ctx, cs, current, "scene_start")
    notes += _lore_push(repo, cs, " ".join(t for t in (title, expected) if t))
    done = _("scene {number} started", number=number)
    return finish(ctx, cs, done=done, extra={"scene": number}, notes=notes)


@command(
    "scene end",
    summary="End the current scene (optionally with its summary)",
    writes=True,
    examples=("didact scene end --summary 'The spirit agreed to help if freed.'",),
)
def scene_end(
    ctx: Context, *, summary: Annotated[str | None, "the scene's summary", Metavar("text")] = None
) -> Out:
    from didact.services import play

    repo = open_repo(ctx)
    current = play.load(repo)
    cs = changeset(ctx, repo, N_("end scene {number}"), number=current.scene)
    number = play.end_scene(cs, current, summary)
    notes = _fire(ctx, cs, current, "scene_end")
    done = _("scene {number} ended", number=number)
    return finish(ctx, cs, done=done, extra={"scene": number}, notes=notes)


@command(
    "log",
    summary="Add a beat to the session journal (action, oracle, roll, result, narration, …)",
    writes=True,
    examples=(
        "didact log action 'Freya wades into the sap pool'",
        "didact log result 'The spirit wakes' --roll r12",
        "didact log narration 'Amber light, the smell of resin.' --importance 6",
        "didact log consequence 'Sweeney sold the route' --about sweeney --about freya",
        "didact log note 'Scouts find the camp' --about bone-queen --secret",
    ),
    description=(
        "Kinds and their marks: action @, oracle ?, roll d:, result ->, consequence =>,\n"
        "narration, dialogue, note, ooc. Log beats, not prose dumps: one line per thing\n"
        "that happened. Rolls are in the log already; link them with --roll.\n"
        "--about names the records a beat concerns: it joins each one's chronicle (`show`,\n"
        "`about`), so what someone did, or what happened to a thing, stays on record.\n"
        "--secret: it happened out of the players' sight (GM views only)."
    ),
)
def log(
    ctx: Context,
    kind: Annotated[
        Literal[
            "action",
            "oracle",
            "roll",
            "result",
            "consequence",
            "narration",
            "dialogue",
            "note",
            "ooc",
        ],
        "the beat's kind",
    ],
    *text: Annotated[str, "what happened", Metavar("text")],
    importance: Annotated[int | None, "1–10: how much it matters later", Metavar("n")] = None,
    roll: Annotated[list[str] | None, "a roll it refers to, e.g. r12", Metavar("roll")] = None,
    about: Annotated[
        list[str] | None, "a record it concerns (repeatable): its chronicle", Metavar("record")
    ] = None,
    secret: Annotated[bool, "out of the players' sight: GM views only"] = False,
) -> Out:
    from didact.services import play

    repo = open_repo(ctx)
    current = play.load(repo)
    refs = [str(repo.resolve(r).entity.id) for r in about or []]
    cs = changeset(ctx, repo, N_("log {kind}"), kind=kind)
    beat = play.add_beat(
        cs, current, kind, " ".join(text), importance=importance, rolls=roll, about=refs,
        secret=secret,
    )  # fmt: skip
    _said_beat(cs, N_("log {beat}: {line}"), N_("log {beat}: (a secret beat)"), beat)
    notes = _lore_push(repo, cs, " ".join(text))
    done = _("{beat} {line}", beat=beat["id"], line=play.beat_line(beat))
    return finish(ctx, cs, done=done, extra={"beat": beat}, notes=notes)


@command(
    "beat edit",
    summary="Correct a journal beat: its text, kind, importance, who it's about, or secrecy",
    writes=True,
    examples=(
        "didact beat edit S1.4 --about sweeney",
        "didact beat edit S1.4 --not-about freya --secret",
        "didact beat edit S2.7 --text 'Sweeney sold the route to the raiders' --importance 8",
    ),
    description=(
        "Beat ids are in `session show` (S<session>.<n>). --about adds a record to the beat,\n"
        "so it shows in that record's chronicle; --not-about takes one off. --secret keeps it\n"
        "out of the players' views; --public shows it again. Undoable like any change."
    ),
)
def beat_edit(
    ctx: Context,
    beat_id: Annotated[str, "the beat, e.g. S1.4", Metavar("beat")],
    *,
    text: Annotated[str | None, "its new text", Metavar("text")] = None,
    kind: Annotated[
        Literal[
            "action",
            "oracle",
            "roll",
            "result",
            "consequence",
            "narration",
            "dialogue",
            "note",
            "ooc",
        ]
        | None,
        "its new kind",
    ] = None,
    importance: Annotated[int | None, "1–10: how much it matters later", Metavar("n")] = None,
    about: Annotated[list[str] | None, "add a record it concerns", Metavar("record")] = None,
    not_about: Annotated[list[str] | None, "take a record off it", Metavar("record")] = None,
    secret: Annotated[bool, "out of the players' sight"] = False,
    public: Annotated[bool, "the players see it again"] = False,
) -> Out:
    from didact.services import play

    if secret and public:
        raise InvalidError(
            _("--secret or --public, not both"),
            hint=_("--secret hides it from the players, --public shows it"),
        )
    repo = open_repo(ctx)
    added = [str(repo.resolve(r).entity.id) for r in about or []]
    dropped = [_ref_id(repo, r) for r in not_about or []]
    cs = changeset(ctx, repo, N_("edit beat {beat}"), beat=beat_id.upper())
    beat = play.edit_beat(
        cs, beat_id, text=text, kind=kind, importance=importance, about=added,
        not_about=dropped, secret=True if secret else (False if public else None),
    )  # fmt: skip
    _said_beat(cs, N_("edit beat {beat}: {line}"), N_("edit beat {beat}: (a secret beat)"), beat)
    done = _("{beat} {line}", beat=beat["id"], line=play.beat_line(beat))
    return finish(ctx, cs, done=done, extra={"beat": beat})


@command(
    "beat rm",
    summary="Remove a journal beat (undoable)",
    writes=True,
    examples=("didact beat rm S1.4",),
)
def beat_rm(ctx: Context, beat_id: Annotated[str, "the beat, e.g. S1.4", Metavar("beat")]) -> Out:
    from didact.services import play

    repo = open_repo(ctx)
    cs = changeset(ctx, repo, N_("remove beat {beat}"), beat=beat_id.upper())
    beat = play.remove_beat(cs, beat_id)
    return finish(ctx, cs, done=_("removed beat {beat}", beat=beat["id"]), extra={"beat": beat})


def _ref_id(repo: Repo, ref: str) -> str:
    """A record's id, or the text as given when the record is gone (a beat can still name it)."""
    try:
        return str(repo.resolve(ref).entity.id)
    except DidactError:
        return ref


@command(
    "capture",
    summary="Record a transcript turn (for hooks: reads Claude Code hook JSON on stdin)",
    examples=(
        'echo \'{"prompt": "I open the door"}\' | didact capture',
        "didact capture --role gm --text 'The door creaks open.'",
        "didact capture --hook          # in a Claude Code hook: silent",
    ),
    description=(
        "Appends one turn to the open session's transcript. Claude Code hooks pipe their JSON:\n"
        "UserPromptSubmit (`prompt`) records the player, Stop (`last_assistant_message`) the GM.\n"
        "The first captured turn after `session start` binds the transcript to that Claude\n"
        "session; turns from other sessions are ignored. With no open session it does nothing."
    ),
)
def capture(
    ctx: Context,
    *,
    role: Annotated[
        Literal["player", "gm"] | None, "who spoke (default: from the hook, or player)"
    ] = None,
    text: Annotated[str | None, "the text (default: stdin)", Metavar("text")] = None,
    hook: Annotated[bool, "print nothing (a hook's output would land in Claude's context)"] = False,
) -> Out:
    from didact.services import play, turns

    repo = open_repo(ctx)
    raw = text if text is not None else (sys.stdin.read() if not sys.stdin.isatty() else "")
    found = play.capture_text(raw, role)

    def skip(why: str, shown: str) -> Out:
        """`why` is data (English); `shown` is the same, for people."""
        context = _lore_context(repo, found, hook, None) if found is not None else ""
        return Out(data={"captured": False, "why": why}, md=context if hook else shown)

    if not repo.initialized() or repo.active_campaign() is None or found is None:
        return skip("nothing captured", _("nothing captured"))
    current = play.load(repo)
    who, words, claude_session = found
    if not current.session_open:
        return skip("no open session: nothing captured", _("no open session: nothing captured"))
    if claude_session and current.bound and claude_session != current.bound:
        return skip(
            "another Claude session is bound: nothing captured",
            _("another Claude session is bound: nothing captured"),
        )
    cs = changeset(ctx, repo, N_("transcript: {who}"), who=who)
    cs.turn = None  # the transcript is history: taking back a turn keeps it
    if claude_session and not current.bound:
        current.bound = claude_session
        play.save(cs, current)
    play.add_turn(cs, current, who, words)
    extra: dict[str, JSON] = {"captured": True}
    context = ""
    if who == "player":  # each player message starts a turn group (`undo --turn`)
        turn = turns.begin(cs, words.strip().splitlines()[0][:80] if words.strip() else None)
        extra["turn"] = turn
        context = _lore_context(repo, found, hook, (cs, int(turn[1:])))
    out = finish(ctx, cs, done=_("captured a {role} turn", role=who), extra=extra)
    return Out(data=out.data, md=context if hook else "\n".join(p for p in (out.md, context) if p))


def _lore_context(
    repo: Repo,
    found: tuple[str, str, str | None],
    hook: bool,
    recording: tuple[Changeset, int] | None,
) -> str:
    """What the player's message brings up, for the GM (the hook adds it to Claude's context).

    Entries shown in the last few turns aren't repeated; with `recording`, what fires is
    remembered in the capture's changeset.
    """
    from didact.services import lore

    who, words, _unused = found
    if who != "player" or repo.active_world() is None:
        return ""
    now = lore.clock(repo)
    if recording is not None:
        now.turn = recording[1]
    result = lore.scan(repo, words, gm=True, now=now, dedupe=True)
    result.hits = [h for h in result.hits if h.reason != "constant"]  # the brief has those
    if recording is not None:
        lore.record(recording[0], now, result.hits)
    if not result.hits:
        return ""
    head = (
        _("Didact lore for this message (GM only lines: don't read them out):")
        if hook
        else _("lore:")
    )
    return "\n".join([head, *result.lines()])


def _lore_push(repo: Repo, cs: Changeset, text: str) -> list[str]:
    """Lore a write brings up, player-safe and not repeated for a few turns: output notes."""
    from didact.services import lore

    if repo.active_world() is None or not text.strip():
        return []
    now = lore.clock(repo)
    result = lore.scan(repo, text, gm=False, now=now, dedupe=True, budget=300)
    hits = [h for h in result.hits if h.reason != "constant"]
    lore.record(cs, now, hits)
    notes = [_("lore: {entry}", entry=h.line()) for h in hits]
    if result.omitted:
        notes.append(_("lore: {count} more (`didact lore scan …`)", count=len(result.omitted)))
    return notes


@command(
    "turn begin",
    summary="Start a turn group: what follows, until the next turn, undoes together",
    writes=True,
    examples=("didact turn begin 'I open the door'",),
    description=(
        "The Claude Code hook does this for you (`didact capture` on each player message).\n"
        "Other clients call it when the player speaks; `didact undo --turn` takes the whole\n"
        "turn back: its changes, journal beats and rolls. The transcript keeps it."
    ),
)
def turn_begin(
    ctx: Context, *label: Annotated[str, "what the player said or did", Metavar("text")]
) -> Out:
    from didact.services import turns

    repo = open_repo(ctx)
    cs = changeset(ctx, repo, N_("turn begins"))
    started = turns.begin(cs, " ".join(label) or None)
    return finish(ctx, cs, done=_("turn {turn} begins", turn=started), extra={"turn": started})


@command(
    "turn end",
    summary="Close the open turn group (later changes belong to no turn)",
    writes=True,
    examples=("didact turn end",),
)
def turn_end(ctx: Context) -> Out:
    from didact.services import turns

    repo = open_repo(ctx)
    cs = changeset(ctx, repo, N_("turn ends"))
    ended = turns.end(cs)
    if ended is None:
        return Out(data={"turn": None}, md=_("no turn is open"))
    return finish(ctx, cs, done=_("turn {turn} ends", turn=ended), extra={"turn": ended})


@command(
    "transcript",
    summary="Show a session's full transcript (or clear it with --clear)",
    writes=True,
    examples=("didact transcript", "didact transcript 3", "didact transcript 3 --clear"),
    description=(
        "The transcript is every player and GM turn, verbatim, captured by the hooks.\n"
        "--clear deletes one session's (or every session's with --all), as one change that\n"
        "`didact undo` can take back. The text stays in the history until `history --clear`."
    ),
)
def transcript(
    ctx: Context,
    session: Annotated[int | None, "the session (default: current)", Metavar("n")] = None,
    *,
    clear: Annotated[bool, "delete the transcript"] = False,
    all_: Annotated[bool, "with --clear: every session's"] = False,
) -> Out:
    from didact.services import play

    repo = open_repo(ctx)
    if clear:
        current = play.load(repo).session
        numbers = list(range(1, current + 1)) if all_ else [session or current]
        cs = (
            changeset(ctx, repo, N_("clear transcripts"))
            if all_
            else changeset(ctx, repo, N_("clear transcript {number}"), number=numbers[0])
        )
        for number in numbers:
            cs.delete(play.transcript_path(repo, number))
        if cs.is_empty():
            return Out(data={"cleared": 0}, md=_("no transcript to clear"))
        done = ngettext("cleared {n} transcript", "cleared {n} transcripts", len(cs.files))
        return finish(ctx, cs, done=done, extra={"cleared": len(cs.files)})
    number = session or play.load(repo).session
    text = repo.read_text(play.transcript_path(repo, number)) if number else None
    if not text:
        return Out(
            data={"session": number, "text": ""},
            md=_("no transcript for session {number}", number=number),
        )
    return Out(data={"session": number, "text": text}, md=text.rstrip())


@command(
    "session show",
    summary="A session as a readable log: scenes, beats and rolls in order, with summaries",
    examples=("didact session show", "didact session show 3 --detail full"),
)
def session_show(
    ctx: Context,
    number: Annotated[int | None, "the session (default: current)", Metavar("n")] = None,
    *,
    gm: Annotated[bool, "include secret beats (out of the players' sight)"] = False,
) -> Out:
    from didact.services import play, sessionview

    repo = open_repo(ctx)
    wanted = number or play.load(repo).session
    if not wanted:
        raise InvalidError(_("no sessions yet"), hint=_("`didact session start`"))
    lines, data = sessionview.render(repo, wanted, full=ctx.detail == "full", gm=gm)
    return Out(data=data, md="\n".join(lines))


@command(
    "session list",
    summary="List the campaign's sessions",
    examples=("didact session list", "didact session list --gm"),
)
def session_list(
    ctx: Context, *, gm: Annotated[bool, "secret titles and summary sections too"] = False
) -> Out:
    from didact.services import play

    repo = open_repo(ctx)
    current = play.load(repo)
    rows: list[JSON] = []
    lines: list[str] = []
    for number in range(1, current.session + 1):
        record = play.session_record(repo, number)
        if record is None:
            continue
        status = str(record.fields.get("status", ""))
        summary = play.summary_of(record.body, gm=gm)
        name = play.title_of(record, f"Session {number}", gm=gm)
        if summary:
            line = _(
                "- session {number} · {name} ({status}): {summary}",
                number=number,
                name=name,
                status=labels.inline(status, labels.session_status(status)),
                summary=summary[:80],
            )
        else:
            line = _(
                "- session {number} · {name} ({status})",
                number=number,
                name=name,
                status=labels.inline(status, labels.session_status(status)),
            )
        lines.append(line)
        rows.append({"session": number, "name": name, "status": status, "summary": summary})
    if not rows:
        return Out(data={"sessions": []}, md=_("no sessions yet"))
    head = ngettext("{n} session:", "{n} sessions:", len(rows))
    return Out(data={"sessions": rows}, md="\n".join([head, *lines]))


@command(
    "summary write",
    summary="Write a summary: a scene, a session, an arc, or the story so far",
    writes=True,
    examples=(
        "didact summary write scene 'Freya bargained with the spirit.'",
        "didact summary write session:3 'The party reached the Wood.'",
        "didact summary write arc:withering 'The Wood sickens…' --sessions 1-4",
        "didact summary write campaign 'So far: …'",
    ),
)
def summary_write(
    ctx: Context,
    target: Annotated[str, "scene[:N], session[:N], arc:<name> or campaign", Metavar("target")],
    *text: Annotated[str, "the summary", Metavar("text")],
    sessions: Annotated[
        str | None, "which sessions an arc covers, e.g. 1-4", Metavar("range")
    ] = None,
) -> Out:
    from didact.services import play

    repo = open_repo(ctx)
    current = play.load(repo)
    words = " ".join(text).strip()
    if not words:
        raise InvalidError(
            _("a summary needs text"),
            hint=_("e.g. `didact summary write session:3 'They found the grave.'`"),
        )
    cs = changeset(ctx, repo, N_("summary {target}"), target=target)
    ref = play.summarize(cs, current, target, words, sessions=sessions)
    return finish(
        ctx, cs, done=_("summary written for {target}", target=ref), extra={"target": ref}
    )


@command(
    "summary due",
    summary="List the summaries still to write",
    examples=("didact summary due",),
)
def summary_due(ctx: Context) -> Out:
    from didact.services import play

    repo = open_repo(ctx)
    missing = play.due(repo, play.load(repo))
    if not missing:
        return Out(data={"due": []}, md=_("no summaries due"))
    lines = [
        ngettext("{n} summary due:", "{n} summaries due:", len(missing)),
        *(f"- {m}" for m in missing),
    ]
    example = code("didact summary write <target> " + chr(39) + "…" + chr(39))
    lines.append(_("write one: {command}", command=example))
    return Out(data={"due": list[JSON](missing)}, md="\n".join(lines))
