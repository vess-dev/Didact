"""A small pack with a Python dice plugin, written into a test's own folder: a dice effect
(`3d6~`: every top face adds a d4 that can't explode), a symbol die and a macro."""

from pathlib import Path

PLUGIN = '''"""The `lucky` test pack: a dice effect added without touching Didact's core."""

from didact.expr import DiePool, RollContext, modifier


@modifier("charm", token="~")  # "3d6~": every top face adds a d4 that can't explode
def charm(pool: DiePool, ctx: RollContext, arg: int | None) -> DiePool:
    """Every die showing its highest face is lucky: add a d4 that can't explode."""
    for die in list(pool.kept()):
        if die.value == die.sides:
            pool.add(ctx.roll("d4"), reason="charm", explode=False)
    return pool
'''

MANIFEST = """id: lucky
name: Lucky (test pack)
kind: supplement
version: 0.1.0
description: A test pack that adds a dice effect, a named die and a macro.
requires: {didact: ">=0.1", packs: [core]}
license: {spdx: CC0-1.0}
plugins: [plugins/lucky.py]
"""

DICE = """dice:
  clover: [blank, blank, hit, hit, hit+hit, charm]
macros:
  best: {params: [die], expr: "{$die, $die}kh1", summary: "Roll twice, keep the better"}
"""


def write(folder: Path) -> Path:
    """Write the pack to `folder/lucky` and return that folder."""
    pack = folder / "lucky"
    (pack / "plugins").mkdir(parents=True, exist_ok=True)
    (pack / "pack.yaml").write_text(MANIFEST, encoding="utf-8")
    (pack / "dice.yaml").write_text(DICE, encoding="utf-8")
    (pack / "GUIDE.md").write_text("# Lucky\n\nA dice effect, a named die and a macro.\n")
    (pack / "plugins" / "lucky.py").write_text(PLUGIN, encoding="utf-8")
    return pack
