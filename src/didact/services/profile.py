"""The campaign profile: what session zero settles, carried by every brief.

Stored in `campaign.yaml` under `profile:`. Didact never asks the player anything itself:
`session zero` returns the questions (the system pack's own, if it has some, then these), the
LLM asks them, and `campaign profile key=value …` saves the answers.

    role: gm              # gm (full GM) | co-gm | oracle (interprets oracles only) | scribe
    tone: grim but hopeful
    themes: [loss, wonder]
    lines: [harm to children]   # never in the game
    veils: [torture]            # may happen, off screen
    lethality: deadly           # gentle | standard | deadly
    fudging: never              # never | peril-points
    invention: book-first       # book-first (roll the book's tables first) | balanced | freeform
    narration: {length: short, person: second, tense: present}
    dice: didact                # didact (Didact rolls) | physical (the player rolls: --got)

A pack adds its own questions in `settings.session_zero: [{key, ask}]`, and its options (the
variant and optional rules its `rules/` declare, `didact.services.options`) are asked too; their
answers are saved under their keys, and rules read the options as `@option.<key>`.
"""

from dataclasses import dataclass
from typing import cast

from didact.core.errors import DidactError, InvalidError
from didact.core.i18n import N_, _, translate
from didact.core.output import JSON
from didact.store.repo import CampaignInfo, Repo


@dataclass(frozen=True, slots=True)
class Question:
    key: str
    ask: str
    choices: tuple[str, ...] = ()
    many: bool = False  # a list: `lines+=spiders`
    option: bool = False  # one of the system's options: rules read it (`@option.<key>`)

    @property
    def asked(self) -> str:
        """The question in the reader's language (`ask` stays English: it's data too)."""
        return translate(self.ask)


QUESTIONS: tuple[Question, ...] = (
    Question(
        "role",
        N_("Should I be the full GM, a co-GM (you make some calls), only the oracle, or scribe?"),
        ("gm", "co-gm", "oracle", "scribe"),
    ),
    Question("tone", N_("What tone do you want: grim, hopeful, whimsical, tense, …?")),
    Question("themes", N_("Any themes you want to explore?"), many=True),
    Question("lines", N_("Lines: anything that must never appear in the game?"), many=True),
    Question("veils", N_("Veils: anything that may happen, but off screen?"), many=True),
    Question(
        "lethality", N_("How deadly should it be: gentle, standard or deadly?"),
        ("gentle", "standard", "deadly"),
    ),
    Question(
        "fudging", N_("Should I ever fudge to save a character: never, or with Peril Points?"),
        ("never", "peril-points"),
    ),
    Question(
        "invention",
        N_("Book-first (roll the book's tables before inventing), balanced, or freeform?"),
        ("book-first", "balanced", "freeform"),
    ),
    Question(
        "narration.length", N_("Narration: short, medium or long?"), ("short", "medium", "long")
    ),
    Question("narration.person", N_("Narrate in second or third person?"), ("second", "third")),
    Question("narration.tense", N_("Present or past tense?"), ("present", "past")),
    Question(
        "dice", N_("Should Didact roll, or will you roll physical dice and tell me?"),
        ("didact", "physical"),
    ),
)  # fmt: skip
DEFAULTS: dict[str, JSON] = {"role": "gm", "invention": "balanced", "dice": "didact"}


def load(campaign: CampaignInfo | None) -> dict[str, JSON]:
    raw = campaign.other.get("profile") if campaign is not None else None
    return dict(raw) if isinstance(raw, dict) else {}


def questions(repo: Repo) -> list[Question]:
    """The pack's own session-zero questions and options first, then Didact's (an option
    replaces Didact's question of the same key: the system's lethality, say)."""
    from didact.services import options, packs, sheets

    found: list[Question] = []
    system = sheets.active_system(repo)
    if system:
        try:
            raw = packs.active(repo).settings(system).get("session_zero")
        except DidactError:
            raw = None
        for item in raw if isinstance(raw, list) else []:
            if isinstance(item, dict) and isinstance(item.get("key"), str):
                found.append(Question(str(item["key"]), str(item.get("ask", item["key"]))))
    for option in options.declared(repo):
        choices = ("on", "off") if option.flag else tuple(option.choices)
        found.append(Question(option.id, option.ask, choices, option=True))
    return found + [q for q in QUESTIONS if q.key not in {f.key for f in found}]


def _question(repo: Repo, key: str) -> Question:
    for question in questions(repo):
        if question.key == key:
            return question
    known = ", ".join(q.key for q in questions(repo))
    raise InvalidError(
        _("the profile has no {key}", key=repr(key)), hint=_("keys: {known}", known=known)
    )


def get(profile: dict[str, JSON], key: str) -> JSON:
    head, _sep, tail = key.partition(".")
    value = profile.get(head)
    if tail:
        return value.get(tail) if isinstance(value, dict) else None
    return value


def change(repo: Repo, profile: dict[str, JSON], text: str) -> str:
    """Apply `key=value`, `key+=item` or `key-=item`. Returns what changed, for the output."""
    for op in ("+=", "-=", "="):
        key, sep, value = text.partition(op)
        if sep and key.strip():
            break
    else:
        raise InvalidError(
            _("can't read {text}", text=repr(text)), hint=_("use key=value, e.g. role=co-gm")
        )
    key, value = key.strip(), value.strip()
    question = _question(repo, key)
    if question.option and op == "=":  # the system's: typed as its rules read it
        from didact.services import options

        found = next(o for o in options.declared(repo) if o.id == key)
        if not value:  # back to the default
            profile.pop(key, None)
            return f"{key}: {_('(cleared)')}"
        profile[key] = found.parse(value)
        return f"{key}: {options.shown(profile[key])}"
    if question.choices and value and value not in question.choices:
        raise InvalidError(
            _("{key} is one of: {choices}", key=key, choices=", ".join(question.choices)),
            hint=_("not {value}", value=repr(value)),
        )
    head, _sep, tail = key.partition(".")
    if question.many:
        current = [str(v) for v in cast(list[JSON], profile.get(head) or [])]
        items = [v.strip() for v in value.split(",") if v.strip()]
        if op == "-=":
            current = [c for c in current if c not in items]
        elif op == "+=":
            current += [i for i in items if i not in current]
        else:
            current = items
        profile[head] = list[JSON](current)
        return f"{key}: {', '.join(current) or _('(none)')}"
    if op != "=":
        raise InvalidError(_("{key} takes `=`", key=key), hint=_("e.g. {key}=…", key=key))
    if tail:
        block = profile.get(head)
        merged = dict(block) if isinstance(block, dict) else {}
        merged[tail] = value
        profile[head] = merged
    else:
        profile[head] = value
    return f"{key}: {value or _('(cleared)')}"


def line(profile: dict[str, JSON], *, skip: frozenset[str] = frozenset()) -> str:
    """One line for the brief: `Profile: role gm · tone grim · lines: … · dice physical (--got)`.
    `skip`: keys shown elsewhere (the brief gives each changed option a line of its own)."""
    from didact.core import labels
    from didact.services.options import shown

    def key(name: str) -> str:
        return labels.inline(name, labels.profile_key(name))

    def value(raw: JSON) -> str:  # one of Didact's choices is named; a free answer is as given
        return labels.inline(str(raw), labels.profile_value(str(raw)))

    merged = {k: v for k, v in {**DEFAULTS, **profile}.items() if k not in skip or k in DEFAULTS}
    parts = [f"{key('role')} {value(merged['role'])}"]
    for name in ("tone", "lethality", "fudging"):
        if merged.get(name):
            parts.append(f"{key(name)} {value(merged[name])}")
    for name in ("themes", "lines", "veils"):
        items = merged.get(name)
        if isinstance(items, list) and items:
            parts.append(f"{key(name)}: {', '.join(str(i) for i in items)}")
    parts.append(f"{key('invention')} {value(merged['invention'])}")
    narration = merged.get("narration")
    if isinstance(narration, dict) and narration:
        parts.append(f"{key('narration')} " + "/".join(value(v) for v in narration.values()))
    dice = merged["dice"]
    parts.append(
        _("dice physical (ask, then --got)")
        if dice == "physical"
        else f"{key('dice')} {value(dice)}"
    )
    known = {q.key.partition(".")[0] for q in QUESTIONS}
    parts += [  # a pack's own answers, in its own words
        f"{k} {shown(v)}" for k, v in profile.items() if k not in known and k not in skip
    ]
    return _("Profile: {parts}", parts=" · ".join(parts))


def physical_dice(repo: Repo) -> bool:
    return load(repo.active_campaign()).get("dice") == "physical"
