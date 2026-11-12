"""The web app's state, and its one door into Didact.

Every command, read or write, goes through `App.run`, which calls `didact.cli.main.execute`
exactly as the command line does, one at a time under a lock: the store isn't built for
concurrent writes, and this is a single-user app. Pages that need more than a command gives
(the whole-library graph) read through `App.repo`, under the same lock.
"""

import contextlib
import io
import json
import secrets
import shlex
import sys
import threading
import traceback
from collections import OrderedDict
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from urllib.parse import urlencode

from didact.cli.main import Result, execute
from didact.commands import load_all
from didact.commands.registry import REGISTRY, CommandSpec
from didact.core.config import Config, resolve_config
from didact.core.context import Context
from didact.core.errors import DidactError, UsageError
from didact.core.i18n import _
from didact.core.output import JSON, Out
from didact.store.repo import Repo

REFUSED = ("batch", "serve")  # commands that make no sense from a browser
SWITCHERS = ("world use", "campaign open", "campaign close", "world new", "campaign new")
REPLACERS = ("world delete", "campaign delete", "snapshot", "reset")  # with --yes: it may go
VALUED_GLOBALS = ("--format", "--detail", "--home", "--world", "--campaign")
FLASH_LIMIT = 64


def spec_for(argv: Sequence[str]) -> CommandSpec | None:
    """The command an argument list runs (the longest registered prefix of its words)."""
    words: list[str] = []
    skip = False
    for arg in argv:
        if skip:
            skip = False
            continue
        if arg in VALUED_GLOBALS:
            skip = True
            continue
        if arg.startswith("-"):
            if words:
                break
            continue
        words.append(arg)
    for size in range(len(words), 0, -1):
        spec = REGISTRY.get(" ".join(words[:size]))
        if spec is not None:
            return spec
    return None


def supports(argv: Sequence[str], param: str) -> bool:
    spec = spec_for(argv)
    return spec is not None and any(p.name == param for p in spec.params)


@dataclass(frozen=True, slots=True)
class Ran:
    """One command run from the browser: what was asked, and what came back."""

    argv: tuple[str, ...]
    result: Result

    @classmethod
    def failed(cls, argv: Sequence[str], error: DidactError) -> Ran:
        return cls(tuple(argv), Result(error.exit_code, None, error, "md", "brief"))

    @property
    def line(self) -> str:
        """The same command as you'd type it."""
        return shlex.join(["didact", *self.argv]) if self.argv else "didact"

    @property
    def ok(self) -> bool:
        return self.result.code == 0

    @property
    def out(self) -> Out | None:
        return self.result.out

    @property
    def error(self) -> DidactError | None:
        return self.result.error

    @property
    def data(self) -> dict[str, JSON]:
        return self.result.out.data if self.result.out is not None else {}

    @property
    def md(self) -> str:
        """The output as Markdown (JSON or YAML, when asked for, as a code block)."""
        out = self.result.out
        if out is None:
            return ""
        if self.result.format != "md":
            return f"```\n{self.result.text().rstrip()}\n```"
        return out.markdown(self.result.detail)

    @property
    def undo_target(self) -> str | None:
        """What `undo --event` takes back this run's change (a roll `r7` or a change `e12`)."""
        spec = spec_for(self.argv)
        if not self.ok or spec is None or not spec.writes or spec.name in ("undo", "redo"):
            return None
        data = self.data
        if data.get("dry_run") or data.get("staged"):
            return None
        roll, label, event = data.get("roll"), data.get("label"), data.get("event")
        if isinstance(roll, int) and isinstance(label, str) and label.startswith("#r"):
            return f"r{roll}"
        if isinstance(event, int) and not isinstance(event, bool):
            return f"e{event}"
        return None


@dataclass(slots=True)
class Flash:
    """A run's outcome, kept for the page the browser is sent to next."""

    ran: Ran
    panel: bool = False  # a result panel on the page, rather than a toast
    values: dict[str, list[str]] = field(default_factory=dict)  # the form, to fill in again


class App:
    """What one `didact serve` knows: where the library is, the lock, the CSRF secret."""

    def __init__(
        self,
        *,
        home: str | None = None,
        world: str | None = None,
        campaign: str | None = None,
        gm: bool = False,
        report: Callable[[str], None] | None = None,
    ) -> None:
        load_all()
        self.home = home
        self.world = world
        self.campaign = campaign
        self.gm_default = gm
        self.config: Config = resolve_config(home=home)
        self.secret = secrets.token_urlsafe(32)
        self.port = 0
        self.lock = threading.RLock()
        self.report = report or (lambda text: None)  # where errors go (the terminal)
        self._flashes: OrderedDict[str, Flash] = OrderedDict()

    # ------------------------------------------------------------------ cookies

    @property
    def csrf_cookie(self) -> str:
        return f"didact_csrf_{self.port}"  # cookies ignore ports: two servers mustn't collide

    @property
    def gm_cookie(self) -> str:
        return f"didact_gm_{self.port}"

    # ------------------------------------------------------------------ running commands

    def globals(self) -> list[str]:
        """The global options `didact serve` was started with, passed on to every command."""
        given: list[str] = ["--home", str(self.config.home)] if self.home else []
        for flag, value in (("--world", self.world), ("--campaign", self.campaign)):
            if value:
                given += [flag, value]
        return given

    def run(self, argv: Sequence[str]) -> Ran:
        """Run one command line (a list, never a shell string) and keep its result."""
        words = [str(arg) for arg in argv]
        if words[:1] == ["didact"]:
            words = words[1:]
        spec = spec_for(words)
        if spec is not None and spec.name in REFUSED:
            refusal = UsageError(
                _("`didact {command}` doesn't run in the browser", command=spec.name),
                hint=_refusal_hint(spec.name),
            )
            return Ran.failed(words, refusal)
        words = _help_instead(words, spec)
        with self.lock:
            result = self._execute(words)
        ran = Ran(tuple(words), result)
        switched = spec is not None and spec.name in SWITCHERS
        replaced = spec is not None and spec.name in REPLACERS and "--yes" in words
        if spec is not None and spec.name == "snapshot":
            replaced = replaced and "--restore" in words
        if ran.ok and (switched or replaced) and not {"--dry-run", "--no-use"} & set(words):
            self.world = self.campaign = (
                None  # the browser chose, or it's gone: forget the override
            )
        return ran

    def _execute(self, words: list[str]) -> Result:
        printed = io.StringIO()
        try:
            with contextlib.redirect_stdout(printed), _no_stdin():
                return execute([*self.globals(), *words])
        except SystemExit:  # argparse printed help: show what it printed
            text = printed.getvalue().rstrip()
            return Result(0, Out(data={"text": text}, md=f"```\n{text}\n```"), None, "md", "brief")
        except Exception as exc:  # a bug: say so in the browser, the traceback in the terminal
            self.report(traceback.format_exc())
            error = DidactError(
                _("internal error: {error}", error=exc),
                hint=_("see the terminal running `didact serve`"),
            )
            return Result(1, None, error, "md", "brief")

    @contextlib.contextmanager
    def repo(self) -> Iterator[Repo]:
        """The library for direct reads (under the lock, like commands)."""
        with self.lock:
            repo = Repo.open(Context(config=self.config, world=self.world, campaign=self.campaign))
            try:
                yield repo
            finally:
                repo.close()

    def context(self) -> tuple[str | None, str | None]:
        """The active world's and campaign's names, for the sidebar."""
        with self.repo() as repo:
            try:
                world, campaign = repo.active_world(), repo.active_campaign()
            except DidactError:
                return None, None
        return (world.name if world else None), (campaign.name if campaign else None)

    # ------------------------------------------------------------------ flashes

    def remember(self, flash: Flash) -> str:
        key = secrets.token_urlsafe(9)
        with self.lock:
            self._flashes[key] = flash
            while len(self._flashes) > FLASH_LIMIT:
                self._flashes.popitem(last=False)
        return key

    def recall(self, key: str) -> Flash | None:
        with self.lock:
            return self._flashes.pop(key, None)


def _refusal_hint(name: str) -> str:
    if name == "batch":
        return _("run one command at a time here, or `didact batch` in a terminal")
    return _("the web app is already running")


def _help_instead(words: list[str], spec: CommandSpec | None) -> list[str]:
    """`roll --help` shows `didact help roll` (argparse would print to the terminal)."""
    options = words[: words.index("--")] if "--" in words else words
    if "-h" not in options and "--help" not in options:
        return words
    return ["help", *spec.words] if spec is not None else ["commands"]


@contextlib.contextmanager
def _no_stdin() -> Iterator[None]:
    """Commands that read stdin (`capture`, `pack import -`) get nothing, and never block."""
    saved = sys.stdin
    sys.stdin = io.StringIO("")
    try:
        yield
    finally:
        sys.stdin = saved


# ---------------------------------------------------------------------------- requests


@dataclass(slots=True)
class Request:
    """One request, parsed: what pages read."""

    app: App
    method: str
    path: str
    query: dict[str, list[str]] = field(default_factory=dict)
    form: dict[str, list[str]] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)  # from the route
    _flash: Flash | None = None
    _flash_taken: bool = False

    def arg(self, name: str, default: str = "") -> str:
        values = self.query.get(name)
        return values[0] if values else default

    def field(self, name: str, default: str = "") -> str:
        values = self.form.get(name)
        return values[0] if values else default

    def fields(self, name: str) -> list[str]:
        return list(self.form.get(name, []))

    @property
    def gm(self) -> bool:
        """Is the GM view on (secrets shown)? A cookie, else how the server was started."""
        raw = self.cookies.get(self.app.gm_cookie)
        return self.app.gm_default if raw is None else raw == "1"

    @property
    def here(self) -> str:
        """This page's URL, without a flash."""
        kept = [(k, v) for k, values in self.query.items() if k != "flash" for v in values]
        return f"{self.path}?{urlencode(kept)}" if kept else self.path

    def take_flash(self) -> Flash | None:
        """The outcome of the action that led here (once: the next call returns None)."""
        if not self._flash_taken:
            self._flash_taken = True
            key = self.arg("flash")
            self._flash = self.app.recall(key) if key else None
            return self._flash
        return None

    def run(self, *argv: str, gm: bool = False) -> Ran:
        """Run a read: with `gm=True` it passes --gm when the GM view is on and it's supported."""
        words = list(argv)
        if gm and self.gm and supports(words, "gm"):
            words.append("--gm")
        return self.app.run(words)


@dataclass(slots=True)
class Response:
    body: bytes
    status: int = 200
    content_type: str = "text/html; charset=utf-8"
    headers: list[tuple[str, str]] = field(default_factory=list)

    @classmethod
    def html(cls, markup: str, status: int = 200) -> Response:
        return cls(markup.encode("utf-8"), status)

    @classmethod
    def json(cls, data: JSON, status: int = 200) -> Response:
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return cls(body, status, "application/json; charset=utf-8")

    @classmethod
    def text(cls, text: str, status: int) -> Response:
        return cls(text.encode("utf-8"), status, "text/plain; charset=utf-8")

    @classmethod
    def redirect(cls, location: str) -> Response:
        return cls(b"", 303, "text/plain; charset=utf-8", [("Location", location)])
