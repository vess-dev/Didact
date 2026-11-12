"""Markdown to HTML, for command output and record bodies.

Raw HTML in the text is shown as text, never run: the renderer has HTML switched off, and
markdown-it refuses `javascript:` and similar links. Single line breaks are kept, because
Didact's output is written line by line.
"""

from markdown_it import MarkdownIt

from didact.web.html import Html, h

_RENDERER = MarkdownIt("commonmark", {"html": False, "breaks": True}).enable(
    ["table", "strikethrough"]
)


def markdown(text: str) -> Html:
    """Rendered Markdown in a `.prose` block (nothing for empty text)."""
    if not text.strip():
        return Html("")
    return h(t'<div class="prose">{Html(_RENDERER.render(text))}</div>')


def inline(text: str) -> Html:
    """One line of Markdown (a hint, a summary) without the paragraph around it."""
    return Html(_RENDERER.renderInline(text))
