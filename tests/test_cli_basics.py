"""The command line skeleton, doctor, help and output formats."""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import pytest

from didact import __version__
from didact.commands.registry import params_of
from didact.core.config import resolve_config
from didact.core.context import Context
from didact.core.output import Out, code, md, table
from tests.conftest import Cli


def test_version_flag_and_command(cli: Cli) -> None:
    assert cli("--version").out.strip() == f"didact {__version__}"
    result = cli("version")
    assert result.code == 0
    assert result.out.startswith(f"didact {__version__} (Python {platform.python_version()})")


def test_bare_didact_lists_commands(cli: Cli) -> None:
    result = cli()
    assert result.code == 0
    assert "- `doctor`: Check that Didact can run here" in result.out


def test_doctor_reports_missing_home_as_warning(cli: Cli, home: Path) -> None:
    result = cli("doctor")
    assert result.code == 0
    assert result.out.startswith("doctor: ready")
    assert "warn data home" in result.out
    assert "`didact init` creates it" in result.out
    assert "SQLite" in result.out


def test_doctor_json_is_structured(cli: Cli, home: Path) -> None:
    home.mkdir()
    result = cli("doctor", "--format", "json")
    data = json.loads(result.out)
    assert data["ready"] is True
    statuses = {c["name"]: c["status"] for c in data["checks"]}
    assert statuses["data home"] == "ok"
    assert statuses["Python"] == "ok"


def test_global_options_work_before_and_after_the_command(cli: Cli) -> None:
    before = json.loads(cli("--format", "json", "version").out)
    after = json.loads(cli("version", "--format", "json").out)
    assert before == after
    assert before["version"] == __version__


def test_yaml_format(cli: Cli) -> None:
    out = cli("version", "--format", "yaml").out
    assert f"version: {__version__}" in out


def test_unknown_command_suggests_the_right_one(cli: Cli) -> None:
    result = cli("doctr")
    assert result.code == 2
    assert "doctor" in result.err
    assert result.err.startswith("error (usage):")
    assert "fix: see `didact commands`" in result.err


def test_errors_follow_the_requested_format(cli: Cli) -> None:
    result = cli("doctr", "--format", "json")
    error = json.loads(result.err)["error"]
    assert error["code"] == "usage"


def test_help_describes_a_command(cli: Cli) -> None:
    result = cli("help", "doctor")
    assert result.code == 0
    assert result.out.startswith("`didact doctor [--repair]`")
    assert "examples:" in result.out
    assert "`didact doctor --format json`" in result.out


def test_help_for_unknown_command_suggests(cli: Cli) -> None:
    result = cli("help", "doctro")
    assert result.code == 1
    assert "did you mean `doctor`?" in result.err


def test_argparse_help_still_works(cli: Cli) -> None:
    result = cli("doctor", "--help")
    assert result.code == 0
    assert "examples:" in result.out


def test_config_resolution_order(tmp_path: Path) -> None:
    env = {"DIDACT_HOME": str(tmp_path / "env-home")}
    assert resolve_config(env=env).home == (tmp_path / "env-home").resolve()
    explicit = resolve_config(home=tmp_path / "explicit", env=env)
    assert explicit.home == (tmp_path / "explicit").resolve()
    default = resolve_config(env={})
    assert default.home == (Path.home() / "Documents" / "DidactLibrary").resolve()
    assert explicit.index_path.name.endswith(".sqlite")


def test_registry_derives_parameters() -> None:
    from typing import Annotated, Literal

    def sample(
        ctx: Context,
        name: Annotated[str, "the name"],
        odds: Literal["likely", "unlikely"] = "likely",
        *extra: str,
        as_: Annotated[str | None, "who"] = None,
        count: int = 1,
        tag: list[str] | None = None,
        quiet: bool = False,
    ) -> Out:
        return Out(data={}, md="")

    params = {p.name: p for p in params_of(sample)}
    assert params["name"].kind == "positional" and params["name"].required
    assert params["odds"].choices == ("likely", "unlikely") and not params["odds"].required
    assert params["extra"].kind == "variadic"
    assert params["as_"].cli_name == "as" and params["as_"].kind == "option"
    assert params["count"].base is int
    assert params["tag"].multiple
    assert params["quiet"].kind == "flag"


def test_no_argument_takes_a_global_option_name() -> None:
    def positional(ctx: Context, version: str) -> Out:  # would read as `--version`
        raise AssertionError

    def option(ctx: Context, *, detail: str = "") -> Out:  # would clash with `--detail`
        raise AssertionError

    for func in (positional, option):
        with pytest.raises(TypeError, match="is a global option"):
            params_of(func)


def test_markdown_helpers() -> None:
    name = "a|b"
    assert md(t"cell {name:cell}") == "cell a\\|b"
    assert md(t"run {name:code}") == "run `a|b`"
    assert code("x`y") == "``x`y``"
    assert table(["k", "v"], [["a|b", 1]]) == "| k | v |\n|---|---|\n| a\\|b | 1 |"


def _run_python(code_text: str) -> str:
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    return subprocess.run(
        [sys.executable, "-c", code_text], capture_output=True, text=True, check=True, env=env
    ).stdout


def test_heavy_libraries_stay_lazy() -> None:
    probe = (
        "import sys\n"
        "from didact.cli.main import main\n"
        "main(['version']); main(['doctor']); main(['help', 'doctor'])\n"
        "heavy = {'pydantic', 'ruamel'}\n"
        "print('HEAVY', sorted(m for m in sys.modules if m.split('.')[0] in heavy))\n"
    )
    last = _run_python(probe).strip().splitlines()[-1]
    assert last == "HEAVY []"


def _startup_seconds() -> float:
    """The CPU time (user + system) one `didact version` takes. Unlike the wall clock, it
    doesn't grow while other processes keep the machine busy."""
    resource = pytest.importorskip("resource")  # not on Windows
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    subprocess.run([sys.executable, "-m", "didact", "version"], check=True, capture_output=True)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return float(after.ru_utime - before.ru_utime + after.ru_stime - before.ru_stime)


@pytest.mark.slow
def test_startup_is_fast() -> None:
    fastest = min(_startup_seconds() for _ in range(5))  # past one-off costs such as .pyc files
    assert fastest < 0.25, f"startup took {fastest:.3f}s of CPU time"


def test_batch_runs_lines_and_stops_at_a_failure(cli: Cli, tmp_path: Path) -> None:
    cli("world", "new", "vale")
    script = tmp_path / "turn.txt"
    script.write_text("# a turn\nroll 2d6\ndidact new npc Tom\nshow nobody\nroll d4\n")
    stopped = cli("batch", "--file", str(script))
    assert stopped.code == 1
    assert "$ didact roll 2d6" in stopped.out and "$ didact new npc Tom" in stopped.out
    assert "error (not_found)" in stopped.out and "$ didact roll d4" not in stopped.out
    everything = json.loads(
        cli("batch", "--file", str(script), "--keep-going", "--format", "json").out
    )
    assert [r["code"] for r in everything["results"]] == [0, 1, 1, 0]  # Tom exists now
    assert everything["ok"] is False
    script.write_text("batch --file x\n")
    assert cli("batch", "--file", str(script)).code != 0


def test_setup_claude_adds_one_allow_rule(cli: Cli, tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"model": "x", "permissions": {"allow": ["Bash(ls *)"]}}))
    assert "would add" in cli("setup", "claude", "--settings", str(settings), "--check").out
    assert json.loads(settings.read_text())["permissions"]["allow"] == ["Bash(ls *)"]
    assert cli("setup", "claude", "--settings", str(settings)).code == 0
    data = json.loads(settings.read_text())
    assert data["model"] == "x"
    assert data["permissions"]["allow"] == ["Bash(ls *)", "Bash(didact *)"]
    assert (tmp_path / "settings.json.bak").is_file()
    assert "already allows" in cli("setup", "claude", "--settings", str(settings)).out
    removing = ("setup", "claude", "--settings", str(settings), "--remove")
    assert "would remove" in cli(*removing, "--check").out
    assert cli(*removing).code == 0
    assert json.loads(settings.read_text())["permissions"]["allow"] == ["Bash(ls *)"]
    assert "has no" in cli(*removing).out


def test_long_brief_output_is_cut_with_a_way_to_see_it_all() -> None:
    from didact.core.output import Out, budget

    text = "\n".join(f"line {n}" for n in range(5000))
    cut = budget(text, limit=1000)
    assert len(cut) < 1100 and cut.endswith(
        "more lines (`--detail full` shows everything, `--format json` too)"
    )
    assert "line 4999" in Out(data={}, md=text).markdown("full")
    assert "line 4999" not in Out(data={}, md=text).markdown("brief")


def test_plain_reads_any_value_as_words() -> None:
    from didact.core.output import plain

    assert plain([{"name": "dagger", "damage": "d6"}, "rope"]) == "dagger d6, rope"
    assert plain(True) == "true" and plain(None) == "null" and plain(3) == "3"
