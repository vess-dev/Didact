"""Safe edits. A form that saves what you typed also carries what the page showed you (`was.*`
fields), and saving refuses when that part of the record changed since: a change made in the
meantime (by an LLM on the command line, or in another tab) is never overwritten unseen.

Relative changes (`hp-=2`) always go through, since they add up. And in the player view, the
GM's hidden details and fields can't be written over: the page never showed them."""

import json

from didact.core.errors import ConflictError, InvalidError
from didact.core.i18n import _
from didact.core.output import JSON, flatten
from didact.web.app import Request
from didact.web.forms import split_tags, text_block

WAS_DETAILS = "was.details"  # JSON snapshots of what the page showed
WAS_FIELDS = "was.fields"
WAS_VALUES = "was.values"


class StaleForm(ConflictError):
    """The record changed after the page showed it, so saving would overwrite that change."""


def snapshot(values: dict[str, JSON]) -> str:
    return json.dumps(values, ensure_ascii=False, sort_keys=True)


def flat_fields(data: dict[str, JSON]) -> dict[str, JSON]:
    fields = data.get("fields")
    return dict(flatten(fields)) if isinstance(fields, dict) else {}


def check_edit(req: Request, ref: str, changes: dict[str, JSON]) -> None:
    """The name, tags, aliases and description: each one being changed must still be as the
    page showed it."""
    now = _now(req, ref)
    for key in changes:
        if key == "body":
            before = text_block(req.field("was.body")).strip()
            after = text_block(str(now.get("body") or "")).strip()
            if before != after:
                raise StaleForm(
                    _(
                        "{name}'s description changed since you opened this page",
                        name=_name(now, ref),
                    ),
                    hint=_(
                        "the new version is shown above and yours is in the editor: merge "
                        "them, then save again"
                    ),
                )
            continue
        if key == "name":
            was: JSON = req.field("was.name").strip()
            current: JSON = str(now.get("name") or "")
        else:  # tags, aliases
            was = list[JSON](split_tags(req.field(f"was.{key}")))
            current = [str(v) for v in _list(now.get(key))]
        if not _same(was, current):
            shown = current if isinstance(current, str) else ", ".join(map(str, _list(current)))
            raise StaleForm(
                _(
                    "{name}'s {key} changed since you opened this page: now “{value}”",
                    name=_name(now, ref),
                    key=key,
                    value=shown or _("none"),
                ),
                hint=_("the page shows the new value now; change it again if you still want to"),
            )


def check_detail(req: Request, ref: str, name: str) -> None:
    """One named detail (`about`). The player view may add a note for the GM, but not write
    over one it can't see."""
    from didact.services.knowledge import KNOWN_DETAILS

    now = _now(req, ref)
    current = _dict(now.get("details")).get(name)
    if not req.gm and name not in KNOWN_DETAILS and current is not None:
        raise InvalidError(
            _("{name} is one of the GM's notes, hidden in the player view", name=name),
            hint=_gm_hint(),
        )
    was = _was(req, WAS_DETAILS)
    if was is None:
        return
    if not _same(was.get(name), current):
        raise _stale_value(now, ref, name, current, req.field("text"))


def check_set(req: Request, ref: str, key: str, *, absolute: bool) -> None:
    """A field or sheet value. `absolute` is `key=value` or removing it; `+=`/`-=` add up, so
    they're only checked for hidden fields."""
    now = _now(req, ref)
    current_fields, current_values = flat_fields(now), _dict(now.get("values"))
    if not req.gm:
        hidden = set(current_fields) | set(current_values)
        hidden -= _player_keys(req, ref)
        if any(h == key or h.startswith(f"{key}.") for h in hidden):
            raise InvalidError(_("{key} is hidden in the player view", key=key), hint=_gm_hint())
    if not absolute:
        return
    fields, values = _was(req, WAS_FIELDS), _was(req, WAS_VALUES)
    for was, current in ((fields, current_fields), (values, current_values)):
        if was is not None and (key in was or key in current):
            if not _same(was.get(key), current.get(key)):
                raise _stale_value(now, ref, key, current.get(key), req.field("value"))
            return


def _stale_value(now: dict[str, JSON], ref: str, key: str, current: JSON, typed: str) -> StaleForm:
    name = _name(now, ref)
    if current is None:
        message = _("{name}'s {key} changed since you opened this page: gone", name=name, key=key)
    else:
        message = _(
            "{name}'s {key} changed since you opened this page: now “{value}”",
            name=name,
            key=key,
            value=_text(current),
        )
    if typed.strip():
        hint = _(
            "you typed “{typed}”: the page shows the new value now; save again if you still "
            "want yours",
            typed=typed.strip(),
        )
    else:
        hint = _("the page shows the new value now; save again if you still want yours")
    return StaleForm(message, hint=hint)


def _now(req: Request, ref: str) -> dict[str, JSON]:
    """The record as it is now, all of it (the GM's view)."""
    ran = req.app.run(["show", ref, "--gm"])
    if not ran.ok:
        raise ran.error or InvalidError(_("can't read {ref}", ref=ref), hint=_("reload the page"))
    return dict(ran.data)


def _player_keys(req: Request, ref: str) -> set[str]:
    """The field and sheet keys the player view shows (a secret record shows none)."""
    ran = req.app.run(["show", ref])
    if not ran.ok:
        raise ran.error or InvalidError(_("can't read {ref}", ref=ref), hint=_("reload the page"))
    if ran.data.get("hidden") is True:
        raise InvalidError(_("{ref} is secret in the player view", ref=ref), hint=_gm_hint())
    return set(flat_fields(dict(ran.data))) | set(_dict(ran.data.get("values")))


def _gm_hint() -> str:
    return _("turn on the GM view (the GM button in the header) to change it")


def _was(req: Request, name: str) -> dict[str, JSON] | None:
    """A snapshot the form carries, or None for a form without one."""
    raw = req.field(name)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _same(a: JSON, b: JSON) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def _text(value: JSON) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _name(now: dict[str, JSON], ref: str) -> str:
    return str(now.get("name") or ref)


def _dict(value: JSON) -> dict[str, JSON]:
    return value if isinstance(value, dict) else {}


def _list(value: JSON) -> list[JSON]:
    return value if isinstance(value, list) else []
