"""Options: the variant and optional rules a campaign plays with.

A system pack declares them in `rules/`, one document each:

    option: lethality
    title: Lethality
    ask: How deadly should it be?
    choices:
      gentle: "Less lethal: low stakes more often; a dropped PC makes a 3d story roll."
      standard: "As the book has it."
      deadly: "More lethal: high and dire stakes more often; a dropped PC makes a 1d story roll."
    default: standard
    source: "p. 173"
    ---
    option: supplies                # a flag: on or off
    kind: flag
    ask: Play with supplies?
    help: "Each PC has a 4d Supplies resource pool for common items and rations."
    ---
    option: flavor                  # a choice can imply others: the flavor sets its dials
    choices: {standard: …, grimdark: …}
    implies: {grimdark: {lethality: deadly, supplies: true}}

Session zero asks them with Didact's own questions (an option replaces the question of the same
key), the campaign profile keeps the answers (`campaign profile lethality=deadly supplies=on`),
and the pack's rules, character creation and generators read them as `@option.lethality`: the
profile's answer, else what another option implies (all the way: a dial the flavor sets brings
what it implies too), else the default. The brief lists those that differ from the default, with
what they mean.
"""

from dataclasses import dataclass

from didact.core.errors import DidactError, InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.store.repo import Repo

ON = ("on", "yes", "true")
OFF = ("off", "no", "false")


@dataclass(frozen=True, slots=True)
class Option:
    id: str
    pack: str
    title: str
    ask: str
    help: str
    flag: bool
    choices: dict[str, str]  # a choice's value → what it means (a flag has none)
    default: JSON
    implies: dict[str, dict[str, JSON]]  # a choice (or "on") → the options it sets
    source: str

    def meaning(self, value: JSON) -> str:
        """What a value means: a choice's text, or a flag's help when it's on."""
        if self.flag:
            return self.help if value is True else ""
        return self.choices.get(str(value), "")

    def parse(self, text: str) -> JSON:
        """An answer as typed (`deadly`, `on`) as the value rules read."""
        answer = text.strip()
        if self.flag:
            if answer.casefold() in ON:
                return True
            if answer.casefold() in OFF:
                return False
            raise InvalidError(
                _("{option} is on or off", option=self.id),
                hint=_("e.g. {option}=on", option=self.id),
            )
        if answer not in self.choices:
            raise InvalidError(
                _("{option} is one of: {choices}", option=self.id, choices=", ".join(self.choices)),
                hint=_("not {value}", value=repr(answer)),
            )
        return answer


def shown(value: JSON) -> str:
    """A value as the profile shows it: a flag as on or off."""
    if value is True:
        return "on"
    if value is False:
        return "off"
    return str(value)


def declared(repo: Repo) -> list[Option]:
    """The options of the packs in play (the system and its supplements)."""
    from didact.services import packs

    try:
        active = packs.active(repo)
    except DidactError:
        return []
    order = {  # as each pack lists them (dials before the optional rules, say)
        (pack.id, item.id): at
        for pack in active.packs
        for at, item in enumerate(pack.items("option"))
    }
    found = sorted(
        active.all("option"), key=lambda i: (active.ids.index(i.pack), order.get((i.pack, i.id), 0))
    )
    return [_option(item.id, item.pack, item.data) for item in found]


def _option(option_id: str, pack: str, data: dict[str, JSON]) -> Option:
    flag = data.get("kind") == "flag"
    raw = data.get("choices")
    choices = {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}
    default = data.get("default")
    if flag:
        default = default is True
    elif default is None and choices:
        default = next(iter(choices))
    implies = data.get("implies")
    return Option(
        option_id,
        pack,
        str(data.get("title") or option_id),
        str(data.get("ask") or data.get("title") or option_id),
        str(data.get("help") or ""),
        flag,
        choices,
        default,
        {  # a flag's are under `on`
            str(k): v
            for k, v in (implies.items() if isinstance(implies, dict) else [])
            if isinstance(v, dict)
        },
        str(data.get("source") or ""),
    )


def resolved(repo: Repo, answers: dict[str, JSON] | None = None) -> dict[str, JSON]:
    """Every option's value: the profile's answer, else what another option implies, else the
    default (see `_settle`)."""
    settled = _settle(repo, answers)
    return {key: value for key, (value, _setter) in settled.items()}


def implied_by(repo: Repo, answers: dict[str, JSON] | None = None) -> dict[str, tuple[Option, str]]:
    """The options another one sets, each with that option and its value (a flavor sets its
    dials, and a dial what it implies in turn): what `resolved` follows when the profile
    doesn't answer them itself."""
    settled = _settle(repo, answers)
    return {key: setter for key, (_value, setter) in settled.items() if setter is not None}


def _settle(
    repo: Repo, answers: dict[str, JSON] | None
) -> dict[str, tuple[JSON, tuple[Option, str] | None]]:
    """Every option's value, with the option and value that implied it (None: an answer or a
    default). Implications are followed all the way, a step at a time: from the answers, then
    from the defaults of the options still unset (those no other default sets first). An option
    is set once, so an answer wins over what another option implies, that over the default, and
    of two implications the nearer one (in the same step, the later option's); a cycle ends."""
    from didact.services import profile

    options = declared(repo)
    given = answers if answers is not None else profile.load(repo.active_campaign())
    known = {o.id for o in options}
    settled: dict[str, tuple[JSON, tuple[Option, str] | None]] = {
        o.id: (given[o.id], None) for o in options if o.id in given
    }

    def follow(sources: list[Option]) -> None:
        while sources:
            step: dict[str, tuple[JSON, tuple[Option, str] | None]] = {}
            for source in sources:
                chosen = shown(settled[source.id][0])
                for key, value in source.implies.get(chosen, {}).items():
                    if key in known and key not in settled:
                        step[key] = (value, (source, chosen))
            settled.update(step)
            sources = [o for o in options if o.id in step]

    follow([o for o in options if o.id in settled])
    while unset := [o for o in options if o.id not in settled]:
        implied = {key for o in unset for key in o.implies.get(shown(o.default), {})}
        starts = [o for o in unset if o.id not in implied] or unset  # a cycle: its defaults
        settled.update({o.id: (o.default, None) for o in starts})
        follow(starts)
    return {o.id: settled[o.id] for o in options}


def changed(repo: Repo) -> list[tuple[Option, JSON]]:
    """The options that differ from their default, with their values (for the brief)."""
    values = resolved(repo)
    return [(o, values[o.id]) for o in declared(repo) if values.get(o.id) != o.default]
