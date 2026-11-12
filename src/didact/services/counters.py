"""Numbers that never repeat, even after an undo: oracle answers (#o), drafts (#g, #c)."""

import json
from collections.abc import Callable

from didact.core.output import JSON
from didact.store.fsutil import atomic_write
from didact.store.repo import Repo


def next_number(repo: Repo, key: str, floor: Callable[[], int] | None = None) -> int:
    """The next number for `key` in `log/counters.json`. If the counter is missing (a new or
    damaged file), `floor()` says the highest number already used, so none repeats."""
    path = repo.layout.counters_file
    with repo.writing():
        data: dict[str, JSON] = {}
        if path.is_file():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                data = loaded if isinstance(loaded, dict) else {}
            except ValueError:
                data = {}
        current = data.get(key)
        if not isinstance(current, int):
            current = floor() if floor is not None else 0
        number = current + 1
        data[key] = number
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, json.dumps(data))
    return number
