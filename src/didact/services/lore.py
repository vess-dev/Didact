"""Lore: keyword-triggered memory. Mention a thing and what Didact knows about it comes back.

Three kinds of records come up in a scan:
- **lore entries** (`lore` records): `keys`, content in the body, and the options below;
- **cards**: every world record (NPC, place, item, faction, quest, …), keyed by its name and
  aliases, shown as a 2–4 line card;
- **rulings**, keyed by their `keys`, else the rule they settle and their tags.

Lore entry fields (all optional but `keys`):

    keys: [sweeney, ferryman]        # words or phrases (whole words, plurals too), or /regex/
    secondary: [river]               # with logic: and_any (default) | and_all | not_any | not_all
    priority: 50                     # higher first; the budget cuts from the bottom
    kind: lore                       # lore | memory | rule-reminder | preference | secret
    constant: true                   # always in the brief and every scan
    probability: 50                  # percent; drawn per turn from the campaign's seed
    group: weather                   # only the best entry of a group comes back
    sticky: 2 / cooldown: 3 / delay: 1   # in turns, or "2 scenes"
    recursive: false                 # its content doesn't trigger further entries

Scopes never leak: a scan sees the campaign, its world, its system and global, nothing else.
A narrower entry with the same id shadows a wider one.
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import cast

from didact.core import labels
from didact.core.errors import DidactError, InvalidError
from didact.core.i18n import _, ngettext, pgettext
from didact.core.ids import EntityId, Scope
from didact.core.output import JSON
from didact.schema.sheet import Sheet
from didact.services import knowledge, packs, sheets, state
from didact.store import triggers
from didact.store.changeset import Changeset
from didact.store.entity import Entity
from didact.store.index import Trigger
from didact.store.repo import Repo

KINDS = ("lore", "memory", "rule-reminder", "preference", "secret")
LOGIC = ("and_any", "and_all", "not_any", "not_all")
PRIORITY = {"lore": 50, "ruling": 60, "card": 40}
BUDGET = 600  # tokens (about 4 characters each)
DEPTH = 2  # how many times fired content may trigger more entries
DEDUPE = 6  # turns before an entry is pushed again (hooks, `log`, `scene new`)
LORE = "lore"  # campaign state: when entries last fired


@dataclass(slots=True)
class Hit:
    entity: Entity
    scope: Scope
    source: str  # lore | ruling | card
    reason: str  # 'key "sweeney"', 'constant', 'sticky', 'via lore:x'
    position: int
    priority: int
    text: str = ""
    secret: bool = False

    @property
    def tokens(self) -> int:
        return max(1, len(self.text) // 4)

    def line(self) -> str:
        what = self.source if self.source != "lore" else str(self.entity.fields.get("kind", "lore"))
        said = labels.inline(what, labels.lore_kind(what))
        values = {"id": self.entity.id, "what": said, "reason": said_reason(self.reason)}
        if self.secret:
            return _("[{id}] ({what}; {reason} · GM only) {text}", text=self.text, **values)
        return _("[{id}] ({what}; {reason}) {text}", text=self.text, **values)


def said_reason(reason: str) -> str:
    """Why an entry came up, in the reader's language (`Hit.reason` is also a key)."""
    if reason == "constant":
        return pgettext("lore", "constant")
    if reason == "sticky":
        return pgettext("lore", "sticky")
    if reason.startswith('key "') and reason.endswith('"'):
        return _('key "{key}"', key=reason[5:-1])
    if reason.startswith("via "):
        return _("via {id}", id=reason[4:])
    return reason


@dataclass(slots=True)
class Scan:
    hits: list[Hit] = field(default_factory=list)
    omitted: list[Hit] = field(default_factory=list)
    hidden: int = 0  # secret hits left out of a player-safe scan
    skipped: dict[str, str] = field(default_factory=dict)  # id → why it didn't fire

    def lines(self) -> list[str]:
        out = [f"- {h.line()}" for h in self.hits]
        if self.omitted:
            out.append(
                ngettext(
                    "({n} more omitted: raise --budget to see them)",
                    "({n} more omitted: raise --budget to see them)",
                    len(self.omitted),
                )
            )
        if self.hidden:
            out.append(
                ngettext(
                    "({n} secret entry hidden; --gm)",
                    "({n} secret entries hidden; --gm)",
                    self.hidden,
                )
            )
        return out


# ---------------------------------------------------------------------------- timing


@dataclass(slots=True)
class Clock:
    """Where play is: turn and scene numbers, and when each entry last fired."""

    turn: int = 0
    scene: int = 0
    fired: dict[str, list[int]] = field(default_factory=dict)  # id → [turn, scene]


def clock(repo: Repo) -> Clock:
    if repo.active_campaign() is None:
        return Clock()
    from didact.services import play

    turn_state = state.load(repo, "turn")
    count = turn_state.get("count")
    saved = state.load(repo, LORE).get("fired")
    fired = {
        str(k): [int(x) for x in cast(list[int], v)]
        for k, v in (saved.items() if isinstance(saved, dict) else [])
        if isinstance(v, list) and len(v) == 2
    }
    return Clock(count if isinstance(count, int) else 0, play.load(repo).scene, fired)


def record(cs: Changeset, now: Clock, hits: list[Hit]) -> None:
    """Remember that these entries fired now (for cooldowns, sticky entries and dedupe)."""
    if cs.repo.active_campaign() is None or not hits:
        return
    fired = {k: list[JSON](v) for k, v in now.fired.items()}
    for hit in hits:
        fired[str(hit.entity.id)] = [now.turn, now.scene]
    data = state.load(cs.repo, LORE)
    state.plan(cs, LORE, {**data, "fired": cast(JSON, fired)})


def _span(raw: JSON) -> tuple[int, str] | None:
    """`3` → (3, turns); "2 scenes" → (2, scenes)."""
    if isinstance(raw, int) and not isinstance(raw, bool):
        return raw, "turns"
    if isinstance(raw, str):
        match = re.fullmatch(r"\s*(\d+)\s*(turns?|scenes?)?\s*", raw)
        if match:
            unit = "scenes" if (match.group(2) or "").startswith("scene") else "turns"
            return int(match.group(1)), unit
    return None


def _since(now: Clock, entity_id: str, unit: str) -> int | None:
    last = now.fired.get(entity_id)
    if last is None:
        return None
    return (now.turn - last[0]) if unit == "turns" else (now.scene - last[1])


# ---------------------------------------------------------------------------- cards


def card(entity: Entity, sh: Sheet, *, gm: bool, hid: knowledge.Unknown = knowledge.NOTHING) -> str:
    """2–4 lines: who or what it is, its numbers, its first paragraph (and a secret, for GMs).
    `hid`: what a player's card mustn't name."""
    shown = entity if gm else knowledge.player_copy(entity, sh, hid)[0]
    label = entity.type
    facts = [
        str(v)
        for k, v in shown.fields.items()
        if k in ("role", "description", "agenda", "goal", "region") and isinstance(v, str) and v
    ]
    head = f"{shown.name} ({label})" + (": " + "; ".join(facts[:2]) if facts else "")
    stats = sheets.stat_line(shown, sh)
    lines = [head + (f" · {stats}" if stats else "")]
    body, _hidden = knowledge.player_body(shown.body) if not gm else (shown.body, 0)
    paragraph = next(
        (p.strip() for p in body.split("\n\n") if p.strip() and not p.startswith("#")), ""
    )
    if paragraph:
        lines.append(_clip(" ".join(paragraph.split()), 240))
    if gm:
        secrets = knowledge.secret_lines(entity.body)
        if secrets:
            lines.append("secret: " + secrets[0].lstrip("-* ").strip())
    return " / ".join(lines)


def _clip(text: str, size: int) -> str:
    return text if len(text) <= size else text[: size - 1].rsplit(" ", 1)[0] + "…"


def _content(entity: Entity, source: str, repo: Repo, gm: bool) -> str:
    if source == "card":
        hid = knowledge.NOTHING if gm else knowledge.unknown(repo)
        return card(entity, sheets.sheet(repo, entity.type), gm=gm, hid=hid)
    if source == "ruling":
        question = entity.fields.get("question", entity.name)
        return f"Ruling: {question} → {entity.fields.get('ruling', entity.body.strip())}"
    body = entity.body.strip() if gm else knowledge.player_body(entity.body)[0].strip()
    return " ".join(body.split())


# ---------------------------------------------------------------------------- scanning


def _secondary(entity: Entity, tokens: list[str], at: dict[str, list[int]], text: str) -> bool:
    raw = entity.fields.get("secondary")
    keys = [str(k) for k in raw] if isinstance(raw, list) else []
    if not keys:
        return True
    logic = str(entity.fields.get("logic", "and_any"))
    found = [_matches(key, tokens, at, text) is not None for key in keys]
    match logic:
        case "and_all":
            return all(found)
        case "not_any":
            return not any(found)
        case "not_all":
            return not all(found)
        case _:
            return any(found)


def _matches(key: str, tokens: list[str], at: dict[str, list[int]], text: str) -> int | None:
    if triggers.is_regex(key):
        try:
            found = re.search(key[1:-1], text, re.IGNORECASE)
        except re.error:
            return None
        return len(triggers.words(text[: found.start()])) if found else None
    spots = [triggers.find(p, tokens, at) for p in triggers.phrases(key)]
    hits = [s for s in spots if s is not None]
    return min(hits) if hits else None


def _chance(repo: Repo, entity: Entity, now: Clock) -> bool:
    raw = entity.fields.get("probability")
    if not isinstance(raw, int | float) or raw >= 100:
        return True
    campaign = repo.active_campaign()
    seed = str(campaign.other.get("seed")) if campaign is not None else "lore"
    digest = hashlib.sha256(f"{seed}:{entity.id}:{now.turn}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 100 < raw


def _timing(entity: Entity, now: Clock) -> str | None:
    """Why the entry can't fire now (delay, cooldown), or None."""
    delay = _span(entity.fields.get("delay"))
    if delay is not None:
        count, unit = delay
        current = now.turn if unit == "turns" else now.scene
        if current < count:
            if unit == "turns":
                return _("delayed until turn {count}", count=count)
            return _("delayed until scene {count}", count=count)
    cooldown = _span(entity.fields.get("cooldown"))
    if cooldown is not None:
        count, unit = cooldown
        since = _since(now, str(entity.id), unit)
        if since is not None and since <= count:
            if unit == "turns":
                return _("cooling down ({since} of {count} turns)", since=since, count=count)
            return _("cooling down ({since} of {count} scenes)", since=since, count=count)
    return None


def _sticky(entity: Entity, now: Clock) -> bool:
    span = _span(entity.fields.get("sticky"))
    if span is None:
        return False
    since = _since(now, str(entity.id), span[1])
    return since is not None and 0 < since <= span[0]


def scan(
    repo: Repo,
    text: str,
    *,
    gm: bool,
    budget: int = BUDGET,
    now: Clock | None = None,
    dedupe: bool = False,
) -> Scan:
    """What `text` brings up here, best first, within the budget."""
    result = Scan()
    if repo.active_world() is None:
        return result
    now = now or clock(repo)
    chain = repo.chain()
    rank = {str(s): i for i, s in enumerate(chain)}
    found: dict[str, Hit] = {}
    shipped = pack_entries(repo)  # once per scan: loading the pack set isn't free
    _pass(repo, text, chain, rank, now, gm, found, result, shipped, reason_via=None)
    for _depth in range(DEPTH):  # fired content may bring up more
        fresh = [h for h in list(found.values()) if h.source == "lore" and _recursive(h)]
        before = set(found)
        for hit in fresh:
            _pass(repo, hit.text, chain, rank, now, gm, found, result, shipped, reason_via=hit)
        if set(found) == before:
            break
    hits = _best_of_groups(list(found.values()))
    if dedupe:
        hits = [h for h in hits if not _recent(h, now)]
    visible = [h for h in hits if gm or not h.secret]
    result.hidden = len(hits) - len(visible)
    visible.sort(key=lambda h: (-h.priority, h.position, str(h.entity.id)))
    used = 0
    for hit in visible:
        if used >= budget and result.hits:
            result.omitted.append(hit)
            continue
        if not hit.text:
            hit.text = _content(hit.entity, hit.source, repo, gm or hit.secret)
        if used + hit.tokens > budget and result.hits:
            result.omitted.append(hit)
            continue
        used += hit.tokens
        result.hits.append(hit)
    return result


def _recursive(hit: Hit) -> bool:
    """Whether a hit's content may bring up more entries (constant ones never do)."""
    return hit.reason != "constant" and hit.entity.fields.get("recursive", True) is not False


def _recent(hit: Hit, now: Clock) -> bool:
    if hit.entity.fields.get("constant") is True or hit.reason == "sticky":
        return False
    since = _since(now, str(hit.entity.id), "turns")
    return since is not None and since < DEDUPE


def _pass(
    repo: Repo,
    text: str,
    chain: list[Scope],
    rank: dict[str, int],
    now: Clock,
    gm: bool,
    found: dict[str, Hit],
    result: Scan,
    shipped: list[tuple[Entity, Scope]],
    *,
    reason_via: Hit | None,
) -> None:
    tokens = triggers.words(text)
    at = triggers.positions(tokens)
    index = repo.index()
    best: dict[str, tuple[Trigger, int, str]] = {}  # path → (trigger, position, reason)
    for trig in index.triggered(tokens, chain):
        if trig.kind == "constant":
            if reason_via is None:
                best.setdefault(trig.path, (trig, -1, "constant"))
            continue
        spot = (
            _matches(trig.phrase, tokens, at, text)
            if trig.kind == "regex"
            else triggers.find(tuple(trig.phrase.split()), tokens, at)
        )
        if spot is None:
            continue
        reason = f'key "{trig.phrase}"' if reason_via is None else f"via {reason_via.entity.id}"
        if trig.path not in best or spot < best[trig.path][1]:
            best[trig.path] = (trig, spot, reason)
    if reason_via is None:  # sticky entries stay on for a while after they fire
        for entity_id in now.fired:
            rows = [r for r in index.by_id(entity_id, chain) if r.type == "lore"]
            if not rows or any(r.path in best for r in rows):
                continue
            narrowest = min(rows, key=lambda r: rank.get(str(r.scope), 99))
            if _sticky(narrowest.entity(), now):
                sticky = Trigger(narrowest.path, narrowest.scope, "", "sticky", "lore")
                best[narrowest.path] = (sticky, 10**6, "sticky")
    loaded = {row.path: row for row in index.by_paths(best)}
    candidates: list[tuple[Entity, Scope, str, int, str]] = []
    for path, (trig, spot, reason) in best.items():
        found_row = loaded.get(path)
        if found_row is not None:
            candidates.append((found_row.entity(), trig.scope, trig.source, spot, reason))
    candidates += _pack_matches(shipped, tokens, at, text, reason_via)
    for entity, scope, source, spot, reason in candidates:
        key = str(entity.id)
        known = found.get(key)
        if known is not None and rank.get(str(known.scope), 99) <= rank.get(str(scope), 99):
            continue  # a narrower record with this id already came up
        if source == "lore" and reason != "sticky":
            why = _why_not(repo, entity, tokens, at, text, now)
            if why is not None:
                result.skipped[key] = why
                continue
        secret = entity.knowledge == "secret" or entity.fields.get("kind") == "secret"
        priority = entity.fields.get("priority")
        found[key] = Hit(
            entity,
            scope,
            source,
            reason,
            spot,
            priority if isinstance(priority, int) else PRIORITY[source],
            _content(entity, "lore", repo, gm or secret) if source == "lore" else "",
            secret,
        )  # cards and rulings are written out later, only if they make the budget


def pack_entries(repo: Repo) -> list[tuple[Entity, Scope]]:
    """Lore the enabled packs ship (`lore/*.yaml`), as entries in their system's scope."""
    try:
        active = packs.active(repo)
    except DidactError:
        return []
    found: list[tuple[Entity, Scope]] = []
    for item in active.all("lore"):
        data = item.data
        skip = ("lore", "content", "title", "source", "tags")
        fields = {k: v for k, v in data.items() if k not in skip}
        raw_tags = data.get("tags")
        entity = Entity(
            id=EntityId("lore", item.id),
            name=str(data.get("title") or item.id),
            tags=[str(t) for t in raw_tags] if isinstance(raw_tags, list) else [],
            fields=fields,
            body=str(data.get("content", "")).strip() + "\n",
        )
        found.append((entity, Scope("system", item.pack)))
    return found


def _pack_matches(
    shipped: list[tuple[Entity, Scope]],
    tokens: list[str],
    at: dict[str, list[int]],
    text: str,
    reason_via: Hit | None,
) -> list[tuple[Entity, Scope, str, int, str]]:
    matched: list[tuple[Entity, Scope, str, int, str]] = []
    for entity, scope in shipped:
        if entity.fields.get("constant") is True:
            if reason_via is None:
                matched.append((entity, scope, "lore", -1, "constant"))
            continue
        keys = entity.fields.get("keys")
        spots = [
            (spot, str(key))
            for key in (keys if isinstance(keys, list) else [])
            if (spot := _matches(str(key), tokens, at, text)) is not None
        ]
        if spots:
            spot, key = min(spots)
            reason = f'key "{key}"' if reason_via is None else f"via {reason_via.entity.id}"
            matched.append((entity, scope, "lore", spot, reason))
    return matched


def _why_not(
    repo: Repo, entity: Entity, tokens: list[str], at: dict[str, list[int]], text: str, now: Clock
) -> str | None:
    if not _secondary(entity, tokens, at, text):
        return _("secondary keys ({logic}) not met", logic=entity.fields.get("logic", "and_any"))
    waiting = _timing(entity, now)
    if waiting is not None:
        return waiting
    if not _chance(repo, entity, now):
        return _(
            "probability {chance}% didn't come up this turn",
            chance=entity.fields.get("probability"),
        )
    return None


def _best_of_groups(hits: list[Hit]) -> list[Hit]:
    kept: dict[str, Hit] = {}
    loose: list[Hit] = []
    for hit in hits:
        group = hit.entity.fields.get("group")
        if not isinstance(group, str):
            loose.append(hit)
            continue
        current = kept.get(group)
        if current is None or (hit.priority, -hit.position) > (current.priority, -current.position):
            kept[group] = hit
    return loose + list(kept.values())


def constants(repo: Repo, *, gm: bool) -> list[Hit]:
    """Entries marked `constant`: always in the brief."""
    if repo.active_world() is None:
        return []
    return [h for h in scan(repo, "", gm=gm, budget=10**6).hits if h.reason == "constant"]


# ---------------------------------------------------------------------------- entries


def entry_fields(
    keys: list[str],
    *,
    secondary: list[str],
    logic: str | None,
    priority: int | None,
    kind: str | None,
    constant: bool,
    probability: int | None,
    group: str | None,
    sticky: str | None,
    cooldown: str | None,
    delay: str | None,
    recursive: bool,
) -> dict[str, JSON]:
    """A lore entry's fields, checked."""
    if not keys and not constant:
        raise InvalidError(
            _("a lore entry needs keys (or --constant)"), hint=_("e.g. --keys 'sweeney, ferryman'")
        )
    fields: dict[str, JSON] = {"keys": list[JSON](keys)}
    if secondary:
        fields["secondary"] = list[JSON](secondary)
        fields["logic"] = logic or "and_any"
    if logic and logic not in LOGIC:
        raise InvalidError(
            _("logic is one of {choices}", choices=", ".join(LOGIC)), hint=_("e.g. --logic and_any")
        )
    if priority is not None:
        fields["priority"] = priority
    if kind is not None:
        if kind not in KINDS:
            raise InvalidError(
                _("kind is one of {choices}", choices=", ".join(KINDS)), hint=_("e.g. --kind lore")
            )
        fields["kind"] = kind
    if constant:
        fields["constant"] = True
    if probability is not None:
        if not 0 <= probability <= 100:
            raise InvalidError(
                _("probability is a percent: 0–100"), hint=_("e.g. --probability 50")
            )
        fields["probability"] = probability
    if group:
        fields["group"] = group
    for name, raw in (("sticky", sticky), ("cooldown", cooldown), ("delay", delay)):
        if raw is None:
            continue
        span = _span(int(raw) if raw.isdigit() else raw)
        if span is None:
            raise InvalidError(
                _("--{name} takes turns or scenes", name=name),
                hint=_("e.g. --{name} 3 or --{name} '2 scenes'", name=name),
            )
        fields[name] = span[0] if span[1] == "turns" else f"{span[0]} scenes"
    if not recursive:
        fields["recursive"] = False
    return fields


SMALL = frozenset({"a", "an", "the", "of", "to", "in", "on", "at", "and", "or", "is", "was"})


def title_for(content: str) -> str:
    """A short title from the content: its first words, up to about 40 letters."""
    picked: list[str] = []
    for word in content.split():
        if picked and len(" ".join([*picked, word])) > 40:
            break
        picked.append(word.strip(".,;:!?"))
    while len(picked) > 1 and picked[-1].casefold() in SMALL:
        picked.pop()
    return " ".join(picked) or "lore"


def split_keys(raw: list[str] | None) -> list[str]:
    """`--keys 'a, b' --keys c` → [a, b, c] (a /regex/ is kept whole)."""
    found: list[str] = []
    for item in raw or []:
        if triggers.is_regex(item.strip()):
            found.append(item.strip())
            continue
        found += [k.strip() for k in item.split(",") if k.strip()]
    return found


def explain(repo: Repo, entity: Entity, text: str, *, gm: bool) -> list[str]:
    """Why an entry would or wouldn't come up for `text`."""
    found = triggers.keys_of(entity)
    if found is None:
        return [
            _(
                "{id} never comes up in scans (it's a {type} record)",
                id=entity.id,
                type=entity.type,
            )
        ]
    keys, source = found
    tokens = triggers.words(text)
    at = triggers.positions(tokens)
    lines = [
        _(
            "{id} ({source}) keys: {keys}",
            id=entity.id,
            source=source,
            keys=", ".join(keys) or _("(none)"),
        )
    ]
    matched = [k for k in keys if _matches(k, tokens, at, text) is not None]
    too_short = [k for k in keys if not triggers.is_regex(k) and not triggers.phrases(k)]
    if too_short:
        lines.append(
            _(
                "ignored (shorter than {count} letters): {keys}",
                count=triggers.MIN_KEY,
                keys=", ".join(too_short),
            )
        )
    if entity.fields.get("constant") is True:
        lines.append(_("constant: it always comes up"))
    elif not matched:
        lines.append(_("no key appears in the text (whole words, plurals count)"))
    else:
        lines.append(_("matched: {keys}", keys=", ".join(matched)))
    if source == "lore":
        now = clock(repo)
        why = _why_not(repo, entity, tokens, at, text, now)
        lines.append(
            _("blocked: {why}", why=why)
            if why
            else _("nothing blocks it (secondary keys, timing, probability)")
        )
        if _sticky(entity, now):
            lines.append(_("sticky: still on from an earlier turn"))
    scope_ok = any(str(s) == str(sc) for s in repo.chain() for sc in [_scope_of(repo, entity)])
    if not scope_ok:
        lines.append(
            _("out of scope here: scans only see this campaign, its world, system and global")
        )
    if (entity.knowledge == "secret" or entity.fields.get("kind") == "secret") and not gm:
        lines.append(_("secret: player-safe scans hide it (hooks and --gm include it)"))
    return lines


def _scope_of(repo: Repo, entity: Entity) -> Scope | None:
    try:
        rows = repo.index().by_id(str(entity.id))
    except DidactError:
        return None
    return rows[0].scope if rows else None
