"""The sample campaign: a small world to try Didact on, built with the same commands a player
or an LLM would run, so it's a real library with a real history.

`didact sample` builds it into an empty library, and `didact serve --demo` into one of its
own, fresh each time it starts. It plays on the first game system that shipped with Didact or
was installed (or on the one asked for), so nothing here names a system: the valley, its
people and places are the same whatever the rules. Seeded, so it comes out the same each time.
"""

import contextlib
import shlex
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from didact.core.config import resolve_config
from didact.core.errors import DidactError, InvalidError, NotFoundError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.services.care import DEMO_MARK

WORLD, CAMPAIGN, SEED = "vale", "withering", "sample"
DEMO = "didact-demo"  # the demo library's folder, beside Didact's cache folder
MARK = DEMO_MARK  # a file in it: the folder is the demo's, and may be rebuilt (a reset keeps it)

BEFORE_PLAY = (  # the world and its people, places and ties
    "new npc Sweeney --body 'Champion of the Wood, keeper of the old trail.'",
    "about sweeney 'looks=tall, one eye clouded, smells of pipe smoke' "
    "'personality=jovial, greedy' 'wants=buy back the family mill' "
    "'plan=sell the route to the raiders at the ford' 'doing=whittling by the fire' "
    "'thoughts=foreshadow the betrayal; pay it off at the ford'",
    "new loc 'My House' --body 'A crooked cottage at the edge of the village.'",
    "new loc 'The Ford' --body 'Shallow water over old stones.'",
    "about 'the ford' 'looks=brown water, slick stones' 'state=flooded after the rains' "
    "'secret=a drowned shrine under the stones'",
    "new loc 'Old Mill' --body 'The family mill, half fallen in.'",
    "new loc 'Drowned Shrine' --set knowledge=secret --body 'Green stone, black water.'",
    "link 'my house' road 'the ford'",
    "link 'my house' path 'old mill'",
    "link 'the ford' path 'drowned shrine'",
    "new item Chest --body 'An iron-bound chest by the hearth.'",
    "new faction Raiders --body 'Riders from the hills.'",
    "about raiders 'wants=the route through the Wood' 'plan=strike the village at the new moon'",
    "link sweeney lives-at 'my house'",
    "link sweeney owes raiders",
    "link raiders camps-at 'the ford'",
    "inv add 'my house' item:chest",
    "inv add freya Sword",  # just one: a full inventory has a price in some systems
    "quest new 'Stop the raid' --goal 'Keep the village safe at the new moon' "
    "--milestone 'Learn who sold the route' --milestone 'Warn the village'",
    "track new 'The raid' --kind clock --size 6",
    "track tick 'the raid'",
    "visit 'the ford'",
    "visit 'my house'",
)
PLAY = (  # a session under way: a scene, beats, a roll, a fight
    "session start",
    "scene new 'At home'",
    "inv move freya sword chest",
    "log action 'Freya hides the sword in the chest'",
    "log consequence 'Sweeney sold the route to the raiders' --about sweeney --about freya "
    "--importance 8",
    "log note 'Raider scouts find the camp' --about raiders --secret",
    "roll '2d6+1' --reason 'a test roll'",
    "time advance '2 hours'",
    "remind 'The new moon rises' --in '3 days'",
    "new npc 'Raider Scout' --body 'A lean rider with a bone horn.'",
    "about 'raider scout' 'doing=circling the house' 'plan=signal the others'",
    "combat start --party 'raider scout'",
)


@dataclass(slots=True)
class Built:
    """What the sample holds, and what it had to leave out on this system."""

    home: Path
    system: str
    commands: int = 0
    skipped: list[str] = field(default_factory=list)  # in English: it's data
    notes: list[str] = field(default_factory=list)  # the same, as shown

    def skip(self, english: str, shown: str) -> None:
        self.skipped.append(english)
        self.notes.append(shown)

    def to_data(self) -> dict[str, JSON]:
        return {
            "home": str(self.home),
            "system": self.system,
            "world": WORLD,
            "campaign": CAMPAIGN,
            "commands": self.commands,
            "skipped": list[JSON](self.skipped),
        }

    def text(self) -> str:
        lines = [
            _(
                "✔ built the sample campaign in {home}: world {world}, campaign {campaign}, "
                "on {system} ({commands} commands)",
                home=self.home,
                world=WORLD,
                campaign=CAMPAIGN,
                system=self.system,
                commands=self.commands,
            ),
            _("a session is under way: `didact brief`, or `didact serve` to look around"),
        ]
        lines += [_("note: {note}", note=note) for note in self.notes]
        return "\n".join(lines)


def build(
    home: Path, *, system: str | None = None, say: Callable[[str], None] | None = None
) -> Built:
    """Build the sample campaign into `home`, which must hold no world yet."""
    worlds = home / "worlds"
    if worlds.is_dir() and any(worlds.iterdir()):
        raise InvalidError(
            _("{home} already has worlds: the sample goes into an empty library", home=home),
            hint=_("give it one of its own: `didact --home ~/DidactSample sample`"),
        )
    runner = _Runner(home)
    chosen = _system(runner, system)
    built = Built(home, chosen)
    if say:
        say(_("building the sample campaign on {system}…", system=chosen))
    runner.run(f"world new {WORLD} --name Vale --system {chosen} --seed {SEED}")
    runner.run(f"campaign new {CAMPAIGN} --name 'The Withering' --seed {SEED}")
    _hero(runner, built)
    for line in (*BEFORE_PLAY, *PLAY):
        runner.run(line)
    _generated(runner, built)
    built.commands = runner.count
    return built


def demo_home() -> Path:
    """Where `didact serve --demo` keeps its library: beside the cache, never the user's."""
    return resolve_config().cache.parent / DEMO


def fresh_demo(say: Callable[[str], None] | None = None, *, system: str | None = None) -> Built:
    """Build the sample campaign into the demo library, afresh."""
    home = demo_home()
    if home.exists():
        if not (home / MARK).is_file():
            raise InvalidError(
                _(
                    "{home} exists but isn't Didact's demo library, so it wasn't replaced",
                    home=home,
                ),
                hint=_("move that folder away, then run `didact serve --demo` again"),
            )
        shutil.rmtree(home)
    home.mkdir(parents=True)
    (home / MARK).write_text("didact serve --demo rebuilds this library each time\n")
    built = build(home, system=system, say=say)
    _install_shipped(_Runner(home))
    return built


def _install_shipped(runner: _Runner) -> None:
    """Every pack that ships with Didact, installed: the demo shows them all, ready to use.
    One installs the shipped packs it needs too, so the list is read again after each."""
    while True:
        listed = runner.run(["pack", "list"]).get("packs")
        shipped = [
            str(found.get("id"))
            for found in (listed if isinstance(listed, list) else [])
            if isinstance(found, dict) and found.get("origin") == "shipped"
        ]
        if not shipped:
            return
        runner.run(["pack", "install", shipped[0]])


class _Runner:
    """Runs command lines against one library, as the command line would."""

    def __init__(self, home: Path) -> None:
        self.home = home
        self.count = 0

    def run(self, line: str | Sequence[str]) -> dict[str, JSON]:
        from didact.cli.main import execute

        words = shlex.split(line) if isinstance(line, str) else list(line)
        result = execute(["--home", str(self.home), *words])
        if result.error is not None:
            raise result.error
        self.count += 1
        return dict(result.out.data) if result.out is not None else {}


def _system(runner: _Runner, wanted: str | None) -> str:
    """The system asked for, else the first installed one, else the first that ships with
    Didact (installed for the sample), else any Didact can see."""
    listed = runner.run(["pack", "list"]).get("packs")
    packs = [p for p in listed if isinstance(p, dict)] if isinstance(listed, list) else []
    systems = [p for p in packs if p.get("kind") == "system"]

    def ids(*origins: str) -> list[str]:
        return sorted(
            str(p.get("id")) for p in systems if not origins or p.get("origin") in origins
        )

    if wanted is not None and wanted not in ids():
        raise NotFoundError(
            _("no game system {system}", system=repr(wanted)),
            hint=_("systems here: {systems}", systems=", ".join(ids()) or _("none")),
        )
    choice = wanted or next(iter(ids("installed") or ids("shipped") or ids()), None)
    if choice is None:
        raise NotFoundError(
            _("no game system is installed"),
            hint=_("install one: `didact pack install <file>`"),
        )
    if choice in ids("shipped"):
        runner.run(["pack", "install", choice])
    return choice


def _hero(runner: _Runner, built: Built) -> None:
    """Freya, made the system's way at random; a plain record if it has no way."""
    try:
        drafted = runner.run(["char", "new", "--mode", "random", "--prefill", '{"name": "Freya"}'])
        draft = drafted.get("draft")
        runner.run(["char", "commit", str(draft.get("id") if isinstance(draft, dict) else "")])
    except DidactError as err:
        built.skip(
            f"Freya was made by hand: {err.message}",
            _("Freya was made by hand: {problem}", problem=err.message),
        )
        runner.run(["new", "pc", "Freya", "--fill"])


def _generated(runner: _Runner, built: Built) -> None:
    """Something from one of the system's generators, if it has one that runs on its own."""
    listed = runner.run(["gen", "list"]).get("generators")
    ids = sorted(
        str(g.get("id"))
        for g in (listed if isinstance(listed, list) else [])
        if isinstance(g, dict) and str(g.get("id")).startswith(f"{built.system}.")
    )
    for generator in ids:
        draft_id = ""
        try:
            drafted = runner.run(["gen", "run", generator, "--auto"])
            draft = drafted.get("draft")
            draft_id = str(draft.get("id")) if isinstance(draft, dict) else ""
            runner.run(["gen", "commit", draft_id])
            return
        except DidactError:
            if draft_id:  # it ran but wouldn't commit: leave no draft behind
                with contextlib.suppress(DidactError):
                    runner.run(["gen", "discard", draft_id])
    built.skip(
        "no generator ran on its own, so nothing was generated",
        _("no generator ran on its own, so nothing was generated"),
    )
