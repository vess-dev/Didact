"""The `didact` command line, generated from the command registry.

Results go to stdout, errors to stderr; the exit code is 0 (ok), 1 (error) or 2 (usage).
Global options (--format, --detail, --home) work before or after the command words.
"""

import argparse
import contextlib
import io
import json
import shlex
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any, NoReturn, TextIO, cast

from didact import __version__
from didact.commands import load_all
from didact.commands.registry import REGISTRY, CommandSpec, Param
from didact.core import i18n
from didact.core.config import resolve_config
from didact.core.context import Context
from didact.core.errors import DidactError, UsageError
from didact.core.i18n import N_, N_plural, _, translate
from didact.core.output import JSON, Detail, Format, Out

FORMATS: tuple[Format, ...] = ("md", "yaml", "json")
DETAILS: tuple[Detail, ...] = ("brief", "full")


# argparse's own words, which it looks up with gettext: ours translate them. Its messages fill in
# `%s` and `%(name)s` afterwards, so a translation keeps those exactly.
ARGPARSE_WORDS = (
    N_("usage: "),
    N_("positional arguments"),
    N_("options"),
    N_("show this help message and exit"),
    N_("subcommands"),
    N_("%(heading)s:"),
    # its errors, which become ours (`_Parser.error`)
    N_("argument %(argument_name)s: %(message)s"),
    N_("invalid choice: %(value)r (choose from %(choices)s)"),
    N_("invalid choice: %(value)r, maybe you meant %(closest)r? (choose from %(choices)s)"),
    N_("unrecognized arguments: %s"),
    N_("ambiguous option: %(option)s could match %(matches)s"),
    N_("expected one argument"),
    N_("expected at most one argument"),
    N_("expected at least one argument"),
    N_("invalid %(type)s value: %(value)r"),
    N_("the following arguments are required: %s"),
    N_("one of the arguments %s is required"),
    N_("not allowed with argument %s"),
    N_("unexpected option string: %s"),
    N_("ignored explicit argument %r"),
    N_plural("expected %s argument", "expected %s arguments"),
)
argparse._ = translate  # type: ignore[attr-defined]  # argparse calls `_` for these
argparse.ngettext = i18n.translate_plural  # type: ignore[attr-defined]  # and `ngettext`


class _Parser(argparse.ArgumentParser):
    """argparse that raises instead of exiting, so every error looks the same."""

    def error(self, message: str) -> NoReturn:
        words = self.prog.split()[1:]
        target = f"`didact help {' '.join(words)}`" if words else "`didact commands`"
        raise UsageError(message, hint=_("see {target}", target=target), where=self.prog)


def _parser_kwargs() -> dict[str, Any]:
    return {
        "formatter_class": argparse.RawDescriptionHelpFormatter,
        "allow_abbrev": False,
        "suggest_on_error": True,
        "color": False,
    }


def _common_options(*, root: bool) -> argparse.ArgumentParser:
    """Global options. Sub-parsers use SUPPRESS so they never clobber values given earlier."""

    def default(value: object) -> object:
        return value if root else argparse.SUPPRESS

    common = _Parser(add_help=False, **_parser_kwargs())
    common.add_argument(
        "--format", choices=FORMATS, default=default("md"), help=_("output format (default: md)")
    )
    common.add_argument(
        "--detail",
        choices=DETAILS,
        default=default("brief"),
        help=_("how much to show (default: brief)"),
    )
    common.add_argument(
        "--home",
        metavar="<path>",
        default=default(None),
        help=_("data home (default: $DIDACT_HOME or ~/Documents/DidactLibrary)"),
    )
    common.add_argument(
        "--world", metavar="<id>", default=default(None), help=_("use this world for this call")
    )
    common.add_argument(
        "--campaign",
        metavar="<id>",
        default=default(None),
        help=_("use this campaign for this call"),
    )
    return common


_BUILT: dict[tuple[int, str], argparse.ArgumentParser] = {}


def cached_parser() -> argparse.ArgumentParser:
    """The parser, built once per set of commands (building it takes tens of milliseconds, which
    adds up when the web app or MCP run several commands in one request)."""
    key = (len(REGISTRY), i18n.current().code)  # its help is in the language in use
    if key not in _BUILT:
        _BUILT[key] = build_parser()
    return _BUILT[key]


def build_parser() -> argparse.ArgumentParser:
    """Build the full argument parser from the registry."""
    root = _Parser(
        prog="didact",
        description=_("Didact: rules engine, dice, oracles and memory for LLM-run solo TTRPGs."),
        epilog=_(
            "Run `didact commands` for the command list, `didact help <command>` for details."
        ),
        parents=[_common_options(root=True)],
        **_parser_kwargs(),
    )
    root.add_argument("--version", action="store_true", help=_("print the version and exit"))
    root.set_defaults(_spec=None, _group=())

    common = _common_options(root=False)
    parsers: dict[tuple[str, ...], argparse.ArgumentParser] = {(): root}
    actions: dict[tuple[str, ...], Any] = {}

    def subparsers_of(key: tuple[str, ...]) -> Any:
        if key not in actions:
            actions[key] = parsers[key].add_subparsers(title=_("commands"), metavar="<command>")
        return actions[key]

    for spec in sorted(REGISTRY.values(), key=lambda s: s.name):
        words = spec.words
        for depth in range(1, len(words)):
            prefix = words[:depth]
            if prefix in parsers:
                if parsers[prefix].get_default("_spec") is not None:
                    raise RuntimeError(f"command {' '.join(prefix)!r} is also a command group")
                continue
            group = subparsers_of(prefix[:-1]).add_parser(
                prefix[-1],
                help=_("{group} commands", group=" ".join(prefix)),
                parents=[common],
                **_parser_kwargs(),
            )
            group.set_defaults(_spec=None, _group=prefix)
            parsers[prefix] = group
        if words in parsers:
            raise RuntimeError(f"command {spec.name!r} clashes with a command group")
        cmd = subparsers_of(words[:-1]).add_parser(
            words[-1],
            help=translate(spec.summary),
            description=translate(spec.description),
            epilog=_examples_epilog(spec),
            parents=[common],
            **_parser_kwargs(),
        )
        _add_params(cmd, spec)
        cmd.set_defaults(_spec=spec, _group=words)
        parsers[words] = cmd
    return root


def _examples_epilog(spec: CommandSpec) -> str | None:
    if not spec.examples:
        return None
    return _("examples:") + "\n" + "\n".join(f"  {example}" for example in spec.examples)


def _converter(param: Param) -> Callable[[str], object]:
    if param.base is bool:
        return _parse_bool
    return cast(Callable[[str], object], param.base)


def _parse_bool(text: str) -> bool:
    lowered = text.strip().lower()
    if lowered in {"true", "yes", "y", "1", "on"}:
        return True
    if lowered in {"false", "no", "n", "0", "off"}:
        return False
    raise argparse.ArgumentTypeError(_("expected true/false, got {text}", text=repr(text)))


def _add_params(cmd: argparse.ArgumentParser, spec: CommandSpec) -> None:
    for p in spec.params:
        match p.kind:
            case "positional":
                cmd.add_argument(
                    p.name,
                    metavar=p.metavar,
                    help=translate(p.help),
                    type=_converter(p),
                    choices=p.choices,
                    nargs=None if p.required else "?",
                    default=p.default,
                )
            case "variadic":
                cmd.add_argument(
                    p.name,
                    metavar=p.metavar,
                    help=translate(p.help),
                    type=_converter(p),
                    choices=p.choices,
                    nargs="*",
                )
            case "flag":
                cmd.add_argument(p.flag, dest=p.name, action="store_true", help=translate(p.help))
            case "option":
                cmd.add_argument(
                    p.flag,
                    dest=p.name,
                    metavar=p.metavar,
                    help=translate(p.help),
                    type=_converter(p),
                    choices=p.choices,
                    required=p.required,
                    action="append" if p.multiple else "store",
                    default=None if p.multiple else p.default,
                )
    if spec.writes:
        cmd.add_argument(
            "--dry-run", action="store_true", help=_("show what would change without writing")
        )
        cmd.add_argument("--reason", metavar="<text>", help=_("why; recorded in the log"))


def _noticed(out: Out, ctx: Context) -> Out:
    """The result with what opening the library found out on the way (a crash cleared up)."""
    if not ctx.notices:
        return out
    lines = "\n".join(_("note: {note}", note=n) for n in ctx.notices)
    return replace(
        out,
        data={**out.data, "notices": list[JSON](ctx.notices)},
        md=f"{lines}\n{out.md}",
        md_full=None if out.md_full is None else f"{lines}\n{out.md_full}",
    )


def _invoke(spec: CommandSpec, ctx: Context, ns: argparse.Namespace) -> Out:
    args: list[object] = []
    kwargs: dict[str, object] = {}
    for p in spec.params:
        value = getattr(ns, p.name)
        match p.kind:
            case "positional":
                args.append(value)
            case "variadic":
                args.extend(value or [])
            case "option" if p.multiple:
                kwargs[p.name] = value or []
            case _:
                kwargs[p.name] = value
    return spec.func(ctx, *args, **kwargs)


def _peek_format(argv: Sequence[str]) -> Format:
    """Find --format early, so even argument errors come out in the requested format."""
    for i, arg in enumerate(argv):
        value = None
        if arg == "--format" and i + 1 < len(argv):
            value = argv[i + 1]
        elif arg.startswith("--format="):
            value = arg.split("=", 1)[1]
        if value in FORMATS:
            return value
    return "md"


def _write(text: str, stream: TextIO | None = None) -> None:
    if not text.strip():
        return  # silent (e.g. `capture --hook`): not even a blank line
    target = sys.stdout if stream is None else stream
    target.write(text.rstrip("\n") + "\n")


def emit(out: Out, fmt: Format, detail: Detail) -> None:
    """Render a result in the requested format."""
    match fmt:
        case "json":
            _write(json.dumps(out.data, ensure_ascii=False, indent=2))
        case "yaml":
            from didact.core.yamlio import dump_yaml

            _write(dump_yaml(out.data))
        case "md":
            _write(out.markdown(detail))


def emit_error(err: DidactError, fmt: Format) -> None:
    if fmt == "json":
        _write(json.dumps({"error": err.to_data()}, ensure_ascii=False, indent=2), sys.stderr)
        return
    lines = [_("error ({code}): {message}", code=err.code, message=err.message)]
    if err.where:
        lines.append(_("where: {where}", where=err.where))
    if err.hint:
        lines.append(_("fix: {hint}", hint=err.hint))
    _write("\n".join(lines), sys.stderr)


@dataclass(frozen=True, slots=True)
class Result:
    """One command's outcome: its output or its error, and how to render it."""

    code: int
    out: Out | None
    error: DidactError | None
    format: Format
    detail: Detail

    def text(self) -> str:
        """The result as the command line would print it (errors included)."""
        buffer = io.StringIO()
        if self.error is not None:
            with contextlib.redirect_stderr(buffer):
                emit_error(self.error, self.format)
        elif self.out is not None:
            with contextlib.redirect_stdout(buffer):
                emit(self.out, self.format, self.detail)
        return buffer.getvalue()


def execute(argv: Sequence[str]) -> Result:
    """Run one command line (without `didact`) and return its result unprinted.
    `--help` still prints and raises SystemExit, as argparse does."""
    args = list(argv)
    fmt = _peek_format(args)
    try:
        load_all()
        ns = cached_parser().parse_args(args)
        if ns.version:
            return Result(
                0,
                Out(data={"version": __version__}, md=f"didact {__version__}"),
                None,
                fmt,
                "brief",
            )
        ctx = Context(
            config=resolve_config(home=ns.home),
            format=ns.format,
            detail=ns.detail,
            dry_run=getattr(ns, "dry_run", False),
            reason=getattr(ns, "reason", None),
            world=ns.world,
            campaign=ns.campaign,
            command_line=shlex.join(["didact", *args]),
        )
        spec: CommandSpec | None = ns._spec
        if spec is None:
            from didact.commands.meta import overview

            out = overview(ns._group)
        elif spec.name == "batch":
            out = _batch(ns)
        elif spec.name == "serve":
            out = _serve(ns)
        elif spec.name == "sample":
            out = _sample(ctx, ns)
        else:
            out = _invoke(spec, ctx, ns)
        return Result(0 if out.ok else 1, _noticed(out, ctx), None, ctx.format, ctx.detail)
    except DidactError as err:
        return Result(err.exit_code, None, err, fmt, "brief")
    except BrokenPipeError:  # the reader went away: `_main` knows what to do
        raise
    except OSError as exc:  # the disk refused, in a command that had nothing better to say
        from didact.store.fsutil import storage_error

        refused = storage_error(exc)
        return Result(refused.exit_code, None, refused, fmt, "brief")


INHERITED = ("--home", "--world", "--campaign", "--detail")  # batch passes these on


def _batch(ns: argparse.Namespace) -> Out:
    """Run commands one per line (stdin or --file); stop at the first failure unless told."""
    from pathlib import Path

    text = Path(ns.file).read_text(encoding="utf-8") if ns.file else sys.stdin.read()
    passed: list[str] = []
    for flag in INHERITED:
        value = getattr(ns, flag.lstrip("-"), None)
        if value is not None and not (flag == "--detail" and value == "brief"):
            passed += [flag, str(value)]
    shown: list[str] = []
    results: list[JSON] = []
    ok = True
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        words = shlex.split(line)
        if words[:1] == ["didact"]:
            words = words[1:]
        if words[:1] == ["batch"]:
            raise UsageError(
                _("a batch can't run another batch"), hint=_("put its lines in this one")
            )
        if words[:1] == ["serve"]:
            raise UsageError(
                _("a batch can't start the web app"), hint=_("run `didact serve` alone")
            )
        given = {w.split("=", 1)[0] for w in words if w.startswith("--")}
        extra = [
            x for i in range(0, len(passed), 2) if passed[i] not in given for x in passed[i : i + 2]
        ]
        result = execute([*words, *extra])
        command = shlex.join(words)
        shown.append(f"$ didact {command}\n{result.text().rstrip()}")
        entry: dict[str, JSON] = {"command": command, "code": result.code}
        if result.error is not None:
            entry["error"] = cast(JSON, result.error.to_data())
        elif result.out is not None:
            entry["data"] = result.out.data
        results.append(entry)
        if result.code != 0:
            ok = False
            if not ns.keep_going:
                shown.append(_("(stopped at the first failure; --keep-going carries on)"))
                break
    return Out(
        data={"results": results, "ok": ok}, md="\n\n".join(shown) or _("nothing to run"), ok=ok
    )


def _sample(ctx: Context, ns: argparse.Namespace) -> Out:
    """Build the sample campaign into the library (`didact.cli.sample`)."""
    from didact.cli.sample import build

    built = build(ctx.config.home, system=ns.system)
    return Out(data=built.to_data(), md=built.text())


def _serve(ns: argparse.Namespace) -> Out:
    """Run the web app until Ctrl-C; the work is in `didact.web`."""
    from didact.web import serve

    def say(text: str, stream: TextIO = sys.stdout) -> None:
        stream.write(text.rstrip("\n") + "\n")
        stream.flush()

    home = ns.home
    if ns.demo:
        from didact.cli.sample import fresh_demo

        if ns.home:
            raise UsageError(_("--demo serves a library of its own"), hint=_("leave out --home"))
        built = fresh_demo(say)
        home = str(built.home)
        say(
            _(
                "the sample campaign, on {system}, in {home} (rebuilt each time --demo starts)",
                system=built.system,
                home=home,
            )
        )
    serve(
        home=home,
        world=ns.world,
        campaign=ns.campaign,
        host=ns.host,
        port=ns.port,
        open_browser=ns.open_,
        gm=ns.gm,
        say=say,
        report=lambda text: say(text, sys.stderr),
    )
    return Out(data={"stopped": True}, md=_("didact serve stopped"))


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the `didact` script. Returns the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    with i18n.use(i18n.command_line_language()):
        return _main(args)


def _main(args: list[str]) -> int:
    try:
        result = execute(args)
        if result.error is not None:
            emit_error(result.error, result.format)
        elif result.out is not None:
            emit(result.out, result.format, result.detail)
        return result.code
    except SystemExit as exc:  # argparse's own --help
        return exc.code if isinstance(exc.code, int) else 0
    except BrokenPipeError:  # e.g. `didact commands | head`
        return 0
