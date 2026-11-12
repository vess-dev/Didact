"""Where dice faces come from: a portable seeded stream, or faces typed in from physical dice.

The stream is counter-based: draw k of stream `key` is SHA-256(`key:k`), rejection-sampled.
That makes every roll reproducible from (key, expression) alone, on any machine or Python.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Protocol

from didact.core.errors import InvalidError
from didact.core.i18n import _
from didact.expr.model import DieSpec, Face

_SPAN = 2**64


class Source(Protocol):
    def draw(self, die: DieSpec) -> Face:
        """The face this die shows (value and symbols)."""
        ...


@dataclass(slots=True)
class HashStream:
    key: str
    counter: int = 0

    def below(self, n: int) -> int:
        """Uniform integer in [0, n)."""
        limit = (_SPAN // n) * n
        while True:
            digest = hashlib.sha256(f"{self.key}:{self.counter}".encode()).digest()
            self.counter += 1
            value = int.from_bytes(digest[:8], "big")
            if value < limit:
                return value % n

    def draw(self, die: DieSpec) -> Face:
        match die.kind:
            case "numeric":
                return Face(1 + self.below(die.sides))
            case "fudge":
                return Face(self.below(3) - 1)
            case "digit":
                digits = [1 + self.below(die.sides) for _unused in range(die.digits)]
                return Face(int("".join(map(str, digits))))
            case "custom":
                return die.faces[self.below(len(die.faces))]


@dataclass(slots=True)
class PhysicalFaces:
    """Faces read off real dice (`--got 6,3,4`), consumed in the order dice are rolled."""

    tokens: list[str]
    used: int = 0
    record: list[str] = field(default_factory=list)

    @classmethod
    def parse(cls, text: str) -> PhysicalFaces:
        tokens = [t.strip() for t in text.replace(" ", ",").split(",") if t.strip()]
        if not tokens:
            raise InvalidError(_("--got needs faces"), hint=_("e.g. `--got 6,3,4`"))
        return cls(tokens)

    def draw(self, die: DieSpec) -> Face:
        if self.used >= len(self.tokens):
            raise InvalidError(
                _(
                    "--got ran out of faces: this roll needs another d{die} "
                    "(dice are read in the order rolled, including explosions and rerolls)",
                    die=die.text,
                ),
                hint=_("add the missing faces to --got"),
            )
        token = self.tokens[self.used]
        self.used += 1
        self.record.append(token)
        return _face_from_text(die, token)

    def leftover(self) -> list[str]:
        return self.tokens[self.used :]


def _face_from_text(die: DieSpec, token: str) -> Face:
    def bad() -> InvalidError:
        return InvalidError(
            _("{token} isn't a face of d{die}", token=repr(token), die=die.text),
            hint=_("check the --got faces"),
        )

    match die.kind:
        case "numeric":
            if not token.lstrip("-").isdigit() or not 1 <= int(token) <= die.sides:
                raise bad()
            return Face(int(token))
        case "fudge":
            mapping = {"+": 1, "1": 1, "+1": 1, "-": -1, "-1": -1, "0": 0}
            if token not in mapping:
                raise bad()
            return Face(mapping[token])
        case "digit":
            if len(token) != die.digits or not all(
                c.isdigit() and 1 <= int(c) <= die.sides for c in token
            ):
                raise bad()
            return Face(int(token))
        case "custom":
            for face in die.faces:
                if token == face.text() or (
                    token in ("-", "blank", "·") and not face.symbols and face.value == 0
                ):
                    return face
            raise bad()
