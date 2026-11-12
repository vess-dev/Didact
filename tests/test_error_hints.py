"""Every error Didact raises says how to fix it (`hint=`). A sweep over the source: a new
`raise` without a hint fails here, rather than leaving a player, or an LLM, stuck."""

import ast
from pathlib import Path

ERRORS = frozenset(
    {"DidactError", "UsageError", "NotFoundError", "InvalidError", "ConflictError", "StaleForm"}
)
SOURCE = Path(__file__).resolve().parents[1] / "src" / "didact"


def _hintless() -> list[str]:
    found: list[str] = []
    for path in sorted(SOURCE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                continue
            func = node.exc.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            named = {k.arg for k in node.exc.keywords}
            if name in ERRORS and "hint" not in named and None not in named:  # None: **kwargs
                found.append(f"{path.relative_to(SOURCE.parent)}:{node.lineno} {name}")
    return found


def test_every_error_says_how_to_fix_it() -> None:
    missing = _hintless()
    assert not missing, "give these a hint=… saying how to fix it:\n" + "\n".join(missing)
