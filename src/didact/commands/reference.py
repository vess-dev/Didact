"""The reference desk: rules lookup, define, explain."""

import difflib
from typing import Annotated

from didact.commands._common import open_repo
from didact.commands.registry import REGISTRY, Metavar, command
from didact.core import labels
from didact.core.context import Context
from didact.core.errors import NotFoundError
from didact.core.i18n import _, ngettext, translate
from didact.core.output import JSON, Out, code


@command(
    "rules lookup",
    summary="Look a rule up in the enabled packs' rules text (with the commands that run it)",
    examples=(
        "didact rules lookup saves",
        "didact rules lookup critical damage",
        "didact rules lookup fatigue --detail full",
    ),
)
def rules_lookup(
    ctx: Context, *words: Annotated[str, "what you're looking for", Metavar("topic")]
) -> Out:
    from didact.core.words import phrase_words
    from didact.services import packs, reference, rules, rulings

    repo = open_repo(ctx)
    active = packs.active(repo)
    played = repo.active_world() is not None
    asked = list(words)
    found = reference.lookup(active, asked)
    settled = rulings.matching(repo, asked) if played else []
    split = phrase_words(asked) if not found and not settled else None
    if split is not None:  # a quoted phrase that isn't there: its words, each as a word
        found = reference.lookup(active, split, whole=True)
        settled = rulings.matching(repo, split) if played else []
    if not found and not settled:
        topic = " ".join(words)
        return Out(
            data={"sections": [], "rulings": []},
            md=_(
                "no rules text about {quoted} (try `didact explain {topic}` or other words)",
                quoted=repr(topic),
                topic=topic,
            ),
        )
    full = ctx.detail == "full"
    lines: list[str] = [f"- {rulings.line(e)}" for e in settled]
    if settled:
        lines = [_("Rulings here (they come first):"), *lines, ""]
    if split is not None:  # (it says first that the phrase isn't there)
        lines.insert(
            0,
            _(
                "no rules text about {quoted} as written; these have its words:",
                quoted=repr(" ".join(asked)),
            ),
        )
    rows: list[JSON] = []
    all_rules = rules.all_rules(active)
    for _unused, section in found:
        where = " · ".join(p for p in (section.page, section.source) if p)
        lines += [
            f"## {section.title} ({section.qualified}{' · ' + where if where else ''})",
            reference.excerpt(section.body, full),
        ]
        linked = list(section.mechanics)
        linked += [
            r.id.rpartition(".")[2] for r in all_rules if r.data.get("reference") == section.id
        ]
        for ref in dict.fromkeys(linked):
            try:
                rule = rules.find_rule(active, ref, section.pack)
            except NotFoundError:
                continue
            lines.append(_("run it: {command}", command=code(rule.usage())))
        lines.append("")
        rows.append(
            {
                "id": section.qualified,
                "title": section.title,
                "body": section.body,
                "source": section.source,
            }
        )
    ruled: list[JSON] = [{"id": str(e.id), "line": rulings.line(e)} for e in settled]
    data: dict[str, JSON] = {"sections": rows, "rulings": ruled}
    if split is not None:
        data["words"] = list[JSON](split)  # what found them: the phrase's words
    return Out(data=data, md="\n".join(lines).rstrip())


@command(
    "define",
    summary="Define a game term from the enabled packs' glossaries",
    examples=("didact define fatigue", "didact define 'chaos factor'"),
)
def define(ctx: Context, *words: Annotated[str, "the term", Metavar("term")]) -> Out:
    from didact.services import packs, reference

    repo = open_repo(ctx)
    active = packs.active(repo)
    word = " ".join(words)
    found = reference.define(active, word)
    if not found:
        known = [t.term for t in reference.terms(active)]
        close = difflib.get_close_matches(word, known, n=3)
        hint = (
            _("did you mean {terms}?", terms=", ".join(close))
            if close
            else _("try `didact rules lookup {word}`", word=word)
        )
        raise NotFoundError(_("no glossary term {word}", word=repr(word)), hint=hint)
    lines: list[str] = []
    for term in found:
        lines.append(f"**{term.term}** ({term.pack}): {term.definition}")
        if term.see:
            lines.append(_("see: {terms}", terms=", ".join(term.see)))
    data: dict[str, JSON] = {
        "terms": [{"term": t.term, "pack": t.pack, "definition": t.definition} for t in found]
    }
    return Out(data=data, md="\n".join(lines))


@command(
    "explain",
    summary="What is this? A rule, table, record type, compendium entry, term, command or guide",
    examples=(
        "didact explain save",
        "didact explain weather",
        "didact explain roll",
        "didact explain fatigue",
    ),
)
def explain(ctx: Context, *words: Annotated[str, "the thing", Metavar("name")]) -> Out:
    from didact import guides
    from didact.services import packs, reference, rules, sheets

    name = " ".join(words).strip()
    repo = open_repo(ctx)
    found: list[str] = []
    data: dict[str, JSON] = {"name": name, "matches": []}
    matches: list[JSON] = []
    active = packs.active(repo) if repo.initialized() else None
    if active is not None:
        try:
            rule = rules.find_rule(active, name)
            help_text = str(rule.data.get("help") or rule.title)
            found.append(
                _(
                    "- {kind} {id}: {help}\n  run: {command} · more: {more}",
                    kind=labels.inline(rule.kind, labels.item_kind(rule.kind)),
                    id=rule.id,
                    help=help_text,
                    command=code(rule.usage()),
                    more=code(f"didact rules show {rule.id}"),
                )
            )
            matches.append({"kind": rule.kind, "id": rule.id})
        except NotFoundError:
            pass
        for kind, template, how in (
            (
                "table",
                _("- table {item} · {title} ({source})\n  use: {command}"),
                "didact table roll {id}",
            ),
            (
                "entry",
                _("- compendium entry {item} · {title} ({source})\n  use: {command}"),
                "didact spawn {id}",
            ),
            (
                "deck",
                _("- deck {item} · {title} ({source})\n  use: {command}"),
                "didact deck draw {id}",
            ),
            (
                "bag",
                _("- bag {item} · {title} ({source})\n  use: {command}"),
                "didact bag draw {id}",
            ),
        ):
            try:
                item = active.find(kind, name)
            except NotFoundError:
                continue
            title = item.data.get("title") or item.data.get("name") or item.id
            found.append(
                template.format(
                    item=item.qualified,
                    title=title,
                    source=item.source,
                    command=code(how.format(id=item.qualified)),
                )
            )
            matches.append({"kind": kind, "id": item.qualified})
        sheet = sheets.sheet(repo, name)
        if not sheet.empty:
            fields = ", ".join(f for s in sheet.schemas for f in s.fields)
            found.append(
                _(
                    "- record type {name}: fields {fields}\n  template: {command}",
                    name=name,
                    fields=fields,
                    command=code(f"didact template {name}"),
                )
            )
            matches.append({"kind": "type", "id": name})
        for term in reference.define(active, name):
            found.append(
                _(
                    "- term {term} ({pack}): {definition}",
                    term=term.term,
                    pack=term.pack,
                    definition=term.definition,
                )
            )
            matches.append({"kind": "term", "id": term.term})
        for _unused, section in reference.lookup(active, name.split(), limit=1):
            found.append(
                _(
                    "- rules text: {title} ({id}) → {command}",
                    title=section.title,
                    id=section.qualified,
                    command=code(f"didact rules lookup {name}"),
                )
            )
            matches.append({"kind": "reference", "id": section.qualified})
    spec = REGISTRY.get(name)
    if spec is not None:
        found.append(
            _(
                "- command `didact {name}`: {summary}\n  usage: {usage}",
                name=spec.name,
                summary=translate(spec.summary),
                usage=code(spec.usage()),
            )
        )
        matches.append({"kind": "command", "id": spec.name})
    if name in guides.topics():
        found.append(
            _(
                "- guide {name}: {about} → {command}",
                name=name,
                about=guides.topics()[name],
                command=code(f"didact guide {name}"),
            )
        )
        matches.append({"kind": "guide", "id": name})
    data["matches"] = matches
    if not found:
        raise NotFoundError(
            _("nothing called {name} here", name=repr(name)),
            hint=_("try `didact rules lookup`, `didact find` or `didact commands`"),
        )
    return Out(data=data, md="\n".join([f"{name}:", *found]))


@command(
    "search",
    summary="Search everything at once: rules, terms, mechanics, tables, records, docs, …",
    examples=(
        "didact search fatigue",
        "didact search chaos factor --in rules --in terms",
        "didact search sweeney --in records --in transcript",
        "didact search 'hidden path' --in docs",
    ),
    description=(
        "One ranked list across every source (every word must appear; titles count most).\n"
        "Each hit ends with the command that shows it. Records follow player-safe rules\n"
        "unless you pass --gm. Sources: rules, terms, mechanics, tables, compendium, records,\n"
        "transcript, docs."
    ),
)
def search(
    ctx: Context,
    *words: Annotated[str, "what you're looking for", Metavar("words")],
    in_: Annotated[list[str] | None, "only these sources", Metavar("source")] = None,
    limit: Annotated[int, "how many hits", Metavar("n")] = 12,
    gm: Annotated[bool, "records' secrets too (GM eyes only)"] = False,
) -> Out:
    from didact.services import packs
    from didact.services import search as finder

    query = " ".join(words).strip()
    if not query:
        raise NotFoundError(_("search for something"), hint=_("e.g. `didact search fatigue`"))
    wanted = in_ or list(finder.SOURCES)
    unknown = sorted(set(wanted) - set(finder.SOURCES))
    if unknown:
        raise NotFoundError(
            _("no source {source}", source=repr(unknown[0])),
            hint=_("sources: {sources}", sources=", ".join(finder.SOURCES)),
        )
    repo = open_repo(ctx)
    active = packs.active(repo)
    docs = [  # the help in the reader's language, and in English too: both words find it
        finder.Doc(
            f"command:{spec.name}",
            f"didact {spec.name}: {translate(spec.summary)}",
            " ".join(
                dict.fromkeys(
                    [
                        translate(spec.summary),
                        spec.summary,
                        translate(spec.description),
                        spec.description,
                        *spec.examples,
                    ]
                )
            ),
            f"didact help {spec.name}",
        )
        for spec in REGISTRY.values()
    ]
    hits, hidden = finder.search(repo, active, query, sources=wanted, gm=gm, limit=limit, docs=docs)
    if not hits:
        lines = [_("nothing matches {query} (try fewer or other words)", query=repr(query))]
    else:
        lines = [
            ngettext(
                "{n} best matches for {query}:",
                "{n} best matches for {query}:",
                len(hits),
                query=repr(query),
            )
        ]
        for hit in hits:
            source = labels.inline(hit.source, labels.search_source(hit.source))
            lines.append(f"- [{source}] {hit.title} · `{hit.next}`")
            if hit.snippet:
                lines.append(f"  {hit.snippet}")
    if hidden:
        lines.append(
            ngettext(
                "({n} secret record matches hidden; `--gm` shows them)",
                "({n} secret record matches hidden; `--gm` shows them)",
                hidden,
            )
        )
    data: dict[str, JSON] = {"query": query, "hits": [h.to_data() for h in hits], "hidden": hidden}
    return Out(data=data, md="\n".join(lines))
