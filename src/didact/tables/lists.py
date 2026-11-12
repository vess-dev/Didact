"""Weighted lists an oracle keeps (threads, characters), and rolling on one.

A list is plain text lines in order; an entry listed twice is on two lines, so it comes up
twice as often. Two ways to roll:

- `uniform`: one die over the lines.
- `sections`: lines fill sections of 5, up to 5 sections (25 lines). With more than
  one section in use, a die picks the section: d4 for two, d6 for three, d8 for four, d10 for
  five, read in pairs (1–2 is the first). Then a d10 read in pairs picks the line. A line past
  the last entry is blank: choose something yourself (or roll again).
"""

import math
from dataclasses import dataclass

from didact.core.i18n import _, ngettext

METHODS = ("sections", "uniform")
SECTION = 5  # lines per section
SECTIONS = 5  # sections per list


@dataclass(frozen=True, slots=True)
class Pick:
    entry: str | None  # None: a blank line (choose), or nothing listed yet
    line: int | None  # 1-based
    how: str  # "section 2 (d4 → 3), line 4 (d10 → 8)"

    @property
    def choose(self) -> bool:
        return self.entry is None and self.line is not None


def capacity(method: str) -> int | None:
    return SECTION * SECTIONS if method == "sections" else None


def dice_for(count: int, method: str) -> list[str]:
    """The dice to roll for a list of `count` lines, in order."""
    if count <= 0:
        return []
    if method == "uniform":
        return [f"d{count}"]
    sections = min(SECTIONS, math.ceil(count / SECTION))
    return ([f"d{sections * 2}"] if sections > 1 else []) + [f"d{SECTION * 2}"]


def pick(entries: list[str], method: str, faces: list[int]) -> Pick:
    """Read the dice (`faces`, one per die from `dice_for`) against the list."""
    if not entries:
        return Pick(None, None, _("nothing listed"))
    if method == "uniform":
        line = faces[0]
        return Pick(entries[line - 1], line, _("line {n}", n=line))
    sections = min(SECTIONS, math.ceil(len(entries) / SECTION))
    section = math.ceil(faces[0] / 2) if sections > 1 else 1
    line_face = faces[-1]
    line = (section - 1) * SECTION + math.ceil(line_face / 2)
    parts = [_("line {n} ({die} → {face})", n=line, die=f"d{SECTION * 2}", face=line_face)]
    if sections > 1:
        die = f"d{sections * 2}"
        parts.insert(0, _("section {n} ({die} → {face})", n=section, die=die, face=faces[0]))
    how = ", ".join(parts)
    if line > len(entries):
        return Pick(None, line, _("{how}: blank, choose", how=how))
    return Pick(entries[line - 1], line, how)


def add(entries: list[str], entry: str, times: int, most: int, room: int | None) -> list[str]:
    """Add `times` more lines for `entry` (at most `most` in all). Raises ValueError."""
    already = sum(1 for e in entries if e.casefold() == entry.casefold())
    if already + times > most:
        raise ValueError(
            _(
                "{entry} is listed {already} times; the most is {most}",
                entry=repr(entry),
                already=already,
                most=most,
            )
        )
    if room is not None and len(entries) + times > room:
        raise ValueError(_("the list is full ({room} lines)", room=room))
    return [*entries, *([entry] * times)]


def drop(entries: list[str], entry: str, *, every: bool) -> tuple[list[str], int]:
    """Take one line of `entry` off (the last), or every line. Returns the list and how many."""
    matches = [i for i, e in enumerate(entries) if e.casefold() == entry.casefold()]
    if not matches:
        return entries, 0
    gone = set(matches) if every else {matches[-1]}
    return [e for i, e in enumerate(entries) if i not in gone], len(gone)


def lines(name: str, entries: list[str], method: str) -> list[str]:
    """A list as numbered lines (in sections of 5 for `sections`), duplicates marked ×n."""
    if not entries:
        return [_("{name}: (empty)", name=name)]
    out = [ngettext("{name}: {n} line", "{name}: {n} lines", len(entries), name=name)]
    for index, entry in enumerate(entries, start=1):
        weight = sum(1 for e in entries if e.casefold() == entry.casefold())
        mark = f" (×{weight})" if weight > 1 else ""
        if method == "sections" and index % SECTION == 1 and len(entries) > SECTION:
            out.append("  " + _("section {n}", n=math.ceil(index / SECTION)))
        out.append(f"  {index}. {entry}{mark}")
    return out
