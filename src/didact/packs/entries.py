"""Checking compendium entries when a pack is built: each needs an id, a type and a name."""

import re

from didact.core.i18n import _
from didact.packs.kinds import register_validator
from didact.packs.source import Doc, Problem

TYPE_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")


def check_entry(doc: Doc) -> list[Problem]:
    problems: list[Problem] = []
    type_ = doc.data.get("type")
    if not isinstance(type_, str) or not TYPE_RE.match(type_):
        message = _("an entry needs a `type` (the record type it spawns)")
        problems.append(doc.problem(("type",), message, _("e.g. type: monster")))
    name = doc.data.get("name")
    if not isinstance(name, str) or not name.strip():
        problems.append(doc.problem(("name",), _("an entry needs a `name`")))
    return problems


register_validator("entry", check_entry)
