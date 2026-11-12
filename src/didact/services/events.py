"""Game events that run `trigger` rules: time passing, scenes, sessions and fights starting and
ending.

    trigger: new-day
    on: time                         # time | scene_start | scene_end | session_start | session_end
    when: "@time.passed >= 86400"    # optional; triggers can read @time.*, @scene, @session
    steps: ["A new day dawns: check rations."]

`combat_start` and `combat_end` read the fight that starts or ends: `@combat.round` and
`@combat.fighters`.

`for: pcs` (or `party`) runs a trigger once per player character (or party member), as `who`:
experience after each session, say.

Field changes fire the sheet's hooks instead (see `hooks`); `on: manual` triggers run only with
`didact do`. A trigger's rolls and changes join the changeset of whatever fired it.
"""

from didact.core.errors import DidactError
from didact.core.i18n import _
from didact.expr.model import Value
from didact.packs.library import PackSet
from didact.rules.engine import Engine, Rule
from didact.services import packs, play, rules
from didact.store.changeset import Changeset
from didact.store.repo import Repo

EVENTS = (
    "time", "scene_start", "scene_end", "session_start", "session_end", "combat_start",
    "combat_end",
)  # fmt: skip


def fire(
    repo: Repo,
    cs: Changeset,
    event: str,
    preset: dict[str, Value] | None = None,
    *,
    dry: bool = False,
    command: str | None = None,
) -> list[str]:
    """Run every `on: <event>` trigger whose `when` holds. Returns a line per trigger that ran."""
    try:
        active = packs.active(repo)
    except DidactError:
        return []  # no packs here yet: nothing to trigger
    values = now(repo) | (preset or {})
    ran: list[str] = []
    for rule in rules.all_rules(active):
        if rule.kind != "trigger" or rule.data.get("on") != event:
            continue
        each = rule.data.get("for")
        if each in ("party", "pcs"):
            ran += _for_each(repo, cs, active, rule, str(each), values, dry=dry, command=command)
            continue
        needs = [
            p.name
            for p in rule.params.values()
            if not p.optional and p.default is None and p.name != "oracle"  # supplied
        ]
        if needs:
            ran.append(
                _(
                    "{rule}: skipped (it needs {params}; run it with `do`)",
                    rule=rule.id,
                    params=", ".join(needs),
                )
            )
            continue
        host = rules.LibraryHost(repo, cs, active, dry, command)
        if "oracle" in rule.params and host.oracle_state(rule) is None:
            ran.append(_("{rule}: skipped (its oracle has no state yet)", rule=rule.id))
            continue  # a dry run starts nothing
        try:
            result = Engine(host).run(rule, {}, preset=values)
        except DidactError as exc:
            raise failed(rule, exc) from exc
        if not result.skipped:
            ran.append(f"{rule.id}: " + " · ".join(line.strip() for line in result.lines))
    return ran


def failed(rule: Rule, exc: DidactError) -> DidactError:
    """A trigger that fails says it's the trigger, and how to get on without it: a pack's
    mistake mustn't stop `scene end`, `session end` or `combat end` for good."""
    away = _(
        "to go on without it for now: `didact override add trigger {rule} --data "
        '\'{{"on": "manual"}}\'` (`didact override remove` brings it back)',
        rule=rule.id,
    )
    return DidactError(
        _("trigger {rule} failed: {problem}", rule=rule.id, problem=exc.message),
        hint=f"{exc.hint}; {away}" if exc.hint else away,
        where=exc.where,
        code=exc.code,
    )


def _for_each(
    repo: Repo,
    cs: Changeset,
    active: PackSet,
    rule: Rule,
    each: str,
    values: dict[str, Value],
    *,
    dry: bool,
    command: str | None,
) -> list[str]:
    """A `for:` trigger, once per party member (`pcs`: the player characters), as `who`."""
    from didact.services import party

    ran: list[str] = []
    probe = rules.LibraryHost(repo, cs, active, dry, command)
    if "oracle" in rule.params and probe.oracle_state(rule) is None:
        return [_("{rule}: skipped (its oracle has no state yet)", rule=rule.id)]
    for member in party.members(repo, gm=True):
        if each == "pcs" and member.role != "pc":
            continue
        host = rules.LibraryHost(repo, cs, active, dry, command)
        try:
            result = Engine(host).run(rule, {"who": str(member.entity.id)}, preset=values)
        except DidactError as exc:
            raise failed(rule, exc) from exc
        if not result.skipped:
            said = " · ".join(line.strip() for line in result.lines)
            ran.append(f"{rule.id} ({member.entity.name}): {said}")
    return ran


def now(repo: Repo) -> dict[str, Value]:
    """Where play stands, as every rule reads it: the system played (`@system`), `@session`,
    `@scene`, the game time (`@time.day`, `@time.hour`, … as the calendar has them) and, while
    a fight is on, `@combat.round` and `@combat.fighters`."""
    from didact.services import combat, sheets, timeline

    current = play.load(repo)
    found: dict[str, Value] = {
        "system": sheets.active_system(repo) or "",
        "session": current.session,
        "scene": current.scene,
    }
    fight = combat.load(repo) if repo.active_world() is not None else None
    if fight is not None:
        found |= combat.values(fight)
    return found | timeline.calendar(repo).values(current.seconds)
