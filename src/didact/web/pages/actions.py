"""The two POST endpoints: `/run` runs one command, `/gm` switches the GM view.

`/run` turns a form into an argument list (never a shell string), runs it through
`App.run`, keeps the outcome for the next page, and redirects there (POST, redirect, GET):
reloading a page never runs a command twice. Forms say how to build the list with the
`action` field:

- `words`: `w` fields in order are the command line; `o:--flag` fields add `--flag value`
  when filled in, and `f:--flag` fields add `--flag` when checked;
- `command`: a generated command form (`cmd` names it, `a.<param>` fields fill it);
- `line`: a whole command line typed in a box (split like a shell would);
- `set`, `edit`, `new`, `about`, `do`: the record page's and the reference page's forms;
- `options`, `remind`: the Settings page's options, and the Status page's reminders.
"""

import json
import shlex
from collections.abc import Callable

from didact.commands.registry import REGISTRY
from didact.core.errors import DidactError, UsageError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.web import safe
from didact.web.app import Flash, Ran, Request, Response
from didact.web.forms import (
    command_argv,
    lines,
    option,
    rule_argv,
    rule_params,
    split_tags,
    text_block,
)
from didact.web.html import record_url

type Builder = Callable[[Request], list[str]]


def run(req: Request) -> Response:
    """Run the command a form stands for, then go back (or on) with its outcome."""
    action = req.field("action", "words")
    builder = BUILDERS.get(action)
    try:
        if builder is None:
            raise UsageError(
                _("unknown form action {action}", action=repr(action)), hint=_("reload the page")
            )
        argv = builder(req)
    except DidactError as err:
        ran = Ran.failed([], err)
    else:
        ran = req.app.run(argv)
    values = {k: v for k, v in req.form.items() if k != "csrf"}
    key = req.app.remember(Flash(ran, panel=req.field("show") == "panel", values=values))
    target = safe_path(req.field("next"))
    if ran.ok and req.field("next_ok"):
        wanted = req.field("next_ok")
        created = ran.data.get("id")
        if wanted == "@record":
            if isinstance(created, str) and not ran.data.get("dry_run"):
                target = record_url(created)
        else:
            target = safe_path(wanted)
    joiner = "&" if "?" in target else "?"
    fragment = ""
    if "#" in target:
        target, _sep, fragment = target.partition("#")
        fragment = f"#{fragment}"
    return Response.redirect(f"{target}{joiner}flash={key}{fragment}")


def gm(req: Request) -> Response:
    """Switch the GM view on or off (a cookie), then go back."""
    on = req.field("on") == "1"
    cookie = f"{req.app.gm_cookie}={'1' if on else '0'}; Path=/; HttpOnly; SameSite=Strict"
    response = Response.redirect(safe_path(req.field("next")))
    response.headers.append(("Set-Cookie", cookie))
    return response


def safe_path(target: str) -> str:
    """Only paths on this site: never another site, never a scheme."""
    if not target.startswith("/") or target.startswith("//") or any(c in target for c in "\\\r\n"):
        return "/"
    return target


# ---------------------------------------------------------------------------- builders


def _words(req: Request) -> list[str]:
    argv = [word.strip() for word in req.fields("w") if word.strip()]
    for name, values in req.form.items():
        if name.startswith("o:"):
            for value in values:
                if value.strip():
                    argv += option(name[2:], value.strip())
        elif name.startswith("f:") and any(values):
            argv.append(name[2:])
    return argv


def _command(req: Request) -> list[str]:
    name = req.field("cmd")
    spec = REGISTRY.get(name)
    if spec is None:
        raise UsageError(_("no command {name}", name=repr(name)), hint=_("see the Commands page"))
    return command_argv(spec, req.form)


def _line(req: Request) -> list[str]:
    text = req.field("line").strip()
    try:
        words = shlex.split(text)
    except ValueError as exc:
        raise UsageError(
            _("can't read that command line: {error}", error=exc), hint=_("check its quotes")
        ) from exc
    if words[:1] == ["$"]:  # pasted from a result, prompt and all
        words = words[1:]
    if words[:1] == ["didact"]:
        words = words[1:]
    if not words:
        raise UsageError(_("type a command first"), hint=_("e.g. `roll 2d6` or `help`"))
    return words


def _set(req: Request) -> list[str]:
    ref = req.field("ref")
    assignment = req.field("assignment").strip()
    if assignment:
        assigned = _assigned(assignment)
        if assigned is not None:
            safe.check_set(req, ref, assigned[0], absolute=assigned[1])
        return ["set", ref, assignment]
    key = req.field("key").strip()
    if not key:
        raise UsageError(_("a change needs a field name"), hint=_("e.g. `mood` or `hp`"))
    if req.field("unset"):
        safe.check_set(req, ref, key, absolute=True)
        return ["set", ref, "--unset", key]
    op = req.field("op", "=")
    if op not in ("=", "+=", "-="):
        op = "="
    safe.check_set(req, ref, key, absolute=op == "=")
    return ["set", ref, f"{key}{op}{req.field('value').strip()}"]


def _assigned(text: str) -> tuple[str, bool] | None:
    """The key an assignment typed as `key=value` changes (as the page names it), and whether
    it replaces the value (`=`) rather than adding to it."""
    from didact.services.assign import parse_assignment

    try:
        found = parse_assignment(text)
    except DidactError:
        return None  # the command itself says what's wrong
    path = found.path
    if path[0] == "mechanics":
        path = path[2:]
    elif path[0] in ("fields", "extra"):
        path = path[1:]
    return ".".join(path), found.op == "="


def _edit(req: Request) -> list[str]:
    """Only what changed: name, tags, aliases, body."""
    changes: dict[str, JSON] = {}
    if "name" in req.form:
        name = req.field("name").strip()
        if name and name != req.field("was.name"):
            changes["name"] = name
    for key in ("tags", "aliases"):
        if key in req.form:
            now = split_tags(req.field(key))
            if now != split_tags(req.field(f"was.{key}")):
                changes[key] = list[JSON](now)
    if "body" in req.form:
        body = text_block(req.field("body"))
        if body.strip() != text_block(req.field("was.body")).strip():
            changes["body"] = body.strip() + "\n" if body.strip() else ""
    if not changes:
        raise UsageError(_("nothing changed"), hint=_("change a value, then save"))
    safe.check_edit(req, req.field("ref"), changes)
    return ["edit", req.field("ref"), "--data", json.dumps(changes, ensure_ascii=False)]


def _new(req: Request) -> list[str]:
    argv = ["new", req.field("type").strip(), req.field("name").strip()]
    for tag in split_tags(req.field("tags")):
        argv += option("--tag", tag)
    body = text_block(req.field("body")).strip()
    if body:
        argv += option("--body", body)
    for line in lines(req.field("fields")):
        argv += option("--set", line)
    if req.field("secret"):
        argv += ["--set", "knowledge=secret"]
    scope = req.field("scope").strip()
    if scope:
        argv += ["--scope", scope]
    if req.field("fill"):
        argv.append("--fill")
    if req.field("dry_run"):
        argv.append("--dry-run")
    return argv


def _about(req: Request) -> list[str]:
    name = req.field("name").strip()
    if not name:
        raise UsageError(_("a detail needs a name"), hint=_("e.g. looks, wants or plan"))
    safe.check_detail(req, req.field("ref"), name)
    return ["about", req.field("ref"), f"{name}={req.field('text').strip()}"]


def _options(req: Request) -> list[str]:
    """The campaign's options as the Settings page shows them: only what changed is saved (an
    option left at "default" keeps following its default, or what another option implies)."""
    changes = [
        f"{name[4:]}={value}"
        for name, value in ((n, req.field(n)) for n in req.form if n.startswith("opt."))
        if value != req.field(f"was.{name[4:]}")
    ]
    if not changes:
        raise UsageError(_("nothing changed"), hint=_("change a value, then save"))
    return ["campaign", "profile", *changes]


def _remind(req: Request) -> list[str]:
    """A reminder from the Status page: its text, and when (once after a while, or every so
    often), as a number and a unit."""
    text = req.field("text").strip()
    amount, unit = req.field("amount").strip(), req.field("unit").strip()
    if not text:
        raise UsageError(_("say what the reminder is"), hint=_("e.g. Eat a ration"))
    if not amount or not unit:
        raise UsageError(_("say how long from now"), hint=_("e.g. 1 day"))
    flag = "--every" if req.field("when") == "every" else "--in"
    said = ["--", text] if text.startswith("-") else [text]
    return ["remind", *option(flag, f"{amount} {unit}"), *said]


def _do(req: Request) -> list[str]:
    rule = req.field("rule")
    shown = req.app.run(["rules", "show", rule])
    if not shown.ok:
        raise shown.error or UsageError(_("no rule {rule}", rule=repr(rule)))
    data = shown.data.get("data")
    rule_id = str(shown.data.get("id") or rule)
    params = rule_params(rule_id, data if isinstance(data, dict) else {})
    return rule_argv(rule_id, params, req.form)


BUILDERS: dict[str, Builder] = {
    "words": _words,
    "command": _command,
    "line": _line,
    "set": _set,
    "edit": _edit,
    "new": _new,
    "about": _about,
    "do": _do,
    "options": _options,
    "remind": _remind,
}
