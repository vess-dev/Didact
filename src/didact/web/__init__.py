"""The browser app behind `didact serve`: browse and edit the library, and run any command.

A top layer like `cli` and `mcp`: nothing imports it. Pages read through commands (or the
services, where a command is too coarse), and every change runs a real `didact` command
line through `didact.cli.main.execute`, so validation, the event log, undo, hooks and turn
groups apply exactly as on the command line. Standard library HTTP, HTML built in Python,
and plain CSS and JavaScript from `static/`.
"""

from didact.web.server import serve

__all__ = ["serve"]
