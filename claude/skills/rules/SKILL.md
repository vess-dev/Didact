---
name: rules
description: Look a rule up in the game's rules text.
disable-model-invocation: true
argument-hint: "<topic>"
---

!`"${CLAUDE_PLUGIN_ROOT}/bin/didact" rules lookup $ARGUMENTS`

Answer the player's rules question ("$ARGUMENTS") from this text, citing the section. If it
doesn't cover it, try `didact search $ARGUMENTS`, and say plainly if the rules are silent.
