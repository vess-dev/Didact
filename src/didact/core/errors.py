"""Errors that say what went wrong, where, and how to fix it."""


class DidactError(Exception):
    """Base error. Every error carries a message, and ideally a location and a fix."""

    code: str = "error"
    exit_code: int = 1

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        where: str | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.where = where
        if code is not None:
            self.code = code

    def to_data(self) -> dict[str, str]:
        data = {"code": self.code, "message": self.message}
        if self.where:
            data["where"] = self.where
        if self.hint:
            data["hint"] = self.hint
        return data


class UsageError(DidactError):
    """The command line itself is wrong (unknown command, bad option, missing argument)."""

    code = "usage"
    exit_code = 2


class NotFoundError(DidactError):
    """A named thing (entity, world, pack, table, …) does not exist in the visible scopes."""

    code = "not_found"


class InvalidError(DidactError):
    """Data failed validation."""

    code = "invalid"


class UnknownName(InvalidError):
    """An expression names something that isn't there: a `variable` (`@STR`), a `die`
    (`[fate]`) or a `name` (a function or macro). Callers decide by `what`, never by the
    message, which is in the user's language."""

    def __init__(
        self, message: str, *, what: str, hint: str | None = None, where: str | None = None
    ) -> None:
        super().__init__(message, hint=hint, where=where)
        self.what = what


class ConflictError(DidactError):
    """The change clashes with existing state (duplicate id, references still pointing at it, …)."""

    code = "conflict"


class StorageError(DidactError):
    """The disk refused: it's full or read-only, or a file can't be reached."""

    code = "storage"
