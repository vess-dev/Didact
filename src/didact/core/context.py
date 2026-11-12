"""The per-invocation context handed to every command."""

from dataclasses import dataclass, field

from didact.core.config import Config
from didact.core.output import Detail, Format


@dataclass(slots=True)
class Context:
    """Everything a command needs to know about how it was called."""

    config: Config
    format: Format = "md"
    detail: Detail = "brief"
    dry_run: bool = False
    reason: str | None = None
    world: str | None = None  # overrides the active world for this call
    campaign: str | None = None  # overrides the active campaign for this call
    command_line: str | None = None  # the invocation, recorded in the event log
    notices: list[str] = field(default_factory=list)  # shown with the result: a crash cleared up
