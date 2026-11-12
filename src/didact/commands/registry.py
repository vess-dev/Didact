"""The typed command registry: the single source for the CLI and, later, MCP.

A command is a plain function registered with `@command`. Its first parameter is the
`Context`; every other parameter becomes an argument:

- positional parameters → positional arguments (optional when they have a default)
- `*args` → any number of trailing positional arguments
- keyword-only parameters → `--options`; `bool` ones are flags; `list[...]` ones repeat
- a trailing underscore is dropped (`as_` → `--as`), other underscores become dashes
- `Annotated[T, "help text"]` documents a parameter; `Literal[...]` becomes a choice list
- `Annotated[T, "help", Metavar("record")]` shows `--as <record>` instead of `--as <as>`

Supported value types: str, int, float, bool, Literal[...], optional (`| None`) and list[...].
"""

import annotationlib
import inspect
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from types import NoneType, UnionType
from typing import Annotated, Any, Literal, TypeAliasType, Union, get_args, get_origin

from didact.core.output import Out

type ParamKind = Literal["positional", "variadic", "option", "flag"]
type CommandFunc = Callable[..., Out]

_EMPTY = inspect.Parameter.empty


@dataclass(frozen=True, slots=True)
class Metavar:
    """How an argument's value is named in usage lines: `Metavar("record")` → `<record>`."""

    name: str


@dataclass(frozen=True, slots=True)
class Param:
    """One argument of a command, derived from the function signature."""

    name: str  # the Python parameter name
    cli_name: str  # how it is spelled on the command line (without dashes)
    kind: ParamKind
    base: type  # str, int, float or bool
    help: str
    required: bool
    default: object
    choices: tuple[str, ...] | None
    multiple: bool
    value_name: str | None = None  # from Metavar; defaults to the cli name

    @property
    def flag(self) -> str:
        return f"--{self.cli_name}"

    @property
    def metavar(self) -> str:
        return f"<{self.value_name or self.cli_name}>"


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """A registered command: name, docs, parameters and the function to call."""

    name: str  # e.g. "roll" or "world new"
    func: CommandFunc
    summary: str
    description: str
    examples: tuple[str, ...]
    writes: bool  # mutates state → also accepts --dry-run and --reason
    params: tuple[Param, ...]

    @property
    def words(self) -> tuple[str, ...]:
        return tuple(self.name.split())

    def usage(self) -> str:
        """A one-line usage string, e.g. `didact world new <id> [--system <system>]`."""
        parts = ["didact", *self.words]
        for p in self.params:
            match p.kind:
                case "positional":
                    parts.append(p.metavar if p.required else f"[{p.metavar}]")
                case "variadic":
                    parts.append(f"[{p.metavar} ...]")
                case "flag":
                    parts.append(f"[{p.flag}]")
                case "option":
                    item = f"{p.flag} {p.metavar}"
                    if p.multiple:
                        item += " ..."
                    parts.append(item if p.required else f"[{item}]")
        if self.writes:
            parts.extend(["[--dry-run]", "[--reason <text>]"])
        return " ".join(parts)


REGISTRY: dict[str, CommandSpec] = {}
# Options every command has already (see cli.main); a parameter can't reuse these names.
GLOBAL_OPTIONS = frozenset(
    {"format", "detail", "home", "world", "campaign", "dry-run", "reason", "help", "version"}
)


def command[F: CommandFunc](
    name: str,
    *,
    summary: str,
    examples: Sequence[str] = (),
    writes: bool = False,
    description: str | None = None,
) -> Callable[[F], F]:
    """Register a function as a Didact command."""

    def decorate(func: F) -> F:
        if name in REGISTRY:
            raise RuntimeError(f"duplicate command {name!r}")
        REGISTRY[name] = CommandSpec(
            name=name,
            func=func,
            summary=summary,
            description=description or inspect.getdoc(func) or summary,
            examples=tuple(examples),
            writes=writes,
            params=params_of(func),
        )
        return func

    return decorate


def params_of(func: Callable[..., Any]) -> tuple[Param, ...]:
    """Derive the CLI parameters from a command function's signature."""
    signature = inspect.signature(func, annotation_format=annotationlib.Format.FORWARDREF)
    parameters = list(signature.parameters.values())
    if not parameters or parameters[0].name != "ctx":
        raise TypeError(f"{func.__qualname__}: the first parameter must be `ctx`")
    return tuple(_param(func, p) for p in parameters[1:])


def _param(func: Callable[..., Any], p: inspect.Parameter) -> Param:
    annotation, help_text, value_name = _unwrap_annotated(p.annotation)
    param = _build_param(func, p, annotation, help_text)
    return replace(param, value_name=value_name) if value_name else param


def _build_param(
    func: Callable[..., Any], p: inspect.Parameter, annotation: object, help_text: str
) -> Param:
    where = f"{func.__qualname__}({p.name})"
    if p.name.rstrip("_").replace("_", "-") in GLOBAL_OPTIONS:
        # an option would clash on the command line; any argument would clash in the parsed
        # namespace (a positional named `version` would read as `--version`)
        raise TypeError(f"{where}: {p.name.rstrip('_')} is a global option; choose another name")
    base, optional, choices, is_list = _analyze(annotation, where)
    cli_name = p.name.rstrip("_").replace("_", "-")
    has_default = p.default is not _EMPTY
    default = p.default if has_default else None

    match p.kind:
        case inspect.Parameter.VAR_POSITIONAL:
            return Param(p.name, cli_name, "variadic", base, help_text, False, (), choices, True)
        case inspect.Parameter.POSITIONAL_ONLY | inspect.Parameter.POSITIONAL_OR_KEYWORD:
            if is_list:
                raise TypeError(f"{where}: use *args instead of a list-typed positional parameter")
            required = not has_default and not optional
            return Param(
                p.name, cli_name, "positional", base, help_text, required, default, choices, False
            )
        case inspect.Parameter.KEYWORD_ONLY:
            if base is bool and not is_list:
                if default not in (None, False):
                    raise TypeError(f"{where}: bool options must default to False")
                return Param(p.name, cli_name, "flag", bool, help_text, False, False, None, False)
            required = not has_default
            fallback: object = [] if is_list and default is None else default
            return Param(
                p.name, cli_name, "option", base, help_text, required, fallback, choices, is_list
            )
        case _:
            raise TypeError(f"{where}: **kwargs parameters are not supported")


def _unwrap_annotated(annotation: object) -> tuple[object, str, str | None]:
    if get_origin(annotation) is Annotated:
        base, *metadata = get_args(annotation)
        help_text = next((m for m in metadata if isinstance(m, str)), "")
        value_name = next((m.name for m in metadata if isinstance(m, Metavar)), None)
        return base, help_text, value_name
    return annotation, "", None


def _analyze(annotation: object, where: str) -> tuple[type, bool, tuple[str, ...] | None, bool]:
    """Return (base type, optional?, choices, list?) for a parameter annotation."""
    if annotation is _EMPTY:
        raise TypeError(f"{where}: missing type annotation")
    if isinstance(annotation, TypeAliasType):  # `type Where = Literal[...]`
        annotation = annotation.__value__
    optional = False
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        args = get_args(annotation)
        rest = [a for a in args if a is not NoneType]
        if len(rest) != 1:
            raise TypeError(f"{where}: only `T | None` unions are supported")
        optional = len(rest) != len(args)
        annotation = rest[0]
        origin = get_origin(annotation)
    if origin is list:
        (inner,) = get_args(annotation)
        base, _, choices, _ = _analyze(inner, where)
        return base, optional, choices, True
    if origin is Literal:
        return str, optional, tuple(str(a) for a in get_args(annotation)), False
    if annotation in (str, int, float, bool):
        assert isinstance(annotation, type)
        return annotation, optional, None, False
    raise TypeError(f"{where}: unsupported parameter type {annotation!r}")
