"""Pack versions (`1.2.0`, `0.3.0-beta.1`) and requirement ranges (`>=0.1, <2`)."""

import re
from dataclasses import dataclass
from functools import total_ordering

from didact.core.errors import InvalidError
from didact.core.i18n import _

_VERSION = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-.]?([0-9A-Za-z.-]+))?$")
_CLAUSE = re.compile(r"^(>=|<=|==|!=|~=|>|<|=)?\s*(\S+)$")


@total_ordering
@dataclass(frozen=True, slots=True)
class Version:
    major: int
    minor: int = 0
    patch: int = 0
    pre: str = ""  # a pre-release sorts before the release: 1.0.0-beta < 1.0.0

    @classmethod
    def parse(cls, text: str) -> Version:
        match = _VERSION.match(text.strip())
        if not match:
            raise InvalidError(
                _("invalid version {text}", text=repr(text)),
                hint=_("use MAJOR.MINOR.PATCH, e.g. 0.1.0"),
            )
        major, minor, patch, pre = match.groups()
        return cls(int(major), int(minor or 0), int(patch or 0), pre or "")

    def _key(self) -> tuple[int, int, int, int, str]:
        return (self.major, self.minor, self.patch, 0 if self.pre else 1, self.pre)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() < other._key()

    def __str__(self) -> str:
        text = f"{self.major}.{self.minor}.{self.patch}"
        return f"{text}-{self.pre}" if self.pre else text


def satisfies(version: str | Version, spec: str) -> bool:
    """`satisfies("0.2.1", ">=0.1, <1")`; an empty spec accepts anything."""
    have = version if isinstance(version, Version) else Version.parse(version)
    for raw in spec.split(","):
        clause = raw.strip()
        if not clause or clause == "*":
            continue
        match = _CLAUSE.match(clause)
        if not match:
            raise InvalidError(
                _("invalid version range {spec}", spec=repr(spec)), hint=_("e.g. `>=0.1, <2`")
            )
        op, text = match.group(1) or "==", match.group(2)
        want = Version.parse(text)
        ok = {
            ">=": have >= want,
            "<=": have <= want,
            ">": have > want,
            "<": have < want,
            "==": have == want,
            "=": have == want,
            "!=": have != want,
            "~=": have >= want
            and have.major == want.major
            and (want.major > 0 or have.minor == want.minor),
        }[op]
        if not ok:
            return False
    return True


def parse_requirement(text: str) -> tuple[str, str]:
    """`"core >=0.1"` → ("core", ">=0.1"); `"core"` → ("core", "")."""
    match = re.match(r"^\s*([a-z0-9][a-z0-9-]*)\s*(.*)$", text)
    if not match:
        raise ValueError(_("invalid pack requirement {text}", text=repr(text)))
    return match.group(1), match.group(2).strip()
