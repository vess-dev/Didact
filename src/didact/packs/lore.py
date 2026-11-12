"""Checking lore entries shipped in packs (`lore/*.yaml`): rule reminders, setting canon, …

lore: torch-uses
keys: [torch, lantern]
kind: rule-reminder
content: "Torches burn for 3 uses; an oil can relights a lantern 6 times."
"""

from didact.core.i18n import _
from didact.packs.kinds import register_validator
from didact.packs.source import Doc, Problem

LORE_KEYS = frozenset({
    "lore", "keys", "content", "kind", "priority", "secondary", "logic", "constant", "group",
    "probability", "recursive", "title", "source", "tags",
})  # fmt: skip


def check_lore(doc: Doc) -> list[Problem]:
    data = doc.data
    problems = [
        doc.problem(
            (key,),
            _("unknown key `{key}`", key=key),
            _("a lore entry takes: {keys}", keys=", ".join(sorted(LORE_KEYS))),
        )
        for key in sorted(set(data) - LORE_KEYS)
    ]
    keys = data.get("keys")
    if not data.get("constant") and not (isinstance(keys, list) and keys):
        problems.append(
            doc.problem(("keys",), _("a lore entry needs `keys` (or `constant: true`)"))
        )
    if not isinstance(data.get("content"), str) or not str(data.get("content")).strip():
        problems.append(
            doc.problem(("content",), _("a lore entry needs `content`, naming its subject"))
        )
    return problems


register_validator("lore", check_lore)
