"""`pack validate` warns where an expression quotes a parameter of free text (`'$book'`): an
apostrophe in the text ends the quotes and the rule breaks on it, while `@book` reads it whole.
An enum's or a number's quotes are left be, and so is quoted text outside an expression (the
`quote-lite` fixture)."""

from tests.conftest import Cli

FIX = "(fix: read it as `@book`, which takes any text whole)"


def test_a_quoted_free_text_parameter_is_a_warning(cli: Cli) -> None:
    checked = cli("pack", "validate", "quote-lite")
    assert checked.code == 0 and "✔ ok, 4 warnings: quote-lite 0.1.0" in checked.out
    quoted = "`'$book'` quotes `$book`, free text: an apostrophe in it ends the quotes"
    for line in (6, 8, 9):  # `if:`, a `let:` value, a message's `{…}`
        assert f"warning: rules/books.yaml:{line}: {quoted} {FIX}" in checked.out
    assert "generators/shelf.yaml:6: `'$first'` quotes `$first`" in checked.out  # drafts too
    assert "$dose" not in checked.out and "$count" not in checked.out  # an enum, a number
    assert cli("world", "new", "w", "--system", "quote-lite").code == 0
    assert cli("campaign", "new", "c").code == 0
    broken = cli("do", "shelve", "book=Ana's Diary")  # what the warning is about
    assert broken.code == 1 and "unexpected \"s Diary'" in broken.err
    assert "Read: Ana's Diary." in cli("do", "read", "book=Ana's Diary").out
