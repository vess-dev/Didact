---
name: roll
description: Roll dice through Didact (logged).
disable-model-invocation: true
argument-hint: "<dice, e.g. 2d6+1>"
---

Roll `$ARGUMENTS` with Didact: `didact roll '$ARGUMENTS' --reason 'player roll'`. Show the
player the result line exactly as Didact prints it, and what it means if the context makes
that clear.
