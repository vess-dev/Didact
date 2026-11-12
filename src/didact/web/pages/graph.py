"""The graph: records as nodes and their links as edges, drawn by `graph.js`.

`/api/graph` reads the index directly (a command per record would be far too slow): every
record visible here, the narrowest copy of each id, archived ones left out, and secret
ones only in the GM view. `focus` and `depth` keep one record's neighbourhood.

In map mode (`?mode=map`) it draws the map of the world instead, from `didact map`: the places
the viewer knows, the paths between them, the regions they lie in, and where the party is.
"""

import contextlib
from collections import deque

from didact.core.errors import DidactError
from didact.core.i18n import _, ngettext
from didact.core.ids import EntityId
from didact.core.output import JSON
from didact.services import details, knowledge
from didact.store.index import Row
from didact.web.app import Request, Response
from didact.web.html import Html, chip, h, icon, join, link_button, record_url, url
from didact.web.layout import page
from didact.web.pages.common import as_dict, as_list, type_color, type_label

MAX_DEPTH = 4
BOOKKEEPING = frozenset({"session", "scene", "summary"})
MAP_STATES: dict[str, int] = {  # a place's state on the map → its colour
    "here": 3,
    "visited": 1,
    "not visited": 9,
    "secret": 5,
    "unknown": 9,
}


def map_state_labels() -> dict[str, str]:
    return {
        "here": _("Where the party is"),
        "visited": _("Visited"),
        "not visited": _("Not visited"),
        "secret": _("Secret"),
        "unknown": _("Paths not yet followed"),
    }


def _graph_words() -> Html:
    """What graph.js says, in the page's language (data attributes: the CSP allows no inline
    script)."""
    words = {
        "unfollowed": _("A path not yet followed"),
        "failed": _("The graph couldn't load."),
        "empty": _("No records to draw yet: records and their links show up here."),
        "all-off": _("Every type is switched off: turn one on above."),
    }
    return join(h(t' data-t-{key}="{text}"') for key, text in words.items())


def show(req: Request) -> Response:
    if req.arg("mode") == "map":
        return _map_page(req)
    focus = req.arg("focus").strip()
    depth = _depth(req.arg("depth"))
    source = url("/api/graph", focus=focus or None, depth=str(depth) if focus else None)
    if focus:
        steps = [
            chip(
                ngettext("{n} step", "{n} steps", n),
                href=url("/graph", focus=focus, depth=str(n)),
                kind="active" if n == depth else "",
            )
            for n in range(1, MAX_DEPTH + 1)
        ]
        whole = link_button("/graph", _("Whole library"), icon_name="maximize-2", kind="flat")
        back = link_button(record_url(focus), _("Open record"), icon_name="file-text", kind="flat")
        before, _sep, after = _("around {record}", record="\x00").partition("\x00")
        focus_bar = h(
            t'<div class="chips">{icon("crosshair")}<span class="dim">{before}'
            t"<strong>{focus}</strong>{after}</span>{steps}{whole}{back}</div>"
        )
    else:
        focus_bar = None
    find = _("Find a record")
    body = h(
        t'<div class="graph-toolbar">{_modes(on_map=False)}<input class="entry" type="search" '
        t'id="graph-search" placeholder="{find}" aria-label="{find}">'
        t'<div class="chips" id="graph-types"></div>{focus_bar}</div>'
        t'<div class="graph" id="graph" data-src="{source}" data-focus="{focus}"{_graph_words()}>'
        t'<svg id="graph-svg" role="img" aria-label="{_("Records and their links")}"></svg>'
        t'<p class="graph-note dim" id="graph-note" hidden></p>'
        t'<div class="graph-help dim small">{_("Drag to move · wheel to zoom · click to open")}'
        t"</div></div><noscript><p>"
        t"{_('The graph needs JavaScript; the Records page lists everything.')}</p></noscript>"
    )
    return page(req, _("Graph"), body, nav="graph", wide=True, scripts=("graph.js",))


def _map_page(req: Request) -> Response:
    find = _("Find a place")
    drawing = _("The places the party knows and the paths between them")
    help_ = _("Drag to move · wheel to zoom · click a place to open it")
    no_js = _("The map needs JavaScript; the Status page lists the places near the party.")
    body = h(
        t'<div class="graph-toolbar">{_modes(on_map=True)}<input class="entry" type="search" '
        t'id="graph-search" placeholder="{find}" aria-label="{find}">'
        t'<div class="chips" id="graph-types"></div></div>'
        t'<div class="graph is-map" id="graph" data-src="/api/graph?mode=map"{_graph_words()}>'
        t'<svg id="graph-svg" role="img" aria-label="{drawing}"></svg>'
        t'<p class="graph-note dim" id="graph-note" hidden></p>'
        t'<div class="graph-help dim small">{help_}</div></div>'
        t"<noscript><p>{no_js}</p></noscript>"
    )
    return page(req, _("Map"), body, nav="graph", wide=True, scripts=("graph.js",))


def _modes(*, on_map: bool) -> Html:
    """Records or the map: the graph's two views."""
    records = chip(
        _("Records"), href="/graph", icon_name="share-2", kind="" if on_map else "active"
    )
    drawn = chip(_("Map"), href="/graph?mode=map", icon_name="map", kind="active" if on_map else "")
    return h(t'<div class="chips">{records}{drawn}</div>')


def api(req: Request) -> Response:
    if req.arg("mode") == "map":
        return Response.json(map_data(req))
    focus = req.arg("focus").strip() or None
    return Response.json(graph_data(req, focus=focus, depth=_depth(req.arg("depth"))))


def map_data(req: Request) -> dict[str, JSON]:
    """{nodes, edges, types, focus, labels} for the map: the places the viewer knows (all of
    them in the GM view), each path between them, the region each lies in, and where the party
    is. A path to a place the players haven't found leads to a "?"."""
    ran = req.run("map", gm=True)
    if not ran.ok:
        message = ran.error.message if ran.error is not None else _("the map couldn't be read")
        return {"nodes": [], "edges": [], "types": [], "error": message}
    places = [as_dict(p) for p in as_list(ran.data.get("places"))]
    known = {str(p.get("id")) for p in places}
    nodes: list[dict[str, JSON]] = []
    edges: list[tuple[str, str, str]] = []
    paths: set[tuple[str, str, str]] = set()
    for place in places:
        place_id = str(place.get("id"))
        state = str(place.get("state") or "not visited")
        nodes.append({"id": place_id, "name": str(place.get("name") or place_id), "state": state})
        region = place.get("region")
        if isinstance(region, str) and region in known:
            edges.append((place_id, region, "in"))
        for raw in as_list(place.get("exits")):
            exit_ = as_dict(raw)
            how, to = str(exit_.get("how") or ""), exit_.get("to")
            if isinstance(to, str) and to in known:
                first, second = sorted((place_id, to))
                if (first, second, how) not in paths:  # each end lists the same path
                    paths.add((first, second, how))
                    edges.append((place_id, to, how))
            elif to is None:  # somewhere the players don't know yet
                stub = f"?{len(nodes)}"
                nodes.append({"id": stub, "name": "?", "state": "unknown", "link": False})
                edges.append((place_id, stub, how))
    degree = {str(n["id"]): 0 for n in nodes}
    for source, target, _rel in edges:
        degree[source] += 1
        degree[target] += 1
    counts: dict[str, int] = {}
    for node in nodes:
        state = str(node["state"])
        node |= {
            "type": state,  # the chips switch places on and off by state
            "color": MAP_STATES.get(state, 9),
            "degree": degree[str(node["id"])],
            "knowledge": "secret" if state == "secret" else "known",
        }
        counts[state] = counts.get(state, 0) + 1
    order = list(MAP_STATES)
    labels = map_state_labels()
    types: list[JSON] = [
        {
            "type": state,
            "label": labels.get(state, state.capitalize()),
            "color": MAP_STATES.get(state, 9),
            "count": n,
        }
        for state, n in sorted(
            counts.items(), key=lambda item: order.index(item[0]) if item[0] in order else 99
        )
    ]
    here = ran.data.get("here")
    data: dict[str, JSON] = {
        "nodes": list[JSON](nodes),
        "edges": [
            {"source": s, "target": t_, "rel": rel, "kind": "region" if rel == "in" else "path"}
            for s, t_, rel in edges
        ],
        "types": types,
        "focus": here if isinstance(here, str) and here in known else None,
        "labels": True,
    }
    if not places:
        data["error"] = _("No places yet: `didact new loc …` makes one, `didact link` joins them.")
    return data


def _depth(raw: str) -> int:
    return max(1, min(MAX_DEPTH, int(raw))) if raw.isdigit() else 2


def graph_data(req: Request, *, focus: str | None, depth: int) -> dict[str, JSON]:
    """{nodes, edges, types, focus}: what the viewer may see, around `focus` if given."""
    wanted = focus.partition("@")[0] if focus else None
    try:
        with req.app.repo() as repo:
            chain = repo.chain()
            rows = repo.index().rows(chain) if repo.initialized() else []
            if focus and not EntityId.looks_like(focus.partition("@")[0]):
                with contextlib.suppress(DidactError):  # a name or an alias
                    wanted = str(repo.resolve(focus).entity.id)
    except DidactError as err:
        return {"nodes": [], "edges": [], "types": [], "error": err.message}
    order = {scope: i for i, scope in enumerate(chain)}
    best: dict[str, Row] = {}
    for record in rows:
        if record.knowledge == "secret" and not req.gm:
            continue
        kept = best.get(record.id)
        if kept is None or order.get(record.scope, 99) < order.get(kept.scope, 99):
            best[record.id] = record
    edges: list[tuple[str, str, str]] = []
    for record in best.values():
        links = record.data.get("links")
        for link in links if isinstance(links, list) else []:
            if not isinstance(link, dict):
                continue
            target = str(link.get("to", "")).partition("@")[0]
            rel = str(link.get("rel", ""))
            if not req.gm and knowledge.secret_path(rel):
                continue  # a way the players haven't found
            if target in best and target != record.id:
                edges.append((record.id, target, rel))
    with contextlib.suppress(DidactError), req.app.repo() as repo:
        for record in best.values():  # what holds what: a chest in a house, a sword in it
            for held in details.held_ids(repo, record.entity()):
                if held in best and held != record.id:
                    edges.append((record.id, held, "holds"))
    keep = set(best)
    missing = False
    if wanted:
        if wanted in best:
            keep = _around(wanted, edges, depth)
        else:
            keep, missing = set(), True
    degree: dict[str, int] = dict.fromkeys(keep, 0)
    kept_edges = [e for e in edges if e[0] in keep and e[1] in keep]
    for source, target, _rel in kept_edges:
        degree[source] += 1
        degree[target] += 1
    nodes: list[JSON] = [
        {
            "id": r.id,
            "name": r.name,
            "type": r.type,
            "scope": str(r.scope),
            "knowledge": r.knowledge,
            "color": type_color(r.type),
            "degree": degree.get(r.id, 0),
        }
        for r in sorted(best.values(), key=lambda r: r.id)
        if r.id in keep
    ]
    counts: dict[str, int] = {}
    for r in best.values():
        if r.id in keep:
            counts[r.type] = counts.get(r.type, 0) + 1
    types: list[JSON] = [
        {
            "type": kind,
            "label": type_label(kind),
            "color": type_color(kind),
            "count": n,
            "shown": bool(focus) or kind not in BOOKKEEPING,  # sessions and scenes: on request
        }
        for kind, n in sorted(counts.items(), key=lambda item: type_label(item[0]))
    ]
    data: dict[str, JSON] = {
        "nodes": nodes,
        "edges": [{"source": s, "target": t_, "rel": rel} for s, t_, rel in kept_edges],
        "types": types,
        "focus": wanted,
    }
    if missing:
        data["error"] = _("nothing called {name} to show here", name=focus)
    return data


def _around(start: str, edges: list[tuple[str, str, str]], depth: int) -> set[str]:
    """Records within `depth` links of `start`, either way."""
    near: dict[str, set[str]] = {}
    for source, target, _rel in edges:
        near.setdefault(source, set()).add(target)
        near.setdefault(target, set()).add(source)
    seen = {start}
    queue = deque([(start, 0)])
    while queue:
        node, steps = queue.popleft()
        if steps == depth:
            continue
        for other in near.get(node, ()):
            if other not in seen:
                seen.add(other)
                queue.append((other, steps + 1))
    return seen
