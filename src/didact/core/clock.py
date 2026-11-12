"""Real-world timestamps (in-game time lives in the play layer)."""

from datetime import UTC, datetime


def local_display(timestamp: str) -> str:
    """An ISO UTC timestamp shown in local time: `YYYY-MM-DD HH:MM`."""
    try:
        moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return timestamp
    return moment.astimezone().strftime("%Y-%m-%d %H:%M")


def now_iso() -> str:
    """Current UTC time as an ISO-8601 string with seconds precision: `YYYY-MM-DDTHH:MM:SSZ`."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
