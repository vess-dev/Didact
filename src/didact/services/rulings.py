"""Rulings: how an unclear rule was settled, so the same question gets the same answer.

A ruling is a `ruling` record: its name is the question, its fields hold the question, the
ruling and optionally the rule it's about, and its body is the ruling. It lives in the campaign
(the default), the world, or the system (every game of that system). `rules lookup` shows the
rulings that match the topic, and `do <rule>` shows the rulings about that rule.
"""

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.core.ids import EntityId, Scope, slugify
from didact.core.output import JSON
from didact.services import records
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.repo import Repo

NAME_LENGTH = 80


def scope_for(repo: Repo, text: str | None) -> Scope:
    """`campaign` (default), `world`, `system`, or a full scope such as `world:vale`."""
    wanted = (text or "campaign").strip()
    if ":" in wanted or wanted == "global":
        return repo.check_scope(Scope.parse(wanted))
    chain = {s.kind: s for s in repo.chain()}
    if wanted in chain:
        return chain[wanted]
    raise InvalidError(
        _("no {scope} here for the ruling", scope=wanted),
        hint=_("use campaign, world or system (or a full scope)"),
    )


def add(
    cs: Changeset,
    question: str,
    answer: str,
    *,
    scope: Scope,
    rule: str | None = None,
    tags: list[str] | None = None,
    keys: list[str] | None = None,
) -> Entity:
    text = " ".join(question.split())
    if not text or not answer.strip():
        raise InvalidError(
            _("a ruling needs a question and an answer"),
            hint=_("e.g. `didact ruling add 'Can you swim in armor?' 'No'`"),
        )
    name = text if len(text) <= NAME_LENGTH else text[: NAME_LENGTH - 1].rsplit(" ", 1)[0] + "…"
    fields: dict[str, JSON] = {"question": text, "ruling": answer.strip()}
    if rule:
        fields["rule"] = rule
    if keys:
        fields["keys"] = list[JSON](keys)  # what brings it up in scans (else its rule, tags)
    base = slugify(name)[:40].strip("-") or "ruling"
    entity_id = EntityId("ruling", base)
    taken = {r.id for r in cs.repo.index().rows([scope], types=["ruling"], include_archived=True)}
    number = 2
    while str(entity_id) in taken:
        entity_id = EntityId("ruling", f"{base}-{number}")
        number += 1
    entity = records.build_entity(
        entity_id, name, dict(fields), tags=tags or (), body=answer.strip() + "\n"
    )
    records.create(cs, scope, entity)
    return entity


def _all(repo: Repo) -> list[Entity]:
    rows = repo.index().rows(repo.chain(), types=["ruling"])
    return [repo.located(row).entity for row in rows]


def matching(repo: Repo, words: list[str]) -> list[Entity]:
    """Rulings whose question, answer, rule or tags mention every word."""
    wanted = [w.casefold() for w in words if w.strip()]
    if not wanted:
        return []
    found: list[Entity] = []
    for entity in _all(repo):
        text = " ".join(
            [entity.name, entity.body, *entity.tags, *(str(v) for v in entity.fields.values())]
        ).casefold()
        if all(w in text for w in wanted):
            found.append(entity)
    return found


def for_rule(repo: Repo, rule_id: str) -> list[Entity]:
    """Rulings about a rule (`my-system.attack` or just `attack`)."""
    bare = rule_id.rpartition(".")[2]
    return [
        e
        for e in _all(repo)
        if isinstance(e.fields.get("rule"), str) and str(e.fields["rule"]) in (rule_id, bare)
    ]


def line(entity: Entity) -> str:
    question = entity.fields.get("question", entity.name)
    answer = entity.fields.get("ruling", entity.body.strip())
    return f"ruling [{entity.id}]: {question} → {answer}"
