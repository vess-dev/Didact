"""Decks and bags: shuffled piles you draw from without replacement.

deck: tarot                       bag: initiative
cards: [The Fool, The Magician]   tokens: {pc: 2, enemy: "@enemies", end-of-round: 1}
standard: true   # 52 cards       ends_round: end-of-round
jokers: 2
"""

from didact.core.output import JSON
from didact.expr import HashStream

RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
SUITS = ("♠", "♥", "♦", "♣")


def cards(data: dict[str, JSON]) -> list[str]:
    found: list[str] = []
    if data.get("standard"):
        found = [f"{rank}{suit}" for suit in SUITS for rank in RANKS]
    raw = data.get("cards")
    if isinstance(raw, list):
        found += [str(c.get("name") if isinstance(c, dict) else c) for c in raw]
    jokers = data.get("jokers", 0)
    found += [f"Joker {i + 1}" for i in range(jokers if isinstance(jokers, int) else 0)]
    return found


def tokens(data: dict[str, JSON], counts: dict[str, int]) -> list[str]:
    """A bag's tokens, with counts from the bag (numbers) or given at fill time."""
    found: list[str] = []
    raw = data.get("tokens")
    for name, count in raw.items() if isinstance(raw, dict) else []:
        n = counts.get(name, count if isinstance(count, int) else 0)
        found += [name] * max(n, 0)
    return found


def shuffled(items: list[str], stream: str) -> list[str]:
    """Fisher–Yates with a Didact stream: the same stream always gives the same order."""
    source = HashStream(stream)
    order = list(items)
    for i in range(len(order) - 1, 0, -1):
        j = source.below(i + 1)
        order[i], order[j] = order[j], order[i]
    return order


def pile(state: dict[str, JSON], name: str) -> dict[str, JSON]:
    found = state.get(name)
    return found if isinstance(found, dict) else {}
