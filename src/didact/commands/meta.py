"""Meta commands: version, doctor, commands, help."""

import difflib
import os
import platform
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Literal

from didact import __version__
from didact.commands._common import open_repo
from didact.commands.registry import REGISTRY, CommandSpec, Metavar, command
from didact.core import labels
from didact.core.context import Context
from didact.core.errors import DidactError, NotFoundError, UsageError
from didact.core.i18n import N_, _, ngettext, pgettext, translate
from didact.core.output import JSON, Out, code
from didact.store.repo import Repo

type Status = Literal["ok", "warn", "fail"]


@command("version", summary="Print Didact's version", examples=("didact version",))
def version(ctx: Context) -> Out:
    python = platform.python_version()
    return Out(
        data={"version": __version__, "python": python},
        md=_("didact {version} (Python {python})", version=__version__, python=python),
    )


# ---------------------------------------------------------------------------- doctor


@dataclass(frozen=True, slots=True)
class Check:
    """One check. `name`, `detail` and `fix` are English (marked with `N_`), and `detail` may
    name `values`: the data keeps the English, the line shows the language in use."""

    name: str
    status: Status
    detail: str
    fix: str | None = None
    values: dict[str, str] = field(default_factory=dict)

    def _filled(self, text: str) -> str:
        return text.format(**self.values) if self.values else text

    def line(self) -> str:
        label = labels.inline(
            {"ok": "ok  ", "warn": "warn", "fail": "FAIL"}[self.status],
            labels.check_state(self.status),
        )
        text = f"- {label} {translate(self.name)}: {self._filled(translate(self.detail))}"
        if not self.fix:
            return text
        return _("{check} → fix: {fix}", check=text, fix=translate(self.fix))

    def to_data(self) -> dict[str, JSON]:
        data: dict[str, JSON] = {
            "name": self.name,
            "status": self.status,
            "detail": self._filled(self.detail),
        }
        if self.fix:
            data["fix"] = self.fix
        return data


@command(
    "doctor",
    summary="Check that Didact can run here, and repair what a crash left",
    examples=("didact doctor", "didact doctor --repair", "didact doctor --format json"),
)
def doctor(
    ctx: Context,
    *,
    repair: Annotated[
        bool, "take back a change a crash cut short, and mend the end of the event log"
    ] = False,
) -> Out:
    """Check Python, SQLite (FTS5), the data home, the cache, the core pack and the event log.
    Writes nothing unless told to repair; any command that opens the library repairs too."""
    repaired = _repair(ctx) if repair else []
    checks = [
        _check_python(),
        _check_sqlite(),
        _check_dir(N_("data home"), ctx.config.home, missing_fix=N_("`didact init` creates it")),
        _check_dir(N_("cache"), ctx.config.cache, missing_fix=None),
        _check_core_pack(),
        _check_log(ctx),
        _check_thesaurus(),
    ]
    counts = {s: sum(c.status == s for c in checks) for s in ("ok", "warn", "fail")}
    ready = counts["fail"] == 0
    tally = ", ".join(
        f"{n} {labels.inline(s, labels.check_state(s))}" for s, n in counts.items() if n
    )
    head = (
        _("doctor: ready ({tally})", tally=tally)
        if ready
        else _("doctor: NOT ready ({tally})", tally=tally)
    )
    return Out(
        data={"ready": ready, "version": __version__, "checks": [c.to_data() for c in checks]},
        md="\n".join([head, *(c.line() for c in checks), *repaired]),
        ok=ready,
    )


def _repair(ctx: Context) -> list[str]:
    """Clear up what a crash left, now. Opening the library takes back a change cut short (and
    `execute` shows the note it leaves); the end of the log is mended here."""
    repo = open_repo(ctx)
    if not repo.initialized():
        return [_("nothing to repair")]
    with repo.writing():
        cut = repo.log.heal()
    if cut:
        return [_("cut off a half-written line at the end of the event log")]
    return [] if ctx.notices else [_("nothing to repair")]


def _check_log(ctx: Context) -> Check:
    """The whole event log reads, and no change is waiting to be taken back."""
    name, repo = N_("event log"), Repo(ctx.config)
    try:
        count = len(repo.log.all())
    except DidactError as err:
        return Check(
            name,
            "fail",
            "{error}",
            fix=N_("restore the line from a backup or remove it"),
            values={"error": err.message},
        )
    fix = "`didact doctor --repair`"
    if repo.layout.applying_file.exists():
        return Check(name, "warn", N_("a change was cut short and is half written"), fix=fix)
    if repo.log.torn():
        return Check(name, "warn", N_("its last line was cut short"), fix=fix)
    return Check(name, "ok", N_("{count} events"), values={"count": str(count)})


def _check_core_pack() -> Check:
    from didact.packs.library import CORE, bundled_dir

    bundled = bundled_dir()
    if bundled is None or not (bundled / CORE).is_dir():
        return Check(
            N_("core pack"),
            "fail",
            N_("not found: this copy of Didact is incomplete"),
            fix=N_("install Didact again, from a checkout or a full release"),
        )
    return Check(N_("core pack"), "ok", "{path}", values={"path": str(bundled / CORE)})


def _check_thesaurus() -> Check:
    from didact.core import words

    if not words.thesaurus_ready():
        return Check(
            N_("thesaurus"), "warn", N_("not installed: searches don't match synonyms"),
            fix="`didact setup thesaurus`",
        )  # fmt: skip
    return Check(N_("thesaurus"), "ok", "{path}", values={"path": str(words.wordnet_dir())})


def _check_python() -> Check:
    # The package requires 3.14 to even import, so this reports rather than gates.
    return Check("Python", "ok", "{version}", values={"version": platform.python_version()})


def _check_sqlite() -> Check:
    version = sqlite3.sqlite_version
    con = sqlite3.connect(":memory:")
    try:
        try:
            con.execute("CREATE VIRTUAL TABLE fts USING fts5(body)")
        except sqlite3.OperationalError:
            return Check(
                "SQLite",
                "fail",
                N_("{version} without FTS5"),
                fix=N_(
                    "use a Python whose SQLite includes FTS5 (Homebrew and python.org builds do)"
                ),
                values={"version": version},
            )
        try:
            con.execute("CREATE VIRTUAL TABLE tri USING fts5(body, tokenize='trigram')")
        except sqlite3.OperationalError:
            return Check(
                "SQLite",
                "warn",
                N_("{version} with FTS5 but no trigram tokenizer"),
                fix=N_(
                    "substring name search falls back to a slower scan (SQLite 3.34+ has trigram)"
                ),
                values={"version": version},
            )
    finally:
        con.close()
    return Check("SQLite", "ok", N_("{version} with FTS5 and trigram"), values={"version": version})


def _check_dir(name: str, path: Path, *, missing_fix: str | None) -> Check:
    """A directory must exist and be writable, or be creatable."""
    at = {"path": str(path)}
    if path.exists():
        if not path.is_dir():
            return Check(
                name,
                "fail",
                N_("{path} is not a directory"),
                fix=N_("point it at a folder"),
                values=at,
            )
        if os.access(path, os.W_OK):
            return Check(name, "ok", "{path}", values=at)
        return Check(
            name, "fail", N_("{path} is not writable"), fix=N_("fix its permissions"), values=at
        )
    parent = next(p for p in path.parents if p.exists())
    if not os.access(parent, os.W_OK):
        return Check(
            name,
            "fail",
            N_("{path} cannot be created ({parent} is not writable)"),
            fix=N_("choose another location"),
            values={**at, "parent": str(parent)},
        )
    if missing_fix is None:
        return Check(name, "ok", N_("{path} (created on first use)"), values=at)
    return Check(name, "warn", N_("{path} does not exist yet"), fix=missing_fix, values=at)


# ---------------------------------------------------------------------------- commands / help


@command(
    "commands",
    summary="List every command with a one-line summary",
    examples=("didact commands", "didact commands --format json"),
)
def commands(ctx: Context) -> Out:
    return overview(())


def overview(prefix: tuple[str, ...] = ()) -> Out:
    """List the commands under a prefix (all commands for the empty prefix)."""
    specs = sorted(
        (s for s in REGISTRY.values() if s.words[: len(prefix)] == prefix), key=lambda s: s.name
    )
    if not specs:
        raise NotFoundError(
            _("no commands under {prefix}", prefix=repr(" ".join(prefix))),
            hint=_("run `didact commands`"),
        )
    title = (
        _("didact {prefix} commands", prefix=" ".join(prefix)) if prefix else _("didact commands")
    )
    lines = [title, *(f"- {code(s.name)}: {translate(s.summary)}" for s in specs)]
    lines += [
        "",
        _(
            "Details: `didact help <command>`. Global options: --format md|yaml|json, "
            "--detail brief|full, --home <path>, --world <id>, --campaign <id>."
        ),
    ]
    data: dict[str, JSON] = {
        "commands": [{"name": s.name, "summary": s.summary, "usage": s.usage()} for s in specs]
    }
    return Out(data=data, md="\n".join(lines), whole=True)


@command(
    "help",
    summary="Explain a command: usage, arguments and examples",
    examples=("didact help doctor", "didact help help"),
)
def help_(ctx: Context, *words: Annotated[str, "the command to explain, e.g. `doctor`"]) -> Out:
    if not words:
        return overview(())
    name = " ".join(words)
    spec = REGISTRY.get(name)
    if spec is not None:
        return describe(spec)
    if any(s.words[: len(words)] == words for s in REGISTRY.values()):
        return overview(words)
    from didact import guides

    if name in guides.topics():
        return guide(ctx, name)
    close = difflib.get_close_matches(name, list(REGISTRY), n=3)
    hint = _did_you_mean(close) if close else _("run `didact commands`")
    raise NotFoundError(_("unknown command {name}", name=repr(name)), hint=hint)


def _did_you_mean(close: list[str]) -> str:
    """`did you mean `a` or `b`?`"""
    either = f" {pgettext('one name or another', 'or')} "
    return _("did you mean {names}?", names=either.join(code(c) for c in close))


@command(
    "guide",
    summary="Read a guide: how to do things with Didact (dice, …)",
    examples=("didact guide", "didact guide dice", "didact guide play --lang fr"),
)
def guide(
    ctx: Context,
    topic: Annotated[str | None, "the topic, e.g. `dice`"] = None,
    *,
    lang: Annotated[
        str | None,
        "a translation, by language code (fr, pt-BR, …); default: the language in use "
        "(English where there's none)",
    ] = None,
) -> Out:
    from didact import guides
    from didact.core import i18n

    available = guides.topics()
    packed = _pack_guides(ctx)
    by_tag = {x.tag.casefold(): x.code for x in i18n.LANGUAGES.values()}
    wanted = by_tag.get(lang.casefold().replace("_", "-")) if lang is not None else None
    if lang is not None and wanted is None:
        raise UsageError(
            _("no language {lang}", lang=repr(lang)),
            hint=_("use one of: {languages}", languages=", ".join(sorted(by_tag))),
        )
    if lang is None and i18n.current().code != i18n.DEFAULT:
        wanted = i18n.current().code  # the language this call speaks ($DIDACT_LANG)
    if wanted is not None:
        available = {name: guides.summary(name, wanted) for name in available}
    if topic is None:
        lines = [_("guides (`didact guide <topic>`):")]
        lines += [f"- {code(name)}: {summary}" for name, summary in available.items()]
        lines += [
            _("- {topic}: how to run the {pack} pack", topic=code(pack_id), pack=pack_id)
            for pack_id in packed
        ]
        return Out(data={"topics": {**available, **dict.fromkeys(packed, "")}}, md="\n".join(lines))
    if topic in packed and topic not in available:
        return Out(
            data={"topic": topic, "text": packed[topic]}, md=packed[topic].rstrip(), whole=True
        )
    if topic not in available:
        close = difflib.get_close_matches(topic, list(available), n=3)
        hint = _did_you_mean(close) if close else _("run `didact guide`")
        raise NotFoundError(_("no guide {topic}", topic=repr(topic)), hint=hint)
    if wanted is None:
        text = guides.read(topic)
        return Out(data={"topic": topic, "text": text}, md=text.rstrip(), whole=True)
    shown = guides.translated(topic, wanted)
    note = (
        [
            _(
                "note: translated from an older English version (`didact guide {topic}`)",
                topic=topic,
            )
        ]
        if shown.language != "en" and not shown.current
        else []
    )
    return Out(
        data={
            "topic": topic,
            "text": shown.text,
            "language": shown.language,
            "current": shown.current,
        },
        md="\n".join([shown.text.rstrip(), *note]),
        whole=True,
    )


def _pack_guides(ctx: Context) -> dict[str, str]:
    """The enabled packs' GUIDE.md, by pack id (none outside a library)."""
    from didact.services import packs

    try:
        repo = open_repo(ctx)
        active = packs.active(repo)
    except DidactError:
        return {}
    return {p.id: str(p.bundle.get("guide")) for p in active.packs if p.bundle.get("guide")}


def describe(spec: CommandSpec) -> Out:
    """Full help for one command, generated from its registration."""
    lines = [code(spec.usage()), "", translate(spec.description)]
    params = list(spec.params)
    if params or spec.writes:
        lines += ["", _("arguments:")]
        for p in params:
            label = p.metavar if p.kind in ("positional", "variadic") else f"{p.flag} {p.metavar}"
            if p.kind == "flag":
                label = p.flag
            notes: list[str] = []
            if p.choices:
                notes.append(_("one of {choices}", choices=", ".join(p.choices)))
            if p.kind == "option" and not p.required and p.default not in (None, [], ()):
                notes.append(_("default {value}", value=p.default))
            if p.multiple and p.kind == "option":
                notes.append(_("repeatable"))
            suffix = f" ({'; '.join(notes)})" if notes else ""
            lines.append(f"- {code(label)}: {translate(p.help) or '—'}{suffix}")
        if spec.writes:
            lines.append(f"- {code('--dry-run')}: {_('show what would change without writing')}")
            lines.append(f"- {code('--reason <text>')}: {_('why; recorded in the log')}")
    if spec.examples:
        lines += ["", _("examples:"), *(f"- {code(e)}" for e in spec.examples)]
    data: dict[str, JSON] = {
        "name": spec.name,
        "summary": spec.summary,
        "description": spec.description,
        "usage": spec.usage(),
        "writes": spec.writes,
        "params": [
            {
                "name": p.cli_name,
                "kind": p.kind,
                "type": p.base.__name__,
                "required": p.required,
                "help": p.help,
                "choices": list(p.choices) if p.choices else None,
            }
            for p in params
        ],
        "examples": list(spec.examples),
    }
    return Out(data=data, md="\n".join(lines), whole=True)


@command(
    "batch",
    summary="Run several commands in one call: one per line, from stdin or a file",
    examples=(
        "didact batch <<'EOF'\nroll 2d6\nset freya hp-=2\nlog result 'The rope holds'\nEOF",
        "didact batch --file turn.txt --keep-going",
    ),
    description=(
        "Each line is a didact command (with or without the word `didact`); `#` starts a\n"
        "comment. --home, --world, --campaign and --detail pass on to every line. It stops at\n"
        "the first failure unless --keep-going. With --format json you get one result per line."
    ),
)
def batch(
    ctx: Context,
    *,
    file: Annotated[str | None, "read the commands from this file", Metavar("path")] = None,
    keep_going: Annotated[bool, "carry on after a failed command"] = False,
) -> Out:
    raise UsageError(
        _("batch runs from the command line"),
        hint=_("pipe the commands in: `didact batch <<'EOF' …`"),
    )


@command(
    "sample",
    summary="Build the sample campaign into an empty library, to try Didact on",
    examples=(
        "didact --home ~/DidactSample sample",
        "didact --home ~/DidactSample sample --system my-system",
    ),
    description=(
        "A small river valley: a PC made at random, people with the GM's notes, places\n"
        "joined by paths (one of them secret), a faction, items in a chest, a quest, a clock,\n"
        "and a session under way with beats, a roll and a fight. It's built with ordinary\n"
        "commands, so its history is real and undo works. The library must hold no world yet.\n"
        "`didact serve --demo` serves one of its own, rebuilt each time it starts."
    ),
)
def sample(
    ctx: Context,
    *,
    system: Annotated[
        str | None, "the game system (default: the first that came with Didact)", Metavar("pack")
    ] = None,
) -> Out:
    raise UsageError(
        _("sample runs from the command line"), hint=_("run `didact sample` in a terminal")
    )


@command(
    "setup thesaurus",
    summary="Choose the thesaurus searches use for synonyms (WordNet: English or another language)",
    examples=(
        "didact setup thesaurus",
        "didact setup thesaurus --lang fr",
        "didact setup thesaurus --check",
        "didact setup thesaurus --progress",
        "didact setup thesaurus --available",
        "didact setup thesaurus --from ~/Downloads/my-wordnet.xml",
        "didact setup thesaurus --remove --lang fr",
        "didact setup thesaurus --remove",
    ),
    description=(
        "Uses one language's WordNet for synonyms: --lang picks it (English by default),\n"
        "downloading it into Didact's cache folder first if it isn't there (English is about\n"
        "110 MB once installed). Languages downloaded before stay, to switch back without\n"
        "downloading again. `search`, `find` and `rules lookup` then also match synonyms;\n"
        "without a thesaurus they still match exact words and near spellings. A download\n"
        "reports how far it is: --progress shows it, as the browser app's Settings page does."
    ),
)
def setup_thesaurus(
    ctx: Context,
    *,
    lang: Annotated[str | None, "the language to use (en, fr, de, es, …)"] = None,
    from_: Annotated[
        str | None, "add a WordNet file (WN-LMF XML) and use it", Metavar("file")
    ] = None,
    check: Annotated[bool, "only say what's there and which is in use"] = False,
    progress: Annotated[bool, "how far a download is"] = False,
    available: Annotated[bool, "list the languages it can be downloaded in"] = False,
    remove: Annotated[bool, "delete the thesaurus (or, with --lang, that language)"] = False,
) -> Out:
    from didact.core import words

    where = str(words.wordnet_dir())
    if progress:
        running = words.progress()
        if running is None:
            return Out(data={"progress": None}, md=_("no download under way"))
        done = f"{running.count}/{running.total}" if running.total else str(running.count)
        said = (
            _("failed: {error}", error=running.error)
            if running.stage == "failed"
            else f"{running.stage} {done}"
        )
        return Out(data={"progress": running.to_data()}, md=f"{running.language}: {said}")
    if available:
        offered = words.available()
        return Out(
            data={"available": [{"language": c, "name": n} for c, n in offered]},
            md="\n".join(
                [
                    ngettext("{n} language:", "{n} languages:", len(offered)),
                    *(f"- {c}: {n}" for c, n in offered),
                ]
            ),
        )
    if remove:
        if lang:
            gone = words.remove_language(lang.strip().casefold())
            return Out(
                data={"removed": [lang] if gone else [], "path": where},
                md=(
                    _("✔ removed {lang}", lang=lang)
                    if gone
                    else _("{lang} isn't installed", lang=lang)
                ),
            )
        everything = words.remove()
        return Out(
            data={"removed": everything, "path": where},
            md=(
                _("✔ removed the thesaurus ({path})", path=where)
                if everything
                else _("no thesaurus to remove")
            ),
        )
    if not check:
        _thesaurus_use(lang, from_)
    lexicons = words.installed()
    rows: list[JSON] = [
        {"id": x.id, "language": x.language, "name": x.name, "active": x.active} for x in lexicons
    ]
    if not lexicons:
        return Out(
            data={"lexicons": [], "path": where},
            md=_("no thesaurus yet: get it with {command}", command=code("didact setup thesaurus")),
        )
    lines = [_("thesaurus ({path}):", path=where)]
    lines += [
        _("- {name} ({language}, {id})  ← in use", name=x.name, language=x.language, id=x.id)
        if x.active
        else f"- {x.name} ({x.language}, {x.id})"
        for x in lexicons
    ]
    return Out(data={"lexicons": rows, "path": where}, md="\n".join(lines))


def _thesaurus_use(lang: str | None, from_: str | None) -> None:
    """Make `lang` (or the file) the thesaurus in use, downloading it first if needed."""
    from didact.core import words as w

    if from_ is not None:
        source, is_file, code_ = str(Path(from_).expanduser()), True, ""
    else:
        code_ = (lang or "en").strip().casefold()
        if w.use(code_) is not None:
            w.settled(code_)
            return  # there already: just switch to it
        source, is_file = w.project_for(code_), False
        if source not in w.known_projects():
            w.settled(code_)
            raise UsageError(
                _("no wordnet for {lang}", lang=code_),
                hint=_("`didact setup thesaurus --available` lists them"),
            )
    try:
        w.add(source, file=is_file, language=code_)
    except Exception as err:  # the network, a file wn can't read, or a download under way
        raise UsageError(
            _("couldn't add {source}: {error}", source=source, error=err),
            hint=_("check the connection (or the file) and try again"),
        ) from err


ALLOW_RULE = "Bash(didact *)"


@command(
    "setup claude",
    summary="Let Claude Code run didact without asking each time (an allow rule in its settings)",
    examples=(
        "didact setup claude --check",
        "didact setup claude",
        "didact setup claude --settings .claude/settings.json   # just this project",
        "didact setup claude --remove",
    ),
    description=(
        f"Adds `{ALLOW_RULE}` to `permissions.allow` in Claude Code's settings (your user\n"
        "settings by default), keeping everything else and a `.bak` copy; --remove takes it\n"
        "out again. The Didact plugin's PreToolUse hook does the same job without touching\n"
        "settings; use one or the other."
    ),
)
def setup_claude(
    ctx: Context,
    *,
    settings: Annotated[
        str | None, "the settings file (default: ~/.claude/settings.json)", Metavar("path")
    ] = None,
    check: Annotated[bool, "only say what would change"] = False,
    remove: Annotated[bool, "take the allow rule out again"] = False,
) -> Out:
    import json
    import os
    from pathlib import Path

    default = os.environ.get("DIDACT_CLAUDE_SETTINGS", "~/.claude/settings.json")
    path = Path(settings or default).expanduser()
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except json.JSONDecodeError as exc:
        raise UsageError(
            _("{path} isn't valid JSON: {error}", path=path, error=exc),
            hint=_("fix it by hand first"),
        ) from exc
    if not isinstance(data, dict):
        raise UsageError(_("{path} isn't a JSON object", path=path), hint=_("fix it by hand first"))
    permissions = data.setdefault("permissions", {})
    allow = permissions.setdefault("allow", []) if isinstance(permissions, dict) else None
    if not isinstance(allow, list):
        raise UsageError(
            _("{path}: permissions.allow isn't a list", path=path), hint=_("fix it by hand first")
        )
    if remove:
        if ALLOW_RULE not in allow:
            return Out(
                data={"settings": str(path), "changed": False},
                md=_("✔ {path} has no {rule} rule", path=path, rule=ALLOW_RULE),
            )
        if check:
            return Out(
                data={"settings": str(path), "changed": False, "would_remove": ALLOW_RULE},
                md=_(
                    "would remove {rule} from permissions.allow in {path}",
                    rule=ALLOW_RULE,
                    path=path,
                ),
            )
        allow.remove(ALLOW_RULE)
    elif ALLOW_RULE in allow:
        return Out(
            data={"settings": str(path), "changed": False},
            md=_("✔ {path} already allows {rule}", path=path, rule=ALLOW_RULE),
        )
    elif check:
        return Out(
            data={"settings": str(path), "changed": False, "would_add": ALLOW_RULE},
            md=_("would add {rule} to permissions.allow in {path}", rule=ALLOW_RULE, path=path),
        )
    else:
        allow.append(ALLOW_RULE)
    if path.is_file():
        path.with_name(path.name + ".bak").write_text(
            path.read_text(encoding="utf-8"), encoding="utf-8"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    done = (
        _(
            "✔ {path} no longer allows {rule} (restart Claude Code to pick it up)",
            path=path,
            rule=ALLOW_RULE,
        )
        if remove
        else _(
            "✔ {path} now allows {rule} (restart Claude Code to pick it up)",
            path=path,
            rule=ALLOW_RULE,
        )
    )
    return Out(data={"settings": str(path), "changed": True}, md=done)
