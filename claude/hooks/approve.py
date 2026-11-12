"""PreToolUse hook: let plain `didact …` commands run without a permission prompt.

Only a single `didact` command is approved: nothing chained (`;`, `&&`, `|`), redirected
(`>`, `<`) or substituted (`$…`, backticks). Anything else gets no decision from this hook, so
Claude Code asks as usual. Quoted text is fine: `didact roll '6d10>=8'`.
"""

import json
import shlex
import sys

OPERATORS = frozenset(";&|<>()")


def plain_didact(command: str) -> bool:
    if "\n" in command or "`" in command or "$" in command:
        return False
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:  # unbalanced quotes
        return False
    if not tokens or tokens[0] != "didact":  # the one on PATH; not any file named didact
        return False
    return not any(token and set(token) <= OPERATORS for token in tokens)


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    command = str(event.get("tool_input", {}).get("command", ""))
    if event.get("tool_name") == "Bash" and plain_didact(command):
        decision = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "a plain didact command",
        }
        print(json.dumps({"hookSpecificOutput": decision}))


if __name__ == "__main__":
    main()
