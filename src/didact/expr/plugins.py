"""The plugin API: pack code adds dice modifiers (and dice, functions, macros, chains).

    from didact.expr import DiePool, RollContext, modifier

    @modifier("purr", token="~")
    def purr(pool: DiePool, ctx: RollContext, arg: int | None) -> DiePool:
        ...

A plugin module may also define `register(registry)` to add named dice, functions, macros or
dice chains. Everything a pack registers is namespaced by the pack: `lucky.charm`.
"""

import importlib.util
import sys
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path
from typing import cast

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.expr.model import ArgKind, ModifierFunc, ModifierSpec, Registry

PLUGIN_ORDER = 80
_ATTRIBUTE = "__didact_modifier__"


def modifier[F: Callable[..., object]](
    name: str,
    *,
    token: str,
    aliases: Sequence[str] = (),
    arg: ArgKind = "none",
    order: int = PLUGIN_ORDER,
    summary: str = "",
    default: int | None = None,
    groups: bool = False,
) -> Callable[[F], F]:
    """Declare a dice modifier. It is registered when its pack is loaded."""

    def decorate(func: F) -> F:
        doc = (func.__doc__ or "").strip()
        spec = ModifierSpec(
            name=name,
            tokens=(token, *aliases),
            order=order,
            arg=arg,
            apply=cast(ModifierFunc, func),
            summary=summary or doc.split("\n", 1)[0],
            default_arg=default,
            groups=groups,
        )
        setattr(func, _ATTRIBUTE, spec)
        return func

    return decorate


def load_plugin(path: Path, registry: Registry, *, namespace: str) -> list[str]:
    """Import a pack's plugin file and register what it declares; returns the names added."""
    module_name = f"didact_plugins.{namespace}.{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise InvalidError(
            _("can't load plugin {path}", path=path), hint=_("plugins are .py files")
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        raise InvalidError(
            _("plugin {name} failed to load: {error}", name=path.name, error=exc),
            where=str(path),
            hint=_("fix the plugin code"),
        ) from exc
    added: list[str] = []
    for value in vars(module).values():
        declared = getattr(value, _ATTRIBUTE, None)
        if isinstance(declared, ModifierSpec):
            named = replace(declared, name=f"{namespace}.{declared.name}")
            try:
                registry.add_modifier(named)
            except ValueError as exc:
                raise InvalidError(
                    _("plugin {name}: {error}", name=path.name, error=exc),
                    where=str(path),
                    hint=_("choose another token"),
                ) from exc
            added.append(named.name)
    register = getattr(module, "register", None)
    if callable(register):
        before = _names(registry)
        register(registry)
        added.extend(sorted(_names(registry) - before))
    return added


def _names(registry: Registry) -> set[str]:
    return {
        *registry.modifiers,
        *(f"d[{d}]" for d in registry.dice),
        *registry.functions,
        *registry.macros,
        *(f"chain:{c}" for c in registry.chains),
    }
