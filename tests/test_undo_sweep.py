"""The undo sweep: undo takes a whole session back, byte for byte, and redo brings it all back.

It catches any command that writes around the changesets, or undoes only part of what it did.
Outside undo, by design: the event log and counters (numbers never repeat), which world and
campaign are active, backups, and the lock and staging files.
"""

import difflib
import shlex
from pathlib import Path

from tests.conftest import Cli

SESSION = """
world new vale --system mini-system
pack enable leap-setting
campaign new run --date '23 October 2102'
new pc Freya --fill
new npc 'Old Tom' --body 'Runs the mill.' --tag miller
new loc 'The Mill'
new loc 'Old Bridge'
new item 'Silver Key'
link 'Old Tom' lives-at 'The Mill'
link 'The Mill' road 'Old Bridge'
set 'Old Tom' mood=grim coins=3
set 'Old Tom' coins+=2
edit 'Old Tom' --data '{"body": "Runs the mill.\\nOwes the witch.\\n"}'
about 'Old Tom' plan=flee looks=tall
note 'Old Tom' 'Hates geese'
rename 'Old Tom' 'Tom Miller'
inv add freya Rope Torch
inv add 'The Mill' 'Silver Key'
inv move freya Rope 'The Mill'
inv use freya Torch
visit 'The Mill'
time set '1 November 2102'
session start
scene new 'The drowned mill'
log consequence 'Tom lied' --about npc:old-tom
log note 'Raiders gather' --secret
report 'the tower stands' --of tower --about npc:old-tom
beat edit S1.2 --text 'Raiders gather at the ford'
time advance '2 hours'
remind 'Rations low' --in '1 day'
quest new 'Free the spirit'
track new Doom --kind clock --size 6
track tick doom
new npc Goblin
combat start --party goblin
combat next
combat leave goblin --why fled
combat end
lore add 'Tom owes the witch' --keys 'tom, witch'
ruling add 'Can you swim in armor?' 'No'
names use Brannoc --for 'the ferryman'
save 'before the end'
archive 'Silver Key'
party add npc:old-tom --as companion
party remove npc:old-tom --why left
reveal npc:old-tom plan
rm goblin
scene end --summary 'They left.'
session end --summary 'A start.'
"""
OUTSIDE_UNDO = ("log/", "state.yaml", ".lock", ".staging/", "backups/")


def _files(home: Path) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    for path in sorted(home.rglob("*")):
        rel = path.relative_to(home).as_posix()
        if path.is_file() and not rel.startswith(OUTSIDE_UNDO):
            found[rel] = path.read_bytes()
    return found


def _differences(want: dict[str, bytes], got: dict[str, bytes]) -> str:
    lines: list[str] = []
    for name in sorted(set(want) | set(got)):
        if want.get(name) == got.get(name):
            continue
        if name not in got or name not in want:
            lines.append(f"{name}: {'missing' if name not in got else 'left over'}")
            continue
        lines.append(f"{name}: changed")
        diff = difflib.unified_diff(
            want[name].decode(errors="replace").splitlines(),
            got[name].decode(errors="replace").splitlines(),
            lineterm="",
        )
        lines += [f"    {line}" for line in list(diff)[2:14]]
    return "\n".join(lines)


def _all_the_way(cli: Cli, command: str) -> int:
    for count in range(500):
        result = cli(command)
        assert result.code == 0, result.err
        if result.out.startswith("nothing to"):
            return count
    raise AssertionError(f"{command} never ran out")


def test_undo_takes_a_whole_session_back_and_redo_replays_it(cli: Cli, home: Path) -> None:
    start = _files(home)
    lines = [line for line in SESSION.strip().splitlines() if line.strip()]
    for line in lines:
        result = cli(*shlex.split(line))
        assert result.code == 0, (line, result.err)
    end = _files(home)
    undone = _all_the_way(cli, "undo")
    assert undone >= len(lines)  # some commands make more than one change
    assert _files(home) == start, _differences(start, _files(home))
    assert _all_the_way(cli, "redo") == undone
    assert _files(home) == end, _differences(end, _files(home))
