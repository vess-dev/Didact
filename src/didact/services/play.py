"""The play layer: sessions and scenes, the journal of beats, transcripts and summaries.

History is kept in three layers, all of them:
1. the full transcript (`transcripts/session-004.md`): every player message and GM reply;
2. the journal (`journal/session-004.jsonl`): typed beats with marks (`@ ? d: -> =>`);
3. summaries: scene → session → arc → campaign, each recording what it covers.
Sessions and scenes are records (`session:4`, `scene:12`), so they can be found and linked.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from didact.core.clock import now_iso
from didact.core.errors import ConflictError, InvalidError, NotFoundError
from didact.core.i18n import _
from didact.core.ids import EntityId, Scope
from didact.core.output import JSON
from didact.services import records, state
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Located, Repo

PLAY = "play"

type BeatKind = Literal[
    "action", "oracle", "roll", "result", "consequence", "narration", "dialogue", "note", "ooc"
]
BEAT_KINDS: dict[str, str] = {  # kind → its mark in the journal
    "action": "@",
    "oracle": "?",
    "roll": "d:",
    "result": "->",
    "consequence": "=>",
    "narration": "",
    "dialogue": '"',
    "note": "//",
    "ooc": "(ooc)",
}
type Role = Literal["player", "gm"]


@dataclass(slots=True)
class PlayState:
    session: int = 0
    session_open: bool = False
    scene: int = 0
    scene_open: bool = False
    bound: str | None = None  # the Claude Code session whose turns go into the transcript
    seconds: int = 0  # in-game time since the campaign began (see didact.services.clock)
    location: str | None = None  # where the party is (`didact visit`)
    extra: dict[str, JSON] = field(default_factory=dict)

    @classmethod
    def from_data(cls, data: dict[str, JSON]) -> PlayState:
        known = {
            "session", "session_open", "scene", "scene_open", "bound", "seconds", "location",
        }  # fmt: skip
        return cls(
            session=_int(data.get("session")),
            session_open=bool(data.get("session_open")),
            scene=_int(data.get("scene")),
            scene_open=bool(data.get("scene_open")),
            bound=str(data["bound"]) if isinstance(data.get("bound"), str) else None,
            seconds=_int(data.get("seconds")),
            location=str(data["location"]) if isinstance(data.get("location"), str) else None,
            extra={k: v for k, v in data.items() if k not in known},
        )

    def to_data(self) -> dict[str, JSON]:
        data: dict[str, JSON] = {
            "session": self.session,
            "session_open": self.session_open,
            "scene": self.scene,
            "scene_open": self.scene_open,
            "seconds": self.seconds,
        }
        if self.bound:
            data["bound"] = self.bound
        if self.location:
            data["location"] = self.location
        return data | self.extra


def _int(raw: JSON) -> int:
    return raw if isinstance(raw, int) and not isinstance(raw, bool) else 0


def campaign_dir(repo: Repo) -> Path:
    campaign = repo.active_campaign()
    if campaign is None:
        raise InvalidError(
            _("no campaign is open: play happens in one"),
            hint=_("`didact campaign open <id>` (or start one: `didact campaign new <id>`)"),
        )
    return repo.layout.campaign_dir(campaign.world, campaign.id)


def load(repo: Repo) -> PlayState:
    if repo.active_campaign() is None:
        return PlayState()
    return PlayState.from_data(state.load(repo, PLAY))


def save(cs: Changeset, current: PlayState) -> None:
    state.plan(cs, PLAY, current.to_data())


def marks(repo: Repo) -> dict[str, JSON]:
    """What rolls and beats are tagged with: the open session, scene and turn group."""
    from didact.services import turns

    found: dict[str, JSON] = {}
    turn = turns.current(repo)
    if turn:
        found["turn"] = turn
    try:
        current = load(repo)
    except InvalidError:
        return found
    if not current.session_open:
        return found
    found["session"] = current.session
    if current.scene_open:
        found["scene"] = current.scene
    return found


# ---------------------------------------------------------------------------- records


def _scope(repo: Repo) -> Scope:
    campaign = repo.active_campaign()
    assert campaign is not None
    return Scope("campaign", campaign.id)


def _record(repo: Repo, type_: str, number: int) -> Located:
    return repo.resolve(f"{type_}:{number}", scopes=[_scope(repo)])


def _create(cs: Changeset, type_: str, number: int, name: str, fields: dict[str, JSON]) -> Entity:
    entity = records.build_entity(EntityId(type_, str(number)), name, {"fields": fields})
    records.create(cs, _scope(cs.repo), entity)
    return entity


def _update(
    cs: Changeset, type_: str, number: int, values: dict[str, JSON], summary: str | None = None
) -> None:
    located = _record(cs.repo, type_, number)

    def change(entity: Entity) -> None:
        for key, value in values.items():
            if value is None:
                entity.fields.pop(key, None)  # None removes a field (e.g. `stale`)
            else:
                entity.fields[key] = value
        if summary is not None:
            entity.body = set_summary(entity.body, summary)

    records.edit(cs, located.path, change)


def set_summary(body: str, text: str) -> str:
    """Put `text` under a `## Summary` heading at the top of a body (replacing an old one)."""
    lines = body.splitlines()
    kept: list[str] = []
    skipping = False
    for line in lines:
        if line.strip() == "## Summary":
            skipping = True
            continue
        if skipping and line.startswith("## "):
            skipping = False
        if not skipping:
            kept.append(line)
    rest = "\n".join(kept).strip()
    return f"## Summary\n\n{text.strip()}\n" + (f"\n{rest}\n" if rest else "")


def get_summary(body: str) -> str:
    text = body.split("## Summary", 1)
    if len(text) < 2:
        return ""
    return text[1].split("\n## ", 1)[0].strip()


def summary_of(body: str, *, gm: bool) -> str:
    """A record's summary as this view may show it: a player view leaves out its secret
    sections (`### Secrets` under the summary, say)."""
    from didact.services import knowledge

    return get_summary(body if gm else knowledge.player_body(body)[0])


def title_of(record: Entity | None, fallback: str, *, gm: bool) -> str:
    """A session's or scene's title as this view may show it: a secret one goes by its
    number (`fallback`) in a player view."""
    from didact.services import knowledge

    if record is None or not knowledge.visible(record.knowledge, gm):
        return fallback
    return record.name


# ---------------------------------------------------------------------------- sessions and scenes


def start_session(cs: Changeset, current: PlayState, title: str | None) -> int:
    campaign_dir(cs.repo)  # sessions belong to a campaign: say so plainly if there isn't one
    if current.session_open:
        raise ConflictError(
            _("session {session} is still open", session=current.session),
            hint=_("`didact session end` first (or keep playing)"),
        )
    current.session += 1
    current.session_open = True
    current.bound = None  # the first captured turn binds the transcript to its Claude session
    name = title or f"Session {current.session}"
    _create(
        cs,
        "session",
        current.session,
        name,
        {"number": current.session, "status": "open", "started": now_iso()},
    )
    save(cs, current)
    return current.session


def end_session(cs: Changeset, current: PlayState, summary: str | None) -> int:
    campaign_dir(cs.repo)  # a closed campaign says so first
    if not current.session_open:
        raise InvalidError(_("no session is open"), hint=_("`didact session start`"))
    if current.scene_open:
        end_scene(cs, current, None)
    _update(cs, "session", current.session, {"status": "closed", "ended": now_iso()}, summary)
    current.session_open = False
    current.bound = None
    save(cs, current)
    return current.session


def new_scene(cs: Changeset, current: PlayState, title: str | None, expected: str | None) -> int:
    if not current.session_open:
        raise InvalidError(_("scenes happen in a session"), hint=_("`didact session start` first"))
    if current.scene_open:
        end_scene(cs, current, None)
    current.scene += 1
    current.scene_open = True
    fields: dict[str, JSON] = {
        "number": current.scene,
        "session": current.session,
        "status": "open",
    }
    if expected:
        fields["expected"] = expected
    _create(cs, "scene", current.scene, title or f"Scene {current.scene}", fields)
    _update(
        cs, "session", current.session, {"scenes": _scenes_of(cs, current.session, current.scene)}
    )
    save(cs, current)
    return current.scene


def _scenes_of(cs: Changeset, session: int, adding: int) -> list[JSON]:
    located = _record(cs.repo, "session", session)
    entity = records.planned(cs, located.path)
    found = entity.fields.get("scenes")
    listed = [s for s in found if isinstance(s, int)] if isinstance(found, list) else []
    return list[JSON]([*listed, adding] if adding not in listed else listed)


def end_scene(cs: Changeset, current: PlayState, summary: str | None) -> int:
    if not current.scene_open:
        raise InvalidError(_("no scene is open"), hint=_("`didact scene new`"))
    _update(cs, "scene", current.scene, {"status": "closed"}, summary)
    current.scene_open = False
    save(cs, current)
    return current.scene


# ---------------------------------------------------------------------------- journal


def journal_path(repo: Repo, session: int) -> Path:
    return campaign_dir(repo) / "journal" / f"session-{session:03d}.jsonl"


def add_beat(
    cs: Changeset,
    current: PlayState,
    kind: str,
    text: str,
    *,
    importance: int | None = None,
    rolls: list[str] | None = None,
    about: list[str] | None = None,
    secret: bool = False,
) -> dict[str, JSON]:
    """One journal line. `about` names the records it concerns (ids): each record's chronicle
    shows it. `secret` beats happen out of the players' sight (GM views only)."""
    if kind not in BEAT_KINDS:
        raise InvalidError(
            _("unknown beat kind {kind}", kind=repr(kind)),
            hint=_("use one of: {kinds}", kinds=", ".join(BEAT_KINDS)),
        )
    campaign_dir(cs.repo)
    if not current.session_open:
        raise InvalidError(
            _("the journal records sessions"), hint=_("`didact session start` first")
        )
    if not text.strip():
        raise InvalidError(
            _("a beat needs text"), hint=_("e.g. `didact log action 'Freya climbs the tower'`")
        )
    path = journal_path(cs.repo, current.session)
    existing = cs.planned_text(path) or ""
    number = _next_number(existing)
    beat: dict[str, JSON] = {
        "id": f"S{current.session}.{number}",
        "seq": cs.repo.log.last_seq() + 1,  # the event that writes it: orders beats among rolls
        "ts": now_iso(),
        "session": current.session,
        "kind": kind,
        "text": text.strip(),
        "time": current.seconds,
    }
    if current.scene_open:
        beat["scene"] = current.scene
    if importance is not None:
        if not 1 <= importance <= 10:
            raise InvalidError(_("importance is 1–10"), hint=_("e.g. --importance 7"))
        beat["importance"] = importance
    if rolls:
        beat["rolls"] = list[JSON](["#" + r.lstrip("#") for r in rolls])
    if about:
        beat["about"] = list[JSON](dict.fromkeys(about))
    if secret:
        beat["secret"] = True
    if cs.turn:
        beat["turn"] = cs.turn
    cs.append(path, json.dumps(beat, ensure_ascii=False) + "\n")
    return beat


def _next_number(journal: str) -> int:
    """The next beat number in a session: after the highest one, so a removed beat's number
    is never given again."""
    highest = 0
    for line in journal.splitlines():
        if line.strip():
            beat_id = str(json.loads(line).get("id", ""))
            tail = beat_id.rpartition(".")[2]
            highest = max(highest, int(tail) if tail.isdigit() else 0)
    return highest + 1


def _session_of(beat_id: str) -> int:
    head = beat_id.strip().upper().partition(".")[0]
    if not head.startswith("S") or not head[1:].isdigit():
        raise InvalidError(
            _("{beat} isn't a beat id", beat=repr(beat_id)), hint=_("beat ids look like S3.12")
        )
    return int(head[1:])


def find_beat(repo: Repo, beat_id: str) -> tuple[int, list[dict[str, JSON]], int]:
    """A beat by id (S3.12): its session, that session's beats, and its index among them."""
    session = _session_of(beat_id)
    found = beats(repo, session)
    wanted = beat_id.strip().upper()
    for index, beat in enumerate(found):
        if str(beat.get("id", "")).upper() == wanted:
            return session, found, index
    raise NotFoundError(
        _("no beat {beat} in the journal", beat=beat_id),
        hint=_("see `didact session show {session}`", session=session),
    )


def _write_journal(cs: Changeset, session: int, found: list[dict[str, JSON]]) -> None:
    text = "".join(json.dumps(b, ensure_ascii=False) + "\n" for b in found)
    path = journal_path(cs.repo, session)
    if text:
        cs.write(path, text)
    else:
        cs.delete(path)


def edit_beat(
    cs: Changeset,
    beat_id: str,
    *,
    text: str | None = None,
    kind: str | None = None,
    importance: int | None = None,
    about: list[str] | None = None,
    not_about: list[str] | None = None,
    secret: bool | None = None,
) -> dict[str, JSON]:
    """Correct a beat: its text, kind, importance, who it's about, whether it's secret."""
    session, found, index = find_beat(cs.repo, beat_id)
    beat = dict(found[index])
    if text is not None:
        if not text.strip():
            raise InvalidError(_("a beat needs text"), hint=_("remove it with `didact beat rm`"))
        beat["text"] = text.strip()
    if kind is not None:
        if kind not in BEAT_KINDS:
            raise InvalidError(
                _("unknown beat kind {kind}", kind=repr(kind)),
                hint=_("use one of: {kinds}", kinds=", ".join(BEAT_KINDS)),
            )
        beat["kind"] = kind
    if importance is not None:
        if not 1 <= importance <= 10:
            raise InvalidError(_("importance is 1–10"), hint=_("e.g. --importance 7"))
        beat["importance"] = importance
    raw_about = beat.get("about")
    listed = [str(a) for a in raw_about] if isinstance(raw_about, list) else []
    listed = [a for a in [*listed, *(about or [])] if a not in (not_about or [])]
    if listed:
        beat["about"] = list[JSON](dict.fromkeys(listed))
    else:
        beat.pop("about", None)
    if secret is not None:
        if secret:
            beat["secret"] = True
        else:
            beat.pop("secret", None)
    found[index] = beat
    _write_journal(cs, session, found)
    return beat


def remove_beat(cs: Changeset, beat_id: str) -> dict[str, JSON]:
    session, found, index = find_beat(cs.repo, beat_id)
    beat = found.pop(index)
    _write_journal(cs, session, found)
    return beat


def visible(beat: dict[str, JSON], gm: bool) -> bool:
    """Whether a viewer sees a beat: secret beats are for the GM."""
    return gm or not beat.get("secret")


def beats(repo: Repo, session: int) -> list[dict[str, JSON]]:
    text = repo.read_text(journal_path(repo, session)) or ""
    found: list[dict[str, JSON]] = []
    for line in text.splitlines():
        if line.strip():
            item = json.loads(line)
            if isinstance(item, dict):
                found.append(item)
    return found


def beat_line(beat: dict[str, JSON]) -> str:
    mark = BEAT_KINDS.get(str(beat.get("kind")), "")
    text = str(beat.get("text", ""))
    if beat.get("kind") == "dialogue":
        body = f'"{text}"'
    elif mark:
        body = f"{mark} {text}"
    else:
        body = text
    rolls = beat.get("rolls")
    if isinstance(rolls, list) and rolls:
        body += f" ({', '.join(str(r) for r in rolls)})"
    return body


# ---------------------------------------------------------------------------- transcript


def transcript_path(repo: Repo, session: int) -> Path:
    return campaign_dir(repo) / "transcripts" / f"session-{session:03d}.md"


def add_turn(cs: Changeset, current: PlayState, role: Role, text: str) -> None:
    campaign_dir(cs.repo)
    if not current.session_open:
        raise InvalidError(_("no session is open"), hint=_("`didact session start`"))
    path = transcript_path(cs.repo, current.session)
    head = "" if cs.planned_text(path) else f"# Session {current.session} transcript\n\n"
    cs.append(path, f"{head}### {now_iso()} · {role}\n\n{text.strip()}\n\n")


def capture_text(raw: str, role: Role | None) -> tuple[Role, str, str | None] | None:
    """Read what a Claude Code hook sends (JSON on stdin) or plain text.

    UserPromptSubmit gives `prompt` (the player's turn); Stop gives `last_assistant_message`
    (the GM's reply). Returns (role, text, the hook's session id) or None if nothing to keep.
    """
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    if isinstance(data, dict):
        session = str(data["session_id"]) if isinstance(data.get("session_id"), str) else None
        if isinstance(data.get("prompt"), str):
            return "player", str(data["prompt"]), session
        if isinstance(data.get("last_assistant_message"), str):
            return "gm", str(data["last_assistant_message"]), session
        return None
    if not raw.strip():
        return None
    return role or "player", raw, None


# ---------------------------------------------------------------------------- summaries


def summarize(
    cs: Changeset, current: PlayState, target: str, text: str, *, sessions: str | None
) -> str:
    """Write a summary. Targets: `scene` / `scene:N`, `session` / `session:N`, `arc:<name>`,
    `campaign` (the story so far). Returns the record it went to."""
    last_event = cs.repo.log.last_seq()
    kind, _sep, which = target.partition(":")
    if kind in ("scene", "session"):
        number = (
            int(which)
            if which.isdigit()
            else (current.scene if kind == "scene" else current.session)
        )
        if number <= 0:
            raise InvalidError(
                _("no {kind} yet to summarize", kind=kind),
                hint=_("`didact session start` or `didact scene new` first"),
            )
        written: dict[str, JSON] = {
            "summarized": now_iso(),
            "summary_covers": f"#e{last_event}",
            "stale": None,  # rewritten: no longer stale
        }
        _update(cs, kind, number, written, text)
        return f"{kind}:{number}"
    if kind in ("arc", "campaign"):
        slug = "campaign" if kind == "campaign" else f"arc-{which or 'current'}"
        entity_id = EntityId("summary", slug)
        repo = cs.repo
        fields: dict[str, JSON] = {
            "kind": kind,
            "summarized": now_iso(),
            "up_to_session": current.session,
        }
        if sessions:
            fields["sessions"] = sessions
        if repo.exists(_scope(repo), entity_id):
            located = repo.resolve(str(entity_id), scopes=[_scope(repo)])

            def change(entity: Entity) -> None:
                entity.fields.update(fields)
                entity.fields.pop("stale", None)
                entity.body = text.strip() + "\n"

            records.edit(cs, located.path, change)
        else:
            name = "The story so far" if kind == "campaign" else f"Arc: {which or 'current'}"
            entity = records.build_entity(entity_id, name, {"fields": fields, "body": text})
            records.create(cs, _scope(repo), entity)
        return str(entity_id)
    raise InvalidError(
        _("can't summarize {target}", target=repr(target)),
        hint=_("use scene, session, arc:<name> or campaign"),
    )


def due(repo: Repo, current: PlayState) -> list[str]:
    """Summaries still to write, as lines: `session:3`, `campaign (stale: …)`."""
    return [
        _("{target} ({why})", target=t, why=why) if why else t
        for t, why in due_items(repo, current)
    ]


def due_items(repo: Repo, current: PlayState) -> list[tuple[str, str]]:
    """Summaries still to write: closed scenes and sessions without one, a stale story so far.
    Each is (target, why), why being "" when the summary is simply missing."""
    found: list[tuple[str, str]] = []
    scope = [_scope(repo)]
    for type_, top in (("scene", current.scene), ("session", current.session)):
        for number in range(1, top + 1):
            try:
                located = _record(repo, type_, number)
            except NotFoundError:
                continue
            fields = located.entity.fields
            if fields.get("status") == "closed" and not get_summary(located.entity.body):
                found.append((f"{type_}:{number}", ""))
            elif isinstance(fields.get("stale"), str):
                found.append((f"{type_}:{number}", _("stale: {why}", why=fields["stale"])))
    closed = current.session - (1 if current.session_open else 0)
    if closed >= 1:
        try:
            story = repo.resolve("summary:campaign", scopes=scope).entity
            up_to = story.fields.get("up_to_session")
            if isinstance(story.fields.get("stale"), str):
                found.append(("campaign", _("stale: {why}", why=story.fields["stale"])))
            elif isinstance(up_to, int) and up_to < closed:
                stops = _("the story so far stops at session {n}", n=up_to)
                found.append(("campaign", stops))
        except NotFoundError:
            if closed >= 2:
                found.append(("campaign", _("no story-so-far yet")))
    return found


def summary_text(repo: Repo, ref: str, *, gm: bool = True) -> str:
    """A session's, arc's or the story's summary; a player view leaves out secret sections."""
    from didact.services import knowledge

    try:
        entity = repo.resolve(ref, scopes=[_scope(repo)]).entity
    except NotFoundError:
        return ""
    if not knowledge.visible(entity.knowledge, gm):
        return ""
    body = entity.body if gm else knowledge.player_body(entity.body)[0]
    return get_summary(body) or (body.strip() if entity.type == "summary" else "")


def session_record(repo: Repo, number: int) -> Entity | None:
    try:
        return _record(repo, "session", number).entity
    except NotFoundError:
        return None


def scene_record(repo: Repo, number: int) -> Entity | None:
    try:
        return _record(repo, "scene", number).entity
    except NotFoundError:
        return None
